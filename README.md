# QA-MCP

<div align="center">

[![CI](https://github.com/Atakan-Emre/McpTestGenerator/workflows/CI/badge.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Docker](https://img.shields.io/docker/pulls/atakanemree/qa-mcp.svg)](https://hub.docker.com/r/atakanemree/qa-mcp)

**🇬🇧 English** | [**🇹🇷 Türkçe**](#-türkçe)

</div>

QA-MCP is a Model Context Protocol server for structured QA work. It gives MCP clients a shared test case model, quality analysis, normalization utilities, Xray export payloads, and suite composition tools so test artifacts stay consistent across teams and projects.

---

# 🇬🇧 English

## Overview

QA-MCP is designed for teams that want deterministic, reusable test artifacts instead of ad-hoc prompts and inconsistent manual QA documents.

It currently focuses on:

- Standardized test case generation from feature descriptions and acceptance criteria
- Linting and improvement guidance against a shared QA schema
- Normalization from Gherkin, Markdown, JSON, and plain text into the QA-MCP model
- Xray-compatible JSON payload generation
- Smoke, sanity, regression, and E2E suite composition
- Coverage reporting for requirements and modules
- MCP resources and prompt templates for repeatable LLM usage

## Current Runtime Model

- Transport: `stdio` only
- Network listeners: not enabled in the current release
- Write-capable Jira/Xray sync: not exposed in the current release
- Audit logging: available and enabled by default

If you need an HTTP server or direct Jira/Xray synchronization, treat those as future integration work rather than currently shipped features.

## Quick Start

### Install from PyPI

```bash
pip install qa-mcp
qa-mcp --version
```

### Install with uv

```bash
pip install uv
uv pip install qa-mcp
qa-mcp --version
```

### Run with Docker

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i --rm atakanemree/qa-mcp:latest
```

### Connect an MCP client

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

Docker-based MCP client configuration:

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

## Public MCP Surface

### Tools

| Tool | Purpose |
|------|---------|
| `testcase.generate` | Generate standardized test cases from feature text and acceptance criteria |
| `testcase.lint` | Analyze a single test case and return score, issues, and improvement guidance |
| `testcase.lint_batch` | Analyze a collection of test cases and return aggregate findings |
| `testcase.normalize` | Normalize Gherkin, Markdown, JSON, or plain text into the QA-MCP schema |
| `testcase.to_xray` | Convert a single standardized test case into Xray-compatible JSON payload |
| `testcase.to_xray_batch` | Convert multiple test cases into Xray-compatible bulk payloads |
| `suite.compose` | Select and compose smoke, sanity, regression, or E2E suites |
| `suite.coverage_report` | Report requirement, module, risk, and scenario coverage |
| `xray.get_mapping_template` | Return the suggested QA-MCP to Xray field mapping template |

### Resources

| URI | Purpose |
|-----|---------|
| `qa://standards/testcase/v1` | Canonical QA-MCP test case standard |
| `qa://checklists/lint-rules/v1` | Lint rules, penalties, and scoring guidance |
| `qa://mappings/xray/v1` | Xray mapping reference |
| `qa://examples/good` | Good example test cases |
| `qa://examples/bad` | Anti-pattern example test cases |

### Prompts

| Prompt | Purpose |
|--------|---------|
| `create-manual-test` | Guide an LLM toward structured manual test creation |
| `select-smoke-tests` | Guide smoke suite selection from an existing pool |
| `generate-negative-scenarios` | Guide negative scenario generation |
| `review-test-coverage` | Guide coverage review against existing test assets |

## Configuration

Effective runtime settings in the current release:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `info` | Standard application log level |
| `AUDIT_LOG_ENABLED` | `true` | Enables tool invocation audit logging |

Notes:

- `qa-mcp` currently runs in `stdio` mode.
- Container images may include placeholder environment variables for future transports or integrations, but they are not active features unless the server implementation actually uses them.

## Docker

Published image: `atakanemree/qa-mcp`

```bash
# Pull
docker pull atakanemree/qa-mcp:latest

# Verify the packaged CLI
docker run --rm atakanemree/qa-mcp:latest --version

# Run the MCP server in stdio mode
docker run -i --rm atakanemree/qa-mcp:latest

# Compose targets
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## Documentation

- [USAGE.md](USAGE.md): Detailed usage examples and request payloads
- [CONTRIBUTING.md](CONTRIBUTING.md): Contributor workflow and quality checks
- [docs/PUBLISHING.md](docs/PUBLISHING.md): Package and release publishing flow
- [CHANGELOG.md](CHANGELOG.md): Release history
- [DOCKERHUB.md](DOCKERHUB.md): Docker Hub description source

## Roadmap

### Shipped

- Standard test case schema and resources
- Generation, linting, normalization, Xray export, suite composition, and coverage reporting
- Prompt templates for structured QA workflows
- PyPI packaging, Docker image publishing, and audit logging

### Near-Term Focus

- Better normalization coverage for messy real-world inputs
- Stronger example libraries and schema-oriented documentation
- Clearer suite selection rationale and coverage reporting ergonomics

### Planned Integrations

- Read-only integrations for external QA systems where they materially improve traceability
- Carefully gated write-capable integrations only when the operational model is explicit and safe

## License

MIT License. See [LICENSE](LICENSE).

---

# 🇹🇷 Türkçe

## Genel Bakış

QA-MCP, yapılandırılmış QA iş akışları için hazırlanmış bir Model Context Protocol sunucusudur. MCP istemcilerine ortak bir test case modeli, kalite analizi, normalizasyon araçları, Xray çıktı payload'ları ve suite kompozisyon araçları sağlar.

Bugünkü kapsamı:

- Feature açıklamaları ve acceptance criteria üzerinden standart test case üretimi
- Ortak QA şemasına göre lint analizi ve iyileştirme yönlendirmesi
- Gherkin, Markdown, JSON ve düz metni QA-MCP modeline dönüştürme
- Xray uyumlu JSON payload üretimi
- Smoke, sanity, regression ve E2E suite kompozisyonu
- Requirement ve modül bazlı coverage raporlama
- Tekrarlanabilir LLM kullanımı için MCP resource ve prompt şablonları

## Mevcut Çalışma Modeli

- Transport: yalnızca `stdio`
- Ağ dinleyicisi: mevcut sürümde yok
- Yazma yetkili Jira/Xray senkronizasyonu: mevcut sürümde yok
- Audit logging: mevcut ve varsayılan olarak açık

HTTP sunucusu veya doğrudan Jira/Xray senkronizasyonu gerekiyorsa, bunları mevcut özellik değil gelecek entegrasyon işi olarak değerlendirin.

## Hızlı Başlangıç

### PyPI üzerinden kurulum

```bash
pip install qa-mcp
qa-mcp --version
```

### uv ile kurulum

```bash
pip install uv
uv pip install qa-mcp
qa-mcp --version
```

### Docker ile çalıştırma

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i --rm atakanemree/qa-mcp:latest
```

### MCP istemcisine bağlama

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

Docker tabanlı istemci yapılandırması:

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

## Public MCP Yüzeyi

### Tool'lar

| Tool | Amaç |
|------|------|
| `testcase.generate` | Feature metni ve acceptance criteria'dan standart test case üretir |
| `testcase.lint` | Tek bir test case için skor, issue ve iyileştirme önerileri döner |
| `testcase.lint_batch` | Birden fazla test case için toplu kalite analizi yapar |
| `testcase.normalize` | Gherkin, Markdown, JSON veya düz metni QA-MCP şemasına dönüştürür |
| `testcase.to_xray` | Tek bir test case'i Xray uyumlu JSON payload'a çevirir |
| `testcase.to_xray_batch` | Birden fazla test case'i toplu Xray payload formatına çevirir |
| `suite.compose` | Smoke, sanity, regression veya E2E suite seçimi yapar |
| `suite.coverage_report` | Requirement, modül, risk ve senaryo kapsamını raporlar |
| `xray.get_mapping_template` | QA-MCP → Xray alan eşleme şablonunu döner |

### Resource'lar

| URI | Amaç |
|-----|------|
| `qa://standards/testcase/v1` | Kanonik QA-MCP test case standardı |
| `qa://checklists/lint-rules/v1` | Lint kuralları, cezalar ve puanlama mantığı |
| `qa://mappings/xray/v1` | Xray mapping referansı |
| `qa://examples/good` | İyi örnek test case'ler |
| `qa://examples/bad` | Anti-pattern örnek test case'ler |

### Prompt'lar

| Prompt | Amaç |
|--------|------|
| `create-manual-test` | LLM'i yapılandırılmış manual test üretimine yönlendirir |
| `select-smoke-tests` | Mevcut havuzdan smoke suite seçimine yönlendirir |
| `generate-negative-scenarios` | Negatif senaryo üretimine yönlendirir |
| `review-test-coverage` | Mevcut test varlıkları üzerinden kapsam analizine yönlendirir |

## Yapılandırma

Mevcut sürümde etkili olan runtime ayarları:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `LOG_LEVEL` | `info` | Uygulama log seviyesi |
| `AUDIT_LOG_ENABLED` | `true` | Tool çağrıları için audit log'u açar |

Notlar:

- `qa-mcp` şu anda yalnızca `stdio` modunda çalışır.
- Container image içinde gelecekteki transport veya entegrasyonlara ait placeholder environment variable'lar bulunabilir; sunucu implementasyonu bunları kullanmadıkça aktif özellik sayılmamalıdır.

## Docker

Yayınlanan image: `atakanemree/qa-mcp`

```bash
# Çek
docker pull atakanemree/qa-mcp:latest

# Paketlenmiş CLI'yı doğrula
docker run --rm atakanemree/qa-mcp:latest --version

# MCP server'ı stdio modunda çalıştır
docker run -i --rm atakanemree/qa-mcp:latest

# Compose target'ları
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## Dokümantasyon

- [USAGE.md](USAGE.md): Detaylı kullanım örnekleri ve request payload'ları
- [CONTRIBUTING.md](CONTRIBUTING.md): Katkı akışı ve kalite kontrolleri
- [docs/PUBLISHING.md](docs/PUBLISHING.md): Paket ve release yayın süreci
- [CHANGELOG.md](CHANGELOG.md): Sürüm geçmişi
- [DOCKERHUB.md](DOCKERHUB.md): Docker Hub açıklama kaynağı

## Yol Haritası

### Yayında Olanlar

- Standart test case şeması ve resource seti
- Üretim, lint, normalizasyon, Xray export, suite kompozisyonu ve coverage raporlama
- Yapılandırılmış QA iş akışları için prompt şablonları
- PyPI paketleme, Docker image yayını ve audit logging

### Kısa Vadeli Odak

- Gerçek dünyadaki dağınık girdiler için daha güçlü normalizasyon
- Daha güçlü örnek kütüphaneleri ve şema odaklı dokümantasyon
- Suite seçim gerekçesi ve coverage raporlarının kullanım ergonomisini iyileştirme

### Planlanan Entegrasyonlar

- İzlenebilirliği gerçekten artıran dış QA sistemleri için read-only entegrasyonlar
- Ancak operasyon modeli açık ve güvenli olduğunda devreye alınacak, kontrollü write-capable entegrasyonlar

## Lisans

MIT License. Ayrıntılar için [LICENSE](LICENSE).
