#!/usr/bin/env python3
"""Smoke-test the skill engine's expand_from semantics.

Calls execute_skill('open-url-fallback-chain', ...) with 3 browsers
and a deliberately-bad URL; verifies the engine fanned 1 step into
3 (one per browser) by inspecting the returned `steps` list length.

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import asyncio
import json
import sys
import os

# Run from inside the agent-pipe runtime so we get the same module.
sys.path.insert(0, "/usr/lib/mios/agent-pipe")
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")
import server  # noqa: E402


async def main() -> int:
    res = await server.execute_skill(
        "open-url-fallback-chain",
        {
            "url": "about:blank-mios-skilltest",
            # 3 obviously-not-a-browser ids so every step "fails"
            # cleanly and we can confirm all 3 were attempted.
            "browsers": ["mios-no-browser-1",
                         "mios-no-browser-2",
                         "mios-no-browser-3"],
        },
        session_id=None,
    )
    print(json.dumps(res, indent=2, default=str)[:1500])
    steps = res.get("steps") or []
    bound = [s.get("args", {}).get("browser") for s in steps]
    expected_bound = ["mios-no-browser-1",
                      "mios-no-browser-2",
                      "mios-no-browser-3"]
    print()
    print(f"PASS check: {len(steps)} steps emitted; "
          f"bound browsers={bound}")
    if len(steps) == 3 and bound == expected_bound:
        print("PASS: expand_from fanned 1 step into 3 with "
              "correct browser bindings.")
        return 0
    print("FAIL: expected 3 steps with the 3 browser names; "
          f"got {len(steps)} steps + bindings={bound}.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
