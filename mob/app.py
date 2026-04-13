"""mob — tiny creatures who live at the bottom of your terminal."""

from __future__ import annotations

import argparse
import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Static

from mob.art import ANIMALS, Animal
from mob.term_colors import detect_terminal_colors

HOP_ROOM = 3


class CreatureScene(Static):
    """Renders the creature at absolute (x, y), with optional hop lift."""

    x: reactive[int] = reactive(4)
    y: reactive[int] = reactive(0)
    y_lift: reactive[int] = reactive(0)
    pose: reactive[str] = reactive("idle")

    def __init__(self, animal: Animal, **kwargs) -> None:
        super().__init__(**kwargs)
        self.animal = animal

    def render(self) -> str:
        art = self.animal.poses[self.pose].strip("\n").split("\n")
        pad = " " * max(0, self.x)
        shifted = [pad + line for line in art]
        top_count = max(0, self.y - self.y_lift)
        return "\n".join([""] * top_count + shifted)


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

    @property
    def scene(self) -> CreatureScene:
        return self.query_one(CreatureScene)

    def compose(self) -> ComposeResult:
        yield CreatureScene(self.animal, id="creature")

    def on_mount(self) -> None:
        self.title = f"mob — {self.animal.name}"
        if self._bg:
            self.screen.styles.background = self._bg
        if self._fg:
            self.screen.styles.color = self._fg
            self.scene.styles.color = self._fg
        self.set_interval(4.0, self._maybe_blink)
        if self.animal.behavior.secondary_idles:
            self.set_interval(6.0, self._maybe_secondary_idle)
        self._schedule_next_burst()

    def _art_height(self) -> int:
        return len(self.animal.poses["idle"].strip("\n").split("\n"))

    def _max_y(self) -> int:
        return max(HOP_ROOM, self.size.height - self._art_height())

    # ------------------------------------------------------------------
    # burst scheduling — long sits, clustered hops

    def _schedule_next_burst(self) -> None:
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
        if self.animal.behavior.movement == "crawl":
            self._start_random_crawl()
        else:
            self._start_random_hop()

    def action_sleep(self) -> None:
        self._asleep = not self._asleep
        self.scene.pose = "sleeping" if self._asleep else "idle"

    # ------------------------------------------------------------------

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
    MobApp(animal=ANIMALS[args.animal], fg=fg, bg=bg).run()


if __name__ == "__main__":
    main()
