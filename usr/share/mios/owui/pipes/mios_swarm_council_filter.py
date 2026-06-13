# AI-hint: Injects the force_council flag into the request body to bypass relevance gating and force concurrent execution of all MiOS sub-agents (Hermes, opencode, CPU reasoner) via the Agent Pipe at port 8640.
# AI-functions: __init__, inlet, class Filter, class Valves
"""
title: MiOS Swarm · Council
author: MiOS
version: 1.0.0
description: |
  Chat-bar TOGGLE (operator 2026-05-22 "AI SWARM"). When ON, forces the
  FULL multi-agent swarm for this chat: every eligible MiOS sub-agent
  (Hermes + opencode + the CPU reasoner) runs CONCURRENTLY on the same
  prompt and the answers are synthesised -- bypassing relevance gating and
  the chat short-circuit. OFF = natural/automatic dispatch (the default).

  Mechanism: the inlet injects body.mios_flags.force_council = true; the
  MiOS Agent Pipe (:8640) reads it per-request and overrides _pick_fanout_
  agents(force_council=True). The toggle-filter inlet runs ONLY when the
  operator has the chip selected, so OFF leaves every request untouched.
"""

from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        ENABLED: bool = Field(
            default=True,
            description="Master kill-switch for this toggle (admin).",
        )

    def __init__(self):
        self.valves = self.Valves()
        # Render as a clickable chip in the chat input bar + an on/off entry
        # in the Integrations menu. Offline-safe base64 SVG (a 3-node swarm).
        self.toggle = True
        self.icon = (
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5v"
            "cmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3"
            "Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxp"
            "bmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN"
            "4PSIxMiIgY3k9IjUiIHI9IjIuNSIvPjxjaXJjbGUgY3g9IjUiIGN5PSIxNyIgcj"
            "0iMi41Ii8+PGNpcmNsZSBjeD0iMTkiIGN5PSIxNyIgcj0iMi41Ii8+PHBhdGggZ"
            "D0iTTEyIDcuNXYzTTEwIDEybC0zIDNNMTQgMTJsMyAzIi8+PC9zdmc+"
        )

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Optional[Callable[..., Awaitable]] = None,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        # inlet runs ONLY when the chip is selected -> set the flag
        # unconditionally (the ENABLED valve is the admin kill-switch).
        if not self.valves.ENABLED:
            return body
        flags = body.get("mios_flags")
        if not isinstance(flags, dict):
            flags = {}
        flags["force_council"] = True
        body["mios_flags"] = flags
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🤝 swarm: full council forced",
                         "done": True},
            })
        return body
