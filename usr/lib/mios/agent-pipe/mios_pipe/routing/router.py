# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1: the pure Router.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_router_py.md

from __future__ import annotations

from typing import Optional

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
        return RouteDecision("agent", intent=intent or "(none)", broad=deep,
                             reason="default: unclassified -> full agent pipeline")


def route(refined: Optional[dict]) -> RouteDecision:
    """Module-level convenience: route via a shared stateless Router."""
    return _ROUTER.route(refined)


def should_fanout(refined: Optional[dict]) -> bool:
    """True when the refined plan routes to a parallel fan-out."""
    return route(refined).fanout


_ROUTER = Router()
