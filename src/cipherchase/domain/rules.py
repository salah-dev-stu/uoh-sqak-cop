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


def is_enclosed(board: Board, thief: Cell, barriers: frozenset[Cell]) -> bool:
    """Rules 46/47 — barrier on the thief's OWN cell, or no legal move at all.

    Cop-free by construction: enclosure is a property of the thief's hidden cell,
    so it is a fact only the THIEF can observe. That is why a conforming thief
    must announce it (``claim_response.caught``) instead of settling silently —
    an unannounced enclosure forks the game into capture-vs-timeout, which is
    the contradictory-report shape rule 35 scores 0/0 for BOTH teams.
    """
    return thief in barriers or not board.neighbors(thief, barriers)


def is_capture(
    board: Board,
    cop: Cell,
    thief: Cell,
    barriers: frozenset[Cell],
) -> bool:
    """Co-location (cop claims the thief's cell) or a rules-46/47 enclosure.

    No cop-adjacency condition: the book makes the three capture families equal
    in standing, so a thief walled in from across the board is caught just the
    same. Requiring adjacency here would let us score SURVIVAL on a sub-game the
    opponent scores CAPTURE — two honest reports contradicting, which is 0/0.
    """
    return cop == thief or is_enclosed(board, thief, barriers)


def outcome(
    board: Board,
    cop: Cell,
    thief: Cell,
    barriers: frozenset[Cell],
    turn: int,
    *,
    survival_threshold: int,
) -> Outcome | None:
    """CAPTURE if caught, SURVIVAL at the threshold, else None (game continues)."""
    if is_capture(board, cop, thief, barriers):
        return Outcome.CAPTURE
    if turn >= survival_threshold:
        return Outcome.SURVIVAL
    return None
