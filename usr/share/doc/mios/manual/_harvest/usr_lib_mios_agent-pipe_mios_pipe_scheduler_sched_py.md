<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_sched -- scheduler primitives for the MiOS agent-pipe...

mios_sched -- scheduler primitives for the MiOS agent-pipe (WS-1, the AIOS
Agent Scheduler reordering layer).

Pure stdlib (asyncio / time / collections) so it unit-tests in isolation, in the
sibling-module style of mios_jsonsalvage / mios_owui. server.py owns the wiring
(the SSOT flag, the global instance, the degrade-open context manager); this
module owns only the reusable mechanism.

PriorityGate
============
A bounded concurrency gate -- like asyncio.Semaphore -- EXCEPT that, when
contended, it hands the next freed permit to the HIGHEST-PRIORITY waiter
(FIFO tie-break) instead of the earliest arrival. That is the reordering a plain
Semaphore cannot do: with a Semaphore, once a dispatch is queued behind the
global cap, a later higher-priority dispatch can never jump ahead. The MiOS
agent-pipe already computes a per-turn / per-lane priority (_sched_priority /
_dispatch_priority) but, before WS-1, those were advisory only because the global
cap admitted FIFO. PriorityGate makes them ACTIVE.

Anti-starvation
---------------
Strict priority can starve low-priority work forever under sustained
high-priority load. `starvation_s > 0` enables aging: a waiter that has been
queued longer than `starvation_s` is served AHEAD of priority, so the lowest
lanes still make progress.

Key invariant
-------------
    available > 0  =>  no waiters

Release hands a permit DIRECTLY to the chosen waiter (it never bumps
`available` while any waiter exists). Therefore the acquire fast path -- "a
permit is free, take it" -- can only run when the queue is empty, so it can
never jump ahead of a queued higher-priority dispatch. This keeps the fast path
allocation-free (no future, no heap) while preserving correctness.

Concurrency model: single-threaded asyncio. There is no await between the check
and the mutation in any method, so no lock is needed.

<!-- mios-src:c188199820c6 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py:3-41 -->

### Pick a LIGHT engine the agent can run on for concurrent...

Pick a LIGHT engine the agent can run on for concurrent fan-out, else None
    (caller uses the agent's OWN endpoint). DEFAULT: None for everything
    (DISPATCH_OFFLOAD_CPU off) so each distinct node runs on its OWN hardware
    concurrently instead of all funneling to the single CPU lane (operator
).

<!-- mios-src:be593746a089 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py:233-237 -->

### Compute the turn priority from ``refined`` + the resolved...

Compute the turn priority from ``refined`` + the resolved [sched] ``cfg`` table.
    Every tier/weight resolves from ``cfg`` with an _SCHED_FALLBACK default (== the
    historical literal), so an empty ``cfg`` is byte-identical to the prior heuristic.
    Split from _sched_priority so the wrapper can degrade-open (cfg={}) on any error.

<!-- mios-src:59f15a0c6e2b from usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py:270-273 -->

### Score a turn the AIOS way

Score a turn the AIOS way: priority = f(complexity, urgency, resource-need).
    Derived from the refined plan (no hardcoded topic map): complexity from the
    task/step count + tool count; urgency from the model's refined.urgency signal (a
    numeric model value when [sched].priority_mode='model', else membership in the
    operator-localizable [sched] urgency vocabulary, matched Unicode-casefold);
    resource-need from the target lane. Higher = sooner. Tiers + weights are SSOT in
    mios.toml [sched] with degrade-open fallbacks EQUAL to the historical literals, so
    an absent section is byte-identical. Currently ADVISORY (logged + exposed) -- the
    lane semaphores still admit in arrival order; this is the hook a future policy
    engine would order on. Degrades open on any error to the literal-fallback path.

<!-- mios-src:5cbaa53282a7 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py:335-344 -->

### SEMAPHORE KEY -- the distinct HARDWARE UNIT an agent runs...

SEMAPHORE KEY -- the distinct HARDWARE UNIT an agent runs on, which is
    NOT the same as its lane CATEGORY (_agent_lane). With more than one machine
    of a category on the tailnet (e.g. the local 4090 AND a remote GPU box),
    'gpu' is no longer ONE piece of hardware, so a shared 'gpu' semaphore would
    throttle BOTH boxes to a single per-lane budget. A custom per-node lane
    (e.g. 'potato-gpu' -- any lane outside the base category set) therefore gets
    its OWN semaphore so distinct machines fire with INDEPENDENT concurrency
 budgets ("each remote node gets its OWN semaphore").
    Agents without a custom lane fall back to the category (local hardware).
    NOTE: _agent_lane stays the CATEGORY (gpu/cpu/igpu/mobile/accelerator) so
    SLOW_LANES trimming + the cpu-parallelism bonus keep working -- e.g. a
    'potato-cpu' node is category 'cpu' (slow -> trimmed) yet has its OWN sem.

 SWARM Phase-0 : an explicit `sub_lane` is the FINEST
    semaphore key -- it lets N single-model servers on the SAME device (e.g.
    'gpu0' for several concurrent small llama-server instances on the one 4090)
    each hold an INDEPENDENT concurrency budget instead of all collapsing onto a
    single 'gpu' semaphore (the documented OOM-cascade mode). Defaults to the
    prior behaviour when unset -> byte-identical for today's nodes (none set it).

<!-- mios-src:168ee3cf97dc from usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py:361-379 -->
