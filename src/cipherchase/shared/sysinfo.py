"""Best-effort system probe for the Step-0 declaration (FR-F4).

Kept intentionally simple and dependency-free (no psutil): OS/CPU/RAM/GPU and
Python version, enough to attest the hardware a game ran on.
"""

from __future__ import annotations

import os
import platform
from typing import Any


def _ram_gb() -> float:
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 1)
    except (ValueError, OSError, AttributeError):
        return 0.0


def _gpu() -> str:
    return "Apple Silicon" if platform.machine() == "arm64" else "unknown"


def system_info() -> dict[str, Any]:
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "gpu": _gpu(),
        "python": platform.python_version(),
    }
