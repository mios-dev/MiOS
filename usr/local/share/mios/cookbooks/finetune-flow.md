# Cookbook: SFT → DPO Fine-Tuning Flow

> Full path: `/usr/local/share/mios/cookbooks/finetune-flow.md`
> Datasets: `var/lib/mios/training/sft.jsonl` and `dpo.jsonl`
> Both are universal JSONL — consumable by OpenAI fine-tuning,
> axolotl, trl, llama-factory, MLX-LM, unsloth.

## Why SFT then DPO

OpenAI's recommended PFT (Preference Fine-Tuning) flow:

1. **SFT** establishes the format and base behavior. The model learns to
   produce MiOS-shaped answers (cite files, three-section troubleshoot
   format, refuse to fabricate).
2. **DPO** sharpens preference between two responses where both are
   plausible but one is more aligned (image-time fix vs runtime hack;
   citing PACKAGES.md vs guessing).

DPO without an SFT pass tends to under-train; the dataset is too small
to teach format from scratch.

## OpenAI cloud path

```bash
# 1. SFT
SFT_FILE=$(curl -s https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose=fine-tune -F file=@./var/lib/mios/training/sft.jsonl | jq -r .id)
SFT_JOB=$(curl -s https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "{\"training_file\":\"$SFT_FILE\",\"model\":\"gpt-4.1-mini\"}" | jq -r .id)
# Wait for completion (poll), capture fine_tuned_model id
SFT_MODEL=$(curl -s https://api.openai.com/v1/fine_tuning/jobs/$SFT_JOB \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq -r .fine_tuned_model)

# 2. DPO on top of the SFT-tuned model
DPO_FILE=$(curl -s https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose=fine-tune -F file=@./var/lib/mios/training/dpo.jsonl | jq -r .id)
curl https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d "{\"training_file\":\"$DPO_FILE\",\"model\":\"$SFT_MODEL\",\"method\":{\"type\":\"dpo\"}}"
```

## Local fine-tuning paths

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

Re-run the local-runner.py against the deployed (cloud) or served
(local) tuned model:

```bash
# Cloud OpenAI:
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint https://api.openai.com/v1 \
  --key $OPENAI_API_KEY \
  --model ft:gpt-4.1-mini:org:mios-engineer:abc123 \
  --eval ./var/lib/mios/evals/mios-knowledge.eval.json \
  --dataset ./var/lib/mios/evals/dataset.jsonl

# Local (after deploying via vLLM, llama.cpp, etc.):
python3 ./var/lib/mios/evals/mios-knowledge.local-runner.py \
  --endpoint http://localhost:8000/v1 \
  --model ./mios-llama-3.1-8b-tuned/
```

Look for: ↑ pass rate, ↑ avg score vs the pre-tune baseline.

## When to re-tune

- Major MiOS release (e.g. v0.3.0 with new architectural law)
- New upstream tech adopted (e.g. switch from ostree to bootc-composefs-native)
- Eval pass rate drops below 85% on the latest checkpoint

The `mios_build_kb_refresh` tool regenerates `sft.jsonl` and `dpo.jsonl`
from the live repo — run that, then re-tune.
