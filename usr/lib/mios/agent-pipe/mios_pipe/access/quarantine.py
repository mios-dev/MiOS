# AI-hint: CaMeL dual-context QUARANTINE boundary -- the deeper half of the F2/T-033 prompt-injection defense (Debenedetti et al., "Defeating Prompt Injections by Design"), composed as a DETERMINISTIC (not probabilistic) dispatch gate that is STRICTER than the Rule-of-Two sibling. The CaMeL principle: untrusted/attacker-controllable content (web/file/tool output that TAINTS the session) must not be able to make the privileged action-planner take a sensitive OR state-changing action it would not otherwise. The MiOS expression: the boundary BITES when the session is TAINTED (axis A -- the EXISTING provenance-taint signal, passed in as session_tainted) AND the verb is PRIVILEGED -- i.e. it READS sensitive/private data (axis B -- the SSOT [verbs.*].sensitive flag) OR mutates state / has side-effects (axis C -- derived from the SSOT [verbs.*].permission tier via the EXISTING mios_ruleof2.is_state_change policy). Where Rule-of-Two gates the all-three case (A AND B AND C), quarantine-enforce additionally gates the tainted+(B OR C) case -- a STRICTER posture for full CaMeL isolation. Pure + stdlib + composes EXISTING signals (the SAME taint bool, the SAME SSOT verb metadata, the SAME tier->side-effect derivation as T-033) -- no re-invented taint/privilege logic, no English-keyword classifier. The SSOT [security].quarantine_mode (off|audit|enforce) enum + its degrade-open normaliser are SHARED VERBATIM with mios_ruleof2 so the two architectural gates can never drift. This module owns ONLY the deterministic decision so it unit-tests in isolation; mios_dispatch / server.py own the wiring (the mode flag, the chokepoint placement, the mios_hitl.decide routing). NEVER imports server.
# AI-related: ./mios_ruleof2.py, ./mios_sandbox.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_firewall.py, /usr/share/mios/mios.toml, ./test_mios_quarantine.py
# AI-functions: normalize_mode, evaluate, quarantined_extract, class QuarantineVerdict
"""mios_quarantine -- the CaMeL dual-context quarantine gate (F2/T-033 deeper half).

Pure stdlib (+ the pure mios_ruleof2 sibling for the shared mode enum and the
tier->side-effect derivation). The CaMeL design (Debenedetti et al., "Defeating
Prompt Injections by Design") keeps untrusted/attacker-controllable content from
autonomously driving privileged actions. The SOUND, brick-safe MiOS expression of
that boundary is a DETERMINISTIC dispatch gate:

  A  untrusted-input : the session ingested attacker-controllable content (the
                       EXISTING provenance-taint chain; passed in as ``session_tainted``).
  B  sensitive-access: the verb READS sensitive / private / cross-tenant data (the SSOT
                       ``[verbs.*].sensitive`` flag -- additive metadata, not a keyword
                       classifier).
  C  state-change    : the verb mutates state / has external side-effects (derived from
                       the SSOT ``[verbs.*].permission`` tier via the EXISTING
                       ``mios_ruleof2.is_state_change`` policy).

The quarantine boundary BITES when the session is TAINTED (A) AND the verb is
PRIVILEGED -- it either reads sensitive data (B) OR changes state (C). When it bites
the dispatch must be GATED (routed to human review) or BLOCKED; otherwise it proceeds.

This is the STRICTER superset of the Rule-of-Two gate (mios_ruleof2). Rule-of-Two
gates only the all-three chain (A AND B AND C); quarantine-enforce additionally gates
the tainted + (B OR C) case -- the posture you want when you require full CaMeL
isolation: untrusted-content-derived privileged actions cannot fire autonomously; a
human (or a non-tainted plan) must authorize them.

This module is the testable DECISION only. It composes signals the rest of the pipe
already computes -- it does NOT re-derive taint (mios_firewall owns A) or privilege
(the SSOT verb metadata owns B; mios_ruleof2 owns C's derivation). It NEVER imports
server; the wiring (the mode flag, the chokepoint placement, the HITL routing) lives
in mios_dispatch / server.py, composing this gate with the existing
firewall/HITL/Rule-of-Two gates via stricter-wins at the SINGLE dispatch chokepoint
(so there is no second action path that bypasses it).

SOUNDNESS NOTE: the boundary is sound because it sits at the SAME single chokepoint as
the existing gates and only ADDS refusals (stricter-wins composition) -- enabling
quarantine can make the posture stricter, never weaker. The Q-LLM extraction seam
below (``quarantined_extract``) is the OPTIMIZATION on top of this required core; it is
STUBBED (degrade-open to None) as the documented next increment.
"""

from __future__ import annotations

import mios_ruleof2

# Reuse T-033's SSOT mode enum VERBATIM: ``[security].quarantine_mode`` shares the
# EXACT tri-state semantics (off | audit | enforce) with ``[security].rule_of_two_mode``,
# so the enum tokens AND the degrade-open normaliser are SHARED (no second copy of the
# mode literals -- a single SSOT for the architectural-gate mode vocabulary).
MODE_OFF = mios_ruleof2.MODE_OFF
MODE_AUDIT = mios_ruleof2.MODE_AUDIT
MODE_ENFORCE = mios_ruleof2.MODE_ENFORCE

# The three structural axis keys (reused from mios_ruleof2 -- structural identifiers,
# no English/topic content: they name the dataflow axes, not any verb or domain). The
# quarantine boundary is concerned with A and the UNION B-or-C ("privileged").
PROP_UNTRUSTED = mios_ruleof2.PROP_UNTRUSTED       # A -- attacker-controllable content present
PROP_SENSITIVE = mios_ruleof2.PROP_SENSITIVE       # B -- reads sensitive / private data
PROP_STATECHANGE = mios_ruleof2.PROP_STATECHANGE   # C -- mutates state / side effects

# Per-mode action WHEN THE BOUNDARY BITES (tainted AND privileged). When it does not
# bite the action is always "proceed" regardless of mode (untrusted content is absent,
# or the verb is neither sensitive nor state-changing -- nothing to quarantine). Pure
# enum dispatch over the SSOT mode value (not a content heuristic) -- mirrors the
# Rule-of-Two action matrix so the two gates stay structurally identical.
ACT_PROCEED, ACT_AUDIT, ACT_GATE = "proceed", "audit", "gate"
_BITE_ACTION = {MODE_OFF: ACT_PROCEED, MODE_AUDIT: ACT_AUDIT, MODE_ENFORCE: ACT_GATE}


def normalize_mode(mode) -> str:
    """Resolve the SSOT ``[security].quarantine_mode`` value to a known enum; an
    empty/unknown token -> off (degrade-open: an unrecognised mode never silently
    enforces or audits). Delegates to the SHARED T-033 normaliser so the two
    architectural-gate modes can never drift in their parsing."""
    return mios_ruleof2.normalize_mode(mode)


class QuarantineVerdict:
    """The deterministic verdict for one ``(session_tainted, verb)`` quarantine
    evaluation: which axes are present (A / B / C), whether the verb is privileged
    (B OR C), whether the boundary BITES (tainted AND privileged), the SSOT mode in
    force, and the resulting action (proceed | audit | gate). Pure data -- the caller
    maps the action onto the dispatch outcome (proceed / audit-log / HITL-block)."""

    __slots__ = ("untrusted", "sensitive", "state_change", "privileged",
                 "bites", "mode", "action")

    def __init__(self, *, untrusted, sensitive, state_change, mode) -> None:
        self.untrusted = bool(untrusted)
        self.sensitive = bool(sensitive)
        self.state_change = bool(state_change)
        # "Privileged" = the action either READS sensitive data (B) OR CHANGES state
        # (C). The CaMeL dual-context boundary cares about EITHER -- untrusted content
        # must not autonomously drive a sensitive read OR a state change. (Rule-of-Two
        # requires BOTH B AND C alongside A; quarantine is the stricter superset.)
        self.privileged = self.sensitive or self.state_change
        # The boundary BITES only when untrusted content is PRESENT and the action is
        # privileged: an untrusted-content-derived privileged action cannot fire
        # autonomously. Untainted sessions (A absent) never bite -- quarantine only
        # constrains the dataflow once attacker-controllable content is in scope.
        self.bites = self.untrusted and self.privileged
        self.mode = normalize_mode(mode)
        self.action = _BITE_ACTION[self.mode] if self.bites else ACT_PROCEED

    def to_dict(self) -> dict:
        return {
            "properties": {
                PROP_UNTRUSTED: self.untrusted,
                PROP_SENSITIVE: self.sensitive,
                PROP_STATECHANGE: self.state_change,
            },
            "privileged": self.privileged,
            "bites": self.bites,
            "mode": self.mode,
            "action": self.action,
        }


def evaluate(*, session_tainted, permission_tier, sensitive,
             mode: str = MODE_OFF) -> QuarantineVerdict:
    """Evaluate the quarantine boundary for one verb dispatch. Inputs:

      session_tainted -- axis A, the EXISTING provenance-taint signal (bool;
                         mios_firewall owns it -- not re-derived here).
      permission_tier -- the verb's SSOT ``[verbs.*].permission`` (drives axis C via
                         the SAME ``mios_ruleof2.is_state_change`` derivation T-033 uses).
      sensitive       -- the verb's SSOT ``[verbs.*].sensitive`` flag (axis B).
      mode            -- the SSOT ``[security].quarantine_mode`` in force.

    Returns a :class:`QuarantineVerdict`. Total + pure: never raises (an unclassifiable
    tier degrades to side-effecting via :func:`mios_ruleof2.is_state_change`), so a
    call-site can treat any exception as impossible and keep its own degrade-open
    fallback for the I/O around it. Re-derives NOTHING -- it composes the three signals
    the rest of the pipe already computes."""
    return QuarantineVerdict(
        untrusted=session_tainted,
        sensitive=sensitive,
        state_change=mios_ruleof2.is_state_change(permission_tier),
        mode=mode)


def quarantined_extract(untrusted_content, *, schema=None):
    """Q-LLM EXTRACTION SEAM (CaMeL dual-context) -- STUBBED, degrade-open to None.

    The full CaMeL design routes untrusted content to a QUARANTINED LLM that may ONLY
    extract structured data and CANNOT emit actions, while a privileged planner LLM --
    which never sees the raw untrusted text -- composes the action plan over that
    extracted data (capability-tracked dataflow between two isolated contexts). That
    dual-context split is a larger change to the orchestrator's context plumbing (a
    second constrained inference lane + the data-vs-control flow tracking between the
    contexts), so it is STUBBED here as the documented NEXT INCREMENT.

    The SOUND GATE (:func:`evaluate` wired at the dispatch chokepoint) is the REQUIRED
    core and is INDEPENDENT of this seam: it makes untrusted-content-derived privileged
    actions non-autonomous whether or not this extraction lane exists. This stub
    returning ``None`` means "no constrained extraction available" -> the caller
    proceeds exactly as today (degrade-open); it NEVER newly-opens the gate (the gate
    does not depend on this seam, so a None here cannot weaken the boundary).

    Intended interface (future): ``untrusted_content`` is the raw attacker-controllable
    text; ``schema`` constrains the structured shape the quarantined extractor may emit;
    the return is that structured data (no free-form text, no action tokens) or None."""
    return None
