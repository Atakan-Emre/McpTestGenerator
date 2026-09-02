"""Conformance tests for MCP revision 2025-11-25 features.

Covers the metadata the server publishes (tool titles, behaviour annotations,
result schemas), the structured-content contract, resource templates, and
argument completion.
"""

import jsonschema
import pytest
from mcp.types import CallToolResult, Completion, PromptReference, ResourceTemplateReference

from qa_mcp.core.schemas import OUTPUT_SCHEMAS
from qa_mcp.server import (
    EXAMPLE_QUALITIES,
    TOOL_TITLES,
    call_tool,
    complete_argument,
    list_resource_templates,
    list_resources,
    list_tools,
)


class _Arg:
    """Minimal stand-in for types.CompletionArgument."""

    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value


class TestToolMetadata:
    """Tools must advertise the newer descriptive fields."""

    @pytest.mark.asyncio
    async def test_every_tool_has_a_display_title(self):
        tools = await list_tools()
        assert tools
        for tool in tools:
            assert tool.title, f"{tool.name} has no title"
            assert tool.annotations is not None
            assert tool.annotations.title == tool.title

    @pytest.mark.asyncio
    async def test_every_tool_is_annotated_read_only(self):
        """QA-MCP tools are pure functions; clients should not gate them."""
        for tool in await list_tools():
            annotations = tool.annotations
            assert annotations.readOnlyHint is True, tool.name
            assert annotations.destructiveHint is False, tool.name
            assert annotations.idempotentHint is True, tool.name
            assert annotations.openWorldHint is False, tool.name

    @pytest.mark.asyncio
    async def test_every_tool_declares_an_output_schema(self):
        for tool in await list_tools():
            assert tool.outputSchema is OUTPUT_SCHEMAS[tool.name]
            assert tool.outputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_title_table_matches_the_published_tools(self):
        """A new tool cannot ship without a title and schema."""
        names = {tool.name for tool in await list_tools()}
        assert names == set(TOOL_TITLES)
        assert names == set(OUTPUT_SCHEMAS)

    def test_all_output_schemas_are_valid_json_schema(self):
        for name, schema in OUTPUT_SCHEMAS.items():
            jsonschema.Draft202012Validator.check_schema(schema)
            assert schema, name


class TestStructuredContent:
    """Tool results are returned as structured data, not a text blob."""

    SAMPLE = {
        "title": "Structured content probe case",
        "description": "A test case used to exercise the structured output contract.",
        "preconditions": ["System is ready for testing"],
        "steps": [
            {
                "step_number": 1,
                "action": "Execute the probe flow",
                "expected_result": "Probe flow completes",
            }
        ],
        "expected_result": "The probe completes successfully",
        "module": "probe",
        "requirements": ["REQ-1"],
    }

    CALLS = {
        "testcase_generate": {"feature": "Login", "acceptance_criteria": ["Valid login works"]},
        "testcase_lint": {"testcase": SAMPLE},
        "testcase_lint_batch": {"testcases": [SAMPLE]},
        "testcase_normalize": {"input_data": SAMPLE},
        "testcase_to_xray": {"testcase": SAMPLE, "project_key": "PROJ"},
        "testcase_to_xray_batch": {"testcases": [SAMPLE], "project_key": "PROJ"},
        "suite_compose": {"testcases": [SAMPLE], "target": "regression"},
        "suite_coverage_report": {"testcases": [SAMPLE], "requirements": ["REQ-1"]},
        "xray_get_mapping_template": {},
    }

    @pytest.mark.asyncio
    async def test_every_tool_is_exercised(self):
        """Guard against a tool being added without a conformance case."""
        names = {tool.name for tool in await list_tools()}
        assert names == set(self.CALLS)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name", sorted(CALLS))
    async def test_result_validates_against_its_output_schema(self, tool_name):
        """The runtime validates structuredContent; so must we."""
        result = await call_tool(tool_name, dict(self.CALLS[tool_name]))

        assert isinstance(result, dict), f"{tool_name} did not return structured content"
        jsonschema.validate(instance=result, schema=OUTPUT_SCHEMAS[tool_name])

    @pytest.mark.asyncio
    async def test_lint_error_path_also_matches_the_schema(self):
        """Error-shaped results are ordinary results and must still conform."""
        result = await call_tool("testcase_lint", {"testcase": {"steps": "not-a-list"}})
        jsonschema.validate(instance=result, schema=OUTPUT_SCHEMAS["testcase_lint"])

    @pytest.mark.asyncio
    async def test_compose_error_path_also_matches_the_schema(self):
        result = await call_tool("suite_compose", {"testcases": [], "target": "bogus"})
        jsonschema.validate(instance=result, schema=OUTPUT_SCHEMAS["suite_compose"])


class TestProtocolErrors:
    """Failures must be flagged with isError, not smuggled into a success."""

    @pytest.mark.asyncio
    async def test_unknown_tool_sets_is_error(self):
        result = await call_tool("no_such_tool", {})
        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_missing_required_argument_sets_is_error(self):
        result = await call_tool("testcase_lint", {})
        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_successful_call_is_not_an_error_result(self):
        result = await call_tool("xray_get_mapping_template", {})
        assert not isinstance(result, CallToolResult)


class TestResourceTemplatesAndCompletion:
    """Parameterised resources and argument completion."""

    @pytest.mark.asyncio
    async def test_example_template_is_published(self):
        templates = await list_resource_templates()
        assert [t.uriTemplate for t in templates] == ["qa://examples/{quality}"]
        assert templates[0].title

    @pytest.mark.asyncio
    async def test_template_expands_to_real_resources(self):
        """Each completion value must resolve to a listed resource."""
        listed = {str(r.uri) for r in await list_resources()}
        for quality in EXAMPLE_QUALITIES:
            assert f"qa://examples/{quality}" in listed

    @pytest.mark.asyncio
    async def test_completion_offers_every_quality(self):
        result = await complete_argument(
            ResourceTemplateReference(type="ref/resource", uri="qa://examples/{quality}"),
            _Arg("quality", ""),
        )
        assert isinstance(result, Completion)
        assert sorted(result.values) == sorted(EXAMPLE_QUALITIES)

    @pytest.mark.asyncio
    async def test_completion_filters_by_prefix(self):
        result = await complete_argument(
            ResourceTemplateReference(type="ref/resource", uri="qa://examples/{quality}"),
            _Arg("quality", "g"),
        )
        assert result.values == ["good"]

    @pytest.mark.asyncio
    async def test_completion_for_prompt_argument(self):
        result = await complete_argument(
            PromptReference(type="ref/prompt", name="select-smoke-tests"),
            _Arg("max_duration", "1"),
        )
        assert result is not None
        assert all(v.startswith("1") for v in result.values)

    @pytest.mark.asyncio
    async def test_completion_returns_none_for_unknown_argument(self):
        result = await complete_argument(
            PromptReference(type="ref/prompt", name="create-manual-test"),
            _Arg("feature", "x"),
        )
        assert result is None


class TestInputSchemas:
    """Published input schemas must match what the tools actually accept."""

    @pytest.mark.asyncio
    async def test_compose_target_enum_lists_every_supported_suite(self):
        """Regression: `integration`/`performance` gained rules but stayed
        absent from the enum, so the runtime rejected them before dispatch."""
        from qa_mcp.core.standards import SUITE_RULES

        tools = {tool.name: tool for tool in await list_tools()}
        enum = tools["suite_compose"].inputSchema["properties"]["target"]["enum"]

        assert sorted(enum) == sorted(SUITE_RULES)

    @pytest.mark.asyncio
    async def test_all_input_schemas_are_valid_json_schema(self):
        for tool in await list_tools():
            jsonschema.Draft202012Validator.check_schema(tool.inputSchema)
