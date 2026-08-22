<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_preempt -- round-robin preemption policy + snapshot...

mios_preempt -- round-robin preemption policy + snapshot contract (WS-A12, the
AIOS scheduler time-slice layer).

Pure stdlib (time passed in -> deterministic). Strict-priority scheduling can let
a long high-priority generation hog the lane; RR time-slicing preempts it after a
QUANTUM, snapshots its partial state, requeues it, and lets the next waiter run.
This module owns the BOOKKEEPING: quantum expiry, a bounded free-list of snapshot
slots (so suspensions can't grow unbounded), and a priority-ordered suspended
queue. server.py owns the engine-side interruptible decode + snapshot
restore/save (which needs llama.cpp/SGLang support); this is the testable policy.

TURN-boundary preemption seam (T-019 / SCHED-01)
================================================
:func:`turn_boundary` is the agent-pipe's TURN-level preemption hook -- DISTINCT
from the decode-loop RR time-slice ([dispatch].rr_*) and from the priority SCORER
([sched]). The dispatch turn loop calls it AFTER a turn's AIOS priority is known;
when enabled the turn-boundary :class:`PreemptScheduler` may snapshot + yield the
turn to a higher-priority waiter and resume it. It is FLAG-GATED on
``mios.toml [scheduler].preempt_enable`` (DEFAULT-OFF -> byte-identical no-op) and
DEGRADE-OPEN (any scheduler error runs the turn normally -- a turn is never
dropped). It is the clean substrate later scheduler policies build on. The module
reads its ``[scheduler]`` SSOT itself (mios_sched-style) so it is self-contained +
unit-testable; server.py injects the live "is a higher-priority turn waiting?"
probe via :func:`configure`. ONE-WAY BOUNDARY: this module never imports server.

Token-time-sliced priority queue (T-020 / SCHED-02)
===================================================
:class:`TokenSliceQueue` is the queueing POLICY that sits ON TOP of the T-019
turn_boundary mechanism. Turns enqueue with a priority + a per-turn SLICE BUDGET
measured in TOKENS (a token-time quantum -- NOT wall-clock); the scheduler
dispatches the highest-priority ready turn, accounts the tokens it generates
against its slice (via the shared :mod:`mios_tokenize` seam -- never a re-derived
chars//N), and at each slice boundary :func:`slice_boundary` re-evaluates through
turn_boundary: yield the lane to a higher-priority waiter (the existing
snapshot/resume) or continue. It has its OWN master gate
(``[scheduler].queue_enable``, DEFAULT-OFF) so the default path is byte-identical
(no queue interposition) and is DEGRADE-OPEN (any queue error runs the turn
normally -- never dropped/stalled). The queue is bounded so advisory bookkeeping
can never grow without limit. The live token feed + the precise gate-relative
enqueue/dispatch placement are operator-live-validated; this module owns the
ordering + slice-accounting policy + the boundary re-eval.

<!-- mios-src:cfd7c1f1160f from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:3-44 -->

### Pure per-slice-boundary decision for an interruptible...

Pure per-slice-boundary decision for an interruptible generation.

    - finished -> COMPLETE (the decode loop saw a stop/EOS within the slice).
    - a higher-priority waiter IS queued AND this run has spent its quantum AND
      we can bound the suspension (a free snapshot slot exists) -> PREEMPT.
    - otherwise CONTINUE (run another slice).

    Bounded-suspension safety: when no snapshot slot is free (`can_suspend` is
    False) we NEVER preempt -- the task runs to completion instead -- so the set
    of suspended generations can never exceed the cap and a preempted task is
    never dropped on the floor. A generation is only ever preempted at a slice
    boundary, so its partial output up to that boundary is always captured.

<!-- mios-src:1cc1431d8b8e from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:67-78 -->

### Remove a SPECIFIC suspended task and free its slot...

Remove a SPECIFIC suspended task and free its slot, returning its
        Snapshot (None if it was not suspended). This is the self-resume path for
        the gate-driven driver: a preempted generation re-acquires the lane via
        the priority gate (which already orders waiters by priority), so it
        discharges ITS OWN snapshot rather than popping the global highest via
        resume() -- that would let one coroutine steal another's saved state.

<!-- mios-src:a24e575e741c from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:173-178 -->

### Token-time-sliced priority queue (T-020 / SCHED-02) -- the...

Token-time-sliced priority queue (T-020 / SCHED-02) -- the queueing POLICY on
    top of the T-019 turn-boundary mechanism. It orders ready turns by priority and,
    for a dispatched turn, accounts the tokens it generates against a per-turn SLICE
    BUDGET (a token-time quantum -- N tokens, NOT wall-clock). When a turn crosses its
    slice budget the scheduler re-evaluates (the caller drives that via slice_boundary
    -> turn_boundary): a higher-priority waiter may preempt it, else it continues.

    Pure bookkeeping (deterministic; token counts are passed IN) so it unit-tests in
    isolation, like PreemptScheduler. Single-threaded asyncio: every method is
    allocation-light and lock-free (no await between a check and its mutation). The
    queue is BOUNDED (max_turns) and evicts only STALE ready entries, so its advisory
    bookkeeping can never grow without limit even if a caller misses a remove(); a
    turn's coroutine is never affected by eviction (degrade-open). The live token feed
    + the precise gate-relative enqueue/dispatch placement are operator-live-validated;
    this class owns the MLFQ ordering (LRU eviction + contention-gated priority decay)
    + slice accounting.

<!-- mios-src:e1f4efb7cddc from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:197-212 -->

### Add `tokens` to the turn's CURRENT-slice counter. Returns...

Add `tokens` to the turn's CURRENT-slice counter. Returns True iff it
        crossed its slice budget (a slice boundary -- the caller then re-evaluates),
        carrying the remainder into the next slice. A 0/absent budget never trips
        (slicing off). Unknown task / bad count -> False (degrade-open).

<!-- mios-src:5354ab1aab26 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:272-275 -->

### Resolve the [scheduler] table: layered mios.toml merged...

Resolve the [scheduler] table: layered mios.toml merged over the degrade-open
    fallbacks, then MIOS_SCHEDULER_* env overrides (highest precedence). Pure SSOT
    (mios_config); never raises (missing/broken config -> fallbacks).

<!-- mios-src:1d6aa0808674 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:356-358 -->

### Override the turn-boundary wiring under exact names...

Override the turn-boundary wiring under exact names (one-way boundary).

    server.py calls this to inject the live PriorityGate head-priority probe
    (``head_priority=``) so the seam can tell when a higher-priority turn waits;
    tests inject a spy ``turn_scheduler=`` / ``clock=`` / ``preempt_enable=``.
    Friendly aliases (head_priority/turn_scheduler/clock/quantum_s/...) map to the
    module globals. Unknown keys are ignored (partial-injection safe).

<!-- mios-src:3cf51353a9a4 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:428-434 -->

### True iff a higher-priority turn is waiting. Two OR-combined...

True iff a higher-priority turn is waiting. Two OR-combined signals: the
    injected gate head-priority probe (T-019) and -- ONLY when the token-time-sliced
    queue is enabled ([scheduler].queue_enable, T-020) -- the queue's highest-priority
    READY waiter (excluding this turn). False when unwired or on any probe error -- no
    signal => no preemption (degrade-open). With queue_enable OFF this is byte-
    identical to the prior probe-only behaviour.

<!-- mios-src:71b6dbb44fdc from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:444-449 -->

### Turn-boundary preemption seam (T-019 / SCHED-01). The...

Turn-boundary preemption seam (T-019 / SCHED-01). The dispatch turn loop
    calls this AFTER a turn's AIOS priority is known -- the clean point at which a
    scheduler decides whether to preempt. Returns True iff this turn was preempted
    (snapshotted + yielded + resumed), else False.

    DEFAULT-OFF ([scheduler].preempt_enable=false): returns False IMMEDIATELY --
    the PreemptScheduler is NOT consulted, so the turn runs byte-identically.

    ENABLED: consults the turn-boundary PreemptScheduler via the pure decide()
    primitive (at a boundary the prior slice is spent, so quantum_expired=True ->
    preempt iff a higher-priority turn waits AND a snapshot slot is free, else run
    to completion -- bounded suspension). On PREEMPT it SNAPSHOTS this turn into a
    slot, cooperatively YIELDS the event loop (bounded by max_preempt_depth ticks
    AND the quantum, so a turn is never starved or busy-waited), then RESUMES by
    discharging ITS OWN snapshot -- the snapshot/resume round-trip per the
    PreemptScheduler API. The richer cross-turn blocking policy that later
    schedulers (T-020/T-058) layer on this seam is operator-live-validated.

    DEGRADE-OPEN: ANY scheduler error -> returns False and the turn proceeds
    normally; a best-effort discharge prevents a leaked snapshot. Preemption NEVER
    drops or corrupts a turn.

<!-- mios-src:29831a5f65d6 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:471-491 -->

### Token-time-slice boundary hook (T-020 / SCHED-02) -- the...

Token-time-slice boundary hook (T-020 / SCHED-02) -- the queueing POLICY on
    top of the T-019 turn_boundary mechanism. The generation loop calls this as a
    dispatched turn produces output: it ACCOUNTS the tokens generated this step
    against the turn's SLICE BUDGET (a token-time quantum -- SLICE_TOKENS tokens, NOT
    wall-clock) and, ONLY when the budget is crossed (a slice boundary), RE-EVALUATES
    via turn_boundary -- snapshot + yield to a higher-priority waiter, or continue.
    Returns True iff the turn was preempted at this boundary.

    Token-time accounting: `tokens` is a count the caller already measured through the
    mios_tokenize seam; alternatively pass `text` and it is counted HERE through the
    SAME seam (never a re-derived chars//N).

    DEFAULT-OFF ([scheduler].queue_enable=false): returns False IMMEDIATELY -- the
    queue is NOT consulted, so the turn runs byte-identically (no interposition).

    ENABLED: accounts the tokens; a slice boundary delegates to turn_boundary (itself
    gated on preempt_enable + a higher-priority waiter -- the queue head is one such
    signal, see _higher_priority_waiting). On a real preempt the turn is REQUEUED
    (ready) so the next dispatch() re-orders it by priority.

    DEGRADE-OPEN: ANY queue/scheduler error -> returns False and the turn runs
    normally; a turn is never dropped or stalled.

<!-- mios-src:0c8ade64051e from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:531-552 -->
