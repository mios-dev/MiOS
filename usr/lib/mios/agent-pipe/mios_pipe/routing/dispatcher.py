# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1c: the pure Dispatcher. Runs a RouteDecision (from mios_router) by routing its `mode` to the matching per-mode HANDLER, where handlers are INJECTED (server.py provides the concrete chat/dispatch/swarm/dag/agent runners built from its existing branch bodies), so this module imports nothing from server.py and is unit-testable. Completes the Router(decide) -> Dispatcher(run) split the Kernel facade composes. Unknown mode falls back to the 'agent' handler (the safe full-pipeline default). Additive + unwired in Stage 1 -> zero behaviour change.
# AI-related: ./mios_router.py, ./mios_kernel.py, ./server.py, ./test_mios_dispatcher.py
# AI-functions: run, modes, can_handle, class Dispatcher
"""mios_dispatcher -- the pure mode Dispatcher (WS-A11/WS-3, Stage 1c).

The "run" half of the AIOS Router/Dispatcher split. mios_router classifies a
refined plan into a RouteDecision(mode, ...); this Dispatcher routes that mode to
a registered async handler. Handlers are injected by server.py (the concrete
chat / dispatch / multi_task / dag / agent execution paths, lifted from the
current inline cascade), so the routing table is pure + testable while the heavy
bodies stay where they are until Stage 2 rewires them behind this seam.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class Dispatcher:
    """Routes RouteDecision.mode -> the injected handler for that mode."""

    def __init__(self, handlers: Optional[Dict[str, Callable]] = None, *,
                 default_mode: str = "agent") -> None:
        self._handlers: Dict[str, Callable] = dict(handlers or {})
        self._default = str(default_mode)

    @staticmethod
    def _mode_of(decision: Any) -> str:
        m = getattr(decision, "mode", None)
        if m is None and isinstance(decision, dict):
            m = decision.get("mode")
        return str(m or "")

    async def run(self, decision: Any, **ctx) -> Any:
        """Run the decision via its mode handler. Falls back to the default-mode
        handler for an unknown/missing mode; raises KeyError if neither exists
        (a fail-loud wiring error, not a runtime degrade)."""
        mode = self._mode_of(decision)
        handler = self._handlers.get(mode) or self._handlers.get(self._default)
        if handler is None:
            raise KeyError(
                f"mios_dispatcher: no handler for mode {mode!r} and no "
                f"'{self._default}' fallback (handlers wired: {self.modes()})")
        return await handler(decision, **ctx)

    def modes(self) -> list:
        return sorted(self._handlers)

    def can_handle(self, mode: str) -> bool:
        return str(mode) in self._handlers or self._default in self._handlers
