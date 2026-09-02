"""
Test Case Lint Tool.

Analyzes test cases for quality issues and provides improvement suggestions.
"""

from typing import Any, TypedDict

from qa_mcp.core.lint import LintEngine
from qa_mcp.core.models import LintResult, TestCase, TestCaseDraft
from qa_mcp.core.standards import TestCaseStandard


class CommonIssue(TypedDict):
    rule: str
    count: int


def lint_testcase(
    testcase: dict,
    include_improvement_plan: bool = True,
    strict_mode: bool = False,
) -> dict:
    """
    Lint a test case and return quality analysis.

    Args:
        testcase: Test case dictionary to analyze
        include_improvement_plan: Whether to include prioritized improvement plan
        strict_mode: If True, applies stricter validation rules

    Returns:
        Dictionary containing:
        - score: Quality score (0-100)
        - grade: Letter grade (A-F)
        - passed: Whether it meets minimum threshold
        - issues: List of found issues
        - suggestions: General improvement suggestions
        - improvement_plan: Prioritized actions (if requested)
    """
    # Initialize engine
    standard = TestCaseStandard.get_default()
    if strict_mode:
        standard.minimum_score = 75  # Higher threshold in strict mode

    engine = LintEngine(standard)

    # Parse into the permissive draft model. A test case that violates the
    # standard is precisely what lint exists to report on, so it must not be
    # rejected before the rules get to run.
    try:
        tc = TestCaseDraft(**testcase)
    except Exception as e:
        return {
            "score": 0,
            "grade": "F",
            "passed": False,
            "schema_valid": False,
            "schema_errors": [str(e)],
            "issues": [
                {
                    "severity": "error",
                    "field": "structure",
                    "rule": "valid_structure",
                    "message": f"Test case yapısı okunamadı: {str(e)}",
                    "suggestion": "Alan tiplerini kontrol edin (steps bir liste, tags bir string listesi olmalı)",
                }
            ],
            "suggestions": ["Test case yapısını QA-MCP standardına göre düzeltin"],
            "improvement_plan": [],
            "error": str(e),
        }

    # Separately record whether the input also satisfies the strict standard.
    schema_errors: list[str] = []
    try:
        TestCase(**testcase)
    except Exception as e:
        schema_errors.append(str(e))

    # Run lint
    result: LintResult = engine.lint(tc)

    # Build response
    response = {
        "score": result.score,
        "grade": result.grade,
        "passed": result.passed,
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "issues": [
            {
                "severity": issue.severity.value,
                "field": issue.field,
                "rule": issue.rule,
                "message": issue.message,
                "suggestion": issue.suggestion,
            }
            for issue in result.issues
        ],
        "suggestions": result.suggestions,
    }

    # Add improvement plan if requested
    if include_improvement_plan:
        response["improvement_plan"] = engine.get_improvement_plan(result)

    # Add summary statistics
    response["summary"] = {
        "total_issues": len(result.issues),
        "errors": sum(1 for i in result.issues if i.severity.value == "error"),
        "warnings": sum(1 for i in result.issues if i.severity.value == "warning"),
        "info": sum(1 for i in result.issues if i.severity.value == "info"),
        "minimum_score": standard.minimum_score,
    }

    return response


def lint_batch(
    testcases: list[dict],
    include_improvement_plan: bool = False,
    strict_mode: bool = False,
) -> dict:
    """
    Lint multiple test cases and provide aggregate analysis.

    Args:
        testcases: List of test case dictionaries
        include_improvement_plan: Whether to include improvement plans
        strict_mode: If True, applies stricter validation rules

    Returns:
        Dictionary containing:
        - results: Individual lint results for each test case
        - aggregate: Aggregate statistics
        - recommendations: Overall recommendations
    """
    results: list[dict[str, Any]] = []
    total_score = 0
    total_passed = 0
    all_issues: list[dict[str, Any]] = []

    for idx, tc in enumerate(testcases):
        result = lint_testcase(tc, include_improvement_plan, strict_mode)
        result["index"] = idx
        result["testcase_id"] = tc.get("id", f"TC-{idx + 1}")
        results.append(result)

        total_score += result["score"]
        if result["passed"]:
            total_passed += 1
        all_issues.extend(result["issues"])

    # Calculate aggregate statistics
    count = len(testcases)
    avg_score = total_score / count if count > 0 else 0
    pass_rate = (total_passed / count * 100) if count > 0 else 0

    # Find common issues
    issue_counts: dict[str, int] = {}
    for issue in all_issues:
        key = issue.get("rule")
        if isinstance(key, str):
            issue_counts[key] = issue_counts.get(key, 0) + 1

    issue_items: list[CommonIssue] = [{"rule": k, "count": v} for k, v in issue_counts.items()]
    common_issues = sorted(
        issue_items,
        key=lambda x: x["count"],
        reverse=True,
    )[:5]  # Top 5 common issues

    # Generate recommendations
    recommendations = []
    if avg_score < 60:
        recommendations.append("Genel test case kalitesi düşük. Standart eğitimi önerilir.")
    if any(i["rule"] == "preconditions.required" for i in common_issues):
        recommendations.append("Birçok test case'de ön koşullar eksik. Bu alanı zorunlu kılın.")
    if any(i["rule"] == "test_data.recommended" for i in common_issues):
        recommendations.append(
            "Test data tanımlaması yetersiz. Data-driven testing pratiklerini uygulayın."
        )
    if pass_rate < 70:
        recommendations.append(
            f"Geçme oranı düşük (%{pass_rate:.1f}). Kalite kapısı standartlarını gözden geçirin."
        )

    return {
        "results": results,
        "aggregate": {
            "total_testcases": count,
            "average_score": round(avg_score, 1),
            "pass_rate": round(pass_rate, 1),
            "passed_count": total_passed,
            "failed_count": count - total_passed,
            "total_issues": len(all_issues),
            "common_issues": common_issues,
        },
        "recommendations": recommendations,
        "grade_distribution": _calculate_grade_distribution(results),
    }


def _calculate_grade_distribution(results: list[dict]) -> dict:
    """Calculate distribution of grades."""
    distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for result in results:
        grade = result.get("grade", "F")
        distribution[grade] = distribution.get(grade, 0) + 1
    return distribution
