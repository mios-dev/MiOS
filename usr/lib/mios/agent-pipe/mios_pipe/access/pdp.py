# AI-hint: WS-A9 Policy Decision Point (PDP) -- the pure capability/risk decision core shared by the agent-pipe's RBAC SURFACE filters (_agent_rbac_filter...
# AI-doc: usr/share/doc/mios/manual/access.md

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
