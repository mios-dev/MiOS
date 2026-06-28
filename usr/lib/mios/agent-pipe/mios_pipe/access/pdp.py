# AI-hint: WS-A9 Policy Decision Point (PDP) -- the pure capability/risk decision core shared by the agent-pipe's RBAC SURFACE filters (_agent_rbac_filter/_user_rbac_filter) AND the dispatch-time gate in _dispatch_mios_verb_inner, so a verb pruned from a caller's tool surface can NEVER still dispatch (the bypass WS-A9 closes). One decide() applies denied_verbs / allowed_verbs / a max_permission risk ceiling to a verb. Critically it FIXES the fail-OPEN defect: a non-empty-but-UNKNOWN max_permission used to mean "no ceiling" (silently granting everything); resolve_ceiling() now FAILS CLOSED to the safest tier. server.py owns the wiring (contextvars for the dispatching agent + the request user, the audit-event emit, the SSOT [agents.*]/[users.*] policy keys); this module owns only the decision logic.
# AI-related: ./server.py, ./mios_sched.py, /usr/share/mios/mios.toml, ./test_mios_pdp.py, ./automation/99-postcheck.sh
# AI-functions: permission_rank, resolve_ceiling, decide, class Decision
"""mios_pdp -- the MiOS agent-pipe Policy Decision Point (WS-A9, the AIOS
Access-Manager capability gate).

Pure stdlib so it unit-tests in isolation, in the sibling-module style of
mios_sched / mios_toolconflict / mios_trace. server.py owns the wiring (the
dispatching-agent + request-user contextvars, the audit-event emit, and the
SSOT [agents.<name>] / [users.<name>] policy keys); this module owns only the
DECISION: given a verb + a caller's policy, allow or deny.

The bypass it closes
====================
Before WS-A9 the per-agent and per-user RBAC ran ONLY at surface-build time
(pruning the model-facing tool list). The dispatch chokepoint did taint-firewall
+ HITL + enum validation but NO capability check -- so a verb absent from the
filtered surface (a stale tool_call, a direct/MCP/A2A caller, a model that
fabricated a name) would still dispatch. WS-A9 routes BOTH the surface filters
AND the dispatch gate through THIS one decide(), so surface and dispatch can
never diverge.

The fail-OPEN defect it fixes
=============================
The old filters computed `max_rank = rank(mp) if mp in TIERS else None`, i.e. a
max_permission naming an UNKNOWN tier (a config typo) collapsed to None == "no
ceiling" -> the caller silently kept the FULL surface. That is fail-OPEN on the
security axis. resolve_ceiling() now returns rank 0 (the safest tier only) for a
non-empty-but-unknown ceiling -> FAIL CLOSED. (An empty/absent max_permission is
still "no ceiling", the genuine no-op default.)

Decision semantics (decide)
===========================
  * `name` in denied_verbs            -> DENY  (applies to verbs AND non-verbs).
  * not a catalog verb (recipe/skill/MCP/client tool) -> ALLOW (only denied applies).
  * allowed_verbs set and `name` not in it            -> DENY.
  * max_permission ceiling set and the verb's tier outranks it -> DENY.
  * otherwise ALLOW.
An empty policy (no denied/allowed/ceiling) trivially allows everything -> the
ZERO-behaviour-change default for single-user MiOS.
"""

from __future__ import annotations

from typing import Iterable, Optional


class Decision:
    """Result of a PDP evaluation. `allow` is the verdict; `rule` names the
    clause that decided it; `reason` is a human-readable refusal string."""

    __slots__ = ("allow", "rule", "reason")

    def __init__(self, allow: bool, rule: str = "ok", reason: str = "") -> None:
        self.allow = bool(allow)
        self.rule = str(rule)
        self.reason = str(reason)

    def __repr__(self) -> str:  # pragma: no cover -- debug aid
        return f"Decision(allow={self.allow}, rule={self.rule!r})"


def _tiers(tiers: Iterable[str]) -> list:
    return [str(t).strip().lower() for t in (tiers or []) if str(t).strip()]


def permission_rank(perm: str, tiers: Iterable[str]) -> int:
    """Risk rank of a permission tier (lower = safer). A tier NOT in the lattice
    ranks ABOVE the top (most restrictive) so an unclassified verb is gated, not
    granted -- fail-closed on the risk axis (mirrors server._perm_rank)."""
    t = _tiers(tiers)
    p = str(perm or "").strip().lower()
    try:
        return t.index(p)
    except ValueError:
        return len(t)


def resolve_ceiling(max_perm: str, tiers: Iterable[str]) -> Optional[int]:
    """Ceiling rank for a configured max_permission.

      ""  / absent      -> None  (no ceiling -- the genuine no-op default)
      a KNOWN tier       -> its rank
      a NON-EMPTY UNKNOWN tier -> 0  (FAIL CLOSED: only the safest tier passes)

    The last case is the WS-A9 fix for the old fail-OPEN behaviour (unknown ->
    None -> no ceiling -> full surface granted on a config typo)."""
    mp = str(max_perm or "").strip().lower()
    if not mp:
        return None
    t = _tiers(tiers)
    if mp in t:
        return t.index(mp)
    return 0  # fail-closed: an unrecognised ceiling restricts to the safest tier


def decide(name: str, *, in_catalog: bool, verb_perm: str,
           denied: Iterable[str], allowed: Iterable[str],
           ceiling_rank: Optional[int], tiers: Iterable[str]) -> Decision:
    """Evaluate one verb/tool against one caller's policy. See module docstring
    for the clause order. `ceiling_rank` is the output of resolve_ceiling()."""
    nm = str(name or "")
    denied_s = {str(v) for v in (denied or [])}
    allowed_s = {str(v) for v in (allowed or [])}
    if nm in denied_s:
        return Decision(False, "denied_verbs",
                        f"'{nm}' is in the caller's denied_verbs")
    if not in_catalog:
        # Non-verb tools (recipes / skills / MCP / client tools) are only gated
        # by an explicit denied_verbs entry (handled above); pass otherwise.
        return Decision(True, "non_verb", "")
    if allowed_s and nm not in allowed_s:
        return Decision(False, "allowed_verbs",
                        f"'{nm}' is not in the caller's allowed_verbs")
    if ceiling_rank is not None:
        if permission_rank(verb_perm, tiers) > ceiling_rank:
            return Decision(False, "max_permission",
                            f"'{nm}' ({verb_perm}-tier) exceeds the caller's "
                            f"max_permission ceiling")
    return Decision(True, "ok", "")
