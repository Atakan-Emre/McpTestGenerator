# QA-MCP: Test Standardization & Orchestration Server

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Atakan-Emre/McpTestGenerator/releases)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](https://github.com/Atakan-Emre/McpTestGenerator/blob/main/LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-26%20passed-brightgreen.svg)](https://github.com/Atakan-Emre/McpTestGenerator/actions)

**LLM istemcilerinin bağlanıp standart test case üretme, kalite kontrol, Xray formatına çevirme ve test set kompozisyonu yapabildiği bir MCP sunucusu.**

[Kurulum](#-kurulum) • [Kullanım](#-kullanım) • [Tools](#-tools) • [Resources](#-resources) • [Docker](#-docker) • [Güvenlik](#-güvenlik) • [Detaylı Kılavuz](USAGE.md)

</div>

---

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

---

## 📦 Kurulum

### pip ile

```bash
pip install qa-mcp
```

### Kaynak koddan

```bash
git clone https://github.com/Atakan-Emre/McpTestGenerator.git
cd McpTestGenerator
pip install -e .
```

### Docker ile

```bash
docker pull atakanemre/qa-mcp:latest
docker run -i atakanemre/qa-mcp:latest
```

---

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
      "args": ["run", "-i", "--rm", "atakanemre/qa-mcp:1.0.0"]
    }
  }
}
```

---

## 🔧 Tools

### `testcase.generate`

Feature açıklaması ve acceptance criteria'dan standart test case üretir.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `feature` | string | ✅ | Feature açıklaması |
| `acceptance_criteria` | string[] | ✅ | Kabul kriterleri listesi |
| `module` | string | ❌ | Modül/bileşen adı |
| `risk_level` | enum | ❌ | `low`, `medium`, `high`, `critical` |
| `include_negative` | boolean | ❌ | Negatif senaryolar dahil mi (default: true) |

**Örnek:**

```json
{
  "feature": "Kullanıcı girişi",
  "acceptance_criteria": [
    "Geçerli email ve şifre ile giriş yapılabilmeli",
    "3 başarısız denemeden sonra hesap kilitlenmeli"
  ],
  "module": "auth",
  "risk_level": "high"
}
```

---

### `testcase.lint`

Mevcut test case'i analiz eder, eksikleri ve iyileştirme önerilerini döner.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `testcase` | object | ✅ | Analiz edilecek test case |

**Çıktı:**

```json
{
  "score": 72,
  "issues": [
    {"severity": "error", "field": "preconditions", "message": "Ön koşullar tanımlanmamış"},
    {"severity": "warning", "field": "test_data", "message": "Boundary değerler eksik"}
  ],
  "suggestions": ["Negatif senaryo ekleyin", "Expected result daha spesifik olmalı"]
}
```

---

### `testcase.normalize`

Farklı formatlardaki test case'leri standart formata çevirir.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `input` | string/object | ✅ | Normalize edilecek test case |
| `source_format` | enum | ❌ | `auto`, `markdown`, `gherkin`, `json` |

---

### `testcase.to_xray`

Standart test case'i Xray import formatına çevirir.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `testcase` | object | ✅ | Dönüştürülecek test case |
| `project_key` | string | ✅ | Jira proje anahtarı |
| `test_type` | enum | ❌ | `Manual`, `Automated`, `Generic` |

**Çıktı:**

```json
{
  "xray_payload": { "..." },
  "field_mapping_report": { "..." },
  "warnings": []
}
```

---

### `suite.compose`

Test case listesinden Smoke/Regression/E2E suite önerisi oluşturur.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `testcases` | object[] | ✅ | Test case listesi |
| `target` | enum | ✅ | `smoke`, `regression`, `e2e`, `sanity` |
| `sprint` | string | ❌ | Sprint adı/numarası |
| `max_duration_minutes` | number | ❌ | Maksimum suite süresi |

---

### `suite.coverage_report`

Test suite için kapsama raporu oluşturur.

**Parametreler:**

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `testcases` | object[] | ✅ | Test case listesi |
| `requirements` | string[] | ❌ | Kapsanacak gereksinimler |

---

## 📚 Resources

MCP Resources, LLM'in erişebileceği statik verilerdir:

| URI | Açıklama |
|-----|----------|
| `qa://standards/testcase/v1` | Test case standardı |
| `qa://checklists/lint-rules/v1` | Lint kuralları |
| `qa://mappings/xray/v1` | Xray alan eşlemesi |
| `qa://examples/good/*` | İyi test case örnekleri |
| `qa://examples/bad/*` | Kötü test case örnekleri |

---

## 💬 Prompts

Önceden tanımlanmış prompt şablonları:

| Prompt | Açıklama |
|--------|----------|
| `create-manual-test` | Xray Manual Test oluşturma |
| `select-smoke-tests` | Smoke test seçimi |
| `generate-negative-scenarios` | Negatif senaryo üretimi |
| `review-test-coverage` | Test kapsam analizi |

---

## 🐳 Docker

### Image Çekme

```bash
# Latest (demo için)
docker pull atakanemre/qa-mcp:latest

# Spesifik versiyon (üretim için önerilen)
docker pull atakanemre/qa-mcp:1.0.0

# Multi-arch (otomatik seçim)
docker pull atakanemre/qa-mcp:1.0.0  # linux/amd64 veya linux/arm64
```

### Çalıştırma

```bash
# Stdio mode (varsayılan, en güvenli)
docker run -i --rm atakanemre/qa-mcp:1.0.0

# Environment variables ile
docker run -i --rm \
  -e LOG_LEVEL=debug \
  -e ENABLE_WRITE_TOOLS=false \
  atakanemre/qa-mcp:1.0.0
```

### Docker MCP Gateway ile

```yaml
# docker-compose.yml
services:
  qa-mcp:
    image: atakanemre/qa-mcp:1.0.0
    environment:
      - ENABLE_WRITE_TOOLS=false
```

---

## 🔒 Güvenlik

### Transport

- **Varsayılan: stdio** - En güvenli, lokal süreç iletişimi
- **HTTP (opsiyonel)** - Origin doğrulaması, localhost bind, auth gerektirir

### Environment Variables

| Değişken | Default | Açıklama |
|----------|---------|----------|
| `ENABLE_WRITE_TOOLS` | `false` | Jira/Xray yazma tool'larını etkinleştirir |
| `LOG_LEVEL` | `info` | Log seviyesi (`debug`, `info`, `warning`, `error`) |
| `AUDIT_LOG_ENABLED` | `true` | Audit log'u etkinleştirir |
| `HTTP_ENABLED` | `false` | HTTP transport'u etkinleştirir |
| `HTTP_BIND_HOST` | `127.0.0.1` | HTTP bind adresi |
| `HTTP_PORT` | `8080` | HTTP port |

### Güvenlik Kontrol Listesi

- ✅ Tool allowlist yaklaşımı
- ✅ Parametre doğrulama
- ✅ Rate limiting
- ✅ Audit logging
- ✅ SBOM + provenance (Docker image)

---

## 📊 Başarı Ölçütleri

| Metrik | Hedef |
|--------|-------|
| Lint skoru ortalaması | ↑ Artmalı |
| Eksik alan yüzdesi | ↓ Düşmeli |
| Xray import sonrası düzeltme | ↓ Düşmeli |
| Test case üretim süresi | ↓ Düşmeli |

---

## 🗺️ Yol Haritası

- [x] **v1.0** - MVP: generate, lint, to_xray, compose
- [ ] **v1.1** - Policy/guardrails, audit logs
- [ ] **v1.2** - Jira/Xray sync (read-only)
- [ ] **v2.0** - HTTP transport, OAuth

---

## 📄 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

Copyright (c) 2024-2026 [Atakan Emre](https://github.com/Atakan-Emre)

---

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

---

## 👤 Geliştirici

**Atakan Emre**

- GitHub: [@Atakan-Emre](https://github.com/Atakan-Emre)
- Repository: [McpTestGenerator](https://github.com/Atakan-Emre/McpTestGenerator)

---

<div align="center">

**QA-MCP** ile test kalitesini standardize edin! 🚀

[![GitHub Stars](https://img.shields.io/github/stars/Atakan-Emre/McpTestGenerator?style=social)](https://github.com/Atakan-Emre/McpTestGenerator/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Atakan-Emre/McpTestGenerator?style=social)](https://github.com/Atakan-Emre/McpTestGenerator/network/members)

</div>
