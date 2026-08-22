<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### External-MCP consume client for the agent-pipe federated...

External-MCP consume client for the agent-pipe federated tool surface (refactor R-MCP).

Extracted VERBATIM from ``server.py``. MiOS CONSUMES external MCP servers (not
just publishes its own): a layered registry read, an initialize handshake over
Streamable-HTTP or a spawned stdio subprocess, ``tools/list`` registration of
every remote tool namespaced ``mcp.<server>.<tool>``, and ``tools/call``
forwarding. The ``GET /v1/mcp/clients`` / ``GET /v1/mcp/tools`` /
``POST /v1/mcp/dispatch`` routes stay in ``server.py`` as thin wrappers calling
the ``*_logic`` functions here.

The shared MCP-tool registry + lock (``_MCP_CLIENT_TOOLS`` / ``_MCP_CLIENT_LOCK``)
remain server-resident (the worker / toolsearch / toolexec planes share them) and
are injected via :func:`configure`, together with the HTTP client factory, the
per-tool embedder (``_mcp_embed_new_tools``, from ``mios_toolsearch``), and the
worker-tool-surface cache invalidator. This module never imports ``server``
(one-way boundary); ``server.py`` re-imports every moved name under its original
alias so the importable surface is byte-identical.

The declared revision is the ``[mcp].protocol_version`` SSOT
(:data:`MCP_PROTOCOL_VERSION`, env ``MIOS_MCP_PROTOCOL_VERSION``). The newer MCP
feature set (durable Tasks, elicitation, OAuth resource-server auth, tool icons,
structured tool output) and the upcoming stateless-transport revision are scoped
follow-ups; this client implements the core initialize / tools-list / tools-call
consume path over Streamable-HTTP (current) + stdio.

<!-- mios-src:d7b2cccfa70c from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:3-27 -->

### Layered registry read

Layered registry read: vendor < /etc < user. Later overlays REPLACE
    earlier entries with the same id (not merge) so an operator can disable a
    vendor entry by re-declaring it with enabled:false.

<!-- mios-src:b81ca5cb9ce8 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:106-108 -->

### Long-lived MCP server subprocess speaking newline-delimited...

Long-lived MCP server subprocess speaking newline-delimited JSON-RPC 2.0
 over stdin/stdout (MCP stdio transport). Mirrors _mcp_http_rpc's
    error-envelope shape so callers need NO special-casing. Self-heals: a dead
    process is respawned AND re-initialized on the next call (restart-on-crash).
    Non-blocking (asyncio subprocess + StreamReader.readline). stderr -> DEVNULL
    (spec: the server MAY log to stderr; the client MAY ignore it).

<!-- mios-src:e7659031ee24 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:173-178 -->

### P4: surface a stdio MCP server's stderr (first chunk) in...

P4: surface a stdio MCP server's stderr (first chunk) in the journal instead of
        silently discarding it -- otherwise a spawn/crash is an opaque 'stdio init failed'.

<!-- mios-src:f2dca439aad7 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:223-224 -->
