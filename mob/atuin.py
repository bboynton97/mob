"""Listen for completed shell commands via atuin's local SQLite history.

Atuin's `history.db` runs in WAL mode, so polling it read-only every second
doesn't contend with atuin's writes. Filters to commands that have finished
(duration > 0) so we only fire once per command.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DEFAULT_DB = Path.home() / ".local" / "share" / "atuin" / "history.db"


@dataclass(frozen=True)
class CommandEvent:
    id: str
    timestamp_ns: int
    command: str
    exit_code: int
    duration_ns: int


def default_db_path() -> Path:
    override = os.environ.get("ATUIN_DB_PATH")
    return Path(override) if override else DEFAULT_DB


def is_available() -> bool:
    return default_db_path().exists()


class AtuinPoller:
    """Background thread that tails atuin's SQLite history."""

    def __init__(
        self,
        on_event: Callable[[CommandEvent], None],
        db_path: Path | None = None,
        interval: float = 1.0,
    ) -> None:
        self._on_event = on_event
        self._db_path = db_path or default_db_path()
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._watermark_ns = 0

    def start(self) -> bool:
        if not self._db_path.exists():
            return False
        # Initialize watermark to now so we don't replay historical commands.
        self._watermark_ns = time.time_ns()
        self._thread = threading.Thread(
            target=self._run, name="atuin-poller", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
            except sqlite3.Error:
                pass
            self._stop.wait(self._interval)

    def _poll_once(self) -> None:
        uri = f"file:{self._db_path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1.0) as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, command, exit, duration
                FROM history
                WHERE timestamp > ? AND duration > 0
                ORDER BY timestamp
                LIMIT 100
                """,
                (self._watermark_ns,),
            ).fetchall()
        for row_id, ts_ns, command, exit_code, duration_ns in rows:
            self._watermark_ns = max(self._watermark_ns, ts_ns)
            self._on_event(
                CommandEvent(
                    id=row_id,
                    timestamp_ns=ts_ns,
                    command=command,
                    exit_code=exit_code,
                    duration_ns=duration_ns,
                )
            )
