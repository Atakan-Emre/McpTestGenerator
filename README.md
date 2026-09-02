# QA-MCP v2

<div align="center">

[![CI](https://github.com/Atakan-Emre/McpTestGenerator/workflows/CI/badge.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/qa-mcp.svg)](https://pypi.org/project/qa-mcp/)
[![MCP SDK](https://img.shields.io/badge/mcp%20SDK-2.x-blue.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Docker](https://img.shields.io/docker/pulls/atakanemree/qa-mcp.svg)](https://hub.docker.com/r/atakanemree/qa-mcp)

**The Model Context Protocol (MCP) server for deterministic, structured, and scalable Quality Assurance.**

**🇬🇧 [English](#-english)** | **🇹🇷 [Türkçe](#-türkçe)**

</div>

> **Version 2** — built on the **mcp 2.x** SDK, with typed structured results and
> an environment-driven setup that connects QA-MCP to your own Jira/Xray tenant.
> Upgrading from 1.x? See [Migrating from 1.x](#-migrating-from-1x).

---

# 🇬🇧 English

## 📖 Overview

**QA-MCP** bridges the gap between ad-hoc LLM prompts and structured software testing. It provides AI agents and MCP clients with a shared test case model, rigorous quality analysis, and powerful normalization utilities.

Say goodbye to inconsistent manual QA documents. QA-MCP ensures that whether you are generating test cases from raw feature descriptions, converting Gherkin syntax, or composing complete regression suites, your test artifacts remain standardized, reusable, and perfectly aligned across your engineering teams.

It works with **zero configuration** and never touches the network. Give it your Jira credentials and it additionally reads from — and, if you explicitly allow it, writes to — your own Xray project.

### ✨ Key Features

- **🚀 Standardized Generation:** Automatically generate high-quality, structured test cases from feature descriptions and acceptance criteria.
- **🛠️ Smart Normalization:** Seamlessly convert Gherkin, Markdown, JSON, and plain text into the canonical QA-MCP schema.
- **📈 Advanced Linting & Scoring:** Evaluate test cases against a shared QA schema with detailed scores, issue tracking, and improvement guidance — including rules for hardcoded credentials and non-parameterized test data.
- **🔗 Xray Ready:** Convert standardized test cases into Xray-compatible JSON payloads, and — once a tenant is configured — read and create real Xray tests. Uses Xray Cloud's GraphQL API and Server/DC's `/rest/raven` REST API, so **test steps actually travel with the issue** instead of being dropped by the Jira issue API.
- **📦 Suite Composition:** Compose Smoke, Sanity, Regression, E2E, Integration, and Performance suites, each with its own selection rules.
- **📊 Coverage Reporting:** Track requirement, module, risk, and scenario coverage, and report which inputs were skipped rather than silently dropping them.
- **🧩 Modern MCP Surface:** Typed `structuredContent` results whose schemas are generated from the result models, read-only tool annotations, display titles, resource templates, and argument completion.
- **🏢 Enterprise Ready:** Configure everything from the environment. Credentials are validated at startup, held as secrets, and never logged. Write access is a separate, explicit opt-in.

## 🚀 Quick Start

### Install via PyPI

```bash
pip install qa-mcp
qa-mcp --version
```

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

### Check your setup

```bash
qa-mcp --check-config
```

Validates the configuration, prints exactly which tools the deployment would expose, and exits non-zero when something is wrong.

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

**With your own Jira/Xray tenant** (a stdio MCP server does not inherit your shell environment, so credentials go in the client's `env` block):

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
        "QA_MCP_XRAY_API_TOKEN": "<Jira API token>",
        "QA_MCP_XRAY_CLIENT_ID": "<Xray API Key client id>",
        "QA_MCP_XRAY_CLIENT_SECRET": "<Xray API Key client secret>",
        "QA_MCP_XRAY_PROJECT_KEY": "QA"
      }
    }
  }
}
```

On **Jira Cloud these are two different credentials**: a Jira API token for
issues, and an Xray API Key for test steps, which Xray keeps outside Jira. On
**Server/Data Center** one personal access token covers both. QA-MCP refuses to
create a test whose steps it cannot import rather than silently producing an
empty one.

Full walkthrough: **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)**.

## 🛠️ Public MCP Surface

Tool names intentionally use underscores so strict MCP clients accept them. Every tool returns typed structured content validated against a published output schema.

### Tools — always available

| Tool | Purpose |
|------|---------|
| `testcase_generate` | Generate standardized test cases from feature text and acceptance criteria. |
| `testcase_lint` | Analyze a single test case, returning a quality score, issues, and improvement steps. |
| `testcase_lint_batch` | Analyze a collection of test cases and return aggregate findings. |
| `testcase_normalize` | Normalize Gherkin, Markdown, JSON, or plain text into the QA-MCP schema. |
| `testcase_to_xray` | Convert a single test case into an Xray-compatible JSON payload. |
| `testcase_to_xray_batch` | Convert multiple test cases into Xray-compatible bulk payloads. |
| `suite_compose` | Compose a Smoke, Sanity, Regression, E2E, Integration, or Performance suite. |
| `suite_coverage_report` | Generate requirement, module, risk, and scenario coverage reports. |
| `xray_get_mapping_template` | Get the suggested QA-MCP to Xray field mapping template. |

These nine are pure functions: nothing is persisted, no external system is contacted, and repeating a call changes nothing. They are annotated read-only so clients need not gate them.

### Tools — published once a Jira/Xray tenant is configured

| Tool | Requires | Purpose |
|------|----------|---------|
| `xray_verify_connection` | `QA_MCP_XRAY_ENABLED` | Verify the credentials and report which account they belong to. |
| `xray_get_test` | `QA_MCP_XRAY_ENABLED` | Fetch a single Xray test issue from Jira. |
| `xray_search_tests` | `QA_MCP_XRAY_ENABLED` | Search test issues by JQL, or list a project's tests. |
| `xray_create_test` | `QA_MCP_ENABLE_WRITE_TOOLS` | **Creates** an Xray test issue in Jira. |

The first three are read-only. `xray_create_test` is the only tool that changes anything in Jira: it is absent unless writes are explicitly enabled, it is annotated non-read-only so clients prompt for approval, and the client re-checks the flag on every call.

### Resources

| URI | Purpose |
|-----|---------|
| `qa://standards/testcase/v1` | Canonical QA-MCP test case standard. |
| `qa://checklists/lint-rules/v1` | Lint rules, penalties, and scoring logic. |
| `qa://mappings/xray/v1` | Xray mapping reference documentation. |
| `qa://examples/{quality}` | Example test cases; `good` for best practice, `bad` for anti-patterns. |

`qa://examples/{quality}` is a resource template — clients can complete the `quality` argument.

### Prompts

| Prompt | Purpose |
|--------|---------|
| `create-manual-test` | Guide the LLM toward structured manual test creation. |
| `select-smoke-tests` | Assist in selecting an optimal smoke suite from an existing pool. |
| `generate-negative-scenarios` | Guide the generation of robust negative/edge-case scenarios. |
| `review-test-coverage` | Analyze existing test assets for coverage gaps. |

## ⚙️ Architecture & Configuration

- **Transport:** standard input/output (`stdio`).
- **Offline by default:** the nine analysis tools never open a socket. Jira/Xray connectivity is opt-in and validated at startup.
- **Configuration:** entirely environment-driven — no config file to fork, no code to edit.

**Most common settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `QA_MCP_LOG_LEVEL` | `INFO` | Log level; logs go to stderr. |
| `QA_MCP_AUDIT_LOG_ENABLED` | `true` | Log every tool call (argument names only, never values). |
| `QA_MCP_LINT_MINIMUM_SCORE` | `60` | Score a test case needs to pass. |
| `QA_MCP_LINT_DISABLED_RULES` | `[]` | Rule ids your team does not enforce, as a JSON array. |
| `QA_MCP_XRAY_ENABLED` | `false` | Allow QA-MCP to contact Jira/Xray. |
| `QA_MCP_XRAY_BASE_URL` | — | Jira base URL. |
| `QA_MCP_XRAY_DEPLOYMENT` | `cloud` | `cloud` or `server`; decides which Xray API is used. |
| `QA_MCP_XRAY_API_TOKEN` | — | Jira API token or personal access token. |
| `QA_MCP_XRAY_CLIENT_ID` / `_CLIENT_SECRET` | — | Xray Cloud API Key; required for test steps on Cloud. |
| `QA_MCP_ENABLE_WRITE_TOOLS` | `false` | Publish `xray_create_test`, which writes to Jira. |

Full reference — including Jira Cloud vs Server/Data Center authentication, per-tenant custom field ids, and credential handling — in **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)** and [`.env.example`](.env.example).

## 🐳 Docker Deployment

The official image is available on Docker Hub: `atakanemree/qa-mcp`

```bash
# Verify the packaged CLI
docker run --rm atakanemree/qa-mcp:latest --version

# Run the MCP server in stdio mode
docker run -i --rm atakanemree/qa-mcp:latest

# With your own tenant configuration
docker run -i --rm --env-file .env atakanemree/qa-mcp:latest

# Docker Compose usage
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

Pass tokens through `--env-file` or your orchestrator's secret mechanism — never bake them into an image.

## 🔄 Migrating from 1.x

| Change | What to do |
|--------|------------|
| Requires the **mcp 2.x** SDK | `pip install --upgrade qa-mcp` pulls it in. MCP clients need no changes: the wire format is unchanged. |
| Environment variables are namespaced (`QA_MCP_*`) | Nothing breaks — the unprefixed 1.x names (`LOG_LEVEL`, `AUDIT_LOG_ENABLED`, `ENABLE_WRITE_TOOLS`) are still accepted. The prefixed names take precedence. |
| Dotted tool aliases (`testcase.lint`) are no longer published | Set `QA_MCP_LEGACY_TOOL_ALIASES=true` if an older client still calls them. |
| `ENABLE_WRITE_TOOLS` is no longer inert | It now publishes a tool that writes to Jira, and is rejected at startup unless a tenant is configured. Leave it off unless you mean it. |
| Library callers read `result[0].text` | Tool results are now returned as structured content; read the result object directly. MCP clients are unaffected. |

Run `qa-mcp --check-config` after upgrading — it reports exactly what your configuration exposes.

## 📚 Documentation

  - **[USAGE.md](USAGE.md):** Detailed usage examples and request payloads.
  - **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md):** Connecting your own Jira/Xray tenant and quality bar.
  - **[docs/CI-CD.md](docs/CI-CD.md):** Jenkins pipeline and SonarQube analysis setup.
  - **[docs/MCP-2.x-MIGRATION.md](docs/MCP-2.x-MIGRATION.md):** Record of the mcp 2.x SDK migration.
  - **[docs/PUBLISHING.md](docs/PUBLISHING.md):** Package and release publishing flow.
  - **[CONTRIBUTING.md](CONTRIBUTING.md):** Contributor workflow and quality checks.
  - **[CHANGELOG.md](CHANGELOG.md):** Release history.

## 🗺️ Roadmap

  - **Done in v2:** typed structured results on the mcp 2.x SDK, environment-driven configuration, read-only Jira/Xray integration, and a strictly gated write endpoint.
  - **Next:** richer Xray operations (test sets, test plans, execution results) and bulk import against a live tenant.
  - **Later:** additional QA system integrations beyond Xray, and optional network transports.

## 📄 License

Released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

# 🇹🇷 Türkçe

## 📖 Genel Bakış

**QA-MCP**, gelişigüzel LLM promptları ile yapılandırılmış yazılım testi arasındaki boşluğu kapatır. AI ajanlarına ve MCP istemcilerine ortak bir test case modeli, titiz kalite analizi ve güçlü normalizasyon araçları sunar.

Tutarsız manuel QA dokümanlarına veda edin. İster ham feature açıklamasından test üretin, ister Gherkin dönüştürün, ister komple regresyon suite'i oluşturun — test varlıklarınız standart, tekrar kullanılabilir ve ekipler arasında hizalı kalır.

**Hiçbir yapılandırma gerektirmeden** çalışır ve ağa hiç çıkmaz. Jira kimlik bilgilerinizi verdiğinizde ayrıca kendi Xray projenizden okur; açıkça izin verirseniz oraya yazar.

### ✨ Temel Özellikler

  - **🚀 Standart Üretim:** Feature metinlerinden ve kabul kriterlerinden otomatik olarak yüksek kaliteli, yapılandırılmış test case'ler üretin.
  - **🛠️ Akıllı Normalizasyon:** Gherkin, Markdown, JSON ve düz metinleri standart QA-MCP şemasına sorunsuz dönüştürün.
  - **📈 Gelişmiş Linting ve Skorlama:** Test senaryolarını ortak kalite şemasına göre değerlendirin; hardcoded credential ve parametrik olmayan test verisi kuralları dahil detaylı skor, hata ve iyileştirme adımları alın.
  - **🔗 Xray Entegrasyonu:** Standart test case'leri Xray uyumlu JSON payload'larına dönüştürün; tenant bağlıysa gerçek Xray test'leri okuyup oluşturun. Xray Cloud'da GraphQL, Server/DC'de `/rest/raven` REST API'si kullanılır — böylece **test adımları issue ile birlikte gider**, Jira issue API'sinde olduğu gibi düşmez.
  - **📦 Suite Yönetimi:** Smoke, Sanity, Regression, E2E, Integration ve Performance suitlerini, her biri kendi seçim kurallarıyla oluşturun.
  - **📊 Kapsam Raporlama:** Gereksinim, modül, risk ve senaryo kapsamını izleyin; standarda uymayan girdiler sessizce atılmaz, raporlanır.
  - **🧩 Güncel MCP Yüzeyi:** Şemaları sonuç modellerinden üretilen tipli `structuredContent`, read-only tool annotation'ları, görünen adlar, resource template ve argüman tamamlama.
  - **🏢 Kurumsal Kullanıma Hazır:** Her şey ortam değişkeniyle yapılandırılır. Kimlik bilgileri başlangıçta doğrulanır, sır olarak tutulur, hiçbir yere loglanmaz. Yazma erişimi ayrı ve bilinçli bir tercihtir.

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

### Kurulumu doğrulama

```bash
qa-mcp --check-config
```

Yapılandırmayı doğrular, hangi tool'ların yayınlanacağını yazdırır ve bir sorun varsa sıfırdan farklı kodla çıkar.

## 🔌 MCP İstemcisine Bağlanma

Tercih ettiğiniz MCP istemcisini (örn. Claude Desktop) QA-MCP kullanacak şekilde yapılandırın.

**Standart yapılandırma:**

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

**Kendi Jira/Xray tenant'ınızla:**

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "qa-mcp",
      "env": {
        "QA_MCP_XRAY_ENABLED": "true",
        "QA_MCP_XRAY_BASE_URL": "https://sirketiniz.atlassian.net",
        "QA_MCP_XRAY_AUTH_MODE": "basic",
        "QA_MCP_XRAY_EMAIL": "qa-automation@sirketiniz.com",
        "QA_MCP_XRAY_API_TOKEN": "<Jira API token>",
        "QA_MCP_XRAY_CLIENT_ID": "<Xray API Key client id>",
        "QA_MCP_XRAY_CLIENT_SECRET": "<Xray API Key client secret>",
        "QA_MCP_XRAY_PROJECT_KEY": "QA"
      }
    }
  }
}
```

**Jira Cloud'da bunlar iki ayrı kimliktir:** issue'lar için Jira API token'ı,
test adımları için Xray API Key. Xray, adımları Jira'nın dışında tutar.
**Server/Data Center'da** tek bir personal access token ikisini de karşılar.
QA-MCP, adımlarını aktaramayacağı bir test'i sessizce boş oluşturmak yerine
reddeder.

stdio MCP sunucusu shell ortamınızı miras almaz; kimlik bilgileri istemcinin
`env` bloğuna yazılır.

Adım adım kurulum: **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)**.

## 🛠️ Public MCP Yüzeyi

Tool adları katı MCP istemcileriyle uyum için bilerek underscore (`_`) kullanır. Her tool, yayınlanmış bir çıktı şemasına karşı doğrulanmış tipli yapısal içerik döner.

### Tool'lar — her zaman mevcut

| Tool | Amaç |
|------|------|
| `testcase_generate` | Feature metni ve kabul kriterlerinden standart test case üretir. |
| `testcase_lint` | Tek bir test case'i analiz eder; kalite skoru, hatalar ve iyileştirme adımları döner. |
| `testcase_lint_batch` | Test case koleksiyonunu analiz eder ve toplu bulgular döner. |
| `testcase_normalize` | Gherkin, Markdown, JSON veya düz metni QA-MCP şemasına çevirir. |
| `testcase_to_xray` | Tek test case'i Xray uyumlu JSON payload'ına dönüştürür. |
| `testcase_to_xray_batch` | Birden fazla test case'i toplu Xray payload'ına dönüştürür. |
| `suite_compose` | Smoke, Sanity, Regression, E2E, Integration veya Performance suite oluşturur. |
| `suite_coverage_report` | Gereksinim, modül, risk ve senaryo kapsam raporları üretir. |
| `xray_get_mapping_template` | Önerilen QA-MCP → Xray alan eşleme şablonunu döner. |

Bu dokuz tool saf fonksiyondur: hiçbir şey kalıcılaştırmaz, dış sisteme çıkmaz, tekrar çağrılması bir şey değiştirmez. Read-only işaretlidirler, istemciler onay sormak zorunda kalmaz.

### Tool'lar — Jira/Xray tenant bağlandığında yayınlanır

| Tool | Gereksinim | Amaç |
|------|-----------|------|
| `xray_verify_connection` | `QA_MCP_XRAY_ENABLED` | Kimlik bilgilerini doğrular, hangi hesaba ait olduğunu bildirir. |
| `xray_get_test` | `QA_MCP_XRAY_ENABLED` | Jira'dan tek bir Xray test issue'sunu getirir. |
| `xray_search_tests` | `QA_MCP_XRAY_ENABLED` | JQL ile test arar veya projedeki testleri listeler. |
| `xray_create_test` | `QA_MCP_ENABLE_WRITE_TOOLS` | Jira'da Xray test issue'su **oluşturur**. |

İlk üçü salt okunurdur. Jira'da değişiklik yapan tek tool `xray_create_test`'tir: yazma açıkça etkinleştirilmedikçe hiç yayınlanmaz, read-only olmayan olarak işaretlidir (istemciler onay ister) ve istemci her çağrıda bayrağı yeniden kontrol eder.

### Resource'lar (Kaynaklar)

| URI | Amaç |
|-----|------|
| `qa://standards/testcase/v1` | Kanonik QA-MCP test case standardı. |
| `qa://checklists/lint-rules/v1` | Lint kuralları, cezalar ve puanlama mantığı. |
| `qa://mappings/xray/v1` | Xray eşleme referans dokümantasyonu. |
| `qa://examples/{quality}` | Örnek test case'ler; `good` iyi örnekler, `bad` anti-pattern'ler. |

`qa://examples/{quality}` bir resource template'tir — istemciler `quality` argümanını tamamlayabilir.

### Prompt'lar

| Prompt | Amaç |
|--------|------|
| `create-manual-test` | LLM'i yapılandırılmış manuel test oluşturmaya yönlendirir. |
| `select-smoke-tests` | Mevcut havuzdan optimal smoke suite seçmeye yardım eder. |
| `generate-negative-scenarios` | Sağlam negatif/edge-case senaryo üretimini yönlendirir. |
| `review-test-coverage` | Mevcut test varlıklarını kapsam boşlukları için analiz eder. |

## ⚙️ Mimari ve Yapılandırma

  - **Transport:** standart girdi/çıktı (`stdio`).
  - **Varsayılan olarak çevrimdışı:** dokuz analiz tool'u hiç soket açmaz. Jira/Xray bağlantısı opsiyoneldir ve başlangıçta doğrulanır.
  - **Yapılandırma:** tamamen ortam değişkeni tabanlı — fork edilecek config dosyası, düzenlenecek kod yok.

**En sık kullanılan ayarlar:**

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `QA_MCP_LOG_LEVEL` | `INFO` | Log seviyesi; loglar stderr'e gider. |
| `QA_MCP_AUDIT_LOG_ENABLED` | `true` | Her tool çağrısını loglar (yalnızca argüman adları, değerleri asla). |
| `QA_MCP_LINT_MINIMUM_SCORE` | `60` | Test case'in geçmesi için gereken skor. |
| `QA_MCP_LINT_DISABLED_RULES` | `[]` | Ekibinizin uygulamadığı kural id'leri (JSON dizi). |
| `QA_MCP_XRAY_ENABLED` | `false` | Jira/Xray bağlantısına izin verir. |
| `QA_MCP_XRAY_BASE_URL` | — | Jira temel adresi. |
| `QA_MCP_XRAY_DEPLOYMENT` | `cloud` | `cloud` veya `server`; hangi Xray API'sinin kullanılacağını belirler. |
| `QA_MCP_XRAY_API_TOKEN` | — | Jira API token veya personal access token. |
| `QA_MCP_XRAY_CLIENT_ID` / `_CLIENT_SECRET` | — | Xray Cloud API Key; Cloud'da test adımları için gerekli. |
| `QA_MCP_ENABLE_WRITE_TOOLS` | `false` | Jira'ya yazan `xray_create_test` tool'unu yayınlar. |

Tam referans — Jira Cloud ve Server/Data Center kimlik doğrulama farkları, tenant'a özel custom field id'leri ve kimlik bilgisi yönetimi dahil — **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)** ve [`.env.example`](.env.example) dosyalarındadır.

## 🐳 Docker Dağıtımı

Resmî imaj Docker Hub'da: `atakanemree/qa-mcp`

```bash
# Paketlenmiş CLI'yı doğrula
docker run --rm atakanemree/qa-mcp:latest --version

# MCP server'ı stdio modunda çalıştır
docker run -i --rm atakanemree/qa-mcp:latest

# Kendi tenant yapılandırmanızla
docker run -i --rm --env-file .env atakanemree/qa-mcp:latest

# Docker Compose kullanımı
docker compose up qa-mcp
docker compose --profile dev up qa-mcp-dev
```

Token'ları `--env-file` ile veya orkestratörünüzün secret mekanizmasıyla geçirin — imaja gömmeyin.

## 🔄 1.x'ten Geçiş

| Değişiklik | Ne yapmalı |
|-----------|-----------|
| **mcp 2.x** SDK gerekir | `pip install --upgrade qa-mcp` gerekeni kurar. MCP istemcilerinde değişiklik gerekmez: wire formatı aynıdır. |
| Ortam değişkenleri `QA_MCP_*` öneki aldı | Hiçbir şey kırılmaz — 1.x'teki öneksiz adlar (`LOG_LEVEL`, `AUDIT_LOG_ENABLED`, `ENABLE_WRITE_TOOLS`) hâlâ kabul edilir. Önekli adlar önceliklidir. |
| Noktalı tool alias'ları (`testcase.lint`) artık yayınlanmıyor | Eski bir istemci hâlâ çağırıyorsa `QA_MCP_LEGACY_TOOL_ALIASES=true` ayarlayın. |
| `ENABLE_WRITE_TOOLS` artık atıl değil | Jira'ya yazan bir tool yayınlar ve tenant yapılandırılmamışsa başlangıçta reddedilir. Bilinçli değilseniz kapalı bırakın. |
| Kütüphane olarak `result[0].text` okuyan kod | Tool sonuçları artık yapısal içerik olarak döner; sonuç nesnesini doğrudan okuyun. MCP istemcileri etkilenmez. |

Yükselttikten sonra `qa-mcp --check-config` çalıştırın — yapılandırmanızın tam olarak neyi yayınladığını bildirir.

## 📚 Dokümantasyon

  - **[USAGE.md](USAGE.md):** Detaylı kullanım örnekleri ve request payload'ları.
  - **[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md):** Kendi Jira/Xray tenant'ınızı ve kalite eşiğinizi bağlama.
  - **[docs/CI-CD.md](docs/CI-CD.md):** Jenkins pipeline ve SonarQube analiz kurulumu.
  - **[docs/MCP-2.x-MIGRATION.md](docs/MCP-2.x-MIGRATION.md):** mcp 2.x SDK geçişinin kaydı.
  - **[docs/PUBLISHING.md](docs/PUBLISHING.md):** Paket ve release yayın süreci.
  - **[CONTRIBUTING.md](CONTRIBUTING.md):** Katkı akışı ve kalite kontrolleri.
  - **[CHANGELOG.md](CHANGELOG.md):** Sürüm geçmişi.

## 🗺️ Yol Haritası

  - **v2'de tamamlandı:** mcp 2.x SDK üzerinde tipli yapısal sonuçlar, ortam değişkeni tabanlı yapılandırma, salt okunur Jira/Xray entegrasyonu ve sıkı kilitli bir yazma uç noktası.
  - **Sırada:** daha zengin Xray işlemleri (test set, test plan, koşum sonuçları) ve canlı tenant'a toplu import.
  - **Daha sonra:** Xray dışındaki QA sistemleri için entegrasyonlar ve opsiyonel ağ transport'ları.

## 📄 Lisans

**MIT License** ile yayınlanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.
