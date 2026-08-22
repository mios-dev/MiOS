<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib offline unit tests for mios_pipe.observability.drift_monitor -- the Jensen-Shannon Goodhart alarm (CONS-02). No network / no DB / no live model: the module is pure. Proves the Done-When math -- identical distributions score 0.0, disjoint ones score exactly 1.0 (log base 2 bound), the measure is symmetric and monotone in how far a verdict distribution has shifted, an axis missing from either side or backed by a thin live window is reported compared=False and never alerts, and crossing the threshold sets alerting on both the axis and the report. Run: python test_mios_drift_monitor.py
AI-related: ./mios_pipe/observability/drift_monitor.py, ./mios_pipe/routing/consensus.py
AI-functions: _server_or_skip, t_route_axis_extractors, t_route_payload_normalization, t_route_gate_closed, main

<!-- mios-src:5d98e1666f0f from usr/lib/mios/agent-pipe/test_mios_drift_monitor.py:1-3 -->

