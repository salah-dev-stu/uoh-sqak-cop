"""ScentDecoder (WB §3): Δ = τ_t − (1−ρ)·τ_{t−1} → the thief's exact cell."""

from __future__ import annotations

from cipherchase.domain.cells import cell_key
from cipherchase.domain.scent_decode import ScentDecoder
from cipherchase.domain.smell import SmellField

PH = {"grid_size": 5, "center_intensity": 0.9, "decay": 0.1, "falloff": 0.7}


def _smell() -> SmellField:
    return SmellField(7, 5, 0.9, 0.1, 0.7)


def test_decoder_recovers_the_exact_deposit_cell_from_two_snapshots() -> None:
    smell, decoder = _smell(), ScentDecoder(7, 4.0, 0.85, PH)
    smell.decay_all()
    smell.deposit((5, 5))
    decoder.update(smell.snapshot())
    smell.decay_all()
    smell.deposit((5, 4))  # thief moved W
    belief = decoder.update(smell.snapshot())
    assert decoder.last_decoded == (5, 4)  # Δ-argmax = the CURRENT cell, not the trail
    assert belief.most_likely() == (5, 4)


def test_decoder_tracks_a_moving_thief_with_zero_error() -> None:
    smell, decoder = _smell(), ScentDecoder(7, 4.0, 0.85, PH)
    path = [(3, 3), (3, 4), (4, 4), (5, 4), (5, 5), (5, 6)]
    for cell in path:
        smell.decay_all()
        smell.deposit(cell)
        belief = decoder.update(smell.snapshot())
    assert belief.most_likely() == path[-1]


def test_ambiguous_delta_falls_back_to_persistent_belief() -> None:
    decoder = ScentDecoder(7, 4.0, 0.85, PH)
    snap = {cell_key((3, 3)): 0.9}
    decoder.update(snap)
    # identical repeated snapshot (no fresh deposit visible) → Δ ~ residue only
    belief = decoder.update({k: v * 0.9 for k, v in snap.items()})
    assert decoder.last_decoded is None  # ambiguity detected
    assert belief.most_likely() == (3, 3)  # persistent grid still carries the story


def test_empty_snapshot_never_crashes() -> None:
    decoder = ScentDecoder(7, 4.0, 0.85, PH)
    belief = decoder.update({})
    assert belief.most_likely() == (0, 0)  # uniform → deterministic tie-break


def test_unsaturated_fresh_stamp_tracks_a_league_style_field() -> None:
    # najamjad warm-up finding: their field never saturates and never culls — the
    # unique fresh-intensity cell IS the opponent. Our filter (built for OUR
    # saturating physics) lagged 5-10 turns on such fields. The fresh-stamp
    # shortcut must track the mover exactly.
    dec = ScentDecoder(7, 4.0, 0.85, PH)
    field: dict[str, float] = {}
    path = [(3, 3), (3, 4), (4, 4), (5, 4), (5, 3), (5, 2), (6, 2)]
    for pos in path:
        field = {k: round(v * 0.9, 4) for k, v in field.items() if v * 0.9 > 0.003}
        field[f"{pos[0]},{pos[1]}"] = 0.9  # fresh, unculled, never above 0.9
        grid = dec.update(dict(field))
        assert grid.most_likely() == pos, f"lost the mover at {pos}"


def test_real_najamjad_wires_are_tracked_step_by_step() -> None:
    # Golden fixture: an actual captured 34-step league game (their thief's own
    # broadcast smell). The decoder must follow the fresh stamp all game long.
    import json
    from pathlib import Path
    fixture = json.loads((Path(__file__).parent / "fixtures_league_smell.json").read_text())
    dec = ScentDecoder(7, 4.0, 0.85, {**PH, "min_center_intensity": 0.5})
    lost = []
    for entry in fixture:
        sg = entry["smell_grid"]
        grid = dec.update(dict(sg))
        strongest = max(sg, key=sg.get)
        strongest = tuple(int(x) for x in strongest.split(","))
        if grid.most_likely() != strongest:
            lost.append(entry["step"])
    assert lost == [], f"decoder lost the real opponent at steps {lost}"
