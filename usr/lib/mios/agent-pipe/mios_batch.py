# AI-hint: WS-A6 batch-coalescing core, designed per 2026 best practice (researched): vLLM/SGLang/llama.cpp already do SERVER-SIDE continuous batching (a rolling scheduler coalesces incoming prompts into GPU batches optimally), so client-side request-batching on those lanes would DOUBLE-BATCH and add latency for no gain. Therefore this coalescer BYPASSES native-continuous-batching lanes (all of MiOS's local lanes) and only applies a small batch_interval WINDOW to NON-native endpoints (e.g. a rate-limited remote API). Pure stdlib: batch_key derivation, is_native_batch bypass test (host:port hint list), and a CoalesceWindow flush decision (interval-elapsed OR max-size). server.py owns the async hold-and-flush + the chokepoint wiring (flag-gated); this module owns the decision.
# AI-related: ./mios_lanes.py, ./mios_sched.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_batch.py
# AI-functions: batch_key, is_native_batch, class CoalesceWindow
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

import re
from typing import Iterable


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
