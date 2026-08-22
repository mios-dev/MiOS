<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A16 cost/quality SmartRouting core, designed per researched best practice (LiteLLM router + adaptive/cascading routing): LOCAL-FIRST escalation -- always try the cheap/local lane(s) first, and escalate to a stronger (remote) core ONLY when a quality gate fails or the local group is exhausted, paying the premium only when it matters, bounded by a per-day cost budget. Pure stdlib: a Lane cost/quality model, local-first ordering, the cascade pick (choose_next given what's been attempted + the quality verdict + the budget), and a CostLedger. server.py owns the actual remote calls (wiring the dead anthropic/gemini adapters) + the quality gate; this module owns the routing decision so it unit-tests in isolation.
AI-related: ./mios_lanes.py, ./mios_batch.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_smartroute.py
AI-functions: order_lanes, choose_next, should_escalate, class Lane, class CostLedger

<!-- mios-src:ebcb15def710 from usr/lib/mios/agent-pipe/mios_pipe/routing/smartroute.py:1-3 -->

