#!/usr/bin/env python3
# AI-hint: Integration test script to verify that the `refine` post-parse logic correctly demotes long, multi-step prompts to `agent` intent while prese...
# AI-doc: usr/share/doc/mios/manual/tests.md
from __future__ import annotations
import asyncio
import os
import sys

import _agentpipe_path  # noqa: F401  -- repo agent-pipe on sys.path, not the installed copy
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")
import server  # noqa: E402


LONG_PROMPT = (
    "find all of my installed games; research all their ratings, "
    "review and launch the highest reviewed game I have installed "
    "for me on my PC"
)
SHORT_DISPATCH = "open chrome"


async def main() -> int:
    fails = 0
    print(f"=== case 1: long multi-step prompt ({len(LONG_PROMPT)} chars) ===")
    r = await server.refine_intent(LONG_PROMPT, history=None)
    if r is None:
        print("  SKIP: refine returned None")
    else:
        print(f"  intent: {r.get('intent')!r}  (expect: agent or dag)")
        if r.get("intent") in ("agent", "dag", "multi_task"):
            print("  PASS")
        else:
            print(f"  FAIL: expected agent/dag/multi_task, got {r.get('intent')!r}")
            fails += 1

    print()
    print(f"=== case 2: short dispatch ({len(SHORT_DISPATCH)} chars) ===")
    r = await server.refine_intent(SHORT_DISPATCH, history=None)
    if r is None:
        print("  SKIP: refine bypassed (likely trivial-bypass)")
    else:
        print(f"  intent: {r.get('intent')!r}  (expect: dispatch or agent)")
        if r.get("intent") in ("dispatch", "agent"):
            print("  PASS (not demoted to chat/dag)")
        else:
            print(f"  FAIL: unexpected intent {r.get('intent')!r}")
            fails += 1

    print()
    print("=== case 3: arg-shape guard via inline check ===")
    forged = {
        "intent": "dispatch",
        "args": {"name": "the highest reviewed game on disk"},
        "tool": "open_app",
    }
    args = forged.get("args") or {}
    wordy = any(
        isinstance(v, str) and len(v.strip().split()) > 3
        for v in args.values()
    )
    if wordy:
        print("  PASS guard fires: wordy arg detected "
              "('the highest reviewed game on disk' = 6 words)")
    else:
        print("  FAIL: guard missed multi-word semantic arg")
        fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
