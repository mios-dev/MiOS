# AI-hint: WS-A8 per-request trace/span observability primitive for the agent-pipe.
# AI-doc: usr/share/doc/mios/manual/observability.md

from __future__ import annotations

import collections
import time
import uuid
from typing import Dict, List, Optional


def new_trace_id() -> str:
    """A fresh trace id (16 hex chars)."""
    return uuid.uuid4().hex[:16]


def new_span_id() -> str:
    """A fresh span id (8 hex chars)."""
    return uuid.uuid4().hex[:8]


class Span:
    """One timed stage within a trace."""

    __slots__ = ("trace_id", "span_id", "parent_id", "name", "attrs",
                 "status", "error", "_t0_wall", "_t0_perf", "_t1_perf", "ended")

    def __init__(self, trace_id: str, span_id: str, parent_id: str,
                 name: str, attrs: Optional[dict] = None) -> None:
        self.trace_id = str(trace_id)
        self.span_id = str(span_id)
        self.parent_id = str(parent_id or "")
        self.name = str(name)
        self.attrs: Dict = dict(attrs or {})
        self.status = "open"
        self.error = ""
        self._t0_wall = time.time()       # epoch seconds, for display
        self._t0_perf = time.perf_counter()  # monotonic, for duration
        self._t1_perf: Optional[float] = None
        self.ended = False

    def finish(self, status: str = "ok", error: str = "") -> "Span":
        """Stamp end-time + status. Idempotent (first finish wins)."""
        if self.ended:
            return self
        self._t1_perf = time.perf_counter()
        self.status = str(status)
        self.error = str(error or "")
        self.ended = True
        return self

    @property
    def duration_ms(self) -> float:
        end = self._t1_perf if self._t1_perf is not None else time.perf_counter()
        return round((end - self._t0_perf) * 1000.0, 3)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "status": self.status,
            "error": self.error,
            "ts": round(self._t0_wall, 3),
            "duration_ms": self.duration_ms,
            "attrs": self.attrs,
        }


class Tracer:
    """Bounded in-memory span buffer + id factory for one agent-pipe process."""

    def __init__(self, enabled: bool = True, max_traces: int = 256,
                 max_spans_per_trace: int = 128) -> None:
        self.enabled = bool(enabled)
        self._max_traces = max(1, int(max_traces))
        self._max_spans = max(1, int(max_spans_per_trace))
        self._traces: "collections.OrderedDict[str, List[dict]]" = collections.OrderedDict()
        self._seen: "collections.OrderedDict[str, int]" = collections.OrderedDict()

    def start_span(self, name: str, *, trace_id: str, parent_id: str = "",
                   attrs: Optional[dict] = None) -> Span:
        """Create (but do not yet record) a span. Caller finish()es it then
        record()s it (server.py's context manager does both)."""
        return Span(trace_id, new_span_id(), parent_id, name, attrs)

    def record(self, span: Span) -> None:
        """Add a (finished) span to its trace's buffer. No-op if disabled."""
        if not self.enabled:
            return
        tid = span.trace_id
        if not tid:
            return
        if tid not in self._traces:
            self._traces[tid] = []
            self._seen[tid] = 0
            while len(self._traces) > self._max_traces:
                old, _ = self._traces.popitem(last=False)
                self._seen.pop(old, None)
        self._traces.move_to_end(tid)
        self._seen[tid] = self._seen.get(tid, 0) + 1
        lst = self._traces[tid]
        if len(lst) < self._max_spans:
            lst.append(span.to_dict() if not isinstance(span, dict) else span)

    def get_trace(self, trace_id: str) -> List[dict]:
        """All recorded spans for a trace, in finish order (empty if unknown)."""
        return list(self._traces.get(str(trace_id), []))

    def recent(self, n: int = 20) -> List[dict]:
        """Most-recent traces (newest first) as {trace_id, spans, seen, name}."""
        out: List[dict] = []
        for tid in reversed(self._traces):
            spans = self._traces[tid]
            root = next((s for s in spans if not s.get("parent_id")), None)
            out.append({
                "trace_id": tid,
                "spans": len(spans),
                "seen": self._seen.get(tid, len(spans)),
                "root": (root or {}).get("name", ""),
            })
            if len(out) >= max(1, int(n)):
                break
        return out

    def stats(self) -> dict:
        return {
            "enabled": self.enabled,
            "traces": len(self._traces),
            "spans": sum(len(v) for v in self._traces.values()),
            "max_traces": self._max_traces,
            "max_spans_per_trace": self._max_spans,
        }
