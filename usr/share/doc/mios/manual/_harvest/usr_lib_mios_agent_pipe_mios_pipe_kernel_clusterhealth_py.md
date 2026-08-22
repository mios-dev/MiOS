<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: CLUSTER/SCHEDULER/HEALTH route-handler LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). Owns the *_logic bodies behind the three deferred liveness/observability endpoints: the per-agent + per-endpoint health probe (/v1/cluster/health -> cluster_health_logic), the AIOS-style per-lane scheduler snapshot (/v1/scheduler -> scheduler_state_logic), and the capability/health rollup (/health -> health_logic). These were deferred from the R-CAPS wave because they read the runtime-REASSIGNED lane-resolver singleton; that landmine is solved -- mios_lanes_resolver owns it behind _lane_resolver_current(), which the moved cluster-health body already reaches through sys.modules, so nothing is injected by value. Bodies moved byte-identically; the @app routes stay THIN in server.py calling these via sys.modules so the HTTP + importable surface is unchanged. Static config is imported from mios_config, the DCI posture from mios_dci, the SLO classes from mios_slo, and the privilege-set provenance from mios_secset; every server-resident runtime global/helper is dependency-INJECTED via configure(). This module NEVER imports server.
AI-related: ./server.py, ./mios_config.py, ./mios_dci.py, ./mios_slo.py, ./mios_secset.py, ./test_mios_clusterhealth.py
AI-functions: cluster_health_logic, scheduler_state_logic, health_logic, clusterhealth_router, cluster_health, scheduler_state, health, configure

<!-- mios-src:c705ecb3d3b6 from usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py:1-3 -->

