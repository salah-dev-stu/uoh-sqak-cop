"""The manifest must quote the bytes that actually travel (anrbj666, fix #3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from manifest import canonical_bytes, digest, lines  # noqa: E402


def test_the_canonical_hash_is_the_one_the_opponent_computes(tmp_path) -> None:
    # anrbj666 hashed 02e82563.. from the file we mailed; our manifest quoted
    # 84c73118.. from the file on disk. Same document, two serialisations —
    # and no way for them to tell that from a manifest carrying only one.
    path = tmp_path / "result_x.json"
    path.write_text(json.dumps({"b": 2, "a": 1}, indent=2))  # pretty, unsorted
    theirs = digest(json.dumps({"a": 1, "b": 2}, sort_keys=True,
                               ensure_ascii=False, separators=(",", ":")).encode())
    assert digest(canonical_bytes(path)) == theirs
    assert digest(path.read_bytes()) != theirs  # the mismatch that started it


def test_both_hashes_appear_labelled(tmp_path) -> None:
    (tmp_path / "result_x.json").write_text('{"a": 1}')
    out = "\n".join(lines(tmp_path))
    assert "canonical" in out and "on-disk" in out and "result_x.json" in out
