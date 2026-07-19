"""Doc-truth guard (IC-16/T463): every documented CLI command actually parses."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from cipherchase.cli import _parser

ROOT = Path(__file__).resolve().parents[2]
DOCS = ("README.md", "docs/deploy-tunnel.md")
_CLI = re.compile(r"(?:uv run )?cipherchase\s+(.+)")


def _documented_commands():
    """Yield (doc, argv, is_future) for each `cipherchase …` line inside a code fence."""
    for doc in DOCS:
        in_fence = False
        for line in (ROOT / doc).read_text().splitlines():
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            match = _CLI.match(line.strip()) if in_fence else None
            if not match:
                continue
            raw = match.group(1)
            future = "future" in raw.split("#", 1)[1] if "#" in raw else False
            tail = raw.split("#", 1)[0].strip()
            yield doc, shlex.split(tail), future


def test_every_documented_cli_command_parses_or_is_marked_future() -> None:
    checked = 0
    for doc, argv, future in _documented_commands():
        checked += 1
        if future:
            continue  # explicitly deferred — exempt, but still counted
        try:
            _parser().parse_args(argv)
        except SystemExit:
            pytest.fail(f"documented CLI does not parse: `cipherchase {' '.join(argv)}` in {doc}")
    assert checked >= 3  # the quick-start + deploy commands are all covered
