"""Write the 4 JSON artifacts with their canonical filenames (FR-G1, F11).

``config``/``log`` are per sub-game (``_g<NN>``); ``declaration``/``result`` are
per series. Files are pretty-printed JSON (the graded, human-readable proof).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cipherchase.report import schemas


def filename(kind: str, game_id: str, sub_game: int | None = None) -> str:
    if kind in (schemas.CONFIG, schemas.LOG):
        return f"{kind}_{game_id}_g{sub_game:02d}.json"
    return f"{kind}_{game_id}.json"


def write_artifact(directory: str | Path, artifact: dict[str, Any]) -> Path:
    name = filename(artifact["_schema"], artifact["game_id"], artifact.get("sub_game"))
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_all(directory: str | Path, artifacts: list[dict[str, Any]]) -> list[Path]:
    return [write_artifact(directory, artifact) for artifact in artifacts]
