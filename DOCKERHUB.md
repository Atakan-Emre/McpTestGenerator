# QA-MCP

[![CI](https://github.com/Atakan-Emre/McpTestGenerator/workflows/CI/badge.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![Docker Pulls](https://img.shields.io/docker/pulls/atakanemree/qa-mcp.svg)](https://hub.docker.com/r/atakanemree/qa-mcp)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Atakan-Emre/McpTestGenerator/blob/main/LICENSE)

QA-MCP is a Model Context Protocol server for structured QA work. It helps MCP clients generate standardized test cases, lint them against a shared schema, normalize existing material, export Xray-compatible payloads, and compose suites from existing test assets.

## Runtime Model

- Transport: `stdio` only
- Network ports: none exposed by the application runtime
- Intended usage: MCP client launches the container as a subprocess

Current container images do not provide an active HTTP server mode.

## Quick Start

```bash
# Pull the latest published image
docker pull atakanemree/qa-mcp:latest

# Verify the packaged CLI
docker run --rm atakanemree/qa-mcp:latest --version

# Run the MCP server in stdio mode
docker run --rm -i atakanemree/qa-mcp:latest
```

## MCP Client Configuration

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "atakanemree/qa-mcp:latest"]
    }
  }
}
```

## Public Capability Summary

| Tool | Purpose |
|------|---------|
| `testcase_generate` | Generate standardized test cases |
| `testcase_lint` | Lint a single test case |
| `testcase_lint_batch` | Lint multiple test cases |
| `testcase_normalize` | Normalize Gherkin, Markdown, JSON, or plain text |
| `testcase_to_xray` | Convert a single test case to Xray payload |
| `testcase_to_xray_batch` | Convert multiple test cases to Xray payloads |
| `suite_compose` | Compose smoke, sanity, regression, or E2E suites |
| `suite_coverage_report` | Report requirement and module coverage |
| `xray_get_mapping_template` | Return Xray mapping guidance |

## Effective Runtime Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `info` | Application log level |
| `AUDIT_LOG_ENABLED` | `true` | Enables audit logging |

## Published Tags

| Tag | Meaning |
|-----|---------|
| `latest` | Most recent stable image |
| `1.0.4` | Current stable release |
| `1.0` | Major/minor convenience tag |
| `1` | Major convenience tag |

## Security Posture

- Runs as non-root user in the production image
- Uses `stdio` as the primary transport
- Does not expose write-capable Jira/Xray sync in the current release

## Documentation

- GitHub repository: [Atakan-Emre/McpTestGenerator](https://github.com/Atakan-Emre/McpTestGenerator)
- README: [README.md](https://github.com/Atakan-Emre/McpTestGenerator#readme)
- Usage guide: [USAGE.md](https://github.com/Atakan-Emre/McpTestGenerator/blob/main/USAGE.md)
- PyPI package: [qa-mcp](https://pypi.org/project/qa-mcp/)

## Maintainer

Atakan Emre
GitHub: [@Atakan-Emre](https://github.com/Atakan-Emre)
