#!/usr/bin/env python3
"""Set the release version, touching only the places that carry it.

A blanket search-and-replace across these files is how `pydantic>=2.0.0`
silently became `pydantic>=2.1.0` during the 2.1.0 release: the old version
string appears in dependency pins too. This edits one anchored line per file
and fails loudly if an anchor is missing.

    python scripts/bump_version.py 2.1.1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (path, pattern, replacement template) - each pattern must anchor on the
# surrounding syntax, never on the bare version string.
EDITS: list[tuple[str, str, str]] = [
    ("pyproject.toml", r'(?m)^version = "[^"]+"', 'version = "{v}"'),
    ("src/qa_mcp/__init__.py", r'(?m)^__version__ = "[^"]+"', '__version__ = "{v}"'),
    (
        "Dockerfile",
        r'org\.opencontainers\.image\.version="[^"]+"',
        'org.opencontainers.image.version="{v}"',
    ),
    ("docker-compose.yml", r"qa-mcp:\$\{VERSION:-[^}]+\}", "qa-mcp:${{VERSION:-{v}}}"),
    (
        "DOCKERHUB.md",
        r"\| `[\d.]+` \| Current stable release \|",
        "| `{v}` | Current stable release |",
    ),
]

SEMVER = re.compile(r"^\d+\.\d+\.\d+([-.\w]*)$")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not SEMVER.match(argv[1]):
        print(f"usage: {argv[0]} <semver>", file=sys.stderr)
        return 2

    version = argv[1]
    for relative, pattern, template in EDITS:
        path = REPO / relative
        text = path.read_text(encoding="utf-8")
        replacement = template.format(v=version)
        updated, count = re.subn(pattern, replacement, text)
        if count == 0:
            print(f"error: no version anchor found in {relative}", file=sys.stderr)
            return 1
        path.write_text(updated, encoding="utf-8")
        print(f"  {relative}: {count} occurrence(s) -> {version}")

    print(f"\nNow add a [{version}] section to CHANGELOG.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
