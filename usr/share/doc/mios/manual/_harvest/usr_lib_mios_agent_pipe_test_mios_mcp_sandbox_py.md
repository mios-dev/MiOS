<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for T-032 (SEC-01 Hermetic MCP Sandboxing). Pure stdlib + asyncio, no server.py/DB/network. Verifies MCP sandbox gate parsing, gatekeeper traversal blocking, and _McpStdioClient._spawn routing through the gatekeeper.
AI-related: ./mios_pipe/federation/mcp.py, /usr/libexec/mios/mcp-server-runner
AI-functions: check, t_sandbox_gate_parsing, t_gatekeeper_traversal_blocking, t_spawn_routes_through_gatekeeper, t_spawn_direct_when_disabled, main

<!-- mios-src:072809e982b3 from usr/lib/mios/agent-pipe/test_mios_mcp_sandbox.py:1-4 -->

