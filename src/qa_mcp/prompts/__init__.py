"""MCP Prompts for QA-MCP."""

from qa_mcp.prompts.templates import (
    PROMPT_REGISTRY,
    get_create_manual_test_prompt,
    get_generate_negative_scenarios_prompt,
    get_review_test_coverage_prompt,
    get_select_smoke_tests_prompt,
)

__all__ = [
    "get_create_manual_test_prompt",
    "get_select_smoke_tests_prompt",
    "get_generate_negative_scenarios_prompt",
    "get_review_test_coverage_prompt",
    "PROMPT_REGISTRY",
]
