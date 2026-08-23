<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A12 round-robin preemption state machine + generation-snapshot contract, PLUS the T-019/SCHED-01 TURN-boundary preemption seam AND the T-020/SCHED-02 token-time-sliced priority QUEUE that layers on it. Pure-stdlib core that decides WHEN a running dispatch has used its time-slice (Quantum), holds the snapshot of a preempted generation (Snapshot: partial output + position + priority + slot), and manages a BOUNDED free-list of snapshot slots + a suspended queue with priority-ordered resume (PreemptScheduler). This is the policy/bookkeeping half of RR time-slicing; server.py owns the actual interruptible decode loop + restoring a snapshot into the engine (VM/engine-deep). The turn_boundary() hook is the clean, FLAG-GATED (mios.toml [scheduler].preempt_enable, DEFAULT-OFF) integration seam the agent-pipe dispatch turn loop (mios_chat) calls AFTER a turn's priority is known: when enabled it consults the turn-boundary PreemptScheduler to snapshot/yield/resume a turn to a higher-priority waiter; default-off it is a byte-identical no-op; degrade-open it always falls back to running the turn. T-020 adds TokenSliceQueue (priority-ordered ready turns + per-turn token-time SLICE accounting -- a slice is N tokens via the mios_tokenize seam, NOT wall-clock) + the slice_boundary() hook: at each token-slice boundary it re-evaluates via turn_boundary (yield to a higher-priority waiter, else continue). The queue is its OWN master gate ([scheduler].queue_enable, DEFAULT-OFF) so default-off stays byte-identical. This module reads its [scheduler] SSOT itself (via mios_config, mios_sched-style) and takes the live "higher-priority-waiting" probe through configure() -- it NEVER imports server (one-way boundary). Pure so it unit-tests in isolation, in the mios_sched / mios_pdp sibling style.
AI-related: ./mios_sched.py, ./mios_config.py, ./mios_chat.py, ./mios_tokenize.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_preempt.py
AI-functions: expired, remaining, acquire_slot, release_slot, suspend, resume, discharge, is_suspended, can_admit, stats, decide, configure, turn_boundary, slice_boundary, turn_scheduler_stats, enqueue, dispatch, account, head_priority, requeue, remove, class Quantum, class Snapshot, class PreemptScheduler, class TokenSliceQueue

<!-- mios-src:057ffefd574c from usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py:1-3 -->

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
