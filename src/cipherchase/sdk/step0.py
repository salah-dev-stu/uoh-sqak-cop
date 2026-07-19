"""Signed Step-0 declaration assembly (F5) — git hash via the gatekeeper (R3)."""

from __future__ import annotations

import subprocess
from typing import Any

from cipherchase.peer.declaration import build_declaration
from cipherchase.shared.gatekeeper import ApiGatekeeper
from cipherchase.shared.sysinfo import system_info
from cipherchase.shared.version import VERSION


def git_commit(gate: ApiGatekeeper) -> str:
    def probe() -> str:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"

    try:
        return gate.execute(probe, service="subprocess", action="git_rev_parse")
    except Exception:
        return "unknown"


def step0(cfg: Any, gate: ApiGatekeeper) -> dict[str, Any]:
    game = cfg.private["game"]
    llm_cfg = cfg.private.get("llm", {})
    return build_declaration(
        team=game["group_id"],
        players=list(game["members"]),
        role=cfg.role,
        git_commit=git_commit(gate),
        llm={
            "provider": cfg.private["trash_talk"]["provider"],
            "model": llm_cfg.get("model", "template"),
            "version": llm_cfg.get("version", "n/a"),
        },
        system=system_info(),
        version=VERSION,
    )
