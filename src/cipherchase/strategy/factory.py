"""Resolve a brain from a ``package.module:Class`` config spec (FR-C4).

The student seam: swapping ``police_class``/``thief_class`` in ``game.toml``
picks a different brain with zero engine changes (heuristic, expectimax, RL…).
"""

from __future__ import annotations

import importlib
from typing import Any

from cipherchase.domain.board import Board
from cipherchase.domain.brains import BrainBase
from cipherchase.exceptions import ConfigError


def load_brain(
    spec: str, board: Board, params: dict[str, Any] | None = None, rng: Any = None
) -> BrainBase:
    try:
        module_name, class_name = spec.split(":")
        module = importlib.import_module(module_name)
        brain_cls = getattr(module, class_name)
    except (ValueError, ModuleNotFoundError, AttributeError) as exc:
        raise ConfigError(f"bad brain spec {spec!r}: {exc}") from exc
    return brain_cls(board, params, rng)
