# QA-MCP

<div align="center">

[![CI](https://github.com/Atakan-Emre/McpTestGenerator/workflows/CI/badge.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Docker](https://img.shields.io/docker/pulls/atakanemree/qa-mcp.svg)](https://hub.docker.com/r/atakanemree/qa-mcp)

**The Model Context Protocol (MCP) server for deterministic, structured, and scalable Quality Assurance.**

**🇬🇧 [English](#-english)** | **🇹🇷 [Türkçe](#-türkçe)**

</div>

---

# 🇬🇧 English

## 📖 Overview

**QA-MCP** bridges the gap between ad-hoc LLM prompts and structured software testing. It provides AI agents and MCP clients with a shared test case model, rigorous quality analysis, and powerful normalization utilities. 

Say goodbye to inconsistent manual QA documents. QA-MCP ensures that whether you are generating test cases from raw feature descriptions, converting Gherkin syntax, or composing complete regression suites, your test artifacts remain standardized, reusable, and perfectly aligned across your engineering teams.

### ✨ Key Features

- **🚀 Standardized Generation:** Automatically generate high-quality, structured test cases from feature descriptions and acceptance criteria.
- **🛠️ Smart Normalization:** Seamlessly convert Gherkin, Markdown, JSON, and plain text into the canonical QA-MCP schema.
- **📈 Advanced Linting & Scoring:** Evaluate test cases against a shared QA schema with detailed scores, issue tracking, and improvement guidance.
- **🔗 Xray Ready:** Instantly convert standardized test cases into Xray-compatible JSON payloads for Jira integration.
- **📦 Suite Composition:** Dynamically compose and manage Smoke, Sanity, Regression, E2E, Integration, and Performance test suites.
- **📊 Coverage Reporting:** Track and report coverage metrics across requirements, modules, and risk areas.
- **🧩 Modern MCP Surface:** Built on the **mcp 2.x** SDK — typed `structuredContent` results whose schemas are derived from the result models, read-only tool annotations, display titles, resource templates, and argument completion.
- **🏢 Enterprise Ready:** Point it at your own Jira/Xray tenant with environment variables alone. Credentials are validated at startup, never logged, and write access is a separate, explicit opt-in. See [ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md).

## 🚀 Quick Start

### Install via PyPI
```bash
pip install qa-mcp
qa-mcp --version
````

### Install via uv

```bash
pip install uv
uv pip install qa-mcp
qa-mcp --version
```

### Run via Docker

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i --rm atakanemree/qa-mcp:latest
```

## 🔌 Connecting an MCP Client

Configure your preferred MCP client (e.g., Claude Desktop) to use QA-MCP.

**Standard Configuration:**

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

**Docker Configuration:**

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

## 🛠️ Public MCP Surface

### Tools

Tool names intentionally use underscores so Claude Desktop and other strict MCP clients accept them.

| Tool | Purpose |
|------|---------|
| `testcase_generate` | Generate standardized test cases from feature text and acceptance criteria. |
| `testcase_lint` | Analyze a single test case, returning a quality score, issues, and improvement steps. |
| `testcase_lint_batch` | Analyze a collection of test cases and return aggregate findings. |
| `testcase_normalize` | Normalize Gherkin, Markdown, JSON, or plain text into the QA-MCP schema. |
| `testcase_to_xray` | Convert a single test case into an Xray-compatible JSON payload. |
| `testcase_to_xray_batch` | Convert multiple test cases into Xray-compatible bulk payloads. |
| `suite_compose` | Select and compose Smoke, Sanity, Regression, or E2E suites. |
| `suite_coverage_report` | Generate requirement, module, risk, and scenario coverage reports. |
| `xray_get_mapping_template`| Get the suggested QA-MCP to Xray field mapping template. |

### Resources

| URI | Purpose |
|-----|---------|
| `qa://standards/testcase/v1` | Canonical QA-MCP test case standard. |
| `qa://checklists/lint-rules/v1`| Lint rules, penalties, and scoring logic. |
| `qa://mappings/xray/v1` | Xray mapping reference documentation. |
| `qa://examples/good` | Best-practice test case examples. |
| `qa://examples/bad` | Anti-pattern test case examples. |

### Prompts

| Prompt | Purpose |
|--------|---------|
| `create-manual-test` | Guide the LLM toward structured manual test creation. |
| `select-smoke-tests` | Assist in selecting an optimal smoke suite from an existing pool. |
| `generate-negative-scenarios`| Guide the generation of robust negative/edge-case scenarios. |
| `review-test-coverage` | Analyze existing test assets for coverage gaps. |

## ⚙️ Architecture & Configuration

QA-MCP is designed for secure, localized execution:

  - **Transport:** Currently operates exclusively via standard input/output (`stdio`).
  - **Integrations:** Direct write-capable synchronization (e.g., Jira/Xray APIs) and network listeners are planned for future roadmap milestones. Current Xray functionality focuses on robust payload generation.

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `info` | Standard application log level. |
| `AUDIT_LOG_ENABLED`| `true` | Enables tool invocation audit logging for traceability. |

## 🐳 Docker Deployment

The official image is available on Docker Hub: `atakanemree/qa-mcp`

```bash
# Verify the packaged CLI
docker run --rm atakanemree/qa-mcp:latest --version

# Run the MCP server in stdio mode
docker run -i --rm atakanemree/qa-mcp:latest

# Docker Compose usage
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## 📚 Documentation

For deep dives into QA-MCP's architecture and contribution guidelines, explore the docs:

  - **[USAGE.md](USAGE.md):** Detailed usage examples and request payloads.
  - **[CONTRIBUTING.md](CONTRIBUTING.md):** Contributor workflow and quality checks.
  - **[CHANGELOG.md](CHANGELOG.md):** Release history.
  - **[docs/CI-CD.md](docs/CI-CD.md):** Jenkins pipeline and SonarQube analysis setup.
  - **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md):** Connecting your own Jira/Xray tenant and quality bar.
  - **[docs/MCP-2.x-MIGRATION.md](docs/MCP-2.x-MIGRATION.md):** Record of the mcp 2.x SDK migration.
  - **[docs/PUBLISHING.md](docs/PUBLISHING.md):** Package and release publishing flow.

## 🗺️ Roadmap

  - **Phase 1 (Current):** Standard schema, generation, linting, normalization, Xray payload export, and suite composition via `stdio`.
  - **Phase 2 (Near-Term):** Enhanced normalization logic for messy real-world inputs, expanded example libraries, and richer coverage reporting ergonomics.
  - **Phase 3 (Planned):** Read-only integrations for external QA systems and strictly gated, safe write-capable endpoints.

## 📄 License

Released under the **MIT License**. See [LICENSE](LICENSE) for details.

-----

# 🇹🇷 Türkçe

## 📖 Genel Bakış

**QA-MCP**, LLM istemleri (prompt) ile yapılandırılmış yazılım test süreçleri arasındaki köprüyü kurar. Yapay zeka ajanlarına ve MCP istemcilerine ortak bir test senaryosu modeli, titiz bir kalite analizi ve güçlü normalizasyon araçları sunar.

Tutarsız ve manuel hazırlanan QA dokümanlarına veda edin. QA-MCP; ham özellik tanımlarından test case üretirken, Gherkin sözdizimini dönüştürürken veya kapsamlı regresyon suitleri oluştururken test varlıklarınızın standart, yeniden kullanılabilir ve yazılım ekiplerinizle mükemmel bir uyum içinde kalmasını sağlar.

### ✨ Temel Özellikler

  - **🚀 Standart Üretim:** Feature metinlerinden ve kabul kriterlerinden otomatik olarak yüksek kaliteli, yapılandırılmış test case'ler üretin.
  - **🛠️ Akıllı Normalizasyon:** Gherkin, Markdown, JSON ve düz metinleri standart QA-MCP şemasına sorunsuz bir şekilde dönüştürün.
  - **📈 Gelişmiş Linting ve Skorlama:** Test senaryolarını ortak kalite şemasına göre değerlendirin; detaylı skorlar, hatalar ve iyileştirme adımları elde edin.
  - **🔗 Xray Entegrasyonuna Hazır:** Standart test case'leri anında Jira/Xray uyumlu JSON payload'larına dönüştürün.
  - **📦 Suite Yönetimi:** Smoke, Sanity, Regression, E2E, Integration ve Performance suitlerini dinamik olarak oluşturun ve yönetin.
  - **📊 Kapsam (Coverage) Raporlama:** Gereksinim, modül ve risk bazlı test kapsam metriklerini raporlayın.
  - **🧩 Güncel MCP Yüzeyi:** **mcp 2.x** SDK üzerine kuruludur — şemaları sonuç modellerinden türetilen tipli `structuredContent`, read-only tool annotation'ları, görünen adlar, resource template ve argüman tamamlama.
  - **🏢 Kurumsal Kullanıma Hazır:** Yalnızca ortam değişkenleriyle kendi Jira/Xray tenant'ınıza bağlanır. Kimlik bilgileri başlangıçta doğrulanır, hiçbir yere loglanmaz; yazma erişimi ayrı ve bilinçli bir tercihtir. Bkz. [ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md).

## 🚀 Hızlı Başlangıç

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

## 🔌 MCP İstemcisine Bağlanma

Tercih ettiğiniz MCP istemcisini (örn. Claude Desktop) QA-MCP kullanacak şekilde yapılandırın.

**Standart Yapılandırma:**

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

**Docker Yapılandırması:**

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

## 🛠️ Public MCP Yüzeyi

### Tool'lar (Araçlar)

Tool adları Claude Desktop gibi katı MCP istemcileriyle uyum için bilerek underscore (`_`) kullanır.

| Tool | Amaç |
|------|------|
| `testcase_generate` | Feature metni ve kabul kriterlerinden standart test case üretir. |
| `testcase_lint` | Test case'i analiz eder; kalite skoru, sorunlar ve iyileştirme adımları döner. |
| `testcase_lint_batch` | Birden fazla test case için toplu analiz yapar. |
| `testcase_normalize` | Gherkin, Markdown, JSON veya düz metni QA-MCP şemasına dönüştürür. |
| `testcase_to_xray` | Tek bir test case'i Xray uyumlu JSON payload'a çevirir. |
| `testcase_to_xray_batch`| Test case'leri toplu Xray payload formatına çevirir. |
| `suite_compose` | Smoke, Sanity, Regression veya E2E suite kompozisyonu oluşturur. |
| `suite_coverage_report` | Gereksinim, modül, risk ve senaryo kapsamını raporlar. |
| `xray_get_mapping_template`| QA-MCP -\> Xray alan eşleme şablonunu döner. |

### Resource'lar (Kaynaklar)

| URI | Amaç |
|-----|------|
| `qa://standards/testcase/v1` | Kanonik QA-MCP test case standardı. |
| `qa://checklists/lint-rules/v1`| Lint kuralları, cezalar ve puanlama mantığı. |
| `qa://mappings/xray/v1` | Xray mapping referans dokümantasyonu. |
| `qa://examples/good` | İyi/ideal örnek test case'ler. |
| `qa://examples/bad` | Anti-pattern (hatalı) örnek test case'ler. |

### Prompt'lar

| Prompt | Amaç |
|--------|------|
| `create-manual-test` | LLM'i yapılandırılmış manuel test üretimine yönlendirir. |
| `select-smoke-tests` | Mevcut havuzdan en uygun smoke suite seçimine yardımcı olur. |
| `generate-negative-scenarios`| Kapsamlı negatif/uç durum senaryolarının üretilmesini sağlar. |
| `review-test-coverage` | Test eksikliklerini bulmak için mevcut varlıkları analiz eder. |

## ⚙️ Mimari ve Yapılandırma

QA-MCP, güvenli ve lokal çalışacak şekilde tasarlanmıştır:

  - **Bağlantı (Transport):** Şu anda yalnızca standart girdi/çıktı (`stdio`) üzerinden çalışır.
  - **Entegrasyonlar:** Doğrudan yazma yetkisine sahip API senkronizasyonları (örn. Jira/Xray'e direkt push) ve ağ dinleyicileri (network listeners) gelecek yol haritasında planlanmıştır. Mevcut Xray özelliği güçlü payload üretimine odaklanır.

**Ortam Değişkenleri:**
| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `LOG_LEVEL` | `info` | Uygulama log seviyesi. |
| `AUDIT_LOG_ENABLED`| `true` | İzlenebilirlik için araç çağrılarına ait audit log'ları aktifleştirir. |

## 🐳 Docker Dağıtımı

Resmi imaj Docker Hub üzerinde yayındadır: `atakanemree/qa-mcp`

```bash
# Paketlenmiş CLI'yı doğrula
docker run --rm atakanemree/qa-mcp:latest --version

# MCP server'ı stdio modunda çalıştır
docker run -i --rm atakanemree/qa-mcp:latest

# Docker Compose kullanımı
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

## 📚 Dokümantasyon

Mimari detaylar ve projeye katkı rehberleri için:

  - **[USAGE.md](USAGE.md):** Detaylı kullanım örnekleri ve request payload'ları.
  - **[CONTRIBUTING.md](CONTRIBUTING.md):** Katkı akışı ve kalite kontrolleri.
  - **[CHANGELOG.md](CHANGELOG.md):** Sürüm ve değişiklik geçmişi.
  - **[docs/CI-CD.md](docs/CI-CD.md):** Jenkins pipeline ve SonarQube analiz kurulumu.
  - **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md):** Kendi Jira/Xray tenant'ınızı ve kalite eşiğinizi bağlama.
  - **[docs/MCP-2.x-MIGRATION.md](docs/MCP-2.x-MIGRATION.md):** mcp 2.x SDK geçişinin kaydı.
  - **[docs/PUBLISHING.md](docs/PUBLISHING.md):** Paket ve release yayın süreci.

## 🗺️ Yol Haritası

  - **Aşama 1 (Mevcut):** `stdio` üzerinden standart şema, üretim, linting, normalizasyon, Xray export ve suite kompozisyonu.
  - **Aşama 2 (Kısa Vadeli):** Dağınık girdiler için geliştirilmiş normalizasyon mantığı, daha zengin örnek kütüphaneleri ve iyileştirilmiş raporlama ergonomisi.
  - **Aşama 3 (Planlanan):** Dış QA sistemleri için read-only entegrasyonlar ve kontrollü/güvenli write-capable uç noktalar.

## 📄 Lisans

**MIT License** ile yayınlanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.
