# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1b: the pure Kernel facade.
# AI-doc: usr/share/doc/mios/manual/kernel.md

from __future__ import annotations

from typing import Any, Optional

class Kernel:
    """Composition root: Router + Dispatcher + the five manager seams."""

    __slots__ = ("router", "dispatcher", "scheduler", "memory",
                 "context", "tools", "access")

    def __init__(self, *, router, dispatcher,
                 scheduler: Any = None, memory: Any = None,
                 context: Any = None, tools: Any = None, access: Any = None) -> None:
        if router is None or dispatcher is None:
            raise ValueError("Kernel requires both a router and a dispatcher")
        self.router = router
        self.dispatcher = dispatcher
        self.scheduler = scheduler   # SchedulerManager seam (priority/lanes/preempt)
        self.memory = memory         # MemoryManager seam (recall/store/scratch)
        self.context = context       # ContextManager seam (tokenize/pack/compact/KV)
        self.tools = tools           # ToolManager seam (conflict/dispatch)
        self.access = access         # AccessManager seam (PDP/HITL/principal)

    async def handle(self, refined: Optional[dict], **ctx) -> Any:
        """The Router/Dispatcher flow: classify the refined plan, then run the
        decision. The single entry chat_completions will delegate to."""
        decision = self.router.route(refined)
        return await self.dispatcher.run(decision, refined=refined, **ctx)

    def managers(self) -> dict:
        """Introspection: which manager seams are wired (for /v1/scheduler)."""
        return {
            "scheduler": self.scheduler is not None,
            "memory": self.memory is not None,
            "context": self.context is not None,
            "tools": self.tools is not None,
            "access": self.access is not None,
        }
