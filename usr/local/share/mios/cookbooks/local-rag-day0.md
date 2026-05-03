# Cookbook: Day-0 Local RAG against 'MiOS' LocalAI

> Full path: `/usr/local/share/mios/cookbooks/local-rag-day0.md`
> Canonical local target. Same recipe works against Ollama / vLLM /
> LM Studio / llama.cpp / LiteLLM by changing `MIOS_AI_ENDPOINT`.

## Why this path

LAW 5 (UNIFIED-AI-REDIRECTS) requires every 'MiOS' agent to target
`http://localhost:8080/v1` -- the LocalAI Quadlet at
`etc/containers/systemd/mios-ai.container`. Running the KB through
the same endpoint gives bit-for-bit consistency between what an
end-user agent sees and what your retrieval/eval pipeline sees.

## Prerequisites

```bash
# Inside 'MiOS' (or any Linux host with podman + python3)
sudo systemctl is-active mios-ai.service && echo "LocalAI is up"

# Or for non-'MiOS' hosts, start a Qdrant for the vector index:
podman run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $PWD/qdrant_data:/qdrant/storage:Z docker.io/qdrant/qdrant:latest

pip install httpx qdrant-client
```

## Step 1 -- Set the unified env (matches `/etc/profile.d/mios-env.sh`)

```bash
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}              # empty key OK for local
export MIOS_AI_MODEL=${MIOS_AI_MODEL:-gpt-4o-mini}    # whatever LocalAI alias
export MIOS_AI_EMBED_MODEL=${MIOS_AI_EMBED_MODEL:-text-embedding-3-large}
```

Verify:

```bash
curl -fsS "$MIOS_AI_ENDPOINT/models" \
  -H "Authorization: Bearer $MIOS_AI_KEY" | jq '.data[].id'
```

## Step 2 -- Embed `chunks.jsonl` into Qdrant

```bash
python3 ./var/lib/mios/embeddings/ingest_local.py \
  ./var/lib/mios/embeddings/chunks.jsonl
```

You'll see batched embedding progress and a sanity probe at the end.

## Step 3 -- Query the index from your application

```python
import os, httpx
from qdrant_client import QdrantClient

endpoint = os.environ["MIOS_AI_ENDPOINT"]
key      = os.environ.get("MIOS_AI_KEY", "")
embed_m  = os.environ["MIOS_AI_EMBED_MODEL"]
chat_m   = os.environ["MIOS_AI_MODEL"]
qdrant   = QdrantClient(url="http://localhost:6333")

def retrieve(query: str, k: int = 5):
    headers = {"Content-Type": "application/json"}
    if key: headers["Authorization"] = f"Bearer {key}"
    qv = httpx.post(f"{endpoint}/embeddings", headers=headers,
                    json={"model": embed_m, "input": [query]}).json()["data"][0]["embedding"]
    return qdrant.search(collection_name="mios-kb", query_vector=qv, limit=k)

def answer(query: str):
    hits = retrieve(query)
    context = "\n\n".join(f"[{h.payload['chunk_id']}] {h.payload['text']}" for h in hits)
    headers = {"Content-Type": "application/json"}
    if key: headers["Authorization"] = f"Bearer {key}"
    msgs = [
        {"role": "system",
         "content": "You are MiOS-Engineer. Cite chunk IDs (e.g. [mios-006]) when you use a passage."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]
    return httpx.post(f"{endpoint}/chat/completions", headers=headers,
                      json={"model": chat_m, "messages": msgs}).json()["choices"][0]["message"]["content"]

print(answer("Why does 'MiOS' use lockdown=integrity not confidentiality?"))
```

## Step 4 -- Run the eval against your local stack

```bash
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint "$MIOS_AI_ENDPOINT" \
  --model    "$MIOS_AI_MODEL" \
  --eval     ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset  ./var/lib/mios/evals/dataset.jsonl \
  --report   ./mios-eval-report.json
```

Pass rate < 100% indicates retrieval/model gaps to address.

## Switching to a different local runtime

| Runtime | `MIOS_AI_ENDPOINT` | `MIOS_AI_MODEL` |
| --- | --- | --- |
| 'MiOS' LocalAI (canonical) | `http://localhost:8080/v1` | (per LocalAI manifest) |
| Ollama | `http://localhost:11434/v1` | `qwen2.5:32b` etc. |
| vLLM | `http://localhost:8000/v1` | `meta-llama/Llama-3.1-70B-Instruct` |
| LM Studio | `http://localhost:1234/v1` | (per LM Studio loaded model) |
| llama.cpp server | `http://localhost:8080/v1` | `any` (server returns its loaded model) |
| LiteLLM proxy | `http://localhost:4000/v1` | (per litellm config.yaml) |
| OpenRouter | `https://openrouter.ai/api/v1` | `meta-llama/llama-3.1-70b-instruct` |

The rest of the recipe is unchanged. **This is the Day-0 portability
guarantee.**
