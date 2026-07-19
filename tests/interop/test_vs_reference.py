"""THE interop proof: a full live series vs the ACTUAL reference peer (F1/F14).

Two real processes over localhost MCP — ours (`cipherchase peer`) against the
lecturer's `police_thief` — value-aligned terms, roles swapping, both audits
verified. Heavy: runs only with CIPHERCHASE_INTEROP=1 and the reference repo
present.  Run:  CIPHERCHASE_INTEROP=1 uv run pytest tests/interop/test_vs_reference.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT.parent / "reference-repo"
pytestmark = pytest.mark.skipif(
    os.environ.get("CIPHERCHASE_INTEROP") != "1" or not REFERENCE.exists(),
    reason="set CIPHERCHASE_INTEROP=1 with the reference repo present",
)

MAX_STEPS, NUM_GAMES = 12, 2
SHARED = {  # ONE source of truth, rendered into both schemas
    "board": 7, "smell": 5, "decay": 0.1, "emit": 0.9, "min_center": 0.5,
    "setting": "New York", "hint_words": 15, "thief_start": [3, 3], "cop_start": [0, 0],
}


def _our_config(base: Path, role: str, my_port: int, opp_port: int) -> Path:
    src = ROOT / "config" / role
    out = base / f"ours-{role}"
    out.mkdir()
    game = json.loads((src / "game.json").read_text())
    game["board_and_agents"].update(board_size=SHARED["board"], thief_start=SHARED["thief_start"],
                                    cop_start=SHARED["cop_start"], axis_origin_corner="top-left")
    game["world"] = {"map_area": SHARED["setting"], "hint_max_words": SHARED["hint_words"]}
    game["pheromones"].update(grid_size=SHARED["smell"], center_intensity=SHARED["emit"],
                              decay=SHARED["decay"], min_center_intensity=SHARED["min_center"])
    game["movement_and_barriers"].update(survival_threshold=MAX_STEPS, max_moves=MAX_STEPS)
    game["network_and_league"]["num_games"] = NUM_GAMES
    (out / "game.json").write_text(json.dumps(game))
    toml = (src / "game.toml").read_text()
    toml = toml.replace(f"my_port = {8001 if role == 'police' else 8002}", f"my_port = {my_port}")
    toml = toml.replace('opponent_url = "http://127.0.0.1:'
                        f'{8002 if role == "police" else 8001}/mcp"',
                        f'opponent_url = "http://127.0.0.1:{opp_port}/mcp"')
    toml = toml.replace("turn_timeout_seconds = 180", "turn_timeout_seconds = 90")
    (out / "game.toml").write_text(toml)
    (out / "rate_limits.json").write_bytes((src / "rate_limits.json").read_bytes())
    return out


def _ref_config(base: Path, role: str, my_port: int, opp_port: int) -> Path:
    out = base / f"ref-{role}"
    out.mkdir()
    (out / "game.json").write_text(json.dumps({
        "schema_version": "1.3",
        "board_and_agents": {"grid_size": SHARED["board"], "num_agents": 2,
                             "thief_start": SHARED["thief_start"], "cop_start": SHARED["cop_start"],
                             "axis_origin_corner": "top-left", "axis_start_index": 0},
        "world": {"map_area": SHARED["setting"], "hint_max_words": SHARED["hint_words"]},
        "movement_and_barriers": {"move_set": ["N", "S", "E", "W", "STAY"], "max_barriers": 14,
                                  "max_moves": MAX_STEPS, "survival_threshold": MAX_STEPS},
        "scoring": {"capture_cop": 20, "capture_thief": 5, "survival_cop": 5,
                    "survival_thief": 10, "tie_score": 2, "technical_loss": 0},
        "pheromones": {"pheromone_center_intensity": SHARED["emit"],
                       "pheromone_decay": SHARED["decay"],
                       "pheromone_grid_size": SHARED["smell"],
                       "pheromone_min_center_intensity": SHARED["min_center"]},
        "network_and_league": {"num_games": NUM_GAMES},
    }))
    (out / "game.toml").write_text(f"""version = "1.10"
[game]
group_name = "Reference"
group_id = "uoh-reference"
members = ["ref-1"]
repos = {{ cop = "https://example.com/c", thief = "https://example.com/t" }}
mcp_servers = {{ cop = "http://127.0.0.1:{my_port}/mcp", thief = "http://127.0.0.1:{my_port}/mcp" }}
[paths]
logs_dir = "logs"
log_filename = "{role}_match.json"
[play]
step_speed_seconds = 0.0
seed = 1234
[network]
my_port = {my_port}
opponent_url = "http://127.0.0.1:{opp_port}/mcp"
turn_timeout_seconds = 90
poll_interval_seconds = 0.2
[llm]
provider = "claude"
model = "stub"
[email]
enabled = false
""")
    ref_limits = REFERENCE / "config" / "police" / "rate_limits.json"
    (out / "rate_limits.json").write_bytes(ref_limits.read_bytes())
    return out


@pytest.mark.parametrize(("our_role", "ports"), [("thief", (8991, 8992)), ("police", (8995, 8996))])
def test_full_series_vs_the_reference_peer(tmp_path: Path, our_role: str, ports: tuple) -> None:
    ref_role = "police" if our_role == "thief" else "thief"
    ours = _our_config(tmp_path, our_role, ports[0], ports[1])
    theirs = _ref_config(tmp_path, ref_role, ports[1], ports[0])
    workdir = tmp_path / "refwork"
    workdir.mkdir()
    ref = subprocess.Popen(
        ["uv", "run", "--project", str(REFERENCE), "python", "-m", "police_thief", "peer",
         "--role", ref_role, "--config", str(theirs), "--stub-llm", "--no-gui"],
        cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    mine = subprocess.Popen(
        ["uv", "run", "cipherchase", "peer", "--role", our_role, "--config", str(ours)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        my_out, my_err = mine.communicate(timeout=300)
        ref_out, ref_err = ref.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        mine.kill()
        ref.kill()
        pytest.fail(f"series deadlocked\nOURS:{mine.stdout}\nREF:{ref.stdout}")
    assert mine.returncode == 0, f"our peer failed:\n{my_out}\n{my_err}"
    assert ref.returncode == 0, f"reference failed:\n{ref_out}\n{ref_err}"
    summary = json.loads(my_out.strip().splitlines()[-1])
    subs = summary["sub_games"]
    assert len(subs) == NUM_GAMES
    roles = [s["role"] for s in subs]
    assert roles[0] != roles[1], "roles must swap between sub-games"
    for sub in subs:
        assert sub["result"] in ("capture", "survival"), f"illegal outcome: {sub}"
        assert sub["audit"]["passed"] is True, f"audit not verified: {sub}"
