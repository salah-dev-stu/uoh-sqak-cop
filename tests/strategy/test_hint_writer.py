"""Contextual hints (F6, Ch4/6): grounded in the real game, honest about lying."""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.strategy.hint_writer import HintContext, compose

LANDMARKS = ["Harlem", "Central Park", "the waterfront"]


def _ctx(**kw) -> HintContext:
    base = {"role": "police", "intent": "truth", "step": 3, "direction": Direction.N,
            "gap": 4, "barriers": 2, "landmarks": LANDMARKS, "max_words": 15}
    base.update(kw)
    return HintContext(**base)


_WORDS = {"north": Direction.N, "south": Direction.S, "east": Direction.E, "west": Direction.W}


def test_truthful_hints_are_grounded_and_never_misstate_the_heading() -> None:
    for step in range(8):
        text = compose(_ctx(direction=Direction.S, intent="truth", step=step))
        assert any(mark.lower() in text.lower() for mark in LANDMARKS), text
        spoken = _WORDS.keys() & set(text.lower().replace("—", " ").split())
        for word in spoken:
            assert _WORDS[word] is Direction.S, text  # truth names the REAL heading


def test_a_lie_never_states_the_direction_actually_taken() -> None:
    # intent="lie" is SEALED into the commit — the words must really be false,
    # or the audit convicts us of lying about lying (F6).
    for real in (Direction.N, Direction.S, Direction.E, Direction.W):
        for step in range(8):
            text = compose(_ctx(direction=real, intent="lie", step=step)).lower()
            spoken = _WORDS.keys() & set(text.replace("—", " ").split())
            for word in spoken:  # if it names a heading, it must be the WRONG one
                assert _WORDS[word] is not real, text


def test_hints_respect_the_agreed_word_budget() -> None:
    for role in ("police", "thief"):
        for intent in ("truth", "lie"):
            for step in range(12):
                text = compose(_ctx(role=role, intent=intent, step=step))
                assert len(text.split()) <= 15, text
                assert text.endswith((".", "!", "?"))


def test_hints_vary_across_turns_rather_than_looping_one_line() -> None:
    seen = {compose(_ctx(step=s, gap=s % 5)) for s in range(10)}
    assert len(seen) >= 5  # a real commentator, not a stuck record


def test_roles_speak_differently() -> None:
    cop = compose(_ctx(role="police", intent="truth", step=1))
    thief = compose(_ctx(role="thief", intent="truth", step=1))
    assert cop != thief


def test_landmarkless_setting_still_produces_a_clean_sentence() -> None:
    text = compose(_ctx(landmarks=[]))
    assert text and len(text.split()) <= 15 and text.endswith((".", "!", "?"))


def test_a_tight_word_budget_is_enforced_by_trimming() -> None:
    # An opponent may agree a much smaller hint_max_words than our lines need
    # (rule 12 allows raising a term). The budget always wins, and the trimmed
    # line still reads as a sentence rather than a severed fragment.
    for step in range(8):
        text = compose(_ctx(step=step, max_words=4))
        assert len(text.split()) <= 4, text
        assert text.endswith(".") and not text.endswith((",.", ";.", "—."))
