"""
Typed tool results.

These models are the published contract of every QA-MCP tool. The MCP runtime
derives each tool's ``outputSchema`` from them and validates the structured
content it returns, so a change here is a change to the public API.

The tool implementations in ``qa_mcp.tools`` stay dict-based and free of MCP
imports; the dicts are validated into these models at the server boundary.

Every model allows extra keys. A tool may add a field without breaking a client
that has not been updated, and error-shaped results (which carry an extra
``error``) validate against the same model as successful ones.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Result(BaseModel):
    """Base for every tool result: open to extension, forbidding nothing."""

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# testcase_generate
# ---------------------------------------------------------------------------


class CoverageSummary(_Result):
    positive_scenarios: int = Field(description="Number of positive scenarios generated")
    negative_scenarios: int = Field(description="Number of negative scenarios generated")
    boundary_tests: int = Field(description="Number of boundary test suggestions")
    acceptance_criteria_covered: list[str] = Field(description="Acceptance criteria ids covered")


class GenerateResult(_Result):
    testcases: list[dict[str, Any]] = Field(description="Generated standard test cases")
    suggestions: list[str] = Field(description="Additional testing suggestions")
    coverage_summary: CoverageSummary
    total_generated: int = Field(description="Number of test cases generated")


# ---------------------------------------------------------------------------
# testcase_lint / testcase_lint_batch
# ---------------------------------------------------------------------------


class LintIssue(_Result):
    severity: Literal["error", "warning", "info"]
    field: str = Field(description="Field the issue concerns")
    rule: str = Field(description="Lint rule id")
    message: str
    suggestion: str | None = None


class LintSummary(_Result):
    total_issues: int
    errors: int
    warnings: int
    info: int
    minimum_score: int = Field(description="Score required to pass")


class LintResult(_Result):
    score: int = Field(ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]
    passed: bool = Field(description="Met the minimum quality threshold")
    schema_valid: bool = Field(description="Conforms to the QA-MCP standard's schema constraints")
    schema_errors: list[str] = Field(default_factory=list)
    issues: list[LintIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    improvement_plan: list[dict[str, Any]] | None = None
    summary: LintSummary | None = None


class CommonIssue(_Result):
    rule: str
    count: int


class LintAggregate(_Result):
    total_testcases: int
    average_score: float
    pass_rate: float
    passed_count: int
    failed_count: int
    total_issues: int
    common_issues: list[CommonIssue] = Field(default_factory=list)


class LintBatchResult(_Result):
    results: list[LintResult]
    aggregate: LintAggregate
    recommendations: list[str] = Field(default_factory=list)
    grade_distribution: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# testcase_normalize
# ---------------------------------------------------------------------------


class NormalizeResult(_Result):
    testcase: dict[str, Any] | None = Field(
        description="Test case raised to the standard; null when it could not be parsed"
    )
    source_format_detected: Literal["markdown", "gherkin", "json", "plain"]
    transformations: list[str] = Field(description="Transformations applied")
    warnings: list[str] = Field(description="Fields that were padded or changed")


# ---------------------------------------------------------------------------
# testcase_to_xray / testcase_to_xray_batch
# ---------------------------------------------------------------------------


class FieldMappingReport(_Result):
    mapped_fields: list[str] = Field(
        default_factory=list, description="Written to first-class Xray fields"
    )
    embedded_in_description: list[str] = Field(
        default_factory=list,
        description="No Xray equivalent, rendered into the description body",
    )
    unmapped_fields: list[str] = Field(
        default_factory=list, description="Genuinely could not be carried over"
    )
    custom_fields_used: list[str] = Field(default_factory=list)


class XrayConversionResult(_Result):
    xray_payload: dict[str, Any] | None = Field(description="Import-ready Xray JSON")
    field_mapping_report: FieldMappingReport
    warnings: list[str] = Field(default_factory=list)


class XrayBatchSummary(_Result):
    total: int
    successful: int
    failed: int


class XrayBatchResult(_Result):
    xray_payloads: list[dict[str, Any]] = Field(default_factory=list)
    import_payload: dict[str, Any]
    summary: XrayBatchSummary
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# suite_compose / suite_coverage_report
# ---------------------------------------------------------------------------


class SuiteCompositionResult(_Result):
    suite: dict[str, Any] | None = Field(description="Composed suite; null on error")
    selected_testcases: list[dict[str, Any]] = Field(default_factory=list)
    excluded_count: int = 0
    selection_rationale: list[dict[str, Any]] = Field(
        default_factory=list, description="Why each test case was included or excluded"
    )
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    duration_warning: bool = False
    errors: list[str] | None = None


class CoverageReportResult(_Result):
    total_testcases: int
    skipped_testcases: list[dict[str, str]] = Field(
        default_factory=list, description="Inputs that did not conform and were left out"
    )
    requirement_coverage: dict[str, Any] | None = None
    requirement_mapping: dict[str, Any] = Field(default_factory=dict)
    module_coverage: dict[str, Any] | None = None
    module_test_count: dict[str, int] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    scenario_distribution: dict[str, int] = Field(default_factory=dict)
    gaps: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# xray_get_mapping_template
# ---------------------------------------------------------------------------


class XrayMappingTemplate(_Result):
    standard_mappings: dict[str, Any]
    custom_field_suggestions: dict[str, Any]
    xray_specific: dict[str, Any]
    notes: list[str]


# ---------------------------------------------------------------------------
# Jira/Xray integration (only registered when a tenant is configured)
# ---------------------------------------------------------------------------


class XrayAccount(_Result):
    display_name: str | None = None
    email: str | None = None
    account_id: str | None = None
    active: bool | None = None


class XrayConnectionStatus(_Result):
    connected: bool
    base_url: str | None = None
    api_version: str | None = None
    auth_mode: str | None = None
    account: XrayAccount
    write_tools_enabled: bool


class XrayTestSummary(_Result):
    issue_key: str | None = None
    issue_id: str | None = None
    summary: str | None = None
    status: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)


class XraySearchResult(_Result):
    jql: str
    total: int
    returned: int
    tests: list[XrayTestSummary] = Field(default_factory=list)


class XrayCreateResult(_Result):
    created: bool
    issue_key: str | None = None
    issue_id: str | None = None
    url: str | None = None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RESULT_MODELS: dict[str, type[_Result]] = {
    "testcase_generate": GenerateResult,
    "testcase_lint": LintResult,
    "testcase_lint_batch": LintBatchResult,
    "testcase_normalize": NormalizeResult,
    "testcase_to_xray": XrayConversionResult,
    "testcase_to_xray_batch": XrayBatchResult,
    "suite_compose": SuiteCompositionResult,
    "suite_coverage_report": CoverageReportResult,
    "xray_get_mapping_template": XrayMappingTemplate,
    "xray_verify_connection": XrayConnectionStatus,
    "xray_get_test": XrayTestSummary,
    "xray_search_tests": XraySearchResult,
    "xray_create_test": XrayCreateResult,
}
