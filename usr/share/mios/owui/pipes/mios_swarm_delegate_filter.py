"""
title: MiOS Swarm · Delegate
author: MiOS
version: 1.0.0
description: |
  Chat-bar TOGGLE (operator 2026-05-22 "AI SWARM"). When ON, forces the
  per-agent SWARM DECOMPOSITION for this chat: the planner splits the
  request into independent {agent, sub-task} assignments and runs them as
  a CONCURRENT per-agent DAG (different sub-prompts to different agents),
  synthesising one answer. If the local planner declines to split, it
  escalates to the full council swarm -- the toggle never collapses to one
  agent. OFF = natural/automatic (the default).

  Mechanism: the inlet injects body.mios_flags.force_delegate = true; the
  MiOS Agent Pipe (:8640) reads it and runs _plan_swarm -> per-agent DAG
  (or the council fallback). The inlet runs ONLY when the chip is selected.
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
        # Offline-safe base64 SVG (one node branching into two = delegation).
        self.toggle = True
        self.icon = (
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5v"
            "cmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3"
            "Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxp"
            "bmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN"
            "4PSI1IiBjeT0iMTIiIHI9IjIuNSIvPjxjaXJjbGUgY3g9IjE5IiBjeT0iNSIgcj"
            "0iMi41Ii8+PGNpcmNsZSBjeD0iMTkiIGN5PSIxOSIgcj0iMi41Ii8+PHBhdGggZ"
            "D0iTTcuNSAxMWw5LTVNNy41IDEzbDkgNSIvPjwvc3ZnPg=="
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
        flags["force_delegate"] = True
        body["mios_flags"] = flags
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🧩 swarm: per-agent delegation forced",
                         "done": True},
            })
        return body
