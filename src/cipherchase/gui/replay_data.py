"""Replay Viewer verification (FR-G5, F12).

Re-hashes each logged step with the SAME ``CommitReveal.verify`` the peers used
(never a re-implementation). A clean step is "Verified OK" (green); any mismatch
is "TAMPERED" (red) — instant void.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.crypto import CommitReveal
from cipherchase.exceptions import CryptoError

OK = "Verified OK"
BAD = "TAMPERED"


def verify_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verdicts: list[dict[str, Any]] = []
    for record in records:
        step = record.get("payload", {}).get("step")
        try:
            CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
            verdicts.append({"step": step, "status": OK})
        except (CryptoError, KeyError):
            verdicts.append({"step": step, "status": BAD})
    return verdicts


def replay_verdict(records: list[dict[str, Any]]) -> str:
    return OK if all(v["status"] == OK for v in verify_records(records)) else BAD
