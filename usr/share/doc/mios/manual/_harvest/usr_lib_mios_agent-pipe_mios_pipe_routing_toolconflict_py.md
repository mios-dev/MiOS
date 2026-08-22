<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_toolconflict -- per-verb dispatch serialization for...

mios_toolconflict -- per-verb dispatch serialization for the MiOS agent-pipe
(WS-A7, the AIOS Tool Manager conflict/parallel-limit layer).

Pure stdlib (asyncio / collections) so it unit-tests in isolation, in the
sibling-module style of mios_sched / mios_jsonsalvage. server.py owns the wiring
(parsing the SSOT [verbs.*] fields, building the module-global instance, and
wrapping the dispatch chokepoint); this module owns only the reusable mechanism.

The problem
===========
Before WS-A7 the dispatch chokepoint (_dispatch_bounded) special-cased ONE verb
(web_search, a global SearXNG bulkhead) and let every other verb pass straight
through with unbounded concurrency. But several verbs are *stateful and
single-instance*: there is exactly one foreground window and one keyboard, so a
council/DAG fan-out that issues `open_app`, `focus_window` and `pc_type`
concurrently races them against each other -- the keystrokes land in whatever
window won the focus race. Such verbs need to SERIALIZE, not stampede.

The mechanism
=============
Two orthogonal, SSOT-declared controls, both keyed off the verb name:

  parallel_limit (int >= 1)
      A per-verb concurrency cap. `parallel_limit = 1` makes the verb strictly
      single-flight; `= N` admits at most N concurrent dispatches. Backed by a
      per-verb asyncio.Semaphore(N).

  conflict_group (str)
      A named mutual-exclusion set. All verbs sharing a group serialize against
      *each other* (one member of the group runs at a time), not just against
      themselves. Backed by an asyncio.Semaphore(1) per group name.

A verb may declare either, both, or neither. `guard(verb)` returns an async
context manager:

    async with CONFLICT.guard(verb):
        ... dispatch the verb ...

Deadlock-freedom
----------------
A call acquires AT MOST one group lock and AT MOST one verb semaphore, always in
the fixed order group-lock -> verb-semaphore, and releases in reverse. Because
the order is global and each call holds at most one of each kind, no acquire
cycle can form. Cancellation/exception while acquiring rolls back whatever was
already held (the _Guard rollback in __aenter__).

Fast path
---------
A verb that declares neither control hits a no-op guard (two dict lookups, no
semaphore, no await) -- so the overwhelming majority of dispatches are
unaffected. This is the degrade-open default: an empty ConflictGate serializes
nothing.

Concurrency model: single-threaded asyncio. Semaphores are created lazily on
first use (inside a running loop). All bookkeeping mutations happen with no
await between check and mutation, so no lock is needed.

<!-- mios-src:0cfbb5413ebc from usr/lib/mios/agent-pipe/mios_pipe/routing/toolconflict.py:3-59 -->

### Build a gate from the _VERB_CATALOG dict

Build a gate from the _VERB_CATALOG dict: read each verb's
        `parallel_limit` (int) and `conflict_group` (str). Tolerant of missing
        / malformed fields (degrade-open: unparseable -> unconstrained).

<!-- mios-src:f6b724b5d37c from usr/lib/mios/agent-pipe/mios_pipe/routing/toolconflict.py:93-95 -->
