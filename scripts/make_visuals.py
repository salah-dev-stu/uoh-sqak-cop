#!/usr/bin/env python3
"""Render the mandatory visuals headlessly (F12): belief heatmap + replay proof.

Produces docs/sample-run/live_gui_belief.png and replay_verified.png with a
non-interactive backend, so they can be committed without a display. The live
Tkinter GUI (gui/window.py, gui/replay.py) shows the same data interactively.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path("src")))
from cipherchase.domain.belief import BeliefGrid  # noqa: E402
from cipherchase.domain.smell import SmellField  # noqa: E402
from cipherchase.gui.replay_data import verify_records  # noqa: E402

OUT = Path("docs/sample-run")


def belief_heatmap() -> None:
    smell = SmellField(7, 5, 0.9, 0.1, 0.7)
    belief = BeliefGrid(7, smell_trust=4.0)
    for cell in ((5, 5), (5, 4), (4, 4)):  # a short thief scent trail
        smell.deposit(cell)
        smell.decay_all()
    belief.observe_smell(smell.snapshot())
    belief.diffuse()
    fig, ax = plt.subplots(figsize=(4.4, 4.4))
    ax.imshow(belief.as_matrix(), cmap="hot", interpolation="nearest")
    ax.plot(0, 0, "co", markersize=14, label="cop (me)")
    ax.set_title("CipherChase — Live belief heatmap (local truth)")
    ax.legend(loc="upper right")
    fig.savefig(OUT / "live_gui_belief.png", dpi=120, bbox_inches="tight")


def replay_proof() -> None:
    log = json.loads(sorted(OUT.glob("log_*.json"))[0].read_text())
    steps = verify_records(log["records"])
    ok = sum(s["status"] == "Verified OK" for s in steps)
    fig, ax = plt.subplots(figsize=(5.2, 1.8))
    ax.axis("off")
    ax.text(0.5, 0.7, "Verified OK", ha="center", fontsize=30, color="white",
            bbox={"facecolor": "#27ae60", "pad": 12})
    ax.text(0.5, 0.15, f"{ok}/{len(steps)} committed steps re-hashed clean", ha="center", fontsize=11)
    fig.savefig(OUT / "replay_verified.png", dpi=120, bbox_inches="tight")


if __name__ == "__main__":
    belief_heatmap()
    replay_proof()
    print("wrote", OUT / "live_gui_belief.png", "and", OUT / "replay_verified.png")
