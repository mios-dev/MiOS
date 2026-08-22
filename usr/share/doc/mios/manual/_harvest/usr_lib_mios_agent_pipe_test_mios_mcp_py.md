<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for mios_mcp -- the external-MCP CONSUME client extracted from server.py (refactor R-MCP). Hermetically stubs httpx + fastapi.responses + the injected deps (HTTP client / MCP-tool registry+lock / embedder / worker-cache invalidator) with NO network, DB, or subprocess, and asserts: the layered registry read (later overlay REPLACES by id), the ${ENV} header expansion, _mcp_http_rpc parsing BOTH application/json and text/event-stream responses, the per-server probe PROJECTION (tools/list -> mcp.<sid>.<tool> registry entries carrying namespace/tier/taint/examples + cache-invalidate + embed side-effects), the /v1/mcp/clients + /v1/mcp/tools + /v1/mcp/dispatch route-logic shapes, and the _McpStdioClient self-heal state machine (initialize once, skip re-init while alive, respawn+re-initialize after the subprocess dies).
AI-related: ./mios_mcp.py, ./server.py
AI-functions: _run, test_render_headers, test_load_registry_layered, test_http_rpc_json, test_http_rpc_sse, test_probe_server_projection, test_route_logic_shapes, test_call_tool_unknown, test_stdio_self_heal

<!-- mios-src:9af6453758c3 from usr/lib/mios/agent-pipe/test_mios_mcp.py:1-3 -->

