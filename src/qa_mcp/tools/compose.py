"""
Suite Composition Tool.

Composes test suites (Smoke, Regression, E2E) from test case collections.
"""

from typing import Any

from qa_mcp.core.models import (
    Priority,
    RiskLevel,
    SuiteComposition,
    SuiteType,
    TestCase,
)
from qa_mcp.core.standards import SUITE_RULES


def compose_suite(
    testcases: list[dict],
    target: str,
    sprint: str | None = None,
    max_duration_minutes: int | None = None,
    custom_criteria: dict[str, Any] | None = None,
) -> dict:
    """
    Compose a test suite from a collection of test cases.

    Args:
        testcases: List of test cases in QA-MCP standard format
        target: Suite type - 'smoke', 'sanity', 'regression', 'e2e'
        sprint: Sprint name/number for context
        max_duration_minutes: Maximum suite duration (overrides default)
        custom_criteria: Custom selection criteria

    Returns:
        Dictionary containing:
        - suite: Composed suite with selected test cases
        - selection_rationale: Why each test was included/excluded
        - coverage_summary: What's covered and what's not
        - recommendations: Suggestions for improving coverage
    """
    # Parse test cases
    parsed_cases = []
    parse_errors = []

    for idx, tc_dict in enumerate(testcases):
        try:
            tc = TestCase(**tc_dict)
            parsed_cases.append(tc)
        except Exception as e:
            parse_errors.append(f"Test case {idx}: {str(e)}")

    if parse_errors:
        return {
            "suite": None,
            "selection_rationale": [],
            "coverage_summary": {},
            "recommendations": [],
            "errors": parse_errors,
        }

    # Get suite rules
    suite_type = SuiteType(target.lower())
    rules = SUITE_RULES.get(target.lower(), SUITE_RULES["regression"])

    # Override max duration if provided
    if max_duration_minutes:
        rules = {**rules, "max_duration_minutes": max_duration_minutes}

    # Select test cases
    selected, excluded, rationale = _select_testcases(parsed_cases, suite_type, rules)

    # Build coverage summary
    coverage_summary = _build_coverage_summary(parsed_cases, selected, suite_type)

    # Generate recommendations
    recommendations = _generate_recommendations(parsed_cases, selected, excluded, suite_type)

    # Calculate total duration
    total_duration = sum(
        tc.estimated_duration_minutes or 5  # Default 5 min per test
        for tc in selected
    )

    # Build suite composition
    suite = SuiteComposition(
        suite_type=suite_type,
        name=f"{target.upper()} Suite" + (f" - {sprint}" if sprint else ""),
        description=rules.get("description", f"{target} test suite"),
        testcases=[tc.id or f"TC-{idx}" for idx, tc in enumerate(selected)],
        total_duration_minutes=total_duration,
        coverage_summary=coverage_summary,
        rationale=f"{len(selected)} test case seçildi, toplam {total_duration} dakika",
    )

    return {
        "suite": suite.model_dump(),
        "selected_testcases": [tc.model_dump() for tc in selected],
        "excluded_count": len(excluded),
        "selection_rationale": rationale,
        "coverage_summary": coverage_summary,
        "recommendations": recommendations,
        "duration_warning": total_duration > rules.get("max_duration_minutes", 999),
    }


def _select_testcases(
    testcases: list[TestCase],
    suite_type: SuiteType,
    rules: dict,
) -> tuple[list[TestCase], list[TestCase], list[dict]]:
    """Select test cases based on suite rules."""
    selected = []
    excluded = []
    rationale = []

    # Get filter criteria
    priority_filter = rules.get("priority_filter", ["P0", "P1", "P2", "P3"])
    risk_filter = rules.get("risk_filter", ["critical", "high", "medium", "low"])
    max_tests = rules.get("max_tests", 999)
    max_duration = rules.get("max_duration_minutes", 999)

    current_duration = 0

    # Sort by priority and risk (most critical first)
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    sorted_cases = sorted(
        testcases,
        key=lambda tc: (
            priority_order.get(tc.priority.value if tc.priority else "P3", 3),
            risk_order.get(tc.risk_level.value if tc.risk_level else "low", 3),
        ),
    )

    for tc in sorted_cases:
        include = True
        reason = []

        # Check priority
        if tc.priority and tc.priority.value not in priority_filter:
            include = False
            reason.append(f"Öncelik ({tc.priority.value}) suite için uygun değil")

        # Check risk level
        if tc.risk_level and tc.risk_level.value not in risk_filter:
            include = False
            reason.append(f"Risk seviyesi ({tc.risk_level.value}) suite için uygun değil")

        # Check duration
        tc_duration = tc.estimated_duration_minutes or 5
        if current_duration + tc_duration > max_duration:
            include = False
            reason.append(
                f"Süre limiti aşılıyor ({current_duration + tc_duration} > {max_duration})"
            )

        # Check max tests
        if len(selected) >= max_tests:
            include = False
            reason.append(f"Maksimum test sayısına ulaşıldı ({max_tests})")

        # Labels should reinforce valid candidates, not bypass hard constraints.
        if suite_type == SuiteType.SMOKE and "smoke" in tc.labels:
            if include:
                reason.append("'smoke' label'ı mevcut")
        elif suite_type == SuiteType.REGRESSION and "regression" in tc.labels and include:
            reason.append("'regression' label'ı mevcut")

        # Record decision
        if include:
            selected.append(tc)
            current_duration += tc_duration
            rationale.append(
                {
                    "testcase_id": tc.id,
                    "testcase_title": tc.title,
                    "included": True,
                    "reasons": reason or ["Kriterleri karşılıyor"],
                }
            )
        else:
            excluded.append(tc)
            rationale.append(
                {
                    "testcase_id": tc.id,
                    "testcase_title": tc.title,
                    "included": False,
                    "reasons": reason,
                }
            )

    return selected, excluded, rationale


def _build_coverage_summary(
    all_cases: list[TestCase],
    selected: list[TestCase],
    suite_type: SuiteType,
) -> dict:
    """Build coverage summary."""
    # Module coverage
    all_modules = set(tc.module for tc in all_cases if tc.module)
    covered_modules = set(tc.module for tc in selected if tc.module)

    # Feature coverage
    all_features = set(tc.feature for tc in all_cases if tc.feature)
    covered_features = set(tc.feature for tc in selected if tc.feature)

    # Scenario type coverage
    scenario_types = {}
    for tc in selected:
        st = tc.scenario_type.value if tc.scenario_type else "unknown"
        scenario_types[st] = scenario_types.get(st, 0) + 1

    # Risk coverage
    risk_coverage = {}
    for tc in selected:
        rl = tc.risk_level.value if tc.risk_level else "unknown"
        risk_coverage[rl] = risk_coverage.get(rl, 0) + 1

    # Priority coverage
    priority_coverage = {}
    for tc in selected:
        p = tc.priority.value if tc.priority else "unknown"
        priority_coverage[p] = priority_coverage.get(p, 0) + 1

    return {
        "modules": {
            "total": len(all_modules),
            "covered": len(covered_modules),
            "coverage_percent": round(len(covered_modules) / len(all_modules) * 100, 1)
            if all_modules
            else 0,
            "uncovered": list(all_modules - covered_modules),
        },
        "features": {
            "total": len(all_features),
            "covered": len(covered_features),
            "coverage_percent": round(len(covered_features) / len(all_features) * 100, 1)
            if all_features
            else 0,
            "uncovered": list(all_features - covered_features),
        },
        "scenario_types": scenario_types,
        "risk_coverage": risk_coverage,
        "priority_coverage": priority_coverage,
        "testcase_coverage": {
            "total_available": len(all_cases),
            "selected": len(selected),
            "selection_percent": round(len(selected) / len(all_cases) * 100, 1) if all_cases else 0,
        },
    }


def _generate_recommendations(
    all_cases: list[TestCase],
    selected: list[TestCase],
    excluded: list[TestCase],
    suite_type: SuiteType,
) -> list[str]:
    """Generate recommendations for suite improvement."""
    recommendations = []

    # Check for missing critical tests
    critical_excluded = [
        tc for tc in excluded if tc.risk_level == RiskLevel.CRITICAL or tc.priority == Priority.P0
    ]
    if critical_excluded:
        recommendations.append(
            f"⚠️ {len(critical_excluded)} kritik/P0 test case suite dışında kaldı. "
            "Süre veya sayı limitini artırmayı düşünün."
        )

    # Check scenario type balance
    selected_positive = sum(
        1 for tc in selected if tc.scenario_type and tc.scenario_type.value == "positive"
    )
    selected_negative = sum(
        1 for tc in selected if tc.scenario_type and tc.scenario_type.value == "negative"
    )

    if suite_type == SuiteType.REGRESSION and selected_negative < selected_positive * 0.2:
        recommendations.append(
            "ℹ️ Negatif senaryolar yetersiz. Regression suite'de en az %20 negatif test olması önerilir."
        )

    # Check module coverage
    all_modules = set(tc.module for tc in all_cases if tc.module)
    covered_modules = set(tc.module for tc in selected if tc.module)
    uncovered = all_modules - covered_modules

    if uncovered and suite_type == SuiteType.REGRESSION:
        recommendations.append(
            f"ℹ️ {len(uncovered)} modül kapsam dışında: {', '.join(list(uncovered)[:3])}..."
        )

    # Check duration distribution
    if selected:
        avg_duration = sum(tc.estimated_duration_minutes or 5 for tc in selected) / len(selected)
        if avg_duration > 10:
            recommendations.append(
                f"⚠️ Ortalama test süresi yüksek ({avg_duration:.1f} dk). "
                "Uzun test'leri bölmeyi düşünün."
            )

    # Smoke-specific recommendations
    if suite_type == SuiteType.SMOKE:
        if len(selected) > 20:
            recommendations.append(
                "⚠️ Smoke suite çok büyük. 15-20 test idealdir, kritik yolları önceliklendirin."
            )
        if not any(tc.module and "auth" in tc.module.lower() for tc in selected):
            recommendations.append(
                "ℹ️ Smoke suite'de authentication test'i yok. Login akışını eklemeyi düşünün."
            )

    return recommendations


def coverage_report(
    testcases: list[dict],
    requirements: list[str] | None = None,
    modules: list[str] | None = None,
) -> dict:
    """
    Generate a coverage report for test cases.

    Args:
        testcases: List of test cases in QA-MCP standard format
        requirements: Optional list of requirement IDs to check coverage
        modules: Optional list of module names to check coverage

    Returns:
        Dictionary containing:
        - requirement_coverage: Coverage by requirements
        - module_coverage: Coverage by modules
        - risk_coverage: Coverage by risk levels
        - gaps: Identified coverage gaps
        - recommendations: Suggestions for improving coverage
    """
    # Parse test cases
    parsed_cases = []
    for tc_dict in testcases:
        try:
            tc = TestCase(**tc_dict)
            parsed_cases.append(tc)
        except Exception:
            continue

    # Requirement coverage
    req_coverage = {}
    all_covered_reqs = set()

    for tc in parsed_cases:
        for req in tc.requirements:
            all_covered_reqs.add(req)
            if req not in req_coverage:
                req_coverage[req] = []
            req_coverage[req].append(tc.id or tc.title)

    # Check against provided requirements
    req_analysis = None
    if requirements:
        covered = set(requirements) & all_covered_reqs
        uncovered = set(requirements) - all_covered_reqs
        req_analysis = {
            "total_requirements": len(requirements),
            "covered": len(covered),
            "uncovered": len(uncovered),
            "coverage_percent": round(len(covered) / len(requirements) * 100, 1)
            if requirements
            else 0,
            "uncovered_list": list(uncovered),
            "covered_list": list(covered),
        }

    # Module coverage
    all_tc_modules = set(tc.module for tc in parsed_cases if tc.module)
    module_test_count = {}
    for tc in parsed_cases:
        if tc.module:
            module_test_count[tc.module] = module_test_count.get(tc.module, 0) + 1

    module_analysis = None
    if modules:
        covered = set(modules) & all_tc_modules
        uncovered = set(modules) - all_tc_modules
        module_analysis = {
            "total_modules": len(modules),
            "covered": len(covered),
            "uncovered": len(uncovered),
            "coverage_percent": round(len(covered) / len(modules) * 100, 1) if modules else 0,
            "uncovered_list": list(uncovered),
            "test_count_per_module": {m: module_test_count.get(m, 0) for m in modules},
        }

    # Risk coverage analysis
    risk_distribution = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    for tc in parsed_cases:
        if tc.risk_level:
            risk_distribution[tc.risk_level.value] += 1

    # Scenario type analysis
    scenario_distribution = {
        "positive": 0,
        "negative": 0,
        "boundary": 0,
        "edge_case": 0,
        "error_handling": 0,
    }
    for tc in parsed_cases:
        if tc.scenario_type:
            scenario_distribution[tc.scenario_type.value] = (
                scenario_distribution.get(tc.scenario_type.value, 0) + 1
            )

    # Identify gaps
    gaps = []

    if scenario_distribution["negative"] < scenario_distribution["positive"] * 0.3:
        gaps.append(
            {
                "type": "scenario_balance",
                "description": "Negatif senaryolar yetersiz",
                "current": scenario_distribution["negative"],
                "recommended": int(scenario_distribution["positive"] * 0.3),
            }
        )

    if risk_distribution["critical"] == 0 and risk_distribution["high"] == 0:
        gaps.append(
            {
                "type": "risk_coverage",
                "description": "Kritik/Yüksek riskli test yok",
                "recommendation": "Kritik iş akışları için yüksek öncelikli test ekleyin",
            }
        )

    if req_analysis and req_analysis["uncovered"]:
        gaps.append(
            {
                "type": "requirement_coverage",
                "description": f"{len(req_analysis['uncovered_list'])} gereksinim karşılanmamış",
                "uncovered": req_analysis["uncovered_list"][:5],  # First 5
            }
        )

    # Recommendations
    recommendations = []

    total_tests = len(parsed_cases)
    if total_tests < 10:
        recommendations.append(
            "Test sayısı az. Daha kapsamlı test coverage için ek test case'ler oluşturun."
        )

    if scenario_distribution["boundary"] == 0:
        recommendations.append(
            "Boundary test'ler yok. Sınır değer analizi ile test case'ler ekleyin."
        )

    if not any(tc.test_data for tc in parsed_cases):
        recommendations.append(
            "Test data tanımlı değil. Data-driven testing yaklaşımını uygulayın."
        )

    return {
        "total_testcases": total_tests,
        "requirement_coverage": req_analysis,
        "requirement_mapping": req_coverage,
        "module_coverage": module_analysis,
        "module_test_count": module_test_count,
        "risk_distribution": risk_distribution,
        "scenario_distribution": scenario_distribution,
        "gaps": gaps,
        "recommendations": recommendations,
    }
