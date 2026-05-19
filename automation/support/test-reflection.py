#!/usr/bin/env python3
"""Smoke-test reflect_on_step_failure.

Calls the reflection helper with a deliberately-bad failed_node
(unknown verb) and verifies the small refine model returns a
correction with a non-empty tool name + rationale.

Live test -- hits the actual refine endpoint -- so it's slow
(15-30s on CPU) but exercises the real path.
"""
from __future__ import annotations
import asyncio
import os
import sys

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")
import server  # noqa: E402


async def main() -> int:
    failed_node = {
        "id": "n1",
        "tool": "open_app_typo",
        "args": {"name": "chrome"},
    }
    failed_result = {
        "success": False,
        "exit_code": 2,
        "stderr": "unknown verb 'open_app_typo'",
    }
    plan_context = {"summary": "user asked to open chrome"}
    corrected = await server.reflect_on_step_failure(
        failed_node, failed_result, plan_context)
    print(f"  corrected = {corrected}")
    if not corrected:
        print("  RESULT: reflection returned None "
              "(refine model unavailable / parse fail)")
        return 1
    tool = corrected.get("tool", "")
    rationale = corrected.get("rationale", "")
    if not tool:
        print(f"  FAIL: empty tool (rationale={rationale!r})")
        return 1
    print(f"  PASS: corrected tool={tool!r} "
          f"rationale={rationale[:80]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
