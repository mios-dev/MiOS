#!/usr/bin/env python3
"""Verify _strip_think_tags removes qwen3 reasoning leaks from
sub-agent output before it reaches the operator's chat stream.
"""
from __future__ import annotations
import sys

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server


CASES = [
    ("clean string with no think tags", "clean string with no think tags"),
    (
        "Before. <think>internal reasoning here</think> After.",
        "Before. After.",
    ),
    (
        "<think>only think</think>",
        "",
    ),
    (
        "Header.\n<think>multi\nline\nthought</think>\nFooter.",
        "Header.\nFooter.",
    ),
    (
        "Body. <think>unclosed tail because token budget ran out",
        "Body.",
    ),
    (
        "<THINK>case-insensitive</THINK> kept text",
        "kept text",
    ),
]


def main() -> int:
    fails = 0
    for inp, expected in CASES:
        got = server._strip_think_tags(inp)
        # Allow whitespace differences -- strip both sides for compare.
        if got.strip() != expected.strip():
            print(f"  FAIL  input  = {inp!r}")
            print(f"        expect = {expected!r}")
            print(f"        got    = {got!r}")
            fails += 1
        else:
            print(f"  PASS  {inp[:60]!r}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
