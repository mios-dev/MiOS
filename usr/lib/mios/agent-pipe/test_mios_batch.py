#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_batch (WS-A6 batch coalescing). Pure stdlib, no server.py/DB/pytest. Verifies batch_key normalization (scheme + /v1 stripped), the is_native_batch BYPASS test (vLLM/SGLang/llama.cpp lanes -> bypass client-side coalescing, the research-grounded core), and the CoalesceWindow flush decision (open-on-first, flush on max-size OR interval-elapsed, deterministic via passed-in now).
# AI-related: ./mios_batch.py
# AI-functions: check, main
"""Unit tests for mios_batch (WS-A6)."""

import sys

import mios_batch as mb

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_key():
    check("key: strips scheme + /v1", mb.batch_key("http://localhost:11441/v1", "mios-heavy") == "localhost:11441|mios-heavy")
    check("key: bare endpoint", mb.batch_key("localhost:11450", "x") == "localhost:11450|x")
    check("key: distinct models differ", mb.batch_key("e", "a") != mb.batch_key("e", "b"))


def t_native_bypass():
    hints = ["11441", "11440", "11450"]  # SGLang / vLLM / llama-swap local lanes
    check("native: SGLang lane bypassed", mb.is_native_batch("http://localhost:11441/v1", hints) is True)
    check("native: vLLM lane bypassed", mb.is_native_batch("http://localhost:11440/v1", hints) is True)
    check("native: llama.cpp lane bypassed", mb.is_native_batch("http://localhost:11450/v1", hints) is True)
    check("non-native: remote API NOT bypassed", mb.is_native_batch("https://api.example.com/v1", hints) is False)
    check("non-native: empty hints -> nothing bypassed", mb.is_native_batch("http://localhost:11441", []) is False)


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
    # degenerate zero interval = immediate flush (pass-through).
    w0 = mb.CoalesceWindow(interval_s=0.0, max_size=100)
    w0.add(0.0)
    check("window: zero interval -> immediate flush", w0.should_flush(0.0) is True)


def main():
    t_key()
    t_native_bypass()
    t_window_size()
    t_window_interval()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
