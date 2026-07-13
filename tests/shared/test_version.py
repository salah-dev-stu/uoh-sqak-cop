"""Version single-source + startup compatibility guard (NFR-6, FR-I3)."""

from __future__ import annotations

import pytest

from cipherchase.exceptions import IncompatibleVersionError
from cipherchase.shared.version import VERSION, check_compatible


def test_version_is_one_dot_zero() -> None:
    assert VERSION == "1.00"


def test_check_compatible_accepts_same_major() -> None:
    check_compatible("1.00")
    check_compatible("1.50")  # same major → compatible, no raise


def test_check_compatible_rejects_different_major() -> None:
    with pytest.raises(IncompatibleVersionError):
        check_compatible("2.00")


def test_check_compatible_rejects_malformed() -> None:
    with pytest.raises(IncompatibleVersionError):
        check_compatible("not-a-version")
