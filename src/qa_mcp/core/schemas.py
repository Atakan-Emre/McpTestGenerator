"""
JSON Schemas for tool results.

Derived from the Pydantic models in ``qa_mcp.core.results``, which are the
single definition of what a tool returns: the model validates the runtime
value, and its generated schema is what the MCP runtime publishes as the
tool's ``outputSchema``. Maintaining the two by hand let them drift.
"""

from typing import Any

from qa_mcp.core.results import RESULT_MODELS

OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    name: model.model_json_schema() for name, model in RESULT_MODELS.items()
}
