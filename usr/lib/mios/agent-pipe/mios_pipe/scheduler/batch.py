# AI-hint: WS-A6 batch-coalescing core, designed per 2026 best practice (researched): vLLM/SGLang/llama.cpp already do SERVER-SIDE continuous batchin...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_scheduler_batch_py.md
"""mios_batch -- batch-interval coalescing for the MiOS agent-pipe (WS-A6, the
AIOS scheduler call-coalescing layer).

Pure stdlib. RESEARCH NOTE (the proper solution): the modern inference engines
MiOS runs locally -- vLLM (PagedAttention), SGLang (RadixAttention), and
llama.cpp -- all implement CONTINUOUS BATCHING: the engine's own scheduler forms
a rolling batch from concurrent requests with no fixed timer/count, which is
strictly better than any client-side grouping. So coalescing must NOT touch
those lanes (double-batching only adds head-of-line latency). It applies ONLY to
endpoints WITHOUT native continuous batching -- a rate-limited remote API where
grouping calls in a short window genuinely reduces request count. Hence the core
here is: bypass native lanes; window-bound the rest.

Sources: vLLM continuous batching (docs.vllm.ai), SGLang OpenAI-compatible
serving, BentoML "Static, dynamic and continuous batching" (LLM Inference Handbook).
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Callable, Iterable, Optional


def batch_key(endpoint: str, model: str) -> str:
    """Coalescing key = (normalized endpoint, model). Strips a trailing /v1 and
    scheme so two spellings of the same lane share a window."""
    ep = re.sub(r"^https?://", "", str(endpoint or "")).rstrip("/")
    if ep.endswith("/v1"):
        ep = ep[:-3].rstrip("/")
    return f"{ep}|{str(model or '')}"


def is_native_batch(endpoint: str, native_hints: Iterable[str]) -> bool:
    """True when `endpoint` speaks SERVER-SIDE continuous batching (vLLM/SGLang/
    llama.cpp) and must therefore BYPASS client-side coalescing. Matched by the
    SSOT host:port hint list (e.g. the local lane ports). Anything not hinted is
    treated as non-native -> eligible for window coalescing."""
    e = str(endpoint or "")
    return any(h and str(h).strip() in e for h in (native_hints or []))


class CoalesceWindow:
    """A pure per-key batch window for a NON-native endpoint: open on the first
    item, flush when the interval has elapsed OR max_size items are pending.
    Deterministic (caller passes `now`); server.py drives the async hold/flush."""

    __slots__ = ("interval_s", "max_size", "_start", "_pending")

    def __init__(self, interval_s: float = 0.05, max_size: int = 8) -> None:
        self.interval_s = max(0.0, float(interval_s))
        self.max_size = max(1, int(max_size))
        self._start: float = -1.0
        self._pending: int = 0

    def add(self, now: float) -> None:
        """Record an item arriving at `now`; opens the window on the first add."""
        if self._pending == 0:
            self._start = float(now)
        self._pending += 1

    @property
    def pending(self) -> int:
        return self._pending

    def should_flush(self, now: float) -> bool:
        """Flush when at/over max_size, or the interval has elapsed since open."""
        if self._pending == 0:
            return False
        if self._pending >= self.max_size:
            return True
        if self.interval_s <= 0:
            return True   # no window -> flush immediately (degenerate = pass-through)
        return (float(now) - self._start) >= self.interval_s

    def flush(self) -> int:
        """Reset the window, returning the count that was pending."""
        n = self._pending
        self._pending = 0
        self._start = -1.0
        return n


class _Group:
    """One in-flight group: window, member event, release timer."""

    __slots__ = ("window", "event", "timer", "sealed", "size", "reason")

    def __init__(self, window: "CoalesceWindow") -> None:
        self.window = window
        self.event = asyncio.Event()
        self.timer: Any = None
        self.sealed = False
        self.size = 0
        self.reason = ""


class Coalescer:
    """Async hold-and-flush, one window per batch key.

    Sealing, the native bypass and the default-off contract: manual ch59."""

    __slots__ = ("enabled", "interval_s", "max_size", "native_hints", "_groups", "_clock")

    def __init__(self, *, enabled: bool = False, interval_s: float = 0.05,
                 max_size: int = 8, native_hints: Iterable[str] = (),
                 clock: Optional[Callable[[], float]] = None) -> None:
        self.enabled = bool(enabled)
        self.interval_s = max(0.0, float(interval_s))
        self.max_size = max(1, int(max_size))
        self.native_hints = [str(h).strip() for h in (native_hints or []) if str(h).strip()]
        self._groups: dict = {}
        self._clock = clock or (lambda: asyncio.get_running_loop().time())

    def _release(self, key: str, group: "_Group", reason: str) -> None:
        if group.sealed:
            return
        group.sealed = True
        group.reason = reason
        group.size = group.window.flush()
        if group.timer is not None:
            group.timer.cancel()
            group.timer = None
        if self._groups.get(key) is group:
            del self._groups[key]
        group.event.set()

    async def hold(self, endpoint: str, model: str) -> dict:
        """Block until this key's window flushes.

        Returns {held, reason, group_size, leader}; held=False = never delayed."""
        if not self.enabled:
            return {"held": False, "reason": "disabled", "group_size": 1, "leader": True}
        if is_native_batch(endpoint, self.native_hints):
            return {"held": False, "reason": "native", "group_size": 1, "leader": True}

        key = batch_key(endpoint, model)
        group = self._groups.get(key)
        if group is None or group.sealed:
            group = _Group(CoalesceWindow(self.interval_s, self.max_size))
            self._groups[key] = group

        group.window.add(self._clock())
        seat = group.window.pending
        if group.window.should_flush(self._clock()):
            self._release(key, group, "full")
        elif seat == 1:
            group.timer = asyncio.get_running_loop().call_later(
                self.interval_s, self._release, key, group, "interval")

        if not group.sealed:
            await group.event.wait()
        return {"held": True, "reason": group.reason,
                "group_size": group.size, "leader": seat == 1}

    @property
    def open_groups(self) -> int:
        """Windows still holding callers; a leak check."""
        return len(self._groups)
