# AGENTS.md

> In-image agent contract for MiOS. This file is baked into the deployed root
> at `/AGENTS.md` and is the single source of truth for any AI agent running
> on a MiOS host.

**MiOS version:** v0.2.0
**API protocol:** OpenAI REST, served at `http://localhost:8080/v1` by LocalAI
**MCP discovery:** `/v1/mcp` (filesystem mirror) and `/usr/share/mios/ai/mcp/config.json`
**Model catalog:** `/usr/share/mios/ai/manifests/models.json`
**Stateful storage:** `/srv/ai/` (model weights, MCP server state)

## Surface contract

MiOS exposes an OpenAI-compatible REST surface. Agents that speak the OpenAI
protocol require no MiOS-specific SDK or wrapper.

- `GET  /v1/models` -- list locally available models
- `POST /v1/chat/completions` -- chat completions
- `POST /v1/completions` -- legacy completions
- `POST /v1/embeddings` -- embeddings
- `POST /v1/responses` -- responses API (where supported by the backend)

The backend defaults to LocalAI but is drop-in replaceable with Ollama, vLLM,
or llama.cpp. All speak the same protocol.

## Filesystem discovery

For agents that prefer filesystem reads over HTTP (offline, sandboxed):

- `/v1/models` is symlinked to `/usr/share/mios/ai/v1/models.json`
- `/v1/mcp` is symlinked to `/usr/share/mios/ai/mcp/`

## Vendor-neutral by design

MiOS does not ship vendor-specific agent SDKs, IDE plugins, or proprietary
integration shims. If an agent's host environment provides them, that is the
agent's concern; the OS surface is open-spec only.

## Observability

- Logs: `/var/log/mios/` (mios-ai.service, mios-ai-mcp.service)
- State: `/var/lib/mios/` (model cache, session state)
- User config: `~/.config/mios/` (XDG)

## Reference

- Architecture: `/usr/share/mios/INDEX.md` (system) or repository `INDEX.md`
- License surface: `/usr/share/mios/LICENSES.md`
- MCP spec: https://modelcontextprotocol.io/

## License

Apache-2.0.
