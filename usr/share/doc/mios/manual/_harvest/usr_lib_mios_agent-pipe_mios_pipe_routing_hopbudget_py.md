<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_hopbudget -- hop-budget recursion guard + effort...

mios_hopbudget -- hop-budget recursion guard + effort scaling (WS-4, the AIOS
orchestrator-worker structural-guard layer).

Pure stdlib. The agent-pipe's fan-out can re-enter the gateway over HTTP (a
thin-gateway-as-worker, an A2A peer); a process-local depth counter resets to 0
across that hop -> unbounded recursion. The guard carries the depth + an
agent-id Via chain as headers (RFC 9110 Max-Forwards + Via) and kills a loop the
moment a self-id reappears. These functions are the pure decisions behind that
guard, plus the effort->width scaling that makes orchestration intensity a
first-class function of query complexity rather than a fixed cap.

<!-- mios-src:2872d53f220e from usr/lib/mios/agent-pipe/mios_pipe/routing/hopbudget.py:3-13 -->

### Map an 'effort' level to an orchestration fan-out width in...

Map an 'effort' level to an orchestration fan-out width in [1, cap].
    Accepts a named tier (low|medium|high|max|xhigh) or a 0..1 float (complexity
    score). Unknown/empty -> `base`. This is the first-class knob that scales
    swarm intensity to query complexity instead of a single fixed width.

<!-- mios-src:f586e915fa56 from usr/lib/mios/agent-pipe/mios_pipe/routing/hopbudget.py:61-64 -->
