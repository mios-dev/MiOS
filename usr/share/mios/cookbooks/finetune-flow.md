<!-- AI-hint: A technical guide for agents to execute a two-stage SFT-then-DPO fine-tuning pipeline using local trainers (axolotl, trl, MLX-LM, unsloth) to align a model with MiOS-specific formatting and preference constraints, then validate and re-serve it on the mios-llm-light lane. Fully local, no vendor-cloud endpoint (Architectural Law 5).
     AI-related: /usr/share/mios/cookbooks/finetune-flow.md, /var/lib/mios/training/sft.jsonl, /var/lib/mios/training/dpo.jsonl, /var/lib/mios/evals/mios-knowledge.local-runner.py, mios-llm-light, mios-build-kb-refresh, mios-knowledge, mios-eval-report -->
# Cookbook: SFT → DPO Fine-Tuning Flow

> Full path: `/usr/share/mios/cookbooks/finetune-flow.md`
> Datasets: `var/lib/mios/training/sft.jsonl` and `dpo.jsonl`
> Both are universal JSONL — consumable by axolotl, trl, llama-factory,
> MLX-LM, unsloth, and any OpenAI-API-compatible fine-tuning endpoint.

## Where this fits in MiOS

MiOS is one image built two ways at once: an immutable, bootc/OCI-shaped Fedora
workstation that is *also* a local, self-hosted agentic AI operating system. The
agent plane — the **agent-pipe** orchestrator (`:8640`), the **MiOS-Hermes**
gateway (`:8642`), and **PostgreSQL + pgvector** memory (`:5432`) — runs entirely
on local **inference lanes** behind the one OpenAI-compatible endpoint named by
`MIOS_AI_ENDPOINT` (default `http://localhost:8080/v1`). The primary lane is
**`mios-llm-light`** (`:11450`): a `llama.cpp` multi-model server fronted by the
[`llama-swap`](https://github.com/mostlygeek/llama-swap) proxy image, which
auto-swaps the everyday chat/reasoning models behind one endpoint **and** serves
embeddings (`nomic-embed-text`). Gated heavy GPU lanes — `mios-llm-heavy`
(SGLang, `:11441`) and `mios-llm-heavy-alt` (vLLM, `:11440`) — sit alongside it.

This cookbook is how you make those lanes serve a model that is *more* MiOS-shaped:
fine-tune a base model on the datasets MiOS extracts from its own live repo, then
re-serve the tuned weights on `mios-llm-light` so the whole agent stack inherits
the improvement. Because the OS is one rebuildable OCI image with version-locked
inference lanes, a tuned model becomes a reproducible part of the system rather
than a one-off artifact on someone's GPU.

A purpose-built, agent-driven variant of this loop ships as the
**fine-tune subsystem** (mios.toml `[finetune]`): it self-distils a strong local
*teacher* (`gemma4:12b`, served by `mios-llm-light`) into a small role model
(e.g. the refiner), exports an adapter, and can re-serve it on the opt-in
`mios-finetune-serve` endpoint (`:11438`). That subsystem is an operator-gated
heavy build (it saturates a GPU and the framework install needs a one-time
network fetch), so it is deliberately **not** an agent verb — no chat turn can
kick off a multi-hour run. This cookbook is the general, manual SFT→DPO recipe
behind the same idea.

## Why SFT then DPO

Two-stage Preference Fine-Tuning:

1. **SFT** establishes the format and base behavior. The model learns to
   produce MiOS-shaped answers (cite files, three-section troubleshoot
   format, refuse to fabricate).
2. **DPO** sharpens preference between two responses where both are
   plausible but one is more aligned (image-time fix vs runtime hack;
   citing PACKAGES.md vs guessing).

DPO without an SFT pass tends to under-train; the dataset is too small
to teach format from scratch.

## Local fine-tuning paths

The Fine-Tuning Jobs API (`POST /v1/fine_tuning/jobs`) is part of the
OpenAI API spec, but most local OpenAI-API-compatible runtimes — including
the engines behind MiOS's own lanes (`llama.cpp` / SGLang / vLLM) — do not
implement it. Use one of the local trainers below instead. **MiOS does not
document a recipe that hardcodes a vendor-cloud endpoint** (Architectural
Law 5 — UNIFIED-AI-REDIRECTS).

If your `$MIOS_AI_ENDPOINT` happens to expose `/v1/fine_tuning/jobs`
(e.g. a LiteLLM proxy fronting a compatible backend), the OpenAI-API
shape is identical: POST a JSONL file via `/v1/files` with
`purpose=fine-tune`, then create the job referencing the returned
`file_id`.

### axolotl (most popular, supports SFT + DPO + ORPO)

```yaml
# axolotl-mios-sft.yaml (excerpt)
base_model: meta-llama/Llama-3.1-8B-Instruct
datasets:
  - path: ./var/lib/mios/training/sft.jsonl
    type: chat_template
    chat_template: llama3
sequence_len: 4096
adapter: lora
lora_r: 64
```

```bash
accelerate launch -m axolotl.cli.train axolotl-mios-sft.yaml
```

For DPO, switch to `dpo:` block referencing `dpo.jsonl`.

### trl (HuggingFace, programmatic)

```python
from trl import SFTTrainer, DPOTrainer

# SFT
sft = SFTTrainer(
    model="meta-llama/Llama-3.1-8B-Instruct",
    train_dataset=load_jsonl("var/lib/mios/training/sft.jsonl"),
    formatting_func=lambda r: r["messages"],  # OpenAI chat format passes through
    ...
)
sft.train()

# DPO
dpo = DPOTrainer(
    model=sft.model,
    train_dataset=load_jsonl("var/lib/mios/training/dpo.jsonl"),
    ...
)
dpo.train()
```

### MLX-LM (Apple Silicon)

```bash
mlx_lm.lora --model meta-llama/Llama-3.1-8B-Instruct \
  --train --data ./var/lib/mios/training/sft.jsonl \
  --iters 200 --learning-rate 1e-4
```

### unsloth (memory-efficient, single-GPU)

```python
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained("unsloth/llama-3.1-8b-instruct-bnb-4bit")
# ... standard SFT trainer with model+tok and sft.jsonl
```

> The base model above is a generic, public example. Match the base to the
> MiOS lane you intend to serve the result on — e.g. the `[finetune]`
> subsystem tunes `Qwen/Qwen3.5-4B` (`base_model = "qwen3.5:4b"`) so the GGUF
> drops straight back onto the `mios-llm-light` model map. The trainer is
> hardware-agnostic: NVIDIA CUDA, AMD ROCm, Apple MPS, and CPU paths all work,
> 4-bit quantising only where the hardware supports it.

## Validating the tuned model

After local training, convert/serve the tuned model on a MiOS inference lane
(`mios-llm-light` via `llama.cpp`, or a heavy lane via SGLang / vLLM — all
OpenAI-API-compatible), point `$MIOS_AI_ENDPOINT` at the served model, and
re-run the local-runner against it. The cleanest re-entry is to add the tuned
model (or its GGUF) to the `mios-llm-light` model map at
`usr/share/mios/llamacpp/llama-swap.yaml` so `llama-swap` swaps it in on demand
on `:11450`.

```bash
# Tuned model served locally (mios-llm-light :11450 / a heavy lane)
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint "$MIOS_AI_ENDPOINT" \
  --model    "$MIOS_AI_MODEL" \
  --eval     ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset  ./var/lib/mios/evals/dataset.jsonl \
  --report   ./mios-eval-report.json
```

The local-runner implements the same grader logic as the `/v1/evals` surface
against any `/v1/chat/completions` endpoint, so it works regardless of which
lane serves the model. Look for: ↑ pass rate, ↑ avg score vs the pre-tune
baseline.

## When to re-tune

- Major MiOS release (e.g. a new architectural law)
- New upstream tech adopted (e.g. switch from ostree to bootc-composefs-native)
- Eval pass rate drops below 85% on the latest checkpoint

The `mios_build_kb_refresh` tool regenerates `sft.jsonl` and `dpo.jsonl`
from the live repo — run that, then re-tune. Because the corpus is extracted
from the running system (the live verb catalog and the pgvector `knowledge`
table of real operator Q+A), the training data tracks the real OS and never
hardcodes a topic list.
