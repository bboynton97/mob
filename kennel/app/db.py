from __future__ import annotations

import os
from pathlib import Path

import asyncpg

_pool: asyncpg.Pool | None = None

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        await _run_migrations(_pool)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("db pool not initialized")
    return _pool


async def _run_migrations(p: asyncpg.Pool) -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        async with p.acquire() as conn:
            await conn.execute(path.read_text())
