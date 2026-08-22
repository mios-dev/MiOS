<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for mios_clusterhealth -- the cluster/scheduler/health route LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). Stubs every injected dep via configure() plus the runtime-reassigned lane resolver (sys.modules["mios_lanes_resolver"]._lane_resolver_current) with no network / no DB, then asserts each moved *_logic still produces the byte-shape the @app thin wrappers used to: cluster_health_logic (per-agent effective_up/failover_only rollup + lane_resolver snapshot via the getter), scheduler_state_logic (per-lane concurrency + admission/priority/kernel posture object), and health_logic (capability/health rollup -- backend/router/dci/security/passport blocks). Run: python test_mios_clusterhealth.py
AI-related: ./mios_clusterhealth.py, ./server.py
AI-functions: main

<!-- mios-src:48d79e6d2c75 from usr/lib/mios/agent-pipe/test_mios_clusterhealth.py:1-3 -->

