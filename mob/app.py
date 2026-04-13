"""mob — tiny creatures who live at the bottom of your terminal."""

from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Static

from mob.art import POSES
from mob.term_colors import detect_terminal_colors

FROG_WIDTH = 16
HOP_ROOM = 3


class FrogScene(Static):
    """Renders the frog at (x, y_lift) inside a bottom-docked band."""

    x: reactive[int] = reactive(4)
    y_lift: reactive[int] = reactive(0)
    pose: reactive[str] = reactive("idle")

    def render(self) -> str:
        art = POSES[self.pose].strip("\n").split("\n")
        pad = " " * max(0, self.x)
        shifted = [pad + line for line in art]
        top = [""] * max(0, HOP_ROOM - self.y_lift)
        bottom = [""] * max(0, self.y_lift)
        return "\n".join(top + shifted + bottom)


class MobApp(App):
    CSS_PATH = "mob.tcss"

    # textual-ansi leaves the terminal's own background/foreground alone
    theme = "textual-ansi"

    BINDINGS = [
        Binding("f", "feed", show=False),
        Binding("p", "pet", show=False),
        Binding("t", "toy", show=False),
        Binding("s", "sleep", show=False),
        Binding("q", "quit", show=False),
        Binding("ctrl+c", "quit", show=False),
    ]

    def __init__(self, fg: str | None = None, bg: str | None = None) -> None:
        super().__init__()
        self._fg = fg
        self._bg = bg
        self._asleep = False
        self._hopping = False
        self._busy_pose = False
        self._hops_left_in_burst = 0

    @property
    def scene(self) -> FrogScene:
        return self.query_one(FrogScene)

    def compose(self) -> ComposeResult:
        yield FrogScene(id="frog")

    def on_mount(self) -> None:
        if self._bg:
            self.screen.styles.background = self._bg
        if self._fg:
            self.screen.styles.color = self._fg
            self.scene.styles.color = self._fg
        self.set_interval(4.0, self._maybe_blink)
        self._schedule_next_burst()

    # ------------------------------------------------------------------
    # burst scheduling — long sits, clustered hops

    def _schedule_next_burst(self) -> None:
        # skewed distribution: mostly long pauses, occasional short one
        tier = random.choices(
            ["short", "medium", "long", "very_long"],
            weights=[2, 3, 4, 2],
        )[0]
        if tier == "short":
            delay = random.uniform(8, 18)
        elif tier == "medium":
            delay = random.uniform(18, 40)
        elif tier == "long":
            delay = random.uniform(40, 90)
        else:
            delay = random.uniform(90, 180)
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

    # ------------------------------------------------------------------
    # hopping

    def _start_random_hop(self) -> None:
        width = max(FROG_WIDTH, self.size.width)
        max_x = max(0, width - FROG_WIDTH)
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
            # bail on this hop, try to continue burst with the next one
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

    def _run_frames(self, frames: list[tuple[int, int]]) -> None:
        if not frames:
            self._hopping = False
            if not self._asleep and not self._busy_pose:
                self.scene.pose = "idle"
            # short pause before the next hop in the burst
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
        if self._asleep:
            return
        self._flash_pose("eating", 1.4)

    def action_pet(self) -> None:
        if self._asleep:
            return
        self._flash_pose("happy", 1.4)

    def action_toy(self) -> None:
        if self._asleep or self._hopping:
            return
        self._start_random_hop()

    def action_sleep(self) -> None:
        self._asleep = not self._asleep
        self.scene.pose = "sleeping" if self._asleep else "idle"

    # ------------------------------------------------------------------

    def on_resize(self) -> None:
        max_x = max(0, self.size.width - FROG_WIDTH)
        if self.scene.x > max_x:
            self.scene.x = max_x


def main() -> None:
    fg, bg = detect_terminal_colors()
    MobApp(fg=fg, bg=bg).run()


if __name__ == "__main__":
    main()
