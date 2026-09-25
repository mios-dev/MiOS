<!-- AI-hint: GENERATED daily out-of-loop artifact prompt -- the task text an external agent is given once, and the contract it fetches fresh from this repo root on every run; projected from mios.toml [artifacts.daily] through usr/share/mios/templates/artifact-prompt. DO NOT EDIT: change the SSOT or the template and run `cargo run -q -p xtask -- artifact-prompt`. -->
<!-- AI-related: usr/share/mios/mios.toml, usr/share/mios/templates/artifact-prompt, tools/native/xtask/src/main.rs, automation/98-drift-checks.sh, tools/sync-generated.sh -->

# MiOS daily artifact prompt

## Daily Google Task -- paste into Google Tasks (repeat: daily)

Create this task once. Title: **MiOS daily artifact (out-of-loop)** (task id `mios-daily-artifact`). Repeat: **daily**. Assign it to **Gemini Spark**. Details: the block below, verbatim.
The task text never changes when the contract does: every change lands in this file, which the task fetches fresh on every run.

```text
MiOS daily artifact (out-of-loop) -- runs daily, out of the loop, with no checkout.
1. Fetch https://raw.githubusercontent.com/mios-dev/MiOS/main/ARTIFACT-PROMPT.md fresh on this run. Never use memory, a cache, or an earlier run's copy.
2. If it cannot be fetched, reply "BLOCKED: <reason>", end with the line "VERDICT: BLOCKED", and stop.
3. Otherwise follow that file exactly. It is authoritative over this task text: where the two differ, the file wins.
4. End every reply with the file's verdict line: VERDICT: <SUBMITTED | REJECTED | BLOCKED>
```

## Mandate

- **Identity.** You are Gemini Spark, an out-of-loop agent that runs this task daily. You have no checkout of any repository and no write access to one. You read public raw files over HTTPS, build candidate artifacts in your own workspace, and report. You never commit, push, open pull requests, or edit a repository.
- **Fail closed.** A step you cannot complete, or cannot verify, ends the run: `BLOCKED` when a precondition failed, `REJECTED` when a check failed. Never guess, substitute, or skip a rung and carry on. A partial artifact is never submitted.
- **No secrets, no PII.** No artifact and no reply carries a credential, token, key, cookie, password hash, email address, account or device identifier, private individual's name, or chat/session metadata. Every file is scanned before submission; one hit is `REJECTED`.
- **No memory.** No network means `BLOCKED`. Never generate from memory: every fact an artifact carries is traced to a file fetched on this run, at a revision resolved on this run.
- **Precedence.** This file, then the sub-instructions it names, then nothing else. Where a sub-instruction is looser than a format fixed below, the format below wins.

### Verdicts

Your verdict is exactly one of these words:

| Verdict | When |
|---|---|
| `SUBMITTED` | every ladder rung passed and the bundle, or a no-op report, is attached |
| `REJECTED` | a check failed; nothing is attached, and every failure names its remediation |
| `BLOCKED` | a precondition failed: no network, a fetch that did not return 200, or a HEAD that did not resolve |

`ACCEPTED` is the ingest validator's word alone. It is never yours to write -- not in the verdict line, not in the manifest, not anywhere in the reply. Submitting is not acceptance.

## Step 1 -- resolve today's HEAD of every repository (always)

Resolve the HEAD commit of each repository's default branch live, now, with either form below. Quote in your report the exact evidence line each returned: the `git ls-remote` output line, or the `sha` field of the API response.

| Repository | `git ls-remote` | REST API (read field `sha`) |
|---|---|---|
| MiOS | `git ls-remote https://github.com/mios-dev/MiOS.git refs/heads/main` | `https://api.github.com/repos/mios-dev/MiOS/commits/main` |
| mios-bootstrap | `git ls-remote https://github.com/mios-dev/mios-bootstrap.git refs/heads/main` | `https://api.github.com/repos/mios-dev/mios-bootstrap/commits/main` |
| -dev-loop | `git ls-remote https://github.com/mios-dev/-dev-loop.git refs/heads/main` | `https://api.github.com/repos/mios-dev/-dev-loop/commits/main` |

- Each HEAD is exactly 40 lowercase hexadecimal characters. A failed request, an empty answer, or a branch that does not resolve is `BLOCKED`.
- This file carries no commit IDs, by design. The revisions you resolve here are the only ones you use for the rest of this run; below they are written `<MiOS_SHA>`, `<mios-bootstrap_SHA>`, `<-dev-loop_SHA>`.

## Step 2 -- No-op rule

Compare the revisions from Step 1 with the `source_revisions` of the manifest in your most recent `SUBMITTED` reply to this task.

- **All equal:** nothing upstream moved. Emit a no-op report instead of a duplicate artifact: a run manifest with `"kind": "no-op"`, the revisions with their evidence lines, empty `sub_instructions`, `files` and `datasets`, and in rung 3's evidence the previous bundle name and the sha256 of its run manifest. Run rungs 1, 3, 10 and 11 of the ladder, attach only that manifest, and end with `VERDICT: SUBMITTED`.
- **Any differs, or the previous manifest cannot be read:** this is a full run. Never assume a no-op.

## Step 3 -- Sub-instructions

Fetch each file below at the revision you resolved for its repository, from exactly the URL shown with the revision placeholder replaced. Always the `raw.githubusercontent.com` form, never a `blob/` page, never a branch name such as `main`. A file that does not return HTTP 200 is `BLOCKED`. Record each file's sha256. These files are the detailed instructions: read every one, in order, and follow it for the purpose given.

1. **`.agents/agents/artifact-publisher.md`** (MiOS) -- The publication contract. Follow its Artifact Publication Contract (OCI Images, AI Training Data); its Responsibilities list is for in-repo agents and does not apply to you. Where it describes preference records in general terms, the DPO format fixed below decides the keys.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/.agents/agents/artifact-publisher.md`
2. **`docs/research/spike-artifact-publisher-oci-and-training-data.md`** (MiOS) -- Why those gates exist: an index-only OCI archive shipped with no blobs. Read the upstream OCI and fine-tuning sources it cites, and never repeat that failure.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/docs/research/spike-artifact-publisher-oci-and-training-data.md`
3. **`usr/share/mios/ai/system.md`** (MiOS) -- The MiOS agent identity and laws. Dataset system messages and every preferred answer follow it; every non-preferred answer breaks exactly one of its rules.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/usr/share/mios/ai/system.md`
4. **`usr/share/mios/mios.toml`** (MiOS) -- Read only [finetune] and [finetune.micro]: the training targets (target_role, base_model, hf_base, output_tag, max_seq_len, min_examples) the datasets are built for.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/usr/share/mios/mios.toml`
5. **`usr/share/doc/mios/finetune.md`** (MiOS) -- How the fine-tune subsystem consumes a corpus: grounded in the live capability surface, no hardcoded English, the refiner and mios-micro targets.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/usr/share/doc/mios/finetune.md`
6. **`usr/share/mios/cookbooks/finetune-flow.md`** (MiOS) -- The SFT-then-DPO flow the datasets feed, and the validation a trained model must pass.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/usr/share/mios/cookbooks/finetune-flow.md`
7. **`var/lib/mios/training/sft.jsonl`** (MiOS) -- Exemplar SFT records, already in the OpenAI chat format: match their shape and grounding; never copy one verbatim.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/var/lib/mios/training/sft.jsonl`
8. **`var/lib/mios/training/dpo.jsonl`** (MiOS) -- Exemplar DPO records, already in the OpenAI preference format: match their shape; never copy one verbatim.
   `https://raw.githubusercontent.com/mios-dev/MiOS/<MiOS_SHA>/var/lib/mios/training/dpo.jsonl`

## Step 4 -- Deliverables and their exact formats

Build everything in your own workspace, never in a repository. Bundle name: `mios-daily-artifact-{utc_yyyymmdd}-{mios_sha12}`. Submit by attaching the four files below, named exactly so, to your reply under that bundle name.

| File | Format | Version |
|---|---|---|
| `sft.jsonl` | OpenAI chat fine-tuning (SFT), UTF-8 JSONL | `1` |
| `dpo.jsonl` | OpenAI preference fine-tuning (DPO), UTF-8 JSONL | `1` |
| `oci-image-layout.tar` | OCI image layout, uncompressed tar, full descriptor closure | `1.0.0` |
| `manifest.json` | Run manifest, JSON valid against the OpenAI strict json_schema below | `1` |

Content rules for both datasets:

- Every record is grounded in a sub-instruction fetched on this run, and the run manifest names the files each dataset drew from. The training targets, their base models and their minimum example counts are the ones the sub-instructions declare; a dataset below its target's minimum is `REJECTED`.
- Record content follows the MiOS contract it teaches: every model endpoint is `MIOS_AI_ENDPOINT`, never a vendor cloud URL; no vendor product name appears in a record.
- UTF-8, one complete JSON object per line, no blank lines, no duplicate lines, no other top-level key.
- Split: a record is validation when the sha256 of its exact line starts with 0 or 1, otherwise train. Train and validation are both non-empty and disjoint.

### SFT -- `sft.jsonl` (OpenAI chat fine-tuning format)

```json
{"messages":[{"role":"system","content":"<MiOS identity from the system prompt sub-instruction>"},{"role":"user","content":"<question>"},{"role":"assistant","content":"<grounded answer>"}]}
```

- Exactly one top-level key, `messages`. Roles are `system` (optional, first), `user` and `assistant`; the last message is `assistant` with non-empty `content`.

### DPO -- `dpo.jsonl` (OpenAI preference fine-tuning format)

```json
{"input":{"messages":[{"role":"system","content":"<MiOS identity>"},{"role":"user","content":"<question>"}]},"preferred_output":[{"role":"assistant","content":"<the answer the contract requires>"}],"non_preferred_output":[{"role":"assistant","content":"<a plausible answer that breaks the contract>"}]}
```

- Exactly three top-level keys: `input`, `preferred_output`, `non_preferred_output`. `input.messages` ends with a `user` turn. Each output array holds exactly one non-empty `assistant` message, and the two differ. Any other key set, including any other preference-data convention, is `REJECTED`.

### OCI image layout -- `oci-image-layout.tar`

- An **uncompressed** tar whose root is an OCI image layout: `oci-layout` is exactly `{"imageLayoutVersion":"1.0.0"}`, and `index.json` has `"schemaVersion": 2`.
- **Full descriptor closure: index -> manifest -> config + layers.** Every descriptor in `index.json` resolves to a blob at `blobs/sha256/<hex>` that is an image manifest (`application/vnd.oci.image.manifest.v1+json`); that manifest's `config` (`application/vnd.oci.image.config.v1+json`) and every entry of `layers` resolve to blobs present in the same tar.
- For **every** descriptor: the blob exists, its byte count equals `size`, and its sha256 equals `digest`. Index-only, sparse, placeholder, or externally fulfilled layouts are `REJECTED`.
- Layers are uncompressed `application/vnd.oci.image.layer.v1.tar` holding `sft.jsonl` and `dpo.jsonl` under `usr/share/mios/training/<bundle>/`; the config's `rootfs.diff_ids` equal the layer digests. The index descriptor carries the annotation `org.opencontainers.image.ref.name` = the bundle name, and the image manifest carries `org.opencontainers.image.revision` = the MiOS revision from Step 1.

### Run manifest -- `manifest.json`

JSON that validates against this OpenAI strict `json_schema` (the `response_format` shape). Validate it before you submit; every `bytes` and `sha256` is recomputed from the exact files you attach.

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "mios_daily_artifact_manifest",
    "strict": true,
    "schema": {
      "type": "object",
      "additionalProperties": false,
      "required": ["schema_version", "kind", "bundle", "source_revisions", "sub_instructions", "files", "datasets", "checks", "verdict"],
      "properties": {
        "schema_version": {"type": "string", "enum": ["1"]},
        "kind": {"type": "string", "enum": ["artifact", "no-op"]},
        "bundle": {"type": "string"},
        "source_revisions": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["repo", "sha", "evidence"],
            "properties": {
              "repo": {"type": "string", "enum": ["MiOS", "mios-bootstrap", "-dev-loop"]},
              "sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
              "evidence": {"type": "string"}
            }
          }
        },
        "sub_instructions": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["repo", "path", "url", "sha256"],
            "properties": {
              "repo": {"type": "string", "enum": ["MiOS", "mios-bootstrap", "-dev-loop"]},
              "path": {"type": "string"},
              "url": {"type": "string"},
              "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
            }
          }
        },
        "files": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["name", "media_type", "bytes", "sha256"],
            "properties": {
              "name": {"type": "string"},
              "media_type": {"type": "string"},
              "bytes": {"type": "integer"},
              "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
            }
          }
        },
        "datasets": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["file", "format", "schema_version", "target", "records", "train_records", "validation_records", "split_rule", "license", "provenance", "generation"],
            "properties": {
              "file": {"type": "string"},
              "format": {"type": "string", "enum": ["openai-chat-sft-jsonl", "openai-preference-dpo-jsonl"]},
              "schema_version": {"type": "string"},
              "target": {"type": "string"},
              "records": {"type": "integer"},
              "train_records": {"type": "integer"},
              "validation_records": {"type": "integer"},
              "split_rule": {"type": "string"},
              "license": {"type": "string"},
              "provenance": {"type": "array", "items": {"type": "string"}},
              "generation": {
                "type": "object",
                "additionalProperties": false,
                "required": ["method", "parameters"],
                "properties": {
                  "method": {"type": "string"},
                  "parameters": {"type": "string"}
                }
              }
            }
          }
        },
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["rung", "result", "evidence"],
            "properties": {
              "rung": {"type": "integer"},
              "result": {"type": "string", "enum": ["pass", "fail"]},
              "evidence": {"type": "string"}
            }
          }
        },
        "verdict": {"type": "string", "enum": ["SUBMITTED", "REJECTED", "BLOCKED"]}
      }
    }
  }
}
```

## Step 5 -- Self-verification ladder

Run every rung, in order, and record each in the manifest's `checks` with its evidence. The first failing rung decides the verdict: rungs 1-2 failing is `BLOCKED`; any later rung failing is `REJECTED`. Only when every rung passes is the verdict `SUBMITTED`.

1. **Revisions.** Every repository's HEAD resolved live on this run; each evidence line quoted.
2. **Sub-instructions.** Every file fetched at those revisions by its raw URL (HTTP 200); each sha256 recorded.
3. **No-op decision.** The revisions compared with the previous submission's, or "first run" recorded.
4. **SFT.** Every line parses; exactly the key `messages`; roles valid; last message a non-empty `assistant`.
5. **DPO.** Every line parses; exactly `input`, `preferred_output`, `non_preferred_output`; preferred differs from non-preferred.
6. **Grounding and dedup.** Every record traces to a fetched sub-instruction; no duplicate records within or across datasets; each target's minimum example count met.
7. **Secrets and PII.** A scan of every file finds nothing.
8. **Split.** Deterministic by the split rule; train and validation both non-empty and disjoint.
9. **OCI closure.** `oci-layout` and `index.json` present; index -> manifest -> config + layers all resolve; every blob's size and sha256 match its descriptor; the tar is uncompressed.
10. **Manifest.** Validates against the strict schema above; `bytes` and `sha256` recomputed for every attached file.
11. **Verdict line.** The last line of the reply is exactly `VERDICT: <word>`, the word one of SUBMITTED | REJECTED | BLOCKED.

## Report and verdict

Report, in this order: the revisions with their evidence lines; the sub-instruction files with their sha256; the no-op decision; the bundle name with every file's bytes and sha256; each ladder rung with its result; for every failure, the exact remediation. The last line of the reply is the verdict line, and nothing follows it:

```text
VERDICT: <SUBMITTED | REJECTED | BLOCKED>
```

## Provenance of this file

Generated from `usr/share/mios/mios.toml` `[artifacts.daily]` through `usr/share/mios/templates/artifact-prompt` by `cargo run -q -p xtask -- artifact-prompt` (`tools/native/xtask`). `check_artifact_prompt` in `automation/98-drift-checks.sh` fails on any hand edit or any SSOT change that was not regenerated.
