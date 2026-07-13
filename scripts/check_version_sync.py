#!/usr/bin/env python3
"""Fail if any config ``version`` drifts from ``shared/version.py`` (NFR-6 / R6).

Single-source rule: the package ``__version__`` and every ``config/*/game.toml``
``version`` field must be byte-identical. Missing config is tolerated (nothing
to sync yet); a present-but-mismatched field fails.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.shared.version import VERSION  # noqa: E402


def main() -> int:
    violations: list[str] = []
    for toml_path in sorted(Path("config").rglob("game.toml")):
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        found = str(data.get("version", "")).strip()
        if found and found != VERSION:
            violations.append(f"  {toml_path}: version={found!r} != {VERSION!r}")
    if violations:
        print(f"FAIL: {len(violations)} config version(s) drifted from {VERSION!r}:")
        print("\n".join(violations))
        return 1
    print(f"OK: all config versions match {VERSION!r}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
