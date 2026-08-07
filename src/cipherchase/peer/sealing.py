"""Commit-reveal record bookkeeping (FR-F2).

Each peer seals its own moves here — storing ``{payload, nonce, commit}`` — and
reveals the whole book (nonces included) at game end for the mutual audit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.protocol import AuditPayload
from cipherchase.shared.gitinfo import git_commit
from cipherchase.shared.sysinfo import system_info
from cipherchase.shared.version import VERSION


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def trim_words(text: str, max_words: int) -> str:
    return " ".join(text.split()[:max_words])


def sealed_spec_record(book: SealBook, cfg: Any, sub_game_number: int,
                       gate: Any = None) -> None:
    """Step-0 sealed declaration record (F5, PRD_league_runtime §2.2).

    Carries `github_commit` — their spelling, so neither side needs a tolerance.
    Without it the audit trail never pins the code that played, and an opponent
    replaying our records has nothing to check the repo against.
    """
    book.seal({
        "step": 0,
        "type": "system_spec",
        "github_commit": git_commit(gate) if gate else "",
        "spec": system_info(),
        "model": cfg.private.get("llm", {}).get("model", "template"),
        "code_version": VERSION,
        "group_name": cfg.private["game"]["group_name"],
        "sub_game_number": sub_game_number,
    })


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
        self._oob = 0

    def seal(self, payload: dict[str, Any]) -> tuple[str, str]:
        commit, nonce = CommitReveal.seal(payload)
        self._records.append({"payload": payload, "nonce": nonce, "commit": commit})
        return commit, nonce

    def seal_out_of_band(self, payload: dict[str, Any]) -> tuple[str, str]:
        """Seal a non-move record, numbered OUTSIDE the game's step chain.

        A counterparty rebuilding the move chain from step numbers excludes a
        closed set of known types and counts anything unknown as a move — so a
        record type newer than their exclusion list breaks their continuity
        check. Descending negative steps make every non-move record unmistakable
        by NUMBER too, which needs no agreement about types at all.
        """
        self._oob -= 1
        return self.seal({"step": self._oob, **payload})

    def records(self) -> list[dict[str, Any]]:
        return list(self._records)

    def audit_payload(self, sender: str, result_claim: str) -> AuditPayload:
        return AuditPayload(sender=sender, records=self.records(), result_claim=result_claim)
