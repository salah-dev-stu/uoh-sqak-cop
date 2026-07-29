"""Offline log verifier (F3/F4) — the grader's one-command integrity check.

``verify_log`` re-audits any log artifact (ours or an opponent's emailed one)
with the SAME machinery the peers use at end-game: every ``{payload, nonce,
commit}`` is re-hashed (`audit_records`) and the move/barrier sequence is
replayed on the board (`physical_audit`) — so a hash-valid-but-teleporting log
is convicted too. No keys, no network; failures are localised to their record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cipherchase.domain.board import Board
from cipherchase.domain.crypto import audit_records
from cipherchase.domain.physical_audit import physical_audit

_DEFAULT_BOARD = 7


def verify_log(path: str | Path, board_size: int = _DEFAULT_BOARD) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    records = data if isinstance(data, list) else data.get("records", [])
    hashes = audit_records(records)
    physical = physical_audit(records, Board(board_size))
    passed = hashes["passed"] and physical["passed"]
    return {
        "verdict": "Verified OK" if passed else "TAMPERED",
        "records": len(records),
        "failed_indices": hashes["failed_steps"],
        "failed_steps": [records[i]["payload"]["step"] for i in hashes["failed_steps"]],
        "physical_violations": physical["violations"],
    }


def render(report: dict[str, Any]) -> str:
    lines = [f"{report['records']} sealed records re-hashed"]
    for idx, step in zip(report["failed_indices"], report["failed_steps"], strict=True):
        lines.append(f"  commit MISMATCH at record {idx} (step {step})")
    for step in report["physical_violations"]:
        lines.append(f"  hash valid but PHYSICALLY ILLEGAL at step {step} (board convicts)")
    lines.append(report["verdict"] + ("" if report["verdict"] == "Verified OK"
                                      else " — match void 0/0"))
    return "\n".join(lines)
