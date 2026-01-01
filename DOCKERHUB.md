# QA-MCP: Test Standardization & Orchestration Server

[![GitHub](https://img.shields.io/badge/GitHub-Atakan--Emre%2FMcpTestGenerator-blue?logo=github)](https://github.com/Atakan-Emre/McpTestGenerator)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Atakan-Emre/McpTestGenerator/blob/main/LICENSE)

**QA-MCP** is an **MCP (Model Context Protocol) server** that enables LLM clients (Cursor, Claude, VS Code agents, etc.) to perform **standardized test case generation, quality control (lint), Xray format conversion, and test suite composition**.

## 🚀 Quick Start

```bash
# Pull the image
docker pull atakanemree/qa-mcp:latest

# Run (stdio mode)
docker run --rm -it atakanemree/qa-mcp:latest

# Run with HTTP mode
docker run --rm -p 8080:8080 -e QA_MCP_HTTP_ENABLED=true atakanemree/qa-mcp:latest
```

## 🛠️ Features

| Tool | Description |
|------|-------------|
| `generate_testcase` | Generate standardized test cases |
| `lint_testcase` | Test case quality control (A-F grade) |
| `normalize_testcase` | Convert Gherkin/Markdown → Standard format |
| `convert_to_xray` | Export to Xray/Jira import format |
| `compose_suite` | Create Smoke/Regression/E2E test suites |
| `coverage_report` | Test coverage analysis |

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QA_MCP_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `QA_MCP_HTTP_ENABLED` | `false` | Enable HTTP server mode |
| `QA_MCP_HTTP_PORT` | `8080` | HTTP port |
| `QA_MCP_WRITE_TOOLS` | `false` | Enable write tools |
| `QA_MCP_AUDIT_LOG` | `true` | Enable audit logging |

## 📦 Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable version |
| `1.0.0` | First stable release |

## 🔗 Integration

### Cursor IDE

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

### Claude Desktop

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

## 🎯 Use Cases

- **QA Teams**: Standardize test case formats across projects
- **Developers**: Generate comprehensive test cases from requirements
- **CI/CD Pipelines**: Automate test case quality gates
- **Jira/Xray Users**: Seamless test case import to Xray

## 📚 Documentation

For detailed usage guide, visit the [GitHub Repository](https://github.com/Atakan-Emre/McpTestGenerator).

## 📄 License

MIT License - [LICENSE](https://github.com/Atakan-Emre/McpTestGenerator/blob/main/LICENSE)

## 👤 Developer

**Atakan Emre**
- GitHub: [@Atakan-Emre](https://github.com/Atakan-Emre)
