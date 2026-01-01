"""
Test Case data models and enums.

This module defines the standard test case structure used throughout QA-MCP.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification for test cases."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    """Test case priority."""

    P0 = "P0"  # Critical - Must run every build
    P1 = "P1"  # High - Must run every release
    P2 = "P2"  # Medium - Run in regression
    P3 = "P3"  # Low - Run occasionally


class TestType(str, Enum):
    """Type of test case."""

    MANUAL = "Manual"
    AUTOMATED = "Automated"
    GENERIC = "Generic"


class SuiteType(str, Enum):
    """Type of test suite."""

    SMOKE = "smoke"
    SANITY = "sanity"
    REGRESSION = "regression"
    E2E = "e2e"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"


class ScenarioType(str, Enum):
    """Type of test scenario."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    EDGE_CASE = "edge_case"
    ERROR_HANDLING = "error_handling"


class TestData(BaseModel):
    """Test data definition."""

    name: str = Field(..., description="Data variable name")
    value: Any = Field(..., description="Test data value")
    description: str | None = Field(None, description="Description of this data point")
    is_boundary: bool = Field(False, description="Is this a boundary value?")
    is_negative: bool = Field(False, description="Is this negative test data?")


class TestStep(BaseModel):
    """Individual test step."""

    step_number: int = Field(..., ge=1, description="Step sequence number")
    action: str = Field(..., min_length=5, description="Action to perform")
    expected_result: str = Field(..., min_length=5, description="Expected result")
    test_data: list[TestData] | None = Field(None, description="Data used in this step")
    notes: str | None = Field(None, description="Additional notes")


class TestCase(BaseModel):
    """
    Standard test case structure.

    This is the core data model that all QA-MCP tools work with.
    """

    # Identification
    id: str | None = Field(None, description="Unique identifier")
    title: str = Field(..., min_length=10, max_length=200, description="Test case title")
    description: str = Field(..., min_length=20, description="Detailed description")

    # Classification
    module: str | None = Field(None, description="Module/component being tested")
    feature: str | None = Field(None, description="Feature being tested")
    scenario_type: ScenarioType = Field(ScenarioType.POSITIVE, description="Type of scenario")
    risk_level: RiskLevel = Field(RiskLevel.MEDIUM, description="Risk level")
    priority: Priority = Field(Priority.P2, description="Test priority")
    test_type: TestType = Field(TestType.MANUAL, description="Manual/Automated/Generic")

    # Prerequisites
    preconditions: list[str] = Field(
        default_factory=list, description="Conditions that must be true before test execution"
    )

    # Test execution
    steps: list[TestStep] = Field(
        default_factory=list, min_length=1, description="Test steps to execute"
    )

    # Test data
    test_data: list[TestData] = Field(
        default_factory=list, description="Test data required for execution"
    )

    # Expected outcomes
    expected_result: str = Field(..., min_length=10, description="Overall expected result")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    labels: list[str] = Field(default_factory=list, description="Labels (smoke, regression, etc.)")
    estimated_duration_minutes: int | None = Field(
        None, ge=1, le=480, description="Estimated execution time"
    )

    # Traceability
    requirements: list[str] = Field(default_factory=list, description="Linked requirement IDs")
    related_testcases: list[str] = Field(default_factory=list, description="Related test case IDs")

    # Audit
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    author: str | None = Field(None, description="Test case author")

    def model_post_init(self, __context: Any) -> None:
        """Set timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = self.created_at


class LintSeverity(str, Enum):
    """Severity level for lint issues."""

    ERROR = "error"  # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"  # Nice to have


class LintIssue(BaseModel):
    """Individual lint issue."""

    severity: LintSeverity = Field(..., description="Issue severity")
    field: str = Field(..., description="Field with the issue")
    rule: str = Field(..., description="Lint rule that triggered this")
    message: str = Field(..., description="Human-readable message")
    suggestion: str | None = Field(None, description="How to fix this issue")


class LintResult(BaseModel):
    """Result of linting a test case."""

    score: int = Field(..., ge=0, le=100, description="Quality score (0-100)")
    grade: str = Field(..., description="Letter grade (A-F)")
    issues: list[LintIssue] = Field(default_factory=list, description="Found issues")
    suggestions: list[str] = Field(default_factory=list, description="General suggestions")
    passed: bool = Field(..., description="Did it pass minimum quality threshold?")

    @classmethod
    def calculate_grade(cls, score: int) -> str:
        """Calculate letter grade from score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class XrayTestCase(BaseModel):
    """Xray-compatible test case format."""

    testtype: str = Field("Manual", description="Test type")
    summary: str = Field(..., description="Test summary/title")
    preconditions: str | None = Field(None, description="Preconditions text")
    steps: list[dict[str, str]] = Field(default_factory=list, description="Test steps")
    labels: list[str] = Field(default_factory=list, description="Jira labels")
    priority: str | None = Field(None, description="Jira priority")
    components: list[str] = Field(default_factory=list, description="Jira components")
    custom_fields: dict[str, Any] = Field(default_factory=dict, description="Custom fields")


class SuiteComposition(BaseModel):
    """Result of suite composition."""

    suite_type: SuiteType = Field(..., description="Type of suite")
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    testcases: list[str] = Field(default_factory=list, description="Included test case IDs")
    total_duration_minutes: int = Field(0, description="Estimated total duration")
    coverage_summary: dict[str, Any] = Field(default_factory=dict, description="Coverage info")
    rationale: str = Field(..., description="Why these tests were selected")
