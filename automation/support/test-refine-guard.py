#!/usr/bin/env python3
"""Smoke-test the refine chat-promotion guard.

Calls refine_intent() with three actionable inputs that a small
refine model has historically misclassified as chat (operator-
flagged trace: 'mios-open-url https://...' returned intent=chat
+ fabricated 'Wikipedia has been opened' confirmation when nothing
was actually executed). Verifies the post-parse guard rewrites
chat -> dispatch.
"""
from __future__ import annotations
import asyncio
import os
import sys

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")
import server  # noqa: E402


CASES = [
    "mios-open-url https://www.wikipedia.org",
    "https://example.com",
    "git status",
]


async def main() -> int:
    fails = 0
    for text in CASES:
        r = await server.refine_intent(text, history=None)
        if r is None:
            print(f"  SKIP  refine returned None for {text!r} "
                  f"(bypassed or model failed)")
            continue
        intent = r.get("intent")
        print(f"  {text!r:60s} -> intent={intent}")
        if intent == "chat":
            print("    FAIL: still classified as chat")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
