<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_stress -- end-to-end direct-chat stress harness for...

mios_stress -- end-to-end direct-chat stress harness for the MiOS agent-pipe.

Drives the OpenAI /v1/chat/completions path under BOUNDED, load-aware concurrency
and reports latency / throughput / error-rate + a pass/fail verdict. Built for
the full-conversion validation goal (llama.cpp + KV-paging primary, pgvector
backend, all features on).

SAFETY -- the operator's hard-won lessons baked in:
  * COMPLETES every turn (awaits to done) -- NEVER orphans a request. The server
    historically has a request-cancellation gap; abandoning turns (the classic
    bounded-curl mistake) leaves the DAG+deepen churning for minutes -> loadavg
    spikes -> wedge (the documented loadavg-361 incident). This harness never
    abandons a turn.
  * LOAD-AWARE circuit breaker: polls /v1/scheduler between waves; over the load
    ceiling it stops RAMPING and backs off (AIMD) -- "saturate the backlog,
    never the cores."
  * RAMPED concurrency: starts low, climbs toward the target only while healthy.

The pure helpers (percentile/aggregate/ramp/throttle/scenarios/verdict) are
stdlib-only + unit-tested (test_mios_stress.py); the async runner uses httpx
(already an agent-pipe dep) and is exercised live by the operator via
`mios-stresstest`.

<!-- mios-src:8f5d4ac44379 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/stress.py:3-25 -->
