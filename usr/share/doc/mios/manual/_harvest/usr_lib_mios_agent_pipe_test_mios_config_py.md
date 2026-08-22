<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_config (refactor WS R1 config-constants extraction). Pure stdlib, no server.py/DB/pytest/FastAPI. Pins the SSOT readers + core config constants moved out of server.py: _toml_section returns a layered dict for any [section]; _cfg_num / _dispatch_num resolve env-override > table > literal default AND preserve a legit 0 (not a bare `or` chain); the endpoint/backend/auth constants (PORT, _LIGHT_BASE, BACKEND, _AUTH_HOSTPORTS, _AGENT_AUTH_BY_HOSTPORT, CLIENT_TOOLS_PASSTHROUGH, _HEAVY_PROBE_TTL, _DISPATCH_TOML, ...) keep their expected types/shapes. Guards the extracted config layer against silent drift.
AI-related: ./mios_config.py
AI-functions: check, t_import, t_toml_section, t_cfg_num, t_dispatch_num, t_constants, main

<!-- mios-src:084d1bc1583c from usr/lib/mios/agent-pipe/test_mios_config.py:1-4 -->

