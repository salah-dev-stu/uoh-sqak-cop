"""Signed Step-0 declaration assembly (F5) — git hash via the gatekeeper (R3)."""

from __future__ import annotations

from typing import Any

from cipherchase.peer.declaration import build_declaration
from cipherchase.shared.gatekeeper import ApiGatekeeper
from cipherchase.shared.gitinfo import git_commit
from cipherchase.shared.sysinfo import system_info
from cipherchase.shared.version import VERSION


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
