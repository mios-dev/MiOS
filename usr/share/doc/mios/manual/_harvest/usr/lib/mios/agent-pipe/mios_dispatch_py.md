<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Verb->bash dispatch chokepoint -- the...

Verb->bash dispatch chokepoint -- the taint->firewall->HITL->broker launcher.

Extracted verbatim from ``server.py`` (refactor R7). Holds the SSOT command-
template renderer (``_template_to_cmd``), the per-verb dispatch-command builder
(``_build_dispatch_cmd`` -- the launch_app / window_op / os_recipe / pkg / pc_* /
text_* / powershell_run guard registry) and the launcher proper
(``dispatch_mios_verb`` / ``_dispatch_bounded`` / ``_dispatch_mios_verb_inner``).
``server.py`` re-imports every name under its original alias so the module's
public surface is byte-identical.

The moved bodies are UNCHANGED. ``_classify_verb_taint`` / ``_session_is_tainted``
(mios_firewall), ``_hitl_block_reason`` / ``_HITL_ARBITER_URL`` /
``_hitl_arbiter_verdict`` / ``_match_user_cfg`` / ``_dispatch_quota_reason`` /
``_dispatch_pdp_reason`` (mios_policy), ``_action_hash`` / ``_pending_hash`` /
``_hitl_record_pending`` / ``_hitl_gate`` (mios_hitlflow) and ``_loads_lenient``
(mios_jsonsalvage) are imported directly from their sibling modules; ``mios_sandbox``
is imported as a module. Every other server-side symbol they touch (the verb
catalog, the broker socket path, the DB-event helpers, the dispatch ContextVars,
the sandbox-profile resolver and the dedup state) is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).

SECURITY-CRITICAL: every gate here is NAME-KEYED (verb keys, the permission tier
in mios_policy, the ``_HIGH_PRIVILEGE_VERBS`` / ``_LAUNCH_VERBS`` set membership).
Nothing is renamed.

<!-- mios-src:a4ea47df6ca6 from usr/lib/mios/agent-pipe/mios_dispatch.py:3-27 -->

### Persist a /v1/dispatch verb execution as a session-linked...

Persist a /v1/dispatch verb execution as a session-linked ``tool_call`` row
    -- the SAME shape the chat dispatch fast-path and the DAG executor write -- so a
    verb run through the dispatch HTTP front (mios-mcp-server's ``tools/call`` lands
    here) is VISIBLE to same-session provenance-taint propagation.

    ``_session_is_tainted`` decides the Semantic Firewall block by reading prior
    ``tool_call`` rows with ``tainted = true``; the chat + DAG paths each record their
    executions, but the dispatch path did not -- so a tainting verb dispatched here
    left no row, the taint was never seen, and a downstream high-privilege verb in the
    SAME session went un-gated. The taint markers come straight off the verb result
    (``_classify_verb_taint`` set them inside the dispatch chokepoint): no new schema,
    no new taint logic, just the missing persistence.

    Best-effort / degrade-open: the verb has ALREADY executed by the time this runs,
    so an absent DB writer or a write failure is swallowed (the audit row is not
    load-bearing for the verb's own result).

<!-- mios-src:547636815095 from usr/lib/mios/agent-pipe/mios_dispatch.py:127-142 -->

### Bulkhead layer. web_search dispatches share a global...

Bulkhead layer. web_search dispatches share a global concurrency
    semaphore so a council/DAG fan-out -- each call itself expanding into
    MIOS_WEB_FANOUT concurrent sub-queries -- can't stampede the local
    SearXNG; excess calls QUEUE here, with a small pre-acquire jitter to
    stagger simultaneous starts. All other verbs pass straight through.

    WS-A7: additionally, every dispatch is wrapped in the Tool-Manager conflict
    gate, which serializes verbs that declare a parallel_limit (per-verb
    concurrency cap) or a conflict_group (named mutual-exclusion set, e.g. the
    single-foreground-window UI verbs). The gate is a no-op for verbs that
    declare neither (the overwhelming majority), so this adds ~zero overhead to
    the common path while making stateful verbs fan-out-safe.

<!-- mios-src:96b0f8602785 from usr/lib/mios/agent-pipe/mios_dispatch.py:279-290 -->

### Public dispatch entry point, wrapping the bulkhead with a...

Public dispatch entry point, wrapping the bulkhead with a conversation-
    scoped concurrent SINGLE-FLIGHT guard (anti-swarm-duplication; see
    _dispatch_inflight). Concurrent identical (verb, resolved-args) dispatches
    in the same conversation collapse to ONE broker execution + share the
    result, so a side effect never fires N times across a fan-out. In-flight
    only -> sequential repeats re-run fresh.

<!-- mios-src:44e1dd194cfd from usr/lib/mios/agent-pipe/mios_dispatch.py:364-369 -->

### Audit a Rule-of-Two all-three decision -- one structured...

Audit a Rule-of-Two all-three decision -- one structured observability shape for
    both the audit-mode log line and the enforce-mode block. Carries the property
    breakdown (which of A/B/C, the count, the mode) so the decision is reconstructable.
    Best-effort / degrade-open: an absent DB writer or a write failure is swallowed.

<!-- mios-src:5c222419f898 from usr/lib/mios/agent-pipe/mios_dispatch.py:503-506 -->

### The Rule-of-Two architectural gate (F2/T-033, CaMeL-class)...

The Rule-of-Two architectural gate (F2/T-033, CaMeL-class), composed at the
    dispatch chokepoint. Returns a block_result dict to REFUSE the dispatch (enforce
    mode, a confirmed all-three kill-chain not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) are derived from the SSOT verb metadata INSIDE the pure
    ``mios_ruleof2.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    Placed AFTER the existing taint/HITL gates -- each of those returns early on its
    own block -- so Rule-of-Two only ADDS a refusal (the stricter gate wins).

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the all-three posture through the SINGLE ``mios_hitl.decide``
                 resolver; an explicit same-turn ask-to-run approval downgrades the
                 block so the human who approved THIS exact action can run it.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL behaviour;
    never crash, never newly block-everything). A CONFIRMED all-three under enforce
    gates (fail toward safety).

<!-- mios-src:cf3199a1a661 from usr/lib/mios/agent-pipe/mios_dispatch.py:526-545 -->

### Audit a CaMeL quarantine decision (the boundary BIT...

Audit a CaMeL quarantine decision (the boundary BIT: tainted AND privileged) --
    one structured observability shape for both the audit-mode log line and the
    enforce-mode block. Carries the axis breakdown (A + whether B / C, the mode) so the
    decision is reconstructable. Best-effort / degrade-open: an absent DB writer or a
    write failure is swallowed.

<!-- mios-src:e4670aec2bef from usr/lib/mios/agent-pipe/mios_dispatch.py:589-593 -->

### The CaMeL dual-context QUARANTINE gate (F2, the deeper half...

The CaMeL dual-context QUARANTINE gate (F2, the deeper half of T-033), composed
    at the dispatch chokepoint AFTER the Rule-of-Two gate so it only ADDS a refusal
    (stricter-wins). Returns a block_result dict to REFUSE the dispatch (enforce mode, a
    confirmed tainted+privileged action not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) come from the SSOT verb metadata INSIDE the pure
    ``mios_quarantine.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    The boundary BITES on tainted AND (sensitive OR state-change) -- the STRICTER
    superset of Rule-of-Two's all-three, for when you want full CaMeL isolation.

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the bite posture through the SINGLE ``mios_hitl.decide`` resolver
                 (quarantine_block=True); an explicit same-turn ask-to-run approval
                 downgrades the block so the human who approved THIS exact action runs it.

    SOUNDNESS: this sits at the SAME single chokepoint as the firewall / HITL /
    Rule-of-Two gates and only ADDS a refusal -- there is no second action path that
    bypasses it, and stricter-wins composition means enabling it can only make the
    posture stricter, never weaker.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL/Rule-of-Two
    behaviour; never crash, never newly block-everything). A CONFIRMED bite under enforce
    gates (fail toward safety).

<!-- mios-src:c06984198e32 from usr/lib/mios/agent-pipe/mios_dispatch.py:614-639 -->

### Run a single MiOS verb via the launcher broker (unix socket...

Run a single MiOS verb via the launcher broker (unix socket
    /run/mios-launcher/launcher.sock). Returns a structured dict:
    {success, tool, args, output, stderr, exit_code, latency_ms,
     tainted, taint_reason}. Uses the broker's CAPTURE_JSON: protocol
    so stdout/stderr split cleanly.

    Phase A.3: Semantic Firewall stub -- when a high-privilege verb
    is dispatched and the session has ANY upstream tainted tool_call,
    the dispatch is REFUSED (not even sent to the broker) and an
    event row is emitted (kind=firewall_block, severity=high).
    Taint of the dispatched verb itself is computed from
    _classify_verb_taint AND inherited from session state.

<!-- mios-src:376a282b6752 from usr/lib/mios/agent-pipe/mios_dispatch.py:726-737 -->
