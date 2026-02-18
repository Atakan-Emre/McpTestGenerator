# QA-MCP: Test Standardization & Orchestration Server

<div align="center">

[![CI](https://github.com/Atakan-Emre/McpTestGenerator/workflows/CI/badge.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Atakan-Emre/McpTestGenerator/branch/main/graph/badge.svg)](https://codecov.io/gh/Atakan-Emre/McpTestGenerator)
[![PyPI version](https://img.shields.io/pypi/v/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![PyPI downloads](https://img.shields.io/pypi/dm/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/docker/pulls/atakanemree/qa-mcp.svg)](https://hub.docker.com/r/atakanemree/qa-mcp)

**🇬🇧 English** | [🇹🇷 Türkçe](#-türkçe)

</div>

---

# 🇬🇧 English

**An MCP server that enables LLM clients to perform standardized test case generation, quality control, Xray format conversion, and test suite composition.**

## 🎯 Problem

Common issues in enterprise QA:

- **Inconsistent test case formats**: Different people write in different formats → not reusable
- **No standard in Xray/Jira**: Missing fields, unclear datasets, ambiguous steps
- **Smoke/Regression distinction** depends on individuals: Sprint-based planning is difficult
- **When writing tests with LLM**, same suggestions return or critical negative scenarios are missed

## ✨ Solution

QA-MCP provides:

- ✅ **Single test standard**: Everyone produces/improves with the same template
- ✅ **Quality gate**: Lint score + missing field detection
- ✅ **Xray compatible output**: Importable JSON
- ✅ **Test suite/plan composition**: Smoke/Regression/E2E suggestions + tagging
- ✅ **Secure container deployment**: Runnable from Docker Hub

## 📦 Installation

### With uv (recommended)

```bash
# Install uv package manager
pip install uv

# Install qa-mcp
uv pip install qa-mcp
```

### With pip

```bash
pip install qa-mcp
qa-mcp --help
qa-mcp --version
```

### From source

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator

# Using uv (recommended - uses locked dependencies)
uv pip install -e .

# Using pip
pip install -e .
```

### With Docker

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i atakanemree/qa-mcp:latest
```

## 🚀 Usage

### MCP Client Connection

#### Cursor / Claude Desktop

Add to your `mcp.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "qa-mcp",
      "args": []
    }
  }
}
```

#### With Docker

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "atakanemree/qa-mcp:latest"]
    }
  }
}
```

## 🔧 Tools

| Tool | Description |
|------|-------------|
| `testcase.generate` | Generate standardized test cases from feature & acceptance criteria |
| `testcase.lint` | Analyze test case quality, return score and improvement suggestions |
| `testcase.normalize` | Convert Gherkin/Markdown → Standard format |
| `testcase.to_xray` | Export to Xray/Jira import format |
| `suite.compose` | Create Smoke/Regression/E2E test suites |
| `suite.coverage_report` | Generate test coverage analysis |

## 📚 Resources

| URI | Description |
|-----|-------------|
| `qa://standards/testcase/v1` | Test case standard |
| `qa://checklists/lint-rules/v1` | Lint rules |
| `qa://mappings/xray/v1` | Xray field mapping |
| `qa://examples/good/*` | Good test case examples |
| `qa://examples/bad/*` | Bad test case examples |

## 💬 Prompts

| Prompt | Description |
|--------|-------------|
| `create-manual-test` | Create Xray Manual Test |
| `select-smoke-tests` | Smoke test selection |
| `generate-negative-scenarios` | Generate negative scenarios |
| `review-test-coverage` | Test coverage analysis |

## 🐳 Docker

Published image: `atakanemree/qa-mcp` (multi-arch: `linux/amd64`, `linux/arm64`)

```bash
# Pull image
docker pull atakanemree/qa-mcp:latest

# Verify CLI
docker run --rm atakanemree/qa-mcp:latest --help

# Run (stdio mode - default, most secure)
docker run -i --rm atakanemree/qa-mcp:latest

# With environment variables
docker run -i --rm \
  -e LOG_LEVEL=debug \
  -e ENABLE_WRITE_TOOLS=false \
  atakanemree/qa-mcp:latest

# Local compose (production and dev targets)
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## 🔒 Security

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WRITE_TOOLS` | `false` | Enables Jira/Xray write tools |
| `LOG_LEVEL` | `info` | Log level (`debug`, `info`, `warning`, `error`) |
| `AUDIT_LOG_ENABLED` | `true` | Enables audit logging |
| `HTTP_ENABLED` | `false` | Enables HTTP transport |
| `HTTP_PORT` | `8080` | HTTP port |

## 🗺️ Roadmap

- [x] **v1.0** - MVP: generate, lint, to_xray, compose
- [ ] **v1.1** - Policy/guardrails, audit logs
- [ ] **v1.2** - Jira/Xray sync (read-only)
- [ ] **v2.0** - HTTP transport, OAuth

---

# 🇹🇷 Türkçe

**LLM istemcilerinin bağlanıp standart test case üretme, kalite kontrol, Xray formatına çevirme ve test set kompozisyonu yapabildiği bir MCP sunucusu.**

## 🎯 Problem

Kurumsal QA'da tipik sorunlar:

- **Test case formatı dağınık**: Farklı kişiler farklı biçimde yazar → tekrar kullanılamaz
- **Xray/Jira'da standard yok**: Alanlar eksik, dataset belirsiz, adımlar muğlak
- **Smoke/Regression ayrımı** kişiye bağlı: Sprint bazlı planlama zor
- **LLM ile test yazdırınca** aynı öneriler dönüyor veya kritik negatif senaryolar kaçıyor

## ✨ Çözüm

QA-MCP şunları sağlar:

- ✅ **Tek test standardı**: Herkes aynı şablonla üretir/iyileştirir
- ✅ **Kalite kapısı (quality gate)**: Lint skoru + eksik alan tespiti
- ✅ **Xray uyumlu çıktı**: Import edilebilir JSON
- ✅ **Test set/plan kompozisyonu**: Smoke/Regression/E2E önerisi + etiketleme
- ✅ **Güvenli container dağıtımı**: Docker Hub'dan çalıştırılabilir

## 📦 Kurulum

### uv ile (önerilen)

```bash
# uv paket yöneticisini kur
pip install uv

# qa-mcp'yi kur
uv pip install qa-mcp
```

### pip ile

```bash
pip install qa-mcp
qa-mcp --help
qa-mcp --version
```

### Kaynak koddan

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator

# uv ile (önerilen - kilitli bağımlılıkları kullanır)
uv pip install -e .

# pip ile
pip install -e .
```

### Docker ile

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i atakanemree/qa-mcp:latest
```

## 🚀 Kullanım

### MCP İstemcisi ile Bağlantı

#### Cursor / Claude Desktop

`mcp.json` veya `claude_desktop_config.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "qa-mcp",
      "args": []
    }
  }
}
```

#### Docker ile

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "atakanemree/qa-mcp:latest"]
    }
  }
}
```

## 🔧 Tools

| Tool | Açıklama |
|------|----------|
| `testcase.generate` | Feature ve acceptance criteria'dan standart test case üretir |
| `testcase.lint` | Test case kalitesini analiz eder, skor ve öneriler döner |
| `testcase.normalize` | Gherkin/Markdown → Standart format dönüşümü |
| `testcase.to_xray` | Xray/Jira import formatına çevirir |
| `suite.compose` | Smoke/Regression/E2E test suite oluşturur |
| `suite.coverage_report` | Test kapsam analizi raporu üretir |

## 📚 Resources

| URI | Açıklama |
|-----|----------|
| `qa://standards/testcase/v1` | Test case standardı |
| `qa://checklists/lint-rules/v1` | Lint kuralları |
| `qa://mappings/xray/v1` | Xray alan eşlemesi |
| `qa://examples/good/*` | İyi test case örnekleri |
| `qa://examples/bad/*` | Kötü test case örnekleri |

## 💬 Prompts

| Prompt | Açıklama |
|--------|----------|
| `create-manual-test` | Xray Manual Test oluşturma |
| `select-smoke-tests` | Smoke test seçimi |
| `generate-negative-scenarios` | Negatif senaryo üretimi |
| `review-test-coverage` | Test kapsam analizi |

## 🐳 Docker

Yayınlanan image: `atakanemree/qa-mcp` (multi-arch: `linux/amd64`, `linux/arm64`)

```bash
# Image çekme
docker pull atakanemree/qa-mcp:latest

# CLI doğrulama
docker run --rm atakanemree/qa-mcp:latest --help

# Çalıştırma (stdio mode - varsayılan, en güvenli)
docker run -i --rm atakanemree/qa-mcp:latest

# Environment variables ile
docker run -i --rm \
  -e LOG_LEVEL=debug \
  -e ENABLE_WRITE_TOOLS=false \
  atakanemree/qa-mcp:latest

# Local compose (production ve dev target'ları)
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## 🔒 Güvenlik

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `ENABLE_WRITE_TOOLS` | `false` | Jira/Xray yazma tool'larını etkinleştirir |
| `LOG_LEVEL` | `info` | Log seviyesi (`debug`, `info`, `warning`, `error`) |
| `AUDIT_LOG_ENABLED` | `true` | Audit log'u etkinleştirir |
| `HTTP_ENABLED` | `false` | HTTP transport'u etkinleştirir |
| `HTTP_PORT` | `8080` | HTTP port |

## 🗺️ Yol Haritası

- [x] **v1.0** - MVP: generate, lint, to_xray, compose
- [ ] **v1.1** - Policy/guardrails, audit logs
- [ ] **v1.2** - Jira/Xray sync (read-only)
- [ ] **v2.0** - HTTP transport, OAuth

---

## 📄 License / Lisans

MIT License - Copyright (c) 2024-2026 [Atakan Emre](https://github.com/Atakan-Emre)

## 🤝 Contributing / Katkıda Bulunma

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- 🚀 Setting up development environment
- 🧪 Running tests and quality checks
- 📝 Coding standards and best practices
- 🔄 Pull request process

**Quick start:**

1. Fork the repository / Fork yapın
2. Create feature branch / Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Make your changes / Değişiklikleri yapın
4. Run tests / Testleri çalıştırın (`pytest tests/ -v`)
5. Commit your changes / Commit yapın (`git commit -m 'feat: add amazing feature'`)
6. Push to branch / Push yapın (`git push origin feature/amazing-feature`)
7. Open a Pull Request / Pull Request açın

## 👤 Developer / Geliştirici

**Atakan Emre**
- GitHub: [@Atakan-Emre](https://github.com/Atakan-Emre)
- Repository: [McpTestGenerator](https://github.com/Atakan-Emre/McpTestGenerator)

---

<div align="center">

**Standardize test quality with QA-MCP!** 🚀

**QA-MCP ile test kalitesini standardize edin!** 🚀

[![GitHub Stars](https://img.shields.io/github/stars/Atakan-Emre/McpTestGenerator?style=social)](https://github.com/Atakan-Emre/McpTestGenerator/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Atakan-Emre/McpTestGenerator?style=social)](https://github.com/Atakan-Emre/McpTestGenerator/network/members)

</div>
