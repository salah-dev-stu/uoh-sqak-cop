"""Move / barrier / capture adjudication (FR-A2/A3/A4). Pure; config injected."""

from __future__ import annotations

from cipherchase.constants import Cell, Direction, Outcome
from cipherchase.domain.board import Board
from cipherchase.exceptions import IllegalBarrierError, IllegalMoveError


def is_legal_move(board: Board, cell: Cell, direction: Direction, barriers: frozenset[Cell]) -> bool:
    try:
        board.step(cell, direction, barriers)
    except IllegalMoveError:
        return False
    return True


def validate_move(board: Board, cell: Cell, direction: Direction, barriers: frozenset[Cell]) -> Cell:
    return board.step(cell, direction, barriers)


def can_place_barrier(
    board: Board, cop: Cell, target: Cell, barriers: frozenset[Cell], max_barriers: int
) -> bool:
    return (
        len(barriers) < max_barriers
        and board.in_bounds(target)
        and target not in barriers
        and board.distance(cop, target) == 1
    )


def validate_barrier(
    board: Board, cop: Cell, target: Cell, barriers: frozenset[Cell], max_barriers: int
) -> Cell:
    if not can_place_barrier(board, cop, target, barriers, max_barriers):
        raise IllegalBarrierError(f"cannot place barrier at {target} from {cop}")
    return target


def reachable_cells(board: Board, start: Cell, barriers: frozenset[Cell]) -> frozenset[Cell]:
    """BFS closure of cells reachable from ``start`` without crossing a barrier."""
    seen: set[Cell] = {start}
    frontier = [start]
    while frontier:
        cell = frontier.pop()
        for nb in board.neighbors(cell, barriers):
            if nb not in seen:
                seen.add(nb)
                frontier.append(nb)
    return frozenset(seen)


def is_boxed_in(board: Board, thief: Cell, cop: Cell, barriers: frozenset[Cell]) -> bool:
    """True when the thief has no escape cell (all neighbours blocked/cop)."""
    escapes = [c for c in board.neighbors(thief, barriers) if c != cop]
    return not escapes


def is_capture(
    board: Board,
    cop: Cell,
    thief: Cell,
    barriers: frozenset[Cell],
    *,
    require_cop_adjacent: bool = True,
) -> bool:
    """Co-location, barrier-on-thief, or a boxed-in thief (cop adjacent if required)."""
    if cop == thief or thief in barriers:
        return True
    if is_boxed_in(board, thief, cop, barriers):
        return not require_cop_adjacent or board.distance(cop, thief) == 1
    return False


def outcome(
    board: Board,
    cop: Cell,
    thief: Cell,
    barriers: frozenset[Cell],
    turn: int,
    *,
    survival_threshold: int,
    require_cop_adjacent: bool = True,
) -> Outcome | None:
    """CAPTURE if caught, SURVIVAL at the threshold, else None (game continues)."""
    if is_capture(board, cop, thief, barriers, require_cop_adjacent=require_cop_adjacent):
        return Outcome.CAPTURE
    if turn >= survival_threshold:
        return Outcome.SURVIVAL
    return None
