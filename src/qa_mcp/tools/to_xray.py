"""
Xray Conversion Tool.

Converts QA-MCP standard test cases to Xray import format.
"""

from typing import Any

from qa_mcp.core.models import Priority, TestCase

# Xray field mappings
XRAY_PRIORITY_MAP = {
    Priority.P0: "Highest",
    Priority.P1: "High",
    Priority.P2: "Medium",
    Priority.P3: "Low",
}

XRAY_TEST_TYPE_MAP = {
    "Manual": "Manual",
    "Automated": "Generic",
    "Generic": "Generic",
}

# Fields written to first-class Xray/Jira fields.
MAPPED_BASE_FIELDS = frozenset(
    {
        "title",
        "description",
        "test_type",
        "priority",
        "labels",
        "tags",
        "module",
        "steps",
        "preconditions",
    }
)

# Fields that have no Xray equivalent but are rendered into the description body
# by _build_xray_description, so no information is lost.
DESCRIPTION_EMBEDDED_FIELDS = frozenset(
    {
        "expected_result",
        "scenario_type",
        "risk_level",
        "feature",
        "requirements",
        "estimated_duration_minutes",
        "test_data",
    }
)

# Bookkeeping fields that Jira owns itself.
IGNORED_FIELDS = frozenset({"id", "created_at", "updated_at", "author"})


def convert_to_xray(
    testcase: dict,
    project_key: str,
    test_type: str | None = None,
    include_custom_fields: bool = True,
    custom_field_mappings: dict[str, str] | None = None,
) -> dict:
    """
    Convert a QA-MCP test case to Xray import format.

    Args:
        testcase: Test case in QA-MCP standard format
        project_key: Jira project key (e.g., 'PROJ')
        test_type: Xray test type - 'Manual', 'Automated', 'Generic'.
            Defaults to the test case's own ``test_type``.
        include_custom_fields: Whether to include custom field mappings
        custom_field_mappings: Custom field ID mappings (e.g., {'risk_level': 'customfield_10001'})

    Returns:
        Dictionary containing:
        - xray_payload: Ready-to-import Xray JSON
        - field_mapping_report: Which fields were mapped
        - warnings: Any conversion warnings
    """
    warnings: list[str] = []
    field_mapping_report: dict[str, list[str]] = {
        "mapped_fields": [],
        "embedded_in_description": [],
        "unmapped_fields": [],
        "custom_fields_used": [],
    }

    # Parse test case
    try:
        tc = TestCase(**testcase)
    except Exception as e:
        return {
            "xray_payload": None,
            "field_mapping_report": field_mapping_report,
            "warnings": [f"Test case parse hatası: {str(e)}"],
            "error": str(e),
        }

    # Build Xray payload
    effective_test_type = test_type or (tc.test_type.value if tc.test_type else "Manual")
    xray_payload: dict[str, Any] = {
        "testtype": XRAY_TEST_TYPE_MAP.get(effective_test_type, "Manual"),
        "fields": {
            "project": {"key": project_key},
            "summary": tc.title,
            "description": _build_xray_description(tc),
            "issuetype": {"name": "Test"},
        },
    }
    field_mapping_report["mapped_fields"].extend(["title", "description", "test_type"])

    # Priority mapping
    if tc.priority:
        xray_payload["fields"]["priority"] = {"name": XRAY_PRIORITY_MAP.get(tc.priority, "Medium")}
        field_mapping_report["mapped_fields"].append("priority")

    # Labels
    labels = list(tc.labels) + list(tc.tags)
    if labels:
        xray_payload["fields"]["labels"] = labels
        field_mapping_report["mapped_fields"].append("labels")

    # Components (from module)
    if tc.module:
        xray_payload["fields"]["components"] = [{"name": tc.module}]
        field_mapping_report["mapped_fields"].append("module->components")

    # Test steps (Xray specific format)
    xray_steps = _build_xray_steps(tc)
    if xray_steps:
        xray_payload["steps"] = xray_steps
        field_mapping_report["mapped_fields"].append("steps")

    # Preconditions
    if tc.preconditions:
        xray_payload["preconditions"] = "\n".join(f"• {p}" for p in tc.preconditions)
        field_mapping_report["mapped_fields"].append("preconditions")

    # Custom fields
    mapped_custom_qa_fields: set[str] = set()
    if include_custom_fields:
        custom_fields, mapped_custom_qa_fields = _build_custom_fields(tc, custom_field_mappings)
        if custom_fields:
            xray_payload["fields"].update(custom_fields)
            field_mapping_report["custom_fields_used"] = list(custom_fields.keys())

    # Track how every remaining field was handled. Fields that _build_xray_description
    # writes into the description are reported as embedded, not as unmapped: they
    # always carry a value (enums have defaults), so reporting them as losses
    # produced a warning on literally every conversion.
    all_tc_fields = set(TestCase.model_fields.keys())
    for field in sorted(
        all_tc_fields - MAPPED_BASE_FIELDS - IGNORED_FIELDS - mapped_custom_qa_fields
    ):
        value = getattr(tc, field, None)
        if not value:
            continue
        if field in DESCRIPTION_EMBEDDED_FIELDS:
            field_mapping_report["embedded_in_description"].append(field)
        else:
            field_mapping_report["unmapped_fields"].append(field)
            warnings.append(
                f"'{field}' alanı Xray'e map edilemedi - custom field ekleyin veya issue link kullanın"
            )

    return {
        "xray_payload": xray_payload,
        "field_mapping_report": field_mapping_report,
        "warnings": warnings,
    }


def convert_batch_to_xray(
    testcases: list[dict],
    project_key: str,
    test_type: str | None = None,
    include_custom_fields: bool = True,
    custom_field_mappings: dict[str, str] | None = None,
) -> dict:
    """
    Convert multiple test cases to Xray import format.

    Args:
        testcases: List of test cases in QA-MCP standard format
        project_key: Jira project key
        test_type: Xray test type
        include_custom_fields: Whether to include custom fields
        custom_field_mappings: Custom field ID mappings

    Returns:
        Dictionary containing:
        - xray_payloads: List of Xray-ready payloads
        - import_payload: Combined payload for bulk import
        - summary: Conversion summary
        - warnings: Aggregated warnings
    """
    results = []
    all_warnings = []
    successful = 0
    failed = 0

    for idx, tc in enumerate(testcases):
        result = convert_to_xray(
            testcase=tc,
            project_key=project_key,
            test_type=test_type,
            include_custom_fields=include_custom_fields,
            custom_field_mappings=custom_field_mappings,
        )

        if result.get("error"):
            failed += 1
            all_warnings.append(f"Test case {idx + 1}: {result['error']}")
        else:
            successful += 1
            results.append(result["xray_payload"])

        all_warnings.extend(result.get("warnings", []))

    # Build bulk import payload (Xray JSON format)
    import_payload = {
        "tests": results,
    }

    return {
        "xray_payloads": results,
        "import_payload": import_payload,
        "summary": {
            "total": len(testcases),
            "successful": successful,
            "failed": failed,
        },
        "warnings": all_warnings,
    }


def _build_xray_description(tc: TestCase) -> str:
    """Build Xray-compatible description field.

    Xray has no field for the test case's overall expected result, so it is
    rendered here. Dropping it silently used to lose the single most important
    assertion of the test case.
    """
    parts = [tc.description]

    if tc.expected_result:
        parts.append("\n\n*Beklenen Sonuç:*")
        parts.append(tc.expected_result)

    if tc.feature:
        parts.append(f"\n*Feature:* {tc.feature}")

    # Add structured information
    parts.append("\n\n*Test Bilgileri:*")
    parts.append(
        f"• Senaryo Tipi: {tc.scenario_type.value if tc.scenario_type else 'Belirtilmemiş'}"
    )
    parts.append(f"• Risk Seviyesi: {tc.risk_level.value if tc.risk_level else 'Belirtilmemiş'}")

    if tc.requirements:
        parts.append(f"• Gereksinimler: {', '.join(tc.requirements)}")

    if tc.estimated_duration_minutes:
        parts.append(f"• Tahmini Süre: {tc.estimated_duration_minutes} dakika")

    # Test data summary
    if tc.test_data:
        parts.append("\n*Test Verisi:*")
        for data in tc.test_data[:5]:  # Limit to 5
            parts.append(f"• {data.name}: {data.value}")

    return "\n".join(parts)


def _build_xray_steps(tc: TestCase) -> list[dict]:
    """Build Xray step format."""
    xray_steps = []

    for step in tc.steps:
        xray_step = {
            "action": step.action,
            "result": step.expected_result,
        }

        # Add test data as 'data' field if present
        if step.test_data:
            data_str = ", ".join(f"{d.name}={d.value}" for d in step.test_data)
            xray_step["data"] = data_str

        xray_steps.append(xray_step)

    return xray_steps


def _build_custom_fields(
    tc: TestCase,
    custom_field_mappings: dict[str, str] | None,
) -> tuple[dict[str, Any], set[str]]:
    """Build custom field values based on mappings."""
    custom_fields: dict[str, Any] = {}
    mapped_qa_fields: set[str] = set()

    if not custom_field_mappings:
        return custom_fields, mapped_qa_fields

    # Map known fields
    field_values = {
        "risk_level": tc.risk_level.value if tc.risk_level else None,
        "scenario_type": tc.scenario_type.value if tc.scenario_type else None,
        "feature": tc.feature,
        "estimated_duration_minutes": tc.estimated_duration_minutes,
        "estimated_duration": tc.estimated_duration_minutes,
        "requirements": ", ".join(tc.requirements) if tc.requirements else None,
    }

    for qa_field, xray_field_id in custom_field_mappings.items():
        value = field_values.get(qa_field)
        if value is not None:
            custom_fields[xray_field_id] = value
            mapped_qa_fields.add(qa_field)
            if qa_field == "estimated_duration":
                mapped_qa_fields.add("estimated_duration_minutes")

    return custom_fields, mapped_qa_fields


def get_xray_field_mapping_template() -> dict:
    """
    Get a template for Xray field mappings.

    Returns:
        Dictionary with QA-MCP fields and suggested Xray mappings
    """
    return {
        "standard_mappings": {
            "title": "summary",
            "description": "description",
            "priority": "priority",
            "module": "components",
            "tags": "labels",
            "labels": "labels",
            "steps": "Test Steps (Xray built-in)",
            "preconditions": "Precondition (Xray built-in)",
        },
        "custom_field_suggestions": {
            "risk_level": "customfield_XXXXX (Text/Select)",
            "scenario_type": "customfield_XXXXX (Select)",
            "feature": "customfield_XXXXX (Text)",
            "estimated_duration_minutes": "customfield_XXXXX (Number)",
            "requirements": "customfield_XXXXX (Text) veya Issue Links",
        },
        "xray_specific": {
            "test_type": "testtype (Manual/Generic/Cucumber)",
            "test_repository_folder": "Xray Test Repository klasörü",
            "test_sets": "Test Set issue links",
            "test_plans": "Test Plan issue links",
        },
        "notes": [
            "Custom field ID'leri Jira admin'den alınmalı",
            "Select tipi alanlar için önce option'lar oluşturulmalı",
            "Issue links için link type tanımlanmalı",
        ],
    }
