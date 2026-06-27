#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_tokenize (WS-A5 tokenizer seam). Pure stdlib, no server.py/DB/pytest. Verifies the heuristic backend reproduces the pipe's prior len//4 estimate EXACTLY (byte-for-byte parity for count_text/count_messages, so swapping the inline //4 is behaviour-preserving), truncate_to_tokens honours the token budget (and == the old [:N] char slice), and set_backend swaps the measurement while degrading safely.
# AI-related: ./mios_tokenize.py
# AI-functions: check, main
"""Unit tests for mios_tokenize (WS-A5)."""

import json
import sys

import mios_tokenize as tok

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_count_parity():
    s = "hello world " * 17
    check("count_text == prior len//4", tok.count_text(s) == len(s) // 4, f"{tok.count_text(s)} vs {len(s)//4}")
    check("count_text empty -> 0", tok.count_text("") == 0)
    check("count_text None-safe", tok.count_text(None) == 0)
    check("backend_name is heuristic", tok.backend_name() == "heuristic-chars4")


def t_count_messages_parity():
    msgs = [{"role": "user", "content": "a" * 40}, {"role": "assistant", "content": "b" * 12}]
    tools = [{"type": "function", "function": {"name": "x"}}]
    # Must equal the exact pre-WS-A5 _fit_context estimate.
    expect = (sum(len(str(m.get("content") or "")) for m in msgs) + len(json.dumps(tools))) // 4
    check("count_messages == _fit_context //4 estimate",
          tok.count_messages(msgs, tools) == expect, f"{tok.count_messages(msgs, tools)} vs {expect}")
    check("count_messages no tools", tok.count_messages(msgs) == (40 + 12) // 4)
    check("count_messages empty -> 0", tok.count_messages([]) == 0)


def t_truncate():
    s = "x" * 1000
    check("truncate: 50 tokens == [:200] char slice",
          tok.truncate_to_tokens(s, 50) == s[:200])
    check("truncate: under budget unchanged", tok.truncate_to_tokens("short", 100) == "short")
    check("truncate: rstrips trailing space", not tok.truncate_to_tokens("a b " * 100, 10).endswith(" "))
    check("truncate: 0 tokens -> empty-ish", tok.truncate_to_tokens(s, 0) == "")
    # SLOW_LANE_BLOCK_CHARS=1500 routed as 1500//4=375 tokens -> 375*4=1500 chars (identity).
    big = "y" * 5000
    check("truncate: slow-lane block round-trips to 1500 chars",
          tok.truncate_to_tokens(big, 1500 // 4) == big[:1500])


def t_set_backend():
    class Double:
        chars_per_token = 2
        name = "double"
        def count(self, text):
            return len(text) // 2
    try:
        tok.set_backend(Double())
        check("set_backend: name swapped", tok.backend_name() == "double")
        check("set_backend: count uses new backend", tok.count_text("abcd") == 2)
        tok.set_backend(None)  # invalid -> ignored, keeps Double
        check("set_backend: None ignored (degrade-safe)", tok.backend_name() == "double")
    finally:
        tok.set_backend(mios_tokenize_default())


def t_usage_estimate():
    # Moved from server.py: the OpenAI usage object built off count_text (>=1 floor).
    u = tok._usage_estimate("", "")
    check("usage: empty floors to 1/1/2",
          u == {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}, str(u))
    u2 = tok._usage_estimate("a" * 40, "b" * 12)
    check("usage: counts via count_text (40//4, 12//4)",
          u2 == {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}, str(u2))


def mios_tokenize_default():
    return tok.HeuristicBackend()


def main():
    t_count_parity()
    t_count_messages_parity()
    t_truncate()
    t_set_backend()
    t_usage_estimate()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
