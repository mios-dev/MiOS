# 'MiOS' AI Surface (LAW 5: UNIFIED-AI-REDIRECTS)

> Source: `INDEX.md` §2, `ARCHITECTURE.md` §AI-surface,
> `etc/containers/systemd/mios-ai.container`, `usr/share/mios/ai/system.md`.

## Contract

All 'MiOS' system agents, CLI tools, and embedded scripts target a single
OpenAI-compatible endpoint:

```
${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
```

This is **LAW 5: UNIFIED-AI-REDIRECTS**. Vendor LLM URLs (api.openai.com,
generativelanguage.googleapis.com, api.anthropic.com, etc.) are forbidden
**anywhere** in the image. If you need a cloud model, point
`MIOS_AI_ENDPOINT` at it (or proxy it through LiteLLM); never hardcode.

## API surfaces

| Surface | Method | Notes |
| --- | --- | --- |
| `/v1/models` | GET | Returns the catalog. Manifest at `usr/share/mios/ai/v1/models.json`. |
| `/v1/chat/completions` | POST | OpenAI Chat Completions shape. Streaming SSE supported (`stream: true`). Tool calling supported for capable models (`tools` array, `tool_choice`, `finish_reason: tool_calls`). |
| `/v1/completions` | POST | Legacy completions (text-in, text-out). Available but not preferred. |
| `/v1/embeddings` | POST | Returns vectors. The dim count depends on the loaded model. |

Auth: `Authorization: Bearer ${MIOS_AI_KEY}`. The empty string is
accepted by the local LocalAI stack; cloud endpoints require a real key.

## Implementation

A LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`:

```ini
[Unit]
Description='MiOS' Local AI (OpenAI-compatible)
After=network-online.target
Wants=network-online.target

[Container]
Image=quay.io/go-skynet/local-ai:latest
ContainerName=mios-ai
PublishPort=127.0.0.1:8080:8080
Volume=/srv/mios/ai/models:/models:Z
Environment=MODELS_PATH=/models
Environment=THREADS=8
Environment=CONTEXT_SIZE=4096
User=mios-ai
Group=mios-ai
Delegate=yes
# ConditionPathIsDirectory=/etc/mios/ai          # gating per LAW 5

[Service]
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target default.target
```

The Quadlet declares `User=`, `Group=`, `Delegate=yes` per **LAW 6:
UNPRIVILEGED-QUADLETS**, and the image is symlinked into
`/usr/lib/bootc/bound-images.d/` per **LAW 3: BOUND-IMAGES** by the
binder loop in `automation/08-system-files-overlay.sh:74-86`.

## Discovery surfaces

- `usr/share/mios/ai/v1/models.json` — `/v1/models`-shaped catalog
- `usr/share/mios/ai/v1/mcp.json` — MCP server registry (for clients that
  speak Model Context Protocol)
- `usr/share/mios/ai/system.md` — canonical agent prompt (see override
  chain below)

## System-prompt override chain

Highest to lowest precedence:

1. `~/.config/mios/system-prompt.md` — per-user
2. `/etc/mios/ai/system-prompt.md` — host/admin
3. `/usr/share/mios/ai/system.md` — vendor canonical (immutable)

Per-tool stubs at the repo root (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`)
are thin pointers that reference this chain.

## Env vars

| Variable | Purpose | Default |
| --- | --- | --- |
| `MIOS_AI_ENDPOINT` | OpenAI-compatible base URL | `http://localhost:8080/v1` |
| `MIOS_AI_KEY` | Bearer token | `` (empty) |
| `MIOS_AI_MODEL` | Default model id | first entry in `models.json` |
| `MIOS_AI_EMBED_MODEL` | Default embedding model id | `text-embedding-3-large` (proxied) or local equivalent |
| `MIOS_AI_GRADER` | Grader model for evals | `o3` (cloud) or `qwen2.5:32b` (local) |

These are set by `/etc/profile.d/mios-env.sh` from the three-layer env
overlay (see `30-overlay.md`).

## Day-0 portability

This contract is portable across every OpenAI-API-compatible runtime:

- **'MiOS' LocalAI** (canonical): `http://localhost:8080/v1`
- **OpenAI cloud**: `https://api.openai.com/v1`
- **Azure OpenAI**: `https://<res>.openai.azure.com/openai/deployments/<dep>`
- **Ollama**: `http://localhost:11434/v1`
- **vLLM**: `http://localhost:8000/v1`
- **LM Studio**: `http://localhost:1234/v1`
- **llama.cpp server**: `http://localhost:8080/v1` (collides with LocalAI on the same port — pick one)
- **LiteLLM proxy**: `http://localhost:4000/v1` (translates to/from any backend, including a Responses API shim)
- **OpenRouter**: `https://openrouter.ai/api/v1`

The KB ships sample payloads in both Chat Completions and Responses
shapes; see `srv/mios/api/`.

## What 'MiOS' LocalAI does NOT support

| Cloud surface | Local alternative |
| --- | --- |
| `/v1/responses` | Use `/v1/chat/completions`. |
| `/v1/vector_stores` | Self-host a vector DB; ingest `var/lib/mios/embeddings/chunks.jsonl`. |
| `/v1/batches` | Loop your batch JSONL through `/v1/chat/completions` synchronously. |
| `/v1/evals` | Run `var/lib/mios/evals/mios-knowledge.local-runner.py`. |
| `/v1/fine_tuning/jobs` | Use axolotl, trl, llama-factory, MLX-LM, or unsloth on `var/lib/mios/training/sft.jsonl`. |
| MCP tool (`type: "mcp"`) | Wire MCP via your client; LocalAI doesn't auto-fan-out MCP from the server side. |
