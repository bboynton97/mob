# kennel

Leaderboard + sync backend for mob.

## Dev

```
export DATABASE_URL=postgres://localhost/kennel
uv run uvicorn app.main:app --reload
```

## Endpoints

- `POST /submit` — upsert a machine's XP contribution for a pet. Server applies `GREATEST` so values never decrease. Returns `{total_xp, others_xp, rank}`.
- `GET /leaderboard?pet=cat&github_user=X` — top 5 totals for that pet species plus the caller's own row if outside the top.
- `GET /health` — Railway healthcheck.

## Deploy (Railway)

1. Create a Railway project, add a Postgres plugin.
2. Create a service, set **Root Directory** to `kennel`.
3. `DATABASE_URL` is wired automatically by the Postgres plugin.
4. Dockerfile builds; `/health` is the healthcheck.

Migrations run on startup and are idempotent (`CREATE TABLE IF NOT EXISTS`).
