# AGENTS.md -- AI agent contract for the deployed MiOS root overlay

This file describes how AI agents and OpenAI-compatible clients interact with a
running MiOS host. It is the deployed-image counterpart to MiOS-bootstrap's
INDEX.md (which governs build-time agent behavior).

## OpenAI namespace

The deployed root exposes:

- `/v1/models`          -> JSON manifest of locally available models
- `/v1/mcp`             -> MCP server configuration
- `/v1/chat/completions`-> served by LocalAI (Quadlet `mios-ai.container`)
- `/v1/responses`       -> served by LocalAI when configured for the 2026 Responses API

Both filesystem reads of `/v1/*` and HTTP requests to `http://localhost:8080/v1/*`
return equivalent content. Filesystem reads are appropriate for offline tooling;
HTTP is appropriate for any client expecting OpenAI semantics (streaming, tool
calls, structured outputs).

## Sovereign AI mandate

MiOS is engineered to run AI workloads entirely locally:

- Model weights live under `/srv/ai/` (stateful, persistent across `bootc upgrade`)
- Vector databases (Qdrant, Milvus) live under `/srv/ai/vectordb/`
- No telemetry, prompts, or embeddings are transmitted to external providers
  unless the operator explicitly configures an outbound endpoint in
  `/etc/mios/runtime.env`

## Filesystem laws agents must respect

- `/usr` is read-only composefs at runtime. Never attempt to write under `/usr`.
- `/etc` is read-write but bootc-managed; agent-modifiable config lives under
  `/etc/mios/` (admin) or `~/.config/mios/` (per-user).
- `/var/lib/mios/` and `/var/log/mios/` are agent-writable state.
- `/srv/ai/` is the only sanctioned location for large binary AI assets.

## Update model

Agents should not invoke `dnf`, `rpm`, or `flatpak install` against the host.
System updates flow exclusively via `bootc upgrade`; user applications via
`flatpak --user install` from a configured remote.

## Discovery

When introspecting a MiOS host, an agent's first reads should be:

1. `/usr/share/mios/manifest.json` (image metadata)
2. `/etc/mios/runtime.env`         (mutable per-host config)
3. `/v1/models`                    (locally available inference targets)
4. `/v1/mcp`                       (MCP server registry)

This ordering surfaces immutable facts before mutable ones.
