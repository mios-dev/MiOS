# INSTALL.md -- Ingest the 'MiOS' KB into any OpenAI-API-compatible runtime

Three target classes, three recipes. Pick the one matching your stack.

---

## A) OpenAI cloud (full surface -- Vector Stores, Responses API, Evals, Batch)

```bash
export OPENAI_API_KEY=sk-...

# 1. Create a vector store
VS_ID=$(curl -s https://api.openai.com/v1/vector_stores \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"mios-kb"}' | jq -r .id)
echo "Vector store: $VS_ID"

# 2. Upload every doc as a File and capture file_ids
declare -A FILE_IDS
while IFS= read -r f; do
  fid=$(curl -s https://api.openai.com/v1/files \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F purpose=assistants -F file=@"$f" | jq -r .id)
  rel="${f#./}"
  FILE_IDS["$rel"]="$fid"
done < <(find ./usr/share/doc/mios -name '*.md' -type f)

# 3. Rewrite vector_store.import.jsonl with real file_ids and POST as file_batches
python3 - <<'PY'
import json, os, urllib.request
vs_id = os.environ["VS_ID"]
api_key = os.environ["OPENAI_API_KEY"]
mapping = json.loads(os.environ["FILE_IDS_JSON"])  # supply via env
files = []
for line in open("./var/lib/mios/embeddings/vector_store.import.jsonl"):
    obj = json.loads(line)
    rel = obj["attributes"]["fhs_path"].lstrip("/")
    if rel in mapping:
        obj["file_id"] = mapping[rel]
        files.append(obj)
req = urllib.request.Request(
    f"https://api.openai.com/v1/vector_stores/{vs_id}/file_batches",
    data=json.dumps({"files": files}).encode(),
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
print(urllib.request.urlopen(req).read().decode())
PY

# 4. Use it from Responses API
curl https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "$(jq --arg vs "$VS_ID" '.tools[0].vector_store_ids = [$vs]' ./srv/mios/api/responses.example.json)"

# 5. (Optional) create an eval
curl https://api.openai.com/v1/evals \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d @./var/lib/mios/evals/mios-knowledge.eval.json

# 6. (Optional) submit a fine-tuning job
FILE_ID=$(curl -s https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose=fine-tune -F file=@./var/lib/mios/training/sft.jsonl | jq -r .id)
curl https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "{\"training_file\":\"$FILE_ID\",\"model\":\"gpt-4.1-mini\"}"
```

---

## B) 'MiOS' LocalAI (the canonical Day-0 path -- `http://localhost:8080/v1`)

This is the endpoint 'MiOS' itself uses (LAW 5: UNIFIED-AI-REDIRECTS). It's
served by the LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`
and accepts the same Chat Completions / Embeddings shape as OpenAI.

```bash
# 0. Set the unified env vars (or rely on /etc/profile.d/mios-env.sh)
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}    # empty key accepted
export MIOS_AI_MODEL=${MIOS_AI_MODEL:-gpt-4o-mini}    # or whatever your LocalAI manifest names

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
  -d @./srv/mios/api/chat.local.example.json

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

## C) Other local runtimes (Ollama / vLLM / LM Studio / llama.cpp / LiteLLM)

Same as recipe B with a different `MIOS_AI_ENDPOINT`:

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

# LiteLLM proxy (translates many backends + emulates Responses API for cloud parity)
export MIOS_AI_ENDPOINT=http://localhost:4000/v1
export MIOS_AI_MODEL=gpt-4o-mini   # virtual model defined in litellm config.yaml
```

Then run recipe B steps 3-5 unchanged. The KB's chat-form payloads and
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

## Refreshing the KB from upstream 'MiOS'

```bash
# Use the mios_build_kb_refresh function tool against any cloud or local model.
# Or manually:
git clone https://github.com/mios-dev/MiOS.git /tmp/mios-src
python3 ./tools/regenerate_chunks.py /tmp/mios-src ./var/lib/mios/embeddings/chunks.jsonl
# then re-run the ingestion in recipe A or B.
```
