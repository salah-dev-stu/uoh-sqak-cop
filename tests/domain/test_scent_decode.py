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
