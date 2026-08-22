<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Self-improvement analysis for #64 (federation +...

Self-improvement analysis for #64 (federation + self-improve loop).

The risky part of "self-improvement" is an agent modifying itself; the safe,
high-value part is HONESTLY SEEING what is going wrong. This module is that safe
part: given the local outcome record (tool_call successes/latencies + peer
reputation), it surfaces concrete, ranked findings ("tool X fails 40% of the
time", "peer Y is unreliable") that a human -- or, later, a gated closed loop --
can act on. Pure functions over plain dicts: no DB, no server import, no I/O.

<!-- mios-src:f7ef37bfb8a1 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove.py:4-12 -->
