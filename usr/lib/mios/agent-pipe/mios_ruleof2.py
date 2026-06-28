# AI-hint: CaMeL-class architectural prompt-injection defense -- Meta's "Agents Rule of Two" composed as a DETERMINISTIC (not probabilistic) dispatch gate. A turn/verb may hold AT MOST TWO of three properties without human review: (A) untrusted-input -- the session ingested attacker-controllable content (the EXISTING provenance-taint signal, passed in as session_tainted); (B) sensitive-access -- the verb READS sensitive/private/cross-tenant data (the SSOT [verbs.*].sensitive flag, additive); (C) state-change -- the verb mutates state / has external side-effects (the SSOT [verbs.*].permission tier, mapped via the EXISTING mios_sandbox tier->confinement policy: read=pure-info, write/interactive=side-effecting). When ALL THREE hold the chain is the classic prompt-injection kill-chain (untrusted text -> reads secrets -> exfiltrates/acts) and must be gated. Pure + stdlib + composes EXISTING signals (no re-invented taint/privilege logic, no English-keyword classifier): A is the caller's taint bool, B is SSOT metadata, C is derived from the SSOT permission tier through mios_sandbox (FAIL-CLOSED: unknown tier -> side-effecting). server.py / mios_dispatch own the wiring + the mode flag; this module owns only the deterministic decision so it unit-tests in isolation. NEVER imports server.
# AI-related: ./mios_sandbox.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_firewall.py, /usr/share/mios/mios.toml, ./test_mios_ruleof2.py
# AI-functions: normalize_mode, is_state_change, evaluate, class RuleOfTwoVerdict
"""mios_ruleof2 -- the Rule-of-Two architectural prompt-injection gate (CaMeL-class).

Pure stdlib (+ the pure mios_sandbox sibling for the tier->side-effect policy). The
Rule of Two (Meta, "Agents Rule of Two") is a DETERMINISTIC invariant: an agent action
may combine at most TWO of three dangerous properties without human review --

  A  untrusted-input : the session ingested attacker-controllable content (the EXISTING
                       provenance-taint chain; passed in as ``session_tainted``).
  B  sensitive-access: the verb READS sensitive / private / cross-tenant data (the SSOT
                       ``[verbs.*].sensitive`` flag -- additive metadata, not a keyword
                       classifier).
  C  state-change    : the verb mutates state / has external side-effects (derived from
                       the SSOT ``[verbs.*].permission`` tier via the EXISTING
                       ``mios_sandbox`` tier->confinement policy).

When all three hold, the chain is the prompt-injection kill-chain (untrusted text ->
reads secrets -> exfiltrates/acts) and the dispatch must be GATED (routed to human
review) or BLOCKED. With two or fewer, it proceeds.

This module is the testable DECISION only. It composes signals the rest of the pipe
already computes -- it does NOT re-derive taint (mios_firewall owns A) or privilege
(the SSOT verb metadata owns B/C). It NEVER imports server; the wiring (the mode flag,
the chokepoint placement, the HITL routing) lives in mios_dispatch / server.py.

FOLLOW-UP (flagged, NOT built here): the deeper CaMeL design (Debenedetti et al.,
"Defeating Prompt Injections by Design") routes untrusted content to a QUARANTINED LLM
that may only extract structured data and CANNOT emit actions, while a privileged
planner LLM -- which never sees the raw untrusted text -- composes the action plan over
that data (dual-context / capability-tracked dataflow). That is a larger architectural
change to the orchestrator's context plumbing. This wave ships only the Rule-of-Two
COMPOSITION gate (the deterministic ceiling on dangerous-property combinations); the
quarantined-LLM / dual-context split is the natural next step on top of it.
"""

from __future__ import annotations

import mios_sandbox

# The three Rule-of-Two property keys (structural identifiers; no English/topic
# content -- they name the invariant's axes, not any verb or domain).
PROP_UNTRUSTED = "untrusted_input"    # A
PROP_SENSITIVE = "sensitive_access"   # B
PROP_STATECHANGE = "state_change"     # C

# The SSOT [security].rule_of_two_mode enum. off = the evaluator is not consulted
# (byte-identical behaviour); audit = on all-three, log a structured audit line and
# proceed (observe before enforce); enforce = on all-three, route to HITL review /
# block (fail-safe -- a 3-property chain requires a human).
MODE_OFF, MODE_AUDIT, MODE_ENFORCE = "off", "audit", "enforce"
_MODES = (MODE_OFF, MODE_AUDIT, MODE_ENFORCE)

# Per-mode action when ALL THREE properties hold. <=2 properties always -> "proceed"
# regardless of mode (the invariant is satisfied). Pure enum dispatch over the SSOT
# mode value -- not a content heuristic.
ACT_PROCEED, ACT_AUDIT, ACT_GATE = "proceed", "audit", "gate"
_ALL_THREE_ACTION = {MODE_OFF: ACT_PROCEED, MODE_AUDIT: ACT_AUDIT, MODE_ENFORCE: ACT_GATE}


def normalize_mode(mode) -> str:
    """Resolve the SSOT mode value to a known enum; an empty/unknown token -> off
    (degrade-open: an unrecognised mode never silently enforces or audits)."""
    m = str(mode or "").strip().lower()
    return m if m in _MODES else MODE_OFF


def is_state_change(permission_tier) -> bool:
    """Property C: does the verb mutate state / have side-effects? Derived from the
    SSOT ``[verbs.*].permission`` tier via the EXISTING tier->confinement policy in
    mios_sandbox -- ``read`` is a pure-info tier (no confinement) so NOT a state
    change; ``write`` / ``interactive`` resolve to a confined profile (touches the
    fs / injects input) so they ARE. Reusing ``resolve_profile`` keeps the tier
    semantics SSOT (no restated ``{write, interactive}`` literal) and inherits its
    FAIL-CLOSED posture: an unknown/missing tier resolves to the strictest (confined)
    profile, so it counts as a state change (conservative -- fail toward gating)."""
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
        # The invariant: a chain may hold at most TWO properties without review.
        self.all_three = self.count >= 3
        self.mode = normalize_mode(mode)
        self.action = _ALL_THREE_ACTION[self.mode] if self.all_three else ACT_PROCEED

    def to_dict(self) -> dict:
        return {"properties": dict(self.properties), "count": self.count,
                "all_three": self.all_three, "mode": self.mode, "action": self.action}


def evaluate(*, session_tainted, permission_tier, sensitive,
             mode: str = MODE_OFF) -> RuleOfTwoVerdict:
    """Evaluate the Rule of Two for one verb dispatch. Inputs:

      session_tainted -- property A, the EXISTING provenance-taint signal (bool).
      permission_tier -- the verb's SSOT ``[verbs.*].permission`` (drives property C).
      sensitive       -- the verb's SSOT ``[verbs.*].sensitive`` flag (property B).
      mode            -- the SSOT ``[security].rule_of_two_mode`` in force.

    Returns a :class:`RuleOfTwoVerdict`. Total + pure: never raises (an unclassifiable
    tier degrades to side-effecting via :func:`is_state_change`), so a call-site can
    treat any exception as impossible and keep its own degrade-open fallback for I/O."""
    props = {
        PROP_UNTRUSTED: bool(session_tainted),
        PROP_SENSITIVE: bool(sensitive),
        PROP_STATECHANGE: is_state_change(permission_tier),
    }
    return RuleOfTwoVerdict(props, mode)
