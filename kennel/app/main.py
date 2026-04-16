from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from app import db, ws as ws_hub
from app.models import (
    LeaderboardResponse,
    LeaderboardRow,
    SubmitRequest,
    SubmitResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    yield
    await db.close_pool()


app = FastAPI(title="kennel", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.websocket("/sync")
async def sync(
    ws: WebSocket,
    github_user: str,
    machine_fp: str,
    pet: str,
) -> None:
    if not ws_hub.valid_params(github_user, machine_fp, pet):
        await ws.close(code=1008)
        return
    await ws_hub.handle(ws, github_user, machine_fp, pet)


@app.post("/submit", response_model=SubmitResponse)
async def submit(req: SubmitRequest) -> SubmitResponse:
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await db.upsert_contribution(
                conn, req.github_user, req.pet, req.machine_fp, req.xp
            )
            await conn.execute(
                """
                INSERT INTO pets_meta (github_user, pet, pet_name, display_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (github_user, pet)
                DO UPDATE SET pet_name = COALESCE(EXCLUDED.pet_name, pets_meta.pet_name),
                              display_name = EXCLUDED.display_name,
                              updated_at = now()
                """,
                req.github_user, req.pet, req.pet_name, req.display_name,
            )
            total = await conn.fetchval(
                "SELECT COALESCE(SUM(xp), 0)::int FROM contributions "
                "WHERE github_user=$1 AND pet=$2",
                req.github_user, req.pet,
            )
            rank_row = await conn.fetchrow(
                """
                WITH totals AS (
                  SELECT github_user, SUM(xp)::int AS xp
                  FROM contributions WHERE pet=$1
                  GROUP BY github_user
                ),
                ranked AS (
                  SELECT *, RANK() OVER (ORDER BY xp DESC) AS rank FROM totals
                )
                SELECT rank::int AS rank FROM ranked WHERE github_user=$2
                """,
                req.pet, req.github_user,
            )
            rank = int(rank_row["rank"]) if rank_row else None
    return SubmitResponse(
        total_xp=total,
        others_xp=max(0, total - req.xp),
        rank=rank,
    )


@app.get("/leaderboard", response_model=LeaderboardResponse)
async def leaderboard(
    pet: str,
    github_user: str | None = None,
) -> LeaderboardResponse:
    async with db.pool().acquire() as conn:
        rows = await conn.fetch(
            """
            WITH totals AS (
              SELECT c.github_user, c.pet, SUM(c.xp)::int AS xp,
                     m.display_name
              FROM contributions c
              JOIN pets_meta m USING (github_user, pet)
              WHERE c.pet = $1
              GROUP BY c.github_user, c.pet, m.display_name
            ),
            ranked AS (
              SELECT *, RANK() OVER (ORDER BY xp DESC) AS rank FROM totals
            )
            SELECT rank::int AS rank, github_user, display_name, pet, xp
            FROM ranked
            WHERE rank <= 5 OR github_user = $2
            ORDER BY rank
            """,
            pet, github_user or "",
        )
    top: list[LeaderboardRow] = []
    me: LeaderboardRow | None = None
    for r in rows:
        row = LeaderboardRow(
            rank=r["rank"],
            github_user=r["github_user"],
            display_name=r["display_name"],
            pet=r["pet"],
            xp=r["xp"],
        )
        if row.rank <= 5:
            top.append(row)
        if github_user and row.github_user == github_user:
            me = row
    return LeaderboardResponse(top=top, me=me)
