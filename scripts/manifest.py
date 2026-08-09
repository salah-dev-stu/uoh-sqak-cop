"""Emit a manifest an opponent can actually check against what we send.

Our first manifest hashed the pretty-printed bytes on disk while our mailer
transmitted CANONICAL bytes, so the two never matched and anrbj666 reasonably
read the mismatch as a silent rewrite. It was not — same document, two
serialisations — but a manifest that cannot be reproduced by the receiver is
decoration. Both hashes, both labelled, canonical first because that is the one
that travels.

    uv run python scripts/manifest.py docs/league/<dir> [> MANIFEST.txt]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical_bytes(path: Path) -> bytes:
    """The bytes our mailer transmits: sorted keys, compact separators."""
    document = json.loads(path.read_text())
    return json.dumps(document, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def lines(directory: Path) -> list[str]:
    out = ["canonical sha256   on-disk sha256    | path",
           "(what we transmit) (pretty-printed)  |",
           "-" * 62]
    for path in sorted(directory.glob("*.json")):
        out.append(f"{digest(canonical_bytes(path))}   {digest(path.read_bytes())}  "
                   f"| {path.name}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    directory = Path(argv[1])
    if not directory.is_dir():
        print(f"not a directory: {directory}")
        return 1
    print("\n".join(lines(directory)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
