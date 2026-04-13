"""ASCII poses per animal. Each pose is 4 lines, consistent width per animal."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Behavior:
    """How this critter moves and idles."""

    movement: str = "hop"  # "hop" | "crawl"
    secondary_idles: tuple[str, ...] = ()
    secondary_idle_chance: float = 0.0
    crawl_step_seconds: float = 0.18
    # For hoppers: distance range tiers are handled in app.py.
    # For crawlers: how far a single crawl covers, in columns.
    crawl_distance: tuple[int, int] = (10, 40)


@dataclass(frozen=True)
class Animal:
    name: str
    width: int
    poses: dict[str, str]
    behavior: Behavior = field(default_factory=Behavior)


FROG = Animal(
    name="frog",
    width=16,
    poses={
        "idle": r"""
     @ . . @
    ( ------ )
   (  > __ <  )
    ^^  ~~  ^^
""",
        "happy": r"""
     ^ . . ^
    ( ------ )
   (  \ vv /  )
    ^^  ~~  ^^
""",
        "eating": r"""
     @ . . @
    ( ------ )
   (  > oo <  )
    ^^  ~~  ^^
""",
        "sleeping": r"""
     - . . -   z
    ( ------ )  Z
   (  > __ <  ) z
    ^^  ~~  ^^
""",
        "blink": r"""
     - . . -
    ( ------ )
   (  > __ <  )
    ^^  ~~  ^^
""",
        "hop": r"""
     @ . . @
    ( ------ )
   (  < oo >  )
    /        \
""",
    },
)


DOG = Animal(
    name="dog",
    width=15,
    poses={
        "idle": r"""
      __
     (___()'`;
     /,    /`
     \"--\
""",
        "happy": r"""
      __
     (___()^`;
     /,    /`  ~
     \"--\
""",
        "eating": r"""
      __
     (___()o`;  *
     /,    /`  om
     \"--\
""",
        "sleeping": r"""
      __       z
     (___()-.;   Z
     /,    /`   z
     \"--\
""",
        "blink": r"""
      __
     (___()-.;
     /,    /`
     \"--\
""",
        "hop": r"""
      __
     (___()'`;
     /,    /`
     / /  \ \
""",
    },
)


CAT = Animal(
    name="cat",
    width=28,
    behavior=Behavior(
        movement="crawl",
        secondary_idles=("idle2",),
        secondary_idle_chance=0.25,
        crawl_step_seconds=0.22,
        crawl_distance=(8, 30),
    ),
    poses={
        "idle": r"""
     _
  |\'/-..--.
 / u u   ,  ;
`~=`Y'~_<._./
""",
        "blink": r"""
     _
  |\'/-..--.
 / - -   ,  ;
`~=`Y'~_<._./
""",
        "eating": r"""
 _._     _,-'""`-._
(,-.`._,'(       |\`-/|
    `-.-' \ )-`( , o o)
          `-    \`_`"'-
""",
        "happy": r"""
  /\_/\  (
 ( ^.^ ) _)
   \"/  (
 ( | | )
(__d b__)
""",
        "idle2": r"""
  /\_/\  (
 ( o.o ) _)
   \"/  (
 ( | | )
(__d b__)
""",
        "sleeping": r"""
      |\      _,,,---,,_
ZZZzz /,`.-'`'    -.  ;-;;,_
     |,4-  ) )-,_. ,\ (  `'-'
    '---''(_/--'  `-'\_)
""",
        "walk_left": r"""
  |\__/,|   (`\
  |o o  |.--.) )
  ( T   )     /
(((^_(((/(((_/
""",
        "walk_right": r"""
  /')   |,\__/|
 ( (.--.|  o o|
  \     (   T )
   \_)))\)))_^)))
""",
    },
)


TURTLE = Animal(
    name="turtle",
    width=14,
    poses={
        "idle": r"""
       ______
     _/ o  o \__
    /__________\
     ^^      ^^
""",
        "happy": r"""
       ______
     _/ ^  ^ \__
    /___vv_____\
     ^^      ^^
""",
        "eating": r"""
       ______
     _/ o  o \__
    /____oo____\
     ^^      ^^
""",
        "sleeping": r"""
       ______    z
     _/ -  - \__  Z
    /__________\ z
     ^^      ^^
""",
        "blink": r"""
       ______
     _/ -  - \__
    /__________\
     ^^      ^^
""",
        "hop": r"""
       ______
     _/ o  o \__
    /__________\
     //      \\
""",
    },
)


SLIME = Animal(
    name="slime",
    width=12,
    poses={
        "idle": r"""


     ~~~~~
    ( o   o )
    `~~~~~~~`
""",
        "happy": r"""


     ~~~~~
    ( ^   ^ )
    `~~www~~`
""",
        "eating": r"""


     ~~~~~
    ( o   o )
    `~~oo~~~`
""",
        "sleeping": r"""


     ~~~~~    z
    ( -   - )  Z
    `~~~~~~~` z
""",
        "blink": r"""


     ~~~~~
    ( -   - )
    `~~~~~~~`
""",
        "hop": r"""

     ~~~~~
    ( o   o )
     ~~~~~~~
    / /   \ \
""",
    },
)


ANIMALS: dict[str, Animal] = {
    a.name: a for a in (FROG, DOG, CAT, TURTLE, SLIME)
}
