"""The F9 crash boundary: an unexpected exception becomes a result, never a hang."""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.peer.runtime import PeerRuntime
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_unexpected_crash_in_run_yields_error_result_not_a_hang() -> None:
    a, _b = make_pair()
    cfg = ConfigManager.load(CONFIG / "police")
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    rt._run = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # force the boundary
    out = rt.run()
    assert out["result"] == "error"  # a summarised result, never a raised exception
    assert "boom" in out["note"]
