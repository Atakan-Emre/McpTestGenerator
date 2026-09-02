# QA-MCP Usage Guide / Kullanım Kılavuzu

<div align="center">

**🇬🇧 English** | [🇹🇷 Türkçe](#-türkçe-kullanım-kılavuzu)

</div>

---

# 🇬🇧 English Usage Guide

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation Options](#-installation-options)
- [MCP Client Integration](#-mcp-client-integration)
- [Tool Usage Examples](#-tool-usage-examples)
- [Resource Access](#-resource-access)
- [Prompt Templates](#-prompt-templates)
- [Configuration](#️-configuration)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
pip install -e .
```

### 2. Start MCP Server

```bash
qa-mcp
```

### 3. Connect to Cursor/Claude Desktop

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

---

## 📦 Installation Options

### Option 1: With pip (Recommended)

```bash
pip install qa-mcp
```

### Option 2: From Source

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
pip install -e .
```

### Option 3: With Docker

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i --rm atakanemree/qa-mcp:latest
```

### Development Environment

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 🔌 MCP Client Integration

### Cursor IDE

1. Open Cursor settings
2. Edit `mcp.json` file:

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "/path/to/.venv/bin/qa-mcp",
      "args": []
    }
  }
}
```

### Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

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

### MCP with Docker

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

---

## 🔧 Tool Usage Examples

Tool names use underscores to stay compatible with Claude Desktop's MCP validator.

### 1. Test Case Generation (`testcase_generate`)

**Purpose:** Generates standard test cases from feature and acceptance criteria.

**Example Request:**

```json
{
  "feature": "User Login",
  "acceptance_criteria": [
    "User can login with valid email and password",
    "Account should be locked after 3 failed attempts",
    "Forgot password link should work"
  ],
  "module": "auth",
  "risk_level": "high",
  "include_negative": true
}
```

**Example Output:**

```json
{
  "testcases": [
    {
      "id": "TC-A1B2C3D4",
      "title": "User Login - Valid email and password login",
      "description": "This test verifies that the 'User Login' feature works according to acceptance criteria...",
      "risk_level": "high",
      "priority": "P1",
      "steps": [...]
    }
  ],
  "coverage_summary": {
    "positive_scenarios": 3,
    "negative_scenarios": 7,
    "boundary_tests": 2
  },
  "total_generated": 12
}
```

### 2. Test Case Lint (`testcase_lint`)

**Purpose:** Analyzes test case quality, returns score and improvement suggestions.

**Example Request:**

```json
{
  "testcase": {
    "title": "Login test",
    "description": "Login test",
    "preconditions": [],
    "steps": [
      {"step_number": 1, "action": "Login", "expected_result": "OK"}
    ],
    "expected_result": "Works"
  }
}
```

**Example Output:**

```json
{
  "score": 35,
  "grade": "F",
  "passed": false,
  "schema_valid": false,
  "schema_errors": ["title: String should have at least 10 characters"],
  "issues": [
    {
      "severity": "error",
      "field": "preconditions",
      "message": "Preconditions not defined",
      "suggestion": "List the initial states required for the test to run"
    }
  ],
  "improvement_plan": [
    {"priority": 1, "action": "Add preconditions", "impact": "high"}
  ]
}
```

### 3. Batch Lint (`testcase_lint_batch`)

**Purpose:** Analyzes multiple test cases and returns aggregate quality findings.

**Example Request:**

```json
{
  "testcases": [
    {
      "title": "Valid login",
      "description": "Verify successful login",
      "preconditions": ["User account exists"],
      "steps": [
        {"step_number": 1, "action": "Submit valid credentials", "expected_result": "Dashboard opens"}
      ],
      "expected_result": "User is authenticated"
    },
    {
      "title": "Login test",
      "description": "Login test",
      "preconditions": [],
      "steps": [
        {"step_number": 1, "action": "Login", "expected_result": "OK"}
      ],
      "expected_result": "Works"
    }
  ],
  "strict_mode": true
}
```

### 4. Format Conversion (`testcase_normalize`)

**Purpose:** Converts test cases from Gherkin, Markdown, or plain text to standard format.

**Gherkin Example:**

```json
{
  "input_data": "Feature: User Login\nScenario: Valid login\nGiven user is registered\nWhen user enters credentials\nThen user is logged in",
  "source_format": "gherkin"
}
```

### 5. Xray Conversion (`testcase_to_xray`)

**Purpose:** Converts standard test case to Jira/Xray import format.

**Example Request:**

```json
{
  "testcase": {
    "title": "Login Test",
    "description": "Test login functionality",
    "preconditions": ["User exists"],
    "steps": [
      {"step_number": 1, "action": "Navigate to login", "expected_result": "Form displayed"}
    ],
    "expected_result": "User logged in",
    "priority": "P1"
  },
  "project_key": "MYPROJ",
  "test_type": "Manual"
}
```

### 6. Batch Xray Conversion (`testcase_to_xray_batch`)

**Purpose:** Converts multiple standard test cases into Xray-compatible bulk payloads.

**Example Request:**

```json
{
  "testcases": [
    {
      "title": "Valid login",
      "description": "Verify successful login",
      "preconditions": ["User exists"],
      "steps": [
        {"step_number": 1, "action": "Submit valid credentials", "expected_result": "Dashboard opens"}
      ],
      "expected_result": "User logged in"
    },
    {
      "title": "Locked account",
      "description": "Verify blocked user behavior",
      "preconditions": ["Locked user exists"],
      "steps": [
        {"step_number": 1, "action": "Submit locked account credentials", "expected_result": "Access is denied"}
      ],
      "expected_result": "User remains blocked"
    }
  ],
  "project_key": "MYPROJ",
  "test_type": "Manual"
}
```

### 7. Xray Mapping Template (`xray_get_mapping_template`)

**Purpose:** Returns the recommended QA-MCP to Xray custom field mapping template.

**Example Request:**

```json
{}
```

### 8. Suite Composition (`suite_compose`)

**Purpose:** Creates a suite from a test case list.

`target` accepts `smoke`, `sanity`, `regression`, `e2e`, `integration` or
`performance`. Each has its own priority, risk, duration and size limits.

```json
{
  "testcases": [...],
  "target": "smoke",
  "sprint": "Sprint 15",
  "max_duration_minutes": 15
}
```

### 9. Coverage Report (`suite_coverage_report`)

**Purpose:** Reports requirement and module coverage across a test case collection.

**Example Request:**

```json
{
  "testcases": [...],
  "requirements": ["AUTH-001", "AUTH-002", "AUTH-003"],
  "modules": ["auth", "session"]
}
```

---

## 📚 Resource Access

| URI | Description |
|-----|-------------|
| `qa://standards/testcase/v1` | Test case writing standard |
| `qa://checklists/lint-rules/v1` | Lint rules and scoring |
| `qa://mappings/xray/v1` | Xray field mappings |
| `qa://examples/good` | Good test case examples |
| `qa://examples/bad` | Bad test case examples (anti-patterns) |

---

## 💬 Prompt Templates

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `create-manual-test` | Manual test creation guide | feature, acceptance_criteria |
| `select-smoke-tests` | Smoke test selection guide | testcases, max_duration |
| `generate-negative-scenarios` | Negative scenario generation | feature, positive_testcases |
| `review-test-coverage` | Coverage analysis guide | testcases, requirements |

---

## ⚙️ Configuration

### Environment Variables

QA-MCP runs with no configuration at all. Everything below is optional; the
full reference, including connecting a Jira/Xray tenant, is in
**[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)**.

| Variable | Default | Description |
|----------|---------|-------------|
| `QA_MCP_LOG_LEVEL` | `INFO` | Log level; logs go to stderr |
| `QA_MCP_AUDIT_LOG_ENABLED` | `true` | Log every tool call (argument names only) |
| `QA_MCP_LEGACY_TOOL_ALIASES` | `false` | Also publish the pre-1.0.3 dotted tool names |
| `QA_MCP_LINT_MINIMUM_SCORE` | `60` | Score a test case needs to pass |
| `QA_MCP_LINT_STRICT_MINIMUM_SCORE` | `75` | Score required in strict mode |
| `QA_MCP_LINT_MAX_STEPS` | `15` | Steps beyond which a test case is flagged |
| `QA_MCP_LINT_DISABLED_RULES` | `[]` | Rule ids to skip, as a JSON array |
| `QA_MCP_XRAY_ENABLED` | `false` | Allow QA-MCP to contact Jira/Xray |
| `QA_MCP_XRAY_BASE_URL` | — | Jira base URL |
| `QA_MCP_XRAY_AUTH_MODE` | `token` | `basic` (Cloud: email + token) or `token` (Server/DC bearer) |
| `QA_MCP_XRAY_API_TOKEN` | — | API token or personal access token |
| `QA_MCP_XRAY_PROJECT_KEY` | — | Default Jira project key |
| `QA_MCP_XRAY_CUSTOM_FIELDS` | `{}` | QA-MCP field → Jira custom field id, as JSON |
| `QA_MCP_ENABLE_WRITE_TOOLS` | `false` | Publish `xray_create_test`, which writes to Jira |

```bash
qa-mcp --check-config
```

validates the configuration, prints what the deployment would expose, and exits
non-zero when something is wrong. A tenant that is switched on but incomplete
fails here rather than on the first tool call.

**Conditional tools.** `xray_verify_connection`, `xray_get_test` and
`xray_search_tests` appear only once a tenant is configured;
`xray_create_test` appears only when `QA_MCP_ENABLE_WRITE_TOOLS` is true.

**Runtime note:** QA-MCP runs in `stdio` mode only. The 1.x variable names
(`LOG_LEVEL`, `AUDIT_LOG_ENABLED`, `ENABLE_WRITE_TOOLS`) are still accepted so
existing deployments keep working, but the prefixed names above are the
documented ones.

---

## 🔍 Troubleshooting

### 1. "qa-mcp command not found"

```bash
pip show qa-mcp
# or use full path
python -m qa_mcp.server
```

### 2. MCP client cannot start the server

- Make sure the configured `command` path is valid
- Run `qa-mcp` manually once to verify the CLI starts
- Check the MCP client config file for JSON mistakes
- Restart Cursor/Claude Desktop after config changes

### Debug Mode

```bash
LOG_LEVEL=debug qa-mcp
```

---

# 🇹🇷 Türkçe Kullanım Kılavuzu

## 📋 İçindekiler

- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Kurulum Seçenekleri](#-kurulum-seçenekleri)
- [MCP İstemci Entegrasyonu](#-mcp-i̇stemci-entegrasyonu)
- [Tool Kullanım Örnekleri](#-tool-kullanım-örnekleri-1)
- [Resource Erişimi](#-resource-erişimi)
- [Prompt Şablonları](#-prompt-şablonları)
- [Yapılandırma](#️-yapılandırma-1)
- [Sorun Giderme](#-sorun-giderme)

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
pip install -e .
```

### 2. MCP Server'ı Başlat

```bash
qa-mcp
```

### 3. Cursor/Claude Desktop'a Bağla

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

---

## 📦 Kurulum Seçenekleri

### Seçenek 1: pip ile (Önerilen)

```bash
pip install qa-mcp
```

### Seçenek 2: Kaynak Koddan

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
pip install -e .
```

### Seçenek 3: Docker ile

```bash
docker pull atakanemree/qa-mcp:latest
docker run -i --rm atakanemree/qa-mcp:latest
```

### Geliştirme Ortamı

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 🔌 MCP İstemci Entegrasyonu

### Cursor IDE

1. Cursor ayarlarını açın
2. `mcp.json` dosyasını düzenleyin:

```json
{
  "mcpServers": {
    "qa-mcp": {
      "command": "/path/to/.venv/bin/qa-mcp",
      "args": []
    }
  }
}
```

### Claude Desktop

`~/.claude/claude_desktop_config.json` dosyasına ekleyin:

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

### Docker ile MCP

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

---

## 🔧 Tool Kullanım Örnekleri

Tool adları Claude Desktop MCP doğrulayıcısıyla uyum için underscore kullanır.

### 1. Test Case Üretimi (`testcase_generate`)

**Amaç:** Feature ve acceptance criteria'dan standart test case üretir.

**Örnek İstek:**

```json
{
  "feature": "Kullanıcı Girişi",
  "acceptance_criteria": [
    "Geçerli email ve şifre ile giriş yapılabilmeli",
    "3 başarısız denemeden sonra hesap kilitlenmeli",
    "Şifremi unuttum linki çalışmalı"
  ],
  "module": "auth",
  "risk_level": "high",
  "include_negative": true
}
```

**Örnek Çıktı:**

```json
{
  "testcases": [
    {
      "id": "TC-A1B2C3D4",
      "title": "Kullanıcı Girişi - Geçerli email ve şifre ile giriş",
      "description": "Bu test, 'Kullanıcı Girişi' özelliğinin kabul kriterine göre çalıştığını doğrular...",
      "risk_level": "high",
      "priority": "P1",
      "steps": [...]
    }
  ],
  "coverage_summary": {
    "positive_scenarios": 3,
    "negative_scenarios": 7,
    "boundary_tests": 2
  },
  "total_generated": 12
}
```

### 2. Test Case Lint (`testcase_lint`)

**Amaç:** Test case kalitesini analiz eder, skor ve iyileştirme önerileri döner.

**Örnek İstek:**

```json
{
  "testcase": {
    "title": "Login test",
    "description": "Login test",
    "preconditions": [],
    "steps": [
      {"step_number": 1, "action": "Login", "expected_result": "OK"}
    ],
    "expected_result": "Works"
  }
}
```

**Örnek Çıktı:**

```json
{
  "score": 35,
  "grade": "F",
  "passed": false,
  "schema_valid": false,
  "schema_errors": ["title: String should have at least 10 characters"],
  "issues": [
    {
      "severity": "error",
      "field": "preconditions",
      "message": "Ön koşullar tanımlanmamış",
      "suggestion": "Test'in çalışması için gerekli başlangıç durumlarını listeleyin"
    }
  ],
  "improvement_plan": [
    {"priority": 1, "action": "Ön koşullar ekleyin", "impact": "high"}
  ]
}
```

### 3. Toplu Lint (`testcase_lint_batch`)

**Amaç:** Birden fazla test case'i analiz eder ve toplu kalite bulguları döner.

**Örnek İstek:**

```json
{
  "testcases": [
    {
      "title": "Valid login",
      "description": "Verify successful login",
      "preconditions": ["User account exists"],
      "steps": [
        {"step_number": 1, "action": "Submit valid credentials", "expected_result": "Dashboard opens"}
      ],
      "expected_result": "User is authenticated"
    },
    {
      "title": "Login test",
      "description": "Login test",
      "preconditions": [],
      "steps": [
        {"step_number": 1, "action": "Login", "expected_result": "OK"}
      ],
      "expected_result": "Works"
    }
  ],
  "strict_mode": true
}
```

### 4. Format Dönüştürme (`testcase_normalize`)

**Amaç:** Gherkin, Markdown veya düz metin formatındaki test case'leri standart formata çevirir.

**Gherkin Örneği:**

```json
{
  "input_data": "Feature: User Login\nScenario: Valid login\nGiven user is registered\nWhen user enters credentials\nThen user is logged in",
  "source_format": "gherkin"
}
```

### 5. Xray Dönüşümü (`testcase_to_xray`)

**Amaç:** Standart test case'i Jira/Xray import formatına çevirir.

**Örnek İstek:**

```json
{
  "testcase": {
    "title": "Login Test",
    "description": "Test login functionality",
    "preconditions": ["User exists"],
    "steps": [
      {"step_number": 1, "action": "Navigate to login", "expected_result": "Form displayed"}
    ],
    "expected_result": "User logged in",
    "priority": "P1"
  },
  "project_key": "MYPROJ",
  "test_type": "Manual"
}
```

### 6. Toplu Xray Dönüşümü (`testcase_to_xray_batch`)

**Amaç:** Birden fazla standart test case'i toplu Xray payload formatına çevirir.

**Örnek İstek:**

```json
{
  "testcases": [
    {
      "title": "Valid login",
      "description": "Verify successful login",
      "preconditions": ["User exists"],
      "steps": [
        {"step_number": 1, "action": "Submit valid credentials", "expected_result": "Dashboard opens"}
      ],
      "expected_result": "User logged in"
    },
    {
      "title": "Locked account",
      "description": "Verify blocked user behavior",
      "preconditions": ["Locked user exists"],
      "steps": [
        {"step_number": 1, "action": "Submit locked account credentials", "expected_result": "Access is denied"}
      ],
      "expected_result": "User remains blocked"
    }
  ],
  "project_key": "MYPROJ",
  "test_type": "Manual"
}
```

### 7. Xray Alan Eşleme Şablonu (`xray_get_mapping_template`)

**Amaç:** Önerilen QA-MCP → Xray custom field eşleme şablonunu döner.

**Örnek İstek:**

```json
{}
```

### 8. Suite Kompozisyonu (`suite_compose`)

`target` değerleri: `smoke`, `sanity`, `regression`, `e2e`, `integration`,
`performance`. Her birinin kendi öncelik, risk, süre ve adet limitleri vardır.

**Amaç:** Test case listesinden Smoke/Regression/E2E suite oluşturur.

```json
{
  "testcases": [...],
  "target": "smoke",
  "sprint": "Sprint 15",
  "max_duration_minutes": 15
}
```

### 9. Coverage Raporu (`suite_coverage_report`)

**Amaç:** Test case koleksiyonu üzerinde requirement ve modül kapsamını raporlar.

**Örnek İstek:**

```json
{
  "testcases": [...],
  "requirements": ["AUTH-001", "AUTH-002", "AUTH-003"],
  "modules": ["auth", "session"]
}
```

---

## 📚 Resource Erişimi

| URI | Açıklama |
|-----|----------|
| `qa://standards/testcase/v1` | Test case yazım standardı |
| `qa://checklists/lint-rules/v1` | Lint kuralları ve puanlama |
| `qa://mappings/xray/v1` | Xray alan eşlemeleri |
| `qa://examples/good` | İyi test case örnekleri |
| `qa://examples/bad` | Kötü test case örnekleri (anti-patterns) |

---

## 💬 Prompt Şablonları

| Prompt | Açıklama | Argümanlar |
|--------|----------|------------|
| `create-manual-test` | Manual test oluşturma rehberi | feature, acceptance_criteria |
| `select-smoke-tests` | Smoke test seçim rehberi | testcases, max_duration |
| `generate-negative-scenarios` | Negatif senaryo üretimi | feature, positive_testcases |
| `review-test-coverage` | Kapsam analizi rehberi | testcases, requirements |

---

## ⚙️ Yapılandırma

### Environment Variables

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `QA_MCP_LOG_LEVEL` | `INFO` | Log seviyesi; loglar stderr'e gider |
| `QA_MCP_AUDIT_LOG_ENABLED` | `true` | Her tool çağrısını loglar (yalnızca argüman adları) |
| `QA_MCP_LEGACY_TOOL_ALIASES` | `false` | 1.0.3 öncesi noktalı tool adlarını da yayınlar |
| `QA_MCP_LINT_MINIMUM_SCORE` | `60` | Test case'in geçmesi için gereken skor |
| `QA_MCP_LINT_MAX_STEPS` | `15` | Bu adım sayısını aşan test case işaretlenir |
| `QA_MCP_LINT_DISABLED_RULES` | `[]` | Uygulanmayacak kural id'leri (JSON dizi) |
| `QA_MCP_XRAY_ENABLED` | `false` | Jira/Xray bağlantısına izin verir |
| `QA_MCP_XRAY_BASE_URL` | — | Jira temel adresi |
| `QA_MCP_XRAY_AUTH_MODE` | `token` | `basic` (Cloud: e-posta + token) veya `token` (Server/DC bearer) |
| `QA_MCP_XRAY_API_TOKEN` | — | API token veya personal access token |
| `QA_MCP_XRAY_PROJECT_KEY` | — | Varsayılan Jira proje anahtarı |
| `QA_MCP_XRAY_CUSTOM_FIELDS` | `{}` | QA-MCP alanı → Jira custom field id (JSON) |
| `QA_MCP_ENABLE_WRITE_TOOLS` | `false` | Jira'ya yazan `xray_create_test` tool'unu yayınlar |

Tam referans ve tenant bağlama adımları için:
**[docs/ENTERPRISE-SETUP.md](docs/ENTERPRISE-SETUP.md)**.

`qa-mcp --check-config` yapılandırmayı doğrular, neyin yayınlanacağını yazdırır
ve hatalıysa sıfırdan farklı kodla çıkar. 1.x'teki öneksiz adlar
(`LOG_LEVEL` vb.) hâlâ kabul edilir.

**Runtime notu:** QA-MCP şu anda yalnızca `stdio` modunda çalışır. Container image içinde HTTP ile ilgili placeholder environment variable'lar bulunabilir, ancak bunlar mevcut sürümde aktif runtime özelliği değildir.

---

## 🔍 Sorun Giderme

### 1. "qa-mcp command not found"

```bash
pip show qa-mcp
# veya tam yol kullanın
python -m qa_mcp.server
```

### 2. MCP istemcisi server'ı başlatamıyor

- Tanımlanan `command` yolunun geçerli olduğundan emin olun
- CLI'nin açıldığını doğrulamak için `qa-mcp` komutunu bir kez manuel çalıştırın
- MCP istemci config dosyasında JSON hatası olmadığını kontrol edin
- Config değişikliğinden sonra Cursor/Claude Desktop'ı yeniden başlatın

### Debug Modu

```bash
LOG_LEVEL=debug qa-mcp
```

---

## 📄 License / Lisans

MIT License - Copyright (c) 2024-2026 [Atakan Emre](https://github.com/Atakan-Emre)

### Support / Destek

- GitHub Issues: [https://github.com/Atakan-Emre/McpTestGenerator/issues](https://github.com/Atakan-Emre/McpTestGenerator/issues)
