"""Decoration catalog and purchase persistence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Decoration:
    id: str
    name: str
    cost: int
    art: str
    x_offset: int
    y_offset: int = 0


CATALOG: dict[str, Decoration] = {}


def _register(*decos: Decoration) -> None:
    for d in decos:
        CATALOG[d.id] = d


_register(
    Decoration(
        id="yarn",
        name="Yarn ball",
        cost=15,
        x_offset=10,
        art=r"""
 _
(~)
""",
    ),
    Decoration(
        id="plant",
        name="Potted plant",
        cost=25,
        x_offset=2,
        art=r"""
 \|/
 (·)
  |
""",
    ),
    Decoration(
        id="fish",
        name="Fishbowl",
        cost=40,
        x_offset=30,
        art=r"""
 .--.
( o )
 '--'
""",
    ),
    Decoration(
        id="bed",
        name="Pet bed",
        cost=50,
        x_offset=18,
        art=r"""
.______.
|      | z
`------'
""",
    ),
)


def _path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "decorations.json"


def _load_all() -> dict:
    try:
        data = json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_purchased() -> list[str]:
    data = _load_all()
    purchased = data.get("purchased", [])
    return [x for x in purchased if isinstance(x, str) and x in CATALOG]


def load_equipped() -> list[str]:
    data = _load_all()
    equipped = data.get("equipped", [])
    purchased = set(data.get("purchased", []))
    return [x for x in equipped if isinstance(x, str) and x in CATALOG and x in purchased]


def save_purchase(decoration_id: str) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _load_all()
        purchased = data.get("purchased", [])
        if decoration_id not in purchased:
            purchased.append(decoration_id)
        data["purchased"] = purchased
        equipped = data.get("equipped", [])
        if decoration_id not in equipped:
            equipped.append(decoration_id)
        data["equipped"] = equipped
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass


def toggle_equip(decoration_id: str) -> bool:
    """Toggle equip state. Returns new equipped state."""
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _load_all()
        equipped = data.get("equipped", [])
        if decoration_id in equipped:
            equipped.remove(decoration_id)
            now_equipped = False
        else:
            equipped.append(decoration_id)
            now_equipped = True
        data["equipped"] = equipped
        path.write_text(json.dumps(data, indent=2))
        return now_equipped
    except OSError:
        return False
