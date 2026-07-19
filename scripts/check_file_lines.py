#!/usr/bin/env python3
"""Fail if any source file (.py, arena .js/.mjs, index.html) exceeds 150 lines (R8).

The user enforces BOTH counts (HW5 lesson), so this checks each file twice:
  * raw     = total physical lines (``wc -l``)
  * logical = non-blank, non-pure-comment lines (docstrings count as source)

Run from the repo root: ``python scripts/check_file_lines.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

LIMIT = 150
TARGETS = (Path("src/cipherchase"), Path("tests"), Path("scripts"), Path("analysis"))
VIZ = (Path("viz/js"), Path("viz/test"))


def counts(path: Path) -> tuple[int, int]:
    raw = 0
    logical = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        raw += 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        logical += 1
    return raw, logical


def main() -> int:
    violations: list[str] = []
    checked: list[Path] = []
    for target in TARGETS:
        checked.extend(sorted(target.rglob("*.py")))
    for target in VIZ:
        checked.extend(sorted(target.rglob("*.js")) + sorted(target.rglob("*.mjs")))
    checked.append(Path("viz/index.html"))
    for path in checked:
        raw, logical = counts(path)
        if raw > LIMIT or logical > LIMIT:
            violations.append(f"  {path}: raw={raw} logical={logical}")
    if violations:
        print(f"FAIL: {len(violations)} file(s) exceed {LIMIT} lines (raw or logical):")
        print("\n".join(violations))
        return 1
    print(f"OK: all .py files within {LIMIT} lines (raw AND logical).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
