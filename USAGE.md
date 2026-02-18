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

### 1. Test Case Generation (`testcase.generate`)

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

### 2. Test Case Lint (`testcase.lint`)

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

### 3. Format Conversion (`testcase.normalize`)

**Purpose:** Converts test cases from Gherkin, Markdown, or plain text to standard format.

**Gherkin Example:**

```json
{
  "input_data": "Feature: User Login\nScenario: Valid login\nGiven user is registered\nWhen user enters credentials\nThen user is logged in",
  "source_format": "gherkin"
}
```

### 4. Xray Conversion (`testcase.to_xray`)

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

### 5. Suite Composition (`suite.compose`)

**Purpose:** Creates Smoke/Regression/E2E suite from test case list.

```json
{
  "testcases": [...],
  "target": "smoke",
  "sprint": "Sprint 15",
  "max_duration_minutes": 15
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

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `info` | Log level: debug, info, warning, error |
| `ENABLE_WRITE_TOOLS` | `false` | Enables Jira/Xray write tools |
| `AUDIT_LOG_ENABLED` | `true` | Logs tool calls |
| `HTTP_ENABLED` | `false` | Enables HTTP transport |
| `HTTP_PORT` | `8080` | HTTP port number |

---

## 🔍 Troubleshooting

### 1. "qa-mcp command not found"

```bash
pip show qa-mcp
# or use full path
python -m qa_mcp.server
```

### 2. "Connection refused" (in MCP client)

- Make sure server is running
- Check mcp.json paths
- Restart Cursor/Claude Desktop

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

### 1. Test Case Üretimi (`testcase.generate`)

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

### 2. Test Case Lint (`testcase.lint`)

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

### 3. Format Dönüştürme (`testcase.normalize`)

**Amaç:** Gherkin, Markdown veya düz metin formatındaki test case'leri standart formata çevirir.

**Gherkin Örneği:**

```json
{
  "input_data": "Feature: User Login\nScenario: Valid login\nGiven user is registered\nWhen user enters credentials\nThen user is logged in",
  "source_format": "gherkin"
}
```

### 4. Xray Dönüşümü (`testcase.to_xray`)

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

### 5. Suite Kompozisyonu (`suite.compose`)

**Amaç:** Test case listesinden Smoke/Regression/E2E suite oluşturur.

```json
{
  "testcases": [...],
  "target": "smoke",
  "sprint": "Sprint 15",
  "max_duration_minutes": 15
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
| `LOG_LEVEL` | `info` | Log seviyesi: debug, info, warning, error |
| `ENABLE_WRITE_TOOLS` | `false` | Jira/Xray yazma tool'larını etkinleştirir |
| `AUDIT_LOG_ENABLED` | `true` | Tool çağrılarını loglar |
| `HTTP_ENABLED` | `false` | HTTP transport'u etkinleştirir |
| `HTTP_PORT` | `8080` | HTTP port numarası |

---

## 🔍 Sorun Giderme

### 1. "qa-mcp command not found"

```bash
pip show qa-mcp
# veya tam yol kullanın
python -m qa_mcp.server
```

### 2. "Connection refused" (MCP istemcisinde)

- Server'ın çalıştığından emin olun
- mcp.json yollarını kontrol edin
- Cursor/Claude Desktop'ı yeniden başlatın

### Debug Modu

```bash
LOG_LEVEL=debug qa-mcp
```

---

## 📄 License / Lisans

MIT License - Copyright (c) 2024-2026 [Atakan Emre](https://github.com/Atakan-Emre)

### Support / Destek

- GitHub Issues: [https://github.com/Atakan-Emre/McpTestGenerator/issues](https://github.com/Atakan-Emre/McpTestGenerator/issues)
