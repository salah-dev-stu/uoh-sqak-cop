"""IC-7: ∀ JSON-able payloads seal→verify round-trips; ∀ single-char tampers fail."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cipherchase.domain.crypto import CommitReveal
from cipherchase.exceptions import CryptoError
from properties.strategies import bump_hex, payloads


@given(payloads)
def test_seal_then_verify_never_raises(payload) -> None:
    commit, nonce = CommitReveal.seal(payload)
    CommitReveal.verify(payload, nonce, commit)  # the honest path must never raise


@given(payloads, st.integers(min_value=0, max_value=31))
def test_any_nonce_perturbation_is_caught(payload, index) -> None:
    commit, nonce = CommitReveal.seal(payload)
    with pytest.raises(CryptoError):
        CommitReveal.verify(payload, bump_hex(nonce, index), commit)


@given(payloads, st.integers(min_value=0, max_value=63))
def test_any_commit_perturbation_is_caught(payload, index) -> None:
    commit, nonce = CommitReveal.seal(payload)
    with pytest.raises(CryptoError):
        CommitReveal.verify(payload, nonce, bump_hex(commit, index))
