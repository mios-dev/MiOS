<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-SCHED-SLO deadline/SLO scheduling core (the PURE half). The MiOS admission gate is capacity-only (VRAM/host-load) and degrades OPEN -- it can't say "no" and a probe failure silently disables backpressure. This adds SLO request classes (interactive vs best_effort), a per-class deadline budget, a least-deadline-first sort key (EDF-style ordering for the priority gate), and a FAIL-CLOSED shed decision: a best_effort dispatch is shed under capacity contention OR when the health probe failed (treat unknown as contended), while an interactive/foreground turn is NEVER shed. Pure stdlib + deterministic so it unit-tests in isolation; server.py owns wiring classify->_admit shed + the EDF key into PriorityGate, flag-gated. Sibling of mios_sched/mios_preempt.
AI-related: ./mios_sched.py, ./mios_preempt.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_slo.py
AI-functions: classify, deadline, edf_key, should_shed

<!-- mios-src:456176af3e14 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/slo.py:1-3 -->

