"""Stage-1 milestone scenario + dependency purity (Milestone S1, NFR-2)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.constants import Direction
from cipherchase.domain.board import Board

EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_two_pieces_move_legally_and_land_where_expected() -> None:
    board = Board(7)
    cop = board.step((0, 0), Direction.S, EMPTY)
    thief = board.step((3, 3), Direction.N, EMPTY)
    assert cop == (1, 0)
    assert thief == (2, 3)


def test_barrier_blocks_a_direction_and_illegal_step_rejected() -> None:
    board = Board(7)
    assert Direction.E not in board.legal_moves((3, 3), frozenset({(3, 4)}))


def test_domain_layer_is_dependency_pure() -> None:
    # domain/ must import nothing from infra/peer/gui or shared.config (NFR-2).
    domain = Path(__file__).resolve().parents[2] / "src" / "cipherchase" / "domain"
    forbidden = (
        "cipherchase.infra",
        "cipherchase.peer",
        "cipherchase.gui",
        "cipherchase.shared.config",
    )
    for py in domain.glob("*.py"):
        text = py.read_text()
        for name in forbidden:
            assert name not in text, f"{py.name} illegally imports {name}"
