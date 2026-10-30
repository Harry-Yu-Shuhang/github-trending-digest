"""Track browser sessions, allowing refreshes and multiple workspace tabs."""

from __future__ import annotations

import time
from threading import RLock


class BrowserLifecycle:
    def __init__(self, grace_seconds: float = 8, clock=time.monotonic):
        self.grace_seconds = grace_seconds
        self.clock = clock
        self.sessions: set[str] = set()
        self.empty_since: float | None = None
        self.lock = RLock()

    def connect(self, session: str | None) -> None:
        if session:
            with self.lock:
                self.sessions.add(session)
                self.empty_since = None

    def disconnect(self, session: str | None) -> None:
        with self.lock:
            if session not in self.sessions:
                return
            self.sessions.remove(session)
            if not self.sessions:
                self.empty_since = self.clock()

    def should_stop(self) -> bool:
        with self.lock:
            return (
                not self.sessions
                and self.empty_since is not None
                and self.clock() - self.empty_since >= self.grace_seconds
            )
