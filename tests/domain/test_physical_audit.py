"""Physical-claim audit (FR-F3, F4/F6) — the board may never lie.

Hash-audit catches a *changed* move; this catches a move that is *illegal* on
the board it was committed against (off-board / through a barrier).
"""

from __future__ import annotations

from pathlib import Path

from cipherchase.domain.board import Board
from cipherchase.domain.physical_audit import move_violations, physical_audit
from cipherchase.peer.sealing import SealBook
from cipherchase.sdk.game_loop import run_game
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
BOARD = Board(7)


def _record(pos, move, barriers) -> dict:
    book = SealBook()
    book.seal({"step": 1, "state": {"pos": list(pos), "barriers": [list(b) for b in barriers]}, "move": move, "intent": "truth"})
    return book.records()[0]


def test_a_real_self_match_log_is_physically_clean() -> None:
    result = run_game(ConfigManager.load(CONFIG / "police"))
    assert physical_audit(result.records, BOARD)["passed"] is True


def test_off_board_move_is_a_violation() -> None:
    records = [_record((0, 0), "N", [])]  # N from row 0 leaves the board
    assert move_violations(records, BOARD) == [0]


def test_move_through_own_barrier_is_a_violation() -> None:
    records = [_record((3, 3), "E", [(3, 4)])]  # steps into a declared barrier
    assert physical_audit(records, BOARD)["passed"] is False


def test_malformed_record_is_flagged_not_crashed() -> None:
    assert move_violations([{"payload": {"move": "N"}}], BOARD) == [0]


def test_typed_non_move_records_are_exempt_from_board_replay() -> None:
    # Live books carry sealed NON-move records (step-0 spec, control channel).
    # They have no state/move — the board must not convict what it cannot replay.
    from cipherchase.domain.board import Board
    from cipherchase.domain.crypto import CommitReveal
    from cipherchase.domain.physical_audit import physical_audit
    spec = {"step": 0, "type": "system_spec", "model": "template"}
    control = {"step": 3, "type": "control", "kind": "status", "status": "PLAYING"}
    move = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "S", "intent": "truth"}
    records = []
    for payload in (spec, move, control):
        commit, nonce = CommitReveal.seal(payload)
        records.append({"payload": payload, "nonce": nonce, "commit": commit})
    verdict = physical_audit(records, Board(7))
    assert verdict["passed"] is True and verdict["violations"] == []
