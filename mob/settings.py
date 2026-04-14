"""Small key/value settings store at ~/.config/mob/settings.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "settings.json"


def _load_all() -> dict[str, Any]:
    try:
        data = json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get(key: str, default: Any = None) -> Any:
    return _load_all().get(key, default)


def set(key: str, value: Any) -> None:  # noqa: A001 - deliberately shadowing builtin
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _load_all()
        data[key] = value
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass
