"""
Lint Engine for Test Case Quality Analysis.

Analyzes test cases against standards and provides quality scores and suggestions.
"""

from qa_mcp.core.models import (
    LintIssue,
    LintResult,
    LintSeverity,
    ScenarioType,
    TestCase,
)
from qa_mcp.core.standards import TestCaseStandard


class LintEngine:
    """
    Test case linting engine.

    Analyzes test cases against standards and provides:
    - Quality score (0-100)
    - Issues (errors, warnings, info)
    - Suggestions for improvement
    """

    def __init__(self, standard: TestCaseStandard | None = None):
        """Initialize with a standard (uses default if not provided)."""
        self.standard = standard or TestCaseStandard.get_default()

    def lint(self, testcase: TestCase) -> LintResult:
        """
        Lint a test case and return results.

        Args:
            testcase: The test case to analyze

        Returns:
            LintResult with score, issues, and suggestions
        """
        issues: list[LintIssue] = []
        suggestions: list[str] = []
        score = 100  # Start with perfect score, deduct for issues

        # Run all lint checks
        score, issues, suggestions = self._check_title(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_description(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_preconditions(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_steps(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_expected_result(
            testcase, score, issues, suggestions
        )
        score, issues, suggestions = self._check_test_data(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_classification(
            testcase, score, issues, suggestions
        )
        score, issues, suggestions = self._check_traceability(testcase, score, issues, suggestions)

        # Ensure score is within bounds
        score = max(0, min(100, score))

        return LintResult(
            score=score,
            grade=LintResult.calculate_grade(score),
            issues=issues,
            suggestions=suggestions,
            passed=score >= self.standard.minimum_score,
        )

    def _check_title(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check title quality."""
        title = tc.title

        # Length check
        if len(title) < 10:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="title",
                    rule="title.min_length",
                    message="Başlık çok kısa (minimum 10 karakter)",
                    suggestion="Neyin test edildiğini açıkça belirten daha açıklayıcı bir başlık yazın",
                )
            )
            score -= 10

        # Generic words check
        generic_words = ["test", "check", "verify", "kontrol", "doğrula"]
        title_lower = title.lower()
        if any(
            word == title_lower.split()[0] if title_lower.split() else False
            for word in generic_words
        ):
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="title",
                    rule="title.no_generic_start",
                    message="Başlık genel bir kelimeyle başlıyor",
                    suggestion="'Test' yerine test edilen özelliği vurgulayın, örn: 'Kullanıcı Girişi - Geçerli Credentials'",
                )
            )
            score -= 5

        # Check for action verb
        action_verbs = [
            "verify",
            "validate",
            "ensure",
            "confirm",
            "test",
            "check",
            "doğrula",
            "kontrol",
        ]
        has_action = any(verb in title_lower for verb in action_verbs)
        if not has_action:
            suggestions.append("Başlığa bir eylem fiili ekleyin (örn: 'validates', 'ensures')")

        return score, issues, suggestions

    def _check_description(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check description quality."""
        desc = tc.description

        if len(desc) < 20:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="description",
                    rule="description.min_length",
                    message="Açıklama çok kısa (minimum 20 karakter)",
                    suggestion="Test'in amacını, kapsamını ve bağlamını açıklayan detaylı bir açıklama ekleyin",
                )
            )
            score -= 10

        # Check if description duplicates title
        if desc.lower().strip() == tc.title.lower().strip():
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="description",
                    rule="description.not_duplicate_title",
                    message="Açıklama başlığın aynısı",
                    suggestion="Test senaryosunun bağlamını, kapsamını ve önemini açıklayan ek bilgiler ekleyin",
                )
            )
            score -= 5

        return score, issues, suggestions

    def _check_preconditions(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check preconditions."""
        if not tc.preconditions:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="preconditions",
                    rule="preconditions.required",
                    message="Ön koşullar tanımlanmamış",
                    suggestion="Test'in çalışması için gerekli başlangıç durumlarını listeleyin (örn: 'Kullanıcı giriş yapmış', 'API erişilebilir')",
                )
            )
            score -= 15
        else:
            # Check for vague preconditions
            vague_terms = ["configured", "set up", "ready", "available", "hazır", "kurulu"]
            for precond in tc.preconditions:
                if any(term in precond.lower() for term in vague_terms) and len(precond) < 30:
                    issues.append(
                        LintIssue(
                            severity=LintSeverity.INFO,
                            field="preconditions",
                            rule="preconditions.specific",
                            message=f"Ön koşul belirsiz olabilir: '{precond}'",
                            suggestion="Daha spesifik detaylar ekleyin (örn: 'Redis cache çalışıyor' yerine 'Redis localhost:6379 çalışıyor')",
                        )
                    )

        return score, issues, suggestions

    def _check_steps(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check test steps quality."""
        if not tc.steps:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="steps",
                    rule="steps.required",
                    message="Test adımları tanımlanmamış",
                    suggestion="Net action ve expected result içeren adımlar ekleyin",
                )
            )
            score -= 20
            return score, issues, suggestions

        # Check number of steps
        if len(tc.steps) > 15:
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="steps",
                    rule="steps.max_count",
                    message=f"Çok fazla adım ({len(tc.steps)}). Maksimum önerilen: 15",
                    suggestion="Test case'i daha küçük, odaklı test'lere ayırmayı düşünün",
                )
            )
            score -= 5

        # Check each step
        for step in tc.steps:
            # Action quality
            if len(step.action) < 10:
                issues.append(
                    LintIssue(
                        severity=LintSeverity.WARNING,
                        field=f"steps[{step.step_number}].action",
                        rule="step.action.min_length",
                        message=f"Adım {step.step_number} action'ı çok kısa",
                        suggestion="Action'da ne yapılacağını net olarak açıklayın",
                    )
                )
                score -= 3

            # Expected result quality
            if len(step.expected_result) < 10:
                issues.append(
                    LintIssue(
                        severity=LintSeverity.WARNING,
                        field=f"steps[{step.step_number}].expected_result",
                        rule="step.expected.min_length",
                        message=f"Adım {step.step_number} expected result'ı çok kısa",
                        suggestion="Doğrulanabilir, spesifik beklenen sonuç yazın",
                    )
                )
                score -= 3

            # Check for vague expected results
            vague_expected = ["works", "correct", "proper", "çalışır", "doğru", "uygun"]
            if any(term in step.expected_result.lower() for term in vague_expected):
                issues.append(
                    LintIssue(
                        severity=LintSeverity.INFO,
                        field=f"steps[{step.step_number}].expected_result",
                        rule="step.expected.specific",
                        message=f"Adım {step.step_number} expected result belirsiz olabilir",
                        suggestion="'Çalışır' yerine spesifik olun: 'HTTP 200 döner ve response body {expected} içerir'",
                    )
                )

        return score, issues, suggestions

    def _check_expected_result(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check overall expected result."""
        exp = tc.expected_result

        if len(exp) < 10:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="expected_result",
                    rule="expected_result.min_length",
                    message="Genel beklenen sonuç çok kısa",
                    suggestion="Test'in başarılı kabul edilmesi için gereken koşulları detaylı açıklayın",
                )
            )
            score -= 10

        # Check for measurable criteria
        measurable_indicators = [
            "should",
            "must",
            "will",
            "displays",
            "returns",
            "contains",
            "olmalı",
            "döner",
            "gösterir",
            "içerir",
            "eşittir",
        ]
        if not any(ind in exp.lower() for ind in measurable_indicators):
            suggestions.append(
                "Beklenen sonuca ölçülebilir kriterler ekleyin (örn: 'Sayfa 3 saniyede yüklenmelidir')"
            )

        return score, issues, suggestions

    def _check_test_data(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check test data completeness."""
        # Check if test data is needed but missing
        data_indicators = ["input", "enter", "type", "value", "gir", "yaz", "değer"]
        needs_data = any(
            any(ind in step.action.lower() for ind in data_indicators) for step in tc.steps
        )

        if needs_data and not tc.test_data:
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="test_data",
                    rule="test_data.recommended",
                    message="Adımlarda veri girişi var ancak test_data tanımlı değil",
                    suggestion="Test data'yı açıkça tanımlayın (boundary değerler, negatif cases dahil)",
                )
            )
            score -= 5

        # Check for boundary values if numeric data is present
        if tc.test_data:
            has_boundary = any(d.is_boundary for d in tc.test_data)
            has_numeric = any(isinstance(d.value, int | float) for d in tc.test_data)

            if has_numeric and not has_boundary:
                suggestions.append(
                    "Numeric data için boundary değerler (min, max, sınır) eklemeyi düşünün"
                )

        # Scenario type specific checks
        if tc.scenario_type == ScenarioType.POSITIVE and tc.test_data:
            has_negative_data = any(d.is_negative for d in tc.test_data)
            if has_negative_data:
                issues.append(
                    LintIssue(
                        severity=LintSeverity.INFO,
                        field="test_data",
                        rule="test_data.scenario_mismatch",
                        message="Pozitif senaryo olarak işaretlenmiş ama negatif test data içeriyor",
                        suggestion="Scenario type'ı kontrol edin veya ayrı negatif test case oluşturun",
                    )
                )

        return score, issues, suggestions

    def _check_classification(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check classification fields."""
        # Module check
        if not tc.module:
            suggestions.append("Test edilen modülü/bileşeni belirtin")

        # Tags check
        if not tc.tags:
            issues.append(
                LintIssue(
                    severity=LintSeverity.INFO,
                    field="tags",
                    rule="tags.recommended",
                    message="Tag'ler tanımlı değil",
                    suggestion="Kategorize etmek için tag'ler ekleyin (örn: 'api', 'auth', 'payment')",
                )
            )
            score -= 3

        # Labels check (smoke, regression, etc.)
        if not tc.labels:
            suggestions.append("Suite label'ları ekleyin (smoke, regression, e2e, vb.)")

        # Duration estimate
        if tc.estimated_duration_minutes is None:
            suggestions.append("Tahmini çalışma süresi ekleyin (planlama için kullanışlı)")

        return score, issues, suggestions

    def _check_traceability(
        self,
        tc: TestCase,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Check traceability links."""
        if not tc.requirements:
            issues.append(
                LintIssue(
                    severity=LintSeverity.INFO,
                    field="requirements",
                    rule="requirements.recommended",
                    message="Gereksinim bağlantısı yok",
                    suggestion="İzlenebilirlik için requirement ID'leri ekleyin",
                )
            )
            score -= 3

        return score, issues, suggestions

    def get_improvement_plan(self, result: LintResult) -> list[dict]:
        """
        Generate a prioritized improvement plan based on lint results.

        Args:
            result: The lint result to analyze

        Returns:
            List of improvement actions sorted by priority
        """
        plan = []

        # Group issues by severity
        errors = [i for i in result.issues if i.severity == LintSeverity.ERROR]
        warnings = [i for i in result.issues if i.severity == LintSeverity.WARNING]
        infos = [i for i in result.issues if i.severity == LintSeverity.INFO]

        # Add errors first (must fix)
        for issue in errors:
            plan.append(
                {
                    "priority": 1,
                    "type": "error",
                    "field": issue.field,
                    "action": issue.suggestion or issue.message,
                    "impact": "high",
                }
            )

        # Add warnings (should fix)
        for issue in warnings:
            plan.append(
                {
                    "priority": 2,
                    "type": "warning",
                    "field": issue.field,
                    "action": issue.suggestion or issue.message,
                    "impact": "medium",
                }
            )

        # Add suggestions
        for suggestion in result.suggestions:
            plan.append(
                {
                    "priority": 3,
                    "type": "suggestion",
                    "field": "general",
                    "action": suggestion,
                    "impact": "low",
                }
            )

        # Add infos last (nice to have)
        for issue in infos:
            plan.append(
                {
                    "priority": 4,
                    "type": "info",
                    "field": issue.field,
                    "action": issue.suggestion or issue.message,
                    "impact": "low",
                }
            )

        return sorted(plan, key=lambda x: x["priority"])
