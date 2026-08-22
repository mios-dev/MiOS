<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_endpoints (refactor R-wave leaf extraction). Pure stdlib, no server.py/DB/pytest. Pins the endpoint protocol/capability invariants that drive lane routing: _binding_api reads the per-engine then per-agent `api` field (case-folded); _endpoint_is_llamacpp / _endpoint_supports_tool_choice are CONFIG-FIRST (an `api`/`tool_choice` field wins) and otherwise fall back to env-SSOT host:port hint substrings; _endpoint_supports_parallel_tools is hint-only opt-in. MiOS is /v1-only, so there is no wire-dialect to detect -- only /v1 feature-set. Sets the MIOS_*_HINTS env vars BEFORE import so the module-load-time hint tuples are deterministic (independent of mios.toml [dispatch]). Guards the extracted leaf so a later move/refactor can't silently change which feature-set a lane is classified as.
AI-related: ./mios_endpoints.py
AI-functions: check, t_binding_api, t_tool_choice, t_parallel, t_is_llamacpp, main

<!-- mios-src:b0d71d8a1737 from usr/lib/mios/agent-pipe/test_mios_endpoints.py:1-4 -->

