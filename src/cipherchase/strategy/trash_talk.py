"""Bluff-text orchestration (FR-D2/D3/D4) — pure, provider injected.

The hint MAY lie (``intent`` = ``truth``/``lie``); the physical board never
does (enforced by crypto/rules, not here). Talking is throttled to
``every_n_steps`` to save tokens, and any provider failure falls back to the
template so the move is never blocked.
"""

from __future__ import annotations

import random
from typing import Any

from cipherchase.exceptions import ProviderUnavailableError


class TrashTalk:
    def __init__(
        self,
        provider: Any,
        fallback: Any,
        *,
        every_n_steps: int = 3,
        lie_probability: float = 0.4,
        rng: Any = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback
        self.every_n_steps = every_n_steps
        self.lie_probability = lie_probability
        self.rng = rng or random.Random()

    def choose_intent(self) -> str:
        return "lie" if self.rng.random() < self.lie_probability else "truth"

    def maybe_generate(self, ctx: Any) -> str:
        if self.every_n_steps <= 0 or ctx.step % self.every_n_steps != 0:
            return ""
        try:
            return self.provider.generate(ctx)
        except ProviderUnavailableError:
            return self.fallback.generate(ctx)
