# AI-hint: CaMeL-class architectural prompt-injection defense -- Meta's "Agents Rule of Two" composed as a DETERMINISTIC (not probabilistic) dispatch gate.
# AI-doc: usr/share/doc/mios/manual/routing.md

from __future__ import annotations

import mios_sandbox

PROP_UNTRUSTED = "untrusted_input"    # A
PROP_SENSITIVE = "sensitive_access"   # B
PROP_STATECHANGE = "state_change"     # C

MODE_OFF, MODE_AUDIT, MODE_ENFORCE = "off", "audit", "enforce"
_MODES = (MODE_OFF, MODE_AUDIT, MODE_ENFORCE)

ACT_PROCEED, ACT_AUDIT, ACT_GATE = "proceed", "audit", "gate"
_ALL_THREE_ACTION = {MODE_OFF: ACT_PROCEED, MODE_AUDIT: ACT_AUDIT, MODE_ENFORCE: ACT_GATE}

def normalize_mode(mode) -> str:
    """Resolve the SSOT mode value to a known enum; an empty/unknown token -> off
    (degrade-open: an unrecognised mode never silently enforces or audits)."""
    m = str(mode or "").strip().lower()
    return m if m in _MODES else MODE_OFF

def is_state_change(permission_tier) -> bool:
    try:
        return bool(mios_sandbox.resolve_profile(permission_tier).confined)
    except Exception:  # noqa: BLE001 -- fail-safe: an unclassifiable tier is treated as side-effecting
        return True

class RuleOfTwoVerdict:
    """The deterministic verdict for one (session_tainted, verb) evaluation: which of
    {A,B,C} are present, how many, whether all three hold, the SSOT mode in force, and
    the resulting action (proceed | audit | gate). Pure data -- the caller maps the
    action onto the dispatch outcome (proceed / audit-log / HITL-block)."""

    __slots__ = ("properties", "count", "all_three", "mode", "action")

    def __init__(self, properties: dict, mode: str) -> None:
        self.properties = {k: bool(v) for k, v in properties.items()}
        self.count = sum(1 for v in self.properties.values() if v)
        self.all_three = self.count >= 3
        self.mode = normalize_mode(mode)
        self.action = _ALL_THREE_ACTION[self.mode] if self.all_three else ACT_PROCEED

    def to_dict(self) -> dict:
        return {"properties": dict(self.properties), "count": self.count,
                "all_three": self.all_three, "mode": self.mode, "action": self.action}

def evaluate(*, session_tainted, permission_tier, sensitive,
             mode: str = MODE_OFF) -> RuleOfTwoVerdict:
    props = {
        PROP_UNTRUSTED: bool(session_tainted),
        PROP_SENSITIVE: bool(sensitive),
        PROP_STATECHANGE: is_state_change(permission_tier),
    }
    return RuleOfTwoVerdict(props, mode)
