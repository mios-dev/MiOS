# Cookbook: Ingest the MiOS KB via the OpenAI Vector Stores API shape

> Full path: `/usr/share/mios/cookbooks/ingest-kb.md`
> See `usr/share/doc/mios/guides/install.md` for the full recipe set;
> this cookbook covers the Vector-Stores-API path (Files → Vector Store
> → file_batches → Responses API).

## Prerequisites

- An OpenAI-API-compatible endpoint that implements the Vector Stores,
  Files (`purpose=assistants`), and Responses API surfaces. **MiOS
  LocalAI v3+ implements a subset; LiteLLM proxy fronting a backend that
  supports these surfaces is another option.** Architectural Law 5
  (UNIFIED-AI-REDIRECTS) forbids hardcoding any vendor-cloud URL — use
  `$MIOS_AI_ENDPOINT`.
- For pure-local Day-0 ingestion using only `/v1/embeddings` + Qdrant
  (no Vector Stores API needed), see
  `usr/share/mios/cookbooks/local-rag-day0.md` instead.
- `jq`, `curl`, `python3`
- Working directory: this KB's repo root (the `proc/`, `etc/`, `usr/`,
  ... tree)

## Step 0 — Set the unified env

```bash
export MIOS_AI_ENDPOINT=${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}
export MIOS_AI_KEY=${MIOS_AI_KEY:-}    # empty key accepted by LocalAI
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
`kb_version`) for filtered retrieval.

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
`/v1/chat/completions` endpoint.

## Step 6 — Optional: SFT fine-tuning

The Fine-Tuning Jobs API path is documented for endpoints that support
it (`POST /v1/files` with `purpose=fine-tune`, then
`POST /v1/fine_tuning/jobs`). Most local OpenAI-API runtimes do not
implement these surfaces — see
`usr/share/mios/cookbooks/finetune-flow.md` for the local trainer paths
(axolotl / trl / MLX-LM / unsloth).
