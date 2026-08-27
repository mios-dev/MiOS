#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_batch (WS-A6 batch coalescing). Stdlib + asyncio, no DB/pytest.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_batch (WS-A6)."""

import asyncio
import sys
import time

import mios_batch as mb

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def t_key():
    check("key: strips scheme + /v1", mb.batch_key("http://localhost:8442/v1", "mios-heavy") == "localhost:8442|mios-heavy")
    check("key: bare endpoint", mb.batch_key("localhost:8450", "x") == "localhost:8450|x")
    check("key: distinct models differ", mb.batch_key("e", "a") != mb.batch_key("e", "b"))

def t_native_bypass():
    hints = ["8442", "8441", "8450"]  # SGLang / vLLM / llama-swap local lanes
    check("native: SGLang lane bypassed", mb.is_native_batch("http://localhost:8442/v1", hints) is True)
    check("native: vLLM lane bypassed", mb.is_native_batch("http://localhost:8441/v1", hints) is True)
    check("native: llama.cpp lane bypassed", mb.is_native_batch("http://localhost:8450/v1", hints) is True)
    check("non-native: remote API NOT bypassed", mb.is_native_batch("https://api.example.com/v1", hints) is False)
    check("non-native: empty hints -> nothing bypassed", mb.is_native_batch("http://localhost:8442", []) is False)

def t_window_size():
    w = mb.CoalesceWindow(interval_s=10.0, max_size=3)
    check("window: empty -> no flush", w.should_flush(0.0) is False)
    w.add(0.0); w.add(0.1)
    check("window: below size + within interval -> no flush", w.should_flush(0.2) is False)
    w.add(0.2)
    check("window: at max_size -> flush", w.should_flush(0.3) is True)
    check("window: flush returns count + resets", w.flush() == 3 and w.pending == 0)

def t_window_interval():
    w = mb.CoalesceWindow(interval_s=0.05, max_size=100)
    w.add(1000.0)
    check("window: within interval -> hold", w.should_flush(1000.02) is False)
    check("window: interval elapsed -> flush", w.should_flush(1000.10) is True)
    w0 = mb.CoalesceWindow(interval_s=0.0, max_size=100)
    w0.add(0.0)
    check("window: zero interval -> immediate flush", w0.should_flush(0.0) is True)

async def _coalescer_cases():
    C = mb.Coalescer

    c = C(enabled=False, interval_s=5.0)
    t0 = time.perf_counter()
    r = await c.hold("http://remote:9999", "m")
    check("coalescer: disabled never holds",
          r["held"] is False and (time.perf_counter() - t0) < 0.05, str(r))

    c = C(enabled=True, interval_s=5.0, native_hints=["8500"])
    t0 = time.perf_counter()
    r = await c.hold("http://localhost:8500/v1", "m")
    check("coalescer: a native lane bypasses the window",
          r["held"] is False and r["reason"] == "native"
          and (time.perf_counter() - t0) < 0.05, str(r))

    c = C(enabled=True, interval_s=0.12, max_size=8)
    t0 = time.perf_counter()
    outs = await asyncio.gather(*[c.hold("http://remote:9999", "m") for _ in range(4)])
    held = (time.perf_counter() - t0)
    check("coalescer: concurrent same-key callers form ONE group",
          {o["group_size"] for o in outs} == {4}, str(outs))
    check("coalescer: exactly one leader", sum(1 for o in outs if o["leader"]) == 1)
    check("coalescer: the group waits out the interval", held >= 0.10, f"{held:.3f}s")
    check("coalescer: the group is not held past the interval", held < 0.6, f"{held:.3f}s")
    check("coalescer: no window is left behind", c.open_groups == 0)

    c = C(enabled=True, interval_s=30.0, max_size=3)
    t0 = time.perf_counter()
    outs = await asyncio.gather(*[c.hold("http://remote:9999", "m") for _ in range(3)])
    check("coalescer: max_size flushes without waiting out the interval",
          all(o["reason"] == "full" for o in outs) and (time.perf_counter() - t0) < 1.0,
          str(outs))
    check("coalescer: a full group leaves nothing behind", c.open_groups == 0)

    c = C(enabled=True, interval_s=0.05, max_size=8)
    outs = await asyncio.gather(c.hold("http://a:1", "m"), c.hold("http://b:2", "m"))
    check("coalescer: distinct endpoints never share a window",
          [o["group_size"] for o in outs] == [1, 1], str(outs))
    outs = await asyncio.gather(c.hold("http://a:1", "m1"), c.hold("http://a:1", "m2"))
    check("coalescer: distinct models never share a window",
          [o["group_size"] for o in outs] == [1, 1], str(outs))

    c = C(enabled=True, interval_s=0.02, max_size=8)
    a = await c.hold("http://remote:9999", "m")
    b = await c.hold("http://remote:9999", "m")
    check("coalescer: a flushed group is sealed, the next caller opens a fresh one",
          a["group_size"] == 1 and b["group_size"] == 1, f"{a} {b}")
    check("coalescer: sequential holds leave nothing behind", c.open_groups == 0)

def t_coalescer():
    asyncio.run(_coalescer_cases())

def main():
    t_key()
    t_native_bypass()
    t_window_size()
    t_window_interval()
    t_coalescer()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0

if __name__ == "__main__":
    sys.exit(main())
