<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_cost -- cost/energy accounting for the agent plane...

mios_cost -- cost/energy accounting for the agent plane (WS-RES-GOV).

The gap audit + completeness critic: MiOS's _budget_admit is a token-count
rolling-window TRIPWIRE; there is no $-cost and no energy/kWh/VRAM-hour
accounting -- but CLASSic's Cost axis and modern local-GPU serving treat
energy-per-token + $-per-task as first-class signals (on a fully-local GPU OS the
power/thermal envelope is the real constraint, not an API bill).

This module is the PURE accounting:
  * CostModel.estimate() -- one dispatch -> {energy_wh, usd, tokens, lane}. Local
    GPU lane: energy = gpu_watts * elapsed_s; $ = energy * usd_per_kwh. Remote
    lane: $ = tokens * usd_per_mtok (energy attributed to the provider, 0 local).
  * CostLedger -- accumulate total + per-lane energy/$/tokens for budget checks
    (remaining() against a $ ceiling) + /v1/scheduler observability.

server.py owns recording each real dispatch (tokens from usage / tokenizer,
elapsed from the call timing) + the SSOT rates; this is the deterministic core.

<!-- mios-src:f8b5847cb1a2 from usr/lib/mios/agent-pipe/mios_pipe/observability/cost.py:3-20 -->
