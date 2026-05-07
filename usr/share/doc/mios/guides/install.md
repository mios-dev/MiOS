# usr/share/doc/mios/guides/install.md -- Ingest the 'MiOS' KB into any OpenAI-API-compatible runtime

Two recipe classes — pick the one matching your stack. Both target an
OpenAI-API-compatible local endpoint per Architectural Law 5
(UNIFIED-AI-REDIRECTS): no vendor-cloud URLs, no proprietary
side-channels.

---

## A) 'MiOS' LocalAI (the canonical Day-0 path -- `http://localhost:8080/v1`)

This is the endpoint 'MiOS' itself uses. It's served by the LocalAI
Quadlet at `etc/containers/systemd/mios-ai.container` and accepts the
OpenAI Chat Completions / Embeddings / Responses shapes.

```bash
# 0. Set the unified env vars (or rely on /etc/profile.d/mios-env.sh)
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}    # empty key accepted
export MIOS_AI_MODEL=${MIOS_AI_MODEL:-qwen2.5-coder:7b}     # canonical mios.toml [ai].model
export MIOS_AI_EMBED_MODEL=${MIOS_AI_EMBED_MODEL:-nomic-embed-text}

# 1. Verify the endpoint
curl -fsS "$MIOS_AI_ENDPOINT/models" -H "Authorization: Bearer $MIOS_AI_KEY" | jq '.data[].id'

# 2. Stand up a self-hosted vector DB (pick one; recipe shown for Qdrant)
podman run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $PWD/qdrant_data:/qdrant/storage:Z docker.io/qdrant/qdrant:latest

# 3. Embed and ingest chunks.jsonl (universal RAG payload)
python3 ./var/lib/mios/embeddings/ingest_local.py    # emitted alongside chunks.jsonl
# That script reads chunks.jsonl, calls $MIOS_AI_ENDPOINT/embeddings,
# and upserts into Qdrant collection "mios-kb".

# 4. Use it -- Chat Completions form (universal)
curl "$MIOS_AI_ENDPOINT/chat/completions" \
  -H "Authorization: Bearer $MIOS_AI_KEY" -H "Content-Type: application/json" \
  -d @./usr/share/mios/api/chat.local.example.json

# 5. Run the eval against the local endpoint
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint "$MIOS_AI_ENDPOINT" --model "$MIOS_AI_MODEL" \
  --eval ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset ./var/lib/mios/evals/dataset.jsonl
```

The local-runner.py prints per-item pass/fail and a final pass rate; it
implements `string_check`, `text_similarity`, and `score_model` graders
against any `/v1/chat/completions` endpoint.

---

## B) Other local runtimes (Ollama / vLLM / LM Studio / llama.cpp / LiteLLM)

Same as recipe A with a different `MIOS_AI_ENDPOINT`:

```bash
# Ollama
export MIOS_AI_ENDPOINT=http://localhost:11434/v1
export MIOS_AI_MODEL=qwen2.5:32b   # or any pulled model with tool-calling support

# vLLM (from `vllm serve <model>` on default port)
export MIOS_AI_ENDPOINT=http://localhost:8000/v1
export MIOS_AI_MODEL=meta-llama/Llama-3.1-70B-Instruct

# LM Studio
export MIOS_AI_ENDPOINT=http://localhost:1234/v1
export MIOS_AI_MODEL=lmstudio-community/Qwen2.5-72B-Instruct-GGUF

# llama.cpp server
export MIOS_AI_ENDPOINT=http://localhost:8080/v1
export MIOS_AI_MODEL=any   # llama.cpp ignores model name, returns its loaded model

# LiteLLM proxy (translates many backends through one OpenAI-compatible surface)
export MIOS_AI_ENDPOINT=http://localhost:4000/v1
export MIOS_AI_MODEL=qwen2.5-coder:7b   # virtual model defined in litellm config.yaml
```

Then run recipe A steps 3-5 unchanged. The KB's chat-form payloads and
chat-form tool schemas are universal across all of these.

---

## Notes on tool calling with local models

Function calling support varies by model:

| Model family | Tool-call support | Notes |
|---|---|---|
| Llama 3.1+ Instruct | [ok] | Native, OpenAI-format tools |
| Llama 3.2 Vision | [ok] | Same |
| Qwen 2.5 / 3 Instruct | [ok] | Excellent; supports parallel tool calls |
| Mistral / Mixtral Instruct | [ok] | Recent versions |
| Hermes 3 / Hermes 4 | [ok] | Specifically tuned for tools |
| Firefunction v2 | [ok] | Purpose-built for function calling |
| Phi-3+ Instruct | [!] partial | Single tool calls only |
| Older base models |  | Use a tool-tuned variant |

For models that ignore `strict: true`, ship the schemas anyway -- they
serve as in-context documentation for the model. If you need *enforced*
JSON Schema compliance locally, use **vLLM with xgrammar** or
**llama.cpp grammars** (compile your JSON Schema to a GBNF grammar).

---

## Cloud-only OpenAI API surfaces

The OpenAI API spec defines surfaces that LocalAI / Ollama / vLLM / LM
Studio / llama.cpp typically do **not** implement: Vector Stores,
Files (`purpose=assistants`/`fine-tune`), Batch API, Evals API, Fine-
tuning Jobs. **MiOS does not document a recipe that hardcodes a
vendor-cloud endpoint** — Architectural Law 5 forbids it.

If you have an OpenAI-API-compatible endpoint that implements these
surfaces (LocalAI v3+ partial support, LiteLLM proxy fronting a custom
backend, a self-hosted compatible service), set `$MIOS_AI_ENDPOINT` and
`$MIOS_AI_KEY` and the recipes work unchanged. For local fine-tuning
without those surfaces, see `usr/share/mios/cookbooks/finetune-flow.md`
(axolotl / trl / MLX-LM / unsloth paths).

---

## Refreshing the KB from upstream 'MiOS'

```bash
# Use the mios_build_kb_refresh function tool against any local endpoint.
# Or manually:
git clone https://github.com/mios-dev/MiOS.git /tmp/mios-src
python3 ./tools/regenerate_chunks.py /tmp/mios-src ./var/lib/mios/embeddings/chunks.jsonl
# then re-run the ingestion in recipe A.
```
