# QA-MCP Kullanım Kılavuzu

Bu doküman, QA-MCP MCP Server'ının nasıl kurulacağını ve kullanılacağını detaylı olarak açıklar.

## 📋 İçindekiler

- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Kurulum Seçenekleri](#-kurulum-seçenekleri)
- [MCP İstemci Entegrasyonu](#-mcp-i̇stemci-entegrasyonu)
- [Tool Kullanım Örnekleri](#-tool-kullanım-örnekleri)
- [Resource Erişimi](#-resource-erişimi)
- [Prompt Şablonları](#-prompt-şablonları)
- [Yapılandırma](#️-yapılandırma)
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
docker pull atakanemre/qa-mcp:1.0.0
docker run -i --rm atakanemre/qa-mcp:1.0.0
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
      "args": ["run", "-i", "--rm", "atakanemre/qa-mcp:1.0.0"]
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
  "include_negative": true,
  "include_boundary": true
}
```

**Örnek Çıktı:**

```json
{
  "testcases": [
    {
      "id": "TC-A1B2C3D4",
      "title": "Kullanıcı Girişi - Geçerli email ve şifre ile giriş",
      "description": "Bu test, 'Kullanıcı Girişi' özelliğinin şu kabul kriterine göre çalıştığını doğrular...",
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
    },
    {
      "severity": "warning",
      "field": "expected_result",
      "message": "Expected result belirsiz",
      "suggestion": "Spesifik ve doğrulanabilir sonuç yazın"
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

**Örnek Çıktı:**

```json
{
  "xray_payload": {
    "testtype": "Manual",
    "fields": {
      "project": {"key": "MYPROJ"},
      "summary": "Login Test",
      "issuetype": {"name": "Test"},
      "priority": {"name": "High"}
    },
    "steps": [
      {"action": "Navigate to login", "result": "Form displayed"}
    ]
  },
  "field_mapping_report": {
    "mapped_fields": ["title", "description", "priority", "steps"],
    "unmapped_fields": ["risk_level"]
  }
}
```

### 5. Suite Kompozisyonu (`suite.compose`)

**Amaç:** Test case listesinden Smoke/Regression/E2E suite oluşturur.

**Örnek İstek:**

```json
{
  "testcases": [...],
  "target": "smoke",
  "sprint": "Sprint 15",
  "max_duration_minutes": 15
}
```

### 6. Kapsam Raporu (`suite.coverage_report`)

**Amaç:** Test suite için kapsam analizi yapar.

**Örnek İstek:**

```json
{
  "testcases": [...],
  "requirements": ["REQ-001", "REQ-002", "REQ-003"],
  "modules": ["auth", "payment", "cart"]
}
```

---

## 📚 Resource Erişimi

MCP Resources, LLM'lerin erişebileceği statik referans verileridir.

### Mevcut Resources

| URI | Açıklama |
|-----|----------|
| `qa://standards/testcase/v1` | Test case yazım standardı |
| `qa://checklists/lint-rules/v1` | Lint kuralları ve puanlama |
| `qa://mappings/xray/v1` | Xray alan eşlemeleri |
| `qa://examples/good` | İyi test case örnekleri |
| `qa://examples/bad` | Kötü test case örnekleri (anti-patterns) |

### Resource Kullanımı

LLM istemcisi resource'lara şu şekilde erişebilir:

```
"qa://standards/testcase/v1 resource'unu oku ve test case standardını öğren"
```

---

## 💬 Prompt Şablonları

### Mevcut Prompt'lar

| Prompt | Açıklama | Argümanlar |
|--------|----------|------------|
| `create-manual-test` | Manual test oluşturma rehberi | feature, acceptance_criteria |
| `select-smoke-tests` | Smoke test seçim rehberi | testcases, max_duration |
| `generate-negative-scenarios` | Negatif senaryo üretimi | feature, positive_testcases |
| `review-test-coverage` | Kapsam analizi rehberi | testcases, requirements |

### Prompt Kullanımı

```
"create-manual-test prompt'unu kullan, feature: 'Ödeme sistemi'"
```

---

## ⚙️ Yapılandırma

### Environment Variables

| Değişken | Default | Açıklama |
|----------|---------|----------|
| `LOG_LEVEL` | `info` | Log seviyesi: debug, info, warning, error |
| `ENABLE_WRITE_TOOLS` | `false` | Jira/Xray yazma tool'larını etkinleştirir |
| `AUDIT_LOG_ENABLED` | `true` | Tool çağrılarını loglar |
| `HTTP_ENABLED` | `false` | HTTP transport'u etkinleştirir |
| `HTTP_BIND_HOST` | `127.0.0.1` | HTTP bind adresi |
| `HTTP_PORT` | `8080` | HTTP port numarası |

### Örnek Yapılandırma

```bash
export LOG_LEVEL=debug
export ENABLE_WRITE_TOOLS=false
qa-mcp
```

---

## 🔍 Sorun Giderme

### Sık Karşılaşılan Sorunlar

#### 1. "qa-mcp command not found"

```bash
# pip install yolunu kontrol edin
pip show qa-mcp

# veya tam yol kullanın
python -m qa_mcp.server
```

#### 2. "Connection refused" (MCP istemcisinde)

- Server'ın çalıştığından emin olun
- mcp.json yollarını kontrol edin
- Cursor/Claude Desktop'ı yeniden başlatın

#### 3. Lint skoru düşük çıkıyor

- `qa://standards/testcase/v1` resource'unu inceleyin
- `qa://examples/good` örneklerini referans alın
- `improvement_plan` içindeki önerileri uygulayın

#### 4. Xray import başarısız

- `project_key`'in doğru olduğundan emin olun
- `field_mapping_report` içindeki uyarıları kontrol edin
- Custom field mapping gerekebilir

### Debug Modu

```bash
LOG_LEVEL=debug qa-mcp
```

### Destek

- GitHub Issues: [https://github.com/Atakan-Emre/McpTestGenerator/issues](https://github.com/Atakan-Emre/McpTestGenerator/issues)
- Dokümantasyon: [README.md](README.md)

---

## 📄 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

Copyright (c) 2024-2026 [Atakan Emre](https://github.com/Atakan-Emre)
