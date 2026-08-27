# AI-hint: Graceful worker shutdown and SIGTERM drain handler in server.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-drain-handler.py
"""
MiOS Agent-Pipe Graceful Drain & Termination Handler.
Tracks in-flight requests, stops new admissions on SIGTERM, and drains workers cleanly.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

class GracefulDrainManager:
    """Coordinates server request draining and safe termination within deadline."""

    def __init__(self, drain_timeout_s: float = 10.0) -> None:
        self.drain_timeout_s = drain_timeout_s
        self.is_draining = False
        self._active_requests = 0

    def start_drain(self) -> None:
        """Enters drain mode to stop admitting new requests."""
        self.is_draining = True

    def acquire_slot(self) -> bool:
        """Returns True if new request is admitted (not draining), incrementing active count."""
        if self.is_draining:
            return False
        self._active_requests += 1
        return True

    def release_slot(self) -> None:
        """Decrements active request count."""
        if self._active_requests > 0:
            self._active_requests -= 1

    @property
    def active_requests(self) -> int:
        return self._active_requests

    async def wait_for_drain(self, poll_interval_s: float = 0.05) -> bool:
        """Waits until all active requests complete or drain timeout expires."""
        t0 = time.monotonic()
        while self._active_requests > 0:
            if time.monotonic() - t0 >= self.drain_timeout_s:
                return False  # Timed out waiting for drain
            await asyncio.sleep(poll_interval_s)
        return True
