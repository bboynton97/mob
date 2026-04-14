"""Per-pet XP persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "xp.json"


def load(animal: str) -> int:
    try:
        data = json.loads(_path().read_text())
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    value = data.get(animal)
    return value if isinstance(value, int) and value >= 0 else 0


def save(animal: str, xp: int) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        data[animal] = max(0, int(xp))
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass
