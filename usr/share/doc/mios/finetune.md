<!-- AI-hint: Documentation for the MiOS Fine-Tune subsystem, detailing the pipeline to distill a large teacher model into a small, hardware-agnostic role model via LoRA/SFT to bake system behaviors into weights.
     AI-related: /usr/share/mios/finetune/requirements.txt, /etc/mios/mios.toml, /usr/libexec/mios/mios-finetune-serve, mios-finetune-serve, mios-sys-agent, mios-finetune-dataset, mios-finetune, mios-agent-pipe, mios-agent-pipe.service -->
# MiOS Fine-Tune Subsystem

Distil a strong **local** teacher model into a small, fast MiOS **role model** via
LoRA/SFT, then ship the result as an ollama model. FOSS, fully offline after a
one-time framework fetch, and **hardware-agnostic** — it trains on whatever compute
the box has (NVIDIA CUDA / AMD ROCm / Apple MPS / CPU), the same way MiOS runs
inference on any lane.

This is an **operator-gated heavy build**. It is deliberately **not** an agent verb:
no chat turn can start a multi-hour training run.

## Why

The role models' behaviour (routing discipline, real verb names, local-vs-web,
anti-fabrication) is carried today by long injected prompts. Fine-tuning bakes that
behaviour into the *weights* of the small fast model by distilling a much stronger
local teacher — improving quality and robustness without a bigger model on the hot
path. First target: the **refiner** (`mios-sys-agent`, base `qwen3.5:2b`), which
drives all downstream routing.

## Pieces

| Component | Role |
|---|---|
| `mios.toml [finetune]` | SSOT for every knob (base, teacher, LoRA, SFT, device, GGUF). |
| `mios-finetune-dataset` | Builds the SFT corpus by **self-distillation** (no hardcoded English). |
| `mios-finetune` | Hardware-agnostic LoRA/SFT → GGUF → ollama model. |
| `finetune/requirements.txt` | One-time framework install (pick the torch wheel for your hardware). |

## No hardcoded English

The corpus is grounded in the **live system surface**, never a hand-written topic
list:

1. The verb catalog (name + description) is pulled from the running pipe
   (`/v1/verbs/openai-tools`) — 61 verbs today.
2. For each capability, the **teacher** writes N diverse realistic user requests.
3. The teacher also writes queries for the non-dispatch intent classes (chat,
   web/world, broad multi_task), seeded by the schema's *own* definitions.
4. Optionally, **real** operator queries are mined from the knowledge table.
5. Each query is labelled by the teacher against the live refine schema + catalog →
   a refined-intent JSON matching exactly what the pipe parses.

So the dataset tracks the real install; the model writes all the English.

## One-time setup (needs network — operator's call)

```bash
# 1) framework (FOSS). Install the torch wheel matching THIS box first:
python3 -m venv /var/lib/mios/finetune/venv
. /var/lib/mios/finetune/venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # or rocm6.1 / cpu / default(MPS)
pip install -r /usr/share/mios/finetune/requirements.txt
# CUDA only, optional: pip install bitsandbytes unsloth

# 2) HF base weights for the SAME base (PEFT/TRL train on HF, ollama stores GGUF).
#    Set finetune.hf_base in /etc/mios/mios.toml to the HF repo id or a local dir.
#    Match base_model exactly (qwen3.5:2b -> the corresponding Qwen HF repo).

# 3) GGUF export -> ollama ADAPTER needs llama.cpp's convert_lora_to_gguf.py on
#    PATH (or set MIOS_FINETUNE_LORA_CONVERT). Clone github.com/ggml-org/llama.cpp.
```

## Run (local, offline)

```bash
mios-finetune-dataset                 # full corpus -> [finetune].dataset_path
mios-finetune-dataset --limit 2       # fast smoke check (2 verbs + 1 intent class)

mios-finetune --dry-run               # validate device/deps/dataset/hf_base; no GPU work
mios-finetune                         # train -> LoRA adapter (+ adapter.gguf for later)
mios-finetune-serve                   # serve base+adapter (OpenAI + ollama shapes) -- see below
```

`--dry-run` reports the detected device, whether 4-bit applies, missing deps, and
whether the dataset + hf_base are ready — without touching the GPU.

## Serving + adopting the fine-tuned model

Today the trained **adapter** (base + PEFT) is the clean, portable artifact — it runs
correctly anywhere transformers runs. Serve it with the helper:

```bash
# starts an OpenAI- AND ollama-shaped endpoint on [finetune].serve_port (default 11438)
MIOS_FINETUNE_SERVE_PORT=11438 /var/lib/mios/finetune/venv/bin/python \
    /usr/libexec/mios/mios-finetune-serve
#   POST /api/chat   (ollama-native -- what the agent-pipe refiner calls)
#   POST /v1/chat/completions , GET /v1/models , GET /healthz
```

To **A/B-test it as the refiner**: point the pipe's refine endpoint at the helper
(`MIOS_REFINE_ENDPOINT=http://127.0.0.1:11438`, model `[finetune].output_tag`) and
restart `mios-agent-pipe.service`. **Always pass the full refine system prompt (the
61-verb catalog)** — the model grounds tool names against it; without it the model
invents names. The 2B served via transformers is correct but slower than ollama, so use
this to evaluate now and switch production once ollama gains Qwen3-Next LoRA (then the
same adapter runs fast on the official base GGUF — see below). The helper is **opt-in**:
not auto-enabled, so it never competes with live MiOS inference unless you start it.

> ollama path (`mios-finetune` also writes `adapter.gguf`): currently blocked — ollama's
> `qwen3next` runtime reports "loras are not yet implemented", and a merged-GGUF needs
> `--no-mtp` to load but still hits converter-fidelity gaps. Kept ready for when upstream
> matures.

## Hardware-agnostic behaviour

| Hardware | Path |
|---|---|
| NVIDIA CUDA | 4-bit QLoRA (bitsandbytes) when present, else bf16 LoRA; optional Unsloth fast-path. |
| AMD ROCm | bf16/fp16 LoRA (torch+ROCm); 4-bit only if bitsandbytes is present. |
| Apple MPS | fp16 LoRA on unified memory. |
| CPU-only | fp32 LoRA — works everywhere; slow (a fallback, not a goal). |

Device is `auto` by default (`[finetune].device`); 4-bit is `auto` (enabled only
where it actually works).

## Verified run + Qwen3-Next notes (2026-05-26)

The full pipeline was run end-to-end on the 4090 against the real base
`Qwen/Qwen3.5-2B` — which is the **Qwen3-Next** architecture (Gated DeltaNet +
gated-attention, multimodal), not a standard dense transformer. Practical findings:

- **torch on Python 3.14**: the pytorch.org CUDA index has no `cp314` wheels, but
  the **default PyPI** `torch` wheel does and bundles CUDA — `pip install torch`
  (no `--index-url`) gives a working CUDA build here.
- **Gradient checkpointing crashes this arch's backward** (`CUDA error: unknown error`
  on the first `loss.backward`). Set `grad_checkpointing = false` (the run did; 2B fits
  bf16 without it). Knob added for exactly this.
- **LoRA targets must be introspected** — the arch uses DeltaNet `in_proj_*`/`out_proj`
  names a hardcoded `q_proj,…` list misses. `target_modules = "auto"` handles it.
- **Result**: a real trained adapter that, loaded as base+PEFT in transformers,
  produces correct refined JSON (local_state, chat-vs-agent, real verbs). **Deployable
  today via transformers/PEFT/vLLM.**
- **ollama deployment is currently blocked upstream** (Qwen3-Next is very new):
  ollama 0.24 reports *"loras are not yet implemented"* for the adapter path, and the
  merged-model GGUF (q8 and f16) is rejected by ollama's `qwen3next` loader
  (*"layer N missing attn_qkv/attn_gate"*). The adapter + merged-f16 GGUF are kept under
  `work_dir` for when ollama gains Qwen3-Next LoRA / merged-GGUF support.

## Known follow-ons

- **Label validation pass**: drop/repair examples whose `tool`/`hint_tools` aren't
  in the live catalog, or whose `intent` conflicts with the emitted `tool`
  (the teacher occasionally tags a single concrete launch `agent` instead of
  `dispatch`). Raises corpus quality before training.
- **Single-source the refine prompt**: today the dataset's label system prompt
  mirrors `_REFINE_SYSTEM_LITE`; extracting that constant into a shared module
  consumed by both the pipe and the generator removes the drift risk.
- **Extend beyond the refiner**: the same pipeline targets the other role models
  (`target_role`), distilling each from the strongest teacher that fits.
