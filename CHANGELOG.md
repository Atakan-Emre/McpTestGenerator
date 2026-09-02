# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [2.0.0] - 2026-09-02

Migrates to the mcp 2.x SDK and makes QA-MCP configurable for an organisation
that wants to point it at its own Jira/Xray tenant and its own quality bar.

### Breaking
- **Requires the mcp 2.x SDK** (`mcp>=2.1.0,<3.0.0`). The server is rebuilt on
  `MCPServer`; the 1.x decorator API it used no longer exists
- Result attribute names follow the SDK's move to snake_case
  (`input_schema`, `output_schema`, `is_error`, `structured_content`). The wire
  format is unchanged, so MCP clients are unaffected; code driving the server
  as a library is not
- The pre-1.0.3 dotted tool aliases (`testcase.lint`, ...) are no longer
  published by default. Set `QA_MCP_LEGACY_TOOL_ALIASES=true` to restore them
- Environment variables are namespaced: `QA_MCP_LOG_LEVEL`,
  `QA_MCP_AUDIT_LOG_ENABLED`, `QA_MCP_ENABLE_WRITE_TOOLS`. The unprefixed 1.x
  spellings are still accepted so existing deployments keep working
- `ENABLE_WRITE_TOOLS` is no longer inert: it publishes a tool that writes to
  Jira and is rejected at startup unless a tenant is configured

### Added

#### Enterprise configuration
- `qa_mcp.config`: typed, environment-driven settings for the server, the
  quality gate and the Jira/Xray tenant. A contradictory configuration is
  rejected at startup with a message naming the variable, rather than failing
  on the first tool call
- `qa-mcp --check-config` validates the configuration, reports what the
  deployment would expose, and exits non-zero when it is wrong
- Credentials are held as `SecretStr`: absent from `repr()`, from
  `--check-config` output and from error details

#### Jira/Xray integration
- `xray_verify_connection`, `xray_get_test`, `xray_search_tests` — read-only,
  published only once a tenant is configured
- `xray_create_test` — published only when writes are explicitly enabled, and
  re-checked inside the client so a registration mistake cannot reach a write
- Jira Cloud (`basic`) and Server/Data Center (`token`) authentication, with
  per-tenant custom field mappings and a configurable API version

#### Configurable quality gate
- `QA_MCP_LINT_MINIMUM_SCORE`, `QA_MCP_LINT_STRICT_MINIMUM_SCORE` and
  `QA_MCP_LINT_MAX_STEPS`
- `QA_MCP_LINT_DISABLED_RULES` switches rules off and refunds their score by
  exactly the penalty published in the lint-rules resource, so a disabled rule
  does not keep costing points

#### Core
- `qa_mcp.core.results`: Pydantic result models are now the single definition of
  what a tool returns. The published `outputSchema` is generated from them,
  replacing hand-written JSON Schemas that could drift from the code
- Audit logging moved to an MCP extension interceptor, and reports a failed call
  as an error — the runtime converts a raising tool into an error result below
  the interceptor, so catching exceptions alone had logged it as a success
- Argument *names* are audited; argument values never are

#### CI/CD
- Every organisation-specific name in the Jenkins pipeline is a build parameter
  with a default: SonarQube server, scanner tool, project key, interpreter,
  Docker registry and credentials id. Image publishing is opt-in
- `make check-config`, and a `sonar` target that requires `SONAR_HOST_URL` and
  `SONAR_TOKEN` rather than assuming them

### Documentation
- `docs/ENTERPRISE-SETUP.md`: connecting a tenant, enabling writes, setting a
  quality bar, credential handling and troubleshooting
- `.env.example`, kept in step with the settings models by a test

---

## [1.1.0] - 2026-09-02

### Fixed
- Pinned `mcp` to `>=1.9.0,<2.0.0`. The previous unbounded `mcp>=1.0.0` let a
  fresh install resolve to mcp 2.x, which removed the decorator-based low-level
  server API, so the server crashed at import with
  `AttributeError: 'Server' object has no attribute 'list_tools'`
- Fixed every MCP resource being unreadable. `read_resource` compared the
  runtime's `AnyUrl` argument against string keys, so all five `qa://` resources
  failed with `Unknown resource`. URIs are now normalized (trailing slash
  tolerated) before lookup
- Fixed `testcase_lint` being unable to lint substandard test cases. Strict
  Pydantic validation aborted before any rule ran, so every test case that
  violated the standard — including the shipped `qa://examples/bad`
  anti-patterns — came back as score 0 with a raw validation dump instead of
  actionable issues. Linting now runs against a permissive `TestCaseDraft`
  model, and standard conformance is reported separately
- The MCP handshake now reports the QA-MCP version instead of the MCP SDK's

- `testcase_generate` crashing on short input. A brief feature and criterion
  produced a title under the standard's 10-character minimum, which failed
  validation and took the whole call down
- `testcase_normalize` returning `null` plus a raw Pydantic error whenever the
  source content fell short of the standard (short Markdown titles, one-word
  plain text). All formats now go through a single promotion step that pads what
  is missing and reports every adjustment
- `testcase_to_xray` silently dropping `expected_result`: Xray has no field for
  it, and the warning claimed it had been folded into the description when it
  had not. It is now rendered into the description body
- `testcase_to_xray` warning about `scenario_type`, `risk_level` and `test_type`
  on every single conversion. Those fields always hold a default, so the
  "unmapped" report fired unconditionally; the report now separates fields
  embedded in the description from genuinely unmapped ones
- `testcase_to_xray` ignoring the test case's own `test_type` and always
  emitting `Manual` unless the caller passed an override
- `suite_compose` raising an uncaught `ValueError` for an unrecognised target,
  and silently applying regression rules to `integration` and `performance`
- `suite_coverage_report` discarding malformed test cases with a bare
  `except: continue`, so the reported percentages excluded them without saying
  so. Skipped cases are now returned in `skipped_testcases`
- The `resources/` directory shipped as dead weight. `load_resource_file()` was
  never called and its path resolved outside an installed package, so the JSON
  was unreachable while a hand-maintained duplicate in
  `resources/standards.py` served the actual content - and the two had already
  drifted apart. The JSON is now the single source of truth, packaged under
  `qa_mcp/resources/data/` and read through `importlib.resources`
- Broken documentation links in README: they pointed at `google.com/search?q=`
  instead of the files

### Changed
- Enhanced README badges with CI status and code coverage
- `qa://standards/testcase/v1`, `qa://checklists/lint-rules/v1` and
  `qa://mappings/xray/v1` now serve the fuller JSON definitions that were
  previously unreachable, replacing the abridged in-code copies
- `convert_to_xray(test_type=...)` defaults to `None`, meaning "use the test
  case's own `test_type`", instead of hardcoding `"Manual"`
- The `call_tool` handler returns a `dict` (structured content) rather than a
  list of `TextContent`; MCP clients are unaffected, direct library callers
  should read the result dict instead of parsing `result[0].text`
- The `BAD-002` example's title now really exceeds 200 characters, as its own
  documented problem list always claimed

### Removed
- The repository-level `resources/` directory and the unused
  `load_resource_file()` helper; the content moved into the package

### Added

#### MCP protocol revision 2025-11-25
- `outputSchema` on all nine tools, so results are returned as validated
  `structuredContent` instead of a JSON string the client has to parse
- `ToolAnnotations` on all nine tools (`readOnlyHint`, `destructiveHint`,
  `idempotentHint`, `openWorldHint`) — every QA-MCP tool is a pure function
- `title` display names on tools, resources and prompts
- `qa://examples/{quality}` resource template plus a completion handler for its
  argument and for prompt arguments
- Failed tool calls now set `isError`; previously a failure was returned as a
  successful result whose payload happened to mention an error
- `integration` and `performance` suite targets, with their own selection rules

#### CI/CD
- `Jenkinsfile`: declarative pipeline with static analysis, tests, security
  scanning, SonarQube analysis and a blocking quality gate
- `sonar-project.properties` importing the Ruff, MyPy, Bandit, coverage and
  JUnit reports the build produces
- `Makefile` exposing every CI stage as a local target, so a failing build is
  reproducible with the same command
- `docker-compose.sonarqube.yml` for a local SonarQube instance
- `docs/CI-CD.md` documenting the required plugins and configuration
- `ci` optional-dependency group (bandit, pip-audit, build)
- `tests/test_ci_config.py` asserting the cross-references between the
  Jenkinsfile, Makefile and SonarQube configuration

#### Lint rules
- `test_data.hardcoded_credentials` (error): a credential-shaped literal in the
  executable flow. The shipped `BAD-003` anti-pattern documents this as a
  security risk, but no rule caught it - it scored 89/B
- `test_data.hardcoded_identity` (warning): an identifier such as an email
  inlined into a step without being declared as test data
- `test_data.not_parameterized` (warning): literal values in steps with no
  `test_data` at all, so the test only ever works for one data set

Preconditions are exempt: naming the test account there is normal practice, the
smell is a literal baked into the steps. `BAD-003` now scores 57/F.

#### Core
- `TestCaseDraft` / `TestStepDraft`: permissive models for quality analysis.
  `TestCase` is now a strict subclass that re-declares the standard's constraints
- `schema_valid` and `schema_errors` fields on `testcase_lint` responses
- `title.max_length` lint rule (over-long titles were documented as a defect but
  had no rule)
- Regression tests for the MCP resource and prompt handlers, exercised through
  the SDK types the runtime actually passes
- Pre-commit hooks configuration for automated code quality checks
- Comprehensive CONTRIBUTING.md guide
- Dependency locking with uv

### Documentation
- `docs/CI-CD.md`: Jenkins and SonarQube setup, required plugins, and the
  report contract between the Makefile, the pipeline and Sonar
- `docs/MCP-2.x-MIGRATION.md`: migration plan for the mcp 2.x SDK, with every
  API difference verified against mcp 2.1.1 rather than taken from release notes
- Documented the `integration` and `performance` suite targets and the new
  `schema_valid` lint response fields in USAGE.md
- Added PyPI publishing workflow and documentation
- Created GitHub release template
- Aligned core documentation with the shipped stdio-only runtime model and public MCP surface

---

## [1.0.4] - 2026-04-14

### Fixed
- Formatted the MCP server module to satisfy the strict Ruff formatting gate in CI
- Rolled forward the Claude Desktop-compatible tool name release into a clean `1.0.4` publish target

### Documentation
- Synchronized PyPI, Docker, compose, and publishing references to `1.0.4`

---

## [1.0.3] - 2026-04-14

### Fixed
- Renamed public MCP tool names to underscore format so Claude Desktop accepts the server tool list
- Preserved backward compatibility by continuing to accept legacy dotted tool aliases on tool calls
- Synchronized PyPI package version, Docker image metadata, and compose defaults to `1.0.3`

### Documentation
- Updated README, usage guide, prompt templates, and Docker Hub description to reflect Claude-safe tool names

---

## [1.0.2] - 2026-04-03

### Fixed
- Preserved `labels` when JSON normalization falls back to manual field mapping
- Corrected plain-text normalization for short freeform notes
- Corrected Gherkin parsing so `And` lines after `When` remain part of the action flow
- Fixed Xray custom field mapping for `estimated_duration_minutes`
- Synchronized PyPI package version and Docker image metadata to `1.0.2`

### Documentation
- Rewrote README in bilingual English/Turkish format with accurate runtime, roadmap, and capability coverage
- Updated usage, Docker, and publishing guides to match the shipped MCP surface and release flow

---

## [1.0.0] - 2025-01-15

### Added

- Initial release of QA-MCP
- **Tools:**
  - `testcase.generate` - Feature açıklamasından test case üretimi
  - `testcase.lint` - Test case kalite analizi ve skorlama
  - `testcase.normalize` - Farklı formatları standarda çevirme
  - `testcase.to_xray` - Xray import formatına dönüştürme
  - `suite.compose` - Smoke/Regression/E2E suite kompozisyonu
  - `suite.coverage_report` - Kapsama raporu oluşturma
- **Resources:**
  - `qa://standards/testcase/v1` - Test case standardı
  - `qa://checklists/lint-rules/v1` - Lint kuralları
  - `qa://mappings/xray/v1` - Xray alan eşlemesi
  - `qa://examples/good` - İyi test case örnekleri
  - `qa://examples/bad` - Kötü test case örnekleri
- **Prompts:**
  - `create-manual-test` - Manual test oluşturma şablonu
  - `select-smoke-tests` - Smoke test seçim şablonu
  - `generate-negative-scenarios` - Negatif senaryo üretim şablonu
  - `review-test-coverage` - Kapsam analizi şablonu
- **Infrastructure:**
  - Docker multi-arch support (amd64/arm64)
  - stdio transport (default)
  - Audit logging
  - Environment-based configuration

### Security

- Default stdio-only transport for maximum security
- Tool allowlist approach
- Parameter validation on all inputs
- Audit logging for all tool invocations
