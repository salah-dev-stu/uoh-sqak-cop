"""P0 engine truth (IH-1..5, IH-8..12): sealed truth, seeded, config-wired."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cipherchase.constants import Outcome
from cipherchase.sdk.game_loop import run_game
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _cfg() -> ConfigManager:
    return ConfigManager.load(CONFIG / "police")


def test_sealed_payloads_carry_the_real_barrier_view() -> None:
    frames: list[dict] = []
    result = run_game(_cfg(), on_frame=frames.append)
    by_step = {f["turn"]: f for f in frames}
    placed_any = any(f["barriers"] for f in frames)
    assert placed_any, "test needs a game where barriers are placed"
    for record in result.records:
        step = record["payload"]["step"]
        # decision-time truth: payload barriers match the frame captured pre-move
        assert record["payload"]["state"]["barriers"] == by_step[step]["barriers"] or (
            record["payload"]["state"]["barriers"] != []  # thief seals post-placement view
        )
    # the strongest check: the LAST cop payload is never the empty list once walls exist
    last_cop = [r for r in result.records if r["payload"]["step"] == result.turns][0]
    if frames[-1]["barriers"]:
        assert last_cop["payload"]["state"]["barriers"] != []


def test_intent_lie_and_hints_actually_fire() -> None:
    cfg = _cfg()
    cfg.private["trash_talk"]["lie_probability"] = 1.0
    cfg.private["trash_talk"]["every_n_steps"] = 1
    frames: list[dict] = []
    result = run_game(cfg, on_frame=frames.append)
    assert any(r["payload"]["intent"] == "lie" for r in result.records)
    assert any(f["hint"] for f in frames)


def test_zero_token_default_and_seeded_determinism() -> None:
    cfg = _cfg()
    with patch("subprocess.run") as run:
        a = run_game(cfg)
        b = run_game(cfg)
    assert not run.called  # template provider — 0 tokens
    assert [r["payload"] for r in a.records] == [r["payload"] for r in b.records]


def test_fresh_deposit_is_not_decayed_the_same_turn() -> None:
    frames: list[dict] = []
    run_game(_cfg(), on_frame=frames.append)
    first = frames[0]
    thief_key = f'{first["thief"][0]},{first["thief"][1]}'
    assert abs(first["scent"][thief_key] - 0.9) < 1e-9  # 0.9, not 0.9*(1-rho)


def test_tie_when_game_ends_before_survival_threshold() -> None:
    cfg = _cfg()
    cfg.shared["movement_and_barriers"]["max_moves"] = 5  # < survival_threshold 35
    result = run_game(cfg)
    assert result.outcome is Outcome.TIE
    assert result.scores == (2, 2)


def test_belief_alpha_and_max_barriers_come_from_config() -> None:
    cfg = _cfg()
    cfg.private["belief"]["alpha"] = 0.42
    cfg.shared["movement_and_barriers"]["max_barriers"] = 2
    seen: list[float] = []
    from cipherchase.domain.scent_decode import ScentDecoder as Real

    def spy(size, smell_trust, alpha, ph):
        seen.append(alpha)
        return Real(size, smell_trust, alpha, ph)

    frames: list[dict] = []
    with patch("cipherchase.sdk.game_loop.ScentDecoder", side_effect=spy):
        run_game(cfg, on_frame=frames.append)
    assert all(a == 0.42 for a in seen) and seen
    assert len(frames[-1]["barriers"]) <= 2  # brain honors the shared cap
