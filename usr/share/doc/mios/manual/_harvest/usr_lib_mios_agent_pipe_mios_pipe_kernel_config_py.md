<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure config-constant + SSOT-reader layer extracted from server.py (refactor WS R1). Module-level env/literal-derived constants (PORT, MCP_SERVER_PORT, _LIGHT_BASE, BACKEND/_BACKEND_IS_LIGHT/BACKEND_MODEL/_BACKEND_HOSTPORT, _HERMES_ENDPOINT/_HERMES_WORKER_ENDPOINT, _AUTH_HOSTPORTS, _AGENT_AUTH_BY_HOSTPORT, CLIENT_TOOLS_PASSTHROUGH, _TOOL_BACKEND*, _HEAVY_PROBE_TTL, _INGRESS_KEY, _STACK_MODEL/_MICRO_*) plus the layered mios.toml readers (_toml_section, _cfg_num, _dispatch_toml/_DISPATCH_TOML/_dispatch_num). Pure: stdlib (os, logging, tomllib/tomli) only -- NO import of server (one-way boundary, 98-drift-checks.sh check 6). server.py re-imports every name verbatim (surface-parity zero-diff); runtime-coupled fns (_apply_outbound_auth/_heavy_lane_up/_lane_resolver/_pick_tool_backend) STAY in server.py and call these re-imported readers/constants.
AI-related: ./server.py, ./test_mios_config.py, ./mios_surface.py, /usr/share/mios/mios.toml
AI-functions: _toml_section, _cfg_num, _dispatch_toml, _dispatch_num

<!-- mios-src:5b9efc7c2cf9 from usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py:1-3 -->

