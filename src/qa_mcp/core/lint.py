"""
Lint Engine for Test Case Quality Analysis.

Analyzes test cases against standards and provides quality scores and suggestions.
"""

import re
from collections.abc import Iterable
from functools import cache

from qa_mcp.core.models import (
    LintIssue,
    LintResult,
    LintSeverity,
    ScenarioType,
    TestCaseDraft,
)
from qa_mcp.core.standards import TestCaseStandard
from qa_mcp.resources.standards import get_lint_rules


@cache
def _rule_penalties() -> dict[str, int]:
    """Penalty per rule id, read from the published lint-rules resource.

    Refunding a disabled rule needs to know what it cost. Taking the figure
    from the same resource clients read keeps the documentation and the
    arithmetic from disagreeing.
    """
    return {rule["id"]: int(rule.get("penalty", 0)) for rule in get_lint_rules()["rules"]}


class LintEngine:
    """
    Test case linting engine.

    Analyzes test cases against standards and provides:
    - Quality score (0-100)
    - Issues (errors, warnings, info)
    - Suggestions for improvement
    """

    def __init__(
        self,
        standard: TestCaseStandard | None = None,
        disabled_rules: Iterable[str] | None = None,
    ):
        """Initialize with a standard and an optional set of rules to skip.

        Args:
            standard: Thresholds to lint against; the shipped default if omitted.
            disabled_rules: Rule ids an organisation has chosen not to enforce.
                A disabled rule raises no issue and costs no points.
        """
        self.standard = standard or TestCaseStandard.get_default()
        self.disabled_rules = frozenset(disabled_rules or ())

    def lint(self, testcase: TestCaseDraft) -> LintResult:
        """
        Lint a test case and return results.

        Args:
            testcase: The test case to analyze (draft or standard-conforming)

        Returns:
            LintResult with score, issues, and suggestions
        """
        issues: list[LintIssue] = []
        suggestions: list[str] = []
        score = 100  # Start with perfect score, deduct for issues

        # Checks append freely; disabled rules are withdrawn afterwards, along
        # with the points they cost, so a team that switches a rule off is not
        # still penalised by it.

        # Run all lint checks
        score, issues, suggestions = self._check_title(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_description(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_preconditions(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_steps(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_expected_result(
            testcase, score, issues, suggestions
        )
        score, issues, suggestions = self._check_test_data(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_data_hygiene(testcase, score, issues, suggestions)
        score, issues, suggestions = self._check_classification(
            testcase, score, issues, suggestions
        )
        score, issues, suggestions = self._check_traceability(testcase, score, issues, suggestions)

        if self.disabled_rules:
            penalties = _rule_penalties()
            score += sum(
                penalties.get(issue.rule, 0)
                for issue in issues
                if issue.rule in self.disabled_rules
            )
            issues = [i for i in issues if i.rule not in self.disabled_rules]

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
        tc: TestCaseDraft,
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

        if len(title) > 200:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="title",
                    rule="title.max_length",
                    message=f"Başlık çok uzun ({len(title)} karakter, maksimum 200)",
                    suggestion="Başlığı kısaltın; kapsam çok genişse test case'i birden fazla test'e bölün",
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
        tc: TestCaseDraft,
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
        tc: TestCaseDraft,
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
        tc: TestCaseDraft,
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
        max_steps = int(self.standard.quality_rules.get("steps", {}).get("max_steps", 15))
        if len(tc.steps) > max_steps:
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="steps",
                    rule="steps.max_count",
                    message=f"Çok fazla adım ({len(tc.steps)}). Maksimum önerilen: {max_steps}",
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
        tc: TestCaseDraft,
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
        tc: TestCaseDraft,
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
        tc: TestCaseDraft,
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
        tc: TestCaseDraft,
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

    # --- Data hygiene ------------------------------------------------------
    #
    # A test case that inlines a real account and its password is both a
    # security problem and a test that only ever works for that one account.
    # Preconditions are excluded on purpose: naming the test account there is
    # normal practice, the smell is a literal baked into the executable flow.

    _EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _LABELLED_SECRET_PATTERN = re.compile(
        r"(?:password|passwd|pwd|şifre|sifre|parola|token|secret|api[_ -]?key|apikey|credential)"
        r"\s*[:=]\s*(\S+)",
        re.IGNORECASE,
    )
    _LONG_NUMBER_PATTERN = re.compile(r"\b\d{4,}\b")

    @staticmethod
    def _looks_like_a_secret(token: str) -> bool:
        """Heuristic for a literal password: long and mixed across character classes."""
        if len(token) < 8:
            return False
        return (
            any(c.islower() for c in token)
            and any(c.isupper() for c in token)
            and any(c.isdigit() for c in token)
            and any(not c.isalnum() for c in token)
        )

    @staticmethod
    def _flow_text(tc: TestCaseDraft) -> str:
        """The executable part of the test case, where literals do not belong."""
        parts = [tc.title, tc.expected_result]
        for step in tc.steps:
            parts.append(step.action)
            parts.append(step.expected_result)
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _declared_values(tc: TestCaseDraft) -> set[str]:
        """Values the test case declares as test data, lowercased."""
        declared: set[str] = set()
        for data in tc.test_data:
            declared.add(str(data.value).lower())
            declared.add(data.name.lower())
        return declared

    def _check_data_hygiene(
        self,
        tc: TestCaseDraft,
        score: int,
        issues: list[LintIssue],
        suggestions: list[str],
    ) -> tuple[int, list[LintIssue], list[str]]:
        """Flag credentials and identifiers hardcoded into the test flow."""
        flow = self._flow_text(tc)
        if not flow:
            return score, issues, suggestions

        declared = self._declared_values(tc)

        # Emails first, so their '@' is not mistaken for a password symbol.
        emails = [e for e in self._EMAIL_PATTERN.findall(flow) if e.lower() not in declared]
        flow_without_emails = self._EMAIL_PATTERN.sub(" ", flow)

        secrets = {
            match
            for match in self._LABELLED_SECRET_PATTERN.findall(flow_without_emails)
            if match.lower() not in declared
        }
        secrets.update(
            token.strip("'\"`,.;:()[]{}")
            for token in flow_without_emails.split()
            if self._looks_like_a_secret(token.strip("'\"`,.;:()[]{}"))
            and token.strip("'\"`,.;:()[]{}").lower() not in declared
        )

        if secrets:
            issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    field="test_data",
                    rule="test_data.hardcoded_credentials",
                    message=f"Test adımlarında credential görünümlü sabit değer var: {', '.join(sorted(secrets))}",
                    suggestion="Credential'ları test case'den çıkarın; test_data'da adlandırın ve değeri environment variable'dan alın (örn: ${TEST_USER_PASSWORD})",
                )
            )
            score -= 20

        if emails:
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="test_data",
                    rule="test_data.hardcoded_identity",
                    message=f"Test akışında tanımlanmamış kimlik bilgisi sabitlenmiş: {', '.join(sorted(set(emails)))}",
                    suggestion="Bu değeri test_data'da tanımlayın ve adımda adıyla referans verin; test böylece tek bir hesaba bağlı kalmaz",
                )
            )
            score -= 6

        if not tc.test_data and (
            emails or secrets or self._LONG_NUMBER_PATTERN.search(flow) or "'" in flow
        ):
            issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    field="test_data",
                    rule="test_data.not_parameterized",
                    message="Adımlar sabit değerler içeriyor ancak test_data tanımlı değil - test tekrar kullanılabilir değil",
                    suggestion="Sabit değerleri test_data olarak çıkarın; aynı test farklı veri setleriyle çalıştırılabilsin",
                )
            )
            score -= 6

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
