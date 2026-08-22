<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_slo (WS-SCHED-SLO deadline/SLO scheduling core). Pure stdlib, no server.py/pytest. Verifies classify (autonomous/clamped -> best_effort, foreground -> interactive), per-class deadline budgets, the EDF least-deadline-first sort key (earliest deadline first, interactive tie-break), and the FAIL-CLOSED shed decision (interactive never shed; best_effort shed under over-ceiling OR unknown-health, the inversion of the degrade-open hole).
AI-related: ./mios_slo.py
AI-functions: check, main

<!-- mios-src:cc0013f7718b from usr/lib/mios/agent-pipe/test_mios_slo.py:1-4 -->

