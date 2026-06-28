# AI-hint: WS-A14 SSOT-derived security sets. Pure-stdlib resolver that derives the agent-pipe's high-privilege verb set (the taint-firewall + HITL gate scope) and the always-taint verb set from the SSOT ([security].firewall_high_privilege_verbs / [security].taint_verbs) UNIONED with the curated in-code base -- so the firewall scope is driven by mios.toml, not a hardcoded literal that silently drifts from the SSOT list. provenance() reports curated-vs-SSOT origin for the introspection endpoint. server.py owns the wiring (read mios.toml, build the module-level sets, feed the firewall/HITL gate); this module owns only the deterministic set math.
# AI-related: ./server.py, /usr/share/mios/mios.toml, ./mios_hitl.py, ./mios_pdp.py, ./test_mios_secset.py
# AI-functions: high_privilege_set, taint_verb_set, provenance
"""mios_secset -- SSOT-derived security verb sets (WS-A14, the AIOS Access-Manager
firewall/HITL scope layer).

Pure stdlib. The taint firewall + the HITL block gate key off a "high-privilege"
verb set; before WS-A14 that set was a hardcoded Python literal that could drift
from the SSOT [security].firewall_high_privilege_verbs list (which existed but
was never consumed). This module derives the EFFECTIVE set as
curated_base ∪ SSOT_list -- the curated base is the never-removed floor (a verb
the code knows is dangerous can't be dropped by an SSOT edit), and the SSOT can
ADD verbs without a code change. Same pattern for the always-taint verb set.
"""

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
