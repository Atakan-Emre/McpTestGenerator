"""Tests for the MCP resource and prompt handlers.

These handlers are invoked by the MCP runtime with SDK types (``AnyUrl`` for
resource URIs), not plain strings. Calling them with a ``str`` from a test does
not exercise the real code path, which is how a total resource outage went
unnoticed.
"""

import json

import pytest
from pydantic import AnyUrl

from qa_mcp.prompts.templates import PROMPT_REGISTRY
from qa_mcp.server import (
    get_prompt,
    list_prompts,
    list_resources,
    read_resource,
)


class TestResources:
    """Resource listing and reading."""

    @pytest.mark.asyncio
    async def test_every_listed_resource_is_readable_via_anyurl(self):
        """Regression: the runtime passes AnyUrl, which never matched the str keys."""
        resources = await list_resources()
        assert resources

        for resource in resources:
            payload = await read_resource(resource.uri)
            assert json.loads(payload), f"{resource.uri} returned empty JSON"

    @pytest.mark.asyncio
    async def test_read_resource_accepts_plain_string(self):
        """String URIs stay supported for direct/library callers."""
        payload = json.loads(await read_resource("qa://standards/testcase/v1"))
        assert payload["name"] == "QA-MCP Test Case Standard"

    @pytest.mark.asyncio
    async def test_read_resource_tolerates_trailing_slash(self):
        """URL normalization may append a slash to authority-only URIs."""
        payload = json.loads(await read_resource(AnyUrl("qa://examples/good/")))
        assert payload

    @pytest.mark.asyncio
    async def test_unknown_resource_raises(self):
        with pytest.raises(ValueError, match="Unknown resource"):
            await read_resource("qa://does/not/exist")

    @pytest.mark.asyncio
    async def test_bad_examples_expose_a_testcase_payload(self):
        """`qa://examples/bad` must carry lintable test cases, not just prose."""
        examples = json.loads(await read_resource("qa://examples/bad"))
        assert examples
        for example in examples:
            assert "testcase" in example
            assert "problems" in example


class TestPrompts:
    """Prompt listing and rendering."""

    @pytest.mark.asyncio
    async def test_all_registered_prompts_are_listed(self):
        prompts = await list_prompts()
        assert {p.name for p in prompts} == set(PROMPT_REGISTRY)
        assert all(p.description for p in prompts)

    @pytest.mark.asyncio
    async def test_every_prompt_renders_without_arguments(self):
        for name in PROMPT_REGISTRY:
            result = await get_prompt(name, None)
            assert result.messages
            assert result.messages[0].content.text.strip()

    @pytest.mark.asyncio
    async def test_create_manual_test_prompt_embeds_arguments(self):
        result = await get_prompt(
            "create-manual-test",
            {
                "feature": "Şifre Sıfırlama",
                "acceptance_criteria": json.dumps(["Kullanıcı e-posta ile link alır"]),
            },
        )
        text = result.messages[0].content.text
        assert "Şifre Sıfırlama" in text
        assert "Kullanıcı e-posta ile link alır" in text

    @pytest.mark.asyncio
    async def test_prompt_argument_that_is_not_json_is_tolerated(self):
        """Clients send plain strings; a JSONDecodeError must not surface."""
        result = await get_prompt(
            "create-manual-test",
            {"feature": "Login", "acceptance_criteria": "tek kriter, json değil"},
        )
        assert "tek kriter, json değil" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_unknown_prompt_raises(self):
        with pytest.raises(ValueError, match="Unknown prompt"):
            await get_prompt("no-such-prompt", None)


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
