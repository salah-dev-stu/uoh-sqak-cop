"""ConfigManager — private ``game.toml`` overlaid by the signed ``game.json``.

Rule (FR-I1/I2): anything both peers must agree on lives in the signed JSON and
is authoritative; the private TOML may add peer-local settings but can NEVER
override a signed key. Rate-limit buckets load from ``rate_limits.json``.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from cipherchase.domain.negotiation import config_sha256
from cipherchase.shared.version import check_compatible

Json = dict[str, Any]


class ConfigManager:
    def __init__(self, shared: Json, private: Json, rate_limits: Json) -> None:
        self.shared = shared
        self.private = private
        self.rate_limits = rate_limits
        self.config_sha256 = config_sha256(shared)

    @classmethod
    def load(cls, config_dir: str | Path) -> ConfigManager:
        base = Path(config_dir)
        shared = json.loads((base / "game.json").read_text(encoding="utf-8"))
        private = tomllib.loads((base / "game.toml").read_text(encoding="utf-8"))
        rate_limits = json.loads((base / "rate_limits.json").read_text(encoding="utf-8"))
        check_compatible(str(private.get("version", "")))  # startup guard (R6)
        return cls(shared, private, rate_limits)

    @property
    def merged(self) -> Json:
        """Private view with signed keys overlaid — signed always wins."""
        return {**self.private, **self.shared}

    @property
    def role(self) -> str:
        return self.private["game"]["role"]

    @property
    def network(self) -> Json:
        return self.private["network"]

    @property
    def opponent_url(self) -> str:
        return self.network["opponent_url"]

    @property
    def my_port(self) -> int:
        return int(self.network["my_port"])

    @property
    def queue_maxsize(self) -> int:
        return int(self.network["queue_maxsize"])
