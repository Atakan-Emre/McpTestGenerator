"""
JSON Schemas for tool results (MCP revision 2025-11-25).

Declaring an ``outputSchema`` lets the MCP runtime return the result as
``structuredContent`` and validate it, so clients can consume tool output as
typed data instead of parsing a text blob.

The schemas are deliberately open (``additionalProperties`` is left permissive)
and mark only fields that every code path of a tool really returns as
``required`` - including its error paths, which are ordinary results here, not
protocol errors.
"""

from typing import Any

_STRING_ARRAY: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
_OBJECT_ARRAY: dict[str, Any] = {"type": "array", "items": {"type": "object"}}
_NULLABLE_OBJECT: dict[str, Any] = {"type": ["object", "null"]}


GENERATE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "testcases": {**_OBJECT_ARRAY, "description": "Üretilen standart test case'ler"},
        "suggestions": {**_STRING_ARRAY, "description": "Ek test önerileri"},
        "coverage_summary": {
            "type": "object",
            "properties": {
                "positive_scenarios": {"type": "integer"},
                "negative_scenarios": {"type": "integer"},
                "boundary_tests": {"type": "integer"},
                "acceptance_criteria_covered": _STRING_ARRAY,
            },
            "description": "Hangi senaryo tiplerinin kapsandığı",
        },
        "total_generated": {"type": "integer", "description": "Üretilen test case sayısı"},
    },
    "required": ["testcases", "suggestions", "coverage_summary", "total_generated"],
}


_LINT_ISSUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "severity": {"type": "string", "enum": ["error", "warning", "info"]},
        "field": {"type": "string"},
        "rule": {"type": "string"},
        "message": {"type": "string"},
        "suggestion": {"type": ["string", "null"]},
    },
    "required": ["severity", "field", "rule", "message"],
}

LINT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "grade": {"type": "string", "enum": ["A", "B", "C", "D", "F"]},
        "passed": {"type": "boolean", "description": "Minimum kalite eşiğini geçti mi"},
        "schema_valid": {
            "type": "boolean",
            "description": "Test case QA-MCP standardının şema kısıtlarına uyuyor mu",
        },
        "schema_errors": {**_STRING_ARRAY, "description": "Şema ihlallerinin detayı"},
        "issues": {"type": "array", "items": _LINT_ISSUE_SCHEMA},
        "suggestions": _STRING_ARRAY,
        "improvement_plan": _OBJECT_ARRAY,
        "summary": {"type": "object"},
    },
    "required": ["score", "grade", "passed", "schema_valid", "issues", "suggestions"],
}


LINT_BATCH_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "results": {"type": "array", "items": LINT_OUTPUT_SCHEMA},
        "aggregate": {
            "type": "object",
            "properties": {
                "total_testcases": {"type": "integer"},
                "average_score": {"type": "number"},
                "pass_rate": {"type": "number"},
                "passed_count": {"type": "integer"},
                "failed_count": {"type": "integer"},
                "total_issues": {"type": "integer"},
                "common_issues": _OBJECT_ARRAY,
            },
        },
        "recommendations": _STRING_ARRAY,
        "grade_distribution": {"type": "object"},
    },
    "required": ["results", "aggregate", "recommendations", "grade_distribution"],
}


NORMALIZE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "testcase": {
            **_NULLABLE_OBJECT,
            "description": "Standarda yükseltilmiş test case; parse edilemezse null",
        },
        "source_format_detected": {
            "type": "string",
            "enum": ["markdown", "gherkin", "json", "plain"],
        },
        "transformations": {**_STRING_ARRAY, "description": "Uygulanan dönüşümler"},
        "warnings": {**_STRING_ARRAY, "description": "Doldurulan veya değiştirilen alanlar"},
        "error": {"type": "string"},
    },
    "required": ["testcase", "source_format_detected", "transformations", "warnings"],
}


_FIELD_MAPPING_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mapped_fields": {
            **_STRING_ARRAY,
            "description": "Birinci sınıf Xray alanlarına yazılanlar",
        },
        "embedded_in_description": {
            **_STRING_ARRAY,
            "description": "Xray karşılığı olmadığı için description gövdesine gömülenler",
        },
        "unmapped_fields": {**_STRING_ARRAY, "description": "Gerçekten aktarılamayan alanlar"},
        "custom_fields_used": _STRING_ARRAY,
    },
}

TO_XRAY_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "xray_payload": {**_NULLABLE_OBJECT, "description": "Import'a hazır Xray JSON"},
        "field_mapping_report": _FIELD_MAPPING_REPORT_SCHEMA,
        "warnings": _STRING_ARRAY,
        "error": {"type": "string"},
    },
    "required": ["xray_payload", "field_mapping_report", "warnings"],
}


TO_XRAY_BATCH_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "xray_payloads": _OBJECT_ARRAY,
        "import_payload": {"type": "object"},
        "summary": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "successful": {"type": "integer"},
                "failed": {"type": "integer"},
            },
        },
        "warnings": _STRING_ARRAY,
    },
    "required": ["xray_payloads", "import_payload", "summary", "warnings"],
}


COMPOSE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suite": {**_NULLABLE_OBJECT, "description": "Oluşturulan suite; hata durumunda null"},
        "selected_testcases": _OBJECT_ARRAY,
        "excluded_count": {"type": "integer"},
        "selection_rationale": {
            **_OBJECT_ARRAY,
            "description": "Her test case'in neden dahil edildiği/edilmediği",
        },
        "coverage_summary": {"type": "object"},
        "recommendations": _STRING_ARRAY,
        "duration_warning": {"type": "boolean"},
        "errors": _STRING_ARRAY,
    },
    "required": ["suite", "selection_rationale", "coverage_summary", "recommendations"],
}


COVERAGE_REPORT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "total_testcases": {"type": "integer"},
        "skipped_testcases": {
            **_OBJECT_ARRAY,
            "description": "Standarda uymadığı için rapora alınamayan test case'ler",
        },
        "requirement_coverage": _NULLABLE_OBJECT,
        "requirement_mapping": {"type": "object"},
        "module_coverage": _NULLABLE_OBJECT,
        "module_test_count": {"type": "object"},
        "risk_distribution": {"type": "object"},
        "scenario_distribution": {"type": "object"},
        "gaps": {**_OBJECT_ARRAY, "description": "Tespit edilen kapsam boşlukları"},
        "recommendations": _STRING_ARRAY,
    },
    "required": [
        "total_testcases",
        "skipped_testcases",
        "risk_distribution",
        "scenario_distribution",
        "gaps",
        "recommendations",
    ],
}


XRAY_MAPPING_TEMPLATE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "standard_mappings": {"type": "object"},
        "custom_field_suggestions": {"type": "object"},
        "xray_specific": {"type": "object"},
        "notes": _STRING_ARRAY,
    },
    "required": ["standard_mappings", "custom_field_suggestions", "xray_specific", "notes"],
}


OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "testcase_generate": GENERATE_OUTPUT_SCHEMA,
    "testcase_lint": LINT_OUTPUT_SCHEMA,
    "testcase_lint_batch": LINT_BATCH_OUTPUT_SCHEMA,
    "testcase_normalize": NORMALIZE_OUTPUT_SCHEMA,
    "testcase_to_xray": TO_XRAY_OUTPUT_SCHEMA,
    "testcase_to_xray_batch": TO_XRAY_BATCH_OUTPUT_SCHEMA,
    "suite_compose": COMPOSE_OUTPUT_SCHEMA,
    "suite_coverage_report": COVERAGE_REPORT_OUTPUT_SCHEMA,
    "xray_get_mapping_template": XRAY_MAPPING_TEMPLATE_OUTPUT_SCHEMA,
}
