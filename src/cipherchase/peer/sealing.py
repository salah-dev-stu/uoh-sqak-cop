"""Commit-reveal record bookkeeping (FR-F2).

Each peer seals its own moves here — storing ``{payload, nonce, commit}`` — and
reveals the whole book (nonces included) at game end for the mutual audit.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.protocol import AuditPayload


def move_payload(step: int, state: Any, decision: Any) -> dict[str, Any]:
    """The committed payload = the mover's OWN observable state (PLAN §8.1)."""
    barriers = sorted([list(cell) for cell in state.barriers])
    return {
        "step": step,
        "state": {"pos": list(state.position), "barriers": barriers},
        "move": decision.direction.value,
        "intent": decision.intent,
    }


class SealBook:
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def seal(self, payload: dict[str, Any]) -> tuple[str, str]:
        commit, nonce = CommitReveal.seal(payload)
        self._records.append({"payload": payload, "nonce": nonce, "commit": commit})
        return commit, nonce

    def records(self) -> list[dict[str, Any]]:
        return list(self._records)

    def audit_payload(self, sender: str, result_claim: str) -> AuditPayload:
        return AuditPayload(sender=sender, records=self.records(), result_claim=result_claim)
