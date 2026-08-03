"""Trash-talk providers (FR-D4). The MOVE never comes from here — text only.

``template`` is the default, needs no keys and costs 0 tokens (the grader/test
path). ``claude_cli`` reuses the subscription CLI with the API key stripped.
A missing/failed provider raises ``ProviderUnavailableError`` so the caller falls
back to templates — the game never blocks on the LLM.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

from cipherchase.exceptions import ConfigError, ProviderUnavailableError

# Intent-keyed banks (F6): HONEST taunts vs BLUFF misdirection. The physical
# board stays truthful either way — only the words may lie.
_PHRASES: dict[str, dict[str, list[str]]] = {
    "police": {
        "truth": ["You can't hide forever.", "I'm closing in.", "Nowhere left to run."],
        "lie": ["I've lost your trail completely.", "I'm searching the far corner.", "My barriers are spent."],
    },
    "thief": {
        "truth": ["Catch me if you can!", "Too slow, officer.", "I'm already gone."],
        "lie": ["I'm hiding right behind you.", "Heading north, promise.", "I'm cornered, come get me."],
    },
}


@dataclass
class TalkContext:
    role: str
    step: int
    own_move: str = ""
    intent: str = "truth"
    direction: Any = None          # heading actually taken (grounds truth/lie, F6)
    gap: int = 0                   # believed distance to the opponent
    barriers: int = 0              # barriers placed so far
    landmarks: list[str] = field(default_factory=list)   # setting flavour, from config
    max_words: int = 15            # the agreed hint_max_words


class TemplateProvider:
    """Zero-token hints, but GROUNDED: the composer builds each line from the real
    heading, gap, barriers and the setting's landmarks (F6, book Ch4/6)."""

    def generate(self, ctx: TalkContext) -> str:
        from cipherchase.constants import Direction
        from cipherchase.strategy.hint_writer import HintContext, compose
        if ctx.direction is None:  # no game state (early boot) → static fallback bank
            banks = _PHRASES.get(ctx.role, {"truth": ["..."], "lie": ["..."]})
            phrases = banks.get(ctx.intent, banks["truth"])
            return phrases[ctx.step % len(phrases)]
        return compose(HintContext(
            role=ctx.role, intent=ctx.intent, step=ctx.step,
            direction=ctx.direction if isinstance(ctx.direction, Direction) else Direction.STAY,
            gap=ctx.gap, barriers=ctx.barriers, landmarks=list(ctx.landmarks),
            max_words=ctx.max_words))


class ClaudeCliProvider:
    def __init__(self, binary: str = "claude", timeout: float = 8.0, *, gate: Any) -> None:
        self.binary = binary
        self.timeout = timeout
        self.gate = gate

    def generate(self, ctx: TalkContext) -> str:
        # every external call through the ONE gatekeeper — mandatory (R3)
        return self.gate.execute(lambda: self._run(ctx), service="llm", action="generate")

    def _run(self, ctx: TalkContext) -> str:
        prompt = f"In one short taunt, {ctx.role} reacts (move {ctx.own_move})."
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        try:
            proc = subprocess.run(
                [self.binary, "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise ProviderUnavailableError(f"claude cli: {exc}") from exc
        if proc.returncode != 0:
            raise ProviderUnavailableError(f"claude cli exit {proc.returncode}: {proc.stderr}")
        return str(json.loads(proc.stdout).get("result", "")).strip()


def build_provider(config: dict[str, Any], gate: Any = None) -> Any:
    name = config.get("provider", "template")
    if name == "template":
        return TemplateProvider()
    if name == "claude_cli":
        if gate is None:
            raise ConfigError("claude_cli provider requires the gatekeeper (R3)")
        return ClaudeCliProvider(
            binary=config.get("executable", "claude"),
            timeout=float(config.get("step_deadline_seconds", 8.0)),
            gate=gate,
        )
    raise ProviderUnavailableError(f"provider {name!r} is not available")
