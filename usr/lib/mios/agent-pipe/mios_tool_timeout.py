# AI-hint: Tool-call latency profiling and dead-lock watchdog timeout in agent-pipe tool loop.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-tool-timeout.py
"""
MiOS Agent-Pipe Tool Watchdog & Latency Profiler.
Wraps tool execution with strict asyncio timeouts and records execution durations.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict, Optional, Tuple

class ToolWatchdog:
    """Enforces execution deadlines on external tool invocations."""

    def __init__(self, default_timeout_s: float = 30.0) -> None:
        self.default_timeout_s = max(0.1, float(default_timeout_s))

    async def execute_with_watchdog(
        self,
        tool_func: Callable[[], Coroutine[Any, Any, Any]],
        timeout_s: Optional[float] = None
    ) -> Tuple[bool, Any, float]:
        """Executes tool_func within timeout deadline. Returns (success, result/error, latency_ms)."""
        limit = timeout_s if timeout_s is not None else self.default_timeout_s
        t0 = time.monotonic()
        try:
            res = await asyncio.wait_for(tool_func(), timeout=limit)
            latency_ms = (time.monotonic() - t0) * 1000.0
            return True, res, latency_ms
        except asyncio.TimeoutError:
            latency_ms = (time.monotonic() - t0) * 1000.0
            return False, f"Tool execution timed out after {limit:.2f}s", latency_ms
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000.0
            return False, str(exc), latency_ms
