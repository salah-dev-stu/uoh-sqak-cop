"""A role-split opponent serves cop and thief at DIFFERENT addresses (anrbj666).

Their cop and thief are separate services on separate hostnames, so the address
we dial changes every sub-game: we face their cop on the windows where we are
thief, and their thief on the windows where we are cop. Holding one URL for a
whole series dials the wrong service on half of it — and the wrong service
answers, so it fails as a refusal rather than as a connection error.
"""

from __future__ import annotations

from pathlib import Path

from cipherchase.sdk.series import opponent_url_for
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
SPLIT = {"opponent_url": "https://fallback/mcp",
         "opponent_url_police": "https://cop-mcp.alon.website/mcp",
         "opponent_url_thief": "https://thief-mcp.alon.website/mcp"}


def test_we_dial_their_cop_on_the_windows_where_we_are_thief() -> None:
    assert opponent_url_for(SPLIT, our_role="thief") == "https://cop-mcp.alon.website/mcp"


def test_we_dial_their_thief_on_the_windows_where_we_are_cop() -> None:
    assert opponent_url_for(SPLIT, our_role="police") == "https://thief-mcp.alon.website/mcp"


def test_a_single_address_opponent_is_unaffected() -> None:
    one = {"opponent_url": "https://one-address/mcp"}
    assert opponent_url_for(one, our_role="thief") == "https://one-address/mcp"
    assert opponent_url_for(one, our_role="police") == "https://one-address/mcp"


def test_the_shipped_config_still_resolves() -> None:
    net = ConfigManager.load(CONFIG / "thief").network
    assert opponent_url_for(net, our_role="thief") == net["opponent_url"]
