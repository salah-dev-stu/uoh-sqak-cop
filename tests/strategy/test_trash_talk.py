"""Trash-talk orchestration: intent, throttle, fallback (FR-D2/D3/D4)."""

from __future__ import annotations

from unittest.mock import MagicMock

from cipherchase.exceptions import ProviderUnavailableError
from cipherchase.infra.llm_provider import TalkContext, TemplateProvider
from cipherchase.strategy.trash_talk import TrashTalk


def _talk(provider, fallback=None, **kw) -> TrashTalk:
    return TrashTalk(provider, fallback or TemplateProvider(), **kw)


def test_choose_intent_uses_lie_probability() -> None:
    rng = MagicMock()
    rng.random.return_value = 0.1  # < 0.4 → lie
    assert _talk(TemplateProvider(), lie_probability=0.4, rng=rng).choose_intent() == "lie"
    rng.random.return_value = 0.9
    assert _talk(TemplateProvider(), lie_probability=0.4, rng=rng).choose_intent() == "truth"


def test_throttle_stays_silent_off_cadence() -> None:
    talk = _talk(TemplateProvider(), every_n_steps=3)
    assert talk.maybe_generate(TalkContext(role="thief", step=1)) == ""
    assert talk.maybe_generate(TalkContext(role="thief", step=3)) != ""


def test_provider_failure_falls_back_to_template() -> None:
    broken = MagicMock()
    broken.generate.side_effect = ProviderUnavailableError("down")
    talk = _talk(broken, fallback=TemplateProvider(), every_n_steps=1)
    text = talk.maybe_generate(TalkContext(role="police", step=1))
    assert text  # never blocks — template fills in
