"""P2P wire contract (FR-B2). Three dataclasses share one serialise mixin (R2).

On the wire, scent is an intensity field (``"row,col" -> float``) — never the
opponent's coordinates (F7). ``move``/``intent`` are the revealed values; the
nonce is NOT here (it stays hidden until the end-of-game audit).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


class _WireMixin:
    """``to_dict``/``from_dict`` for any dataclass; ignores unknown wire keys."""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)  # type: ignore[call-overload]

    @classmethod
    def from_dict(cls, data: dict[str, Any]):  # type: ignore[no-untyped-def]
        names = {f.name for f in dataclasses.fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class TurnMessage(_WireMixin):
    step: int
    sender: str
    commit: str = ""
    hint: str = ""
    intent: str = "truth"
    move: str | None = None
    smell_grid: dict[str, float] = field(default_factory=dict)
    timestamp: str = ""
    barrier_placed: list[int] | None = None
    capture_claim: list[int] | None = None
    claim_response: dict[str, Any] | None = None
    win_claim: dict[str, Any] | None = None


@dataclass
class ControlMessage(_WireMixin):
    kind: str
    sender: str
    sub_game_number: int = 1
    status: str = ""
    step_budget: float = 0.0
    payload: dict[str, Any] | None = None


@dataclass
class AuditPayload(_WireMixin):
    sender: str
    records: list[dict[str, Any]] = field(default_factory=list)
    result_claim: str = ""
