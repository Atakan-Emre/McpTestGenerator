"""
QA-MCP Server - Main Entry Point.

MCP server for test case generation, quality control, and Xray integration,
built on the mcp 2.x ``MCPServer`` API.

Tools are plain typed functions: the runtime derives each input schema from the
signature and each output schema from the Pydantic result model, so the schemas
cannot drift from the code that produces them. The behaviour itself lives in
``qa_mcp.tools``, which imports nothing from MCP.

What the server exposes depends on configuration. The nine analysis tools are
always available and never touch the network. The Jira/Xray tools appear only
once a tenant is configured, and the one that writes appears only when writes
have been explicitly enabled.
"""

import argparse
import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal, cast

from mcp.server.extension import CallNext, Extension, HandlerResult
from mcp.server.mcpserver import MCPServer
from mcp.types import (
    CallToolRequestParams,
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
    ToolAnnotations,
)

from qa_mcp import __version__
from qa_mcp.config import Settings, get_settings, reload_settings
from qa_mcp.core.results import (
    CoverageReportResult,
    GenerateResult,
    LintBatchResult,
    LintResult,
    NormalizeResult,
    SuiteCompositionResult,
    XrayBatchResult,
    XrayConnectionStatus,
    XrayConversionResult,
    XrayCreateResult,
    XrayMappingTemplate,
    XraySearchResult,
    XrayTestSummary,
)
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

logger = logging.getLogger("qa-mcp")

# PROMPT_REGISTRY is a table of factories; the values are untyped at the table.
PromptFactory = Callable[..., dict[str, Any]]

RiskLevel = Literal["low", "medium", "high", "critical"]
TestType = Literal["Manual", "Automated", "Generic"]
SourceFormat = Literal["auto", "markdown", "gherkin", "json", "plain"]
SuiteTarget = Literal["smoke", "sanity", "regression", "e2e", "integration", "performance"]

# Values the qa://examples/{quality} template accepts.
EXAMPLE_QUALITIES = ("good", "bad")

# Completion suggestions for free-text prompt arguments.
PROMPT_ARGUMENT_SUGGESTIONS: dict[str, list[str]] = {
    "max_duration": ["15", "30", "60", "120"],
}

# Pre-1.0.3 dotted names, published only when legacy_tool_aliases is on.
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

# Every analysis tool is a pure transformation of its arguments: nothing is
# persisted, no external system is contacted, and repeating a call changes
# nothing. Declaring that lets clients skip the approval prompts they show for
# tools that might mutate state.
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

# Jira reads leave the tenant untouched but do reach an external system.
REMOTE_READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

# Creating an issue is additive rather than destructive, but it is neither
# read-only nor idempotent: calling twice creates two issues.
REMOTE_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


# ==============================================================================
# Audit logging
# ==============================================================================


class AuditExtension(Extension):
    """Log every tool invocation.

    mcp 2.x has no central dispatch to hang this off, so it is an interceptor.
    Argument *names* are recorded but never their values: a test case payload
    can be large, and an Xray argument can be sensitive.
    """

    # SEP-2133 requires a reverse-DNS vendor prefix on extension identifiers.
    identifier = "com.atakanemre.qa-mcp/audit"

    async def intercept_tool_call(
        self,
        params: CallToolRequestParams,
        ctx: Any,
        call_next: CallNext,
    ) -> HandlerResult:
        if not get_settings().audit_log_enabled:
            return await call_next(ctx)

        started = datetime.now()
        entry: dict[str, Any] = {
            "timestamp": started.isoformat(),
            "tool": params.name,
            "argument_names": sorted(params.arguments or {}),
        }
        try:
            result = await call_next(ctx)
        except Exception as exc:
            self._log(entry, started, outcome="error", error_type=type(exc).__name__)
            raise

        # A failing tool usually does not reach here as an exception: the
        # runtime converts it into a result carrying isError below this
        # interceptor. Reading the flag is what makes the audit trail honest.
        failed = bool(getattr(result, "isError", None) or getattr(result, "is_error", None))
        self._log(entry, started, outcome="error" if failed else "ok")
        return result

    @staticmethod
    def _log(
        entry: dict[str, Any],
        started: datetime,
        *,
        outcome: str,
        error_type: str | None = None,
    ) -> None:
        entry["outcome"] = outcome
        if error_type:
            entry["error_type"] = error_type
        entry["duration_ms"] = round((datetime.now() - started).total_seconds() * 1000, 1)
        logger.info(f"AUDIT: {json.dumps(entry, ensure_ascii=False)}")


# ==============================================================================
# Server
# ==============================================================================

mcp: MCPServer = MCPServer(
    name="qa-mcp",
    title="QA-MCP",
    version=__version__,
    instructions=(
        "QA-MCP standardizes manual test cases. Generate test cases from acceptance "
        "criteria, lint them against a shared quality standard, normalize Gherkin/"
        "Markdown/JSON into the canonical schema, compose suites, and convert to Xray."
    ),
    extensions=[AuditExtension()],
)


# ==============================================================================
# Tools - test case authoring
# ==============================================================================


@mcp.tool(title="Test Case Üret", annotations=READ_ONLY)
def testcase_generate(
    feature: str,
    acceptance_criteria: list[str],
    module: str | None = None,
    risk_level: RiskLevel = "medium",
    include_negative: bool = True,
    include_boundary: bool = True,
) -> GenerateResult:
    """Feature açıklaması ve acceptance criteria'dan standart test case üretir."""
    return GenerateResult.model_validate(
        generate_testcase(
            feature=feature,
            acceptance_criteria=acceptance_criteria,
            module=module,
            risk_level=risk_level,
            include_negative=include_negative,
            include_boundary=include_boundary,
        )
    )


@mcp.tool(title="Test Case Kalite Analizi", annotations=READ_ONLY)
def testcase_lint(
    testcase: dict[str, Any],
    include_improvement_plan: bool = True,
    strict_mode: bool = False,
) -> LintResult:
    """Test case'i analiz eder, kalite skoru ve iyileştirme önerileri döner."""
    return LintResult.model_validate(
        lint_testcase(
            testcase=testcase,
            include_improvement_plan=include_improvement_plan,
            strict_mode=strict_mode,
        )
    )


@mcp.tool(title="Toplu Kalite Analizi", annotations=READ_ONLY)
def testcase_lint_batch(
    testcases: list[dict[str, Any]],
    strict_mode: bool = False,
) -> LintBatchResult:
    """Birden fazla test case'i toplu analiz eder ve toplu istatistik döner."""
    return LintBatchResult.model_validate(
        lint_batch(testcases=testcases, include_improvement_plan=False, strict_mode=strict_mode)
    )


@mcp.tool(title="Test Case Normalleştir", annotations=READ_ONLY)
def testcase_normalize(
    input_data: str | dict[str, Any],
    source_format: SourceFormat = "auto",
) -> NormalizeResult:
    """Markdown, Gherkin, JSON veya düz metni QA-MCP standardına çevirir."""
    return NormalizeResult.model_validate(
        normalize_testcase(input_data=input_data, source_format=source_format)
    )


# ==============================================================================
# Tools - Xray conversion
# ==============================================================================


@mcp.tool(title="Xray Formatına Dönüştür", annotations=READ_ONLY)
def testcase_to_xray(
    testcase: dict[str, Any],
    project_key: str | None = None,
    test_type: TestType | None = None,
    include_custom_fields: bool = True,
    custom_field_mappings: dict[str, str] | None = None,
) -> XrayConversionResult:
    """Standart test case'i Xray import formatına dönüştürür.

    project_key ve custom_field_mappings verilmezse yapılandırılmış tenant
    değerleri kullanılır.
    """
    settings = get_settings()
    key = project_key or settings.xray.project_key
    if not key:
        raise ValueError(
            "project_key gerekli. Argüman olarak verin veya QA_MCP_XRAY_PROJECT_KEY ayarlayın."
        )

    return XrayConversionResult.model_validate(
        convert_to_xray(
            testcase=testcase,
            project_key=key,
            test_type=test_type,
            include_custom_fields=include_custom_fields,
            custom_field_mappings=custom_field_mappings or settings.xray.custom_fields or None,
        )
    )


@mcp.tool(title="Toplu Xray Dönüşümü", annotations=READ_ONLY)
def testcase_to_xray_batch(
    testcases: list[dict[str, Any]],
    project_key: str | None = None,
    test_type: TestType | None = None,
) -> XrayBatchResult:
    """Birden fazla test case'i toplu olarak Xray formatına dönüştürür."""
    settings = get_settings()
    key = project_key or settings.xray.project_key
    if not key:
        raise ValueError(
            "project_key gerekli. Argüman olarak verin veya QA_MCP_XRAY_PROJECT_KEY ayarlayın."
        )

    return XrayBatchResult.model_validate(
        convert_batch_to_xray(
            testcases=testcases,
            project_key=key,
            test_type=test_type,
            custom_field_mappings=settings.xray.custom_fields or None,
        )
    )


@mcp.tool(title="Xray Alan Eşleme Şablonu", annotations=READ_ONLY)
def xray_get_mapping_template() -> XrayMappingTemplate:
    """Xray alan eşleme şablonunu döner."""
    return XrayMappingTemplate.model_validate(get_xray_field_mapping_template())


# ==============================================================================
# Tools - suites
# ==============================================================================


@mcp.tool(title="Test Suite Oluştur", annotations=READ_ONLY)
def suite_compose(
    testcases: list[dict[str, Any]],
    target: SuiteTarget,
    sprint: str | None = None,
    max_duration_minutes: int | None = None,
) -> SuiteCompositionResult:
    """Test case listesinden Smoke/Sanity/Regression/E2E/Integration/Performance suite oluşturur."""
    return SuiteCompositionResult.model_validate(
        compose_suite(
            testcases=testcases,
            target=target,
            sprint=sprint,
            max_duration_minutes=max_duration_minutes,
        )
    )


@mcp.tool(title="Kapsam Raporu", annotations=READ_ONLY)
def suite_coverage_report(
    testcases: list[dict[str, Any]],
    requirements: list[str] | None = None,
    modules: list[str] | None = None,
) -> CoverageReportResult:
    """Test case koleksiyonu için gereksinim ve modül kapsam raporu üretir."""
    return CoverageReportResult.model_validate(
        coverage_report(testcases=testcases, requirements=requirements, modules=modules)
    )


# ==============================================================================
# Tools - Jira/Xray tenant (registered only when configured)
# ==============================================================================


def _xray_client() -> Any:
    """Build a client for the configured tenant.

    Imported lazily so an offline deployment never imports httpx machinery it
    does not use.
    """
    from qa_mcp.integrations.xray import XrayClient

    return XrayClient(get_settings())


def xray_verify_connection() -> XrayConnectionStatus:
    """Jira/Xray bağlantısını ve kimlik bilgilerini doğrular.

    Token verildikten sonra çalıştırılacak ilk tool budur.
    """
    with _xray_client() as client:
        return XrayConnectionStatus.model_validate(client.verify_connection())


def xray_get_test(issue_key: str) -> XrayTestSummary:
    """Jira'dan tek bir Xray test issue'sunu getirir."""
    with _xray_client() as client:
        return XrayTestSummary.model_validate(client.get_test(issue_key))


def xray_search_tests(
    jql: str | None = None,
    project_key: str | None = None,
    max_results: int = 50,
) -> XraySearchResult:
    """Xray test issue'larını JQL ile arar; jql verilmezse projedeki testleri listeler."""
    with _xray_client() as client:
        return XraySearchResult.model_validate(
            client.search_tests(jql=jql, project_key=project_key, max_results=max_results)
        )


def xray_create_test(xray_payload: dict[str, Any]) -> XrayCreateResult:
    """Jira'da yeni bir Xray test issue'su OLUŞTURUR.

    testcase_to_xray çıktısını girdi olarak alır. Bu tool Jira'da kalıcı
    değişiklik yapar ve yalnızca QA_MCP_ENABLE_WRITE_TOOLS=true iken kayıtlıdır.
    """
    with _xray_client() as client:
        return XrayCreateResult.model_validate(client.create_test(xray_payload))


def register_optional_tools(settings: Settings | None = None) -> list[str]:
    """Register the tools whose availability depends on configuration.

    Returns the names registered, so startup can report exactly what a given
    deployment exposes.
    """
    settings = settings or get_settings()
    registered: list[str] = []
    existing = {tool.name for tool in mcp._tool_manager.list_tools()}

    def _add(fn: Callable[..., Any], name: str, title: str, annotations: ToolAnnotations) -> None:
        """Register a tool unless it is already there.

        A host may build the server more than once, and `main()` runs this
        after `--check-config` has already done so; re-registering a tool would
        either warn or replace it.
        """
        if name in existing:
            return
        mcp.add_tool(fn, name=name, title=title, annotations=annotations)
        existing.add(name)
        registered.append(name)

    if settings.xray.is_configured:
        for fn, title in (
            (xray_verify_connection, "Xray Bağlantısını Doğrula"),
            (xray_get_test, "Xray Testini Getir"),
            (xray_search_tests, "Xray Testlerini Ara"),
        ):
            _add(fn, fn.__name__, title, REMOTE_READ)

        if settings.enable_write_tools:
            _add(xray_create_test, "xray_create_test", "Xray Testi Oluştur", REMOTE_WRITE)

    if settings.legacy_tool_aliases:
        analysis_tools: dict[str, Callable[..., Any]] = {
            "testcase_generate": testcase_generate,
            "testcase_lint": testcase_lint,
            "testcase_lint_batch": testcase_lint_batch,
            "testcase_normalize": testcase_normalize,
            "testcase_to_xray": testcase_to_xray,
            "testcase_to_xray_batch": testcase_to_xray_batch,
            "suite_compose": suite_compose,
            "suite_coverage_report": suite_coverage_report,
            "xray_get_mapping_template": xray_get_mapping_template,
        }
        for alias, canonical in TOOL_NAME_ALIASES.items():
            _add(
                analysis_tools[canonical],
                alias,
                f"{canonical} (deprecated alias)",
                READ_ONLY,
            )

    return registered


# ==============================================================================
# Resources
# ==============================================================================


def _as_json(payload: Any) -> str:
    """Serialize a resource, keeping non-ASCII text readable."""
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.resource(
    "qa://standards/testcase/v1",
    name="Test Case Standard v1",
    title="Test Case Standardı",
    description="Kurumsal test case yazım standardı",
    mime_type="application/json",
)
def standard_resource() -> str:
    return _as_json(get_testcase_standard())


@mcp.resource(
    "qa://checklists/lint-rules/v1",
    name="Lint Rules v1",
    title="Lint Kuralları",
    description="Test case kalite kontrol kuralları ve puanlama",
    mime_type="application/json",
)
def lint_rules_resource() -> str:
    return _as_json(get_lint_rules())


@mcp.resource(
    "qa://mappings/xray/v1",
    name="Xray Field Mapping v1",
    title="Xray Alan Eşlemesi",
    description="QA-MCP to Xray alan eşlemeleri",
    mime_type="application/json",
)
def xray_mapping_resource() -> str:
    return _as_json(get_xray_mapping())


@mcp.resource(
    "qa://examples/{quality}",
    name="Test Case Examples",
    title="Test Case Örnekleri",
    description="Kalite seviyesine göre örnek test case'ler (good, bad)",
    mime_type="application/json",
)
def examples_resource(quality: str) -> str:
    """Serve the good or bad example collection.

    In mcp 1.x these were two fixed resources plus a hand-written template and
    a URI dispatch table; the runtime now matches the pattern.
    """
    if quality == "good":
        return _as_json(get_good_examples())
    if quality == "bad":
        return _as_json(get_bad_examples())
    raise ValueError(f"Bilinmeyen örnek türü: {quality!r}. Geçerli: {', '.join(EXAMPLE_QUALITIES)}")


# ==============================================================================
# Prompts
# ==============================================================================


def _parse_list_argument(value: str | list[str] | None) -> list[str] | None:
    """Coerce a prompt argument that should be a list.

    The MCP wire format carries prompt arguments as strings, and mcp 2.x does
    not parse them: a ``list[str]`` parameter raises on the JSON string a client
    actually sends. So the parameters stay ``str`` and are decoded here, falling
    back to a single-item list for a plain string.
    """
    if value is None or isinstance(value, list):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _parse_object_list_argument(value: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Coerce a prompt argument that should be a list of test cases."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


@mcp.prompt(name="create-manual-test", title="Manuel Test Oluştur")
def create_manual_test(feature: str | None = None, acceptance_criteria: str | None = None) -> str:
    """Feature ve kabul kriterlerinden standart manuel test case üretme şablonu."""
    return cast(PromptFactory, PROMPT_REGISTRY["create-manual-test"])(
        feature=feature,
        acceptance_criteria=_parse_list_argument(acceptance_criteria),
    )["prompt"]


@mcp.prompt(name="select-smoke-tests", title="Smoke Test Seç")
def select_smoke_tests(testcases: str | None = None, max_duration: str | None = None) -> str:
    """Test case listesinden smoke suite seçme şablonu."""
    kwargs: dict[str, Any] = {"testcases": _parse_object_list_argument(testcases)}
    if max_duration:
        try:
            kwargs["max_duration"] = int(max_duration)
        except ValueError:
            pass
    return cast(PromptFactory, PROMPT_REGISTRY["select-smoke-tests"])(**kwargs)["prompt"]


@mcp.prompt(name="generate-negative-scenarios", title="Negatif Senaryo Üret")
def generate_negative_scenarios(
    feature: str | None = None, positive_testcases: str | None = None
) -> str:
    """Mevcut pozitif test case'lerden negatif senaryo üretme şablonu."""
    return cast(PromptFactory, PROMPT_REGISTRY["generate-negative-scenarios"])(
        feature=feature,
        positive_testcases=_parse_object_list_argument(positive_testcases),
    )["prompt"]


@mcp.prompt(name="review-test-coverage", title="Kapsamı İncele")
def review_test_coverage(testcases: str | None = None, requirements: str | None = None) -> str:
    """Test kapsamını gereksinimlere karşı inceleme şablonu."""
    return cast(PromptFactory, PROMPT_REGISTRY["review-test-coverage"])(
        testcases=_parse_object_list_argument(testcases),
        requirements=_parse_list_argument(requirements),
    )["prompt"]


# ==============================================================================
# Completion
# ==============================================================================


@mcp.completion()
async def complete_argument(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None = None,
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


# ==============================================================================
# Entry point
# ==============================================================================


def configure_logging(settings: Settings) -> None:
    """Send logs to stderr; stdout carries the MCP protocol."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    """Main entry point for the QA-MCP server."""
    parser = argparse.ArgumentParser(
        prog="qa-mcp",
        description="QA-MCP server (Model Context Protocol) for test case generation and QA tooling.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate the configuration, report what would be exposed, and exit.",
    )
    args = parser.parse_args()

    try:
        # The process entry point defines the configuration, so read the
        # environment now rather than trusting whatever an earlier import may
        # already have cached.
        settings = reload_settings()
    except Exception as exc:  # configuration errors must be readable, not a traceback
        parser.exit(2, f"Yapılandırma hatası:\n{exc}\n")

    configure_logging(settings)

    if args.check_config:
        optional = register_optional_tools(settings)
        report = {
            "version": __version__,
            "configuration": settings.describe(),
            "optional_tools": optional,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    logger.info(f"Starting QA-MCP Server v{__version__}")
    logger.info(f"Configuration: {json.dumps(settings.describe(), ensure_ascii=False)}")
    optional = register_optional_tools(settings)
    if optional:
        logger.info(f"Optional tools registered: {', '.join(optional)}")

    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
