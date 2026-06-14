<!-- AI-hint: Instructional cookbook for standing up a Day-0 local RAG pipeline ON MiOS against the unified OpenAI-compatible endpoint -- embeddings via nomic-embed-text on the mios-llm-light lane (:11450), vectors stored in PostgreSQL+pgvector, chat via the same MIOS_AI_ENDPOINT every agent uses. Shows how retrieval/eval reproduce exactly what a MiOS agent sees (Law 5), and how the same recipe ports to any OpenAI-compatible runtime.
     AI-related: /usr/share/mios/cookbooks/local-rag-day0.md, /usr/share/mios/mios.toml, /usr/share/mios/llamacpp/mios-llm-light.yaml, /usr/share/containers/systemd/mios-llm-light.container, /usr/share/containers/systemd/mios-pgvector.container, mios-llm-light, mios-pgvector, mios-pg-query, mios-db, mios-env, mios-knowledge, mios-eval-report, MIOS_AI_ENDPOINT -->
# Cookbook: Day-0 Local RAG on MiOS (unified endpoint + pgvector)

> Full path: `/usr/share/mios/cookbooks/local-rag-day0.md`
> Canonical local target. The same recipe works against any OpenAI-API
> runtime (vLLM / SGLang / LM Studio / a bare `llama.cpp` server / LiteLLM)
> by changing `MIOS_AI_ENDPOINT` — that portability is the point of Law 5.

## Where this fits in MiOS

MiOS is one image built two ways at once: an immutable, bootc/OCI Fedora
workstation *and* a local, self-hosted agentic AI OS. The whole AI surface —
inference lanes, the agent-pipe orchestrator, MiOS-Hermes, MCP/A2A, and a
PostgreSQL+pgvector memory — ships inside the same image and is reachable
through **one** OpenAI-compatible front door named by `MIOS_AI_ENDPOINT`
(default `http://localhost:8080/v1`). That single endpoint is **Architectural
Law 5 (UNIFIED-AI-REDIRECTS)**: every agent and tool on the box talks to it,
with no vendor-hardcoded URLs.

This cookbook stands up your **own** retrieval-augmented-generation pipeline
on top of that surface, using the components MiOS already runs:

- **Embeddings + chat** come from the **`mios-llm-light`** lane (`:11450`,
  the primary inference engine), surfaced through the unified endpoint. It
  serves the everyday chat/reasoning models *and* embeddings
  (`nomic-embed-text`, OpenAI-compatible `/v1/embeddings`).
- **Vectors** live in **PostgreSQL + pgvector** (`mios-pgvector`, `:5432`) —
  the same unified agent datastore that backs MiOS's own `knowledge`,
  `agent_memory`, and RAG tables. You are not bolting on a second vector
  store; you are using the one the agent stack already uses.

The payoff is **bit-for-bit consistency**: because your retrieval and eval
pipeline resolve the same `MIOS_AI_ENDPOINT` and the same embedding model an
end-user agent sees, what you measure is what the agent actually experiences.
That is what makes Day-0 evaluation trustworthy on MiOS.

## Why pgvector and not a sidecar vector DB

MiOS retired its early SurrealDB/Qdrant stack: the unified datastore is now
**PostgreSQL + pgvector** (container `mios-pgvector`, accessed in MiOS via the
pure-python `mios-pg-query` client and `mios-db --pg`). Putting your KB
vectors in the same Postgres keeps one backup surface, one access path, and
one embedding contract for both your RAG and the agent's own memory recall.

## Prerequisites

On MiOS, the inference lane and the vector store are already part of the
image — just confirm they're up:

```bash
# Inference + embeddings (the primary lane behind MIOS_AI_ENDPOINT)
systemctl is-active mios-llm-light.service && echo "mios-llm-light is up"

# Unified agent datastore (PostgreSQL + pgvector)
systemctl is-active mios-pgvector.service  && echo "pgvector is up"

# Python client deps for this recipe
pip install httpx psycopg "psycopg[binary]" pgvector
```

On a **non-MiOS** Linux host (replicating the recipe elsewhere), bring up a
pgvector Postgres and point an OpenAI-compatible engine at
`MIOS_AI_ENDPOINT`:

```bash
podman run -d --name pgvector -p 5432:5432 \
  -e POSTGRES_PASSWORD=mios -e POSTGRES_DB=mios \
  -v $PWD/pgdata:/var/lib/postgresql/data:Z \
  docker.io/pgvector/pgvector:pg17
```

> The container image (`ghcr.io/mostlygeek/llama-swap`) and the
> OpenAI/Ollama-compatible API are legitimate **upstream** references — they
> are external tools MiOS integrates. The MiOS *service identity* of the
> primary lane is `mios-llm-light`.

## Step 1 — Set the unified env (matches `/etc/profile.d/mios-env.sh`)

`MIOS_AI_ENDPOINT` is the single OpenAI-compatible endpoint every MiOS agent
and tool targets (Law 5). The model + embed-model defaults come from
`mios.toml [ai]` (`model`, `embed_model`):

```bash
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}                               # empty key OK for local
export MIOS_AI_MODEL=${MIOS_AI_MODEL:-granite4.1:8b}                 # canonical mios.toml [ai].model
export MIOS_AI_EMBED_MODEL=${MIOS_AI_EMBED_MODEL:-nomic-embed-text}  # canonical [ai].embed_model
export MIOS_PG_DSN=${MIOS_PG_DSN:-postgresql:///mios}             # local pgvector (mios-pgvector :5432)
```

Verify the endpoint resolves and lists models:

```bash
curl -fsS "$MIOS_AI_ENDPOINT/models" \
  -H "Authorization: Bearer $MIOS_AI_KEY" | jq '.data[].id'
```

## Step 2 — Create the KB collection in pgvector

`nomic-embed-text` produces 768-dim vectors, so the column is `vector(768)`
(the same dimension MiOS's own `knowledge`/`agent_memory` tables use):

```bash
psql "$MIOS_PG_DSN" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS mios_kb (
  chunk_id  text PRIMARY KEY,
  text      text NOT NULL,
  embedding vector(768)
);
CREATE INDEX IF NOT EXISTS mios_kb_embedding_idx
  ON mios_kb USING hnsw (embedding vector_cosine_ops);
SQL
```

## Step 3 — Embed `chunks.jsonl` into pgvector

```bash
python3 ./var/lib/mios/embeddings/ingest_local.py \
  ./var/lib/mios/embeddings/chunks.jsonl
```

A minimal ingester (each line of `chunks.jsonl` is `{"chunk_id": ..., "text": ...}`):

```python
import json, os, sys, httpx, psycopg
from pgvector.psycopg import register_vector

endpoint = os.environ["MIOS_AI_ENDPOINT"]
key      = os.environ.get("MIOS_AI_KEY", "")
embed_m  = os.environ["MIOS_AI_EMBED_MODEL"]
dsn      = os.environ["MIOS_PG_DSN"]

headers = {"Content-Type": "application/json"}
if key: headers["Authorization"] = f"Bearer {key}"

def embed(texts):
    r = httpx.post(f"{endpoint}/embeddings", headers=headers,
                   json={"model": embed_m, "input": texts}).json()
    return [d["embedding"] for d in r["data"]]

with psycopg.connect(dsn) as conn:
    register_vector(conn)
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    for i in range(0, len(rows), 64):                     # batched embedding
        batch = rows[i:i+64]
        vecs = embed([r["text"] for r in batch])
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO mios_kb (chunk_id, text, embedding) VALUES (%s,%s,%s) "
                "ON CONFLICT (chunk_id) DO UPDATE SET text=EXCLUDED.text, embedding=EXCLUDED.embedding",
                [(r["chunk_id"], r["text"], v) for r, v in zip(batch, vecs)])
        conn.commit()
        print(f"embedded {i+len(batch)}/{len(rows)}")
print("done; sanity probe:", len(embed(["healthcheck"])[0]), "dims")
```

You'll see batched embedding progress and a sanity probe (vector dimension) at
the end.

## Step 4 — Query the index from your application

The query is embedded through the **same** endpoint and embed model, then
matched against pgvector with cosine distance (`<=>`):

```python
import os, httpx, psycopg
from pgvector.psycopg import register_vector

endpoint = os.environ["MIOS_AI_ENDPOINT"]
key      = os.environ.get("MIOS_AI_KEY", "")
embed_m  = os.environ["MIOS_AI_EMBED_MODEL"]
chat_m   = os.environ["MIOS_AI_MODEL"]
dsn      = os.environ["MIOS_PG_DSN"]

headers = {"Content-Type": "application/json"}
if key: headers["Authorization"] = f"Bearer {key}"

def retrieve(query: str, k: int = 5):
    qv = httpx.post(f"{endpoint}/embeddings", headers=headers,
                    json={"model": embed_m, "input": [query]}).json()["data"][0]["embedding"]
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chunk_id, text FROM mios_kb ORDER BY embedding <=> %s LIMIT %s",
                (qv, k))
            return cur.fetchall()

def answer(query: str):
    hits = retrieve(query)
    context = "\n\n".join(f"[{cid}] {text}" for cid, text in hits)
    msgs = [
        {"role": "system",
         "content": "You are MiOS-Engineer. Cite chunk IDs (e.g. [mios-006]) when you use a passage."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]
    return httpx.post(f"{endpoint}/chat/completions", headers=headers,
                      json={"model": chat_m, "messages": msgs}).json()["choices"][0]["message"]["content"]

print(answer("Why does MiOS use lockdown=integrity not confidentiality?"))
```

## Step 5 — Run the eval against your local stack

```bash
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint "$MIOS_AI_ENDPOINT" \
  --model    "$MIOS_AI_MODEL" \
  --eval     ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset  ./var/lib/mios/evals/dataset.jsonl \
  --report   ./mios-eval-report.json
```

Pass rate < 100% indicates retrieval or model gaps to address — and because
the runner used `MIOS_AI_ENDPOINT`, those gaps are the *same* ones a live MiOS
agent would hit.

## Switching to a different local runtime

`MIOS_AI_ENDPOINT` is the only thing that moves; the pgvector store and the
recipe above are unchanged. The MiOS lanes are named by *function*, not by
upstream tool:

| Runtime | `MIOS_AI_ENDPOINT` | `MIOS_AI_MODEL` |
| --- | --- | --- |
| MiOS unified endpoint (canonical) | `http://localhost:8080/v1` | `granite4.1:8b` (mios.toml `[ai].model`) |
| `mios-llm-light` lane direct (llama.cpp via the upstream llama-swap proxy) | `http://localhost:11450/v1` | per `mios-llm-light.yaml` model map |
| `mios-llm-heavy` lane (SGLang, gated) | `http://localhost:11441/v1` | `mios-heavy` (served-name) |
| `mios-llm-heavy-alt` lane (vLLM, gated) | `http://localhost:11440/v1` | `mios-heavy` |
| vLLM (generic) | `http://localhost:8000/v1` | (per served model id) |
| SGLang (generic) | `http://localhost:30000/v1` | (per served model id) |
| LM Studio | `http://localhost:1234/v1` | (per LM Studio loaded model) |
| bare `llama.cpp` server | `http://localhost:8080/v1` | `any` (server returns its loaded model) |
| LiteLLM proxy | `http://localhost:4000/v1` | (per litellm `config.yaml`) |

> The `mios-llm-light` map (`usr/share/mios/llamacpp/mios-llm-light.yaml`)
> currently routes `qwen3.5:4b` (and other legacy role names) onto the served
> reasoning GGUF via aliases; `nomic-embed-text` runs its own `--embedding`
> `llama-server` so `/v1/embeddings` works on the same port. Heavy lanes stay
> inert until enabled and reachable (`health_gate`), so leave the default on
> the light lane unless you've explicitly brought a heavy lane up.

The rest of the recipe is unchanged. **This is the Day-0 portability
guarantee** — and it falls straight out of Law 5: one endpoint, swappable
engines, one place (pgvector) to keep what you've learned.
