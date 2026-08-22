<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_kvfork -- KV-cache FORK primitives for the MiOS...

mios_kvfork -- KV-cache FORK primitives for the MiOS agent-pipe (WS-8, the
AIOS context-manager "fork" capability that extends the existing demand-paging
KV layer, server.py `_kv_paging` / `_kv_slot_action`).

Purpose
=======
The llama.cpp /slots layer already lets us SAVE a conversation's KV to disk and
RESTORE it (`_kv_slot_action`). A SWARM that wants to branch several parallel
cognitive paths from a SHARED PREFIX (e.g. "from this researched context, spawn
3 sub-agents that each take a different angle") needs a FORK: copy a parent
conversation's saved KV file to a NEW child-conversation filename so each branch
pages in the same prefix independently and diverges without clobbering the
parent. That is the RadixAttention prefix-sharing workload, done on the cheap
disk-file prototype (no vLLM/LMCache yet).

Why this lives here (pure, DB-free, sibling module)
---------------------------------------------------
Pure stdlib (re / typing) so it unit-tests in isolation, in the
mios_sched / mios_evict / mios_hitl style. This module owns ONLY the reusable
mechanism: the filesystem-safe filename derivation (kept byte-identical to
server.py `_kv_filename` so a forked child's file is the one `_kv_paging` later
restores), the fork-request validation, and the SLOT-ACTION PLAN. server.py owns
the wiring (the SSOT flag, the async `kv_fork()` that drives `_kv_slot_action`
against a live llama.cpp endpoint, the contextvar, the /v1 observability).

llama.cpp has NO native "copy slot file" verb. A fork is therefore expressed as
a two-step plan over the EXISTING save/restore primitive:

    1. restore  <- parent file   (page the shared prefix INTO the slot)
    2. save     -> child file     (write the slot back out under the new name)

After step 2 the child conversation owns an independent KV file seeded with the
parent's prefix; subsequent turns on the child page IN that file and diverge.
The plan is data only -- the caller (server.py) runs it under the per-slot lock
so a concurrent conversation can't swap the slot between the two steps.

Everything degrades open: a malformed request returns a non-fatal reason and the
caller proceeds without forking (the child simply starts from a cold/empty KV,
exactly as it would today).

<!-- mios-src:6516b5d1056a from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:3-42 -->

### Validate a fork request. Returns (ok, reason). DEGRADE-OPEN...

Validate a fork request. Returns (ok, reason). DEGRADE-OPEN contract: the
    caller treats ok=False as 'skip the fork, proceed cold' -- never an error.

    Rejects:
      * an empty/None source or destination (nothing to fork / nowhere to put it)
      * a source and destination that sanitise to the SAME KV file (a self-fork
        is a no-op that would needlessly rewrite the parent's own file).

<!-- mios-src:962dc2464cfb from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:73-80 -->

### Build the ordered slot-action plan that forks `src_conv`'s...

Build the ordered slot-action plan that forks `src_conv`'s saved KV into a
    new file for `dst_conv`. Two steps over the existing save/restore primitive:

        ("restore", <src token>, <src file>)   # page the shared prefix IN
        ("save",    <dst token>, <dst file>)    # write the slot OUT under dst

    PURE: returns data only; the caller runs the steps (under the per-slot lock)
    via `_kv_slot_action`. Order matters and must be preserved. Call only after
    validate_fork() returns ok -- this does not re-validate (it sanitises, so a
    bad input yields a 'default'/'default' no-op plan rather than raising).

<!-- mios-src:2fb25ef2d788 from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:96-105 -->

### Collapse the two step results into one fork verdict. A fork...

Collapse the two step results into one fork verdict. A fork SUCCEEDS only
    if the SAVE landed (the child file now exists). A failed RESTORE is tolerated
    but noted: the child is then seeded from whatever was already resident in the
    slot rather than the intended parent prefix -- degraded, not fatal.

    Returns (forked, reason). `forked=False` => the caller should let the child
    start cold (its next turn pages in nothing, as today).

<!-- mios-src:1cbbaa9b2af5 from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:115-121 -->
