"""System probe for the Step-0 declaration (FR-F4)."""

from __future__ import annotations

import platform

from cipherchase.shared.sysinfo import system_info


def test_system_info_has_declaration_fields() -> None:
    info = system_info()
    for key in ("os", "cpu", "ram_gb", "gpu", "python"):
        assert key in info


def test_ram_and_python_are_plausible() -> None:
    info = system_info()
    assert isinstance(info["ram_gb"], float)
    assert info["ram_gb"] >= 0.0
    assert info["python"] == platform.python_version()


def test_ram_probe_falls_back_to_zero_on_unsupported_platform() -> None:
    from unittest.mock import patch

    with patch("os.sysconf", side_effect=ValueError("unsupported")):
        assert system_info()["ram_gb"] == 0.0
