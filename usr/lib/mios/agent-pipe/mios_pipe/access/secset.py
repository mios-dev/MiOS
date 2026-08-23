# AI-hint: WS-A14 SSOT-derived security sets. Pure-stdlib resolver that derives the agent-pipe's high-privilege verb set (the taint-firewall + HITL gat...
# AI-doc: usr/share/doc/mios/manual/access.md

from __future__ import annotations

from typing import Iterable, Set


def _norm(items: Iterable) -> Set[str]:
    return {str(v).strip() for v in (items or [])
            if v is not None and str(v).strip()}


def high_privilege_set(curated: Iterable, ssot_extra: Iterable) -> Set[str]:
    """Effective high-privilege verb set = curated base ∪ SSOT additions. The
    curated base is the floor (never droppable by config); the SSOT only adds."""
    return _norm(curated) | _norm(ssot_extra)


def taint_verb_set(builtin: Iterable, ssot_extra: Iterable) -> Set[str]:
    """Always-taint verb set = built-in external-fetch verbs ∪ SSOT
    [security].taint_verbs (a verb whose own execution introduces taint)."""
    return _norm(builtin) | _norm(ssot_extra)


def provenance(curated: Iterable, ssot_extra: Iterable) -> dict:
    """Origin breakdown for the introspection endpoint: totals + which verbs are
    SSOT-only (added by config) vs curated-only (in-code floor)."""
    cur, ss = _norm(curated), _norm(ssot_extra)
    return {
        "total": len(cur | ss),
        "curated": len(cur),
        "ssot": len(ss),
        "ssot_only": sorted(ss - cur),
        "curated_only": sorted(cur - ss),
        "source": "curated_base + [security].firewall_high_privilege_verbs",
    }
