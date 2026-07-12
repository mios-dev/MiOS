#!/bin/bash
# AI-hint: Bakes vLLM model weights into the image at /usr/share/mios/vllm/model if MIOS_VLLM_BAKE_MODEL is set, enabling offline serving via the mios-llm-heavy-alt Quadlet for air-gapped environments.
# AI-related: /usr/share/mios/vllm/model, mios-llm-heavy-alt, mios-grounding, mios-llm-heavy-alt.container
# automation/38-vllm-prep.sh -- bake the vLLM heavy-lane weights into the image
# so the mios-llm-heavy-alt Quadlet serves them OFFLINE (vLLM/HF will NOT download
# air-gapped at runtime). Mirrors automation/38-llamacpp-prep.sh: build-time,
# best-effort, NEVER fails the build (exit 0 on any error).
#
# Weights land in /usr/share/mios/vllm/model (immutable composefs surface; the
# build's /var cleanup doesn't touch /usr/share). The mios-llm-heavy-alt.container mounts
# that dir read-only at /models.
#
# RE-SCOPED (Phase 2 = gated vLLM HEAVY TEXT lane). The model is
# OPT-IN: MIOS_VLLM_BAKE_MODEL (rendered from mios.toml [ai.vllm].bake_model)
# defaults EMPTY so no multi-GB model bloats every image -- set it at build time
# to bake. Recommended text reasoners (Apache-2.0):
#   Qwen/Qwen3-8B          ~16GB fp16 / ~6GB AWQ  -- mid dGPU
#   Qwen/Qwen3-30B-A3B     MoE 30B / 3B-active     -- the "large model", big dGPU + quant
# To serve a GUI-grounding VLM on this same lane instead, point this at one
# (Qwen/Qwen3-VL-4B-Instruct, microsoft/GUI-Actor-7B-Qwen2-VL [MIT],
# Hcompany/Holo1.5-7B, ByteDance-Seed/UI-TARS-1.5-7B) + set
# [ai.vllm].served_name = "mios-grounding".
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[38-vllm] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

MODEL="${MIOS_VLLM_BAKE_MODEL:-}"
SEED_DIR="/usr/share/mios/vllm/model"

if [[ -z "$MODEL" ]]; then
    log "[38-vllm] MIOS_VLLM_BAKE_MODEL empty -- skipping vLLM heavy-lane bake (opt-in; the lane stays gated/inert)"
    exit 0
fi
if [[ -d "$SEED_DIR" ]] && [[ -n "$(ls -A "$SEED_DIR" 2>/dev/null)" ]]; then
    log "[38-vllm] seed already present at ${SEED_DIR}; skipping re-bake"
    exit 0
fi

install -d -m 0755 "$SEED_DIR"

# huggingface_hub snapshot_download (FOSS). Pip-install it if the build
# image doesn't ship it yet. ignore_patterns drops the duplicate .pth /
# original weights so we only bake the safetensors vLLM actually loads.
if ! python3 - "$MODEL" "$SEED_DIR" <<'PY'
import sys
try:
    from huggingface_hub import snapshot_download
except Exception:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "huggingface_hub"], check=False)
    import importlib
    importlib.invalidate_caches()
    from huggingface_hub import snapshot_download
model, dest = sys.argv[1], sys.argv[2]
snapshot_download(repo_id=model, local_dir=dest,
                  ignore_patterns=["*.pth", "original/*", "*.gguf"])
print(f"baked {model} -> {dest}")
PY
then
    log "[38-vllm] download failed (no egress / upstream issue) -- skipping; 'mios update' can retry"
    # Leave the (empty) seed dir; the Quadlet's ConditionPathExists on
    # config.json keeps the unit from crash-looping without weights.
    exit 0
fi

seed_size="$(du -sh "$SEED_DIR" 2>/dev/null | awk '{print $1}')"
log "[38-vllm] baked ${MODEL} -> ${SEED_DIR} (${seed_size:-?})"
exit 0
