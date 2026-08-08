#!/usr/bin/env python3
"""Rebuild ONLY the result of a played series, when the result's shape changes.

The declaration, configs and logs are left exactly as played. Regenerating the
declaration would re-sign a step-0 record over today's state, and rewriting the
logs would touch sealed records — both would falsify evidence of a game that has
already happened, to fix a schema.

`github_commit` names the commit that PLAYED the series, recovered from the
original declaration, not the commit doing the regeneration. A row claiming
today's HEAD would point a grader at code that never played the game.

The mutual signature must come out UNCHANGED: it covers the symmetric outcome
only, so a shape change that moves it touched something it had no business
touching.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cipherchase.report import emit  # noqa: E402
from cipherchase.sdk.league_reports import build_series_artifacts  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402
from cipherchase.shared.gatekeeper import ApiGatekeeper  # noqa: E402


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/league/imreeyal")
    opponent = sys.argv[2] if len(sys.argv) > 2 else "imreeyal"
    role_cfg = sys.argv[3] if len(sys.argv) > 3 else "config/thief"
    logs = sorted(out.glob("log_*_g*.json"))
    if not logs:
        print(f"no logs in {out}")
        return 1
    result_path = next(out.glob("result_*.json"))
    prior = json.loads(result_path.read_text())
    before = prior["mutual_agreement"]["sha256"]
    # A regeneration fixes SHAPE. Whether the game counted is a fact about the
    # game, so it is carried over rather than re-decided — dropping it silently
    # wiped the diversity reward on the first attempt at this.
    was_counted = bool(prior["final_result"].get("counted", False))
    declaration = json.loads(next(out.glob("declaration_*.json")).read_text())
    played_at = declaration["step0"]["git_commit"]
    summaries = []
    for path in logs:
        doc = json.loads(path.read_text())
        summaries.append({
            "sub_game_number": doc["sub_game"], **doc["summary"],
            "records": doc["records"],
            "audit": {"passed": doc["mutual_agreement"]["confirmed"], "status": "done"},
        })
    outcome = {"game_id": logs[0].name.split("_")[1], "game_uid":
               json.loads(logs[0].read_text())["game_uid"], "summaries": summaries}
    cfg = ConfigManager.load(role_cfg)
    gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)
    # Opponent commits as DECLARED by them (argv[6] "odd:even"), not as read
    # from their sealed record — we verify their audit payload and discard it,
    # so we cannot read the field. Filed as-declared and labelled as such.
    declared = sys.argv[6].split(":") if len(sys.argv) > 6 else []
    opp_commits = ({n: declared[0] if n % 2 else declared[1] for n in range(1, 7)}
                   if len(declared) == 2 else "unknown")
    arts = build_series_artifacts(
        cfg, outcome, opponent=opponent, gate=gate, commit=played_at,
        opponent_commits=opp_commits,
        generated_at=datetime.now(UTC).isoformat(), counted=was_counted, first_meeting=True,
        games_played=int(sys.argv[4]) if len(sys.argv) > 4 else 0,
        opponent_counted=int(sys.argv[5]) if len(sys.argv) > 5 else 0)
    result = next(a for a in arts if a["_schema"] == "result")
    print("wrote", emit.write_artifact(out, result), "(declaration/configs/logs untouched)")
    after = result["mutual_agreement"]["sha256"]
    print(f"\nmutual_agreement.sha256 before {before}\n"
          f"                        after  {after}")
    print("UNCHANGED — a shape change must not move the symmetric signature"
          if before == after else "*** MOVED — the shape change touched the signature ***")
    return 0 if before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
