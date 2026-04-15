"""Leaderboard sync: config, identity, and HTTP calls to kennel."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

API_BASE = os.environ.get(
    "MOB_LEADERBOARD_URL",
    "https://mob-production-450c.up.railway.app",
)
HTTP_TIMEOUT = 5.0


# ---------------------------------------------------------------------------
# config


@dataclass
class Config:
    github_user: str
    display_name: str
    machine_fp: str
    enabled: bool = True


def _config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "leaderboard.json"


def load_config() -> Config | None:
    try:
        data = json.loads(_config_path().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return Config(
            github_user=str(data["github_user"]),
            display_name=str(data["display_name"]),
            machine_fp=str(data["machine_fp"]),
            enabled=bool(data.get("enabled", True)),
        )
    except (KeyError, TypeError):
        return None


def save_config(cfg: Config) -> None:
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(cfg), indent=2))
    except OSError:
        pass


def delete_config() -> None:
    try:
        _config_path().unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# identity: local SSH pubkeys cross-referenced with github.com/<user>.keys


def _fp_from_pubkey_line(line: str) -> str | None:
    parts = line.strip().split()
    if len(parts) < 2:
        return None
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (binascii.Error, ValueError):
        return None
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _local_pubkey_fps() -> list[str]:
    ssh_dir = Path.home() / ".ssh"
    fps: list[str] = []
    if not ssh_dir.is_dir():
        return fps
    for p in sorted(ssh_dir.glob("*.pub")):
        try:
            line = p.read_text()
        except OSError:
            continue
        fp = _fp_from_pubkey_line(line)
        if fp:
            fps.append(fp)
    return fps


def _github_pubkey_fps(github_user: str) -> list[str]:
    url = f"https://github.com/{urllib.parse.quote(github_user)}.keys"
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return []
    fps: list[str] = []
    for line in body.splitlines():
        fp = _fp_from_pubkey_line(line)
        if fp:
            fps.append(fp)
    return fps


def find_matching_fp(github_user: str) -> str | None:
    """Return the first local pubkey fingerprint that appears in the user's
    github.com/<user>.keys listing. None if no match (or network failed)."""
    remote = set(_github_pubkey_fps(github_user))
    if not remote:
        return None
    for fp in _local_pubkey_fps():
        if fp in remote:
            return fp
    return None


# ---------------------------------------------------------------------------
# HTTP: submit + fetch


@dataclass
class SubmitResult:
    total_xp: int
    others_xp: int
    rank: int | None


def submit(
    cfg: Config,
    pet: str,
    pet_name: str | None,
    xp: int,
) -> SubmitResult | None:
    payload = json.dumps({
        "github_user": cfg.github_user,
        "machine_fp": cfg.machine_fp,
        "pet": pet,
        "pet_name": pet_name,
        "display_name": cfg.display_name,
        "xp": xp,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/submit",
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    try:
        raw_rank = data.get("rank")
        return SubmitResult(
            total_xp=int(data["total_xp"]),
            others_xp=int(data["others_xp"]),
            rank=None if raw_rank is None else int(raw_rank),
        )
    except (KeyError, TypeError, ValueError):
        return None


@dataclass
class LeaderboardRow:
    rank: int
    display_name: str
    pet: str
    xp: int
    is_me: bool = False


@dataclass
class LeaderboardView:
    top: list[LeaderboardRow]
    me: LeaderboardRow | None


def _row_from_json(data: dict, me_user: str) -> LeaderboardRow | None:
    try:
        return LeaderboardRow(
            rank=int(data["rank"]),
            display_name=str(data["display_name"]),
            pet=str(data["pet"]),
            xp=int(data["xp"]),
            is_me=str(data.get("github_user", "")) == me_user,
        )
    except (KeyError, TypeError, ValueError):
        return None


def fetch_leaderboard(cfg: Config, pet: str) -> LeaderboardView | None:
    qs = urllib.parse.urlencode({"pet": pet, "github_user": cfg.github_user})
    try:
        with urllib.request.urlopen(
            f"{API_BASE}/leaderboard?{qs}", timeout=HTTP_TIMEOUT
        ) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    top_raw = data.get("top")
    if not isinstance(top_raw, list):
        return None
    top: list[LeaderboardRow] = []
    for r in top_raw:
        if isinstance(r, dict):
            row = _row_from_json(r, cfg.github_user)
            if row is not None:
                top.append(row)
    me_raw = data.get("me")
    me = _row_from_json(me_raw, cfg.github_user) if isinstance(me_raw, dict) else None
    if me is not None:
        me.is_me = True
    return LeaderboardView(top=top, me=me)
