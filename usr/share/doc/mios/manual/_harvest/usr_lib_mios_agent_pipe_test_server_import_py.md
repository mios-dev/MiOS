<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Near-runtime import gate for...

!/usr/bin/env python3
AI-hint: Near-runtime import gate for the agent-pipe strangler-fig refactor (WS R0+). Stubs the 3rd-party deps not guaranteed on a bare checkout (httpx/websockets/uvicorn + a minimal fastapi) so that `import server` actually EXECUTES every module-level statement: all config, all defs, EVERY re-import of an extracted symbol, and EVERY stacked `sys.modules["mios_*"].configure(...)` dependency-injection call. A misordered configure() (an injected symbol referenced before it is defined) raises a NameError HERE — the exact runtime regression class that py_compile (syntax-only) and mios_surface (ast, no execution) cannot catch. Then asserts each extracted symbol resolves to its sibling module (server is a thin re-export shim for them). Importing has no side effects: uvicorn.run is __main__-guarded and the background daemons start in the FastAPI lifespan, not at import. Pure stdlib + unittest.mock. Run after every extraction wave.
AI-related: ./server.py, ./mios_surface.py, ./mios_config.py, ./mios_grounding.py, ./mios_verity.py, ./mios_skills.py, ./mios_fanout.py, ./mios_dci.py
AI-functions: _install_stubs, _resolve_toml, check, main

<!-- mios-src:d1ba27cf17f7 from usr/lib/mios/agent-pipe/test_server_import.py:1-4 -->

