#!/usr/bin/env python3
# AI-hint: Smoke-test script to verify the skill engine's expand_from logic by validating that a single step with multiple browser targets correctly fans ...
# AI-doc: usr/share/doc/mios/manual/_harvest/tests_test_expand_from_py.md
from __future__ import annotations

import asyncio
import json
import sys
import os

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")
import server  # noqa: E402


async def main() -> int:
    res = await server.execute_skill(
        "open-url-fallback-chain",
        {
            "url": "about:blank-mios-skilltest",
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
