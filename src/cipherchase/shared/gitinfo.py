"""The commit that is playing — probed through the gatekeeper (R3).

Shared because BOTH the declaration artifact and the sealed step-0 record need
it: the artifact so a grader can read it, the seal so the audit trail pins the
code that actually played. It was in only the first, which meant an opponent
replaying our audit had nothing to check the repo against.
"""

from __future__ import annotations

import subprocess
from typing import Any


def git_commit(gate: Any) -> str:
    def probe() -> str:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"

    try:
        return gate.execute(probe, service="subprocess", action="git_rev_parse")
    except Exception:
        return "unknown"
