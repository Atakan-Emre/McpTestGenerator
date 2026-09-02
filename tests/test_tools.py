"""Tests for MCP tools."""

import re

import pytest

from qa_mcp.server import call_tool, list_tools
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

    def test_lint_non_conforming_testcase_is_still_linted(self):
        """A test case that violates the standard must be linted, not rejected.

        Regression: strict Pydantic validation used to abort before any rule
        ran, so the tool answered every substandard test case with score 0 and
        a raw validation dump instead of actionable issues.
        """
        testcase = {"invalid": "structure"}
        result = lint_testcase(testcase)

        assert result["schema_valid"] is False
        assert result["schema_errors"]
        assert result["passed"] is False
        assert 0 < result["score"] < 60

        rules = {issue["rule"] for issue in result["issues"]}
        assert "title.min_length" in rules
        assert "description.min_length" in rules
        assert "preconditions.required" in rules
        assert "steps.required" in rules
        assert "expected_result.min_length" in rules
        assert "valid_structure" not in rules

    def test_lint_documented_bad_examples_produce_issues(self):
        """The shipped `qa://examples/bad` anti-patterns must be lintable."""
        from qa_mcp.resources.standards import get_bad_examples

        for example in get_bad_examples():
            result = lint_testcase(example["testcase"], include_improvement_plan=False)
            assert result["issues"], f"{example['id']} produced no lint issues"
            assert "valid_structure" not in {i["rule"] for i in result["issues"]}

    def test_lint_unreadable_payload_still_reports_error(self):
        """Wrong field *types* remain a hard structural error."""
        result = lint_testcase({"title": "x", "steps": "not-a-list"})
        assert result["score"] == 0
        assert result["schema_valid"] is False
        assert "error" in result

    def test_lint_conforming_testcase_reports_schema_valid(self):
        """A standard-conforming test case is flagged as schema valid."""
        testcase = {
            "title": "Valid Test Case with Good Title",
            "description": "This is a detailed description of what this test case does.",
            "preconditions": ["User is logged in"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Navigate to the settings page",
                    "expected_result": "Settings page is displayed correctly",
                }
            ],
            "expected_result": "User can access and view settings",
        }
        result = lint_testcase(testcase)
        assert result["schema_valid"] is True
        assert result["schema_errors"] == []

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

    def test_normalize_plain_text_short_input(self):
        """Short plain text should still normalize into a valid testcase."""
        result = normalize_testcase("Login", source_format="plain")
        assert result["testcase"] is not None
        assert len(result["testcase"]["title"]) >= 10
        assert len(result["testcase"]["description"]) >= 20

    def test_normalize_gherkin_and_after_when_stays_in_step(self):
        """`And` after `When` should extend the action, not become a precondition."""
        gherkin = """
Feature: Login
Scenario: Valid login
Given user exists
When user enters username
And user enters password
Then dashboard is shown
        """
        result = normalize_testcase(gherkin, source_format="gherkin")
        testcase = result["testcase"]
        assert testcase is not None
        assert testcase["preconditions"] == ["user exists"]
        assert "user enters username" in testcase["steps"][0]["action"]
        assert "user enters password" in testcase["steps"][0]["action"]

    def test_normalize_json_fallback_preserves_labels(self):
        """Fallback JSON parsing should preserve labels semantics."""
        input_data = {
            "title": "JSON import testcase",
            "description": "This testcase uses non-standard step keys for normalization.",
            "steps": [{"action": "Run action", "expected": "See expected result"}],
            "labels": ["smoke"],
        }
        result = normalize_testcase(input_data, source_format="json")
        assert result["testcase"] is not None
        assert result["testcase"]["labels"] == ["smoke"]
        assert "smoke" not in result["testcase"]["tags"]


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

    def test_convert_duration_mapping_uses_template_field_name(self):
        """`estimated_duration_minutes` should map into Xray custom fields."""
        testcase = {
            "title": "Duration mapping test case",
            "description": "This test verifies estimated duration custom field mapping for Xray.",
            "preconditions": ["System is ready for testing"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Execute the mapped duration flow",
                    "expected_result": "Flow completes successfully",
                }
            ],
            "expected_result": "Estimated duration is included in mapped custom fields",
            "estimated_duration_minutes": 7,
        }
        result = convert_to_xray(
            testcase,
            project_key="TEST",
            custom_field_mappings={"estimated_duration_minutes": "customfield_10042"},
        )
        assert result["xray_payload"] is not None
        assert result["xray_payload"]["fields"]["customfield_10042"] == 7
        assert "estimated_duration_minutes" not in result["field_mapping_report"]["unmapped_fields"]


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


class TestMcpServerToolNames:
    """Test public MCP tool naming compatibility."""

    @pytest.mark.asyncio
    async def test_list_tools_are_claude_desktop_safe(self):
        """Published tool names should match Claude Desktop's validation regex."""
        tools = await list_tools()
        pattern = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

        assert tools
        assert all(pattern.fullmatch(tool.name) for tool in tools)
        assert all("." not in tool.name for tool in tools)
        assert "testcase_generate" in {tool.name for tool in tools}

    @pytest.mark.asyncio
    async def test_call_tool_accepts_legacy_dotted_aliases(self):
        """Legacy dotted names should continue to work for older clients."""
        result = await call_tool(
            "testcase.generate",
            {
                "feature": "User Login",
                "acceptance_criteria": ["User can login with valid credentials"],
            },
        )

        assert isinstance(result, dict)
        assert "testcases" in result
        assert result["total_generated"] >= 1


class TestXrayFieldFidelity:
    """Regressions for information lost or misreported during Xray conversion."""

    BASE = {
        "title": "Xray field fidelity test case",
        "description": "Verifies that conversion neither drops nor misreports fields.",
        "preconditions": ["System is ready for testing"],
        "steps": [
            {
                "step_number": 1,
                "action": "Execute the mapped flow",
                "expected_result": "Flow completes successfully",
            }
        ],
        "expected_result": "The overall expected result must survive conversion",
    }

    def test_expected_result_reaches_the_payload(self):
        """Regression: the overall expected result was silently dropped."""
        result = convert_to_xray(dict(self.BASE), project_key="TEST")
        description = result["xray_payload"]["fields"]["description"]

        assert self.BASE["expected_result"] in description
        assert "expected_result" in result["field_mapping_report"]["embedded_in_description"]
        assert "expected_result" not in result["field_mapping_report"]["unmapped_fields"]

    def test_defaulted_fields_do_not_produce_warnings(self):
        """Regression: always-populated enum defaults warned on every conversion."""
        result = convert_to_xray(dict(self.BASE), project_key="TEST")

        assert result["warnings"] == []
        assert result["field_mapping_report"]["unmapped_fields"] == []

    def test_genuinely_unmapped_field_still_warns(self):
        """A field with no Xray home must still be reported."""
        result = convert_to_xray(
            dict(self.BASE, related_testcases=["TC-OTHER"]), project_key="TEST"
        )

        assert result["field_mapping_report"]["unmapped_fields"] == ["related_testcases"]
        assert len(result["warnings"]) == 1

    def test_testcase_test_type_is_honoured(self):
        """`test_type` on the test case drove nothing; 'Manual' was hardcoded."""
        result = convert_to_xray(dict(self.BASE, test_type="Automated"), project_key="TEST")
        assert result["xray_payload"]["testtype"] == "Generic"

    def test_explicit_test_type_overrides_the_testcase(self):
        result = convert_to_xray(
            dict(self.BASE, test_type="Automated"), project_key="TEST", test_type="Manual"
        )
        assert result["xray_payload"]["testtype"] == "Manual"


class TestNormalizeRobustness:
    """Normalization must always yield a standard-conforming test case."""

    @pytest.mark.parametrize(
        ("payload", "source_format"),
        [
            ("# Kısa\n## Adımlar\n- Ok", "markdown"),
            ("Login", "plain"),
            ("Feature: X\nScenario: Y", "gherkin"),
            ({}, "json"),
            ({"title": "a", "description": "b"}, "json"),
            ("# Başlık\n**kalın**", "auto"),
        ],
    )
    def test_short_input_never_returns_null(self, payload, source_format):
        """Regression: short markdown aborted with a raw Pydantic error."""
        result = normalize_testcase(payload, source_format=source_format)

        assert result.get("error") is None
        testcase = result["testcase"]
        assert testcase is not None
        assert len(testcase["title"]) >= 10
        assert len(testcase["description"]) >= 20
        assert len(testcase["expected_result"]) >= 10
        assert testcase["steps"]

    def test_padding_is_reported_as_a_warning(self):
        """Filled-in content must be visible to the caller, not silent."""
        result = normalize_testcase("# Kısa\n## Adımlar\n- Ok", source_format="markdown")
        assert result["warnings"]
        assert "QA-MCP standardına yükseltildi" in result["transformations"]

    def test_over_long_title_is_truncated(self):
        result = normalize_testcase({"title": "x" * 500, "description": "y" * 40})
        assert len(result["testcase"]["title"]) == 200

    def test_out_of_range_duration_is_dropped(self):
        result = normalize_testcase(
            {
                "title": "Duration probe case",
                "description": "z" * 40,
                "estimated_duration_minutes": 9999,
            }
        )
        assert result["testcase"]["estimated_duration_minutes"] is None
        assert any("Tahmini süre" in w for w in result["warnings"])


class TestComposeTargets:
    """Suite target handling."""

    def test_unknown_target_returns_structured_error(self):
        """Regression: an unknown target raised ValueError out of the tool."""
        result = compose_suite([], target="bogus")

        assert result["suite"] is None
        assert result["errors"]
        assert "smoke" in result["errors"][0]

    @pytest.mark.parametrize(
        "target", ["smoke", "sanity", "regression", "e2e", "integration", "performance"]
    )
    def test_every_suite_type_has_selection_rules(self, target):
        """`integration` and `performance` silently fell back to regression rules."""
        result = compose_suite([], target=target)

        assert result.get("errors") is None
        assert result["suite"]["suite_type"] == target

    def test_target_is_case_and_space_insensitive(self):
        result = compose_suite([], target="  SMOKE ")
        assert result["suite"]["suite_type"] == "smoke"


class TestCoverageReportSkips:
    """Malformed input must be reported, not silently dropped."""

    VALID = {
        "title": "Coverage report probe case",
        "description": "A conforming test case used by the coverage report tests.",
        "preconditions": ["System is ready for testing"],
        "steps": [
            {
                "step_number": 1,
                "action": "Execute the probe",
                "expected_result": "Probe completes",
            }
        ],
        "expected_result": "The probe completes successfully",
        "module": "probe",
    }

    def test_unparseable_testcases_are_reported(self):
        """Regression: they were skipped with a bare `except: continue`, so the
        reported percentages silently excluded them."""
        result = coverage_report([self.VALID, {"title": "too short"}])

        assert result["total_testcases"] == 1
        assert len(result["skipped_testcases"]) == 1
        assert result["skipped_testcases"][0]["index"] == "1"
        assert result["skipped_testcases"][0]["reason"]
        assert any("rapora dahil edilemedi" in r for r in result["recommendations"])

    def test_all_valid_input_reports_no_skips(self):
        result = coverage_report([self.VALID])
        assert result["skipped_testcases"] == []
