<!-- AI-hint: Documentation for the MiOS Fine-Tune subsystem, detailing the operator-gated pipeline that distils a strong local teacher model into a small, hardware-agnostic MiOS role model via LoRA/SFT, baking system behaviours (routing discipline, anti-fabrication) into the weights of the agent-pipe refiner instead of carrying them in long injected prompts.
     AI-related: /usr/share/mios/finetune/requirements.txt, /usr/share/mios/mios.toml, /etc/mios/mios.toml, /usr/libexec/mios/mios-finetune-serve, mios-finetune-serve, mios-sys-agent, mios-finetune-dataset, mios-finetune, mios-agent-pipe, mios-agent-pipe.service, mios-llm-light -->
# MiOS Fine-Tune Subsystem

## Purpose — where this fits in MiOS

MiOS is one thing built two ways: an immutable bootc/OCI Fedora workstation that
is also a **local, self-replicating, agentic AI operating system**. The agent
plane behind that single OpenAI-compatible endpoint (`MIOS_AI_ENDPOINT`) routes
every request through the **agent-pipe** orchestrator, which begins each turn
with a fast **refine** pass — the small model (`mios-sys-agent`) that reads the
user's text plus the live verb catalog and emits the refined-intent JSON the
whole council/swarm dispatch then acts on. The refiner is the narrow waist of
the AI plane: get its routing right and everything downstream behaves.

That routing discipline — picking the right verb names, choosing local-vs-web,
refusing to fabricate — is carried **today by long injected prompts**. The
fine-tune subsystem exists to **bake that behaviour into the refiner's weights**
by distilling a much stronger *locally-served* teacher into the small fast model.
The win is quality and robustness without putting a bigger model on the hot path,
and without ever leaving the box: it is FOSS, fully offline after a one-time
framework fetch, and **hardware-agnostic** — it trains on whatever compute the
host has (NVIDIA CUDA / AMD ROCm / Apple MPS / CPU), the same way MiOS serves
inference on whatever lane is available.

Because MiOS is one rebuildable image, this is how the system improves *itself*:
the refiner that drives the agent plane is retrained from the agent plane's own
live capability surface, then served back into the same pipeline.

This is an **operator-gated heavy build**. It saturates a GPU for a while and its
framework install needs a one-time network fetch, so it is deliberately **not** an
agent verb: no chat turn can start a multi-hour training run. It lives outside the
hot path entirely and only ever competes for resources when the operator runs it.

## Target

First (and currently the only configured) target is the **refiner**:
`target_role = "refiner"`, which is the `mios-sys-agent` role. Its base is
`base_model = "granite4.1:8b"` (the 2026-06-13 fleet modernization repointed the
refiner base to IBM Granite 4.1 8B — the new light brain — from the earlier
`qwen3.5:4b`; the base must match the role's Modelfile `FROM`). The corresponding
HF weights are `hf_base = "ibm-granite/granite-4.1-8b"`
(Apache-2.0, public). The trained adapter ships under
`output_tag = "mios-sys-agent-ft"`. All of these are SSOT knobs in
`mios.toml [finetune]`, overridable per-install via the `/etc/mios/` and
`~/.config/mios/` layers and the `MIOS_FINETUNE_*` env.

## Pieces

| Component | Role |
|---|---|
| `mios.toml [finetune]` | SSOT for every knob (target_role, base, hf_base, teacher, LoRA, SFT, device, GGUF export). |
| `mios-finetune-dataset` | Builds the SFT corpus by **self-distillation** (no hardcoded English). |
| `mios-finetune` | Hardware-agnostic LoRA/SFT → trained adapter (+ optional GGUF export). |
| `mios-finetune-serve` | Standalone helper that serves base+adapter on any hardware (OpenAI + Ollama-compatible shapes). |
| `finetune/requirements.txt` | One-time framework install (pick the torch wheel for your hardware). |

## No hardcoded English

The corpus is grounded in the **live system surface**, never a hand-written topic
list — the same no-hardcode discipline that governs the rest of MiOS:

1. The verb catalog (name + description) is pulled from the running agent-pipe
   (`/v1/verbs/openai-tools` at `[finetune].pipe_url`, `http://127.0.0.1:8640`).
   The catalog tracks the real install, so the example count tracks whatever is
   actually wired (on the developer's box this is on the order of ~60 verbs).
2. For each capability, the **teacher** writes N diverse realistic user requests
   (`seeds_per_capability`, default 4).
3. The teacher also writes queries for the non-dispatch intent classes (chat,
   web/world, broad multi_task), seeded by the schema's *own* definitions.
4. Optionally (`include_knowledge = true`), **real** operator queries are mined
   from the PostgreSQL+pgvector `knowledge` table.
5. Each query is labelled by the teacher against the live refine schema + catalog
   → a refined-intent JSON matching exactly what the pipe parses.

So the dataset tracks the real install; the model writes all the English.

### The teacher is a locally-served model

`teacher_model = "granite4.1:8b"`, served by **`mios-llm-light`** — the primary
local inference lane (llama.cpp behind the `mios-llm-light` proxy image) at
`teacher_endpoint = "http://localhost:11450"`. The teacher must be a *served*
model that is stronger than the student: pointing it at an unserved tag (e.g.
`granite4.1:8b/9b`, which `mios-llm-light` does not serve) 404s the teacher and
starves dataset generation. The student's base (`granite4.1:8b`) stays below the
teacher in capability — that gap is the point of distillation.

## One-time setup (needs network — operator's call)

```bash
# 1) framework (FOSS). Install the torch wheel matching THIS box first:
python3 -m venv /var/lib/mios/finetune/venv
. /var/lib/mios/finetune/venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # or rocm6.1 / cpu / default(MPS)
pip install -r /usr/share/mios/finetune/requirements.txt
# CUDA only, optional: pip install bitsandbytes unsloth

# 2) HF base weights for the SAME base (PEFT/TRL train on HF weights; the GGUF
#    export path stores in the GGUF/Ollama-compatible format).
#    Set finetune.hf_base in /etc/mios/mios.toml to the HF repo id or a local dir.
#    Match base_model exactly (granite4.1:8b -> ibm-granite/granite-4.1-8b).

# 3) GGUF export (optional, [finetune].gguf_convert) needs llama.cpp's
#    convert_lora_to_gguf.py on PATH (or set MIOS_FINETUNE_LORA_CONVERT).
#    Clone github.com/ggml-org/llama.cpp.
```

## Run (local, offline)

```bash
mios-finetune-dataset                 # full corpus -> [finetune].dataset_path
mios-finetune-dataset --limit 2       # fast smoke check (2 verbs + 1 intent class)

mios-finetune --dry-run               # validate device/deps/dataset/hf_base; no GPU work
mios-finetune                         # train -> LoRA adapter (+ adapter.gguf for later)
mios-finetune-serve                   # serve base+adapter (OpenAI + Ollama shapes) -- see below
```

`--dry-run` reports the detected device, whether 4-bit applies, missing deps, and
whether the dataset + hf_base are ready — without touching the GPU. `mios-finetune`
refuses to train on a corpus smaller than `min_examples` (default 24).

## Serving + adopting the fine-tuned model

The trained **adapter** (base + PEFT) is the clean, portable artifact — it runs
correctly anywhere `transformers` runs. Serve it with the helper:

```bash
# starts an endpoint on [finetune].serve_port (default 11438) that speaks BOTH the
# OpenAI-compatible and the Ollama-native wire shapes MiOS uses:
MIOS_FINETUNE_SERVE_PORT=11438 /var/lib/mios/finetune/venv/bin/python \
    /usr/libexec/mios/mios-finetune-serve
#   POST /api/chat              (Ollama-compatible -- the shape the agent-pipe refiner calls)
#   POST /v1/chat/completions , GET /v1/models , GET /healthz
```

To **A/B-test it as the refiner**, point the pipe's refine endpoint at the helper
(`MIOS_REFINE_ENDPOINT=http://127.0.0.1:11438`, model `[finetune].output_tag`) and
restart `mios-agent-pipe.service`. **Always pass the full refine system prompt (the
live verb catalog)** — the model grounds tool names against it; without it the
model invents names. The adapter served via `transformers` is correct but slower
on the hot path than the primary `mios-llm-light` lane, so this helper is for
*evaluation*: it is **opt-in**, not auto-enabled, and never competes with live MiOS
inference unless you start it. Switch production to the adapter once the GGUF path
below matures and the same adapter can run fast on the official base GGUF served by
`mios-llm-light`.

> **GGUF / Ollama-compatible export path** (`mios-finetune` also writes
> `adapter.gguf` when `gguf_convert = true`): currently blocked upstream. The
> GGUF loader for this architecture reports *"loras are not yet implemented"*, and
> a merged-GGUF needs `--no-mtp` to load but still hits converter-fidelity gaps.
> The artifact is kept ready under `work_dir` for when the upstream
> GGUF/Ollama-compatible runtime matures. (Note: Ollama is no longer a MiOS
> backend — it was retired in the WS-10 conversion to `mios-llm-light`/llama.cpp;
> "Ollama-compatible" here refers only to the wire format and GGUF tooling, which
> remain legitimate upstream references.)

## Hardware-agnostic behaviour

| Hardware | Path |
|---|---|
| NVIDIA CUDA | 4-bit QLoRA (bitsandbytes) when present, else bf16 LoRA; optional Unsloth fast-path. |
| AMD ROCm | bf16/fp16 LoRA (torch+ROCm); 4-bit only if bitsandbytes is present. |
| Apple MPS | fp16 LoRA on unified memory. |
| CPU-only | fp32 LoRA — works everywhere; slow (a fallback, not a goal). |

Device is `auto` by default (`[finetune].device`); 4-bit is `auto`
(`load_in_4bit`, enabled only on CUDA+bitsandbytes where it actually works);
`prefer_unsloth` uses the Unsloth fast-path when CUDA + unsloth are present.

## Verified run + Qwen3-Next notes (2026-05-26, historical)

The full pipeline was run end-to-end on the developer's dGPU against the real base
`Qwen/Qwen3.5-2B` (the refiner base at the time; production has since moved to
`granite4.1:8b`) — which is the **Qwen3-Next** architecture (Gated DeltaNet +
gated-attention, multimodal), not a standard dense transformer. Practical
findings, kept as a record because they shaped the current knobs:

- **torch on Python 3.14**: the pytorch.org CUDA index had no `cp314` wheels, but
  the **default PyPI** `torch` wheel did and bundled CUDA — `pip install torch`
  (no `--index-url`) gave a working CUDA build there.
- **Gradient checkpointing crashed this arch's backward** (`CUDA error: unknown
  error` on the first `loss.backward`). Set `grad_checkpointing = false` if a
  custom-op base breaks in backward; the knob exists for exactly this.
- **LoRA targets must be introspected** — the arch uses DeltaNet
  `in_proj_*`/`out_proj` names a hardcoded `q_proj,…` list misses.
  `target_modules = "auto"` handles it.
- **Result**: a real trained adapter that, loaded as base+PEFT in `transformers`,
  produced correct refined JSON (local_state, chat-vs-agent, real verbs).
  **Deployable via transformers/PEFT/vLLM.**
- **GGUF/Ollama-compatible deployment was blocked upstream** (Qwen3-Next was very
  new): the loader reported *"loras are not yet implemented"* for the adapter
  path, and the merged-model GGUF (q8 and f16) was rejected by the `qwen3next`
  loader (*"layer N missing attn_qkv/attn_gate"*). The adapter + merged-f16 GGUF
  are kept under `work_dir` for when upstream gains Qwen3-Next LoRA / merged-GGUF
  support.

## Known follow-ons

- **Label validation pass**: drop/repair examples whose `tool`/`hint_tools` aren't
  in the live catalog, or whose `intent` conflicts with the emitted `tool` (the
  teacher occasionally tags a single concrete launch `agent` instead of
  `dispatch`). Raises corpus quality before training.
- **Single-source the refine prompt**: today the dataset's label system prompt
  mirrors `_REFINE_SYSTEM_LITE`; extracting that constant into a shared module
  consumed by both the pipe and the generator removes the drift risk.
- **Extend beyond the refiner**: the same pipeline targets the other role models
  (`target_role`), distilling each from the strongest *locally-served* teacher
  that fits — extending the self-improvement loop across the whole agent plane.
