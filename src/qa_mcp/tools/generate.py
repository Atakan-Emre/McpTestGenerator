"""
Test Case Generation Tool.

Generates standardized test cases from feature descriptions and acceptance criteria.
"""

import uuid
from datetime import datetime

from qa_mcp.core.models import (
    Priority,
    RiskLevel,
    ScenarioType,
    TestCase,
    TestData,
    TestStep,
)
from qa_mcp.core.standards import NEGATIVE_SCENARIO_PATTERNS


def generate_testcase(
    feature: str,
    acceptance_criteria: list[str],
    module: str | None = None,
    risk_level: str = "medium",
    include_negative: bool = True,
    include_boundary: bool = True,
    test_type: str = "Manual",
    author: str | None = None,
) -> dict:
    """
    Generate standardized test cases from feature description.

    Args:
        feature: Feature description
        acceptance_criteria: List of acceptance criteria
        module: Module/component name
        risk_level: Risk level (low, medium, high, critical)
        include_negative: Whether to include negative scenarios
        include_boundary: Whether to include boundary test suggestions
        test_type: Type of test (Manual, Automated, Generic)
        author: Test case author

    Returns:
        Dictionary containing:
        - testcases: List of generated test cases
        - suggestions: Additional suggestions
        - coverage_summary: What scenarios are covered
    """
    testcases = []
    suggestions = []
    coverage = {
        "positive_scenarios": 0,
        "negative_scenarios": 0,
        "boundary_tests": 0,
        "acceptance_criteria_covered": [],
    }

    # Map risk level
    risk = RiskLevel(risk_level.lower())

    # Determine priority based on risk
    priority_map = {
        RiskLevel.CRITICAL: Priority.P0,
        RiskLevel.HIGH: Priority.P1,
        RiskLevel.MEDIUM: Priority.P2,
        RiskLevel.LOW: Priority.P3,
    }
    priority = priority_map.get(risk, Priority.P2)

    # Generate positive test cases for each acceptance criterion
    for idx, criterion in enumerate(acceptance_criteria, 1):
        tc = _generate_positive_testcase(
            feature=feature,
            criterion=criterion,
            criterion_number=idx,
            module=module,
            risk=risk,
            priority=priority,
            test_type=test_type,
            author=author,
        )
        testcases.append(tc)
        coverage["positive_scenarios"] += 1
        coverage["acceptance_criteria_covered"].append(f"AC-{idx}")

    # Generate negative test cases if requested
    if include_negative:
        negative_cases = _generate_negative_testcases(
            feature=feature,
            acceptance_criteria=acceptance_criteria,
            module=module,
            risk=risk,
            author=author,
        )
        testcases.extend(negative_cases)
        coverage["negative_scenarios"] = len(negative_cases)

    # Generate boundary test suggestions
    if include_boundary:
        boundary_suggestions = _generate_boundary_suggestions(
            feature=feature,
            acceptance_criteria=acceptance_criteria,
        )
        if boundary_suggestions:
            suggestions.extend(boundary_suggestions)
            coverage["boundary_tests"] = len(boundary_suggestions)

    # Additional suggestions based on feature analysis
    suggestions.extend(_analyze_feature_suggestions(feature, acceptance_criteria))

    return {
        "testcases": [tc.model_dump() for tc in testcases],
        "suggestions": suggestions,
        "coverage_summary": coverage,
        "total_generated": len(testcases),
    }


def _generate_positive_testcase(
    feature: str,
    criterion: str,
    criterion_number: int,
    module: str | None,
    risk: RiskLevel,
    priority: Priority,
    test_type: str,
    author: str | None,
) -> TestCase:
    """Generate a positive test case for an acceptance criterion."""

    # Generate descriptive title
    title = f"{feature} - {_extract_key_action(criterion)}"
    if len(title) > 200:
        title = title[:197] + "..."

    # Generate steps from criterion
    steps = _criterion_to_steps(criterion, criterion_number)

    # Generate preconditions
    preconditions = _generate_preconditions(feature, criterion)

    # Generate test data suggestions
    test_data = _extract_test_data(criterion)

    return TestCase(
        id=f"TC-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        description=f"Bu test, '{feature}' özelliğinin şu kabul kriterine göre çalıştığını doğrular: {criterion}",
        module=module,
        feature=feature,
        scenario_type=ScenarioType.POSITIVE,
        risk_level=risk,
        priority=priority,
        test_type=test_type,
        preconditions=preconditions,
        steps=steps,
        test_data=test_data,
        expected_result=f"Sistem başarıyla çalışır ve kabul kriteri karşılanır: {criterion}",
        tags=[module] if module else [],
        labels=["positive", _get_suite_label(risk)],
        requirements=[f"AC-{criterion_number}"],
        created_at=datetime.now(),
        author=author,
    )


def _generate_negative_testcases(
    feature: str,
    acceptance_criteria: list[str],
    module: str | None,
    risk: RiskLevel,
    author: str | None,
) -> list[TestCase]:
    """Generate negative test cases based on feature context."""
    negative_cases = []

    # Analyze feature for applicable negative patterns
    feature_lower = feature.lower()

    # Input validation scenarios
    if any(kw in feature_lower for kw in ["input", "form", "field", "giriş", "alan"]):
        patterns = next(
            (
                p["patterns"]
                for p in NEGATIVE_SCENARIO_PATTERNS
                if p["category"] == "input_validation"
            ),
            [],
        )
        for pattern in patterns[:3]:  # Limit to top 3
            tc = TestCase(
                id=f"TC-{uuid.uuid4().hex[:8].upper()}",
                title=f"{feature} - Negatif: {pattern}",
                description=f"Bu test, '{feature}' özelliğinin '{pattern}' durumunda nasıl davrandığını doğrular.",
                module=module,
                feature=feature,
                scenario_type=ScenarioType.NEGATIVE,
                risk_level=risk,
                priority=Priority.P2,
                preconditions=[f"{feature} sayfası/ekranı açık"],
                steps=[
                    TestStep(
                        step_number=1,
                        action=f"{pattern} durumunu oluşturun veya uygulayın",
                        expected_result="Sistem hata durumunu gracefully handle eder",
                    ),
                    TestStep(
                        step_number=2,
                        action="Sistem davranışını gözlemleyin",
                        expected_result="Uygun hata mesajı gösterilir ve sistem stabil kalır",
                    ),
                ],
                test_data=[TestData(name="invalid_input", value=pattern, is_negative=True)],
                expected_result=f"Sistem '{pattern}' durumunu düzgün handle eder ve kullanıcıya anlaşılır hata mesajı gösterir",
                tags=[module, "negative"] if module else ["negative"],
                labels=["negative", "regression"],
                created_at=datetime.now(),
                author=author,
            )
            negative_cases.append(tc)

    # Authentication scenarios
    if any(kw in feature_lower for kw in ["login", "auth", "password", "giriş", "şifre", "oturum"]):
        patterns = next(
            (
                p["patterns"]
                for p in NEGATIVE_SCENARIO_PATTERNS
                if p["category"] == "authentication"
            ),
            [],
        )
        for pattern in patterns[:2]:  # Limit to top 2
            tc = TestCase(
                id=f"TC-{uuid.uuid4().hex[:8].upper()}",
                title=f"{feature} - Güvenlik: {pattern}",
                description=f"Bu test, kimlik doğrulama sisteminin '{pattern}' durumunda güvenli davrandığını doğrular.",
                module=module,
                feature=feature,
                scenario_type=ScenarioType.NEGATIVE,
                risk_level=RiskLevel.HIGH,
                priority=Priority.P1,
                preconditions=["Kullanıcı kimlik doğrulama gerektiren bir işlem yapmaya çalışıyor"],
                steps=[
                    TestStep(
                        step_number=1,
                        action=f"'{pattern}' senaryosunu uygulayın",
                        expected_result="Sistem güvenli bir şekilde yanıt verir",
                    ),
                    TestStep(
                        step_number=2,
                        action="Erişim durumunu kontrol edin",
                        expected_result="Yetkisiz erişim engellenir",
                    ),
                ],
                test_data=[TestData(name="auth_scenario", value=pattern, is_negative=True)],
                expected_result=f"'{pattern}' durumunda sistem güvenli kalır ve yetkisiz erişime izin vermez",
                tags=[module, "security", "negative"] if module else ["security", "negative"],
                labels=["negative", "security", "regression"],
                created_at=datetime.now(),
                author=author,
            )
            negative_cases.append(tc)

    # Error handling scenarios
    error_patterns = next(
        (p["patterns"] for p in NEGATIVE_SCENARIO_PATTERNS if p["category"] == "error_handling"), []
    )
    for pattern in error_patterns[:2]:  # Add general error handling
        tc = TestCase(
            id=f"TC-{uuid.uuid4().hex[:8].upper()}",
            title=f"{feature} - Hata Durumu: {pattern}",
            description=f"Bu test, '{feature}' özelliğinin '{pattern}' hata durumunda nasıl davrandığını doğrular.",
            module=module,
            feature=feature,
            scenario_type=ScenarioType.ERROR_HANDLING,
            risk_level=risk,
            priority=Priority.P2,
            preconditions=[f"{feature} kullanılıyor"],
            steps=[
                TestStep(
                    step_number=1,
                    action=f"'{pattern}' durumunu simüle edin",
                    expected_result="Sistem hatayı algılar",
                ),
                TestStep(
                    step_number=2,
                    action="Sistem davranışını gözlemleyin",
                    expected_result="Uygun hata handling yapılır",
                ),
            ],
            test_data=[],
            expected_result=f"Sistem '{pattern}' durumunda gracefully degrade olur ve kullanıcıya anlaşılır bilgi verir",
            tags=[module, "error-handling"] if module else ["error-handling"],
            labels=["negative", "regression"],
            created_at=datetime.now(),
            author=author,
        )
        negative_cases.append(tc)

    return negative_cases


def _generate_boundary_suggestions(
    feature: str,
    acceptance_criteria: list[str],
) -> list[str]:
    """Generate boundary test suggestions."""
    suggestions = []

    combined_text = (feature + " " + " ".join(acceptance_criteria)).lower()

    # Numeric boundaries
    if any(
        kw in combined_text
        for kw in ["number", "count", "amount", "limit", "sayı", "miktar", "sınır"]
    ):
        suggestions.append(
            "Boundary test önerisi: Minimum, maksimum ve sınır değerleri için test case'ler ekleyin"
        )

    # Length boundaries
    if any(kw in combined_text for kw in ["length", "character", "uzunluk", "karakter", "text"]):
        suggestions.append(
            "Boundary test önerisi: Minimum/maksimum karakter uzunluğu için test case'ler ekleyin"
        )

    # Date boundaries
    if any(kw in combined_text for kw in ["date", "time", "period", "tarih", "süre", "zaman"]):
        suggestions.append(
            "Boundary test önerisi: Tarih sınırları (geçmiş, gelecek, bugün) için test case'ler ekleyin"
        )

    # File boundaries
    if any(kw in combined_text for kw in ["file", "upload", "size", "dosya", "yükle", "boyut"]):
        suggestions.append(
            "Boundary test önerisi: Dosya boyutu sınırları için test case'ler ekleyin (0 byte, max size, max+1)"
        )

    return suggestions


def _analyze_feature_suggestions(feature: str, acceptance_criteria: list[str]) -> list[str]:
    """Analyze feature and provide additional suggestions."""
    suggestions = []
    combined_text = (feature + " " + " ".join(acceptance_criteria)).lower()

    # Performance suggestion
    if any(kw in combined_text for kw in ["search", "list", "display", "ara", "listele", "göster"]):
        suggestions.append(
            "Performans testi önerisi: Büyük veri setleri ile yanıt süresi testi eklemeyi düşünün"
        )

    # Accessibility suggestion
    if any(kw in combined_text for kw in ["form", "input", "button", "click"]):
        suggestions.append(
            "Erişilebilirlik önerisi: Klavye navigasyonu ve screen reader uyumluluğu test case'leri eklemeyi düşünün"
        )

    # Concurrency suggestion
    if any(kw in combined_text for kw in ["save", "update", "create", "kaydet", "güncelle"]):
        suggestions.append(
            "Eşzamanlılık önerisi: Aynı anda birden fazla kullanıcı senaryosu eklemeyi düşünün"
        )

    return suggestions


def _extract_key_action(criterion: str) -> str:
    """Extract key action phrase from criterion."""
    # Simple extraction - take first meaningful part
    words = criterion.split()
    if len(words) > 6:
        return " ".join(words[:6])
    return criterion


def _criterion_to_steps(criterion: str, criterion_number: int) -> list[TestStep]:
    """Convert acceptance criterion to test steps."""
    steps = []

    # Basic step structure
    steps.append(
        TestStep(
            step_number=1,
            action="Ön koşulların karşılandığından emin olun",
            expected_result="Sistem test için hazır durumda",
        )
    )

    steps.append(
        TestStep(
            step_number=2,
            action=f"Kabul kriteri için ana aksiyonu gerçekleştirin: {criterion}",
            expected_result="Aksiyon başarıyla tamamlanır",
        )
    )

    steps.append(
        TestStep(
            step_number=3,
            action="Sonucu doğrulayın",
            expected_result=f"Kabul kriteri karşılanır: {criterion}",
        )
    )

    return steps


def _generate_preconditions(feature: str, criterion: str) -> list[str]:
    """Generate preconditions based on feature and criterion."""
    preconditions = []
    combined = (feature + " " + criterion).lower()

    # Common preconditions
    if any(kw in combined for kw in ["login", "user", "account", "kullanıcı", "hesap", "giriş"]):
        preconditions.append("Kullanıcı sisteme giriş yapmış durumda")

    if any(kw in combined for kw in ["api", "endpoint", "request"]):
        preconditions.append("API endpoint'i erişilebilir durumda")
        preconditions.append("Geçerli authentication token mevcut")

    if any(kw in combined for kw in ["page", "screen", "sayfa", "ekran"]):
        preconditions.append(f"{feature} sayfası/ekranı açık")

    if any(kw in combined for kw in ["data", "record", "veri", "kayıt"]):
        preconditions.append("Test verisi hazırlanmış")

    # Default if no specific preconditions
    if not preconditions:
        preconditions.append(f"{feature} özelliği erişilebilir durumda")
        preconditions.append("Test ortamı hazır")

    return preconditions


def _extract_test_data(criterion: str) -> list[TestData]:
    """Extract potential test data from criterion."""
    test_data = []

    # Look for quoted values
    import re

    quoted = re.findall(r'"([^"]*)"', criterion)
    for idx, value in enumerate(quoted):
        test_data.append(
            TestData(
                name=f"input_{idx + 1}",
                value=value,
                description="Kabul kriterinden çıkarılan değer",
            )
        )

    # Look for numeric values
    numbers = re.findall(r"\b\d+\b", criterion)
    for idx, num in enumerate(numbers):
        test_data.append(
            TestData(
                name=f"numeric_{idx + 1}",
                value=int(num),
                description="Kabul kriterinden çıkarılan sayısal değer",
            )
        )

    return test_data


def _get_suite_label(risk: RiskLevel) -> str:
    """Get appropriate suite label based on risk level."""
    if risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
        return "smoke"
    elif risk == RiskLevel.MEDIUM:
        return "regression"
    else:
        return "extended"
