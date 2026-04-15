"""mob — tiny creatures who live at the bottom of your terminal."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from mob import leaderboard, settings, xp as xp_store
from mob.art import ANIMALS, Animal
from mob.atuin import AtuinPoller, CommandEvent, is_available as atuin_available
from mob.term_colors import detect_terminal_colors
from mob.update import check_for_update, run_update

XP_PER_COMMAND = 2


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return None


def contrast_shift(fg_hex: str, bg_hex: str | None, amount: float = 0.35) -> str:
    """Nudge fg toward bg so it reads as a muted version of the mob color."""
    fg = _hex_to_rgb(fg_hex)
    if fg is None:
        return fg_hex
    bg = _hex_to_rgb(bg_hex) if bg_hex else (0, 0, 0)
    shifted = [
        max(0, min(255, int(round(f + (b - f) * amount))))
        for f, b in zip(fg, bg)
    ]
    return "#{:02x}{:02x}{:02x}".format(*shifted)


def format_xp(xp: int) -> str:
    for threshold, suffix in ((1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")):
        if xp >= threshold:
            value = xp / threshold
            return f"{value:.1f}{suffix}" if value < 10 else f"{int(value)}{suffix}"
    return str(xp)

HOP_ROOM = 3


def _state_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "mob" / "pets.json"


def _load_pet_name(animal_name: str) -> str | None:
    try:
        data = json.loads(_state_path().read_text())
    except (OSError, ValueError):
        return None
    value = data.get(animal_name) if isinstance(data, dict) else None
    return value if isinstance(value, str) and value else None


def _save_pet_name(animal_name: str, name: str | None) -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        if name:
            data[animal_name] = name
        else:
            data.pop(animal_name, None)
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass


class CreatureScene(Static):
    """Renders the creature at absolute (x, y), with optional hop lift."""

    x: reactive[int] = reactive(4)
    y: reactive[int] = reactive(0)
    y_lift: reactive[int] = reactive(0)
    pose: reactive[str] = reactive("idle")
    heart_frame: reactive[int] = reactive(-1)  # -1 = hearts hidden
    toasts: reactive[tuple[tuple[str, int], ...]] = reactive(())

    HEART_TOTAL = 16
    TOAST_TOTAL = 10
    # (dx from mob's left edge, dy above mob's top line)
    HEART_OFFSETS = ((2, 1), (6, 2), (4, 3))

    def __init__(self, animal: Animal, **kwargs) -> None:
        super().__init__(**kwargs)
        self.animal = animal

    def render(self) -> str:
        art = self.animal.poses[self.pose].strip("\n").split("\n")
        pad = " " * max(0, self.x)
        shifted = [pad + line for line in art]
        top_count = max(0, self.y - self.y_lift)
        lines = [""] * top_count + shifted

        if self.heart_frame >= 0:
            rows: dict[int, list[int]] = {}
            for dx, dy in self.HEART_OFFSETS:
                hy = self.y - self.y_lift - dy - self.heart_frame
                hx = self.x + dx
                if hy < 0 or hx < 0:
                    continue
                rows.setdefault(hy, []).append(hx)
            for row_y, xs in rows.items():
                xs.sort()
                overlay = ""
                cursor = 0
                for x in xs:
                    overlay += " " * max(0, x - cursor) + "[#ff69b4]♥[/]"
                    cursor = x + 1
                while len(lines) <= row_y:
                    lines.append("")
                # Heart rows sit above the mob's top line, which is always
                # blank in the base render — safe to overwrite.
                lines[row_y] = overlay

        for text, frame in self.toasts:
            if not text:
                continue
            toast_y = self.y - self.y_lift - 1 - frame
            toast_x = self.x + 1
            if toast_y < 0 or toast_x < 0:
                continue
            while len(lines) <= toast_y:
                lines.append("")
            padding = " " * toast_x
            lines[toast_y] = padding + f"[bold]{text}[/]"
        return "\n".join(lines)


class ConfirmScreen(ModalScreen[bool]):
    """Minimal yes/no modal. Returns True if yes, False otherwise."""

    BINDINGS = [
        Binding("y", "choose(True)", show=False),
        Binding("n", "choose(False)", show=False),
        Binding("escape", "choose(False)", show=False),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self._message, id="confirm-text")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes (y)", id="confirm-yes", variant="primary")
                yield Button("No (n)", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_choose(self, value: bool) -> None:
        self.dismiss(value)


class MobApp(App):
    CSS_PATH = "mob.tcss"

    # textual-ansi leaves the terminal's own background/foreground alone
    theme = "textual-ansi"

    BINDINGS = [
        Binding("f", "feed", show=False),
        Binding("p", "pet", show=False),
        Binding("t", "toy", show=False),
        Binding("s", "sleep", show=False),
        Binding("slash", "open_commands", show=False),
        Binding("escape", "close_commands", show=False),
        Binding("q", "quit", show=False),
        Binding("ctrl+c", "quit", show=False),
    ]

    def __init__(
        self,
        animal: Animal,
        fg: str | None = None,
        bg: str | None = None,
    ) -> None:
        super().__init__()
        self.animal = animal
        self._fg = fg
        self._bg = bg
        self._asleep = False
        self._hopping = False
        self._busy_pose = False
        self._hops_left_in_burst = 0
        self._pet_name: str | None = _load_pet_name(animal.name)
        self._update_tag: str | None = None
        self._pending_update_tag: str | None = None
        self._xp: int = xp_store.load(animal.name)
        self._atuin: AtuinPoller | None = None
        self._xp_enabled: bool = bool(settings.get("xp_enabled", True))
        self._toast_running: bool = False
        self._pending_atuin_install: bool = False
        self._leaderboard_cfg: leaderboard.Config | None = leaderboard.load_config()
        self._join_stage: str | None = None
        self._join_gh_user: str = ""
        self._join_matched_fp: str = ""
        self._submit_timer: Timer | None = None

    @property
    def scene(self) -> CreatureScene:
        return self.query_one(CreatureScene)

    def compose(self) -> ComposeResult:
        yield CreatureScene(self.animal, id="creature")
        with Container(id="hud"):
            yield Label("", id="xp-badge")
            with Container(id="hud-right"):
                yield Label("", id="name-badge")
                yield Label("", id="update-badge")
                yield ListView(
                    ListItem(Label("Give pet a name"), id="cmd-rename"),
                    ListItem(Label("Feed"), id="cmd-feed"),
                    ListItem(Label("Pet"), id="cmd-pet"),
                    ListItem(Label(""), id="cmd-xp-toggle"),
                    ListItem(Label(""), id="cmd-leaderboard-join"),
                    ListItem(Label(""), id="cmd-update"),
                    id="cmd-list",
                )
                yield Input(placeholder="name your pet…", id="name-input")

    def on_mount(self) -> None:
        self.title = f"mob — {self.animal.name}"
        if self._bg:
            self.screen.styles.background = self._bg
        if self._fg:
            self.screen.styles.color = self._fg
            self.scene.styles.color = self._fg
            for selector in (
                "#name-badge",
                "#update-badge",
                "#cmd-list",
                "#name-input",
            ):
                self.query_one(selector).styles.color = self._fg
            self.query_one("#cmd-list", ListView).styles.border = (
                "round",
                self._fg,
            )
            for label in self.query("#cmd-list Label").results(Label):
                label.styles.color = self._fg
            self.query_one("#name-input", Input).styles.color = self._fg
        xp_base = self._fg or "#cccccc"
        self.query_one("#xp-badge", Label).styles.color = contrast_shift(
            xp_base, self._bg
        )
        self.set_interval(8.0, self._maybe_blink)
        if self.animal.behavior.secondary_idles:
            self.set_interval(14.0, self._maybe_secondary_idle)
        self.set_interval(60.0, self._maybe_sleep)
        if "sleeping2" in self.animal.poses:
            self.set_interval(1.2, self._breathe_sleep)
        self._schedule_next_burst()
        self.query_one("#cmd-list", ListView).display = False
        self.query_one("#name-input", Input).display = False
        self.query_one("#cmd-update", ListItem).display = False
        self._refresh_hud()
        self._refresh_xp_badge()
        self._refresh_xp_toggle_label()
        self._refresh_leaderboard_menu()
        self.run_worker(self._check_updates_worker, thread=True, exclusive=True)
        self._start_atuin_if_enabled()
        if self._leaderboard_cfg and self._leaderboard_cfg.enabled:
            self.run_worker(self._submit_xp_worker, thread=True, exclusive=False)

    def _start_atuin_if_enabled(self) -> None:
        if not self._xp_enabled:
            return
        if self._atuin is not None:
            return
        if not atuin_available():
            return
        self._atuin = AtuinPoller(on_event=self._on_atuin_event)
        self._atuin.start()

    def _stop_atuin(self) -> None:
        if self._atuin is not None:
            self._atuin.stop()
            self._atuin = None

    def _apply_xp_toggle(self, enabled: bool) -> None:
        self._xp_enabled = enabled
        settings.set("xp_enabled", enabled)
        if enabled:
            self._start_atuin_if_enabled()
        else:
            self._stop_atuin()
        self._refresh_xp_toggle_label()
        self._refresh_xp_badge()

    def _after_atuin_confirm(self, install: bool) -> None:
        if not install:
            return
        self._pending_atuin_install = True
        self.exit()

    def _refresh_xp_toggle_label(self) -> None:
        item = self.query_one("#cmd-xp-toggle", ListItem)
        label = item.query_one(Label)
        label.update("Disable xp tracking" if self._xp_enabled else "Enable xp tracking")
        if self._fg:
            label.styles.color = self._fg

    def _check_updates_worker(self) -> None:
        tag = check_for_update()
        if tag:
            self.call_from_thread(self._on_update_available, tag)

    def _refresh_xp_badge(self) -> None:
        badge = self.query_one("#xp-badge", Label)
        badge.update(f"{format_xp(self._xp)} xp")
        badge.display = self._xp_enabled

    def _on_atuin_event(self, event: CommandEvent) -> None:
        # Called from the poller thread — bounce to the UI thread.
        if event.exit_code != 0 or not self._xp_enabled:
            return
        try:
            self.call_from_thread(self._handle_command_event)
        except RuntimeError:
            # App already shutting down; drop silently.
            pass

    def _handle_command_event(self) -> None:
        self._award_xp(XP_PER_COMMAND)
        if self._asleep and random.random() < 0.05:
            self._asleep = False
            if not self._busy_pose and not self._hopping:
                self.scene.pose = "idle"

    def _award_xp(self, amount: int) -> None:
        self._xp += amount
        xp_store.save(self.animal.name, self._xp)
        self._refresh_xp_badge()
        self._show_toast(f"+{amount} xp")
        self._schedule_submit()

    def _show_toast(self, text: str) -> None:
        existing = list(self.scene.toasts)
        # If another toast is still at frame 0 (arrived within a tick of this one),
        # bump it by one so they don't render on top of each other.
        existing = [(t, max(f, 1)) if f == 0 else (t, f) for t, f in existing]
        existing.append((text, 0))
        self.scene.toasts = tuple(existing)
        if not self._toast_running:
            self._toast_running = True
            self.set_timer(0.28, self._toast_tick)

    def _toast_tick(self) -> None:
        advanced = [
            (t, f + 1) for t, f in self.scene.toasts if f + 1 < CreatureScene.TOAST_TOTAL
        ]
        self.scene.toasts = tuple(advanced)
        if advanced:
            self.set_timer(0.28, self._toast_tick)
        else:
            self._toast_running = False

    def _on_update_available(self, tag: str) -> None:
        self._update_tag = tag
        item = self.query_one("#cmd-update", ListItem)
        item.query_one(Label).update(f"Update mob → {tag}")
        item.display = True
        if self._fg:
            item.query_one(Label).styles.color = self._fg
        self._refresh_hud()

    def _art_height(self) -> int:
        return len(self.animal.poses["idle"].strip("\n").split("\n"))

    def _max_y(self) -> int:
        return max(HOP_ROOM, self.size.height - self._art_height())

    # ------------------------------------------------------------------
    # burst scheduling — long sits, clustered hops

    def _schedule_next_burst(self) -> None:
        tier = random.choices(
            ["short", "medium", "long", "very_long"],
            weights=[1, 3, 4, 3],
        )[0]
        if tier == "short":
            delay = random.uniform(15, 30)
        elif tier == "medium":
            delay = random.uniform(30, 70)
        elif tier == "long":
            delay = random.uniform(70, 150)
        else:
            delay = random.uniform(150, 300)
        self.set_timer(delay, self._begin_burst)

    def _begin_burst(self) -> None:
        if self._asleep:
            self._schedule_next_burst()
            return
        self._hops_left_in_burst = random.randint(2, 3)
        self._continue_burst()

    def _continue_burst(self) -> None:
        if self._hops_left_in_burst <= 0:
            self._schedule_next_burst()
            return
        if self._asleep or self._busy_pose:
            self.set_timer(1.0, self._continue_burst)
            return
        self._hops_left_in_burst -= 1
        if self.animal.behavior.movement == "crawl":
            self._start_random_crawl()
        else:
            self._start_random_hop()

    # ------------------------------------------------------------------
    # idle

    def _maybe_blink(self) -> None:
        if self._asleep or self._hopping or self._busy_pose:
            return
        if self.scene.pose != "idle" or random.random() > 0.5:
            return
        self.scene.pose = "blink"
        self.set_timer(0.18, lambda: setattr(self.scene, "pose", "idle"))

    def _maybe_sleep(self) -> None:
        if self._asleep or self._hopping or self._busy_pose:
            return
        if self.scene.pose not in ("idle", "idle2"):
            return
        if random.random() > 0.03:
            return
        self._asleep = True
        self.scene.pose = "sleeping"
        self.set_timer(random.uniform(60.0, 300.0), self._auto_wake)

    def _breathe_sleep(self) -> None:
        if not self._asleep or self._busy_pose or self._hopping:
            return
        if self.scene.pose == "sleeping":
            self.scene.pose = "sleeping2"
        elif self.scene.pose == "sleeping2":
            self.scene.pose = "sleeping"

    def _auto_wake(self) -> None:
        if not self._asleep:
            return
        self._asleep = False
        if not self._busy_pose and not self._hopping:
            self.scene.pose = "idle"

    def _maybe_secondary_idle(self) -> None:
        if self._asleep or self._hopping or self._busy_pose:
            return
        if self.scene.pose != "idle":
            return
        behavior = self.animal.behavior
        if random.random() > behavior.secondary_idle_chance:
            return
        pose = random.choice(behavior.secondary_idles)
        if pose not in self.animal.poses:
            return
        self.scene.pose = pose

    # ------------------------------------------------------------------
    # hopping

    def _start_random_hop(self) -> None:
        width = max(self.animal.width, self.size.width)
        max_x = max(0, width - self.animal.width)
        size_choice = random.choices(
            ["small", "medium", "big"], weights=[3, 3, 2]
        )[0]
        if size_choice == "small":
            distance = random.randint(3, 8)
        elif size_choice == "medium":
            distance = random.randint(8, 20)
        else:
            distance = random.randint(18, max(20, max_x // 2 or 20))

        direction = random.choice([-1, 1])
        target = self.scene.x + direction * distance
        if target < 0 or target > max_x:
            target = self.scene.x - direction * distance
        target = max(0, min(max_x, target))

        if target == self.scene.x:
            self.call_after_refresh(self._continue_burst)
            return
        self._play_hop(target)

    def _play_hop(self, target_x: int) -> None:
        start_x = self.scene.x
        dx = target_x - start_x
        frames = [
            (start_x + round(dx * 0.25), 1),
            (start_x + round(dx * 0.55), 2),
            (start_x + round(dx * 0.85), 1),
            (target_x, 0),
        ]
        self._hopping = True
        self.scene.pose = "hop"
        self._run_frames(frames)

    # ------------------------------------------------------------------
    # crawling (cats and anything else that shouldn't launch itself skyward)

    def _start_random_crawl(self) -> None:
        width = max(self.animal.width, self.size.width)
        max_x = max(0, width - self.animal.width)
        max_y = self._max_y()

        lo, hi = self.animal.behavior.crawl_distance
        distance = random.randint(lo, hi)
        direction = random.choice([-1, 1])
        target_x = self.scene.x + direction * distance
        if target_x < 0 or target_x > max_x:
            direction = -direction
            target_x = self.scene.x + direction * distance
        target_x = max(0, min(max_x, target_x))

        # Vertical target: usually a modest drift, occasionally a bigger
        # climb or drop so the cat explores the full terminal over time.
        if random.random() < 0.25:
            vertical_range = max_y
        else:
            vertical_range = 6
        target_y = self.scene.y + random.randint(-vertical_range, vertical_range)
        target_y = max(HOP_ROOM, min(max_y, target_y))

        if target_x == self.scene.x and target_y == self.scene.y:
            self.call_after_refresh(self._continue_burst)
            return
        pose = "walk_left" if direction < 0 else "walk_right"
        if pose not in self.animal.poses:
            pose = "idle"
        self._hopping = True
        self.scene.pose = pose
        step_x = 1 if direction > 0 else -1
        self._crawl_step(target_x, target_y, step_x)

    def _crawl_step(self, target_x: int, target_y: int, step_x: int) -> None:
        arrived = self.scene.x == target_x and self.scene.y == target_y
        if self._asleep or arrived:
            self._hopping = False
            if not self._asleep and not self._busy_pose:
                self.scene.pose = "idle"
            self.set_timer(random.uniform(0.8, 2.0), self._continue_burst)
            return

        if self.scene.x != target_x:
            self.scene.x += step_x

        # Alternate between the two walk frames for a little animation.
        current = self.scene.pose
        if current in ("walk_left", "walk_left2"):
            alt = "walk_left2" if current == "walk_left" else "walk_left"
            if alt in self.animal.poses:
                self.scene.pose = alt
        elif current in ("walk_right", "walk_right2"):
            alt = "walk_right2" if current == "walk_right" else "walk_right"
            if alt in self.animal.poses:
                self.scene.pose = alt

        # Move y probabilistically, weighted by how much vertical distance
        # remains relative to horizontal — keeps the path roughly diagonal.
        if self.scene.y != target_y:
            remaining_x = max(1, abs(target_x - self.scene.x))
            remaining_y = abs(target_y - self.scene.y)
            if remaining_y >= remaining_x or random.random() < remaining_y / remaining_x:
                self.scene.y += 1 if target_y > self.scene.y else -1

        base = self.animal.behavior.crawl_step_seconds
        # Wider jitter + occasional pause. Lower bound is much smaller so
        # the cat can briefly sprint when it commits to a direction.
        if random.random() < 0.08:
            delay = base * random.uniform(2.5, 5.0)
        else:
            delay = base * random.uniform(0.25, 1.6)
        self.set_timer(
            delay, lambda: self._crawl_step(target_x, target_y, step_x)
        )

    def _run_frames(self, frames: list[tuple[int, int]]) -> None:
        if not frames:
            self._hopping = False
            if not self._asleep and not self._busy_pose:
                self.scene.pose = "idle"
            self.set_timer(random.uniform(0.25, 0.8), self._continue_burst)
            return
        x, y = frames[0]
        self.scene.x = x
        self.scene.y_lift = y
        self.set_timer(0.12, lambda: self._run_frames(frames[1:]))

    # ------------------------------------------------------------------
    # interactions

    def _flash_pose(self, pose: str, seconds: float = 1.2) -> None:
        if self._hopping:
            return
        self._busy_pose = True
        self.scene.pose = pose

        def restore() -> None:
            self._busy_pose = False
            self.scene.pose = "sleeping" if self._asleep else "idle"

        self.set_timer(seconds, restore)

    def action_feed(self) -> None:
        if self._asleep or self._hopping or self._busy_pose:
            return
        self._busy_pose = True
        self._chew_ticks_left = 6  # 6 * 0.28s ≈ 1.7s total
        self.scene.pose = "eating"
        self.set_timer(0.28, self._chew_tick)

    def _chew_tick(self) -> None:
        if self._chew_ticks_left <= 0:
            self._busy_pose = False
            self.scene.pose = "sleeping" if self._asleep else "idle"
            self._play_hearts()
            return
        self._chew_ticks_left -= 1
        current = self.scene.pose
        nxt = "eating2" if current == "eating" else "eating"
        if nxt not in self.animal.poses:
            nxt = "eating"
        self.scene.pose = nxt
        self.set_timer(0.28, self._chew_tick)

    def _play_hearts(self) -> None:
        self.scene.heart_frame = 0
        self._heart_tick()

    def _heart_tick(self) -> None:
        if self.scene.heart_frame >= CreatureScene.HEART_TOTAL:
            self.scene.heart_frame = -1
            return
        self.scene.heart_frame += 1
        self.set_timer(0.28, self._heart_tick)

    def action_pet(self) -> None:
        if self._asleep:
            return
        self._flash_pose("happy", 1.4)
        self._play_hearts()

    def action_toy(self) -> None:
        if self._asleep or self._hopping:
            return
        if self.animal.behavior.movement == "crawl":
            self._start_random_crawl()
        else:
            self._start_random_hop()

    def action_sleep(self) -> None:
        self._asleep = not self._asleep
        self.scene.pose = "sleeping" if self._asleep else "idle"

    # ------------------------------------------------------------------
    # HUD / command palette

    def _refresh_hud(self) -> None:
        badge = self.query_one("#name-badge", Label)
        update_badge = self.query_one("#update-badge", Label)
        cmd_list = self.query_one("#cmd-list", ListView)
        name_input = self.query_one("#name-input", Input)
        hud_open = cmd_list.display or name_input.display
        badge.update(self._pet_name or "")
        badge.display = bool(self._pet_name) and not hud_open
        if self._update_tag:
            update_badge.update(f"update {self._update_tag} · mob update")
        update_badge.display = bool(self._update_tag) and not hud_open

    def action_open_commands(self) -> None:
        cmd_list = self.query_one("#cmd-list", ListView)
        name_input = self.query_one("#name-input", Input)
        name_input.display = False
        cmd_list.display = True
        cmd_list.index = 0
        self._refresh_hud()
        cmd_list.focus()

    def action_close_commands(self) -> None:
        self.query_one("#cmd-list", ListView).display = False
        self.query_one("#name-input", Input).display = False
        self._refresh_hud()
        self.set_focus(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None:
            return
        if event.item.id == "cmd-rename":
            self.query_one("#cmd-list", ListView).display = False
            name_input = self.query_one("#name-input", Input)
            name_input.placeholder = "name your pet…"
            name_input.value = ""
            name_input.display = True
            self._refresh_hud()
            name_input.focus()
        elif event.item.id == "cmd-feed":
            self.action_close_commands()
            self.action_feed()
        elif event.item.id == "cmd-pet":
            self.action_close_commands()
            self.action_pet()
        elif event.item.id == "cmd-xp-toggle":
            self.action_close_commands()
            if not self._xp_enabled and not atuin_available():
                self.push_screen(
                    ConfirmScreen(
                        "xp tracking needs atuin, which isn't installed.\n"
                        "Install it now from https://atuin.sh?"
                    ),
                    self._after_atuin_confirm,
                )
                return
            self._apply_xp_toggle(not self._xp_enabled)
        elif event.item.id == "cmd-leaderboard-join":
            self.action_close_commands()
            if self._leaderboard_cfg:
                self.push_screen(
                    ConfirmScreen("Stop syncing XP to the leaderboard?"),
                    self._after_leave_confirm,
                )
            else:
                self._start_join_flow()
        elif event.item.id == "cmd-update":
            self._pending_update_tag = self._update_tag
            self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "name-input":
            return
        value = event.value.strip()
        event.input.display = False
        self._refresh_hud()
        self.set_focus(None)
        stage = self._join_stage
        if stage == "gh_user":
            if not value:
                self._join_stage = None
                return
            self._show_toast("checking github…")
            gh_user = value
            self.run_worker(
                lambda: self._verify_gh_user_worker(gh_user),
                thread=True,
                exclusive=True,
            )
            return
        if stage == "display_name":
            self._join_stage = None
            if not value:
                return
            self._complete_join(value)
            return
        self._pet_name = value or None
        _save_pet_name(self.animal.name, self._pet_name)

    # ------------------------------------------------------------------
    # leaderboard

    def _refresh_leaderboard_menu(self) -> None:
        item = self.query_one("#cmd-leaderboard-join", ListItem)
        label = item.query_one(Label)
        label.update(
            "Leave leaderboard" if self._leaderboard_cfg else "Join leaderboard"
        )
        if self._fg:
            label.styles.color = self._fg

    def _start_join_flow(self) -> None:
        self._join_stage = "gh_user"
        self.query_one("#cmd-list", ListView).display = False
        name_input = self.query_one("#name-input", Input)
        name_input.placeholder = "github username…"
        name_input.value = ""
        name_input.display = True
        self._refresh_hud()
        name_input.focus()

    def _ask_display_name(self) -> None:
        self._join_stage = "display_name"
        name_input = self.query_one("#name-input", Input)
        name_input.placeholder = "display name…"
        name_input.value = ""
        name_input.display = True
        self._refresh_hud()
        name_input.focus()

    def _verify_gh_user_worker(self, gh_user: str) -> None:
        fp = leaderboard.find_matching_fp(gh_user)
        try:
            self.call_from_thread(self._on_gh_verify_result, gh_user, fp)
        except RuntimeError:
            pass

    def _on_gh_verify_result(self, gh_user: str, fp: str | None) -> None:
        if fp is None:
            self._show_toast("no matching ssh key on github")
            self._join_stage = None
            return
        self._join_gh_user = gh_user
        self._join_matched_fp = fp
        self._ask_display_name()

    def _complete_join(self, display_name: str) -> None:
        cfg = leaderboard.Config(
            github_user=self._join_gh_user,
            display_name=display_name,
            machine_fp=self._join_matched_fp,
        )
        leaderboard.save_config(cfg)
        self._leaderboard_cfg = cfg
        self._refresh_leaderboard_menu()
        self._show_toast("joined the leaderboard")
        self.run_worker(self._submit_xp_worker, thread=True, exclusive=False)

    def _after_leave_confirm(self, confirmed: bool) -> None:
        if not confirmed:
            return
        leaderboard.delete_config()
        self._leaderboard_cfg = None
        self._refresh_leaderboard_menu()
        self._show_toast("left the leaderboard")

    def _submit_xp_worker(self) -> None:
        cfg = self._leaderboard_cfg
        if cfg is None or not cfg.enabled:
            return
        leaderboard.submit(cfg, self.animal.name, self._pet_name, self._xp)

    def _schedule_submit(self) -> None:
        cfg = self._leaderboard_cfg
        if cfg is None or not cfg.enabled:
            return
        if self._submit_timer is not None:
            self._submit_timer.stop()
        self._submit_timer = self.set_timer(60.0, self._flush_submit)

    def _flush_submit(self) -> None:
        self._submit_timer = None
        self.run_worker(self._submit_xp_worker, thread=True, exclusive=False)

    # ------------------------------------------------------------------

    def on_unmount(self) -> None:
        if self._atuin is not None:
            self._atuin.stop()
        if self._submit_timer is not None:
            self._submit_timer.stop()
            self._submit_timer = None

    def on_resize(self) -> None:
        max_x = max(0, self.size.width - self.animal.width)
        if self.scene.x > max_x:
            self.scene.x = max_x
        max_y = self._max_y()
        # Hoppers sit on the floor; crawlers keep their current row, clamped.
        if self.animal.behavior.movement == "hop" or self.scene.y == 0:
            self.scene.y = max_y
        else:
            self.scene.y = min(max_y, max(HOP_ROOM, self.scene.y))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        sys.exit(run_update())

    parser = argparse.ArgumentParser(prog="mob")
    parser.add_argument(
        "animal",
        nargs="?",
        default="frog",
        choices=sorted(ANIMALS),
        help="which critter to summon (default: frog)",
    )
    args = parser.parse_args()

    fg, bg = detect_terminal_colors()
    app = MobApp(animal=ANIMALS[args.animal], fg=fg, bg=bg)
    app.run()
    if app._pending_update_tag:
        sys.exit(run_update(app._pending_update_tag))
    if app._pending_atuin_install:
        rc = _install_atuin()
        if rc == 0:
            # Pre-enable xp tracking so the relaunched session picks it up.
            settings.set("xp_enabled", True)
            print("→ Relaunching mob…")
            os.execvp(sys.argv[0], sys.argv)
        sys.exit(rc)


def _install_atuin() -> int:
    """Run the official atuin installer from setup.atuin.sh."""
    print("→ Installing atuin from https://setup.atuin.sh")
    installer = "curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh"
    rc = subprocess.call(installer, shell=True)
    if rc == 0:
        print()
        print("✓ atuin installed.")
        print("  If you want sync across machines, run: atuin register")
        print("  To import existing shell history:      atuin import auto")
    else:
        print("✖ atuin installer exited with code", rc, file=sys.stderr)
    return rc


if __name__ == "__main__":
    main()
