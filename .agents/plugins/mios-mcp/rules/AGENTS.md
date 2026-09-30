# MiOS MCP Plugin Rules

When the `mios-mcp` plugin is active, the following MCP tools are available:

1. **`mios-control`** — The MiOS MCP server exposing all `[verbs.*]` and `[recipes.*]` from `mios.toml` as MCP tools.
   - Use `tools/list` to discover available system verbs (launch, configure, status, etc.)
   - Use `tools/call` to execute verbs via agent-pipe dispatch
   - Falls back to SSOT floor (mios.toml verbs+recipes) when agent-pipe is unavailable
2. **`dev-loop`** — Multi-harness dev-loop orchestrator for lane management, verification gates, and task ledger operations.
