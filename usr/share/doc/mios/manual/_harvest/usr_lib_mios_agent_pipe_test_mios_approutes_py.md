<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Runtime route-parity gate...

!/usr/bin/env python3
AI-hint: Runtime route-parity gate for the agent-pipe strangler-fig refactor (WS R13 Step 2b) -- the LIVE-FastAPI complement to the AST-only mios_surface gate. Where mios_surface/test_mios_surface project server.py's route table by PARSING text (no execution), this gate BUILDS the real app: it stubs ONLY the one heavy dep absent on a bare host (websockets) and imports server with the genuine fastapi/starlette/pydantic/uvicorn/httpx, so server.app is a real fastapi.FastAPI. It enumerates every route the running app actually registers, filters FastAPI's framework-injected built-ins (the docs/schema/redoc set) by path, drops the auto-paired HEAD, normalises a websocket route to a single method token, and asserts that method+path set is EXACTLY the committed surface golden's route set -- so a future routes->APIRouter migration that drops, renames, or fails to mount a served route reds the build at RUNTIME, catching what a static projection cannot (a route that parses but never binds). Portable: a bare checkout without fastapi skipTests like the suite's crypto skips. A second test asserts server.app is a real FastAPI (not a stub) so the gate can never silently pass against a faked app. Stdlib unittest only.
AI-related: ./server.py, ./mios_surface.py, ./test_mios_surface.py, ./test_server_import.py, ../../../share/mios/ai/v1/surface.generated.json, ../../../../automation/98-drift-checks.sh
AI-functions: _is_repo_module, _install_websockets_stub, _repo_root, _golden_path, _resolve_mios_toml, _app_route_pairs, _golden_route_pairs, TestAppRouteParity.setUpClass, TestAppRouteParity.test_app_is_real_fastapi, TestAppRouteParity.test_route_parity_with_golden

<!-- mios-src:30436322e308 from usr/lib/mios/agent-pipe/test_mios_approutes.py:1-4 -->

