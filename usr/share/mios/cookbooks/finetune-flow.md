# Cookbook: SFT → DPO Fine-Tuning Flow

> Full path: `/usr/share/mios/cookbooks/finetune-flow.md`
> Datasets: `var/lib/mios/training/sft.jsonl` and `dpo.jsonl`
> Both are universal JSONL — consumable by axolotl, trl, llama-factory,
> MLX-LM, unsloth, and any OpenAI-API-compatible fine-tuning endpoint.

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
OpenAI API spec, but most local OpenAI-API-compatible runtimes
(LocalAI / Ollama / vLLM / LM Studio / llama.cpp) do not implement it.
Use one of the local trainers below instead. **MiOS does not document
a recipe that hardcodes a vendor-cloud endpoint** (Architectural
Law 5).

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

## Validating the tuned model

After local training, serve the tuned model via vLLM / llama.cpp /
Ollama (any OpenAI-API-compatible runtime), point `$MIOS_AI_ENDPOINT`
at it, and re-run the local-runner against the served model:

```bash
# Local served model (after vLLM / llama.cpp / Ollama serve)
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint "$MIOS_AI_ENDPOINT" \
  --model    "$MIOS_AI_MODEL" \
  --eval     ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset  ./var/lib/mios/evals/dataset.jsonl \
  --report   ./mios-eval-report.json
```

Look for: ↑ pass rate, ↑ avg score vs the pre-tune baseline.

## When to re-tune

- Major MiOS release (e.g. v0.3.0 with new architectural law)
- New upstream tech adopted (e.g. switch from ostree to bootc-composefs-native)
- Eval pass rate drops below 85% on the latest checkpoint

The `mios_build_kb_refresh` tool regenerates `sft.jsonl` and `dpo.jsonl`
from the live repo — run that, then re-tune.
