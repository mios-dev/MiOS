<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-RES-GOV cost/energy accounting core (the PURE half, CLASSic "Cost" axis). MiOS's only budget signal was a token-count rolling tripwire -- there was ZERO $-cost or energy/kWh accounting, yet on a local-GPU OS the POWER ENVELOPE is the binding constraint. CostModel.estimate() turns one dispatch (prompt/completion tokens + wall-time + lane) into {energy_wh, usd, tokens}: a LOCAL GPU lane is priced by energy (gpu_watts x elapsed -> Wh -> $ at usd_per_kwh); a REMOTE lane by $/Mtok. CostLedger accumulates per-lane totals for budget checks + /v1 observability. Pure stdlib + deterministic so it unit-tests in isolation; server.py owns recording per dispatch + the SSOT rates, flag-gated. Sibling of mios_sched/mios_slo/mios_quota.
AI-related: ./mios_quota.py, ./mios_slo.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_cost.py
AI-functions: estimate, class CostModel, class CostLedger

<!-- mios-src:c89886607219 from usr/lib/mios/agent-pipe/mios_pipe/observability/cost.py:1-3 -->

