"""Tests for MCP tools."""

import pytest
from qa_mcp.tools.generate import generate_testcase
from qa_mcp.tools.lint import lint_testcase, lint_batch
from qa_mcp.tools.normalize import normalize_testcase
from qa_mcp.tools.to_xray import convert_to_xray
from qa_mcp.tools.compose import compose_suite, coverage_report


class TestGenerateTool:
    """Test testcase.generate tool."""

    def test_generate_basic(self):
        """Test basic test case generation."""
        result = generate_testcase(
            feature="User Login",
            acceptance_criteria=[
                "User can login with valid credentials",
                "User sees error with invalid credentials",
            ],
            module="auth",
            risk_level="high",
        )
        assert "testcases" in result
        assert len(result["testcases"]) > 0
        assert "coverage_summary" in result

    def test_generate_with_negative_scenarios(self):
        """Test generation includes negative scenarios."""
        result = generate_testcase(
            feature="Login Form Input Validation",
            acceptance_criteria=["Email field accepts valid format"],
            include_negative=True,
        )
        coverage = result["coverage_summary"]
        assert coverage["negative_scenarios"] > 0

    def test_generate_without_negative_scenarios(self):
        """Test generation can exclude negative scenarios."""
        result = generate_testcase(
            feature="Simple Feature",
            acceptance_criteria=["Feature works"],
            include_negative=False,
        )
        coverage = result["coverage_summary"]
        assert coverage["negative_scenarios"] == 0


class TestLintTool:
    """Test testcase.lint tool."""

    def test_lint_valid_testcase(self):
        """Test linting a valid test case."""
        testcase = {
            "title": "Valid Test Case with Good Title",
            "description": "This is a detailed description of what this test case does.",
            "preconditions": ["User is logged in", "Data is prepared"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Navigate to the settings page",
                    "expected_result": "Settings page is displayed correctly",
                }
            ],
            "expected_result": "User can access and view settings",
            "risk_level": "medium",
            "priority": "P2",
        }
        result = lint_testcase(testcase)
        assert "score" in result
        assert "grade" in result
        assert "issues" in result
        assert result["score"] > 0

    def test_lint_invalid_structure(self):
        """Test linting handles invalid structure."""
        testcase = {"invalid": "structure"}
        result = lint_testcase(testcase)
        assert result["score"] == 0
        assert "error" in result

    def test_lint_batch(self):
        """Test batch linting."""
        testcases = [
            {
                "title": "Test Case Number One",
                "description": "Description for test case one",
                "preconditions": ["Ready"],
                "steps": [
                    {"step_number": 1, "action": "Do action", "expected_result": "Result"}
                ],
                "expected_result": "Done",
            },
            {
                "title": "Test Case Number Two",
                "description": "Description for test case two",
                "preconditions": ["Ready"],
                "steps": [
                    {"step_number": 1, "action": "Do action", "expected_result": "Result"}
                ],
                "expected_result": "Done",
            },
        ]
        result = lint_batch(testcases)
        assert "results" in result
        assert "aggregate" in result
        assert result["aggregate"]["total_testcases"] == 2


class TestNormalizeTool:
    """Test testcase.normalize tool."""

    def test_normalize_json(self):
        """Test normalizing JSON format."""
        input_data = {
            "title": "Test from JSON format",
            "description": "A test case from JSON format",
            "steps": [{"action": "Do something", "expected": "Something happens"}],
        }
        result = normalize_testcase(input_data, source_format="json")
        assert result["testcase"] is not None
        assert result["source_format_detected"] == "json"

    def test_normalize_gherkin(self):
        """Test normalizing Gherkin format."""
        gherkin = """
        Feature: User Login
        Scenario: Valid login
        Given user is registered
        When user enters credentials
        Then user is logged in
        """
        result = normalize_testcase(gherkin, source_format="gherkin")
        assert result["testcase"] is not None
        assert result["source_format_detected"] == "gherkin"

    def test_normalize_auto_detect(self):
        """Test auto-detection of format."""
        json_input = {"title": "Auto detect test", "description": "Testing auto"}
        result = normalize_testcase(json_input, source_format="auto")
        assert result["source_format_detected"] == "json"


class TestToXrayTool:
    """Test testcase.to_xray tool."""

    def test_convert_basic(self):
        """Test basic Xray conversion."""
        testcase = {
            "title": "Test for Xray Conversion",
            "description": "This test will be converted to Xray format",
            "preconditions": ["System is ready"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Perform test action",
                    "expected_result": "Action completes successfully",
                }
            ],
            "expected_result": "Test passes",
            "priority": "P1",
            "module": "core",
            "tags": ["smoke"],
        }
        result = convert_to_xray(testcase, project_key="TEST")
        assert result["xray_payload"] is not None
        assert result["xray_payload"]["fields"]["project"]["key"] == "TEST"
        assert "field_mapping_report" in result

    def test_convert_with_custom_fields(self):
        """Test conversion with custom field mappings."""
        testcase = {
            "title": "Test with Custom Fields",
            "description": "Testing custom field mapping",
            "preconditions": ["Ready"],
            "steps": [{"step_number": 1, "action": "Act", "expected_result": "Result"}],
            "expected_result": "Done",
            "risk_level": "high",
        }
        mappings = {"risk_level": "customfield_10001"}
        result = convert_to_xray(
            testcase,
            project_key="TEST",
            custom_field_mappings=mappings,
        )
        assert "customfield_10001" in result["xray_payload"]["fields"]


class TestComposeTool:
    """Test suite.compose tool."""

    def test_compose_smoke_suite(self):
        """Test composing a smoke suite."""
        testcases = [
            {
                "id": "TC-001",
                "title": "Critical Login Test",
                "description": "Test login functionality",
                "preconditions": ["Ready"],
                "steps": [{"step_number": 1, "action": "Login", "expected_result": "OK"}],
                "expected_result": "Logged in",
                "risk_level": "critical",
                "priority": "P0",
                "estimated_duration_minutes": 3,
            },
            {
                "id": "TC-002",
                "title": "Low Priority Feature Test",
                "description": "Test minor feature",
                "preconditions": ["Ready"],
                "steps": [{"step_number": 1, "action": "Test", "expected_result": "OK"}],
                "expected_result": "Done",
                "risk_level": "low",
                "priority": "P3",
                "estimated_duration_minutes": 10,
            },
        ]
        result = compose_suite(testcases, target="smoke")
        assert result["suite"] is not None
        # Smoke should prioritize critical tests
        assert "TC-001" in result["suite"]["testcases"]

    def test_coverage_report(self):
        """Test coverage report generation."""
        testcases = [
            {
                "id": "TC-001",
                "title": "Module A Test",
                "description": "Testing module A",
                "preconditions": ["Ready"],
                "steps": [{"step_number": 1, "action": "Test", "expected_result": "OK"}],
                "expected_result": "Done",
                "module": "module_a",
                "requirements": ["REQ-001"],
                "scenario_type": "positive",
            },
        ]
        result = coverage_report(
            testcases,
            requirements=["REQ-001", "REQ-002"],
            modules=["module_a", "module_b"],
        )
        assert "requirement_coverage" in result
        assert result["requirement_coverage"]["covered"] == 1
        assert result["requirement_coverage"]["uncovered"] == 1
