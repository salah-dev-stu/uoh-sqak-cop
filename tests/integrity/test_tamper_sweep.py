"""Exhaustive tamper sweep (IC-1..6): every single-field mutation of the real
committed log is caught and localised — 1795 mutations, 0 escapes."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cipherchase.domain.crypto import audit_records
from cipherchase.gui.replay_data import BAD, replay_verdict, verify_records
from integrity.mutations import mutations_of


def _class_of(label: str) -> str:
    for cls in ("step", "pos", "commit"):
        if label.startswith(cls):
            return cls
    return label  # move / intent / barriers / nonce are their own class

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "docs/sample-run/log_uoh-sqak-police-c64efc39_g01.json"
RECORDS = json.loads(LOG.read_text())["records"]


def _expected_n(records) -> int:
    return len(records) * 10 + sum(len(set(r["commit"])) for r in records)


def test_pristine_log_passes_so_the_sweep_proves_discrimination() -> None:
    verdict = audit_records([dict(r) for r in RECORDS])
    assert verdict["passed"] is True and verdict["failed_steps"] == []


def test_generator_yields_ten_plus_di_unique_single_field_mutations() -> None:
    per_record: dict[int, list[str]] = {}
    for label, idx, mutated in mutations_of(RECORDS):
        per_record.setdefault(idx, []).append(label)
        diffs = [j for j, (a, b) in enumerate(zip(RECORDS, mutated, strict=True)) if a != b]
        assert diffs == [idx]  # exactly one record differs from pristine
    for idx, labels in per_record.items():
        d_i = len(set(RECORDS[idx]["commit"]))
        assert len(labels) == 10 + d_i  # 9 payload + 1 nonce + D_i commit (matches N=R·10+ΣD_i)
        assert len(set(labels)) == len(labels)  # labels unique within a record


def test_every_mutation_is_caught_and_localised_zero_escapes() -> None:
    total = _expected_n(RECORDS)
    assert total >= 500  # PLAN P8 floor — survives a shorter regenerated log
    caught, escapes = 0, []
    for label, idx, mutated in mutations_of(RECORDS):
        verdict = audit_records(mutated)
        if verdict["passed"] or idx not in verdict["failed_steps"]:
            escapes.append((label, idx))
        else:
            caught += 1
    assert not escapes, f"tamper escapes: {escapes[:5]} (+{len(escapes) - 5} more)"
    assert caught == total, f"tamper sweep: {caught}/{total} mutations caught"


def test_replay_viewer_verdict_path_discriminates_too() -> None:
    # IC-5: first mutation of each of the 7 classes per record (7·R sample) must
    # read TAMPERED at the mutated step through the GUI verifier, verdict BAD.
    seen: set[tuple[int, str]] = set()
    checked = 0
    for label, idx, mutated in mutations_of(RECORDS):
        key = (idx, _class_of(label))
        if key in seen:
            continue
        seen.add(key)
        verdicts = verify_records(mutated)
        assert verdicts[idx]["status"] == BAD
        assert replay_verdict(mutated) == BAD
        checked += 1
    assert checked == len(RECORDS) * 7  # exactly 7 classes per record


def test_readme_states_the_exact_sweep_count() -> None:
    n = _expected_n(RECORDS)
    text = (ROOT / "README.md").read_text()
    m = re.search(r"(\d+) mutations, (\d+) caught", text)
    assert m, "README must carry the '<N> mutations, <N> caught' honesty line"
    assert int(m.group(1)) == int(m.group(2)) == n
