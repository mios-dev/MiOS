<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### A8: _deepen_until_barrier early-exits on a SATISFIED node...

A8: _deepen_until_barrier early-exits on a SATISFIED node only when the SSOT
    flag is on; degrade-open -> a judge error/timeout falls through to the
    deadline-bound loop (never under-computes). Four scenarios, observed via the
    number of (stubbed) agent coverage passes.

<!-- mios-src:336583d016da from usr/lib/mios/agent-pipe/test_mios_dag_exec.py:188-191 -->
