# mob

Tiny creatures who live at the bottom of your terminal.

![mob — the cat, named "tater"](docs/walk.gif)

Only the animal appears by default — everything below (naming, XP, updates) is opt-in via the `/` menu.

## Install

```
curl -fsSL https://raw.githubusercontent.com/bboynton97/mob/main/scripts/install.sh | bash
```

## Use

```
mob frog    # or: cat
```

<!-- GIF: side-by-side of frog and cat -->

## Keys

| key | does |
| --- | --- |
| `f` | feed (chew chew ♥) |
| `p` | pet (♥) |
| `t` | toss a toy |
| `s` | sleep / wake |
| `/` | command menu (name your pet, etc.) |
| `q` | quit |

<!-- GIF: feeding the cat, hearts drifting up -->

## XP

Your pet earns 2 xp for every successful shell command. Total xp lives top-left, and each command floats a `+2 xp` toast above your pet.

### Setup

XP tracking reads your shell history via [atuin](https://atuin.sh).

1. In mob, open `/` and pick **Enable xp tracking**.
2. If atuin isn't installed, mob asks to install it. Hit **y** — mob exits, runs the official atuin installer, then relaunches itself with tracking on.
3. **Finish atuin's own setup** in your shell:
   ```
   atuin import auto                  # backfill your existing history
   eval "$(atuin init zsh)"           # or: bash, fish, nu — see atuin docs
   ```
   The `init` line goes in your shell rc (`~/.zshrc`, `~/.bashrc`, etc.) so atuin captures every new command.
4. Open a fresh shell, run a few commands, and watch the toasts.

Already have atuin set up? Skip step 2 — toggling on is all you need.

![xp syncing via atuin](docs/xp.gif)

## Name your pet

Open `/` → "Give pet a name". The name persists across sessions.

<!-- GIF: naming the cat "tater" -->

## Update

When a new version is out, an "Update mob → vX.Y.Z" entry shows up in `/`. Pick it and mob reinstalls itself.

![sleeping pet](docs/sleep.gif)
