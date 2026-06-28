# AI-hint: WS-A7 per-verb conflict/parallel-limit serialization for the agent-pipe Tool Manager. Provides ConflictGate, a pure-stdlib asyncio primitive that serializes verb dispatches the way a plain pass-through chokepoint cannot: a per-verb `parallel_limit` (max concurrent dispatches of that verb) AND a `conflict_group` (named mutual-exclusion set so stateful single-instance verbs -- e.g. open_app/focus_window/pc_type all contending for the one foreground window + keyboard -- never interleave across a council/DAG fan-out). server.py owns the wiring (build from _VERB_CATALOG, wrap _dispatch_bounded); this module owns only the reusable mechanism. No-op fast path for the vast majority of verbs that declare neither.
# AI-related: ./mios_sched.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_toolconflict.py
# AI-functions: from_catalog, guard, stats, _group_sem, _verb_sem, class ConflictGate, class _Guard
"""mios_toolconflict -- per-verb dispatch serialization for the MiOS agent-pipe
(WS-A7, the AIOS Tool Manager conflict/parallel-limit layer).

Pure stdlib (asyncio / collections) so it unit-tests in isolation, in the
sibling-module style of mios_sched / mios_jsonsalvage. server.py owns the wiring
(parsing the SSOT [verbs.*] fields, building the module-global instance, and
wrapping the dispatch chokepoint); this module owns only the reusable mechanism.

The problem
===========
Before WS-A7 the dispatch chokepoint (_dispatch_bounded) special-cased ONE verb
(web_search, a global SearXNG bulkhead) and let every other verb pass straight
through with unbounded concurrency. But several verbs are *stateful and
single-instance*: there is exactly one foreground window and one keyboard, so a
council/DAG fan-out that issues `open_app`, `focus_window` and `pc_type`
concurrently races them against each other -- the keystrokes land in whatever
window won the focus race. Such verbs need to SERIALIZE, not stampede.

The mechanism
=============
Two orthogonal, SSOT-declared controls, both keyed off the verb name:

  parallel_limit (int >= 1)
      A per-verb concurrency cap. `parallel_limit = 1` makes the verb strictly
      single-flight; `= N` admits at most N concurrent dispatches. Backed by a
      per-verb asyncio.Semaphore(N).

  conflict_group (str)
      A named mutual-exclusion set. All verbs sharing a group serialize against
      *each other* (one member of the group runs at a time), not just against
      themselves. Backed by an asyncio.Semaphore(1) per group name.

A verb may declare either, both, or neither. `guard(verb)` returns an async
context manager:

    async with CONFLICT.guard(verb):
        ... dispatch the verb ...

Deadlock-freedom
----------------
A call acquires AT MOST one group lock and AT MOST one verb semaphore, always in
the fixed order group-lock -> verb-semaphore, and releases in reverse. Because
the order is global and each call holds at most one of each kind, no acquire
cycle can form. Cancellation/exception while acquiring rolls back whatever was
already held (the _Guard rollback in __aenter__).

Fast path
---------
A verb that declares neither control hits a no-op guard (two dict lookups, no
semaphore, no await) -- so the overwhelming majority of dispatches are
unaffected. This is the degrade-open default: an empty ConflictGate serializes
nothing.

Concurrency model: single-threaded asyncio. Semaphores are created lazily on
first use (inside a running loop). All bookkeeping mutations happen with no
await between check and mutation, so no lock is needed.
"""

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
        # verb -> max concurrent dispatches (>= 1). Entries < 1 are dropped.
        self._limits: Dict[str, int] = {
            str(k): int(v) for k, v in (limits or {}).items()
            if _as_int(v) >= 1
        }
        # verb -> conflict-group name (non-empty).
        self._groups: Dict[str, str] = {
            str(k): str(v).strip() for k, v in (groups or {}).items()
            if str(v).strip()
        }
        # Lazily-created semaphores (need a running loop) + live bookkeeping.
        self._verb_sems: Dict[str, asyncio.Semaphore] = {}
        self._group_sems: Dict[str, asyncio.Semaphore] = {}
        self._verb_inflight: "collections.Counter[str]" = collections.Counter()
        self._group_inflight: "collections.Counter[str]" = collections.Counter()
        self._verb_wait: "collections.Counter[str]" = collections.Counter()
        self._group_wait: "collections.Counter[str]" = collections.Counter()

    # ── construction from the SSOT verb catalog ───────────────────────────
    @classmethod
    def from_catalog(cls, catalog: Optional[dict]) -> "ConflictGate":
        """Build a gate from the _VERB_CATALOG dict: read each verb's
        `parallel_limit` (int) and `conflict_group` (str). Tolerant of missing
        / malformed fields (degrade-open: unparseable -> unconstrained)."""
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

    # ── lazy semaphore accessors ──────────────────────────────────────────
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

    # ── public API ────────────────────────────────────────────────────────
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
        # Fast path: unconstrained verb -> nothing to acquire.
        if self._group is None and self._verb not in g._limits:
            return self
        try:
            # 1) group mutual-exclusion lock (global fixed order: group first).
            if self._group is not None:
                gs = g._group_sem(self._group)
                g._group_wait[self._group] += 1
                try:
                    await gs.acquire()
                finally:
                    g._group_wait[self._group] -= 1
                self._have_group = True
                g._group_inflight[self._group] += 1
            # 2) per-verb parallel-limit permit.
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
            # Cancelled / errored mid-acquire: hand back anything we took.
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
