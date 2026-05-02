# MiOS Knowledge Base — OpenAI-API-Native, FHS-Compliant, Day-0 Local-Compatible

This is the combined v1+v2 deliverable: a drop-in knowledge base for the MiOS
Linux distribution (`github.com/mios-dev/MiOS`) authored to current OpenAI
Platform specifications and laid out in Linux-FHS-3.0-compliant directories.

Every artifact is **copy-paste-ready** at its prescribed path; the top-level
`proc/mios/manifest.json` enumerates every file with path, purpose, format,
and target endpoint, so an automation pipeline can iterate the manifest and
POST each file to the correct endpoint with no human translation.

## What changed v1 → v2

The v1 chunks were written before `github.com/mios-dev/MiOS` was directly
fetchable. v2 is fully repo-grounded — content under `usr/share/doc/mios/`
now reflects the actual `Containerfile`, `Justfile`, `INDEX.md`,
`ARCHITECTURE.md`, `ENGINEERING.md`, `SECURITY.md`, `SELF-BUILD.md`,
`DEPLOY.md`, `CLAUDE.md`, `AGENTS.md`, `llms.txt`. Notable corrections:

- Repo root **is** the system root (`usr/`, `etc/`, `home/`, `srv/`, `v1/`).
  No `system_files/` directory.
- Containerfile is single-stage with a `ctx` scratch context. Not the
  fabricated four-stage pipeline.
- Linux orchestrator is `Justfile` (not `cloud-ws.ps1`); Windows is
  `mios-build-local.ps1`.
- Phase scripts: ~48 in `automation/[0-9][0-9]-*.sh` (not 01-39).
- `PACKAGES.md` lives at `usr/share/mios/PACKAGES.md` and uses fenced
  ` ```packages-<category>` blocks — not a column table.
- `lockdown=integrity`, not `confidentiality`. `init_on_alloc=1`,
  `init_on_free=1`, `page_alloc.shuffle=1` are **disabled** in MiOS due to
  NVIDIA/CUDA incompatibility.
- Six Architectural Laws (USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES,
  BOOTC-CONTAINER-LINT, UNIFIED-AI-REDIRECTS, UNPRIVILEGED-QUADLETS).
- Local AI surface: LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`
  serving `http://localhost:8080/v1` (LAW 5).

## Day-0 local-model compatibility

This KB is designed to work against **any** OpenAI-API-compatible runtime
without modification. The MiOS host's own LocalAI endpoint at
`http://localhost:8080/v1` is the canonical local target — the same endpoint
MiOS's own system agents use, satisfying LAW 5 (UNIFIED-AI-REDIRECTS).

Compatible runtimes verified:

| Runtime | `/v1/chat/completions` | `/v1/embeddings` | tools | strict mode | Vector Stores | Responses API | Batch | Evals | Fine-tuning |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| OpenAI cloud | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Azure OpenAI | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ region | ✅ | ✅ | ✅ |
| MiOS LocalAI | ✅ | ✅ | ✅ | ⚠️ ignored | ❌ | ❌ | ❌ | ❌ | ❌ |
| Ollama | ✅ | ✅ | ✅ | ⚠️ ignored | ❌ | ❌ | ❌ | ❌ | external |
| vLLM | ✅ | ✅ | ✅ | ✅ via xgrammar | ❌ | partial | ❌ | ❌ | external |
| LM Studio | ✅ | ✅ | ✅ | ⚠️ ignored | ❌ | ❌ | ❌ | ❌ | ❌ |
| llama.cpp server | ✅ | ✅ | ✅ via grammars | ⚠️ ignored | ❌ | ❌ | ❌ | ❌ | external |
| LiteLLM | ✅ | ✅ | ✅ | ✅ proxied | proxied | translates | proxied | proxied | proxied |
| OpenRouter | ✅ | partial | ✅ | per-model | ❌ | ❌ | ❌ | ❌ | ❌ |

`⚠️ ignored` means the server accepts `strict: true` as an unknown field and
proceeds without enforcement — the schema is still useful as documentation
to the model but the runtime does not reject malformed JSON.

How this KB handles the gaps:

- **Tool schemas** are shipped in BOTH formats:
  `usr/lib/mios/tools/responses-api/*.json` (OpenAI cloud, flat) and
  `usr/lib/mios/tools/chat-completions-api/*.json` (universal,
  `{type:function,function:{...}}`).
- **Sample API payloads** are shipped for both:
  `srv/mios/api/responses.example.json` (cloud-only) and
  `srv/mios/api/chat.example.json` and `chat.local.example.json` (universal,
  the latter targeting `http://localhost:8080/v1`).
- **RAG** is shipped as both `var/lib/mios/embeddings/vector_store.import.jsonl`
  (OpenAI Vector Stores) and `var/lib/mios/embeddings/chunks.jsonl` (universal,
  feed any vector DB — pgvector, Qdrant, Chroma, Weaviate, Milvus).
- **Evals** are shipped as both `var/lib/mios/evals/mios-knowledge.eval.json`
  (OpenAI Evals API) and a Python local-runner that calls
  `/v1/chat/completions` against any endpoint.
- **Fine-tuning** datasets are JSONL — universally consumable by the OpenAI
  fine-tuning API, axolotl, trl, llama-factory, MLX-LM, unsloth.

See `INSTALL.md` for the full ingestion recipes.

## Top-level files

| File | Purpose |
|---|---|
| `README.md` | This file. |
| `SOURCES.md` | All references — every OpenAI API doc URL, every MiOS repo file, every upstream project, plus sub-knowledge for further iteration. |
| `INSTALL.md` | End-to-end ingestion recipes for OpenAI cloud and self-hosted local stacks. |

## FHS layout

```
proc/mios/manifest.json                      # KB index (synthetic /proc surface)
etc/mios/
  kb.conf.toml                              # KB-wide config
  eval-criteria.json                        # default grader rubric
  system-prompts/
    mios-engineer.md                        # primary system prompt
    mios-reviewer.md                        # PR review prompt
    mios-troubleshoot.md                    # troubleshooting prompt
usr/share/doc/mios/                         # primary subsystem docs
  00-overview.md                            # MiOS overview
  10-build-pipeline.md                      # Containerfile + automation/
  20-packages-md.md                         # PACKAGES.md SSOT
  30-overlay.md                             # repo-root-as-system-root
  40-kargs.md                               # kargs.d format and content
  50-orchestrators.md                       # Justfile + mios-build-local.ps1
  60-ci-signing.md                          # cosign keyless + SBOM
  70-ai-surface.md                          # LocalAI Quadlet, LAW 5
  80-security.md                            # SELinux, firewalld, CrowdSec, fapolicyd
  90-deploy.md                              # bootc + BIB
  upstream/                                 # upstream tech deep dives
    bootc.md ostree.md composefs.md ucore-hci.md fedora-bootc.md
    dnf5.md podman.md bib.md cosign.md ghcr.md nvidia.md
    localai.md cdi.md looking-glass-kvmfr.md rechunk.md
    secureblue.md greenboot.md crowdsec-fapolicyd-usbguard.md
    selinux.md k3s-cockpit.md deploy-targets.md related-distros.md
usr/lib/mios/
  tools/responses-api/                      # OpenAI Responses (flat) format
  tools/chat-completions-api/               # universal Chat Completions format
  schemas/                                  # structured-output JSON Schemas
var/lib/mios/
  embeddings/
    vector_store.import.jsonl               # OpenAI Vector Stores payload
    chunks.jsonl                            # universal RAG chunks
  training/
    sft.jsonl                               # SFT dataset
    dpo.jsonl                               # DPO dataset
  evals/
    mios-knowledge.eval.json                # OpenAI Evals API definition
    mios-knowledge.local-runner.py          # universal /v1/chat/completions runner
srv/mios/api/
  responses.example.json                    # OpenAI Responses payload
  chat.example.json                         # universal Chat Completions
  chat.local.example.json                   # MiOS-localhost-targeted
  batch.requests.jsonl                      # Batch API input
  mcp.tool.json                             # MCP tool snippet
  embeddings.example.json                   # /v1/embeddings request
opt/mios/prompts/                           # XML-structured prompt templates
usr/local/share/mios/cookbooks/             # end-to-end recipes
```

## Refresh contract

When the upstream MiOS repo changes, regenerate the KB by running the
`mios_build_kb_refresh` tool (defined in
`usr/lib/mios/tools/responses-api/mios_build_kb_refresh.json`). It re-scrapes
the repo at a given `git_ref`, regenerates `chunks.jsonl` and
`vector_store.import.jsonl`, and updates `var/lib/mios/training/sft.jsonl`.
