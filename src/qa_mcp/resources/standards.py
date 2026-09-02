"""
MCP Resources - Standards, Rules, and Examples.

These resources are exposed to LLM clients as static reference data.

The content lives as JSON under ``data/``, inside the package, and is read
through ``importlib.resources`` so it resolves from an installed wheel as well
as from a source checkout. It used to be duplicated: a hand-maintained copy in
this module and a second copy in a repository-level ``resources/`` directory
that nothing ever read and that had already drifted from it.
"""

import json
from functools import cache
from importlib import resources
from typing import Any

DATA_PACKAGE = "qa_mcp.resources.data"


@cache
def _load(relative_path: str) -> dict[str, Any]:
    """Read one packaged JSON resource.

    Args:
        relative_path: Slash-separated path under ``qa_mcp/resources/data``.
    """
    resource = resources.files(DATA_PACKAGE)
    for part in relative_path.split("/"):
        resource = resource.joinpath(part)
    return json.loads(resource.read_text(encoding="utf-8"))


def _load_directory(relative_path: str) -> list[dict[str, Any]]:
    """Read every JSON file in a packaged directory, ordered by filename."""
    directory = resources.files(DATA_PACKAGE)
    for part in relative_path.split("/"):
        directory = directory.joinpath(part)

    names = sorted(entry.name for entry in directory.iterdir() if entry.name.endswith(".json"))
    return [_load(f"{relative_path}/{name}") for name in names]


def _flatten_example(document: dict[str, Any]) -> dict[str, Any]:
    """Flatten an example document into the shape the resource exposes.

    On disk an example separates ``metadata`` from the ``testcase`` it
    describes. Clients consume a flat record, so the metadata is lifted to the
    top level while ``testcase`` and any correction guidance stay intact.
    """
    metadata = document.get("metadata", {})
    flattened: dict[str, Any] = {"id": document.get("id")}
    flattened.update(metadata)
    for key, value in document.items():
        if key not in ("id", "metadata"):
            flattened[key] = value
    return flattened


def _sorted_examples(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten example documents and order them by id, not by filename."""
    return sorted(
        (_flatten_example(doc) for doc in documents),
        key=lambda example: str(example.get("id", "")),
    )


def get_testcase_standard() -> dict[str, Any]:
    """
    Get the test case standard definition.

    URI: qa://standards/testcase/v1
    """
    return _load("standards/testcase_v1.json")


def get_lint_rules() -> dict[str, Any]:
    """
    Get the lint rules and scoring definition.

    URI: qa://checklists/lint-rules/v1
    """
    return _load("checklists/lint_rules_v1.json")


def get_xray_mapping() -> dict[str, Any]:
    """
    Get the QA-MCP to Xray field mapping.

    URI: qa://mappings/xray/v1
    """
    return _load("mappings/xray_v1.json")


def get_good_examples() -> list[dict[str, Any]]:
    """
    Get exemplary test cases.

    URI: qa://examples/good
    """
    return _sorted_examples(_load_directory("examples/good"))


def get_bad_examples() -> list[dict[str, Any]]:
    """
    Get anti-pattern test cases.

    URI: qa://examples/bad
    """
    return _sorted_examples(_load_directory("examples/bad"))
