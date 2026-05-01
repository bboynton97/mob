# mob

˚ ｡ ⋆ tiny creatures who live at the bottom of your terminal ⋆ ｡ ˚

<img src="docs/running.gif" alt='mob, the cat named "tater"' width="100%">

Only the animal shows up by default. Naming and xp are opt-in via the `/` menu.


```
curl -fsSL https://raw.githubusercontent.com/bboynton97/mob/main/scripts/install.sh | bash
```

run `mob cat` or `mob frog`

## features

- XP - 2xp per command run in any terminal (syncs between devices too)
- gems - in terminal currency! you can gamble it or buy things for your pet
- leaderboard - who's shipping more? your pet will tell all

Sometimes your pet falls asleep! Every command has a 2% chance of waking them up (shh!). Sometimes they get hyper and run around. 

Connect your machines to sync xp between them with some neat [public key trickery](docs/architecture.md). 

### setup

xp tracking reads your shell history via [atuin](https://atuin.sh).

1. In mob, open `/` and pick **Enable xp tracking**.
2. If atuin isn't installed, mob asks to install it. Hit **y** and mob exits, runs the official atuin installer, then relaunches itself with tracking on.
3. **Finish atuin's own setup** in your shell:
   ```
   atuin import auto                  # backfill your existing history
   eval "$(atuin init zsh)"           # or: bash, fish, nu (see atuin docs)
   ```
   The `init` line goes in your shell rc (`~/.zshrc`, `~/.bashrc`, etc.) so atuin captures every new command.
4. Open a fresh shell, run a few commands, and watch the toasts.

Already have atuin set up? Skip step 2. Toggling on is all you need.

<img src="docs/xp.gif" alt="xp syncing via atuin" width="100%">

## contribute a critter

Got an idea for a new animal? Open a PR ♡
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

```
    ∧,,,∧
   (  ̳•·• ̳)
   /    づ♡   thank u for contributing
```

<img src="docs/sleeping.gif" alt="sleeping pet" width="100%">
