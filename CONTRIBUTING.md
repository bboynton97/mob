# Contributing a New Animal

Want to add a critter to mob? Here's everything you need to know.

## 1. Define the animal in `client/mob/art.py`

Create an `Animal` with a unique name, consistent width, and ASCII poses.

```python
AXOLOTL = Animal(
    name="axolotl",
    width=20,  # widest line across all poses
    behavior=Behavior(
        movement="hop",           # "hop" or "crawl"
    ),
    poses={
        "idle":     r"""...""",
        "blink":    r"""...""",
        "happy":    r"""...""",
        "eating":   r"""...""",
        "eating2":  r"""...""",
        "sleeping": r"""...""",
        "hop":      r"""...""",   # for hoppers
    },
)
```

### Required poses

| Pose | When it's used |
|------|---------------|
| `idle` | Default standing pose |
| `blink` | Brief eye-close, triggered randomly |
| `happy` | Shown when petted |
| `eating` | Chewing frame 1 (alternates with `eating2`) |
| `eating2` | Chewing frame 2 |
| `sleeping` | Asleep / idle timeout |
| `hop` | Mid-air frame (hoppers only) |

### Optional poses

| Pose | Purpose |
|------|---------|
| `sleeping2` | Breathing animation (alternates with `sleeping`) |
| `idle2` | Secondary idle, shown randomly via `secondary_idles` |
| `walk_left` / `walk_left2` | Crawl animation left (crawlers only) |
| `walk_right` / `walk_right2` | Crawl animation right (crawlers only) |

### Rules

- **Every pose must be exactly 4 lines** (pad with blank lines if needed).
- **Width must be consistent** — set `width` to the widest line across all poses.
- Each pose string should start and end with `\n` (raw string, leading newline).

## 2. Choose a movement style

| Style | Behavior | Required poses |
|-------|----------|---------------|
| `"hop"` | Jumps in arcs, lifts off ground | `hop` |
| `"crawl"` | Walks step-by-step, stays grounded | `walk_left`, `walk_right` (+ `2` variants for animation) |

Configure via `Behavior`:

```python
# Hopper (like the frog)
behavior=Behavior(movement="hop")

# Crawler (like the cat)
behavior=Behavior(
    movement="crawl",
    crawl_step_seconds=0.22,      # speed per step
    crawl_distance=(8, 30),       # min/max columns per walk
    secondary_idles=("idle2",),   # optional extra idle poses
    secondary_idle_chance=0.25,
)
```

## 3. Register the animal

Add it to the `ANIMALS` dict at the bottom of `art.py`:

```python
ANIMALS: dict[str, Animal] = {
    a.name: a for a in (FROG, CAT, AXOLOTL)
}
```

That's it — the CLI picks it up automatically via `mob axolotl`.

## 4. Test it

```bash
cd client
uv run mob <your-animal> --dev
```

Dev mode binds extra keys: `s` (toggle sleep), `m` (force move), `r` (nyan).

Check that:
- All poses render without clipping
- Movement looks natural
- Sleep/wake cycle works
- Eating animation alternates correctly
- Width is consistent (no jittering between poses)

## 5. Submit a PR

Open a PR with your changes to `art.py`. Include a screenshot or gif of your critter in action.
