<!-- AI-hint: Manual pages distilled from the source comments of mios_pipe, sanitized, each passage anchored to the comment it came from. -->

# mios_pipe

### Raised by _admit to SHED a best_effort dispatch under...

Raised by _admit to SHED a best_effort dispatch under contention (WS-SCHED-
    SLO). Caught at the fan-out call sites -> the node drops from the merge (the
    swarm already tolerates a dead/empty node); never raised for interactive.

<!-- mios-src:51ed2a246884 from usr/lib/mios/agent-pipe/mios_pipe/vram_scheduler.py:40-42 -->

### Capacity-aware admission gate, run BEFORE the endpoint/lane...

Capacity-aware admission gate, run BEFORE the endpoint/lane semaphores.
    No-op unless ADMIT_ENABLE. DEGRADE-OPEN: any error -> return (admit). Bounds
    every wait by ADMIT_MAX_WAIT then admits anyway -> never deadlocks a turn.
    Gates: (1) global host-load/mem ceiling; (2) a COLD model on an at-VRAM-
    ceiling endpoint waits briefly so cold loads serialize. Warm/under-ceiling
    dispatch returns immediately. (_host_stats_cached/_resident_cached/
    _over_global_ceiling/_is_warm are defined below near _engine_resident.)

<!-- mios-src:31c504d7e4fd from usr/lib/mios/agent-pipe/mios_pipe/vram_scheduler.py:118-124 -->
