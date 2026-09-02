"""Tests for the enterprise configuration path.

An organisation hands QA-MCP its own tokens and thresholds; these assert that
doing so changes what the server exposes and how it behaves, that a wrong
configuration fails at startup rather than at first use, and that credentials
never reach a log or a tool result.
"""

import base64
import json

import httpx
import pytest

from qa_mcp.config import LintSettings, Settings, XraySettings
from qa_mcp.integrations.xray import XrayClient, XrayError

TENANT = {
    "QA_MCP_XRAY_ENABLED": "true",
    "QA_MCP_XRAY_BASE_URL": "https://acme.atlassian.net/",
    "QA_MCP_XRAY_AUTH_MODE": "basic",
    "QA_MCP_XRAY_EMAIL": "qa@acme.com",
    "QA_MCP_XRAY_API_TOKEN": "SECRET-TOKEN-VALUE",
    "QA_MCP_XRAY_PROJECT_KEY": "QA",
}


@pytest.fixture(autouse=True)
def restore_tool_registry():
    """Undo tool registrations a test performs.

    The server is a module-level singleton, so registering optional tools
    mutates state every later test would otherwise see.
    """
    from qa_mcp.server import mcp

    before = {tool.name for tool in mcp._tool_manager.list_tools()}
    yield
    for name in {tool.name for tool in mcp._tool_manager.list_tools()} - before:
        mcp.remove_tool(name)


@pytest.fixture
def tenant_env(monkeypatch):
    """A fully configured tenant."""
    for key, value in TENANT.items():
        monkeypatch.setenv(key, value)
    return TENANT


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/myself"):
        return httpx.Response(
            200,
            json={
                "displayName": "QA Bot",
                "emailAddress": "qa@acme.com",
                "accountId": "abc",
                "active": True,
            },
        )
    if request.url.path.endswith("/search"):
        return httpx.Response(
            200,
            json={
                "total": 1,
                "issues": [
                    {
                        "key": "QA-1",
                        "id": "1",
                        "fields": {
                            "summary": "Login",
                            "status": {"name": "To Do"},
                            "issuetype": {"name": "Test"},
                            "labels": ["smoke"],
                            "components": [{"name": "auth"}],
                        },
                    }
                ],
            },
        )
    if request.url.path.endswith("/issue") and request.method == "POST":
        return httpx.Response(201, json={"key": "QA-42", "id": "42"})
    return httpx.Response(404, json={"errorMessages": ["not found"]})


class TestConfigurationValidation:
    """A wrong configuration must fail loudly at startup."""

    def test_offline_is_the_default(self, monkeypatch):
        for key in TENANT:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv("QA_MCP_ENABLE_WRITE_TOOLS", raising=False)

        settings = Settings()
        assert settings.xray.enabled is False
        assert settings.xray.is_configured is False
        assert settings.enable_write_tools is False

    def test_enabled_without_a_token_is_rejected(self, monkeypatch):
        monkeypatch.setenv("QA_MCP_XRAY_ENABLED", "true")
        monkeypatch.setenv("QA_MCP_XRAY_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.delenv("QA_MCP_XRAY_API_TOKEN", raising=False)

        with pytest.raises(ValueError, match="QA_MCP_XRAY_API_TOKEN"):
            XraySettings()

    def test_basic_auth_without_an_email_is_rejected(self, monkeypatch):
        monkeypatch.setenv("QA_MCP_XRAY_ENABLED", "true")
        monkeypatch.setenv("QA_MCP_XRAY_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("QA_MCP_XRAY_API_TOKEN", "t")
        monkeypatch.setenv("QA_MCP_XRAY_AUTH_MODE", "basic")
        monkeypatch.delenv("QA_MCP_XRAY_EMAIL", raising=False)

        with pytest.raises(ValueError, match="QA_MCP_XRAY_EMAIL"):
            XraySettings()

    def test_write_tools_without_a_tenant_are_rejected(self, monkeypatch):
        """Promising writes with nowhere to write them is a misconfiguration."""
        for key in TENANT:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("QA_MCP_ENABLE_WRITE_TOOLS", "true")

        with pytest.raises(ValueError, match="no Xray tenant is configured"):
            Settings()

    def test_base_url_trailing_slash_is_normalized(self, tenant_env):
        assert Settings().xray.base_url == "https://acme.atlassian.net"

    def test_raising_the_base_threshold_carries_strict_along(self, monkeypatch):
        """Only the base gate is usually set; strict must not end up looser."""
        monkeypatch.setenv("QA_MCP_LINT_MINIMUM_SCORE", "90")
        monkeypatch.delenv("QA_MCP_LINT_STRICT_MINIMUM_SCORE", raising=False)

        settings = LintSettings()
        assert settings.minimum_score == 90
        assert settings.strict_minimum_score == 90

    def test_two_contradictory_thresholds_are_rejected(self, monkeypatch):
        monkeypatch.setenv("QA_MCP_LINT_MINIMUM_SCORE", "90")
        monkeypatch.setenv("QA_MCP_LINT_STRICT_MINIMUM_SCORE", "50")

        with pytest.raises(ValueError, match="cannot be looser"):
            LintSettings()


class TestCredentialHandling:
    """Tokens must not reach a log, a repr or a result."""

    def test_describe_redacts_the_token(self, tenant_env):
        described = json.dumps(Settings().describe())
        assert "SECRET-TOKEN-VALUE" not in described
        assert '"credentials": "set"' in described

    def test_repr_redacts_the_token(self, tenant_env):
        assert "SECRET-TOKEN-VALUE" not in repr(Settings())

    def test_the_token_is_still_usable(self, tenant_env):
        token = Settings().xray.api_token
        assert token is not None
        assert token.get_secret_value() == "SECRET-TOKEN-VALUE"

    def test_error_details_do_not_carry_the_token(self, tenant_env):
        settings = Settings()
        with (
            XrayClient(settings, transport=_mock_transport(_ok_handler)) as client,
            pytest.raises(XrayError) as excinfo,
        ):
            client.get_test("QA-404")

        assert "SECRET-TOKEN-VALUE" not in json.dumps(excinfo.value.to_dict())


class TestXrayClient:
    def test_basic_auth_header(self, tenant_env):
        seen: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["authorization"] = request.headers["authorization"]
            return _ok_handler(request)

        with XrayClient(Settings(), transport=_mock_transport(handler)) as client:
            client.verify_connection()

        expected = base64.b64encode(b"qa@acme.com:SECRET-TOKEN-VALUE").decode()
        assert seen["authorization"] == f"Basic {expected}"

    def test_bearer_auth_header(self, tenant_env, monkeypatch):
        monkeypatch.setenv("QA_MCP_XRAY_AUTH_MODE", "token")
        seen: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["authorization"] = request.headers["authorization"]
            return _ok_handler(request)

        with XrayClient(Settings(), transport=_mock_transport(handler)) as client:
            client.verify_connection()

        assert seen["authorization"] == "Bearer SECRET-TOKEN-VALUE"

    def test_verify_connection_reports_the_account(self, tenant_env):
        with XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client:
            status = client.verify_connection()

        assert status["connected"] is True
        assert status["account"]["display_name"] == "QA Bot"
        assert status["write_tools_enabled"] is False

    def test_search_defaults_to_the_configured_project(self, tenant_env):
        with XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client:
            result = client.search_tests()

        assert 'project = "QA"' in result["jql"]
        assert result["tests"][0]["issue_key"] == "QA-1"

    def test_issue_summaries_drop_unrelated_tenant_detail(self, tenant_env):
        """Jira issues are large; only the reported fields should come back."""
        with XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client:
            test = client.search_tests()["tests"][0]

        assert set(test) == {
            "issue_key",
            "issue_id",
            "summary",
            "status",
            "priority",
            "issue_type",
            "labels",
            "components",
        }

    def test_unconfigured_client_refuses_to_build(self, monkeypatch):
        for key in TENANT:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(XrayError, match="yapılandırılmamış"):
            XrayClient(Settings())

    def test_http_error_carries_an_actionable_hint(self, tenant_env):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"errorMessages": ["Unauthorized"]})

        with (
            XrayClient(Settings(), transport=_mock_transport(handler)) as client,
            pytest.raises(XrayError) as excinfo,
        ):
            client.verify_connection()

        assert excinfo.value.status_code == 401
        assert "QA_MCP_XRAY_AUTH_MODE" in str(excinfo.value)


class TestWriteGating:
    """Nothing may be created in someone's Jira by accident."""

    def test_create_is_refused_when_writes_are_off(self, tenant_env):
        with (
            XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client,
            pytest.raises(XrayError, match="QA_MCP_ENABLE_WRITE_TOOLS"),
        ):
            client.create_test({"fields": {"summary": "x"}})

    def test_create_succeeds_when_writes_are_on(self, tenant_env, monkeypatch):
        monkeypatch.setenv("QA_MCP_ENABLE_WRITE_TOOLS", "true")

        with XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client:
            created = client.create_test({"fields": {"summary": "Login test"}})

        assert created["issue_key"] == "QA-42"
        assert created["url"] == "https://acme.atlassian.net/browse/QA-42"

    def test_create_falls_back_to_the_configured_project(self, tenant_env, monkeypatch):
        monkeypatch.setenv("QA_MCP_ENABLE_WRITE_TOOLS", "true")
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path.endswith("/issue"):
                seen.update(json.loads(request.content))
            return _ok_handler(request)

        with XrayClient(Settings(), transport=_mock_transport(handler)) as client:
            client.create_test({"fields": {"summary": "Login test"}})

        assert seen["fields"]["project"] == {"key": "QA"}

    def test_payload_without_fields_is_rejected(self, tenant_env, monkeypatch):
        monkeypatch.setenv("QA_MCP_ENABLE_WRITE_TOOLS", "true")

        with (
            XrayClient(Settings(), transport=_mock_transport(_ok_handler)) as client,
            pytest.raises(XrayError, match="testcase_to_xray"),
        ):
            client.create_test({"not_fields": {}})


class TestConditionalToolRegistration:
    """What the server exposes follows the configuration."""

    def test_no_xray_tools_without_a_tenant(self, monkeypatch):
        from qa_mcp.server import register_optional_tools

        for key in TENANT:
            monkeypatch.delenv(key, raising=False)
        assert register_optional_tools(Settings()) == []

    def test_read_tools_appear_with_a_tenant(self, tenant_env):
        from qa_mcp.server import register_optional_tools

        registered = register_optional_tools(Settings())
        assert "xray_verify_connection" in registered
        assert "xray_search_tests" in registered
        assert "xray_create_test" not in registered

    def test_the_write_tool_needs_writes_enabled(self, tenant_env, monkeypatch):
        from qa_mcp.server import register_optional_tools

        monkeypatch.setenv("QA_MCP_ENABLE_WRITE_TOOLS", "true")
        assert "xray_create_test" in register_optional_tools(Settings())

    def test_legacy_aliases_are_opt_in(self, monkeypatch):
        from qa_mcp.server import register_optional_tools

        for key in TENANT:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("QA_MCP_LEGACY_TOOL_ALIASES", "true")

        registered = register_optional_tools(Settings())
        assert "testcase.lint" in registered


class TestLegacyEnvironmentNames:
    """QA-MCP 1.x used unprefixed variable names."""

    @pytest.mark.parametrize(
        ("legacy", "value", "attribute", "expected"),
        [
            ("LOG_LEVEL", "debug", "log_level", "DEBUG"),
            ("AUDIT_LOG_ENABLED", "false", "audit_log_enabled", False),
        ],
    )
    def test_legacy_name_is_still_honoured(self, monkeypatch, legacy, value, attribute, expected):
        """Silently ignoring an existing docker-compose would be a nasty upgrade."""
        monkeypatch.delenv(f"QA_MCP_{legacy}", raising=False)
        monkeypatch.setenv(legacy, value)

        assert getattr(Settings(), attribute) == expected

    def test_the_prefixed_name_wins(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("QA_MCP_LOG_LEVEL", "error")

        assert Settings().log_level == "ERROR"
