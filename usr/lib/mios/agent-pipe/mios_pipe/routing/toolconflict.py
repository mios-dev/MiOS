# AI-hint: WS-A7 per-verb conflict/parallel-limit serialization for the agent-pipe Tool Manager.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_toolconflict_py.md

from __future__ import annotations

import asyncio
import collections
from typing import Dict, Optional


class ConflictGate:
    """Per-verb conflict-group + parallel-limit serialization gate."""

    def __init__(
        self,
        limits: Optional[Dict[str, int]] = None,
        groups: Optional[Dict[str, str]] = None,
    ) -> None:
        self._limits: Dict[str, int] = {
            str(k): int(v) for k, v in (limits or {}).items()
            if _as_int(v) >= 1
        }
        self._groups: Dict[str, str] = {
            str(k): str(v).strip() for k, v in (groups or {}).items()
            if str(v).strip()
        }
        self._verb_sems: Dict[str, asyncio.Semaphore] = {}
        self._group_sems: Dict[str, asyncio.Semaphore] = {}
        self._verb_inflight: "collections.Counter[str]" = collections.Counter()
        self._group_inflight: "collections.Counter[str]" = collections.Counter()
        self._verb_wait: "collections.Counter[str]" = collections.Counter()
        self._group_wait: "collections.Counter[str]" = collections.Counter()

    @classmethod
    def from_catalog(cls, catalog: Optional[dict]) -> "ConflictGate":
        limits: Dict[str, int] = {}
        groups: Dict[str, str] = {}
        for verb, spec in (catalog or {}).items():
            if not isinstance(spec, dict):
                continue
            pl = _as_int(spec.get("parallel_limit"))
            if pl >= 1:
                limits[str(verb)] = pl
            cg = str(spec.get("conflict_group") or "").strip()
            if cg:
                groups[str(verb)] = cg
        return cls(limits=limits, groups=groups)

    def _group_sem(self, group: str) -> asyncio.Semaphore:
        s = self._group_sems.get(group)
        if s is None:
            s = asyncio.Semaphore(1)  # group = mutual exclusion
            self._group_sems[group] = s
        return s

    def _verb_sem(self, verb: str) -> asyncio.Semaphore:
        s = self._verb_sems.get(verb)
        if s is None:
            s = asyncio.Semaphore(self._limits[verb])
            self._verb_sems[verb] = s
        return s

    def constrains(self, verb: str) -> bool:
        """True if `verb` declares a parallel_limit or a conflict_group."""
        return verb in self._limits or verb in self._groups

    def guard(self, verb: str) -> "_Guard":
        """Async context manager that serializes a dispatch of `verb` per its
        declared conflict_group / parallel_limit. No-op for unconstrained verbs."""
        return _Guard(self, str(verb))

    def stats(self) -> dict:
        """Read-only snapshot for /v1/scheduler observability."""
        return {
            "verbs_limited": len(self._limits),
            "verb_limits": dict(self._limits),
            "groups": sorted(set(self._groups.values())),
            "verb_groups": dict(self._groups),
            "in_flight": {
                "verbs": {k: v for k, v in self._verb_inflight.items() if v},
                "groups": {k: v for k, v in self._group_inflight.items() if v},
            },
            "waiting": {
                "verbs": {k: v for k, v in self._verb_wait.items() if v},
                "groups": {k: v for k, v in self._group_wait.items() if v},
            },
        }


class _Guard:
    """One-shot async context manager bound to a (gate, verb). Acquires the
    group lock then the per-verb permit on entry; releases both (reverse order)
    on exit. Acquisition failure rolls back whatever was already held."""

    __slots__ = ("_g", "_verb", "_group", "_have_group", "_have_verb")

    def __init__(self, gate: ConflictGate, verb: str) -> None:
        self._g = gate
        self._verb = verb
        self._group = gate._groups.get(verb)
        self._have_group = False
        self._have_verb = False

    async def __aenter__(self) -> "_Guard":
        g = self._g
        if self._group is None and self._verb not in g._limits:
            return self
        try:
            if self._group is not None:
                gs = g._group_sem(self._group)
                g._group_wait[self._group] += 1
                try:
                    await gs.acquire()
                finally:
                    g._group_wait[self._group] -= 1
                self._have_group = True
                g._group_inflight[self._group] += 1
            if self._verb in g._limits:
                vs = g._verb_sem(self._verb)
                g._verb_wait[self._verb] += 1
                try:
                    await vs.acquire()
                finally:
                    g._verb_wait[self._verb] -= 1
                self._have_verb = True
                g._verb_inflight[self._verb] += 1
        except BaseException:
            self._release()
            raise
        return self

    async def __aexit__(self, *exc) -> bool:
        self._release()
        return False

    def _release(self) -> None:
        g = self._g
        if self._have_verb:
            g._verb_inflight[self._verb] -= 1
            g._verb_sem(self._verb).release()
            self._have_verb = False
        if self._have_group and self._group is not None:
            g._group_inflight[self._group] -= 1
            g._group_sem(self._group).release()
            self._have_group = False


def _as_int(v) -> int:
    """Lenient int coercion: returns 0 on anything unparseable (degrade-open)."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0
