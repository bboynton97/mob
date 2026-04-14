"""Self-update support: check for a newer GitHub release and reinstall."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

REPO = "bboynton97/mob"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "mob" / "update.json"


def current_version() -> str:
    try:
        return version("mob")
    except PackageNotFoundError:
        return "0.0.0"


def _parse(tag: str) -> tuple[int, ...]:
    tag = tag.lstrip("vV")
    parts: list[int] = []
    for chunk in tag.split(".")[:3]:
        try:
            parts.append(int(chunk))
        except ValueError:
            return (0,)
    return tuple(parts)


def fetch_latest_tag(timeout: float = 1.5) -> str | None:
    try:
        with urllib.request.urlopen(LATEST_URL, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    tag = data.get("tag_name") if isinstance(data, dict) else None
    return tag if isinstance(tag, str) and tag else None


def _read_cache() -> dict | None:
    try:
        return json.loads(_cache_path().read_text())
    except (OSError, ValueError):
        return None


def _write_cache(tag: str | None) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"tag": tag, "ts": time.time()}))
    except OSError:
        pass


def check_for_update(use_cache: bool = True) -> str | None:
    """Return the latest tag iff it's newer than the installed version."""
    tag: str | None = None
    if use_cache:
        cache = _read_cache()
        if cache and (time.time() - cache.get("ts", 0)) < CACHE_TTL_SECONDS:
            tag = cache.get("tag")
    if tag is None:
        tag = fetch_latest_tag()
        _write_cache(tag)
    if not tag:
        return None
    return tag if _parse(tag) > _parse(current_version()) else None


def run_update(tag: str | None = None) -> int:
    if tag is None:
        tag = fetch_latest_tag()
    if not tag:
        print("Could not resolve latest release tag.", file=sys.stderr)
        return 1
    source = f"git+https://github.com/{REPO}@{tag}"
    for installer, cmd in (
        ("uv", ["uv", "tool", "install", "--force", source]),
        ("pipx", ["pipx", "install", "--force", source]),
    ):
        try:
            subprocess.run(
                [installer, "--version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        print(f"→ Installing mob {tag} via {installer}…")
        result = subprocess.call(cmd)
        if result == 0:
            _write_cache(tag)
        return result
    print(
        "Need 'uv' or 'pipx' on PATH to self-update.\n"
        "  uv:   https://docs.astral.sh/uv/\n"
        "  pipx: https://pipx.pypa.io/",
        file=sys.stderr,
    )
    return 1
