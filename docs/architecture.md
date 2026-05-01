# architecture

## identity: ssh keys instead of auth

mob doesn't have its own auth. instead, it piggybacks on github's public ssh keys.

when you join the leaderboard, mob asks for your github username. then it:

1. fetches `https://github.com/<you>.keys` (github serves this publicly for everyone)
2. reads your local ssh public keys from `~/.ssh/*.pub`
3. hashes both sides to sha-256 fingerprints and looks for a match

if a local key matches a github key, you're verified as that user. the matching fingerprint also doubles as a per-machine id (`machine_fp`), since different machines have different keys.

no passwords, no tokens, no oauth. if you have an ssh key on github, you're already "logged in." the tradeoff is that mob isn't proving you can sign with the key, it just checks you have it. fine for a pet xp leaderboard, not fine for a bank.

## xp syncing

xp syncs through two channels: http for durability, websocket for real-time.

each machine's xp is stored as a separate row: `(github_user, pet, machine_fp) -> xp`. a user's total is the sum across machines. xp only goes up (server uses `GREATEST` on upsert).

**http**: on launch and every 60s of activity, the client posts to `/submit`. server upserts, sums the total, returns `{total_xp, others_xp, rank}`. `others_xp` is xp from your other machines so the client can show an accurate total.

**websocket**: for live cross-machine updates. client connects to `/sync`, server sends a snapshot of all machine contributions, then fans out `peer_update` messages whenever another machine in the same `(user, pet)` room sends new xp. exponential backoff on disconnect (1s to 30s). on reconnect, server re-sends a full snapshot to self-heal.

two channels because the websocket gives instant feedback (laptop sees desktop earning xp) and http is the fallback if it drops. `GREATEST` makes both idempotent so nothing conflicts.
