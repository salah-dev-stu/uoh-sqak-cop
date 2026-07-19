"""Deterministic single-field mutations of a sealed log (IC-2).

Pure function of the log bytes — no randomness. For each record, in a fixed
order, yields deep copies of the full record list with EXACTLY one field
perturbed so its canonical bytes always change: step ±1, next move, toggled
intent, each pos coord ±1, barriers reordered/extended, one nonce nibble, and
one mutation per distinct hex-digit value in the commit.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator

_MOVES = ("N", "S", "E", "W", "STAY")


def _next_move(move: str) -> str:
    return _MOVES[(_MOVES.index(move) + 1) % len(_MOVES)] if move in _MOVES else _MOVES[0]


def _bump(ch: str) -> str:
    return format((int(ch, 16) + 1) % 16, "x")


def _mut(records: list[dict], idx: int, label: str, *, payload=None, nonce=None,
         commit=None) -> tuple[str, int, list[dict]]:
    out = copy.deepcopy(records)
    if payload is not None:
        out[idx]["payload"] = payload
    if nonce is not None:
        out[idx]["nonce"] = nonce
    if commit is not None:
        out[idx]["commit"] = commit
    return (label, idx, out)


def _with_state(payload: dict, **state) -> dict:
    return {**payload, "state": {**payload["state"], **state}}


def mutations_of(records: list[dict]) -> Iterator[tuple[str, int, list[dict]]]:
    for i, rec in enumerate(records):
        p = rec["payload"]
        for delta, label in ((1, "step+1"), (-1, "step-1")):
            yield _mut(records, i, label, payload={**p, "step": p["step"] + delta})
        yield _mut(records, i, "move", payload={**p, "move": _next_move(p["move"])})
        yield _mut(records, i, "intent",
                   payload={**p, "intent": "lie" if p["intent"] == "truth" else "truth"})
        pos = p["state"]["pos"]
        for k, delta, label in ((0, 1, "pos0+1"), (0, -1, "pos0-1"),
                                (1, 1, "pos1+1"), (1, -1, "pos1-1")):
            new_pos = list(pos)
            new_pos[k] += delta
            yield _mut(records, i, label, payload=_with_state(p, pos=new_pos))
        bars = p["state"]["barriers"]
        new_bars = list(reversed(bars)) if len(bars) >= 2 else [*bars, [9, 9]]
        yield _mut(records, i, "barriers", payload=_with_state(p, barriers=new_bars))
        n, j = rec["nonce"], i % 32
        yield _mut(records, i, "nonce", nonce=n[:j] + _bump(n[j]) + n[j + 1:])
        c = rec["commit"]
        for value in sorted(set(c)):
            k = c.index(value)
            yield _mut(records, i, f"commit[{value}]", commit=c[:k] + _bump(value) + c[k + 1:])
