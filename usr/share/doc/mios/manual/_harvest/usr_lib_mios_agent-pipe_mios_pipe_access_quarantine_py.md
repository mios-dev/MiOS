<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_quarantine -- the CaMeL dual-context quarantine gate...

mios_quarantine -- the CaMeL dual-context quarantine gate (F2/T-033 deeper half).

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

<!-- mios-src:05f8230994f2 from usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py:3-43 -->

### Resolve the SSOT ``[security].quarantine_mode`` value to a...

Resolve the SSOT ``[security].quarantine_mode`` value to a known enum; an
    empty/unknown token -> off (degrade-open: an unrecognised mode never silently
    enforces or audits). Delegates to the SHARED T-033 normaliser so the two
    architectural-gate modes can never drift in their parsing.

<!-- mios-src:18e6b11e275d from usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py:62-65 -->

### Evaluate the quarantine boundary for one verb dispatch....

Evaluate the quarantine boundary for one verb dispatch. Inputs:

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
    the rest of the pipe already computes.

<!-- mios-src:eec468986ef1 from usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py:104-117 -->

### Q-LLM EXTRACTION SEAM (CaMeL dual-context) -- STUBBED...

Q-LLM EXTRACTION SEAM (CaMeL dual-context) -- STUBBED, degrade-open to None.

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
    the return is that structured data (no free-form text, no action tokens) or None.

<!-- mios-src:360c65b513a9 from usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py:126-145 -->
