<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### BACKGROUND async daemon loops (strangler-fig refactor)....

BACKGROUND async daemon loops (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. These are the long-lived ``create_task()``
loop bodies the FastAPI startup hooks spawn: ``_membership_watch_loop`` (FED-G3
live membership hot-reload), ``_gossip_loop`` (WS-A18 trust-gated epidemic peer
discovery), ``_selfimprove_loop`` (#64 proactive finding surfacing), and the
``_reputation_restore`` / ``_reputation_flush`` persistence helpers the reputation
flush loop drives. Every heuristic/guard/comment stays byte-identical. Leaf deps
are imported directly; every server-side symbol is injected via :func:`configure`
(one-way boundary -- this module never imports ``server``). ``server.py`` keeps the
``@app.on_event`` startup hooks and re-imports each loop under its original alias so
the importable surface stays byte-identical.

<!-- mios-src:4c85c3f6901d from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:3-15 -->

### Inject server-side deps under their EXACT original names...

Inject server-side deps under their EXACT original names (one-way boundary).

    Called once from ``server.py`` after every injected symbol is defined. Each
    keyword equals the module global it sets; the mutable registries are injected by
    reference so in-place mutation stays shared with server.

<!-- mios-src:70224711ad06 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:75-80 -->

### Draft a bounded change PROPOSAL for one finding (the...

Draft a bounded change PROPOSAL for one finding (the Autodata "implementer").

    A proposal is {target_kind, target_id, change, rationale}: the artifact to change
    (a prompt / skill / config entry IN the improvable surface), a described tweak,
    and the rationale. Mapping a finding to a CONCRETE improvable target + a change is
    a reasoning step that needs a live model -- and must NOT be a hardcoded
    finding->artifact heuristic (that would be an English gate banned by Law 7) -- so
    this seam is wired to a model-backed drafter validated by the operator. Until then
    it returns None: nothing is fabricated, so even a flipped act_enabled never queues
    a guessed change. Patched in tests to exercise the propose->prove->queue path.

<!-- mios-src:d53ab1e39fdd from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:234-243 -->

### Score the current baseline vs the proposed variant on a...

Score the current baseline vs the proposed variant on a DISCRIMINATIVE held-out
    eval (T-064). Returns (baseline_score, proposed_score) as pass^k reliabilities, or
    None when no eval/solver is available (-> the proposal cannot be proven and is not
    queued). The live path fetches eval candidates, curates them with the solver-gap
    (mios_selfimprove_act.curate_eval over the SSOT weak/strong lane pair), runs each
    variant through the lanes, and scores via mios_selfimprove_act.pass_hat_k_score --
    a live, operator-validated step, so the offline default is None. Patched in tests
    to supply synthetic baseline/proposed scores.

<!-- mios-src:eee0f87c8475 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:248-255 -->

### QUEUE a validated, non-regressing proposal for human review...

QUEUE a validated, non-regressing proposal for human review (an `event` row).
    NEVER applies it. Degrade-open: a pg miss logs + drops the proposal and returns
    False; live serving is never affected. Returns True iff the row was written.

<!-- mios-src:2eedf15df7d9 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:260-262 -->

### One ACT pass

One ACT pass: findings -> proposals -> proof-of-utility -> QUEUE (no apply).

    DEFAULT-OFF: returns a no-op summary unless [selfimprove].act_enabled. For each
    high/medium finding (bounded by max_proposals_per_pass): draft a proposal, REJECT
    it up front if it is not in the SSOT improvable surface / is in the protected
    surface (structural isolation -- it is never even scored), else prove utility
    (pass^k non-regression) and QUEUE only a non-regressing proposal. Every accept/
    reject is logged with the score delta (Autodata rejects ~half its own proposals).
    Degrade-open: any error drops the current proposal, never the loop. Returns a
    summary {acted, findings, drafted, queued, rejected}.

<!-- mios-src:a8bec89292c6 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:283-292 -->

### The QUEUED self-improvement proposals awaiting human...

The QUEUED self-improvement proposals awaiting human approval (read-only).
    Degrade-open -> {proposals:[], error} when pg is unreachable so the route stays
    up. These are validated + non-regressing (T-064) but NEVER auto-applied.

<!-- mios-src:9c21095bf1c0 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:346-348 -->

### WS-A4

WS-A4: one GC pass over the LOCAL KV slot dir (no-op when it's remote /
    unset / empty). Plans TTL+size eviction via mios_kvgc, protecting the file of
    whatever conversation is resident in the active slot, then removes evictees.
    Best-effort + degrade-open: any error leaves the files (the tmpfiles age-out
    is the backstop).

<!-- mios-src:6546a5af00a6 from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:394-398 -->

### Read-only

Read-only: the QUEUED self-improvement proposals awaiting human approval -- the
    ACT half of #64 (T-062). Each was validated for target isolation and proven
    non-regressing (T-064 proof-of-utility) before queuing, but is NEVER auto-applied:
    the operator reviews + approves out of band, then a separate path applies it.

<!-- mios-src:fb34bca1c23f from usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py:548-551 -->
