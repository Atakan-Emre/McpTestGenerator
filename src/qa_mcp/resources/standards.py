"""
MCP Resources - Standards, Rules, and Examples.

These resources are exposed to LLM clients as static reference data.
"""

import json
from pathlib import Path
from typing import Any

# Resource base path
RESOURCE_DIR = Path(__file__).parent.parent.parent.parent / "resources"


def get_testcase_standard() -> dict[str, Any]:
    """
    Get the test case standard definition.

    URI: qa://standards/testcase/v1
    """
    return {
        "version": "1.0",
        "name": "QA-MCP Test Case Standard",
        "description": "Kurumsal test case yazım standardı",
        "schema": {
            "required_fields": [
                {
                    "name": "title",
                    "type": "string",
                    "min_length": 10,
                    "max_length": 200,
                    "description": "Test case başlığı - neyin test edildiğini açıkça belirtmeli",
                    "example": "Kullanıcı Girişi - Geçerli email ve şifre ile başarılı login",
                },
                {
                    "name": "description",
                    "type": "string",
                    "min_length": 20,
                    "description": "Test'in amacını, kapsamını ve bağlamını açıklayan detaylı metin",
                    "example": "Bu test, kullanıcıların geçerli kimlik bilgileriyle sisteme giriş yapabildiğini doğrular.",
                },
                {
                    "name": "preconditions",
                    "type": "array[string]",
                    "min_items": 1,
                    "description": "Test çalıştırılmadan önce sağlanması gereken koşullar",
                    "example": ["Kullanıcı kayıtlı", "Hesap aktif", "Login sayfası erişilebilir"],
                },
                {
                    "name": "steps",
                    "type": "array[TestStep]",
                    "min_items": 1,
                    "max_items": 15,
                    "description": "Test adımları - her adımda action ve expected_result olmalı",
                },
                {
                    "name": "expected_result",
                    "type": "string",
                    "min_length": 10,
                    "description": "Test'in genel beklenen sonucu",
                },
            ],
            "recommended_fields": [
                {
                    "name": "risk_level",
                    "type": "enum",
                    "values": ["low", "medium", "high", "critical"],
                    "description": "Risk seviyesi - suite seçimi için kullanılır",
                },
                {
                    "name": "priority",
                    "type": "enum",
                    "values": ["P0", "P1", "P2", "P3"],
                    "description": "Öncelik - P0 en yüksek, P3 en düşük",
                },
                {
                    "name": "test_data",
                    "type": "array[TestData]",
                    "description": "Test için gerekli veriler",
                },
                {
                    "name": "tags",
                    "type": "array[string]",
                    "description": "Kategorize etmek için etiketler",
                },
                {
                    "name": "labels",
                    "type": "array[string]",
                    "description": "Suite label'ları: smoke, regression, e2e",
                },
                {
                    "name": "requirements",
                    "type": "array[string]",
                    "description": "Bağlı gereksinim ID'leri",
                },
            ],
            "step_schema": {
                "step_number": "int - Adım sırası (1'den başlar)",
                "action": "string - Yapılacak işlem (min 5 karakter)",
                "expected_result": "string - Beklenen sonuç (min 5 karakter)",
                "test_data": "array[TestData] - Bu adımda kullanılan veriler (opsiyonel)",
                "notes": "string - Ek notlar (opsiyonel)",
            },
            "test_data_schema": {
                "name": "string - Veri değişken adı",
                "value": "any - Veri değeri",
                "description": "string - Açıklama (opsiyonel)",
                "is_boundary": "boolean - Sınır değer mi?",
                "is_negative": "boolean - Negatif test verisi mi?",
            },
        },
        "best_practices": [
            "Başlık, test edilen özelliği ve senaryoyu açıkça belirtmeli",
            "Her adım için doğrulanabilir expected result yazılmalı",
            "Ön koşullar, test ortamının hazır olduğunu garanti etmeli",
            "Test data açıkça tanımlanmalı, hardcoded değerler kullanılmamalı",
            "Negatif senaryolar için ayrı test case'ler oluşturulmalı",
            "Boundary değerler mutlaka test edilmeli",
            "Traceability için requirement linklerı eklenmeli",
        ],
    }


def get_lint_rules() -> dict[str, Any]:
    """
    Get the lint rules definition.

    URI: qa://checklists/lint-rules/v1
    """
    return {
        "version": "1.0",
        "name": "QA-MCP Lint Kuralları",
        "minimum_passing_score": 60,
        "rules": [
            {
                "id": "title.min_length",
                "severity": "error",
                "description": "Başlık minimum 10 karakter olmalı",
                "penalty": 10,
            },
            {
                "id": "title.no_generic_start",
                "severity": "warning",
                "description": "Başlık genel kelimelerle başlamamalı (Test, Check, Verify)",
                "penalty": 5,
            },
            {
                "id": "description.min_length",
                "severity": "error",
                "description": "Açıklama minimum 20 karakter olmalı",
                "penalty": 10,
            },
            {
                "id": "description.not_duplicate_title",
                "severity": "warning",
                "description": "Açıklama başlıktan farklı olmalı",
                "penalty": 5,
            },
            {
                "id": "preconditions.required",
                "severity": "error",
                "description": "En az bir ön koşul tanımlanmalı",
                "penalty": 15,
            },
            {
                "id": "preconditions.specific",
                "severity": "info",
                "description": "Ön koşullar spesifik olmalı, belirsiz terimlerden kaçınılmalı",
                "penalty": 0,
            },
            {
                "id": "steps.required",
                "severity": "error",
                "description": "En az bir test adımı tanımlanmalı",
                "penalty": 20,
            },
            {
                "id": "steps.max_count",
                "severity": "warning",
                "description": "Test adımları 15'i geçmemeli",
                "penalty": 5,
            },
            {
                "id": "step.action.min_length",
                "severity": "warning",
                "description": "Adım action'ı minimum 10 karakter olmalı",
                "penalty": 3,
            },
            {
                "id": "step.expected.min_length",
                "severity": "warning",
                "description": "Adım expected result'ı minimum 10 karakter olmalı",
                "penalty": 3,
            },
            {
                "id": "step.expected.specific",
                "severity": "info",
                "description": "Expected result spesifik ve doğrulanabilir olmalı",
                "penalty": 0,
            },
            {
                "id": "expected_result.min_length",
                "severity": "error",
                "description": "Genel expected result minimum 10 karakter olmalı",
                "penalty": 10,
            },
            {
                "id": "test_data.recommended",
                "severity": "warning",
                "description": "Data girişi içeren adımlar için test_data tanımlanmalı",
                "penalty": 5,
            },
            {
                "id": "test_data.scenario_mismatch",
                "severity": "info",
                "description": "Test data ve scenario type uyumlu olmalı",
                "penalty": 0,
            },
            {
                "id": "tags.recommended",
                "severity": "info",
                "description": "Tag'ler kategorize etmek için önerilir",
                "penalty": 3,
            },
            {
                "id": "requirements.recommended",
                "severity": "info",
                "description": "Traceability için requirement linklerı önerilir",
                "penalty": 3,
            },
        ],
        "scoring": {
            "max_score": 100,
            "grades": {
                "A": {"min": 90, "description": "Mükemmel - Production-ready"},
                "B": {"min": 80, "description": "İyi - Minor iyileştirmeler gerekli"},
                "C": {"min": 70, "description": "Orta - İyileştirme gerekli"},
                "D": {"min": 60, "description": "Zayıf - Önemli düzeltmeler gerekli"},
                "F": {"min": 0, "description": "Başarısız - Major düzeltmeler gerekli"},
            },
        },
    }


def get_xray_mapping() -> dict[str, Any]:
    """
    Get the Xray field mapping definition.

    URI: qa://mappings/xray/v1
    """
    return {
        "version": "1.0",
        "name": "QA-MCP to Xray Field Mapping",
        "description": "QA-MCP test case alanlarının Xray import formatına dönüşüm kuralları",
        "standard_mappings": {
            "title": {
                "xray_field": "summary",
                "jira_field": "fields.summary",
                "notes": "Direkt mapping",
            },
            "description": {
                "xray_field": "description",
                "jira_field": "fields.description",
                "notes": "Zenginleştirilmiş - test bilgileri eklenir",
            },
            "priority": {
                "xray_field": "priority",
                "jira_field": "fields.priority.name",
                "value_mapping": {
                    "P0": "Highest",
                    "P1": "High",
                    "P2": "Medium",
                    "P3": "Low",
                },
            },
            "module": {
                "xray_field": "components",
                "jira_field": "fields.components[].name",
                "notes": "Array olarak eklenir",
            },
            "tags": {
                "xray_field": "labels",
                "jira_field": "fields.labels",
                "notes": "Labels ile birleştirilir",
            },
            "labels": {
                "xray_field": "labels",
                "jira_field": "fields.labels",
                "notes": "Tags ile birleştirilir",
            },
            "steps": {
                "xray_field": "steps",
                "format": {
                    "action": "step.action",
                    "result": "step.expected_result",
                    "data": "step.test_data (formatted)",
                },
            },
            "preconditions": {
                "xray_field": "preconditions",
                "format": "Bullet list olarak birleştirilir",
            },
        },
        "custom_field_recommendations": {
            "risk_level": {
                "suggested_type": "Select List",
                "options": ["low", "medium", "high", "critical"],
                "notes": "Xray'de custom field olarak oluşturulmalı",
            },
            "scenario_type": {
                "suggested_type": "Select List",
                "options": ["positive", "negative", "boundary", "edge_case", "error_handling"],
            },
            "feature": {
                "suggested_type": "Text Field (single line)",
            },
            "estimated_duration_minutes": {
                "suggested_type": "Number Field",
            },
            "requirements": {
                "suggested_type": "Issue Links",
                "link_type": "Tests",
            },
        },
        "test_types": {
            "Manual": "Manual test - Xray'de manuel test olarak oluşturulur",
            "Automated": "Generic test - Automation framework'e bağlanabilir",
            "Generic": "Generic test - Herhangi bir tipte olabilir",
        },
        "import_formats": {
            "json": {
                "description": "Xray JSON import formatı",
                "endpoint": "/rest/raven/1.0/import/test",
            },
            "csv": {
                "description": "CSV import (basit format)",
                "notes": "Steps için sınırlı destek",
            },
        },
    }


def get_good_examples() -> list[dict[str, Any]]:
    """
    Get good test case examples.

    URI: qa://examples/good/*
    """
    return [
        {
            "id": "GOOD-001",
            "name": "İyi Örnek - Login Senaryosu",
            "testcase": {
                "title": "Kullanıcı Girişi - Geçerli email ve şifre ile başarılı authentication",
                "description": "Bu test, kayıtlı bir kullanıcının geçerli email ve şifre bilgileriyle sisteme başarıyla giriş yapabildiğini doğrular. Test, authentication flow'unun tüm adımlarını kapsar.",
                "module": "auth",
                "feature": "user-login",
                "scenario_type": "positive",
                "risk_level": "critical",
                "priority": "P0",
                "preconditions": [
                    "Test kullanıcısı sisteme kayıtlı (email: test@example.com)",
                    "Kullanıcı hesabı aktif durumda",
                    "Login sayfası erişilebilir (HTTP 200)",
                ],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Login sayfasına git (URL: /login)",
                        "expected_result": "Login formu görüntülenir, email ve password alanları mevcut",
                    },
                    {
                        "step_number": 2,
                        "action": "Email alanına 'test@example.com' gir",
                        "expected_result": "Email alanı değeri kabul eder, validation hatası yok",
                    },
                    {
                        "step_number": 3,
                        "action": "Password alanına geçerli şifreyi gir",
                        "expected_result": "Şifre maskeli olarak görüntülenir",
                    },
                    {
                        "step_number": 4,
                        "action": "Login butonuna tıkla",
                        "expected_result": "Loading indicator görüntülenir, buton disable olur",
                    },
                    {
                        "step_number": 5,
                        "action": "Authentication sonucunu bekle",
                        "expected_result": "Kullanıcı dashboard sayfasına yönlendirilir, welcome mesajı görüntülenir",
                    },
                ],
                "test_data": [
                    {
                        "name": "email",
                        "value": "test@example.com",
                        "description": "Geçerli test kullanıcısı emaili",
                    },
                    {"name": "password", "value": "ValidP@ss123", "description": "Geçerli şifre"},
                ],
                "expected_result": "Kullanıcı başarıyla sisteme giriş yapar, session oluşturulur ve dashboard sayfası görüntülenir",
                "tags": ["auth", "login", "critical-path"],
                "labels": ["smoke", "regression"],
                "estimated_duration_minutes": 3,
                "requirements": ["REQ-AUTH-001", "REQ-AUTH-002"],
            },
            "why_good": [
                "Başlık açık ve spesifik - ne test edildiği belli",
                "Açıklama detaylı ve bağlam sağlıyor",
                "Ön koşullar somut ve doğrulanabilir",
                "Her adımın expected result'ı spesifik",
                "Test data açıkça tanımlanmış",
                "Risk ve priority uygun şekilde belirlenmiş",
                "Traceability için requirement linkleri mevcut",
            ],
        },
        {
            "id": "GOOD-002",
            "name": "İyi Örnek - API Negatif Senaryo",
            "testcase": {
                "title": "API Authentication - Invalid Token ile 401 Unauthorized Response",
                "description": "Bu test, API endpoint'lerinin geçersiz authentication token ile çağrıldığında doğru şekilde 401 Unauthorized yanıtı döndürdüğünü doğrular.",
                "module": "api",
                "feature": "api-security",
                "scenario_type": "negative",
                "risk_level": "high",
                "priority": "P1",
                "preconditions": [
                    "API endpoint erişilebilir durumda",
                    "Geçersiz/expired token hazırlanmış",
                ],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "GET /api/v1/users endpoint'ine geçersiz token ile istek gönder",
                        "expected_result": "HTTP 401 Unauthorized status code döner",
                    },
                    {
                        "step_number": 2,
                        "action": "Response body'yi kontrol et",
                        "expected_result": "Error message 'Invalid or expired token' içerir",
                    },
                    {
                        "step_number": 3,
                        "action": "Response headers'ı kontrol et",
                        "expected_result": "WWW-Authenticate header mevcut",
                    },
                ],
                "test_data": [
                    {"name": "invalid_token", "value": "expired_token_123", "is_negative": True},
                    {"name": "endpoint", "value": "/api/v1/users"},
                ],
                "expected_result": "API, geçersiz token durumunda güvenli bir şekilde 401 yanıtı döner ve hassas bilgi sızdırmaz",
                "tags": ["api", "security", "authentication"],
                "labels": ["regression", "security"],
                "estimated_duration_minutes": 2,
                "requirements": ["REQ-SEC-001"],
            },
            "why_good": [
                "Negatif senaryo olarak açıkça işaretlenmiş",
                "Güvenlik açısından critical bir test",
                "Test data is_negative flag'i ile işaretli",
                "Expected result'lar doğrulanabilir (status code, header)",
            ],
        },
    ]


def get_bad_examples() -> list[dict[str, Any]]:
    """
    Get bad test case examples (anti-patterns).

    URI: qa://examples/bad/*
    """
    return [
        {
            "id": "BAD-001",
            "name": "Kötü Örnek - Belirsiz Test Case",
            "testcase": {
                "title": "Login test",
                "description": "Login test",
                "preconditions": [],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Login yap",
                        "expected_result": "Çalışır",
                    },
                ],
                "expected_result": "OK",
                "tags": [],
            },
            "problems": [
                "Başlık çok kısa ve belirsiz",
                "Açıklama başlıkla aynı",
                "Ön koşullar tanımlı değil",
                "Test adımı çok genel - 'Login yap' ne demek?",
                "Expected result 'Çalışır' doğrulanabilir değil",
                "Risk level ve priority belirtilmemiş",
                "Test data yok",
                "Traceability yok",
            ],
            "lint_score_estimate": 25,
        },
        {
            "id": "BAD-002",
            "name": "Kötü Örnek - Çok Uzun Test Case",
            "testcase": {
                "title": "Tüm e-ticaret akışını baştan sona test et - kullanıcı kaydı, ürün arama, sepete ekleme, checkout, ödeme ve sipariş takibi",
                "description": "Herşeyi test et",
                "preconditions": ["Sistem çalışıyor"],
                "steps": [
                    {"step_number": i, "action": f"Adım {i}", "expected_result": "OK"}
                    for i in range(1, 26)
                ],
                "expected_result": "Hepsi çalışır",
            },
            "problems": [
                "Başlık çok uzun (200+ karakter)",
                "Tek test case çok fazla şeyi kapsıyor - bölünmeli",
                "25 adım var - maximum 15 olmalı",
                "Tüm adımlar generic 'Adım X' - anlamlı değil",
                "Tüm expected result'lar 'OK' - doğrulanabilir değil",
                "Bu kadar büyük test fail ederse hangisi sorun belirsiz",
            ],
            "lint_score_estimate": 35,
            "suggestion": "Bu test en az 5 ayrı test case'e bölünmeli: Registration, Search, Cart, Checkout, Order Tracking",
        },
        {
            "id": "BAD-003",
            "name": "Kötü Örnek - Hardcoded Değerler",
            "testcase": {
                "title": "Kullanıcı john@company.com ile giriş yapabilmeli ve 12345 siparişi görebilmeli",
                "description": "John'un siparişini kontrol et",
                "preconditions": ["John'un hesabı var"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "john@company.com ve S3cr3tP@ss ile giriş yap",
                        "expected_result": "Giriş başarılı",
                    },
                    {
                        "step_number": 2,
                        "action": "12345 siparişine git",
                        "expected_result": "Sipariş görünür",
                    },
                ],
                "expected_result": "John siparişini görür",
                "test_data": [],
            },
            "problems": [
                "Gerçek email ve şifre test case'de hardcoded",
                "Production verisi test case'de geçiyor",
                "Test data ayrı tanımlanmamış",
                "Test tekrar kullanılamaz - sadece 'John' için geçerli",
                "Güvenlik riski - credentials exposed",
            ],
            "lint_score_estimate": 45,
            "suggestion": "Test data parametrik olmalı, credentials environment variable'dan gelmeli",
        },
    ]


def load_resource_file(resource_path: str) -> dict[str, Any] | None:
    """Load a resource from file if it exists."""
    file_path = RESOURCE_DIR / resource_path
    if file_path.exists():
        with open(file_path) as f:
            return json.load(f)
    return None
