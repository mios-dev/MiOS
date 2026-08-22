<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_cost (WS-RES-GOV cost/energy accounting, CLASSic Cost axis). Pure stdlib, no server.py/pytest. Verifies CostModel.estimate for a LOCAL GPU lane (energy = gpu_watts*elapsed -> Wh; $ from usd_per_kwh) and a REMOTE lane ($/Mtok, 0 local energy), plus the CostLedger accumulation (totals + per-lane breakdown) and remaining()/over_budget() against a $ ceiling.
AI-related: ./mios_cost.py
AI-functions: check, main

<!-- mios-src:b2a614f0cb44 from usr/lib/mios/agent-pipe/test_mios_cost.py:1-4 -->

