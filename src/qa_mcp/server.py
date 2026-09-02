"""
QA-MCP Server - Main Entry Point.

MCP server for test case generation, quality control, and Xray integration.
"""

import argparse
import asyncio
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    Completion,
    CompletionArgument,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    PromptReference,
    Resource,
    ResourceTemplate,
    ResourceTemplateReference,
    TextContent,
    Tool,
    ToolAnnotations,
)

from qa_mcp import __version__
from qa_mcp.core.schemas import OUTPUT_SCHEMAS
from qa_mcp.core.standards import SUITE_RULES
from qa_mcp.prompts.templates import PROMPT_REGISTRY
from qa_mcp.resources.standards import (
    get_bad_examples,
    get_good_examples,
    get_lint_rules,
    get_testcase_standard,
    get_xray_mapping,
)
from qa_mcp.tools.compose import compose_suite, coverage_report
from qa_mcp.tools.generate import generate_testcase
from qa_mcp.tools.lint import lint_batch, lint_testcase
from qa_mcp.tools.normalize import normalize_testcase
from qa_mcp.tools.to_xray import (
    convert_batch_to_xray,
    convert_to_xray,
    get_xray_field_mapping_template,
)

PromptFactory = Callable[..., dict[str, Any]]

TOOL_NAME_ALIASES = {
    "testcase.generate": "testcase_generate",
    "testcase.lint": "testcase_lint",
    "testcase.lint_batch": "testcase_lint_batch",
    "testcase.normalize": "testcase_normalize",
    "testcase.to_xray": "testcase_to_xray",
    "testcase.to_xray_batch": "testcase_to_xray_batch",
    "suite.compose": "suite_compose",
    "suite.coverage_report": "suite_coverage_report",
    "xray.get_mapping_template": "xray_get_mapping_template",
}


# Completion suggestions for free-text prompt arguments.
PROMPT_ARGUMENT_SUGGESTIONS: dict[str, list[str]] = {
    "max_duration": ["15", "30", "60", "120"],
}

# Human-readable display names (MCP revision 2025-11-25 `title` field).
TOOL_TITLES = {
    "testcase_generate": "Test Case Üret",
    "testcase_lint": "Test Case Kalite Analizi",
    "testcase_lint_batch": "Toplu Kalite Analizi",
    "testcase_normalize": "Test Case Normalleştir",
    "testcase_to_xray": "Xray Formatına Dönüştür",
    "testcase_to_xray_batch": "Toplu Xray Dönüşümü",
    "suite_compose": "Test Suite Oluştur",
    "suite_coverage_report": "Kapsam Raporu",
    "xray_get_mapping_template": "Xray Alan Eşleme Şablonu",
}


def _canonicalize_tool_name(name: str) -> str:
    """Return the Claude Desktop-safe tool name for the requested tool."""
    return TOOL_NAME_ALIASES.get(name, name)


def _tool_annotations(title: str) -> ToolAnnotations:
    """Behaviour hints for a QA-MCP tool.

    Every tool is a pure transformation of its arguments: nothing is persisted,
    no external system is contacted, and repeating a call with the same input
    has no additional effect. Declaring that lets clients skip the approval
    prompts they show for tools that might mutate state.
    """
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("qa-mcp")

# Configuration
ENABLE_WRITE_TOOLS = os.getenv("ENABLE_WRITE_TOOLS", "false").lower() == "true"
AUDIT_LOG_ENABLED = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"

# Create server instance. Passing the version explicitly stops clients from
# reporting the MCP SDK's version as the server's.
server = Server("qa-mcp", version=__version__)


# ==============================================================================
# Audit Logging
# ==============================================================================


def audit_log(tool_name: str, args: dict[str, Any], result_summary: str) -> None:
    """Log tool invocations for audit purposes."""
    if not AUDIT_LOG_ENABLED:
        return

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "args_hash": hash(json.dumps(args, sort_keys=True, default=str)),
        "result_summary": result_summary[:200],
    }
    logger.info(f"AUDIT: {json.dumps(log_entry)}")


# ==============================================================================
# Tools
# ==============================================================================


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    tools = [
        Tool(
            name="testcase_generate",
            description="Feature açıklaması ve acceptance criteria'dan standart test case üretir",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "string",
                        "description": "Feature açıklaması",
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Kabul kriterleri listesi",
                    },
                    "module": {
                        "type": "string",
                        "description": "Modül/bileşen adı (opsiyonel)",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Risk seviyesi (default: medium)",
                    },
                    "include_negative": {
                        "type": "boolean",
                        "description": "Negatif senaryolar dahil mi (default: true)",
                    },
                    "include_boundary": {
                        "type": "boolean",
                        "description": "Boundary test önerileri dahil mi (default: true)",
                    },
                },
                "required": ["feature", "acceptance_criteria"],
            },
        ),
        Tool(
            name="testcase_lint",
            description="Test case'i analiz eder, kalite skoru ve iyileştirme önerileri döner",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcase": {
                        "type": "object",
                        "description": "Analiz edilecek test case",
                    },
                    "include_improvement_plan": {
                        "type": "boolean",
                        "description": "Öncelikli iyileştirme planı dahil mi (default: true)",
                    },
                    "strict_mode": {
                        "type": "boolean",
                        "description": "Daha katı kurallar uygula (default: false)",
                    },
                },
                "required": ["testcase"],
            },
        ),
        Tool(
            name="testcase_lint_batch",
            description="Birden fazla test case'i toplu analiz eder",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcases": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Analiz edilecek test case listesi",
                    },
                    "strict_mode": {
                        "type": "boolean",
                        "description": "Daha katı kurallar uygula",
                    },
                },
                "required": ["testcases"],
            },
        ),
        Tool(
            name="testcase_normalize",
            description="Farklı formatlardaki test case'leri QA-MCP standardına çevirir",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_data": {
                        "type": ["string", "object"],
                        "description": "Normalize edilecek test case (markdown, gherkin, json veya plain text)",
                    },
                    "source_format": {
                        "type": "string",
                        "enum": ["auto", "markdown", "gherkin", "json", "plain"],
                        "description": "Kaynak format (default: auto)",
                    },
                },
                "required": ["input_data"],
            },
        ),
        Tool(
            name="testcase_to_xray",
            description="Standart test case'i Xray import formatına dönüştürür",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcase": {
                        "type": "object",
                        "description": "Dönüştürülecek test case",
                    },
                    "project_key": {
                        "type": "string",
                        "description": "Jira proje anahtarı (örn: PROJ)",
                    },
                    "test_type": {
                        "type": "string",
                        "enum": ["Manual", "Automated", "Generic"],
                        "description": "Xray test tipi (default: Manual)",
                    },
                    "include_custom_fields": {
                        "type": "boolean",
                        "description": "Custom field'ları dahil et (default: true)",
                    },
                    "custom_field_mappings": {
                        "type": "object",
                        "description": "Custom field ID eşlemeleri",
                    },
                },
                "required": ["testcase", "project_key"],
            },
        ),
        Tool(
            name="testcase_to_xray_batch",
            description="Birden fazla test case'i toplu olarak Xray formatına dönüştürür",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcases": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Dönüştürülecek test case listesi",
                    },
                    "project_key": {
                        "type": "string",
                        "description": "Jira proje anahtarı",
                    },
                    "test_type": {
                        "type": "string",
                        "enum": ["Manual", "Automated", "Generic"],
                    },
                },
                "required": ["testcases", "project_key"],
            },
        ),
        Tool(
            name="suite_compose",
            description="Test case listesinden Smoke/Regression/E2E suite oluşturur",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcases": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Test case listesi",
                    },
                    "target": {
                        "type": "string",
                        "enum": sorted(SUITE_RULES),
                        "description": "Suite tipi",
                    },
                    "sprint": {
                        "type": "string",
                        "description": "Sprint adı/numarası (opsiyonel)",
                    },
                    "max_duration_minutes": {
                        "type": "integer",
                        "description": "Maksimum suite süresi (dakika)",
                    },
                },
                "required": ["testcases", "target"],
            },
        ),
        Tool(
            name="suite_coverage_report",
            description="Test suite için kapsam raporu oluşturur",
            inputSchema={
                "type": "object",
                "properties": {
                    "testcases": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Test case listesi",
                    },
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Kontrol edilecek gereksinim ID'leri",
                    },
                    "modules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Kontrol edilecek modül listesi",
                    },
                },
                "required": ["testcases"],
            },
        ),
        Tool(
            name="xray_get_mapping_template",
            description="Xray alan eşleme şablonunu döner",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

    # Attach the MCP 2025-11-25 metadata in one place so a new tool cannot be
    # added without a display name and a result schema.
    for tool in tools:
        title = TOOL_TITLES[tool.name]
        tool.title = title
        tool.annotations = _tool_annotations(title)
        tool.outputSchema = OUTPUT_SCHEMAS[tool.name]

    return tools


def _tool_error(name: str, message: str) -> CallToolResult:
    """Build a protocol-level error result.

    Returning a plain dict with an ``error`` key left ``isError`` false, so
    clients treated a failed call as a successful one whose payload happened to
    mention an error.
    """
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps({"error": message, "tool": name}, ensure_ascii=False),
            )
        ],
        isError=True,
    )


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any] | CallToolResult:
    """Handle tool calls.

    Returning a ``dict`` makes the runtime emit it as ``structuredContent``
    (validated against the tool's ``outputSchema``) alongside the JSON text
    block, so clients get typed data instead of a string they have to parse.
    """
    canonical_name = _canonicalize_tool_name(name)
    logger.debug(f"Tool called: {name} (canonical: {canonical_name}) with args: {arguments}")

    try:
        result: Any = None

        if canonical_name == "testcase_generate":
            result = generate_testcase(
                feature=arguments["feature"],
                acceptance_criteria=arguments["acceptance_criteria"],
                module=arguments.get("module"),
                risk_level=arguments.get("risk_level", "medium"),
                include_negative=arguments.get("include_negative", True),
                include_boundary=arguments.get("include_boundary", True),
            )
            audit_log(
                canonical_name,
                arguments,
                f"Generated {result.get('total_generated', 0)} test cases",
            )

        elif canonical_name == "testcase_lint":
            result = lint_testcase(
                testcase=arguments["testcase"],
                include_improvement_plan=arguments.get("include_improvement_plan", True),
                strict_mode=arguments.get("strict_mode", False),
            )
            audit_log(canonical_name, arguments, f"Lint score: {result.get('score', 0)}")

        elif canonical_name == "testcase_lint_batch":
            result = lint_batch(
                testcases=arguments["testcases"],
                include_improvement_plan=False,
                strict_mode=arguments.get("strict_mode", False),
            )
            audit_log(
                canonical_name,
                arguments,
                f"Batch lint: {result.get('aggregate', {}).get('average_score', 0)} avg",
            )

        elif canonical_name == "testcase_normalize":
            result = normalize_testcase(
                input_data=arguments["input_data"],
                source_format=arguments.get("source_format", "auto"),
            )
            audit_log(
                canonical_name,
                arguments,
                f"Normalized from {result.get('source_format_detected', 'unknown')}",
            )

        elif canonical_name == "testcase_to_xray":
            result = convert_to_xray(
                testcase=arguments["testcase"],
                project_key=arguments["project_key"],
                test_type=arguments.get("test_type"),
                include_custom_fields=arguments.get("include_custom_fields", True),
                custom_field_mappings=arguments.get("custom_field_mappings"),
            )
            audit_log(
                canonical_name, arguments, f"Converted to Xray for {arguments['project_key']}"
            )

        elif canonical_name == "testcase_to_xray_batch":
            result = convert_batch_to_xray(
                testcases=arguments["testcases"],
                project_key=arguments["project_key"],
                test_type=arguments.get("test_type"),
            )
            audit_log(
                canonical_name,
                arguments,
                f"Batch converted {result.get('summary', {}).get('successful', 0)} to Xray",
            )

        elif canonical_name == "suite_compose":
            result = compose_suite(
                testcases=arguments["testcases"],
                target=arguments["target"],
                sprint=arguments.get("sprint"),
                max_duration_minutes=arguments.get("max_duration_minutes"),
            )
            audit_log(canonical_name, arguments, f"Composed {arguments['target']} suite")

        elif canonical_name == "suite_coverage_report":
            result = coverage_report(
                testcases=arguments["testcases"],
                requirements=arguments.get("requirements"),
                modules=arguments.get("modules"),
            )
            audit_log(
                canonical_name,
                arguments,
                f"Coverage report for {result.get('total_testcases', 0)} tests",
            )

        elif canonical_name == "xray_get_mapping_template":
            result = get_xray_field_mapping_template()
            audit_log(canonical_name, arguments, "Returned mapping template")

        else:
            return _tool_error(name, f"Unknown tool: {name}")

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Tool error: {name} - {str(e)}")
        return _tool_error(name, str(e))


# ==============================================================================
# Resources
# ==============================================================================


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="qa://standards/testcase/v1",
            name="Test Case Standard v1",
            title="Test Case Standardı",
            description="Kurumsal test case yazım standardı",
            mimeType="application/json",
        ),
        Resource(
            uri="qa://checklists/lint-rules/v1",
            name="Lint Rules v1",
            title="Lint Kuralları",
            description="Test case kalite kontrol kuralları",
            mimeType="application/json",
        ),
        Resource(
            uri="qa://mappings/xray/v1",
            name="Xray Field Mapping v1",
            title="Xray Alan Eşlemesi",
            description="QA-MCP to Xray alan eşlemeleri",
            mimeType="application/json",
        ),
        Resource(
            uri="qa://examples/good",
            name="Good Examples",
            title="İyi Örnekler",
            description="İyi test case örnekleri",
            mimeType="application/json",
        ),
        Resource(
            uri="qa://examples/bad",
            name="Bad Examples",
            title="Kötü Örnekler (Anti-pattern)",
            description="Kötü test case örnekleri (anti-patterns)",
            mimeType="application/json",
        ),
    ]


# Values the `qa://examples/{quality}` template accepts.
EXAMPLE_QUALITIES = ("good", "bad")


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """Expose the parameterised form of the example collections.

    `qa://examples/good` and `qa://examples/bad` are two instances of one
    template; declaring it lets clients discover the axis and complete it.
    """
    return [
        ResourceTemplate(
            uriTemplate="qa://examples/{quality}",
            name="Test Case Examples",
            title="Test Case Örnekleri",
            description=(
                "Kalite seviyesine göre örnek test case'ler. "
                f"Geçerli değerler: {', '.join(EXAMPLE_QUALITIES)}"
            ),
            mimeType="application/json",
        ),
    ]


@server.completion()
async def complete_argument(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: Any = None,
) -> Completion | None:
    """Complete resource-template and prompt arguments."""
    prefix = (argument.value or "").lower()

    if isinstance(ref, ResourceTemplateReference) and argument.name == "quality":
        values = [q for q in EXAMPLE_QUALITIES if q.startswith(prefix)]
        return Completion(values=values, total=len(values), hasMore=False)

    if isinstance(ref, PromptReference):
        values = [
            v for v in PROMPT_ARGUMENT_SUGGESTIONS.get(argument.name, []) if v.startswith(prefix)
        ]
        if values:
            return Completion(values=values, total=len(values), hasMore=False)

    return None


RESOURCE_MAP: dict[str, Callable[[], Any]] = {
    "qa://standards/testcase/v1": get_testcase_standard,
    "qa://checklists/lint-rules/v1": get_lint_rules,
    "qa://mappings/xray/v1": get_xray_mapping,
    "qa://examples/good": get_good_examples,
    "qa://examples/bad": get_bad_examples,
}


def _resolve_resource_uri(uri: Any) -> str:
    """Normalize the URI the MCP runtime passes in.

    The SDK hands the handler a pydantic ``AnyUrl``, not a ``str``, and URL
    parsing may append a trailing slash to authority-only URIs. Both forms have
    to resolve to the same registry key.
    """
    uri_str = str(uri)
    if uri_str in RESOURCE_MAP:
        return uri_str

    trimmed = uri_str.rstrip("/")
    if trimmed in RESOURCE_MAP:
        return trimmed

    raise ValueError(f"Unknown resource: {uri_str}")


@server.read_resource()
async def read_resource(uri: Any) -> str:
    """Read a resource by URI."""
    logger.debug(f"Resource read: {uri}")

    key = _resolve_resource_uri(uri)
    data = RESOURCE_MAP[key]()
    return json.dumps(data, ensure_ascii=False, indent=2)


# ==============================================================================
# Prompts
# ==============================================================================


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    prompts = []

    for name, func in PROMPT_REGISTRY.items():
        prompt_data = cast(PromptFactory, func)()
        prompts.append(
            Prompt(
                name=name,
                description=prompt_data.get("description", ""),
                arguments=[
                    PromptArgument(
                        name=arg["name"],
                        description=arg.get("description", ""),
                        required=arg.get("required", False),
                    )
                    for arg in prompt_data.get("arguments", [])
                ],
            )
        )

    return prompts


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Get a prompt by name."""
    logger.debug(f"Prompt requested: {name} with args: {arguments}")

    if name not in PROMPT_REGISTRY:
        raise ValueError(f"Unknown prompt: {name}")

    func = cast(PromptFactory, PROMPT_REGISTRY[name])
    kwargs: dict[str, Any] = {}

    if arguments:
        # Parse arguments based on prompt type
        if name == "create-manual-test":
            kwargs["feature"] = arguments.get("feature")
            if "acceptance_criteria" in arguments:
                try:
                    kwargs["acceptance_criteria"] = json.loads(arguments["acceptance_criteria"])
                except json.JSONDecodeError:
                    kwargs["acceptance_criteria"] = [arguments["acceptance_criteria"]]

        elif name == "select-smoke-tests":
            if "testcases" in arguments:
                try:
                    kwargs["testcases"] = json.loads(arguments["testcases"])
                except json.JSONDecodeError:
                    pass
            if "max_duration" in arguments:
                kwargs["max_duration"] = int(arguments["max_duration"])

        elif name == "generate-negative-scenarios":
            kwargs["feature"] = arguments.get("feature")
            if "positive_testcases" in arguments:
                try:
                    kwargs["positive_testcases"] = json.loads(arguments["positive_testcases"])
                except json.JSONDecodeError:
                    pass

        elif name == "review-test-coverage":
            if "testcases" in arguments:
                try:
                    kwargs["testcases"] = json.loads(arguments["testcases"])
                except json.JSONDecodeError:
                    pass
            if "requirements" in arguments:
                try:
                    kwargs["requirements"] = json.loads(arguments["requirements"])
                except json.JSONDecodeError:
                    kwargs["requirements"] = [arguments["requirements"]]

    prompt_data = func(**kwargs)

    return GetPromptResult(
        description=prompt_data.get("description", ""),
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_data["prompt"],
                ),
            ),
        ],
    )


# ==============================================================================
# Main Entry Point
# ==============================================================================


def main() -> None:
    """Main entry point for the QA-MCP server."""
    parser = argparse.ArgumentParser(
        prog="qa-mcp",
        description="QA-MCP server (Model Context Protocol) for test case generation and QA tooling.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.parse_args()

    logger.info(f"Starting QA-MCP Server v{__version__}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Write tools enabled: {ENABLE_WRITE_TOOLS}")
    logger.info(f"Audit logging enabled: {AUDIT_LOG_ENABLED}")

    async def run_server():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
