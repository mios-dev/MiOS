<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_smartroute -- cost/quality SmartRouting for the MiOS...

mios_smartroute -- cost/quality SmartRouting for the MiOS agent-pipe (WS-A16,
the AIOS SmartRouting / remote-core escalation layer).

Pure stdlib. RESEARCH NOTE (the proper solution): the production pattern (LiteLLM
router, adaptive/cascading routing) is LOCAL-FIRST with quality-gated escalation
-- run the cheap local lane first, escalate to a stronger/remote core only when
the local output fails a quality check or the local group is exhausted, so the
premium (a paid remote token) is paid only when it actually buys quality.
Escalation is also bounded by a per-day cost budget (a runaway can't drain it).
This module is the routing DECISION; server.py runs the lanes + the quality gate
+ the real remote adapter calls.

Sources: LiteLLM Router (docs.litellm.ai/docs/routing), LiteLLM Adaptive Router,
"LLM Gateways & Model Routing" cost-optimization guides (2026).

<!-- mios-src:5395ee0379d5 from usr/lib/mios/agent-pipe/mios_pipe/routing/smartroute.py:3-17 -->
