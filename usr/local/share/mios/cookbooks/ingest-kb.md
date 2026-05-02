# Cookbook: Ingest the MiOS KB into a Vector Store (OpenAI cloud)

> Full path: `/usr/local/share/mios/cookbooks/ingest-kb.md`
> See `INSTALL.md` (top-level) for the full three-recipe set; this is the
> step-by-step OpenAI-cloud variant.

## Prerequisites

- `OPENAI_API_KEY` set
- `jq`, `curl`, `python3`
- Working directory: this KB's repo root (the `proc/`, `etc/`, `usr/`, ... tree)

## Step 1 — Create a vector store

```bash
VS=$(curl -s https://api.openai.com/v1/vector_stores \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
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
  fid=$(curl -s https://api.openai.com/v1/files \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
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

vs_id = os.environ["VS_ID"]
api_key = os.environ["OPENAI_API_KEY"]
mapping = json.loads(os.environ["FILE_IDS_JSON"])

files = []
for line in open("./var/lib/mios/embeddings/vector_store.import.jsonl"):
    obj = json.loads(line)
    rel = obj["attributes"]["fhs_path"].lstrip("/")
    if rel in mapping:
        obj["file_id"] = mapping[rel]
        files.append(obj)
    else:
        print(f"WARN: no file_id for {rel} — skipping")

req = urllib.request.Request(
    f"https://api.openai.com/v1/vector_stores/{vs_id}/file_batches",
    data=json.dumps({"files": files}).encode(),
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
print(urllib.request.urlopen(req).read().decode())
PY
```

Each file is attached with its per-file `chunking_strategy` (auto for
most, smaller chunks for kargs.d and PACKAGES.md) and rich `attributes`
(`doc_type`, `mios_subsystem`, `upstream_tech`, `fhs_path`,
`kb_version`) for filtered retrieval.

## Step 4 — Query via Responses API

```bash
curl https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "$(jq --arg vs "$VS_ID" \
       '.tools[0].vector_store_ids = [$vs]' \
       ./srv/mios/api/responses.example.json)"
```

## Step 5 — Optional: create the eval

```bash
curl https://api.openai.com/v1/evals \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d @./var/lib/mios/evals/mios-knowledge.eval.json
```

## Step 6 — Optional: SFT fine-tuning

```bash
FILE_ID=$(curl -s https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose=fine-tune -F file=@./var/lib/mios/training/sft.jsonl \
  | jq -r .id)
curl https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "{\"training_file\":\"$FILE_ID\",\"model\":\"gpt-4.1-mini\"}"
```

## Step 7 — Optional: DPO after SFT

```bash
DPO=$(curl -s https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose=fine-tune -F file=@./var/lib/mios/training/dpo.jsonl \
  | jq -r .id)
# Use the SFT-tuned model as the base for DPO:
curl https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "{\"training_file\":\"$DPO\",\"model\":\"<your-sft-tuned-model-id>\",\"method\":{\"type\":\"dpo\"}}"
```
