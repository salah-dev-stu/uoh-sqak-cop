"""Single source of truth for the package version (NFR-6 / R6).

The build backend (hatchling) reads ``__version__`` from this file, the runtime
config mirrors it in a ``version`` field, and ``scripts/check_version_sync.py``
plus a unit test assert the two never drift. ``check_compatible`` is the
startup guard that refuses to play against an incompatible peer/config.
"""

from __future__ import annotations

from cipherchase.exceptions import IncompatibleVersionError

__version__ = "1.00"
VERSION = __version__


def _major(value: str) -> int:
    """Parse the major version integer, or reject a malformed string."""
    try:
        return int(str(value).split(".")[0])
    except ValueError:
        raise IncompatibleVersionError(f"malformed version: {value!r}") from None


def check_compatible(other: str) -> None:
    """Raise ``IncompatibleVersionError`` unless ``other`` shares our major.

    Same-major versions are interoperable; a different major (or a malformed
    string) means the peer/config speaks a different protocol and we refuse.
    """
    if _major(other) != _major(VERSION):
        raise IncompatibleVersionError(f"{other!r} incompatible with {VERSION!r}")
