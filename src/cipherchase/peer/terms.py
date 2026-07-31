"""Terms + identity for the negotiation handshake (PRD_league_runtime §2.1).

``terms`` is the value-equal contract both peers must hold (sourced from the
agreed ``game.json``, emitted with the REFERENCE key names); ``identity`` is
exchanged but never compared — it feeds the Step-0 declaration (F5).
"""

from __future__ import annotations

from typing import Any

from cipherchase.exceptions import ConfigError
from cipherchase.shared.sysinfo import system_info


def terms_from_config(cfg: Any) -> dict[str, Any]:
    ba = cfg.shared["board_and_agents"]
    mb = cfg.shared["movement_and_barriers"]
    ph = cfg.shared["pheromones"]
    world = cfg.shared["world"]
    return {
        "board_size": ba["board_size"],
        "smell_grid_size": ph["grid_size"],
        "decay_per_step": ph["decay"],
        "emit_intensity": ph["center_intensity"],
        "min_center_intensity": ph["min_center_intensity"],
        "max_steps": mb["survival_threshold"],
        "barriers_max": mb["max_barriers"],
        "setting": world["map_area"],
        "hint_max_words": world["hint_max_words"],
        "axis_origin_corner": ba["axis_origin_corner"],
        "axis_start_index": ba["axis_start_index"],
        "thief_start": list(ba["thief_start"]),
        "cop_start": list(ba["cop_start"]),
        "num_games": cfg.shared["network_and_league"]["num_games"],
    }


def validate_terms(cfg: Any) -> dict[str, Any]:
    """Fail fast (before opening a port) if any required term is missing."""
    try:
        return terms_from_config(cfg)
    except KeyError as exc:
        raise ConfigError(f"game.json is missing a required term source: {exc}") from exc


def identity_from_config(cfg: Any) -> dict[str, Any]:
    game = cfg.private["game"]
    net = cfg.network
    # rule 49 (najamjad warm-up finding): the declaration must advertise the
    # PUBLIC tunnel URL when one is configured — never a localhost address.
    url = net.get("public_url") or f"http://{net['host']}:{net['my_port']}/mcp"
    return {
        "group_id": game["group_id"],
        "group_name": game["group_name"],
        "members": list(game["members"]),
        "repos": dict(game.get("repos", {})),
        "mcp_servers": {cfg.role: url},
        "llm_model": cfg.private.get("llm", {}).get("model", "template"),
        "spec": system_info(),
    }
