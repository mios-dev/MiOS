# AI-hint: Injects force_tool=true into the request body to force the executor proxy to use tool_choice=required, preventing models from narrating actions instead of executing them via the MiOS Agent Pipe.
# AI-functions: __init__, inlet, class Filter, class Valves
"""
title: MiOS Swarm · Force-tool
author: MiOS
version: 1.0.0
description: |
  Chat-bar TOGGLE (operator 2026-05-22 "AI SWARM"). When ON, forces the
  executor to ACT via a real tool_call instead of narrating it -- the
  standard tool_choice=required guard against the "I posted to Discord"
  lie (a small model describing an action it never invoked). OFF =
  natural/automatic (tool_choice=auto, the default).

  Mechanism: the inlet injects body.mios_flags.force_tool = true; the MiOS
  Agent Pipe (:8640) sets tool_choice=required on the executor proxy for
  this request. Honoured by tool-calling executors; a model that ignores
  it just behaves as auto. The inlet runs ONLY when the chip is selected.
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
        # Offline-safe base64 SVG (a wrench = forced tool action).
        self.toggle = True
        self.icon = (
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5v"
            "cmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3"
            "Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxp"
            "bmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJN"
            "MTQuNyA2LjNhNCA0IDAgMCAwLTUuNCA1LjRMMyAxOGwzIDMgNi4zLTYuM2E0ID"
            "QgMCAwIDAgNS40LTUuNGwtMi41IDIuNS0yLjEtMi4xeiIvPjwvc3ZnPg=="
        )

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Optional[Callable[..., Awaitable]] = None,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        if not self.valves.ENABLED:
            return body
        flags = body.get("mios_flags")
        if not isinstance(flags, dict):
            flags = {}
        flags["force_tool"] = True
        body["mios_flags"] = flags
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🧠 swarm: tool_choice=required",
                         "done": True},
            })
        return body
