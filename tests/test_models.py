"""Tests for core data models."""

from datetime import datetime

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
