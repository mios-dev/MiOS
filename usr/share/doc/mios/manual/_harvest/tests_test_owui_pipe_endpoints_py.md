<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Hermetic endpoint-resolution tests for the OWUI entry-point pipe. Asserts the module IMPORTS at all (an unimported `Any` in a Pipe-body annotation made it unloadable, and lint-python did not scan usr/share/mios), that BACKEND_URL resolves from MIOS_AI_ENDPOINT and REFINE_ENDPOINT from MIOS_REFINE_ENDPOINT or [ports].llm_light rather than from frozen literals, that neither default names a port in [docs].retired_ports, and that the decommissioned-datastore writes are off unless MIOS_DB_URL is set. Skips cleanly when pydantic/aiohttp are absent.
AI-related: usr/share/mios/owui/pipes/mios_agent_pipe.py, usr/share/mios/mios.toml, automation/lint-python.sh
AI-functions: _load_pipe, TestOwuiPipeEndpoints, main

<!-- mios-src:1dbb6e46cda0 from tests/test-owui-pipe-endpoints.py:1-3 -->

