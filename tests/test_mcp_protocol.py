"""Conformance tests for the published MCP surface (mcp 2.x).

Covers the metadata the server advertises, the structured-content contract, the
error contract, resource templates and argument completion.

Note the attribute naming: mcp 2.x exposes ``input_schema`` / ``output_schema``
/ ``is_error`` / ``structured_content``, where 1.x used the camelCase spellings.
The wire format is unchanged; only the Python attributes moved.
"""

import json

import jsonschema
import pytest
from mcp.types import PromptReference, ResourceTemplateReference

from qa_mcp.core.results import RESULT_MODELS
from qa_mcp.core.schemas import OUTPUT_SCHEMAS
from qa_mcp.server import EXAMPLE_QUALITIES, complete_argument, mcp
from tests.conftest import mcp_session

# The tools every deployment exposes, regardless of configuration.
BASE_TOOLS = {
    "testcase_generate",
    "testcase_lint",
    "testcase_lint_batch",
    "testcase_normalize",
    "testcase_to_xray",
    "testcase_to_xray_batch",
    "suite_compose",
    "suite_coverage_report",
    "xray_get_mapping_template",
}


class _Arg:
    """Stand-in for types.CompletionArgument."""

    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value


@pytest.fixture
async def tools():
    return {tool.name: tool for tool in await mcp.list_tools()}


class TestToolMetadata:
    """Tools must advertise titles, annotations and result schemas."""

    async def test_base_tools_are_published(self, tools):
        assert set(tools) >= BASE_TOOLS

    async def test_every_tool_has_a_display_title(self, tools):
        for name, tool in tools.items():
            assert tool.title, f"{name} has no title"

    async def test_analysis_tools_are_annotated_read_only(self, tools):
        """The nine analysis tools are pure functions; clients should not gate them."""
        for name in BASE_TOOLS:
            annotations = tools[name].annotations
            assert annotations is not None, name
            assert annotations.read_only_hint is True, name
            assert annotations.destructive_hint is False, name
            assert annotations.idempotent_hint is True, name
            assert annotations.open_world_hint is False, name

    async def test_every_tool_declares_a_result_schema(self, tools):
        for name in BASE_TOOLS:
            schema = tools[name].output_schema
            assert schema, f"{name} has no output schema"
            assert schema.get("properties"), f"{name} has an empty output schema"

    async def test_output_schemas_come_from_the_result_models(self, tools):
        """Schema and runtime type must have one definition, not two."""
        for name in BASE_TOOLS:
            assert tools[name].output_schema == RESULT_MODELS[name].model_json_schema()

    async def test_input_schemas_are_derived_from_the_signatures(self, tools):
        assert tools["testcase_lint"].input_schema["required"] == ["testcase"]
        assert set(tools["suite_compose"].input_schema["required"]) == {"testcases", "target"}
        assert tools["xray_get_mapping_template"].input_schema.get("required", []) == []

    async def test_suite_target_enum_matches_the_configured_rules(self, tools):
        from qa_mcp.core.standards import SUITE_RULES

        target = tools["suite_compose"].input_schema["properties"]["target"]
        enum = target.get("enum") or target["$ref"]
        if not isinstance(enum, list):  # pragma: no cover - schema shape guard
            defs = tools["suite_compose"].input_schema["$defs"]
            enum = next(iter(defs.values()))["enum"]
        assert sorted(enum) == sorted(SUITE_RULES)

    def test_all_schemas_are_valid_json_schema(self):
        for name, schema in OUTPUT_SCHEMAS.items():
            jsonschema.Draft202012Validator.check_schema(schema)
            assert schema, name


class TestStructuredContent:
    """Tool results are returned as validated structured data."""

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

    def test_every_base_tool_is_exercised(self):
        """Guard against a tool being added without a conformance case."""
        assert set(self.CALLS) == BASE_TOOLS

    @pytest.mark.parametrize("tool_name", sorted(CALLS))
    async def test_result_validates_against_its_schema(self, tool_name):
        result = await mcp.call_tool(tool_name, dict(self.CALLS[tool_name]))

        assert result.is_error is False, result.content
        assert result.structured_content is not None, f"{tool_name} returned no structured content"
        jsonschema.validate(instance=result.structured_content, schema=OUTPUT_SCHEMAS[tool_name])

    async def test_error_shaped_results_still_conform(self):
        """A lint verdict on unreadable input is a result, not a protocol error."""
        result = await mcp.call_tool("testcase_lint", {"testcase": {"steps": "not-a-list"}})
        jsonschema.validate(
            instance=result.structured_content, schema=OUTPUT_SCHEMAS["testcase_lint"]
        )

    async def test_text_content_mirrors_the_structured_content(self):
        result = await mcp.call_tool("xray_get_mapping_template", {})
        assert json.loads(result.content[0].text) == result.structured_content


class TestProtocolErrors:
    """Failures must be flagged, not smuggled into a successful result.

    Driven through a real session: ``mcp.call_tool`` raises, and the conversion
    into a result carrying ``is_error`` happens in the handler above it.
    """

    async def test_unknown_tool_is_an_error(self):
        async with mcp_session() as client:
            result = await client.call_tool("no_such_tool", {})
        assert result.is_error is True

    async def test_missing_required_argument_is_an_error(self):
        async with mcp_session() as client:
            result = await client.call_tool("testcase_lint", {})
        assert result.is_error is True

    async def test_value_outside_the_enum_is_rejected(self):
        async with mcp_session() as client:
            result = await client.call_tool("suite_compose", {"testcases": [], "target": "bogus"})
        assert result.is_error is True

    async def test_missing_project_key_is_an_error(self):
        """Neither an argument nor QA_MCP_XRAY_PROJECT_KEY: refuse, do not guess."""
        async with mcp_session() as client:
            result = await client.call_tool("testcase_to_xray", {"testcase": {}})
        assert result.is_error is True

    async def test_successful_call_is_not_flagged(self):
        async with mcp_session() as client:
            result = await client.call_tool("xray_get_mapping_template", {})
        assert result.is_error is False
        assert result.structured_content is not None


class TestAuditLog:
    """Every tool call is recorded, with its real outcome."""

    async def test_successful_call_is_audited(self, caplog):
        with caplog.at_level("INFO", logger="qa-mcp"):
            async with mcp_session() as client:
                await client.call_tool("xray_get_mapping_template", {})

        entries = _audit_entries(caplog)
        assert entries, "no audit entry was written"
        assert entries[-1]["tool"] == "xray_get_mapping_template"
        assert entries[-1]["outcome"] == "ok"

    async def test_failed_call_is_audited_as_an_error(self, caplog):
        """Regression: the runtime converts a raising tool into an error result
        below the interceptor, so catching exceptions alone logged it as 'ok'."""
        with caplog.at_level("INFO", logger="qa-mcp"):
            async with mcp_session() as client:
                await client.call_tool("testcase_to_xray", {"testcase": {}})

        entries = _audit_entries(caplog)
        assert entries[-1]["tool"] == "testcase_to_xray"
        assert entries[-1]["outcome"] == "error"

    async def test_argument_values_are_not_logged(self, caplog):
        """Argument names are useful; their values may be large or sensitive."""
        with caplog.at_level("INFO", logger="qa-mcp"):
            async with mcp_session() as client:
                await client.call_tool(
                    "testcase_lint", {"testcase": {"title": "SENSITIVE-MARKER-VALUE"}}
                )

        entries = _audit_entries(caplog)
        assert entries[-1]["argument_names"] == ["testcase"]
        assert "SENSITIVE-MARKER-VALUE" not in json.dumps(entries)


def _audit_entries(caplog) -> list[dict]:
    """Parse the AUDIT lines out of captured logs."""
    return [
        json.loads(record.message.removeprefix("AUDIT: "))
        for record in caplog.records
        if record.message.startswith("AUDIT: ")
    ]


class TestResourcesAndTemplates:
    async def test_fixed_resources_are_published_with_titles(self):
        resources = {str(r.uri): r for r in await mcp.list_resources()}
        assert "qa://standards/testcase/v1" in resources
        assert "qa://checklists/lint-rules/v1" in resources
        assert "qa://mappings/xray/v1" in resources
        assert all(r.title for r in resources.values())

    async def test_examples_are_served_by_a_template(self):
        templates = [t.uri_template for t in await mcp.list_resource_templates()]
        assert "qa://examples/{quality}" in templates

    @pytest.mark.parametrize("quality", EXAMPLE_QUALITIES)
    async def test_template_serves_every_advertised_quality(self, quality):
        contents = list(await mcp.read_resource(f"qa://examples/{quality}"))
        payload = json.loads(contents[0].content)
        assert payload and all("testcase" in example for example in payload)

    async def test_every_fixed_resource_is_readable(self):
        for resource in await mcp.list_resources():
            contents = list(await mcp.read_resource(resource.uri))
            assert json.loads(contents[0].content)

    async def test_unknown_quality_is_rejected(self):
        from mcp.server.mcpserver.exceptions import ResourceError

        with pytest.raises(ResourceError):
            list(await mcp.read_resource("qa://examples/mediocre"))


class TestPrompts:
    async def test_all_prompts_are_published_with_titles(self):
        prompts = {p.name: p for p in await mcp.list_prompts()}
        assert set(prompts) == {
            "create-manual-test",
            "select-smoke-tests",
            "generate-negative-scenarios",
            "review-test-coverage",
        }
        assert all(p.title for p in prompts.values())

    async def test_every_prompt_renders_without_arguments(self):
        for prompt in await mcp.list_prompts():
            result = await mcp.get_prompt(prompt.name, {})
            assert result.messages[0].content.text.strip()

    async def test_json_string_arguments_are_parsed(self):
        """Regression: the wire carries prompt arguments as strings, and mcp 2.x
        does not coerce them - a typed `list[str]` parameter raises."""
        result = await mcp.get_prompt(
            "create-manual-test",
            {
                "feature": "Şifre sıfırlama",
                "acceptance_criteria": json.dumps(["Kullanıcı e-posta ile link alır"]),
            },
        )
        text = result.messages[0].content.text
        assert "Şifre sıfırlama" in text
        assert "Kullanıcı e-posta ile link alır" in text

    async def test_a_plain_string_argument_is_tolerated(self):
        result = await mcp.get_prompt(
            "create-manual-test",
            {"feature": "Login", "acceptance_criteria": "tek kriter, json değil"},
        )
        assert "tek kriter, json değil" in result.messages[0].content.text

    async def test_object_list_argument_is_parsed(self):
        result = await mcp.get_prompt(
            "review-test-coverage",
            {
                "testcases": json.dumps([{"id": "TC-1", "title": "Login"}]),
                "requirements": json.dumps(["REQ-1"]),
            },
        )
        assert result.messages[0].content.text.strip()


class TestCompletion:
    async def test_completion_offers_every_quality(self):
        result = await complete_argument(
            ResourceTemplateReference(type="ref/resource", uri="qa://examples/{quality}"),
            _Arg("quality", ""),
        )
        assert sorted(result.values) == sorted(EXAMPLE_QUALITIES)

    async def test_completion_filters_by_prefix(self):
        result = await complete_argument(
            ResourceTemplateReference(type="ref/resource", uri="qa://examples/{quality}"),
            _Arg("quality", "g"),
        )
        assert result.values == ["good"]

    async def test_completion_for_a_prompt_argument(self):
        result = await complete_argument(
            PromptReference(type="ref/prompt", name="select-smoke-tests"),
            _Arg("max_duration", "1"),
        )
        assert result is not None
        assert all(v.startswith("1") for v in result.values)

    async def test_no_completion_for_a_free_text_argument(self):
        result = await complete_argument(
            PromptReference(type="ref/prompt", name="create-manual-test"),
            _Arg("feature", "x"),
        )
        assert result is None
