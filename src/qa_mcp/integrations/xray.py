"""
Jira/Xray client.

QA-MCP is useful entirely offline; this is the opt-in path for an organisation
that wants the server to read from, and optionally write to, its own tenant.
Nothing here runs unless ``QA_MCP_XRAY_ENABLED`` is set and the credentials
validate at startup.

Two rules shape this module:

* **Credentials never appear in output.** Errors quote the status, the method
  and the path, never the Authorization header or the token.
* **Writes are separate from reads.** Every write method checks
  ``enable_write_tools`` itself, rather than trusting the caller to have
  checked, so a mistake in tool registration cannot create issues in someone's
  Jira.
"""

from __future__ import annotations

import base64
from types import TracebackType
from typing import Any

import httpx

from qa_mcp.config import Settings, get_settings


class XrayError(RuntimeError):
    """A Jira/Xray request failed.

    Carries enough context to act on - status, method, path and a short body
    excerpt - and nothing that could leak a credential.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        method: str | None = None,
        path: str | None = None,
        body_excerpt: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path
        self.body_excerpt = body_excerpt

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "status_code": self.status_code,
            "method": self.method,
            "path": self.path,
            "detail": self.body_excerpt,
        }


# Status codes worth explaining rather than echoing.
_STATUS_HINTS = {
    401: "Kimlik doğrulama başarısız. QA_MCP_XRAY_API_TOKEN ve QA_MCP_XRAY_AUTH_MODE değerlerini kontrol edin "
    "(Jira Cloud genellikle auth_mode='basic' ve e-posta ister).",
    403: "Kimlik doğrulandı ancak yetki yok. Token sahibinin bu proje üzerinde izni olduğundan emin olun.",
    404: "Kaynak bulunamadı. Proje anahtarını, issue key'ini ve QA_MCP_XRAY_API_VERSION değerini kontrol edin "
    "(Cloud için '3', Server/DC için '2').",
    429: "Jira hız sınırı uygulandı. İstek sıklığını azaltın veya daha sonra tekrar deneyin.",
}


class XrayClient:
    """Thin, synchronous Jira/Xray REST client.

    Usable as a context manager; a client created without one closes its
    transport in ``close()``.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Build a client for the configured tenant.

        Args:
            settings: Runtime configuration; the process settings if omitted.
            transport: Injected transport, used by the tests to exercise the
                request/response handling without a network.
        """
        self.settings = settings or get_settings()
        xray = self.settings.xray

        if not xray.is_configured:
            raise XrayError(
                "Xray tenant yapılandırılmamış. QA_MCP_XRAY_ENABLED=true ile birlikte "
                "QA_MCP_XRAY_BASE_URL ve QA_MCP_XRAY_API_TOKEN değerlerini ayarlayın."
            )

        self._client = httpx.Client(
            base_url=f"{xray.base_url}/rest/api/{xray.api_version}",
            headers=self._auth_headers(),
            timeout=xray.timeout_seconds,
            verify=xray.verify_tls,
            transport=transport
            or httpx.HTTPTransport(retries=xray.max_retries, verify=xray.verify_tls),
        )

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> XrayClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- internals ---------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Authorization header for the configured auth mode."""
        xray = self.settings.xray
        token = xray.api_token.get_secret_value() if xray.api_token else ""

        if xray.auth_mode == "basic":
            raw = f"{xray.email}:{token}".encode()
            credential = base64.b64encode(raw).decode()
            authorization = f"Basic {credential}"
        else:
            authorization = f"Bearer {token}"

        return {
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Issue a request and turn any failure into an actionable XrayError."""
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise XrayError(
                f"Jira isteği {self.settings.xray.timeout_seconds}s içinde yanıt vermedi. "
                "QA_MCP_XRAY_TIMEOUT_SECONDS değerini artırmayı deneyin.",
                method=method,
                path=path,
            ) from exc
        except httpx.HTTPError as exc:
            # str(exc) carries the URL but never the headers, so no credential.
            raise XrayError(
                f"Jira'ya bağlanılamadı: {exc}",
                method=method,
                path=path,
            ) from exc

        if response.is_success:
            if not response.content:
                return {}
            try:
                payload = response.json()
            except ValueError as exc:
                raise XrayError(
                    "Jira JSON olmayan bir yanıt döndü. base_url bir Jira örneğini "
                    "gösteriyor mu kontrol edin.",
                    status_code=response.status_code,
                    method=method,
                    path=path,
                    body_excerpt=response.text[:200],
                ) from exc
            return payload if isinstance(payload, dict) else {"value": payload}

        hint = _STATUS_HINTS.get(response.status_code, "")
        message = f"Jira {method} {path} -> HTTP {response.status_code}."
        raise XrayError(
            f"{message} {hint}".strip(),
            status_code=response.status_code,
            method=method,
            path=path,
            body_excerpt=response.text[:300],
        )

    def _require_writes(self, operation: str) -> None:
        """Guard every mutating call.

        Checked here rather than only at registration time so that no future
        caller can reach a write by accident.
        """
        if not self.settings.enable_write_tools:
            raise XrayError(
                f"'{operation}' Jira'da değişiklik yapar ve write tool'lar kapalı. "
                "Bilinçli olarak etkinleştirmek için QA_MCP_ENABLE_WRITE_TOOLS=true ayarlayın."
            )

    # -- read operations ---------------------------------------------------

    def verify_connection(self) -> dict[str, Any]:
        """Confirm the credentials work, and report who they belong to.

        The first thing to run after handing QA-MCP a token.
        """
        user = self._request("GET", "/myself")
        return {
            "connected": True,
            "base_url": self.settings.xray.base_url,
            "api_version": self.settings.xray.api_version,
            "auth_mode": self.settings.xray.auth_mode,
            "account": {
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
                "account_id": user.get("accountId"),
                "active": user.get("active"),
            },
            "write_tools_enabled": self.settings.enable_write_tools,
        }

    def get_test(self, issue_key: str) -> dict[str, Any]:
        """Fetch a single Xray test issue."""
        issue = self._request("GET", f"/issue/{issue_key}")
        return _summarize_issue(issue)

    def search_tests(
        self,
        jql: str | None = None,
        project_key: str | None = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Search test issues by JQL, or list a project's tests."""
        xray = self.settings.xray
        if not jql:
            key = project_key or xray.project_key
            if not key:
                raise XrayError(
                    "Arama için jql veya project_key gerekli. Varsayılan için "
                    "QA_MCP_XRAY_PROJECT_KEY ayarlayın."
                )
            jql = (
                f'project = "{key}" AND issuetype = "{xray.test_issue_type}" ORDER BY created DESC'
            )

        payload = self._request(
            "POST",
            "/search",
            json={
                "jql": jql,
                "maxResults": max(1, min(max_results, 100)),
                "fields": ["summary", "status", "priority", "labels", "components", "issuetype"],
            },
        )
        issues = payload.get("issues", [])
        return {
            "jql": jql,
            "total": payload.get("total", len(issues)),
            "returned": len(issues),
            "tests": [_summarize_issue(issue) for issue in issues],
        }

    # -- write operations --------------------------------------------------

    def create_test(self, xray_payload: dict[str, Any]) -> dict[str, Any]:
        """Create a test issue from a payload built by ``testcase_to_xray``.

        Gated behind ``QA_MCP_ENABLE_WRITE_TOOLS``.
        """
        self._require_writes("xray_create_test")

        fields = dict(xray_payload.get("fields") or {})
        if not fields:
            raise XrayError("xray_payload 'fields' içermiyor; önce testcase_to_xray çalıştırın.")

        if "project" not in fields:
            key = self.settings.xray.project_key
            if not key:
                raise XrayError(
                    "Proje belirtilmemiş. Payload'a fields.project ekleyin veya "
                    "QA_MCP_XRAY_PROJECT_KEY ayarlayın."
                )
            fields["project"] = {"key": key}

        created = self._request("POST", "/issue", json={"fields": fields})
        key = created.get("key")
        return {
            "created": True,
            "issue_key": key,
            "issue_id": created.get("id"),
            "url": f"{self.settings.xray.base_url}/browse/{key}" if key else None,
        }


def _summarize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Reduce a Jira issue to the fields QA-MCP reports.

    Jira issues are large and carry tenant detail QA-MCP has no business
    forwarding into a model's context.
    """
    fields = issue.get("fields") or {}

    def _name(value: Any) -> Any:
        return value.get("name") if isinstance(value, dict) else value

    return {
        "issue_key": issue.get("key"),
        "issue_id": issue.get("id"),
        "summary": fields.get("summary"),
        "status": _name(fields.get("status")),
        "priority": _name(fields.get("priority")),
        "issue_type": _name(fields.get("issuetype")),
        "labels": fields.get("labels") or [],
        "components": [_name(c) for c in (fields.get("components") or [])],
    }
