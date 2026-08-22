<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_ruleof2 -- the Rule-of-Two architectural...

mios_ruleof2 -- the Rule-of-Two architectural prompt-injection gate (CaMeL-class).

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

<!-- mios-src:6eb0f4fdd6a9 from usr/lib/mios/agent-pipe/mios_pipe/routing/ruleof2.py:3-35 -->

### Property C

Property C: does the verb mutate state / have side-effects? Derived from the
    SSOT ``[verbs.*].permission`` tier via the EXISTING tier->confinement policy in
    mios_sandbox -- ``read`` is a pure-info tier (no confinement) so NOT a state
    change; ``write`` / ``interactive`` resolve to a confined profile (touches the
    fs / injects input) so they ARE. Reusing ``resolve_profile`` keeps the tier
    semantics SSOT (no restated ``{write, interactive}`` literal) and inherits its
    FAIL-CLOSED posture: an unknown/missing tier resolves to the strictest (confined)
    profile, so it counts as a state change (conservative -- fail toward gating).

<!-- mios-src:ee830813846c from usr/lib/mios/agent-pipe/mios_pipe/routing/ruleof2.py:60-67 -->

### Evaluate the Rule of Two for one verb dispatch. Inputs...

Evaluate the Rule of Two for one verb dispatch. Inputs:

      session_tainted -- property A, the EXISTING provenance-taint signal (bool).
      permission_tier -- the verb's SSOT ``[verbs.*].permission`` (drives property C).
      sensitive       -- the verb's SSOT ``[verbs.*].sensitive`` flag (property B).
      mode            -- the SSOT ``[security].rule_of_two_mode`` in force.

    Returns a :class:`RuleOfTwoVerdict`. Total + pure: never raises (an unclassifiable
    tier degrades to side-effecting via :func:`is_state_change`), so a call-site can
    treat any exception as impossible and keep its own degrade-open fallback for I/O.

<!-- mios-src:2e7c89d49b84 from usr/lib/mios/agent-pipe/mios_pipe/routing/ruleof2.py:96-105 -->
