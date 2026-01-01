"""MCP Resources for QA-MCP."""

from qa_mcp.resources.standards import (
    get_bad_examples,
    get_good_examples,
    get_lint_rules,
    get_testcase_standard,
    get_xray_mapping,
)

__all__ = [
    "get_testcase_standard",
    "get_lint_rules",
    "get_xray_mapping",
    "get_good_examples",
    "get_bad_examples",
]
