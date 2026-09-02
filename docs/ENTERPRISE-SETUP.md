# Enterprise setup

QA-MCP runs with no configuration at all: the nine analysis tools are pure
functions that never touch the network. This guide is for connecting it to your
own Jira/Xray tenant and holding it to your own quality standard.

Everything is environment-driven. There is no config file to fork and no code to
edit.

```bash
qa-mcp --check-config
```

validates what you have set, prints what the server would expose, and exits
non-zero on a bad configuration — run it before wiring QA-MCP into a client.

---

## 1. Start offline

```bash
pip install qa-mcp
qa-mcp --check-config
```

```json
{
  "configuration": {
    "xray": { "enabled": false, "configured": false, "credentials": "unset" },
    "write_tools_enabled": false
  },
  "optional_tools": []
}
```

Nine tools, five resources, four prompts. Nothing leaves the process.

---

## 2. Connect a Jira/Xray tenant

Copy [`.env.example`](../.env.example) to `.env`, or set the variables directly
— in Docker and Kubernetes you want the latter.

### Jira Cloud

```bash
QA_MCP_XRAY_ENABLED=true
QA_MCP_XRAY_BASE_URL=https://your-tenant.atlassian.net
QA_MCP_XRAY_API_VERSION=3
QA_MCP_XRAY_AUTH_MODE=basic
QA_MCP_XRAY_EMAIL=qa-automation@your-company.com
QA_MCP_XRAY_API_TOKEN=<token>
QA_MCP_XRAY_PROJECT_KEY=QA
```

Create the token at
<https://id.atlassian.com/manage-profile/security/api-tokens>. Jira Cloud
authenticates an API token with the account email, which is why `auth_mode` is
`basic` rather than `token`.

### Jira Server / Data Center

```bash
QA_MCP_XRAY_ENABLED=true
QA_MCP_XRAY_BASE_URL=https://jira.internal.your-company.com
QA_MCP_XRAY_API_VERSION=2
QA_MCP_XRAY_AUTH_MODE=token
QA_MCP_XRAY_API_TOKEN=<personal access token>
QA_MCP_XRAY_PROJECT_KEY=QA
```

### Verify

```bash
qa-mcp --check-config
```

```json
{
  "configuration": {
    "xray": {
      "enabled": true, "configured": true,
      "base_url": "https://your-tenant.atlassian.net",
      "auth_mode": "basic", "project_key": "QA",
      "credentials": "set"
    }
  },
  "optional_tools": ["xray_verify_connection", "xray_get_test", "xray_search_tests"]
}
```

Three read-only tools appeared. Then, from your MCP client, call
`xray_verify_connection` — it reports which account the token belongs to.

A configuration that is switched on but incomplete is rejected **at startup**,
not on the first tool call:

```
Yapılandırma hatası:
  QA_MCP_XRAY_ENABLED is true but QA_MCP_XRAY_API_TOKEN is not set.
  Set them, or leave QA_MCP_XRAY_ENABLED unset to run QA-MCP offline.
```

### Custom fields

Xray custom field ids differ per tenant, so they cannot ship as defaults. Read
them from your Jira administration screen and map them by QA-MCP field name:

```bash
QA_MCP_XRAY_CUSTOM_FIELDS={"risk_level":"customfield_10001","scenario_type":"customfield_10002"}
```

`testcase_to_xray` then uses them without the caller having to pass anything.
`xray_get_mapping_template` lists which QA-MCP fields are mappable.

---

## 3. Enable writes — deliberately

Read tools cannot change anything in Jira. Creating issues is separate and off
by default:

```bash
QA_MCP_ENABLE_WRITE_TOOLS=true
```

This publishes one additional tool, `xray_create_test`, annotated as
non-read-only so clients prompt for approval. It takes the payload
`testcase_to_xray` produced.

Two guards sit behind it:

- A configuration that enables writes without a tenant is **rejected at
  startup** — QA-MCP will not promise a write it cannot perform.
- The client checks the flag again on every write call, so a mistake in tool
  registration cannot create issues in your Jira.

Recommended: leave writes off for shared or agent-driven deployments, and enable
them only in a deployment whose token is scoped to a sandbox project.

---

## 4. Set your own quality bar

The shipped standard is a starting point, not a mandate.

```bash
# Fail anything below 75 instead of the default 60
QA_MCP_LINT_MINIMUM_SCORE=75

# Your team splits test cases sooner than the default 15 steps
QA_MCP_LINT_MAX_STEPS=10

# Rules you do not enforce; ids come from qa://checklists/lint-rules/v1
QA_MCP_LINT_DISABLED_RULES=["tags.recommended","requirements.recommended"]
```

A disabled rule raises no issue **and costs no points** — the score is refunded
by exactly the penalty published in the lint-rules resource, so a team that
switches a rule off is not quietly still penalised by it.

Raising only `QA_MCP_LINT_MINIMUM_SCORE` carries the strict threshold up with
it. Setting both to contradictory values is rejected.

---

## 5. Client configuration

### Claude Desktop

`~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "qa-mcp",
      "env": {
        "QA_MCP_XRAY_ENABLED": "true",
        "QA_MCP_XRAY_BASE_URL": "https://your-tenant.atlassian.net",
        "QA_MCP_XRAY_AUTH_MODE": "basic",
        "QA_MCP_XRAY_EMAIL": "qa-automation@your-company.com",
        "QA_MCP_XRAY_API_TOKEN": "<token>",
        "QA_MCP_XRAY_PROJECT_KEY": "QA",
        "QA_MCP_LINT_MINIMUM_SCORE": "75"
      }
    }
  }
}
```

### Docker

```bash
docker run -i --rm --env-file .env atakanemree/qa-mcp:latest
```

Pass the token through `--env-file` or your orchestrator's secret mechanism —
never bake it into an image.

---

## Credential handling

- Tokens are held as `SecretStr`: they do not appear in `repr()`, in
  `--check-config` output, or in `model_dump()`.
- The audit log records tool names and **argument names**, never argument
  values.
- Jira errors quote the status, method and path plus an actionable hint; they
  never echo the Authorization header.
- `QA_MCP_XRAY_VERIFY_TLS=false` exists for an internal CA in a test
  environment. Do not use it in production.

The `.env` file is git-ignored. `.env.example` carries no real values.

---

## Settings reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `QA_MCP_LOG_LEVEL` | `INFO` | Log level; logs go to stderr |
| `QA_MCP_AUDIT_LOG_ENABLED` | `true` | Log every tool call |
| `QA_MCP_LEGACY_TOOL_ALIASES` | `false` | Also publish the pre-1.0.3 dotted tool names |
| `QA_MCP_ENABLE_WRITE_TOOLS` | `false` | Publish `xray_create_test` |
| `QA_MCP_LINT_MINIMUM_SCORE` | `60` | Score required to pass |
| `QA_MCP_LINT_STRICT_MINIMUM_SCORE` | `75` | Score required in strict mode |
| `QA_MCP_LINT_MAX_STEPS` | `15` | Steps beyond which a case is flagged |
| `QA_MCP_LINT_DISABLED_RULES` | `[]` | Rule ids to skip, as a JSON array |
| `QA_MCP_XRAY_ENABLED` | `false` | Allow QA-MCP to contact Jira |
| `QA_MCP_XRAY_BASE_URL` | — | Jira base URL |
| `QA_MCP_XRAY_API_VERSION` | `3` | `3` for Cloud, `2` for Server/DC |
| `QA_MCP_XRAY_AUTH_MODE` | `token` | `basic` (email + token) or `token` (bearer) |
| `QA_MCP_XRAY_EMAIL` | — | Account email; required for `basic` |
| `QA_MCP_XRAY_API_TOKEN` | — | API token or PAT |
| `QA_MCP_XRAY_PROJECT_KEY` | — | Default project key |
| `QA_MCP_XRAY_TEST_ISSUE_TYPE` | `Test` | Issue type used for Xray tests |
| `QA_MCP_XRAY_CUSTOM_FIELDS` | `{}` | QA-MCP field → Jira custom field id |
| `QA_MCP_XRAY_TIMEOUT_SECONDS` | `30` | Per-request timeout |
| `QA_MCP_XRAY_MAX_RETRIES` | `2` | Connection retries |
| `QA_MCP_XRAY_VERIFY_TLS` | `true` | TLS verification |

QA-MCP 1.x read `LOG_LEVEL`, `AUDIT_LOG_ENABLED` and `ENABLE_WRITE_TOOLS`
without the prefix. Those spellings are still accepted so an existing
deployment keeps working; the prefixed names take precedence and are the
documented ones.

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `HTTP 401` from `xray_verify_connection` | Jira Cloud needs `auth_mode=basic` with the account email; a bare bearer token is for Server/DC |
| `HTTP 404` on a known issue | `QA_MCP_XRAY_API_VERSION` is wrong — `3` for Cloud, `2` for Server/DC |
| `HTTP 403` | The token authenticates but its owner lacks permission on the project |
| No `xray_*` tools listed | `QA_MCP_XRAY_ENABLED` is not `true`, or the credentials failed validation — run `qa-mcp --check-config` |
| `xray_create_test` missing | `QA_MCP_ENABLE_WRITE_TOOLS` is not `true` |
| Startup exits with code 2 | The configuration is contradictory; the message names the variable |
