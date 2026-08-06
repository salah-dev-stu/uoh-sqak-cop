"""The two scent rules `subtractive_chebyshev_v1` leaves open (imreeyal, s1).

The registration pins emit, falloff, decay, rounding, cadence and order — but
NOT how a new deposit combines with what the cell already holds, and its `clamp`
upper bound is null. So two peers can declare the identical `81ebee59…` hash and
still run different physics, which is exactly what the lock exists to prevent.

Agreed bilaterally for this pairing, pending a kit fix:
  * combine = max  (keeps the field bounded by emit_intensity without leaning on
    an upper clamp the doc leaves open)
  * order   = deposit_then_decay  (what the doc already says; we had it inverted)

Our old physics decayed THEN deposited and ADDED, so our freshest cell read 0.9
and old trail saturated to 1.0 — above emit_intensity, which is what made them
refuse all 35 of our frames.
"""

from __future__ import annotations

from cipherchase.domain.smell import SmellField

WALK = [(3, 3), (3, 4), (3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (4, 3)]


def _field() -> SmellField:
    return SmellField(7, 5, 0.9, 0.1, model="subtractive_chebyshev_v1")


def _turn(field: SmellField, cell: tuple[int, int]) -> dict[str, float]:
    """One full turn as the registration orders it: deposit, then decay."""
    field.deposit(cell)
    field.decay_all()
    return field.snapshot()


def test_step_one_transmits_what_the_opponent_transmits() -> None:
    # They send 0.8/0.5/0.2 at step 1; we used to send 0.9/0.6/0.3. The gap was
    # not first-mover asymmetry — it is deposit_then_decay vs our inverted order.
    snap = _turn(_field(), (3, 3))
    assert snap["3,3"] == 0.8
    assert snap["2,3"] == 0.5
    assert snap["1,3"] == 0.2


def test_the_field_never_exceeds_the_emit_intensity() -> None:
    # The refusal they raised: our cells reached 1.0 above a 0.9 centre.
    field = _field()
    for step, cell in enumerate(WALK * 3):
        snap = _turn(field, cell)
        assert max(snap.values()) <= 0.9, f"cell above emit_intensity at step {step}"


def test_revisiting_a_cell_refreshes_it_instead_of_stacking() -> None:
    field = _field()
    _turn(field, (3, 3))
    _turn(field, (3, 4))
    back = _turn(field, (3, 3))  # returning to a cell we already scented
    assert back["3,3"] == 0.8, "max refreshes to the fresh value; adding would stack"


def test_an_old_trail_still_decays_away_to_nothing() -> None:
    field = _field()
    _turn(field, (0, 0))
    for _ in range(12):  # walk far away and stay there
        _turn(field, (6, 6))
    assert "0,0" not in field.snapshot(), "max must not freeze a cell forever"


def test_the_live_turn_emits_in_the_declared_order() -> None:
    # We declared order=deposit_then_decay and did the opposite, so our freshest
    # cell went out at full emit_intensity while a conforming peer's went out one
    # decay lower. That single inversion is the whole 0.9-vs-0.8 gap.
    from pathlib import Path

    from fakes.fake_transport import make_pair

    from cipherchase.peer.runtime import PeerRuntime
    from cipherchase.peer.state_machine import State
    from cipherchase.shared.config import ConfigManager
    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "thief")
    cfg.private["scent"] = {"model": "subtractive_chebyshev_v1"}
    a, _b = make_pair()
    rt = PeerRuntime(role="thief", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    grid = [w for (_t, _k, w) in a.sent if w.get("sender") == "thief"][0]["smell_grid"]
    assert max(grid.values()) == 0.8, "the transmitted peak is emit minus one decay"


def test_the_decoder_still_locks_on_under_the_agreed_physics() -> None:
    # The fresh-stamp shortcut was calibrated to a peak at emit_intensity. Under
    # deposit_then_decay the freshest cell arrives one decay lower, so a decoder
    # that insists on 0.9 silently falls back to the matched filter against every
    # conforming peer — losing exactly the fix that made our cop track a league
    # thief in the first place.
    from cipherchase.domain.scent_decode import ScentDecoder
    pher = {"grid_size": 5, "center_intensity": 0.9, "decay": 0.1,
            "falloff": 0.7, "min_center_intensity": 0.5}
    decoder = ScentDecoder(7, 4.0, 0.85, pher)
    field = _field()
    for cell in [(3, 3), (3, 4), (4, 4)]:
        snap = _turn(field, cell)
    assert decoder.fresh_peak(snap) == (4, 4), "the fresh stamp is the opponent"
