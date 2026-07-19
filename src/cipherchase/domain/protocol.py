"""P2P wire contract — reference-exact key sets (PRD_league_runtime §2.4).

One sealed ``TurnMessage`` per turn: the plaintext move/intent are NEVER on the
wire — they live only inside the sealed commit payload, revealed at audit.
``from_dict`` is lenient (filters unknown foreign keys, never crashes);
``to_dict`` emits exactly the reference key set so strict parsers never crash.
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
    hint: str = ""
    smell_grid: dict[str, float] = field(default_factory=dict)
    commit: str = ""
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
