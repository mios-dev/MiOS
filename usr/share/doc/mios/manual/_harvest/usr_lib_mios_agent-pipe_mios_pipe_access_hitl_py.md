<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_hitl -- pure decision helpers for the WS-6 runtime...

mios_hitl -- pure decision helpers for the WS-6 runtime HITL approval gate.

DB-free + stdlib-only so the scope-resolution and gate-decision logic unit-tests
in isolation (sibling-module pattern, like mios_sched / mios_evict). server.py
owns the pgvector pending_action I/O, the event emission, and the approval
endpoints; this module owns only the deterministic, testable decisions.

Modes:
  "log"  (default) -- NON-BLOCKING: record + emit an observability event, then
                      proceed. The autonomous swarm is never deadlocked.
  "gate"           -- BLOCKING: a scoped verb is refused (block_result) and a
                      pending_action row is written until approved out-of-band;
                      the agent's later retry of the same action then passes.

<!-- mios-src:af720917be27 from usr/lib/mios/agent-pipe/mios_pipe/access/hitl.py:3-16 -->

### THE single HITL verdict, reconciling the [ai] risk-tier...

THE single HITL verdict, reconciling the [ai] risk-tier gate, the [hitl]
    verb-scope gate, the Rule-of-Two architectural gate AND the CaMeL quarantine gate.
    Each gate is evaluated ONLY within its own scope; the result is the STRICTER of
    their postures (proceed < observe < block) so that if ANY gate would block this
    verb, it blocks (fail-safe -- the gates can never disagree on the blocking
    outcome). The Rule-of-Two gate contributes a BLOCK posture (`ro2_block=True`) when a
    dispatch holds all three dangerous properties under enforce mode -- the
    deterministic kill-chain refusal (mios_ruleof2). The CaMeL quarantine gate
    contributes a BLOCK posture (`quarantine_block=True`) when a TAINTED session would
    autonomously drive a PRIVILEGED (sensitive-read OR state-change) action under
    enforce mode -- the stricter dual-context refusal (mios_quarantine). `approved`
    downgrades a BLOCK to OBSERVE so an explicitly-approved action runs. Returns
    PROCEED / OBSERVE / BLOCK. Pure + total: it never raises (call-sites stay
    degrade-open on their own I/O, but the DECISION itself errs toward blocking, never
    toward a silent execution). `ro2_block` / `quarantine_block` both default False ->
    inert for the existing call-sites (byte-identical verdict).

<!-- mios-src:52ccc6eeb8ae from usr/lib/mios/agent-pipe/mios_pipe/access/hitl.py:89-104 -->
