# AI-hint: Deterministic GOAP planner (#53) -- min-cost action sequence to a goal, plus the config-bound lane wrappers.
# AI-related: server.py, mios_config, mios_lanes, /usr/share/mios/mios.toml
# AI-functions: satisfies, applicable, apply_effects, plan, validate_actions, _goap_actions, _goap_enabled, _goap_plan
#   Goal-Oriented Action Planning via uniform-cost (Dijkstra) search over world
#   states: given an initial fact-state, a goal, and actions (preconditions +
#   effects + cost), returns the minimum-cost ordered action-name list to reach
#   the goal, [] if already satisfied, or None if unreachable. Deterministic +
#   dependency-free -> a reproducible ALTERNATIVE to the LLM DAG planner for
#   well-specified multi-step tasks (launch->type->verify). Unit-tested in
#   isolation (test_mios_goap.py); server.py reads the action set from SSOT.
"""Deterministic GOAP planner lane (#53), Embabel-style, alongside the LLM DAG.

When a task decomposes into steps whose pre/post-conditions are KNOWN (e.g. you
must open an app before you can type into it, and verify after), an LLM does not
need to "reason out" the order -- it is a search problem with one correct answer.
This module solves it deterministically: uniform-cost search guarantees the
returned plan is minimum-cost and reproducible (same inputs -> same plan).

World state = a dict of fact -> value. An action = {
    "name": str, "pre": {fact: value, ...}, "eff": {fact: value, ...},
    "cost": int (default 1)}. plan() returns [action_name, ...] | [] | None.

This module is server.py-free. It provides the pure SOLVER + action-model
contract AND the config-bound lane wrappers (_goap_enabled / _goap_actions /
_goap_plan) that read the mode + action set from mios.toml [goap] via mios_config
and decide when the lane is active (default off -> the LLM DAG is unchanged).
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional

from mios_config import _toml_section


def satisfies(state: dict, goal: dict) -> bool:
    """True iff every goal fact holds in state."""
    return all(state.get(k) == v for k, v in (goal or {}).items())


def applicable(state: dict, action: dict) -> bool:
    """True iff every precondition of action holds in state."""
    return all(state.get(k) == v for k, v in (action.get("pre") or {}).items())


def apply_effects(state: dict, action: dict) -> dict:
    """The successor state after applying action's effects (state is unchanged)."""
    nxt = dict(state)
    nxt.update(action.get("eff") or {})
    return nxt


def _key(state: dict):
    return tuple(sorted(state.items()))


def validate_actions(actions: list) -> "List[str]":
    """Return a list of human-readable problems with an action set (empty = ok).
    Catches the shapes that would make planning silently misbehave."""
    problems: List[str] = []
    seen = set()
    for i, a in enumerate(actions or []):
        if not isinstance(a, dict):
            problems.append(f"action[{i}] is not a table"); continue
        name = a.get("name")
        if not name:
            problems.append(f"action[{i}] has no name")
        elif name in seen:
            problems.append(f"duplicate action name: {name!r}")
        else:
            seen.add(name)
        for fld in ("pre", "eff"):
            if fld in a and not isinstance(a[fld], dict):
                problems.append(f"action {name!r}: {fld} must be a table")
        if not (a.get("eff")):
            problems.append(f"action {name!r}: no effects (cannot change state)")
        c = a.get("cost", 1)
        if not isinstance(c, int) or c < 0:
            problems.append(f"action {name!r}: cost must be a non-negative int")
    return problems


def plan(initial: dict, goal: dict, actions: list,
         *, max_expansions: int = 20000) -> "Optional[list]":
    """Minimum-cost action-name sequence from initial to goal.

    Returns [] if the goal already holds, a list of action names on success, or
    None if the goal is unreachable (or the search budget is exhausted). Uniform-
    cost search -> the result is optimal and deterministic. max_expansions bounds
    pathological action sets so a planner call can never hang the request path.
    """
    initial = dict(initial or {})
    goal = dict(goal or {})
    if satisfies(initial, goal):
        return []
    counter = 0
    pq = [(0, counter, initial, [])]          # (g, tiebreak, state, path)
    best = {_key(initial): 0}
    expansions = 0
    while pq:
        g, _, state, path = heapq.heappop(pq)
        expansions += 1
        if expansions > max_expansions:
            return None
        if satisfies(state, goal):
            return path
        for action in actions:
            if not applicable(state, action):
                continue
            nxt = apply_effects(state, action)
            nk = _key(nxt)
            ng = g + int(action.get("cost", 1))
            if nk in best and best[nk] <= ng:
                continue                       # already reached cheaper/equal
            best[nk] = ng
            counter += 1
            heapq.heappush(pq, (ng, counter, nxt, path + [action.get("name")]))
    return None


# ── Config-bound lane wrappers (#53). The OPTIONAL deterministic GOAP planner
# lane (alongside the LLM DAG): when a task's steps have KNOWN pre/post-conditions,
# ordering is a search problem with one correct answer -- the solver above resolves
# it deterministically (reproducible, no LLM). DEFAULT-OFF ([goap].mode != enabled)
# -> _goap_plan returns None and the LLM DAG planner in server.py is unchanged. The
# action model is SSOT in mios.toml [goap].actions. This is the LANE (available +
# optional); auto-selecting GOAP vs the LLM DAG for a request is the follow-on.
def _goap_actions() -> list:
    sect = _toml_section("goap")
    acts = sect.get("actions") if isinstance(sect, dict) else None
    return acts if isinstance(acts, list) else []


def _goap_enabled() -> bool:
    return str(_toml_section("goap").get("mode", "off")).strip().lower() \
        in {"available", "on", "enforce", "1", "true", "yes"}


def _goap_plan(goal: dict, initial: "Optional[dict]" = None) -> "Optional[list]":
    """Deterministic min-cost plan (list of verb names) for a goal whose action
    model is declared in [goap].actions, or None when the lane is off / the action
    set is invalid / the goal is unreachable. Degrade-open: never raises into the
    request path."""
    if not _goap_enabled():
        return None
    acts = _goap_actions()
    if not acts or validate_actions(acts):
        return None
    try:
        return plan(dict(initial or {}), dict(goal or {}), acts)
    except Exception:  # noqa: BLE001 -- degrade-open
        return None
