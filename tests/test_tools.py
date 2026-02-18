"""Tests for MCP tools."""

from qa_mcp.tools.compose import compose_suite, coverage_report
from qa_mcp.tools.generate import generate_testcase
from qa_mcp.tools.lint import lint_batch, lint_testcase
from qa_mcp.tools.normalize import normalize_testcase
from qa_mcp.tools.to_xray import convert_to_xray


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
                "steps": [{"step_number": 1, "action": "Do action", "expected_result": "Result"}],
                "expected_result": "Done",
            },
            {
                "title": "Test Case Number Two",
                "description": "Description for test case two",
                "preconditions": ["Ready"],
                "steps": [{"step_number": 1, "action": "Do action", "expected_result": "Result"}],
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
Feature: User Login Functionality
Scenario: Valid user login with correct credentials
Given user is registered in the system
When user enters valid credentials
Then user is successfully logged in
        """
        result = normalize_testcase(gherkin, source_format="gherkin")
        # Gherkin parsing may have warnings but should still produce output
        assert result["source_format_detected"] == "gherkin"
        # Either testcase is present or there are documented warnings
        assert result["testcase"] is not None or len(result["warnings"]) > 0

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
            "title": "Test with Custom Fields for Xray",
            "description": "Testing custom field mapping for Xray conversion",
            "preconditions": ["System is ready for testing"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Perform the action",
                    "expected_result": "See the result",
                }
            ],
            "expected_result": "Conversion completes successfully",
            "risk_level": "high",
        }
        mappings = {"risk_level": "customfield_10001"}
        result = convert_to_xray(
            testcase,
            project_key="TEST",
            custom_field_mappings=mappings,
        )
        assert result["xray_payload"] is not None
        # Custom field should be in the payload if mapping was applied
        assert "customfield_10001" in result["xray_payload"]["fields"]


class TestComposeTool:
    """Test suite.compose tool."""

    def test_compose_smoke_suite(self):
        """Test composing a smoke suite."""
        testcases = [
            {
                "id": "TC-001",
                "title": "Critical Login Test for Authentication",
                "description": "Test login functionality for critical path",
                "preconditions": ["System is ready for testing"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Login to the system",
                        "expected_result": "Login succeeds",
                    }
                ],
                "expected_result": "User is logged in successfully",
                "risk_level": "critical",
                "priority": "P0",
                "estimated_duration_minutes": 3,
            },
            {
                "id": "TC-002",
                "title": "Low Priority Feature Test Case",
                "description": "Test minor feature functionality",
                "preconditions": ["System is ready for testing"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Test the feature",
                        "expected_result": "Feature works",
                    }
                ],
                "expected_result": "Feature test completes successfully",
                "risk_level": "low",
                "priority": "P3",
                "estimated_duration_minutes": 10,
            },
        ]
        result = compose_suite(testcases, target="smoke")
        assert result["suite"] is not None
        # Smoke should prioritize critical tests
        assert "TC-001" in result["suite"]["testcases"]

    def test_compose_smoke_label_does_not_bypass_filters(self):
        """Smoke labels must not bypass priority/risk/duration filters."""
        testcases = [
            {
                "id": "TC-001",
                "title": "Critical smoke test candidate",
                "description": "Valid critical test description for smoke suite selection behavior.",
                "preconditions": ["System is ready for testing"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Execute critical workflow path",
                        "expected_result": "Critical workflow succeeds",
                    }
                ],
                "expected_result": "Critical flow works successfully",
                "risk_level": "critical",
                "priority": "P0",
                "estimated_duration_minutes": 5,
            },
            {
                "id": "TC-002",
                "title": "Low priority testcase with smoke label",
                "description": "Low-priority test should not be force-selected by label alone.",
                "preconditions": ["System is ready for testing"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Execute non-critical workflow path",
                        "expected_result": "Non-critical workflow succeeds",
                    }
                ],
                "expected_result": "Non-critical flow works successfully",
                "risk_level": "low",
                "priority": "P3",
                "labels": ["smoke"],
                "estimated_duration_minutes": 20,
            },
        ]

        result = compose_suite(testcases, target="smoke", max_duration_minutes=15)
        selected = result["suite"]["testcases"]

        assert "TC-001" in selected
        assert "TC-002" not in selected

    def test_coverage_report(self):
        """Test coverage report generation."""
        testcases = [
            {
                "id": "TC-001",
                "title": "Module A Test Case for Coverage",
                "description": "Testing module A functionality for coverage report",
                "preconditions": ["System is ready for testing"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Test the module",
                        "expected_result": "Module works correctly",
                    }
                ],
                "expected_result": "Module test completes successfully",
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
        # Check the structure exists
        assert result["requirement_coverage"] is not None
        assert "total_requirements" in result["requirement_coverage"]
