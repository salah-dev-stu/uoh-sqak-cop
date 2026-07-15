"""LLM/trash-talk providers (FR-D4). Template = 0 tokens, default & test path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cipherchase.exceptions import ProviderUnavailableError
from cipherchase.infra.llm_provider import (
    ClaudeCliProvider,
    TalkContext,
    TemplateProvider,
    build_provider,
)

CTX = TalkContext(role="police", step=2, own_move="N", intent="truth")


def test_template_provider_is_deterministic_and_zero_token() -> None:
    provider = TemplateProvider()
    text = provider.generate(CTX)
    assert isinstance(text, str) and text
    assert provider.generate(CTX) == text  # deterministic


def test_build_provider_defaults_to_template() -> None:
    assert isinstance(build_provider({"provider": "template"}), TemplateProvider)


def test_build_provider_unknown_raises() -> None:
    with pytest.raises(ProviderUnavailableError):
        build_provider({"provider": "no-such-llm"})


def test_claude_cli_parses_json_result() -> None:
    fake = MagicMock(returncode=0, stdout='{"result": "gotcha"}', stderr="")
    with patch("subprocess.run", return_value=fake) as run:
        text = ClaudeCliProvider(binary="claude").generate(CTX)
    assert text == "gotcha"
    assert "ANTHROPIC_API_KEY" not in run.call_args.kwargs["env"]  # key stripped


def test_claude_cli_failure_raises_provider_unavailable() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError("no claude")), pytest.raises(
        ProviderUnavailableError
    ):
        ClaudeCliProvider(binary="claude").generate(CTX)


def test_build_provider_makes_claude_cli() -> None:
    provider = build_provider({"provider": "claude_cli", "executable": "claude"})
    assert isinstance(provider, ClaudeCliProvider)


def test_claude_cli_nonzero_exit_raises() -> None:
    fake = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch("subprocess.run", return_value=fake), pytest.raises(ProviderUnavailableError):
        ClaudeCliProvider(binary="claude").generate(CTX)


def test_llm_call_routes_through_the_gatekeeper() -> None:
    from cipherchase.shared.gatekeeper import ApiGatekeeper

    class _AllowAll:
        def allow(self, service: str) -> bool:
            return True

    gate = ApiGatekeeper(_AllowAll(), sleep=lambda _s: None)
    fake = MagicMock(returncode=0, stdout='{"result": "hi"}', stderr="")
    with patch("subprocess.run", return_value=fake):
        text = ClaudeCliProvider(binary="claude", gate=gate).generate(CTX)
    assert text == "hi"
    assert gate.ledger[-1] == {"service": "llm", "action": "generate", "status": "ok"}
