# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1b: the pure Kernel facade. Composes the AIOS managers (Scheduler / Memory / Context / Tool / Access) + the Router (mios_router) + a Dispatcher behind ONE seam, by INJECTION (server.py provides concrete impls built from its existing functions), so this module stays server.py-free + unit-testable. Defines the route->dispatch flow contract (Kernel.handle: router.route(refined) -> dispatcher.run(decision)) that chat_completions will delegate to in Stage 2 (VM-verified). Additive + unwired in Stage 1 -> zero behaviour change.
# AI-related: ./mios_router.py, ./server.py, ./test_mios_kernel.py
# AI-functions: handle, managers, class Kernel
"""mios_kernel -- the MiOS agent-pipe Kernel facade (WS-A11/WS-3, Stage 1b).

A thin composition that gives the decomposed agent-pipe ONE object holding the
Router (decide), the Dispatcher (run), and the five AIOS manager seams. The
managers + dispatcher are INJECTED by server.py (concrete adapters over the
existing scheduler/memory/context/tool/access code paths) so this module imports
NOTHING from server.py and is fully testable with fakes. Stage 2 builds the
KERNEL once and rewires chat_completions to `KERNEL.handle(refined, ...)`,
replacing the inline intent cascade.

Contract:
    decision = kernel.router.route(refined)        # pure (mios_router)
    result   = await kernel.dispatcher.run(decision, refined=refined, **ctx)
The Dispatcher is duck-typed: any object exposing `async run(decision, **ctx)`.
"""

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
