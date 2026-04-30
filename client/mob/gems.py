"""Global gems currency persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "gems.json"


def load() -> float:
    try:
        data = json.loads(_path().read_text())
    except (OSError, ValueError):
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    value = data.get("gems")
    if isinstance(value, (int, float)) and value >= 0:
        return round(float(value), 1)
    return 0.0


def save(gems: float) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"gems": round(max(0.0, gems), 1)}, indent=2))
    except OSError:
        pass
