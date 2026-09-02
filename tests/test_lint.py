"""Tests for lint engine."""

import pytest

from qa_mcp.core.lint import LintEngine
from qa_mcp.core.models import LintSeverity, Priority, RiskLevel
from qa_mcp.core.models import TestCase as QaTestCase
from qa_mcp.core.models import TestData as QaTestData
from qa_mcp.core.models import TestStep as QaTestStep


class TestLintEngine:
    """Test cases for the lint engine."""

    @pytest.fixture
    def lint_engine(self):
        """Create a lint engine instance."""
        return LintEngine()

    @pytest.fixture
    def good_testcase(self):
        """Create a well-formed test case."""
        return QaTestCase(
            title="User Login - Valid credentials authentication",
            description="This test verifies that users can log in with valid email and password credentials.",
            module="auth",
            risk_level=RiskLevel.HIGH,
            priority=Priority.P1,
            preconditions=[
                "User is registered with email test@example.com",
                "User account is active",
            ],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Navigate to the login page at /login",
                    expected_result="Login form is displayed with email and password fields",
                ),
                QaTestStep(
                    step_number=2,
                    action="Enter valid email address test@example.com",
                    expected_result="Email is accepted without validation errors",
                ),
                QaTestStep(
                    step_number=3,
                    action="Enter valid password and click Login button",
                    expected_result="User is redirected to dashboard page",
                ),
            ],
            expected_result="User successfully logs in and sees the dashboard with welcome message",
            tags=["auth", "login"],
            requirements=["REQ-AUTH-001"],
        )

    @pytest.fixture
    def bad_testcase(self):
        """Create a poorly-formed test case (passes validation but has quality issues)."""
        return QaTestCase(
            title="Login test case",  # Generic title
            description="This is a login test case",  # Duplicate of title essentially
            preconditions=[],  # Missing preconditions
            steps=[
                QaTestStep(
                    step_number=1, action="Login to system", expected_result="It works correctly"
                ),  # Vague
            ],
            expected_result="Everything works fine",  # Vague
        )

    def test_lint_good_testcase(self, lint_engine, good_testcase):
        """Test linting a well-formed test case."""
        result = lint_engine.lint(good_testcase)
        assert result.score >= 80
        assert result.passed is True
        assert result.grade in ["A", "B"]

    def test_lint_bad_testcase(self, lint_engine, bad_testcase):
        """Test linting a poorly-formed test case (has issues but may still pass)."""
        result = lint_engine.lint(bad_testcase)
        # Bad testcase should have multiple issues
        assert len(result.issues) > 0
        # Should have lower score than good testcase (which scores 80+)
        assert result.score < 90
        # Should have suggestions for improvement
        assert len(result.suggestions) > 0 or len(result.issues) > 0

    def test_lint_missing_preconditions(self, lint_engine):
        """Test that missing preconditions are flagged."""
        tc = QaTestCase(
            title="Test without preconditions defined",
            description="This test has no preconditions which is an issue.",
            preconditions=[],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Do something specific here",
                    expected_result="Something happens as expected",
                )
            ],
            expected_result="Test completes without any issues",
        )
        result = lint_engine.lint(tc)
        precondition_issues = [i for i in result.issues if "preconditions" in i.field]
        assert len(precondition_issues) > 0

    def test_lint_generic_title(self, lint_engine):
        """Test that generic titles are flagged."""
        tc = QaTestCase(
            title="Test the login functionality",  # Starts with "Test"
            description="This is a proper description with enough detail about the test.",
            preconditions=["System is ready for testing"],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Perform the test action here",
                    expected_result="Expected result is observed correctly",
                )
            ],
            expected_result="Test completes successfully as expected",
        )
        result = lint_engine.lint(tc)
        # Should have warning about generic title starting with "Test"
        title_issues = [i for i in result.issues if "title" in i.field]
        assert len(title_issues) > 0 or len(result.suggestions) > 0

    def test_improvement_plan_generation(self, lint_engine, bad_testcase):
        """Test that improvement plan is generated correctly."""
        result = lint_engine.lint(bad_testcase)
        plan = lint_engine.get_improvement_plan(result)
        assert len(plan) > 0
        assert all("priority" in item for item in plan)
        assert all("action" in item for item in plan)

    def test_lint_vague_expected_results(self, lint_engine):
        """Test that vague expected results generate info."""
        tc = QaTestCase(
            title="Test with vague expected results",
            description="This test has vague expected results in steps.",
            preconditions=["System is ready to test"],
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Click the submit button on the form",
                    expected_result="Works correctly",
                )
            ],
            expected_result="Everything works as expected",
        )
        result = lint_engine.lint(tc)
        # Should have suggestions or info about being more specific
        assert len(result.issues) > 0 or len(result.suggestions) > 0


class TestDataHygiene:
    """Credentials and identifiers must not be baked into the test flow."""

    @pytest.fixture
    def engine(self):
        return LintEngine()

    def _testcase(self, **overrides):
        base = {
            "title": "Kullanıcı Girişi - Sipariş görüntüleme akışı",
            "description": "Bu test, kullanıcının giriş yapıp siparişini görüntülemesini doğrular.",
            "preconditions": ["Kullanıcı hesabı aktif"],
            "steps": [
                QaTestStep(
                    step_number=1,
                    action="Kullanıcı bilgileriyle giriş yap",
                    expected_result="Kullanıcı dashboard sayfasına yönlendirilir",
                )
            ],
            "expected_result": "Kullanıcı siparişini görüntüler",
            "tags": ["auth"],
            "requirements": ["REQ-1"],
        }
        base.update(overrides)
        return QaTestCase(**base)

    def _rules(self, result):
        return {issue.rule for issue in result.issues}

    def test_hardcoded_password_is_an_error(self):
        """BAD-003 documents this as a security risk; nothing used to catch it."""
        tc = self._testcase(
            steps=[
                QaTestStep(
                    step_number=1,
                    action="john@company.com ve S3cr3tP@ss ile giriş yap",
                    expected_result="Giriş başarılı olur",
                )
            ]
        )
        result = LintEngine().lint(tc)

        assert "test_data.hardcoded_credentials" in self._rules(result)
        severity = next(
            i.severity for i in result.issues if i.rule == "test_data.hardcoded_credentials"
        )
        assert severity == LintSeverity.ERROR

    def test_labelled_secret_is_detected(self):
        tc = self._testcase(
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Authorization header'a token=ghp_abc123def456 ekle",
                    expected_result="İstek yetkilendirilir",
                )
            ]
        )
        assert "test_data.hardcoded_credentials" in self._rules(LintEngine().lint(tc))

    def test_undeclared_email_in_a_step_is_flagged(self):
        tc = self._testcase(
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Email alanına john@company.com gir",
                    expected_result="Email kabul edilir",
                )
            ]
        )
        assert "test_data.hardcoded_identity" in self._rules(LintEngine().lint(tc))

    def test_email_declared_as_test_data_is_not_flagged(self):
        """Declaring the value is exactly the fix, so it must clear the rule."""
        tc = self._testcase(
            steps=[
                QaTestStep(
                    step_number=1,
                    action="Email alanına test@example.com gir",
                    expected_result="Email kabul edilir",
                )
            ],
            test_data=[QaTestData(name="email", value="test@example.com")],
        )
        rules = self._rules(LintEngine().lint(tc))

        assert "test_data.hardcoded_identity" not in rules
        assert "test_data.not_parameterized" not in rules

    def test_email_in_preconditions_only_is_not_flagged(self):
        """Naming the test account as a precondition is normal practice."""
        tc = self._testcase(preconditions=["Test kullanıcısı kayıtlı (test@example.com)"])
        assert "test_data.hardcoded_identity" not in self._rules(LintEngine().lint(tc))

    def test_literal_values_without_test_data_are_flagged(self):
        tc = self._testcase(
            steps=[
                QaTestStep(
                    step_number=1,
                    action="12345 numaralı siparişin detayına git",
                    expected_result="Sipariş detayı görüntülenir",
                )
            ]
        )
        assert "test_data.not_parameterized" in self._rules(LintEngine().lint(tc))

    def test_clean_testcase_triggers_no_data_hygiene_rules(self):
        rules = self._rules(LintEngine().lint(self._testcase()))
        assert not {r for r in rules if r.startswith("test_data.hardcoded")}
