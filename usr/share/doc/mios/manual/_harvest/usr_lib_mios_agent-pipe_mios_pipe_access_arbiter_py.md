<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_arbiter -- the MiOS out-of-process policy-arbiter...

mios_arbiter -- the MiOS out-of-process policy-arbiter decision core (WS-9).

Pure stdlib. The agent-pipe already has a HITL arbiter CLIENT
(_hitl_arbiter_verdict) that POSTs a high-risk action to an external arbiter for
an allow/deny verdict -- but no arbiter SERVICE existed. This is the decision
logic that service runs: a deterministic, auditable second opinion that the
operator can own/change independently of the agent-pipe.

Policy (first match wins):
  1. verb in deny  -> DENY (always; the hard floor)
  2. allow set AND verb in allow -> ALLOW
  3. allow set AND verb NOT in allow -> DENY (allow-list is exclusive)
  4. tier rank >= block_tier rank -> DENY (risk ceiling)
  5. otherwise -> ALLOW
Fail-closed inputs (an unknown tier ranks above the top) keep an unclassified
high-risk verb gated rather than waved through.

<!-- mios-src:145f61874a4f from usr/lib/mios/agent-pipe/mios_pipe/access/arbiter.py:3-19 -->
