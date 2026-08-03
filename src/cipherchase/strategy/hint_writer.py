"""Contextual hint composition (F6, book Ch4/6) — pure Python, zero tokens.

The wire hint is FREE natural language and MAY lie; the board may not. This
composer grounds every line in the real game — the heading actually taken, the
believed gap, barriers placed, and the landmarks of the agreed setting — so the
words carry information an opponent can reason about (and be deceived by).

Honesty rule that makes ``intent`` meaningful: a ``truth`` line names the real
heading; a ``lie`` line NEVER does — it names a different one or misdirects
entirely. The sealed ``intent`` is therefore an audit-checkable claim, not a
label we could contradict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cipherchase.constants import Direction

_WORD = {Direction.N: "north", Direction.S: "south", Direction.E: "east",
         Direction.W: "west", Direction.STAY: "still"}
_OPPOSITE = {Direction.N: Direction.S, Direction.S: Direction.N,
             Direction.E: Direction.W, Direction.W: Direction.E,
             Direction.STAY: Direction.N}

_TRUTH = {
    "police": ["Working my way {dir} from {mark}.",
               "Closing in near {mark} — nowhere left to run.",
               "Every road past {mark} is watched now.",
               "{barriers} streets sealed near {mark}. I am {gap} behind."],
    "thief": ["Still moving {dir} — {mark} is behind me now.",
              "Past {mark} and running {dir}.",
              "You are {gap} steps late — I passed {mark} already.",
              "{mark} was crowded. I kept going {dir}."],
}
_LIE = {
    "police": ["I have lost the trail completely near {mark}.",
               "Searching the far side by {mark} — nothing here.",
               "Heading {dir} now; the rest of the map is yours.",
               "My barriers are spent around {mark}. Take your time."],
    "thief": ["Doubling back {dir} past {mark}.",
              "I am cornered by {mark}. Come and get me.",
              "Resting at {mark}. Not moving tonight.",
              "Heading {dir} past {mark}, promise."],
}


@dataclass
class HintContext:
    role: str
    intent: str
    step: int
    direction: Direction
    gap: int
    barriers: int
    landmarks: list[str] = field(default_factory=list)
    max_words: int = 15


def compose(ctx: HintContext) -> str:
    """One grounded sentence, within the agreed word budget."""
    bank = (_LIE if ctx.intent == "lie" else _TRUTH).get(ctx.role, _TRUTH["police"])
    template = bank[ctx.step % len(bank)]
    spoken = _OPPOSITE[ctx.direction] if ctx.intent == "lie" else ctx.direction
    mark = ctx.landmarks[ctx.step % len(ctx.landmarks)] if ctx.landmarks else "the district"
    text = template.format(dir=_WORD[spoken], mark=mark, gap=ctx.gap, barriers=ctx.barriers)
    words = text.split()
    if len(words) > ctx.max_words:  # the agreed hint_max_words always wins
        text = " ".join(words[:ctx.max_words]).rstrip(",;—") + "."
    return text
