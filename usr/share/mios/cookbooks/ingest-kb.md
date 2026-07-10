<!-- AI-hint: Instructional cookbook for ingesting the MiOS knowledge base through the OpenAI-compatible Vector Stores API surface (Files -> Vector Store -> file_batches -> Responses API), against the unified MIOS_AI_ENDPOINT served by the mios-llm-light inference lane; covers creating a vector store, uploading docs as Files, attaching with chunking + attributes, querying, and optional eval/SFT.
     AI-related: /usr/share/mios/cookbooks/ingest-kb.md, /usr/share/mios/cookbooks/local-rag-day0.md, /usr/share/mios/cookbooks/finetune-flow.md, /usr/share/mios/api/responses.example.json, /var/lib/mios/embeddings/vector_store.import.jsonl, /var/lib/mios/evals/mios-knowledge.eval.json, mios-llm-light, mios-pgvector, MIOS_AI_ENDPOINT -->
# Cookbook: Ingest the MiOS KB via the OpenAI Vector Stores API shape

> Full path: `/usr/share/mios/cookbooks/ingest-kb.md`
> See `usr/share/doc/mios/guides/install.md` for the full recipe set;
> this cookbook covers the Vector-Stores-API path (Files → Vector Store
> → file_batches → Responses API).

## Why this cookbook exists (its place in the whole)

MiOS is one system built two ways at once: an immutable, bootc/OCI-shaped
Fedora workstation *and* a local, self-hosted agentic AI OS. The AI half runs
entirely on your hardware behind a single OpenAI-compatible endpoint
(`MIOS_AI_ENDPOINT`): the **agent-pipe**
orchestrator and **MiOS-Hermes** gateway reason over requests, while the
**`mios-llm-light`** inference lane (`:11450`) does the generation **and** the
embeddings (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`), and
**PostgreSQL + pgvector** (`mios-pgvector`, `:5432`) holds the unified agent
memory.

This cookbook serves that whole by making the OS's own documentation
*retrievable*: it ingests the MiOS KB (this repo's `usr/share/doc/mios/` tree)
into a vector store through the OpenAI **Vector Stores / Files / Responses**
API shape, so any OpenAI-API-compatible client can ground answers in the exact
docs that describe the running system. Because the KB lives inside the same
rebuildable OCI image as everything else, what you ingest here matches, byte
for byte, what every box on the same image ships — the self-describing,
self-replicating property is what makes the agent stack trustworthy.

> **Two ingest paths, one endpoint.** If your runtime does not expose the
> Vector Stores API, use the pure-local path instead: `/v1/embeddings`
> (served by `mios-llm-light`) into **pgvector** — see
> `usr/share/mios/cookbooks/local-rag-day0.md`. Both paths target the same
> `MIOS_AI_ENDPOINT`; this one buys you server-side chunking, attribute
> filtering, and the Responses file-search tool.

## Prerequisites

- An OpenAI-API-compatible endpoint that implements the **Vector Stores**,
  **Files** (`purpose=assistants`), and **Responses** API surfaces. On MiOS the
  unified endpoint (`MIOS_AI_ENDPOINT`) is
  fronted by the agent stack over the `mios-llm-light` lane (`:11450`) —
  whether these higher-level surfaces are available depends on the runtime in
  front of it. A LiteLLM proxy (or any gateway) that fronts a backend
  implementing these surfaces is the portable option. Architectural Law 5
  (UNIFIED-AI-REDIRECTS) forbids hardcoding any vendor-cloud URL — always
  resolve `$MIOS_AI_ENDPOINT`.
- `jq`, `curl`, `python3`
- Working directory: this KB's repo root (the `usr/`, `etc/`, `srv/`, `var/`,
  ... tree — the repo root *is* the deployed system root).

## Step 0 — Set the unified env

```bash
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8642/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}    # empty key accepted locally
```

## Step 1 — Create a vector store

```bash
VS=$(curl -s "$MIOS_AI_ENDPOINT/vector_stores" \
  -H "Authorization: Bearer $MIOS_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"mios-kb","metadata":{"kb_version":"2026.05.02"}}' \
  | jq -r .id)
echo "VS_ID=$VS"
export VS_ID="$VS"
```

## Step 2 — Upload every doc as a File

```bash
declare -A FILE_IDS
while IFS= read -r f; do
  fid=$(curl -s "$MIOS_AI_ENDPOINT/files" \
    -H "Authorization: Bearer $MIOS_AI_KEY" \
    -F purpose=assistants \
    -F file=@"$f" | jq -r .id)
  rel="${f#./}"
  FILE_IDS["$rel"]="$fid"
  echo "$rel -> $fid"
done < <(find ./usr/share/doc/mios -name '*.md' -type f)

# Persist for step 3
python3 -c "import json,sys; d={k.lstrip('/'): v for k,v in dict([line.split(' -> ',1) for line in sys.stdin if ' -> ' in line]).items()}; print(json.dumps(d))" \
  > /tmp/mios-file-ids.json < <(for k in "${!FILE_IDS[@]}"; do echo "$k -> ${FILE_IDS[$k]}"; done)
export FILE_IDS_JSON="$(cat /tmp/mios-file-ids.json)"
```

## Step 3 — Attach with attributes + chunking strategy

```bash
python3 - <<'PY'
import json, os, urllib.request

vs_id    = os.environ["VS_ID"]
endpoint = os.environ["MIOS_AI_ENDPOINT"].rstrip("/")
api_key  = os.environ.get("MIOS_AI_KEY", "")
mapping  = json.loads(os.environ["FILE_IDS_JSON"])

files = []
for line in open("./var/lib/mios/embeddings/vector_store.import.jsonl"):
    obj = json.loads(line)
    rel = obj["attributes"]["fhs_path"].lstrip("/")
    if rel in mapping:
        obj["file_id"] = mapping[rel]
        files.append(obj)
    else:
        print(f"WARN: no file_id for {rel} — skipping")

headers = {"Content-Type": "application/json"}
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

req = urllib.request.Request(
    f"{endpoint}/vector_stores/{vs_id}/file_batches",
    data=json.dumps({"files": files}).encode(),
    headers=headers)
print(urllib.request.urlopen(req).read().decode())
PY
```

Each file is attached with its per-file `chunking_strategy` (auto for
most, smaller chunks for kargs.d and PACKAGES.md) and rich `attributes`
(`doc_type`, `mios_subsystem`, `upstream_tech`, `fhs_path`,
`kb_version`) for filtered retrieval. The chunk embeddings are produced by the
same `nomic-embed-text` model `mios-llm-light` serves to the rest of the agent
stack, so retrieval here is dimension- and model-consistent with the live
pgvector knowledge recall.

## Step 4 — Query via Responses API

```bash
curl "$MIOS_AI_ENDPOINT/responses" \
  -H "Authorization: Bearer $MIOS_AI_KEY" -H "Content-Type: application/json" \
  -d "$(jq --arg vs "$VS_ID" \
       '.tools[0].vector_store_ids = [$vs]' \
       ./usr/share/mios/api/responses.example.json)"
```

## Step 5 — Optional: create the eval

```bash
curl "$MIOS_AI_ENDPOINT/evals" \
  -H "Authorization: Bearer $MIOS_AI_KEY" -H "Content-Type: application/json" \
  -d @./var/lib/mios/evals/mios-knowledge.eval.json
```

Note: the local Evals API surface depends on the runtime. If
`$MIOS_AI_ENDPOINT` doesn't implement `/v1/evals`, run
`./var/lib/mios/evals/mios-knowledge.local-runner.py` instead — it
implements the same grader logic against any
`/v1/chat/completions` endpoint (i.e. directly against `mios-llm-light`).

## Step 6 — Optional: SFT fine-tuning

The Fine-Tuning Jobs API path is documented for endpoints that support
it (`POST /v1/files` with `purpose=fine-tune`, then
`POST /v1/fine_tuning/jobs`). Most local OpenAI-API runtimes do not
implement these surfaces — see
`usr/share/mios/cookbooks/finetune-flow.md` for the local trainer paths
(axolotl / trl / MLX-LM / unsloth).
