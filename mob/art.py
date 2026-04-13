"""ASCII poses for the frog. Each pose is exactly 4 lines, same width."""

IDLE = r"""
     @ . . @
    ( ------ )
   (  > __ <  )
    ^^  ~~  ^^
"""

HAPPY = r"""
     ^ . . ^
    ( ------ )
   (  \ vv /  )
    ^^  ~~  ^^
"""

EATING = r"""
     @ . . @
    ( ------ )
   (  > oo <  )
    ^^  ~~  ^^
"""

SLEEPING = r"""
     - . . -   z
    ( ------ )  Z
   (  > __ <  ) z
    ^^  ~~  ^^
"""

BLINK = r"""
     - . . -
    ( ------ )
   (  > __ <  )
    ^^  ~~  ^^
"""

HOP = r"""
     @ . . @
    ( ------ )
   (  < oo >  )
    /        \
"""

POSES = {
    "idle": IDLE,
    "happy": HAPPY,
    "eating": EATING,
    "sleeping": SLEEPING,
    "blink": BLINK,
    "hop": HOP,
}
