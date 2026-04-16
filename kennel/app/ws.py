"""WebSocket sync hub: per-(github_user, pet) rooms with fan-out."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

from app import db


GH_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
FP_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PET_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


@dataclass
class Client:
    ws: WebSocket
    machine_fp: str


@dataclass
class _Rooms:
    by_key: dict[tuple[str, str], set[Client]] = field(default_factory=lambda: defaultdict(set))

    def add(self, user: str, pet: str, client: Client) -> None:
        self.by_key[(user, pet)].add(client)

    def remove(self, user: str, pet: str, client: Client) -> None:
        bucket = self.by_key.get((user, pet))
        if not bucket:
            return
        bucket.discard(client)
        if not bucket:
            self.by_key.pop((user, pet), None)

    def peers(self, user: str, pet: str, exclude: Client) -> list[Client]:
        return [c for c in self.by_key.get((user, pet), ()) if c is not exclude]


rooms = _Rooms()


def valid_params(user: str, fp: str, pet: str) -> bool:
    return bool(GH_RE.match(user) and FP_RE.match(fp) and PET_RE.match(pet))


async def handle(ws: WebSocket, github_user: str, machine_fp: str, pet: str) -> None:
    await ws.accept()
    client = Client(ws=ws, machine_fp=machine_fp)

    async with db.pool().acquire() as conn:
        snapshot = await db.fetch_contributions(conn, github_user, pet)
    await ws.send_json({"type": "snapshot", "contributions": snapshot})

    rooms.add(github_user, pet, client)
    try:
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") != "update":
                continue
            try:
                xp = int(msg.get("xp", 0))
            except (TypeError, ValueError):
                continue
            if xp < 0:
                continue
            async with db.pool().acquire() as conn:
                new_xp = await db.upsert_contribution(
                    conn, github_user, pet, machine_fp, xp
                )
            payload = {
                "type": "peer_update",
                "machine_fp": machine_fp,
                "xp": new_xp,
            }
            for peer in rooms.peers(github_user, pet, exclude=client):
                try:
                    await peer.ws.send_json(payload)
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        rooms.remove(github_user, pet, client)
