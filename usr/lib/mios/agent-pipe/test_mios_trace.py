#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_trace (WS-A8 trace/span observability). Pure stdlib, no server.py / DB / pytest -- runs as `python3 test_mios_trace.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Covers span lifecycle (open->finish, duration, status/error), parent linkage, the bounded buffer (per-trace span cap + LRU trace eviction), disabled-tracer no-op, get_trace ordering, recent() shape, and id uniqueness.
# AI-related: ./mios_trace.py, ./test_mios_sched.py
# AI-functions: check, main
"""Unit tests for mios_trace (WS-A8)."""

import sys
import time

import mios_trace as tr

_fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))


def t_ids():
    a = {tr.new_trace_id() for _ in range(200)}
    b = {tr.new_span_id() for _ in range(200)}
    check("ids: trace ids unique", len(a) == 200)
    check("ids: span ids unique", len(b) == 200)
    check("ids: trace id len 16", len(tr.new_trace_id()) == 16)
    check("ids: span id len 8", len(tr.new_span_id()) == 8)


def t_span_lifecycle():
    s = tr.Span("t1", "s1", "", "route", {"k": "v"})
    check("span: opens with status=open", s.status == "open" and not s.ended)
    time.sleep(0.01)
    s.finish("ok")
    check("span: finish sets ended/status", s.ended and s.status == "ok")
    check("span: duration > 0", s.duration_ms > 0, f"{s.duration_ms}ms")
    d0 = s.duration_ms
    time.sleep(0.01)
    check("span: duration frozen after finish", s.duration_ms == d0)
    s.finish("error", "Boom")  # idempotent: first finish wins
    check("span: finish idempotent", s.status == "ok" and s.error == "")
    dd = s.to_dict()
    check("span: to_dict shape", set(dd) >= {"trace_id", "span_id", "parent_id",
          "name", "status", "duration_ms", "ts", "attrs"})
    check("span: attrs preserved", dd["attrs"] == {"k": "v"})


def t_error_status():
    s = tr.Span("t", "s", "", "dispatch")
    s.finish("error", "ValueError")
    check("span: error status + name", s.status == "error" and s.error == "ValueError")


def t_record_and_get():
    T = tr.Tracer(enabled=True, max_traces=8, max_spans_per_trace=8)
    root = tr.Span("trA", "r", "", "request").finish("ok")
    child = tr.Span("trA", "c", "r", "dispatch").finish("ok")
    T.record(root)
    T.record(child)
    spans = T.get_trace("trA")
    check("buffer: get_trace returns recorded spans", len(spans) == 2)
    check("buffer: finish order preserved", spans[0]["name"] == "request" and spans[1]["name"] == "dispatch")
    check("buffer: parent linkage intact", spans[1]["parent_id"] == "r")
    check("buffer: unknown trace -> []", T.get_trace("nope") == [])


def t_disabled_noop():
    T = tr.Tracer(enabled=False)
    T.record(tr.Span("x", "y", "", "n").finish())
    check("disabled: records nothing", T.get_trace("x") == [])
    check("disabled: stats enabled False", T.stats()["enabled"] is False)


def t_span_cap():
    T = tr.Tracer(enabled=True, max_traces=8, max_spans_per_trace=3)
    for i in range(10):
        T.record(tr.Span("capt", f"s{i}", "", f"n{i}").finish())
    spans = T.get_trace("capt")
    check("cap: stored spans bounded to max_spans_per_trace", len(spans) == 3, f"got {len(spans)}")
    check("cap: kept the FIRST spans (cap drops later)", spans[0]["name"] == "n0")
    check("cap: recent() reports total seen past the cap",
          T.recent(1)[0]["seen"] == 10, f"{T.recent(1)}")


def t_trace_eviction():
    T = tr.Tracer(enabled=True, max_traces=3, max_spans_per_trace=8)
    for i in range(5):
        T.record(tr.Span(f"tr{i}", "s", "", "request").finish())
    check("evict: at most max_traces retained", T.stats()["traces"] == 3, f"{T.stats()}")
    check("evict: oldest trace dropped", T.get_trace("tr0") == [] and T.get_trace("tr1") == [])
    check("evict: newest traces kept", len(T.get_trace("tr4")) == 1)


def t_lru_touch():
    # Recording into an existing trace should mark it most-recently-used, so it
    # survives eviction over a trace that has not been touched.
    T = tr.Tracer(enabled=True, max_traces=2, max_spans_per_trace=8)
    T.record(tr.Span("A", "1", "", "request").finish())
    T.record(tr.Span("B", "1", "", "request").finish())
    T.record(tr.Span("A", "2", "r", "dispatch").finish())  # touch A
    T.record(tr.Span("C", "1", "", "request").finish())     # evicts LRU -> B
    check("lru: touched trace A survives", len(T.get_trace("A")) == 2)
    check("lru: untouched trace B evicted", T.get_trace("B") == [])
    check("lru: new trace C present", len(T.get_trace("C")) == 1)


def t_recent_shape():
    T = tr.Tracer(enabled=True)
    T.record(tr.Span("z", "r", "", "request").finish())
    T.record(tr.Span("z", "c", "r", "dispatch").finish())
    rec = T.recent(5)
    check("recent: newest-first list", isinstance(rec, list) and rec[0]["trace_id"] == "z")
    check("recent: reports root span name", rec[0]["root"] == "request", f"{rec[0]}")
    st = T.stats()
    check("stats: counts traces+spans", st["traces"] == 1 and st["spans"] == 2)


def main() -> int:
    t_ids()
    t_span_lifecycle()
    t_error_status()
    t_record_and_get()
    t_disabled_noop()
    t_span_cap()
    t_trace_eviction()
    t_lru_touch()
    t_recent_shape()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
