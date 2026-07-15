"""Typed exceptions for CipherChase — one module, no duplication (R2)."""

from __future__ import annotations


class CipherChaseError(Exception):
    """Base class for every CipherChase domain and runtime error."""


class IllegalMoveError(CipherChaseError):
    """A move is off-board, diagonal, or through a barrier (FR-A2)."""


class IllegalBarrierError(CipherChaseError):
    """A barrier placement is non-adjacent or exceeds the budget (FR-A3)."""


class CryptoError(CipherChaseError):
    """Commit/reveal verification failed (FR-F1)."""


class TamperError(CryptoError):
    """Mutual audit found a mismatch → tamper_forfeit 0/0 (FR-F3)."""


class GateLimitError(CipherChaseError):
    """The API gatekeeper's rate/budget limit was exceeded (NFR-3/4)."""


class ConfigError(CipherChaseError):
    """Config missing, malformed, or signature mismatch (FR-I)."""


class ProtocolError(CipherChaseError):
    """A wire message is malformed or arrived in an illegal state (FR-B)."""


class HandshakeError(CipherChaseError):
    """Peers failed to agree on a byte-identical signed config (FR-I1, F14)."""


class ProviderUnavailableError(CipherChaseError):
    """An LLM provider is missing/failed — fall back to templates (FR-D4)."""


class DeadlineError(CipherChaseError):
    """A peer missed a turn/response deadline → technical loss (FR-H3)."""


class TransportError(CipherChaseError):
    """An MCP send/receive failed (FR-B3)."""


class TransportTimeoutError(TransportError):
    """No message arrived within the poll deadline (FR-B3)."""


class QueueFullError(CipherChaseError):
    """An inbox reached its bounded capacity — backpressure, never drop (NFR-5)."""


class IllegalTransitionError(CipherChaseError):
    """A state-machine transition is not permitted (FR-H2)."""


class IncompatibleVersionError(CipherChaseError):
    """Peer/config version is incompatible with ours (NFR-6)."""
