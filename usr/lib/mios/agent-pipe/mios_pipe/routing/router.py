# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1: the pure Router. Maps a refined plan's intent (chat|dispatch|multi_task|agent|dag, + deep/deterministic flags) to a typed RouteDecision (mode + whether to fan out + the single dispatch tool), the "decide" half of the AIOS Router/Dispatcher split that today lives as a sprawling refined.get('intent') cascade inline in chat_completions. This module is PURE (no server/FastAPI/IO) so the routing decision is unit-testable in isolation; server.py keeps the branch BODIES for now and (Stage 2, VM-verified) will delegate the classification here. Additive + unwired in Stage 1 -> zero behaviour change.
# AI-related: ./server.py, ./mios_kernel.py (Stage 2), ./test_mios_router.py
# AI-functions: route, should_fanout, class RouteDecision, class Router
"""mios_router -- the pure routing decision for the MiOS agent-pipe (WS-A11/WS-3
kernel decomposition, Stage 1).

A request's refined plan carries an `intent`; today chat_completions selects its
execution shape through a large, scattered `refined.get('intent')` cascade. This
module extracts the PRIMARY classification into one pure function: refined plan
-> RouteDecision. The Dispatcher (Stage 2) runs the decision; the Kernel facade
(Stage 2) composes Router + Dispatcher + the manager seams. Keeping Stage 1
additive + unwired means it is fully testable with ZERO risk to the live path
until the Stage-2 delegation is verified in the VM.

Modes (the execution shape the Dispatcher will run):
  chat       -- conversational reply, no tools / no fan-out
  dispatch   -- exactly ONE MiOS verb call (RouteDecision.tool)
  multi_task -- broad swarm fan-out (parallel facets)
  dag        -- a structured multi-node DAG plan
  agent      -- general single-agent tool-loop (the safe default; may deepen)
"""

from __future__ import annotations

from typing import Optional

# The canonical intents the refiner emits (SSOT-aligned with the prompt). An
# unknown/empty intent routes to the safe full-pipeline default ("agent").
_INTENTS = {"chat", "dispatch", "multi_task", "agent", "dag"}
_FANOUT_MODES = {"multi_task", "dag"}


class RouteDecision:
    """The typed routing decision -- what the Dispatcher will run."""

    __slots__ = ("mode", "intent", "tool", "broad", "deterministic", "reason")

    def __init__(self, mode: str, *, intent: str = "", tool: str = "",
                 broad: bool = False, deterministic: bool = False,
                 reason: str = "") -> None:
        self.mode = str(mode)
        self.intent = str(intent)
        self.tool = str(tool or "")
        self.broad = bool(broad)
        self.deterministic = bool(deterministic)
        self.reason = str(reason)

    @property
    def fanout(self) -> bool:
        """True when the mode runs a parallel fan-out (multi_task / dag, or a
        'broad'/deep agent turn)."""
        return self.mode in _FANOUT_MODES or (self.mode == "agent" and self.broad)

    def to_dict(self) -> dict:
        return {"mode": self.mode, "intent": self.intent, "tool": self.tool,
                "broad": self.broad, "deterministic": self.deterministic,
                "fanout": self.fanout, "reason": self.reason}


class Router:
    """Pure router: refined plan -> RouteDecision. No I/O, no globals."""

    def route(self, refined: Optional[dict]) -> RouteDecision:
        r = refined if isinstance(refined, dict) else {}
        intent = str(r.get("intent") or "").strip().lower()
        deep = bool(r.get("deep"))
        deterministic = bool(r.get("_deterministic"))

        if intent == "chat":
            return RouteDecision("chat", intent=intent, reason="conversational reply")
        if intent == "dispatch":
            tool = str(r.get("tool") or r.get("verb") or "").strip()
            return RouteDecision("dispatch", intent=intent, tool=tool,
                                 deterministic=deterministic,
                                 reason="single verb dispatch")
        if intent == "multi_task":
            return RouteDecision("multi_task", intent=intent, broad=True,
                                 reason="broad swarm fan-out")
        if intent == "dag":
            return RouteDecision("dag", intent=intent, broad=True,
                                 reason="structured DAG plan")
        if intent == "agent":
            return RouteDecision("agent", intent=intent, broad=deep,
                                 reason="agent tool-loop" + (" (deep)" if deep else ""))
        # Unknown / empty intent -> safe default: the full agent pipeline.
        return RouteDecision("agent", intent=intent or "(none)", broad=deep,
                             reason="default: unclassified -> full agent pipeline")


def route(refined: Optional[dict]) -> RouteDecision:
    """Module-level convenience: route via a shared stateless Router."""
    return _ROUTER.route(refined)


def should_fanout(refined: Optional[dict]) -> bool:
    """True when the refined plan routes to a parallel fan-out."""
    return route(refined).fanout


_ROUTER = Router()
