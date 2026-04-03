"""
Test Case Normalization Tool.

Converts test cases from various formats to the QA-MCP standard format.
"""

import re
import uuid
from datetime import datetime

from qa_mcp.core.models import (
    Priority,
    RiskLevel,
    ScenarioType,
    TestCase,
    TestStep,
)


def _ensure_list(value: str | list[str] | None) -> list[str]:
    """Normalize scalar or list inputs into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str) and item.strip()]


def normalize_testcase(
    input_data: str | dict,
    source_format: str = "auto",
) -> dict:
    """
    Normalize a test case from various formats to QA-MCP standard.

    Args:
        input_data: Test case in string (markdown/gherkin) or dict format
        source_format: Source format - 'auto', 'markdown', 'gherkin', 'json', 'plain'

    Returns:
        Dictionary containing:
        - testcase: Normalized test case in standard format
        - source_format_detected: Detected source format
        - transformations: List of transformations applied
        - warnings: Any warnings during normalization
    """
    transformations: list[str] = []
    warnings: list[str] = []
    text_input = input_data if isinstance(input_data, str) else str(input_data)

    # Detect format if auto
    if source_format == "auto":
        source_format = _detect_format(input_data)
        transformations.append(f"Format otomatik tespit edildi: {source_format}")

    # Parse based on format
    try:
        if source_format == "gherkin":
            testcase, parse_warnings = _parse_gherkin(text_input)
        elif source_format == "markdown":
            testcase, parse_warnings = _parse_markdown(text_input)
        elif source_format == "json" or isinstance(input_data, dict):
            testcase, parse_warnings = _parse_json(input_data)
        else:  # plain text
            testcase, parse_warnings = _parse_plain_text(text_input)

        warnings.extend(parse_warnings)

    except Exception as e:
        return {
            "testcase": None,
            "source_format_detected": source_format,
            "transformations": transformations,
            "warnings": [f"Parse hatası: {str(e)}"],
            "error": str(e),
        }

    # Validate and fill missing fields
    testcase, fill_warnings = _fill_missing_fields(testcase)
    warnings.extend(fill_warnings)
    transformations.append("Eksik alanlar varsayılan değerlerle dolduruldu")

    # Normalize values
    testcase = _normalize_values(testcase)
    transformations.append("Değerler standartlaştırıldı")

    return {
        "testcase": testcase.model_dump(),
        "source_format_detected": source_format,
        "transformations": transformations,
        "warnings": warnings,
    }


def _detect_format(input_data: str | dict) -> str:
    """Detect the format of input data."""
    if isinstance(input_data, dict):
        return "json"

    text = str(input_data).strip()

    # Gherkin detection
    gherkin_keywords = ["Feature:", "Scenario:", "Given", "When", "Then", "And", "But"]
    if any(kw in text for kw in gherkin_keywords):
        return "gherkin"

    # Markdown detection
    if text.startswith("#") or "## " in text or "**" in text:
        return "markdown"

    return "plain"


def _parse_gherkin(input_data: str) -> tuple[TestCase, list[str]]:
    """Parse Gherkin format test case."""
    warnings: list[str] = []
    text = str(input_data).strip()
    lines = text.split("\n")

    title = ""
    description = ""
    steps: list[TestStep] = []
    preconditions: list[str] = []
    step_number = 0
    current_actions: list[str] = []
    current_expectations: list[str] = []
    last_context: str | None = None

    def flush_step() -> None:
        nonlocal step_number, current_actions, current_expectations
        if not current_actions:
            return

        step_number += 1
        steps.append(
            TestStep(
                step_number=step_number,
                action="; ".join(current_actions),
                expected_result="; ".join(current_expectations) or "[Beklenen sonuç belirtilmeli]",
            )
        )
        current_actions = []
        current_expectations = []

    for line in lines:
        line = line.strip()

        if line.startswith("Feature:"):
            description = line[8:].strip()
        elif line.startswith("Scenario:"):
            flush_step()
            title = line[9:].strip()
            last_context = None
        elif line.startswith("Given"):
            flush_step()
            preconditions.append(line[5:].strip())
            last_context = "given"
        elif line.startswith("When"):
            flush_step()
            current_actions = [line[4:].strip()]
            current_expectations = []
            last_context = "when"
        elif line.startswith("Then"):
            current_expectations.append(line[4:].strip())
            last_context = "then"
        elif line.startswith("And") or line.startswith("But"):
            content = line[3:].strip()
            if last_context == "given":
                preconditions.append(content)
            elif last_context == "when":
                current_actions.append(content)
            elif last_context == "then":
                current_expectations.append(content)
            else:
                warnings.append(f"Bağlamı belirsiz Gherkin satırı atlandı: {line}")

    flush_step()

    if not title:
        title = "Gherkin'den içe aktarılan test case senaryosu"
        warnings.append("Scenario adı bulunamadı, varsayılan başlık kullanıldı")

    # Ensure title meets minimum length
    if len(title) < 10:
        title = f"Gherkin Senaryo: {title}"

    if not steps:
        warnings.append("Test adımları çıkarılamadı")
        steps = [
            TestStep(
                step_number=1,
                action="[Gherkin'den çevrilecek - adım tanımlanmalı]",
                expected_result="[Gherkin'den çevrilecek - sonuç tanımlanmalı]",
            )
        ]

    # Build description ensuring minimum length
    if not description:
        description = f"Gherkin senaryosundan dönüştürüldü: {title}"
    if len(description) < 20:
        description = f"Gherkin Feature: {description} - otomatik dönüştürülmüş senaryo"

    # Build expected result ensuring minimum length
    expected = steps[-1].expected_result if steps else "[Beklenen sonuç belirtilmeli]"
    if len(expected) < 10:
        expected = f"Senaryo sonucu: {expected}"

    tc = TestCase(
        id=f"TC-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        description=description,
        preconditions=preconditions if preconditions else ["[Ön koşullar belirtilmeli]"],
        steps=steps,
        expected_result=expected,
        tags=["gherkin-import"],
    )

    return tc, warnings


def _parse_markdown(input_data: str) -> tuple[TestCase, list[str]]:
    """Parse Markdown format test case."""
    warnings = []
    text = str(input_data).strip()
    lines = text.split("\n")

    title = ""
    description = ""
    preconditions = []
    steps = []
    expected_result = ""
    current_section = None
    step_number = 0

    for line in lines:
        line_stripped = line.strip()

        # Title detection
        if line_stripped.startswith("# "):
            title = line_stripped[2:].strip()
        elif line_stripped.startswith("## "):
            section_name = line_stripped[3:].strip().lower()
            if "description" in section_name or "açıklama" in section_name:
                current_section = "description"
            elif "precondition" in section_name or "ön koşul" in section_name:
                current_section = "preconditions"
            elif "step" in section_name or "adım" in section_name:
                current_section = "steps"
            elif "expected" in section_name or "beklenen" in section_name:
                current_section = "expected"
        elif line_stripped.startswith("- ") or line_stripped.startswith("* "):
            content = line_stripped[2:].strip()
            if current_section == "preconditions":
                preconditions.append(content)
            elif current_section == "steps":
                step_number += 1
                # Try to split action and expected
                if " -> " in content:
                    parts = content.split(" -> ")
                    steps.append(
                        TestStep(
                            step_number=step_number,
                            action=parts[0].strip(),
                            expected_result=parts[1].strip()
                            if len(parts) > 1
                            else "[Belirtilmeli]",
                        )
                    )
                else:
                    steps.append(
                        TestStep(
                            step_number=step_number,
                            action=content,
                            expected_result="[Beklenen sonuç belirtilmeli]",
                        )
                    )
        elif line_stripped and current_section == "description":
            description += line_stripped + " "
        elif line_stripped and current_section == "expected":
            expected_result += line_stripped + " "

    if not title:
        title = "Markdown'dan içe aktarılan test case"
        warnings.append("Başlık bulunamadı")

    if not steps:
        warnings.append("Test adımları çıkarılamadı")
        steps = [
            TestStep(
                step_number=1,
                action="[Markdown'dan çevrilecek]",
                expected_result="[Markdown'dan çevrilecek]",
            )
        ]

    tc = TestCase(
        id=f"TC-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        description=description.strip() or f"Markdown'dan dönüştürüldü: {title}",
        preconditions=preconditions if preconditions else ["[Ön koşullar belirtilmeli]"],
        steps=steps,
        expected_result=expected_result.strip() or steps[-1].expected_result,
        tags=["markdown-import"],
    )

    return tc, warnings


def _parse_json(input_data: str | dict) -> tuple[TestCase, list[str]]:
    """Parse JSON/dict format test case."""
    warnings: list[str] = []

    if isinstance(input_data, str):
        import json

        data = json.loads(input_data)
    else:
        data = input_data

    # Try direct parsing first
    try:
        tc = TestCase(**data)
        return tc, warnings
    except Exception:
        pass

    # Manual field mapping for non-standard formats
    title = (
        data.get("title") or data.get("name") or data.get("summary") or "İçe aktarılan test case"
    )
    description = data.get("description") or data.get("desc") or f"Test case: {title}"

    # Preconditions
    preconditions = data.get("preconditions") or data.get("prerequisites") or []
    if isinstance(preconditions, str):
        preconditions = [preconditions]

    # Steps
    raw_steps = data.get("steps") or data.get("test_steps") or []
    steps = []
    for idx, step in enumerate(raw_steps, 1):
        if isinstance(step, dict):
            steps.append(
                TestStep(
                    step_number=idx,
                    action=step.get("action") or step.get("step") or str(step),
                    expected_result=step.get("expected_result")
                    or step.get("expected")
                    or "[Belirtilmeli]",
                )
            )
        elif isinstance(step, str):
            steps.append(
                TestStep(
                    step_number=idx,
                    action=step,
                    expected_result="[Beklenen sonuç belirtilmeli]",
                )
            )

    if not steps:
        steps = [
            TestStep(
                step_number=1,
                action="[Adım belirtilmeli]",
                expected_result="[Beklenen sonuç belirtilmeli]",
            )
        ]
        warnings.append("Test adımları bulunamadı")

    # Expected result
    expected_result = (
        data.get("expected_result")
        or data.get("expected")
        or data.get("outcome")
        or steps[-1].expected_result
    )

    tags = _ensure_list(data.get("tags"))
    labels = _ensure_list(data.get("labels"))
    requirements = _ensure_list(data.get("requirements"))
    related_testcases = _ensure_list(data.get("related_testcases"))

    if not tags:
        tags = ["json-import"]

    tc = TestCase(
        id=data.get("id") or f"TC-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        description=description,
        preconditions=preconditions if preconditions else ["[Ön koşullar belirtilmeli]"],
        steps=steps,
        expected_result=expected_result,
        module=data.get("module") or data.get("component"),
        feature=data.get("feature"),
        scenario_type=ScenarioType(data["scenario_type"])
        if data.get("scenario_type") in {scenario.value for scenario in ScenarioType}
        else ScenarioType.POSITIVE,
        risk_level=RiskLevel(data["risk_level"])
        if data.get("risk_level") in {risk.value for risk in RiskLevel}
        else RiskLevel.MEDIUM,
        priority=Priority(data["priority"])
        if data.get("priority") in ["P0", "P1", "P2", "P3"]
        else Priority.P2,
        tags=tags,
        labels=labels,
        estimated_duration_minutes=data.get("estimated_duration_minutes")
        if isinstance(data.get("estimated_duration_minutes"), int)
        else None,
        requirements=requirements,
        related_testcases=related_testcases,
    )

    return tc, warnings


def _parse_plain_text(input_data: str) -> tuple[TestCase, list[str]]:
    """Parse plain text format test case."""
    warnings = []
    text = str(input_data).strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # First line as title
    title = lines[0] if lines else "Düz metinden içe aktarılan test case"

    # Rest as description/steps
    description = " ".join(lines[1:]) if len(lines) > 1 else title

    if len(title) < 10:
        title = f"Düz metin: {title}"
    if len(description) < 20:
        description = f"Düz metinden dönüştürülen not: {description}"

    # Try to extract numbered steps
    steps = []
    step_pattern = re.compile(r"^(\d+)[.\)]\s*(.+)$")

    for line in lines[1:]:
        match = step_pattern.match(line)
        if match:
            step_num = int(match.group(1))
            action = match.group(2)
            steps.append(
                TestStep(
                    step_number=step_num,
                    action=action,
                    expected_result="[Beklenen sonuç belirtilmeli]",
                )
            )

    if not steps:
        warnings.append(
            "Numaralandırılmış adımlar bulunamadı, tüm metin açıklama olarak kullanıldı"
        )
        steps = [
            TestStep(
                step_number=1,
                action=description[:200] if len(description) > 200 else description,
                expected_result="[Beklenen sonuç belirtilmeli]",
            )
        ]

    tc = TestCase(
        id=f"TC-{uuid.uuid4().hex[:8].upper()}",
        title=title[:200] if len(title) > 200 else title,
        description=description,
        preconditions=["[Ön koşullar belirtilmeli]"],
        steps=steps,
        expected_result="[Beklenen sonuç belirtilmeli]",
        tags=["plain-text-import"],
    )

    warnings.append("Düz metin formatı sınırlı yapı sağlar, manuel düzenleme önerilir")

    return tc, warnings


def _fill_missing_fields(tc: TestCase) -> tuple[TestCase, list[str]]:
    """Fill missing fields with defaults."""
    warnings: list[str] = []

    if not tc.id:
        tc.id = f"TC-{uuid.uuid4().hex[:8].upper()}"

    if tc.created_at is None:
        tc.created_at = datetime.now()

    if tc.updated_at is None:
        tc.updated_at = tc.created_at

    if tc.risk_level is None:
        tc.risk_level = RiskLevel.MEDIUM
        warnings.append("Risk seviyesi belirtilmedi, 'medium' olarak ayarlandı")

    if tc.priority is None:
        tc.priority = Priority.P2
        warnings.append("Öncelik belirtilmedi, 'P2' olarak ayarlandı")

    if tc.scenario_type is None:
        tc.scenario_type = ScenarioType.POSITIVE

    return tc, warnings


def _normalize_values(tc: TestCase) -> TestCase:
    """Normalize field values."""
    # Trim whitespace
    tc.title = tc.title.strip()
    tc.description = tc.description.strip()
    tc.expected_result = tc.expected_result.strip()

    # Normalize preconditions
    tc.preconditions = [p.strip() for p in tc.preconditions if p.strip()]

    # Normalize steps
    for step in tc.steps:
        step.action = step.action.strip()
        step.expected_result = step.expected_result.strip()

    # Normalize tags (lowercase)
    tc.tags = [t.lower().strip() for t in tc.tags if t.strip()]

    return tc
