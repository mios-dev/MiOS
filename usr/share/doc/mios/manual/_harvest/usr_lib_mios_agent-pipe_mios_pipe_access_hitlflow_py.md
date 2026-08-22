<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_hitlflow -- HITL ask-to-run + runtime approval-gate...

mios_hitlflow -- HITL ask-to-run + runtime approval-gate flow.

Extracted verbatim from ``server.py`` (R7 security wave). Holds the WS-6 runtime
HITL gate, the structural action-identity hashers, the chat-native ask-to-run
approval round-trip (propose -> model-classified approval -> per-action-hash
bypass -> re-dispatch) and the Reflexion episodic read-side. ``server.py``
re-imports every name under its original alias so the public surface is
byte-identical.

SECURITY-CRITICAL: the gates are NAME-KEYED on verb keys + permission tiers.
Nothing is renamed; the moved bodies are unchanged. ``mios_hitl`` (pure decision
helpers), ``mios_jsonsalvage``, ``mios_pg`` and ``mios_sse`` are imported
directly from their sibling modules; every other server-side symbol the flow
touches (the HITL/ASK config scalars, the router/planner endpoints, the
``_db_*`` / ``_pg_mirror`` DB helpers, ``_emit_session_event``,
``_row_age_seconds``, ``_usage_estimate``, the ``_hitl_approved_var``
ContextVar and ``dispatch_mios_verb``) is injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``).

<!-- mios-src:68ed64864f19 from usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py:3-21 -->

### The runtime HITL gate ([hitl] verb-scope half), called from...

The runtime HITL gate ([hitl] verb-scope half), called from
    _dispatch_mios_verb_inner for scoped verbs. Returns a block_result dict to REFUSE
    the dispatch (gate mode, not yet approved) or None to PROCEED. The block/proceed
    verdict is computed by the SINGLE shared resolver (``mios_hitl.decide``) that the
    [ai] risk-tier gate also routes through, so the two HITL gates can no longer
    disagree. Always emits an observability event. Never raises -> degrade-open to
    PROCEED (an agent is never wedged by the gate failing).

<!-- mios-src:472346b93151 from usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py:200-206 -->

### Generative judge (NO phrase list -- operator "NOTHING...

Generative judge (NO phrase list -- operator "NOTHING HARDCODED"): given the
    PROPOSED action + the user's reply, classify BY MEANING as 'approve' (run it now),
    'reject' (skip it), or 'unrelated' (a new request, not an answer to the proposal).
    Only called when a proposal is actually pending. Degrade -> 'unrelated' on any
    error (SAFE: the action stays un-run; the user can re-confirm). Never auto-runs on
    ambiguity.

<!-- mios-src:a5e3a762f92c from usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py:233-238 -->

### Reflexion episodic buffer (ref AIOS B.3 / Shinn et al....

Reflexion episodic buffer (ref AIOS B.3 / Shinn et al. 2023): pull
    recent `reflect_corrected` events for THIS session so a fresh
    reflection can REUSE a prior fix instead of re-deriving it. The audit
    flagged these rows as write-only -- this is the missing read side.
    Best-effort: returns [] on any DB miss so reflection never blocks.

<!-- mios-src:5011b5d04f9e from usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py:382-386 -->
