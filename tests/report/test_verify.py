"""`cipherchase verify` — offline re-audit of any log artifact (grader path)."""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.report.verify import verify_log

SAMPLE = sorted(
    (Path(__file__).resolve().parents[2] / "docs/sample-run").glob("log_*police*_g01.json"))[0]


def test_committed_sample_verifies_clean() -> None:
    report = verify_log(SAMPLE)
    assert report["verdict"] == "Verified OK"
    assert report["records"] == 70
    assert report["failed_steps"] == [] and report["physical_violations"] == []


def test_tampered_move_is_localised_to_its_record(tmp_path) -> None:
    log = json.loads(SAMPLE.read_text())
    original = log["records"][12]["payload"]["move"]
    log["records"][12]["payload"]["move"] = "N" if original != "N" else "S"  # guaranteed change
    bad = tmp_path / "log.json"
    bad.write_text(json.dumps(log))
    report = verify_log(bad)
    assert report["verdict"] == "TAMPERED"
    assert report["failed_steps"] == [log["records"][12]["payload"]["step"]]
    assert report["failed_indices"] == [12]


def test_bare_records_list_is_accepted_too(tmp_path) -> None:
    records = json.loads(SAMPLE.read_text())["records"]
    bare = tmp_path / "records.json"
    bare.write_text(json.dumps(records))
    assert verify_log(bare)["verdict"] == "Verified OK"


def test_physically_illegal_but_hash_valid_record_is_caught(tmp_path) -> None:
    # Re-seal a teleport move: the hash verifies, the BOARD convicts (F4/F6).
    from cipherchase.domain.crypto import CommitReveal
    log = json.loads(SAMPLE.read_text())
    rec = log["records"][3]
    rec["payload"]["state"]["pos"] = [0, 0]
    rec["payload"]["move"] = "N"  # off the board from (0,0)
    rec["commit"], rec["nonce"] = CommitReveal.seal(rec["payload"])
    bad = tmp_path / "log.json"
    bad.write_text(json.dumps(log))
    report = verify_log(bad)
    assert report["verdict"] == "TAMPERED"
    assert report["failed_steps"] == []          # every hash still checks out…
    assert 3 in report["physical_violations"]    # …but physics says no
