"""Tests for the packaged resource data.

The MCP-facing behaviour of resources and prompts is covered in
test_mcp_protocol.py against the runtime's own API. What remains here is the
data itself: that it ships inside the package, is ordered predictably, and
agrees with the lint engine.
"""


class TestPackagedResourceData:
    """Resource content is packaged JSON, not a hand-maintained Python copy."""

    def test_data_files_resolve_from_the_installed_package(self):
        """Regression: the data lived in a repo-level directory that nothing read
        and that an installed wheel could not reach."""
        from importlib import resources

        data = resources.files("qa_mcp.resources.data")
        for relative in (
            "standards/testcase_v1.json",
            "checklists/lint_rules_v1.json",
            "mappings/xray_v1.json",
        ):
            node = data
            for part in relative.split("/"):
                node = node.joinpath(part)
            assert node.is_file(), f"{relative} is not packaged"

    def test_examples_are_ordered_by_id(self):
        from qa_mcp.resources.standards import get_bad_examples, get_good_examples

        for loader in (get_good_examples, get_bad_examples):
            ids = [example["id"] for example in loader()]
            assert ids == sorted(ids), ids

    def test_every_example_carries_metadata_and_a_testcase(self):
        from qa_mcp.resources.standards import get_bad_examples, get_good_examples

        for example in get_good_examples():
            assert example["testcase"] and example["why_good"] and example["name"]
        for example in get_bad_examples():
            assert example["testcase"] and example["problems"] and example["name"]

    def test_every_penalising_lint_rule_is_documented(self):
        """The lint-rules resource must describe what the engine actually does."""
        import re
        from pathlib import Path

        from qa_mcp.resources.standards import get_lint_rules

        engine_source = (
            Path(__file__).resolve().parent.parent / "src/qa_mcp/core/lint.py"
        ).read_text(encoding="utf-8")
        emitted = set(re.findall(r'rule="([^"]+)"', engine_source))
        documented = {rule["id"]: rule for rule in get_lint_rules()["rules"]}

        undocumented = emitted - set(documented)
        assert not undocumented, f"lint rules missing from the resource: {sorted(undocumented)}"

        # A documented rule that carries a penalty must be one the engine raises
        # as an issue; suggestion-only rules are documented with penalty 0.
        penalising = {rule_id for rule_id, r in documented.items() if r.get("penalty", 0) > 0}
        assert penalising <= emitted, (
            f"documented but never emitted: {sorted(penalising - emitted)}"
        )
