# Migrating QA-MCP to the mcp 2.x SDK

Status: **planned**. QA-MCP 1.1.0 pins `mcp>=1.9.0,<2.0.0`.

Everything below was verified by running mcp `2.1.1` against QA-MCP's own tool
functions in a throwaway environment, not read from release notes. Where a
finding contradicts an assumption you might reasonably make, it is called out.

---

## Why this is a real migration, not a version bump

mcp 2.x removed the decorator API the current server is built on. `Server` still
exists at `mcp.server.lowlevel`, but `@server.list_tools()`, `@server.call_tool()`
and friends are gone — only `add_request_handler()` remains. Installing mcp 2.x
against today's code fails at import:

```
AttributeError: 'Server' object has no attribute 'list_tools'
```

The SDK says as much when you reach for the old name:

```
No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed
to MCPServer (from mcp.server.mcpserver import MCPServer)
```

---

## What changes

### 1. Programming model: dispatch table → typed functions

Today `list_tools()` returns nine hand-written `Tool` objects with hand-written
`inputSchema` dicts, and `call_tool()` is a 130-line `if/elif` chain that unpacks
`arguments` by hand.

Under 2.x a tool is a typed function and the SDK derives the schema:

```python
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

mcp = MCPServer(name="qa-mcp", title="QA-MCP", version=__version__)

READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False,
    idempotentHint=True, openWorldHint=False,
)

@mcp.tool(title="Test Case Kalite Analizi", annotations=READ_ONLY)
def testcase_lint(
    testcase: dict[str, Any],
    include_improvement_plan: bool = True,
    strict_mode: bool = False,
) -> LintResultModel:
    """Test case'i analiz eder, kalite skoru ve iyileştirme önerileri döner."""
    return lint_testcase(testcase, include_improvement_plan, strict_mode)
```

Verified: the derived schema had `required=['testcase']`, the docstring became
the description, and `title` / `annotations` / `outputSchema` were all populated.
The `if/elif` dispatch and every `inputSchema` literal go away.

### 2. Output schemas must come from Pydantic models

This is the finding that decides how much work the migration is.

| Return annotation | Resulting `output_schema` |
| --- | --- |
| `-> dict[str, Any]` | `properties: []`, `required: None` — effectively empty |
| `-> LintResultModel` (Pydantic) | `properties: [score, grade, passed, schema_valid, issues]`, `required: [score, grade, passed, schema_valid]` |

So `src/qa_mcp/core/schemas.py` — nine hand-written JSON Schemas — has to become
nine Pydantic result models, and the tool functions must return them. That is a
genuine improvement (one definition serves as both the runtime type and the
published schema) but it is the bulk of the effort. Simply returning `dict`
would silently ship empty output schemas and lose what 1.1.0 gained.

### 3. Attribute names moved from camelCase to snake_case

Wire format is unchanged; the Python attributes were renamed. Constructors still
accept the camelCase aliases (`ToolAnnotations(readOnlyHint=True)` works), but
reading them does not.

| 1.x | 2.x |
| --- | --- |
| `result.serverInfo` | `result.server_info` |
| `result.protocolVersion` | `result.protocol_version` |
| `tool.inputSchema` | `tool.input_schema` |
| `tool.outputSchema` | `tool.output_schema` |
| `annotations.readOnlyHint` | `annotations.read_only_hint` |
| `result.structuredContent` | `result.structured_content` |
| `result.isError` | `result.is_error` |
| `result.resourceTemplates` | `result.resource_templates` |

`tests/test_mcp_protocol.py` reads every one of these. It is the test file that
needs the most mechanical editing.

### 4. Templated resources become native

`list_resource_templates()` plus the manual `RESOURCE_MAP` dispatch in
`read_resource()` collapse into a URI pattern:

```python
@mcp.resource("qa://examples/{quality}", title="Test Case Örnekleri",
              mime_type="application/json")
def examples(quality: str) -> list[dict[str, Any]]:
    return get_good_examples() if quality == "good" else get_bad_examples()
```

Verified: the template was published as `qa://examples/{quality}` and
`read_resource("qa://examples/bad")` returned the right 10434-byte payload.

This also retires `_resolve_resource_uri()` — the `AnyUrl`-versus-`str` bug it
was written for cannot recur, because the SDK does the matching.

### 5. Transport

`stdio_server()` + `server.run(read, write, create_initialization_options())`
becomes `await mcp.run_stdio_async()`.

### 6. Protocol revision

mcp 2.1.1 advertises `LATEST_PROTOCOL_VERSION = 2026-07-28`, up from
`2025-11-25`. New in it is a multi-round-trip prompt flow
(`InputRequiredResult` / `ctx.input_responses`). QA-MCP has no use for it today.
Negotiation is backwards compatible — a 2.x client and this server settled on
`2025-11-25` in testing.

---

## Gotchas found by testing

**Prompt arguments are not coerced from strings.** The MCP wire format carries
prompt arguments as strings, and a typed signature does *not* parse them:

| Argument passed for `acceptance_criteria: list[str] | None` | Result |
| --- | --- |
| `["a", "b"]` (native list) | works |
| `'["a","b"]'` (JSON string, i.e. what a client actually sends) | **`ValueError: Error rendering prompt`** |
| omitted | works, `None` |

So the manual `json.loads` handling in today's `get_prompt` must be preserved —
either keep the parameters annotated as `str` and parse inside the function, or
attach a validator. Porting the signatures naively will break every prompt that
takes a list. This is the single most likely way to ship a regression.

**Legacy dotted tool names survive.** `TOOL_NAME_ALIASES` can be kept by
registering the same function twice:

```python
mcp.add_tool(testcase_lint, name="testcase_lint")
mcp.add_tool(testcase_lint, name="testcase.lint")   # verified: accepted
```

Confirm whether the aliases should still appear in `list_tools` (they would) or
whether they should be dropped at the same time — 1.0.3 introduced them purely
for Claude Desktop compatibility.

---

## What 1.1.0 already did to prepare

The concepts map one-to-one, so the migration is a re-expression rather than a
redesign:

| 1.1.0 (mcp 1.x) | 2.x equivalent |
| --- | --- |
| `OUTPUT_SCHEMAS` dict | Pydantic return models |
| Handler returns a `dict` → `structuredContent` | Same behaviour, derived from the return model |
| `ToolAnnotations` built in `_tool_annotations()` | Passed to `@mcp.tool(annotations=...)` unchanged |
| `TOOL_TITLES` table | `@mcp.tool(title=...)` |
| `list_resource_templates` + `EXAMPLE_QUALITIES` | URI pattern in `@mcp.resource` |
| `@server.completion()` | `@mcp.completion()` — same signature |
| `CallToolResult(isError=True)` | Raise; the SDK sets `is_error` |

Tool behaviour lives in `src/qa_mcp/tools/*.py` as plain functions with no MCP
imports. None of it changes.

---

## Plan

1. **Result models.** Replace `core/schemas.py` with Pydantic models. Keep the
   existing `tests/test_mcp_protocol.py::TestStructuredContent` assertions
   green against the JSON Schemas the models generate — that test is the safety
   net for the whole migration, so port it first and leave it running on 1.x.
2. **Branch and bump the pin** to `mcp>=2.1,<3`. Update
   `test_mcp_dependency_has_an_upper_bound`.
3. **Rewrite `server.py`** against `MCPServer`. Expect it to lose roughly half
   its lines: the dispatch chain, the input schemas and the resource map all go.
4. **Port the prompts**, keeping the string-parsing behaviour. Add a test that
   sends a JSON-string argument, which is what the wire actually carries.
5. **Mechanically rename** the camelCase attribute reads in the tests.
6. **Re-run the acceptance checks** already used for 1.1.0: the full suite,
   `make ci`, a clean wheel install, and a live stdio session.
7. **Decide on the legacy dotted aliases** — keep or drop, and say which in the
   changelog.

Steps 1 and 2–5 are separable: step 1 is a refactor that ships on mcp 1.x and
reduces the 2.x change to mechanical work.

## Definition of done

- `make ci` green on mcp 2.x
- Nine tools published with a non-empty `output_schema` (`properties` populated),
  a `title`, and read-only annotations
- All five `qa://` resources readable, `qa://examples/{quality}` served by the
  template
- Every prompt renders from JSON-string arguments
- Clean wheel install driven through a live stdio session, as for 1.1.0
