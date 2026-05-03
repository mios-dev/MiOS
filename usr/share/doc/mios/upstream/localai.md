# LocalAI -- MiOS's Canonical Local LLM Endpoint

> 'MiOS' LAW 5 (UNIFIED-AI-REDIRECTS) requires every system agent to
> target `http://localhost:8080/v1`. The endpoint is served by the
> LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`.
> Source: `INDEX.md` §AI-surface, `ARCHITECTURE.md` §AI-surface,
> `usr/share/doc/mios/70-ai-surface.md`.

## Project

- Repo: <https://github.com/mudler/LocalAI>
- Docs: <https://localai.io/>
- License: MIT (FOSS -- aligns with MiOS's FOSS posture)

## Why LocalAI specifically

LocalAI is the OpenAI-API-compatible facade with the broadest backend
support -- llama.cpp, vLLM-style, transformers, gpt4all, exllama,
whisper.cpp, stable-diffusion, embeddings via sentence-transformers,
audio TTS/STT, all behind one consistent `/v1/*` surface. 'MiOS' treats
it as the runtime; users swap models via the LocalAI manifest, not by
swapping endpoint code.

## Surfaces exposed at `http://localhost:8080/v1`

| Endpoint | Purpose | Day-0 with this KB |
| --- | --- | --- |
| `GET /v1/models` | Model catalog | [ok] |
| `POST /v1/chat/completions` | Chat (SSE streaming + tool calling) | [ok] -- KB ships `chat.local.example.json` |
| `POST /v1/embeddings` | Embeddings | [ok] -- KB ships `chunks.jsonl` + `ingest_local.py` |
| `POST /v1/completions` | Legacy completions | [!] -- not used by 'MiOS' agents |
| `POST /v1/audio/speech` (TTS) | Optional | future |
| `POST /v1/audio/transcriptions` (STT) | Optional | future |

## Auth

`Authorization: Bearer $MIOS_AI_KEY` -- empty key accepted by the local
stack. Vendor URLs are forbidden anywhere in the image (LAW 5). The
unified env vars resolve via `/etc/profile.d/mios-env.sh`:

```bash
export MIOS_AI_ENDPOINT=http://localhost:8080/v1
export MIOS_AI_KEY=                # empty
export MIOS_AI_MODEL=gpt-4o-mini   # whatever LocalAI manifest names; 'MiOS' aliases
```

## Discovery surfaces (MiOS-specific)

- `usr/share/mios/ai/v1/models.json` -- `/v1/models`-shaped catalog (matches what LocalAI returns)
- `usr/share/mios/ai/v1/mcp.json` -- MCP server registry (MiOS-internal)
- `usr/share/mios/ai/system.md` -- canonical agent prompt

## Tool calling

Modern models served via LocalAI (Llama 3.1+, Qwen 2.5+, Hermes 3+,
Firefunction, Mistral 0.3+) support OpenAI-format tool calls. Strict
mode (`strict: true`) is *accepted* but not *enforced* by the server --
ship the schemas anyway as in-context documentation. For enforced JSON
Schema compliance, run vLLM with xgrammar or llama.cpp with grammars.

## Cross-refs

- `usr/share/doc/mios/70-ai-surface.md`
- `usr/share/doc/mios/upstream/related-distros.md` (Ollama / vLLM / LM Studio / llama.cpp / LiteLLM as alternative endpoints)
- `etc/containers/systemd/mios-ai.container` (the Quadlet itself)
