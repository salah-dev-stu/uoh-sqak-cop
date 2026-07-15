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
from dataclasses import dataclass
from typing import Any

from cipherchase.exceptions import ProviderUnavailableError

_PHRASES = {
    "police": ["You can't hide forever.", "I'm closing in.", "Nowhere left to run."],
    "thief": ["Catch me if you can!", "Too slow, officer.", "I'm already gone."],
}


@dataclass
class TalkContext:
    role: str
    step: int
    own_move: str = ""
    intent: str = "truth"


class TemplateProvider:
    """Pure-Python canned phrases — deterministic, zero tokens."""

    def generate(self, ctx: TalkContext) -> str:
        phrases = _PHRASES.get(ctx.role, ["..."])
        return phrases[ctx.step % len(phrases)]


class ClaudeCliProvider:
    def __init__(self, binary: str = "claude", timeout: float = 8.0) -> None:
        self.binary = binary
        self.timeout = timeout

    def generate(self, ctx: TalkContext) -> str:
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


def build_provider(config: dict[str, Any]) -> Any:
    name = config.get("provider", "template")
    if name == "template":
        return TemplateProvider()
    if name == "claude_cli":
        return ClaudeCliProvider(binary=config.get("executable", "claude"))
    raise ProviderUnavailableError(f"provider {name!r} is not available")
