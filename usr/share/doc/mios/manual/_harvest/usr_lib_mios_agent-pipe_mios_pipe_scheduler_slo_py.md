<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_slo -- SLO-class admission + EDF ordering +...

mios_slo -- SLO-class admission + EDF ordering + fail-closed shed (WS-SCHED-SLO).

The modern SLO-serving frontier (SCORPIO/Andes/QLM): each request carries a
deadline/SLO class, the scheduler orders least-deadline-first, and best-effort
work is SHED under contention rather than unconditionally admitted. MiOS's
`_admit` is capacity-only (it always admits after a bounded wait) and worse,
degrades OPEN -- a DB/VRAM-probe failure during a storm silently disables
backpressure entirely.

This module is the PURE policy:
  * classify()     -- turn signals -> SLO class (interactive | best_effort).
  * deadline()     -- now + the class's wall-clock budget.
  * edf_key()      -- least-deadline-first sort key (earliest deadline served
                      first; interactive breaks ties).
  * should_shed()  -- FAIL-CLOSED: shed a best_effort dispatch under contention
                      OR when health is UNKNOWN (probe failed); NEVER shed
                      interactive. This inverts the current degrade-open hole.

server.py owns wiring (classify the turn, feed edf_key into PriorityGate._pick,
call should_shed in _admit), all flag-gated. Deterministic, no I/O.

<!-- mios-src:551d74690cd4 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/slo.py:3-23 -->

### Map turn signals to an SLO class. An AUTONOMOUS /...

Map turn signals to an SLO class. An AUTONOMOUS / background turn is
    best_effort; a FOREGROUND turn is interactive UNLESS its scheduling priority
    was clamped below `interactive_priority` (the autonomous-clamp path), in which
    case it is best_effort too. Fail-safe default (foreground, unclamped) ->
    interactive (protect the human). Unspecified priority / interactive_priority
    fall back to the SSOT-injected defaults (`_DEFAULT_PRIORITY` /
    `_INTERACTIVE_PRIORITY`).

<!-- mios-src:0708625fadb4 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/slo.py:56-62 -->

### FAIL-CLOSED shed decision. An INTERACTIVE turn is NEVER...

FAIL-CLOSED shed decision. An INTERACTIVE turn is NEVER shed (the human is
    protected). A BEST_EFFORT dispatch is shed when the system is over its
    capacity ceiling OR when health is UNKNOWN (`healthy=False`, e.g. the load/mem
    probe failed) -- the latter is the correctness fix: where `_admit` currently
    degrades OPEN (admit-on-probe-failure), best_effort here degrades CLOSED (shed
    when we can't confirm headroom), so a probe failure during a storm tightens
    backpressure instead of disabling it.

<!-- mios-src:46ddfd3a5992 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/slo.py:90-96 -->
