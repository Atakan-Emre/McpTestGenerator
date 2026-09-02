"""Tests for core data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from qa_mcp.core.models import (
    LintResult,
    Priority,
    RiskLevel,
    ScenarioType,
)
from qa_mcp.core.models import (
    TestCase as QaTestCase,
)
from qa_mcp.core.models import (
    TestCaseDraft as QaTestCaseDraft,
)
from qa_mcp.core.models import (
    TestData as QaTestData,
)
from qa_mcp.core.models import (
    TestStep as QaTestStep,
)


class TestTestCaseModel:
    """Test TestCase model validation and behavior."""

    def test_valid_testcase_creation(self):
        """Test creating a valid test case."""
        tc = QaTestCase(
            title="Valid Test Case Title",
            description="This is a valid test case description with enough detail.",
            preconditions=["User is logged in"],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Click the button",
                    expected_result="Button changes state",
                )
            ],
            expected_result="Test completes successfully",
        )
        assert tc.title == "Valid Test Case Title"
        assert tc.risk_level == RiskLevel.MEDIUM  # Default
        assert tc.priority == Priority.P2  # Default

    def test_testcase_with_all_fields(self):
        """Test creating a test case with all optional fields."""
        tc = QaTestCase(
            id="TC-001",
            title="Complete Test Case",
            description="A test case with all fields populated",
            module="auth",
            feature="login",
            scenario_type=ScenarioType.POSITIVE,
            risk_level=RiskLevel.HIGH,
            priority=Priority.P0,
            preconditions=["System is running", "User exists"],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Navigate to login page",
                    expected_result="Login form is displayed",
                )
            ],
            test_data=[
                QaTestData(name="username", value="testuser"),
                QaTestData(name="password", value="secret", is_boundary=False),
            ],
            expected_result="User is logged in successfully",
            tags=["auth", "login"],
            labels=["smoke", "regression"],
            estimated_duration_minutes=5,
            requirements=["REQ-001"],
            author="Test Author",
        )
        assert tc.id == "TC-001"
        assert tc.module == "auth"
        assert len(tc.test_data) == 2
        assert tc.estimated_duration_minutes == 5

    def test_testcase_auto_timestamps(self):
        """Test that timestamps are auto-generated."""
        tc = QaTestCase(
            title="Test with timestamps generated automatically",
            description="Testing that timestamp fields are generated automatically",
            preconditions=["System is ready"],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Perform action here",
                    expected_result="Result is observed",
                )
            ],
            expected_result="Test completes with timestamps set",
        )
        assert tc.created_at is not None
        assert tc.updated_at is not None
        assert isinstance(tc.created_at, datetime)


class TestTestStepModel:
    """Test TestStep model."""

    def test_valid_step(self):
        """Test creating a valid step."""
        step = QaTestStep(
            step_number=1,
            action="Click the submit button",
            expected_result="Form is submitted successfully",
        )
        assert step.step_number == 1

    def test_step_with_test_data(self):
        """Test step with embedded test data."""
        step = QaTestStep(
            step_number=1,
            action="Enter username",
            expected_result="Username accepted",
            test_data=[QaTestData(name="username", value="test@example.com")],
            notes="Use valid email format",
        )
        assert len(step.test_data) == 1
        assert step.notes == "Use valid email format"


class TestLintResultModel:
    """Test LintResult model."""

    def test_grade_calculation(self):
        """Test grade calculation from score."""
        assert LintResult.calculate_grade(95) == "A"
        assert LintResult.calculate_grade(85) == "B"
        assert LintResult.calculate_grade(75) == "C"
        assert LintResult.calculate_grade(65) == "D"
        assert LintResult.calculate_grade(50) == "F"

    def test_lint_result_creation(self):
        """Test creating a lint result."""
        result = LintResult(
            score=85,
            grade="B",
            issues=[],
            suggestions=["Add more test data"],
            passed=True,
        )
        assert result.score == 85
        assert result.passed is True


class TestTestCaseDraft:
    """The permissive model the lint engine reads."""

    def test_draft_accepts_a_testcase_that_violates_the_standard(self):
        """Regression: substandard input must be representable, so it can be linted."""
        draft = QaTestCaseDraft(
            title="Login test",
            description="Login test",
            preconditions=[],
            steps=[{"step_number": 1, "action": "Login yap", "expected_result": "Çalışır"}],
            expected_result="OK",
        )
        assert draft.title == "Login test"
        assert draft.steps[0].action == "Login yap"

    def test_draft_defaults_are_empty_not_missing(self):
        draft = QaTestCaseDraft()
        assert draft.title == ""
        assert draft.description == ""
        assert draft.steps == []
        assert draft.expected_result == ""

    def test_strict_testcase_still_enforces_the_standard(self):
        with pytest.raises(ValidationError):
            QaTestCase(
                title="Login test",
                description="Login test",
                steps=[],
                expected_result="OK",
            )

    def test_testcase_is_a_draft(self):
        """LintEngine takes a draft; a strict TestCase must satisfy that contract."""
        assert issubclass(QaTestCase, QaTestCaseDraft)


class TestPackagingConstraints:
    """Guards on dependency metadata."""

    def test_mcp_dependency_has_an_upper_bound(self):
        """Regression: an unbounded `mcp>=1.0.0` let mcp 2.x break the server on install.

        mcp 2.x removed the decorator-based low-level API 1.x code was built on
        and renamed FastMCP to MCPServer, so a fresh install resolved to a
        version that crashed at import. The specific ceiling will move; that
        there is one must not.
        """
        from importlib.metadata import requires

        mcp_requirements = [r for r in (requires("qa-mcp") or []) if r.startswith("mcp")]
        assert mcp_requirements, "qa-mcp no longer declares an mcp dependency"
        assert any("<" in r for r in mcp_requirements), (
            f"mcp dependency must declare an upper bound: {mcp_requirements}"
        )

    def test_mcp_upper_bound_matches_the_installed_major(self):
        """The pin must admit the version actually being tested against."""
        from importlib.metadata import version

        installed_major = int(version("mcp").split(".")[0])
        assert installed_major == 2, (
            f"tests run against mcp {installed_major}.x; update the pin and this guard together"
        )
