"""
MCP Prompt Templates.

These prompts guide LLMs in producing consistent, high-quality outputs.
"""

from typing import Any


def get_create_manual_test_prompt(
    feature: str | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """
    Get the prompt template for creating manual test cases.

    MCP Prompt Name: create-manual-test
    """
    base_prompt = """Sen bir QA uzmanısın. Verilen feature ve acceptance criteria'ya göre 
kapsamlı test case'ler oluşturman gerekiyor.

## Test Case Oluşturma Kuralları

1. **Başlık**: Neyin test edildiğini açıkça belirt (10-200 karakter)
2. **Açıklama**: Test'in amacını ve kapsamını detaylı anlat
3. **Ön Koşullar**: Test başlamadan önce sağlanması gereken tüm koşulları listele
4. **Adımlar**: Her adım için:
   - Yapılacak işlem (action) - net ve tekrarlanabilir
   - Beklenen sonuç (expected_result) - doğrulanabilir ve spesifik
5. **Test Data**: Kullanılacak verileri açıkça tanımla
6. **Risk ve Öncelik**: Uygun risk_level ve priority değerlerini belirle

## Senaryo Tipleri

- **Pozitif**: Normal, başarılı akış senaryoları
- **Negatif**: Hata durumları, invalid input senaryoları
- **Boundary**: Sınır değer testleri (min, max, limit)
- **Edge Case**: Nadir ama olası durumlar

## Output Format

testcase.generate tool'unu kullanarak test case oluştur. Tool şu parametreleri alır:
- feature: Feature açıklaması
- acceptance_criteria: Kabul kriterleri listesi
- module: Modül adı (opsiyonel)
- risk_level: low/medium/high/critical
- include_negative: true/false
- include_boundary: true/false
"""

    if feature:
        base_prompt += f"\n\n## Mevcut Context\n\nFeature: {feature}"

    if acceptance_criteria:
        base_prompt += "\n\nAcceptance Criteria:\n"
        for idx, ac in enumerate(acceptance_criteria, 1):
            base_prompt += f"{idx}. {ac}\n"

    return {
        "name": "create-manual-test",
        "description": "Xray Manual Test oluşturma rehberi",
        "prompt": base_prompt,
        "arguments": [
            {
                "name": "feature",
                "description": "Test edilecek özellik",
                "required": True,
            },
            {
                "name": "acceptance_criteria",
                "description": "Kabul kriterleri listesi",
                "required": True,
            },
        ],
    }


def get_select_smoke_tests_prompt(
    testcases: list[dict] | None = None,
    max_duration: int = 15,
) -> dict[str, Any]:
    """
    Get the prompt template for selecting smoke tests.

    MCP Prompt Name: select-smoke-tests
    """
    base_prompt = f"""Sen bir QA Lead'sin. Mevcut test case havuzundan Smoke test suite'i 
oluşturman gerekiyor.

## Smoke Test Seçim Kriterleri

1. **Kritik Yol Testleri**: Ana kullanıcı journey'lerini kapsamalı
2. **High-Risk Alanlar**: Critical ve high risk test'ler öncelikli
3. **P0/P1 Öncelik**: En yüksek öncelikli test'ler
4. **Hızlı Çalışma**: Toplam süre maksimum {max_duration} dakika olmalı
5. **Temel Fonksiyonlar**: Login, ana işlemler, kritik entegrasyonlar

## Seçilmemesi Gerekenler

- Uzun süren E2E test'ler
- Edge case ve boundary test'ler (regression için)
- Low priority test'ler
- Detaylı negatif senaryolar

## Smoke Suite Özellikleri

- Maksimum 15-20 test case
- Her kritik modülden en az 1 test
- Toplam süre: {max_duration} dakika

## Output Format

suite.compose tool'unu kullanarak smoke suite oluştur:
- testcases: Tüm test case listesi
- target: "smoke"
- max_duration_minutes: {max_duration}
"""

    return {
        "name": "select-smoke-tests",
        "description": "Smoke test seçimi rehberi",
        "prompt": base_prompt,
        "arguments": [
            {
                "name": "testcases",
                "description": "Mevcut test case havuzu",
                "required": True,
            },
            {
                "name": "max_duration",
                "description": "Maksimum suite süresi (dakika)",
                "required": False,
            },
        ],
    }


def get_generate_negative_scenarios_prompt(
    feature: str | None = None,
    positive_testcases: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Get the prompt template for generating negative test scenarios.

    MCP Prompt Name: generate-negative-scenarios
    """
    base_prompt = """Sen bir QA Security uzmanısın. Pozitif test case'lere karşılık gelen 
negatif senaryoları belirlemelisin.

## Negatif Senaryo Kategorileri

### 1. Input Validation
- Boş input
- Null değer
- Özel karakterler (SQL injection, XSS)
- Maksimum uzunluk aşımı
- Minimum uzunluk ihlali
- Geçersiz format (email, telefon, vb.)

### 2. Authentication & Authorization
- Geçersiz credentials
- Expired session/token
- Yetersiz yetki
- Session hijacking denemeleri

### 3. Boundary Testing
- Minimum değerin 1 altı
- Maksimum değerin 1 üstü
- Zero değeri
- Negatif sayılar

### 4. Error Handling
- Network timeout
- Server error (5xx)
- Resource not found (404)
- Rate limit aşımı
- Database bağlantı hatası

### 5. Concurrency
- Eşzamanlı istekler
- Race condition
- Deadlock senaryoları

## Output Format

Her pozitif senaryo için en az 2 negatif senaryo öner.
testcase.generate tool'unu kullanarak negatif senaryoları da içeren bir aday set üret:
- include_negative: true
- include_boundary: false
Tool çıktısından negatif test case'leri seç ve gerekiyorsa daha spesifik failure mode'larla zenginleştir.
"""

    if feature:
        base_prompt += f"\n\n## Mevcut Context\n\nFeature: {feature}"

    return {
        "name": "generate-negative-scenarios",
        "description": "Negatif senaryo üretimi rehberi",
        "prompt": base_prompt,
        "arguments": [
            {
                "name": "feature",
                "description": "Test edilecek özellik",
                "required": True,
            },
            {
                "name": "positive_testcases",
                "description": "Mevcut pozitif test case'ler",
                "required": False,
            },
        ],
    }


def get_review_test_coverage_prompt(
    testcases: list[dict] | None = None,
    requirements: list[str] | None = None,
) -> dict[str, Any]:
    """
    Get the prompt template for reviewing test coverage.

    MCP Prompt Name: review-test-coverage
    """
    base_prompt = """Sen bir QA Manager'sın. Test suite'in kapsamını analiz etmen ve 
eksikleri belirlemelisin.

## Kapsam Analiz Kriterleri

### 1. Gereksinim Kapsamı (Requirement Coverage)
- Her gereksinim için en az 1 test case var mı?
- Kritik gereksinimler daha fazla test ile kapsanıyor mu?

### 2. Modül Kapsamı
- Tüm modüller test ediliyor mu?
- Entegrasyon noktaları test ediliyor mu?

### 3. Senaryo Dağılımı
- Pozitif/Negatif oran makul mü? (önerilen: %70/%30)
- Boundary test'ler var mı?
- Error handling test'leri var mı?

### 4. Risk Dağılımı
- Critical/High risk alanlar yeterince kapsanıyor mu?
- Düşük riskli alanlara gereksiz odaklanma var mı?

### 5. Test Data Kalitesi
- Test data tanımlı mı?
- Boundary değerler kullanılıyor mu?
- Data-driven test yaklaşımı var mı?

## Output Format

suite.coverage_report tool'unu kullanarak analiz yap:
- testcases: Test case listesi
- requirements: Gereksinim listesi (opsiyonel)
- modules: Modül listesi (opsiyonel)
"""

    return {
        "name": "review-test-coverage",
        "description": "Test kapsam analizi rehberi",
        "prompt": base_prompt,
        "arguments": [
            {
                "name": "testcases",
                "description": "Analiz edilecek test case'ler",
                "required": True,
            },
            {
                "name": "requirements",
                "description": "Kontrol edilecek gereksinimler",
                "required": False,
            },
        ],
    }


# Registry of all available prompts
PROMPT_REGISTRY = {
    "create-manual-test": get_create_manual_test_prompt,
    "select-smoke-tests": get_select_smoke_tests_prompt,
    "generate-negative-scenarios": get_generate_negative_scenarios_prompt,
    "review-test-coverage": get_review_test_coverage_prompt,
}
