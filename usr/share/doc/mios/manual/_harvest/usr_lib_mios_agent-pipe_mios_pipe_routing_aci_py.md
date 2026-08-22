<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_aci -- pure Agent-Computer Interface output normalizer...

mios_aci -- pure Agent-Computer Interface output normalizer (WS-5).

DB-free + stdlib-only so the truncation logic unit-tests in isolation
(sibling-module pattern, like mios_sched / mios_evict / mios_hitl).

The problem: feeding raw tool/terminal output back to a model either saturates
the context window or, with a naive head-only slice (`out[:N]`), DROPS THE TAIL
-- which for command/terminal output is exactly where the error, exit code, or
final result lands. The ACI pattern keeps the most informative ENDS (head AND
tail) and elides the middle with an explicit, anti-fabrication marker, bounding
both line count and char count.

server.py owns the knobs + where this is applied; this module owns the pure
transform.

<!-- mios-src:260300d15f4c from usr/lib/mios/agent-pipe/mios_pipe/routing/aci.py:3-17 -->

### Bound `text` to a context budget by keeping the head AND...

Bound `text` to a context budget by keeping the head AND the tail and
    eliding the middle with a marker. Applies an optional line cap first, then a
    char cap. Returns `text` unchanged when already within budget.

    head_frac in (0,1) splits the kept budget between head and tail; the default
    keeps slightly more head (early context) while preserving the tail (the
    result/error). Degrade-open: any error returns a plain head slice.

<!-- mios-src:513eab2ffc9e from usr/lib/mios/agent-pipe/mios_pipe/routing/aci.py:32-38 -->
