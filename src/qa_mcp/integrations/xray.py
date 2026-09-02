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

Jira and Xray are two different APIs, and which one is needed depends on the
deployment:

* **Jira REST** (``/rest/api/{2,3}``) reads and creates issues. Both
  deployments use it, authenticated with the Jira credentials.
* **Xray Cloud** keeps test steps outside Jira entirely and exposes them only
  through its GraphQL API at ``xray.cloud.getxray.app``, authenticated with a
  separate Xray API Key (client id + secret) exchanged for a 24-hour token.
* **Xray Server/Data Center** serves the same data over REST under
  ``/rest/raven/``, on the Jira host and with the Jira credentials.

Creating a Test through the Jira issue API alone produces an issue with no
steps. That is the trap this module exists to avoid.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta
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


# Xray Server/Data Center serves test steps from its 1.0 endpoints, which
# remain available under the 2.0 API.
XRAY_SERVER_API_VERSION = "1.0"

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

        self._transport = transport
        self._cloud_client: httpx.Client | None = None
        self._cloud_token: str | None = None
        self._cloud_token_expires: datetime | None = None

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
        if self._cloud_client is not None:
            self._cloud_client.close()

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

    # -- Xray Cloud API ----------------------------------------------------

    def _cloud(self) -> httpx.Client:
        """Client for the Xray Cloud API host, built on first use."""
        if self._cloud_client is None:
            xray = self.settings.xray
            self._cloud_client = httpx.Client(
                base_url=xray.cloud_base_url,
                timeout=xray.timeout_seconds,
                verify=xray.verify_tls,
                transport=self._transport
                or httpx.HTTPTransport(retries=xray.max_retries, verify=xray.verify_tls),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        return self._cloud_client

    def _cloud_authorization(self) -> str:
        """Exchange the Xray API Key for a bearer token, reusing it until it ages out.

        The token Xray issues is valid for 24 hours; it is cached for slightly
        less so a long-running server never presents an expired one.
        """
        now = datetime.now()
        if self._cloud_token and self._cloud_token_expires and now < self._cloud_token_expires:
            return self._cloud_token

        xray = self.settings.xray
        if not (xray.client_id and xray.client_secret):
            raise XrayError(
                "Xray Cloud API anahtarı yok. Xray Global Settings -> API Keys altından "
                "bir anahtar oluşturup QA_MCP_XRAY_CLIENT_ID ve QA_MCP_XRAY_CLIENT_SECRET "
                "değerlerini ayarlayın. Bu, Jira API token'ından farklı bir kimliktir."
            )

        response = self._cloud().post(
            "/api/v2/authenticate",
            json={
                "client_id": xray.client_id,
                "client_secret": xray.client_secret.get_secret_value(),
            },
        )
        if not response.is_success:
            raise XrayError(
                f"Xray Cloud kimlik doğrulaması başarısız (HTTP {response.status_code}). "
                "QA_MCP_XRAY_CLIENT_ID ve QA_MCP_XRAY_CLIENT_SECRET değerlerini kontrol edin.",
                status_code=response.status_code,
                method="POST",
                path="/api/v2/authenticate",
                body_excerpt=response.text[:200],
            )

        # The endpoint answers with the bare token as a JSON string.
        token = response.json()
        if not isinstance(token, str) or not token:
            raise XrayError(
                "Xray Cloud beklenmeyen bir kimlik doğrulama yanıtı döndü.",
                method="POST",
                path="/api/v2/authenticate",
                body_excerpt=response.text[:200],
            )

        self._cloud_token = token
        self._cloud_token_expires = now + timedelta(hours=23)
        return token

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Run a GraphQL operation against Xray Cloud.

        Values travel as variables rather than interpolated text, so a summary
        containing quotes or braces cannot corrupt - or inject into - the query.
        """
        response = self._cloud().post(
            "/api/v2/graphql",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {self._cloud_authorization()}"},
        )
        if not response.is_success:
            raise XrayError(
                f"Xray Cloud GraphQL isteği başarısız (HTTP {response.status_code}).",
                status_code=response.status_code,
                method="POST",
                path="/api/v2/graphql",
                body_excerpt=response.text[:300],
            )

        payload = response.json()
        # GraphQL reports failures inside a 200 response.
        if payload.get("errors"):
            messages = "; ".join(
                str(e.get("message", e)) for e in payload["errors"] if isinstance(e, dict)
            )
            raise XrayError(
                f"Xray Cloud GraphQL hatası: {messages or payload['errors']}",
                method="POST",
                path="/api/v2/graphql",
            )
        return payload.get("data") or {}

    # -- read operations ---------------------------------------------------

    def verify_connection(self) -> dict[str, Any]:
        """Confirm the credentials work, and report exactly what they reach.

        Jira and Xray are separate services on Cloud, so a working Jira token
        does not imply Xray access. This reports both, and names the variables
        still missing rather than leaving the gap to be discovered on the first
        write.
        """
        xray = self.settings.xray
        user = self._request("GET", "/myself")

        xray_api: dict[str, Any] = {
            "reachable": False,
            "detail": None,
            "missing_settings": xray.missing_xray_api_settings,
        }
        if xray.has_xray_api:
            if xray.is_cloud:
                try:
                    self._cloud_authorization()
                    xray_api["reachable"] = True
                    xray_api["detail"] = "Xray Cloud API anahtarı doğrulandı"
                except XrayError as exc:
                    xray_api["detail"] = str(exc)
            else:
                # Server/DC reaches Xray with the Jira credentials already proven above.
                xray_api["reachable"] = True
                xray_api["detail"] = "Xray Server/DC, Jira kimlik bilgileriyle erişilebilir"
        else:
            xray_api["detail"] = (
                "Xray API anahtarı ayarlanmamış; test adımları aktarılamaz. "
                f"Eksik: {', '.join(xray.missing_xray_api_settings)}"
            )

        return {
            "connected": True,
            "base_url": xray.base_url,
            "api_version": xray.api_version,
            "auth_mode": xray.auth_mode,
            "deployment": xray.deployment,
            "account": {
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
                "account_id": user.get("accountId"),
                "active": user.get("active"),
            },
            "xray_api": xray_api,
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
        """Create a Test issue from a payload built by ``testcase_to_xray``.

        Routes by deployment, because the two store test steps in different
        places:

        * **Cloud** - one GraphQL ``createTest`` carrying the steps.
        * **Server/DC** - create the Jira issue, then post each step to Xray's
          REST endpoint on the same host.

        A payload with steps is never created through the Jira issue API alone:
        that yields a Test with no steps, which looks like success and is not.

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

        steps = [
            {
                "action": str(step.get("action", "")),
                "data": str(step.get("data", "")),
                "result": str(step.get("result", "")),
            }
            for step in xray_payload.get("steps") or []
        ]
        test_type = xray_payload.get("testtype") or self.settings.xray.test_issue_type

        if steps and not self.settings.xray.has_xray_api:
            missing = ", ".join(self.settings.xray.missing_xray_api_settings)
            raise XrayError(
                f"Bu test case {len(steps)} adım içeriyor ancak Xray API'sine erişim yok, "
                "dolayısıyla adımlar aktarılamaz. Jira issue API'si tek başına adımsız bir "
                f"Test oluşturur. Eksik ayar(lar): {missing}."
            )

        if self.settings.xray.is_cloud and steps:
            return self._create_test_cloud(fields, steps, test_type)
        return self._create_test_server(fields, steps)

    def _create_test_cloud(
        self,
        fields: dict[str, Any],
        steps: list[dict[str, str]],
        test_type: str,
    ) -> dict[str, Any]:
        """Create a Test with its steps in a single Xray Cloud GraphQL call."""
        mutation = """
        mutation CreateTest($testType: UpdateTestTypeInput!, $steps: [CreateStepInput], $jira: JSON!) {
          createTest(testType: $testType, steps: $steps, jira: $jira) {
            test {
              issueId
              jira(fields: ["key"])
            }
            warnings
          }
        }
        """
        data = self._graphql(
            mutation,
            {
                "testType": {"name": test_type},
                "steps": steps,
                "jira": {"fields": fields},
            },
        )
        result = (data.get("createTest") or {}).get("test") or {}
        key = (result.get("jira") or {}).get("key")
        return {
            "created": True,
            "issue_key": key,
            "issue_id": result.get("issueId"),
            "url": f"{self.settings.xray.base_url}/browse/{key}" if key else None,
            "steps_imported": len(steps),
            "api_used": "xray-cloud-graphql",
            "warnings": (data.get("createTest") or {}).get("warnings") or [],
        }

    def _create_test_server(
        self,
        fields: dict[str, Any],
        steps: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Create the Jira issue, then attach steps through Xray's REST API.

        Server/Data Center has no single call that does both, so the issue can
        exist while a later step upload fails. That partial state is reported
        rather than hidden: the caller gets the issue key and the count that
        actually landed.
        """
        created = self._request("POST", "/issue", json={"fields": fields})
        key = created.get("key")

        imported = 0
        warnings: list[str] = []
        if steps and key:
            for index, step in enumerate(steps, 1):
                try:
                    self._raven_request(
                        "POST",
                        f"/api/test/{key}/step",
                        json={
                            "step": step["action"],
                            "data": step["data"],
                            "result": step["result"],
                        },
                    )
                    imported += 1
                except XrayError as exc:
                    warnings.append(f"Adım {index} aktarılamadı: {exc}")
                    break

        if steps and imported < len(steps):
            warnings.append(
                f"{key} oluşturuldu ancak {len(steps)} adımdan {imported} tanesi aktarıldı. "
                "Test'i Jira'da kontrol edin."
            )

        return {
            "created": True,
            "issue_key": key,
            "issue_id": created.get("id"),
            "url": f"{self.settings.xray.base_url}/browse/{key}" if key else None,
            "steps_imported": imported,
            "api_used": "jira-rest+xray-raven" if steps else "jira-rest",
            "warnings": warnings,
        }

    def _raven_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Call Xray's Server/Data Center REST API.

        It lives on the Jira host under /rest/raven and accepts the same
        credentials, so only the base path differs.
        """
        base = f"{self.settings.xray.base_url}/rest/raven/{XRAY_SERVER_API_VERSION}"
        try:
            response = self._client.request(method, f"{base}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise XrayError(
                f"Xray (raven) API'sine bağlanılamadı: {exc}", method=method, path=path
            ) from exc

        if response.is_success:
            if not response.content:
                return {}
            try:
                payload = response.json()
            except ValueError:
                return {}
            return payload if isinstance(payload, dict) else {"value": payload}

        raise XrayError(
            f"Xray {method} {path} -> HTTP {response.status_code}. "
            f"{_STATUS_HINTS.get(response.status_code, '')}".strip(),
            status_code=response.status_code,
            method=method,
            path=path,
            body_excerpt=response.text[:300],
        )


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
