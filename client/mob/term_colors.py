"""Query the terminal for its real fg/bg colors via OSC 10 and 11.

Works in Ghostty, iTerm2, Alacritty, Kitty, WezTerm, xterm, and most modern
terminals. Returns None when the terminal doesn't respond (tmux without
passthrough, Apple Terminal in some modes, non-tty, etc.) so callers can
gracefully fall back.
"""

from __future__ import annotations

import os
import re
import select
import sys
import termios
import time
import tty


_RGB_RE = re.compile(r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)")


def _query_osc(osc_num: int, timeout: float = 0.2) -> str:
    """Send an OSC color query and read the reply. Empty string on failure."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return ""
    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        return ""
    try:
        tty.setraw(fd)
        sys.stdout.write(f"\x1b]{osc_num};?\x1b\\")
        sys.stdout.flush()
        buf = ""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            r, _, _ = select.select([fd], [], [], remaining)
            if not r:
                break
            try:
                chunk = os.read(fd, 128).decode(errors="ignore")
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            # Reply terminates with ST (ESC \) or BEL
            if "\x1b\\" in buf or "\x07" in buf:
                break
        return buf
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _parse_rgb(response: str) -> str | None:
    """Parse 'rgb:RRRR/GGGG/BBBB' (any hex width) into '#rrggbb'."""
    if not response:
        return None
    m = _RGB_RE.search(response)
    if not m:
        return None
    out = []
    for c in m.groups():
        bits = len(c) * 4
        if bits == 0:
            return None
        val = int(c, 16)
        scaled = round(val * 255 / ((1 << bits) - 1))
        out.append(max(0, min(255, scaled)))
    return "#{:02x}{:02x}{:02x}".format(*out)


def detect_terminal_colors() -> tuple[str | None, str | None]:
    """Return (foreground_hex, background_hex). Either may be None."""
    fg = _parse_rgb(_query_osc(10))
    bg = _parse_rgb(_query_osc(11))
    return fg, bg
