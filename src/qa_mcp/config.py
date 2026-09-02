"""
Runtime configuration.

Everything an organisation needs to change in order to run QA-MCP against its
own Jira/Xray tenant and its own QA standard is settable from the environment.
Nothing here is read at import time by the tools themselves: they take a
``Settings`` instance, so tests and multi-tenant callers can build their own.

Precedence is the usual pydantic-settings order: explicit constructor argument,
then environment variable, then ``.env``, then the default below.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
AuthMode = Literal["none", "token", "basic"]


class XraySettings(BaseSettings):
    """Connection details for a Jira/Xray tenant.

    Credentials are ``SecretStr`` so they do not leak into logs, tracebacks or
    ``model_dump()`` output. Nothing connects anywhere unless ``enabled`` is
    true and the connection actually validates.
    """

    model_config = SettingsConfigDict(
        env_prefix="QA_MCP_XRAY_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(
        False,
        description="Allow QA-MCP to contact Jira/Xray. Off by default.",
    )
    base_url: str | None = Field(
        None,
        description="Jira base URL, e.g. https://acme.atlassian.net",
    )
    auth_mode: AuthMode = Field(
        "token",
        description="'token' for a bearer/PAT, 'basic' for email + API token",
    )
    email: str | None = Field(
        None,
        description="Account email; required for Jira Cloud basic auth",
    )
    api_token: SecretStr | None = Field(
        None,
        description="API token or personal access token",
    )
    project_key: str | None = Field(
        None,
        description="Default Jira project key, e.g. QA",
    )
    test_issue_type: str = Field("Test", description="Issue type used for Xray tests")
    api_version: Literal["2", "3"] = Field(
        "3",
        description="Jira REST API version: '3' for Cloud, '2' for Server/Data Center",
    )
    timeout_seconds: float = Field(30.0, gt=0, le=300)
    verify_tls: bool = Field(True, description="Disable only for an internal CA in testing")
    max_retries: int = Field(2, ge=0, le=10)

    # Xray custom field ids differ per tenant, so they cannot be hardcoded.
    # Supplied as QA_MCP_XRAY_CUSTOM_FIELDS='{"risk_level": "customfield_10001"}'
    custom_fields: dict[str, str] = Field(
        default_factory=dict,
        description="QA-MCP field name -> Jira custom field id",
    )

    @field_validator("base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str | None) -> str | None:
        return value.rstrip("/") if value else value

    @model_validator(mode="after")
    def _check_credentials(self) -> XraySettings:
        """A tenant that is switched on must be fully specified.

        Failing here, at startup, is far kinder than failing on the first tool
        call with a 401 the user has to decode.
        """
        if not self.enabled:
            return self

        missing: list[str] = []
        if not self.base_url:
            missing.append("QA_MCP_XRAY_BASE_URL")
        if not self.api_token:
            missing.append("QA_MCP_XRAY_API_TOKEN")
        if self.auth_mode == "basic" and not self.email:
            missing.append("QA_MCP_XRAY_EMAIL")

        if missing:
            raise ValueError(
                "QA_MCP_XRAY_ENABLED is true but "
                f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not set. "
                "Set them, or leave QA_MCP_XRAY_ENABLED unset to run QA-MCP offline."
            )
        return self

    @property
    def is_configured(self) -> bool:
        """True when the tenant is switched on and usable."""
        return bool(self.enabled and self.base_url and self.api_token)


class LintSettings(BaseSettings):
    """Thresholds an organisation may want to hold itself to.

    The defaults reproduce the shipped QA-MCP standard; raising
    ``minimum_score`` is how a team tightens its own quality gate.
    """

    model_config = SettingsConfigDict(
        env_prefix="QA_MCP_LINT_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    minimum_score: int = Field(60, ge=0, le=100, description="Score required to pass")
    strict_minimum_score: int = Field(
        75, ge=0, le=100, description="Score required to pass in strict mode"
    )
    max_steps: int = Field(15, ge=1, le=100, description="Steps beyond which a case is flagged")
    disabled_rules: set[str] = Field(
        default_factory=set,
        description="Rule ids to skip, e.g. QA_MCP_LINT_DISABLED_RULES='[\"tags.recommended\"]'",
    )

    @model_validator(mode="after")
    def _strict_is_not_looser(self) -> LintSettings:
        """Strict mode must be at least as strict as the normal gate.

        Raising only the base threshold is the common case and should just
        work, so an unset strict threshold follows it up. Two thresholds that
        were both set and still contradict each other is a real mistake.
        """
        if self.strict_minimum_score >= self.minimum_score:
            return self

        if "strict_minimum_score" not in self.model_fields_set:
            self.strict_minimum_score = self.minimum_score
            return self

        raise ValueError(
            f"QA_MCP_LINT_STRICT_MINIMUM_SCORE ({self.strict_minimum_score}) is below "
            f"QA_MCP_LINT_MINIMUM_SCORE ({self.minimum_score}); strict mode cannot be looser"
        )


class Settings(BaseSettings):
    """Top-level runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="QA_MCP_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # The unprefixed spellings are what QA-MCP 1.x read. Accepting them keeps an
    # existing docker-compose or Claude Desktop config working instead of
    # silently ignoring it; the prefixed names are the documented ones.
    log_level: LogLevel = Field(
        "INFO",
        validation_alias=AliasChoices("QA_MCP_LOG_LEVEL", "LOG_LEVEL"),
    )
    audit_log_enabled: bool = Field(
        True,
        description="Log every tool invocation",
        validation_alias=AliasChoices("QA_MCP_AUDIT_LOG_ENABLED", "AUDIT_LOG_ENABLED"),
    )

    enable_write_tools: bool = Field(
        False,
        description=(
            "Expose tools that create or modify issues in Jira/Xray. "
            "Requires a configured Xray tenant."
        ),
        validation_alias=AliasChoices("QA_MCP_ENABLE_WRITE_TOOLS", "ENABLE_WRITE_TOOLS"),
    )

    legacy_tool_aliases: bool = Field(
        False,
        description=(
            "Also publish the pre-1.0.3 dotted tool names (testcase.lint, ...). "
            "Off by default; they double the tool list."
        ),
    )

    lint: LintSettings = Field(default_factory=LintSettings)
    xray: XraySettings = Field(default_factory=XraySettings)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _write_tools_need_a_tenant(self) -> Settings:
        """Refuse a configuration that promises writes it cannot perform."""
        if self.enable_write_tools and not self.xray.is_configured:
            raise ValueError(
                "QA_MCP_ENABLE_WRITE_TOOLS is true but no Xray tenant is configured. "
                "Set QA_MCP_XRAY_ENABLED=true along with QA_MCP_XRAY_BASE_URL and "
                "QA_MCP_XRAY_API_TOKEN, or turn write tools off."
            )
        return self

    def describe(self) -> dict[str, Any]:
        """A redacted summary, safe to log at startup."""
        return {
            "log_level": self.log_level,
            "audit_log_enabled": self.audit_log_enabled,
            "write_tools_enabled": self.enable_write_tools,
            "legacy_tool_aliases": self.legacy_tool_aliases,
            "lint": {
                "minimum_score": self.lint.minimum_score,
                "strict_minimum_score": self.lint.strict_minimum_score,
                "max_steps": self.lint.max_steps,
                "disabled_rules": sorted(self.lint.disabled_rules),
            },
            "xray": {
                "enabled": self.xray.enabled,
                "configured": self.xray.is_configured,
                "base_url": self.xray.base_url,
                "auth_mode": self.xray.auth_mode,
                "project_key": self.xray.project_key,
                "api_version": self.xray.api_version,
                "custom_fields": sorted(self.xray.custom_fields),
                # Deliberately never the token itself.
                "credentials": "set" if self.xray.api_token else "unset",
            },
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide settings, read once."""
    return Settings()


def reload_settings() -> Settings:
    """Re-read the environment. Intended for tests and for `.env` reloads."""
    get_settings.cache_clear()
    return get_settings()
