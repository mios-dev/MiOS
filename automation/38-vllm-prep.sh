#!/bin/bash
# automation/38-vllm-prep.sh -- bake the GUI-grounding VLM weights into the
# image so the mios-vllm Quadlet serves them OFFLINE (vLLM/HF will NOT
# download air-gapped at runtime). Mirrors automation/37-ollama-prep.sh:
# build-time, best-effort, NEVER fails the build (exit 0 on any error).
#
# Weights land in /usr/share/mios/vllm/grounding (immutable composefs
# surface; the build's /var cleanup doesn't touch /usr/share). The
# mios-vllm.container mounts that dir read-only at /models/grounding.
#
# Default model: Qwen3-VL-4B-Instruct -- open GUI grounder, ~6-10GB VRAM,
# beats older specialists (OS-Atlas/ShowUI) on ScreenSpot-Pro. Override
# with MIOS_VLLM_BAKE_MODEL=<hf-repo> at build time; empty disables the
# bake entirely (e.g. CI builds that only validate the pipeline). Other
# clean FOSS choices: microsoft/GUI-Actor-7B-Qwen2-VL (MIT),
# Hcompany/Holo1.5-7B (Apache), ByteDance-Seed/UI-TARS-1.5-7B (Apache).
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[38-vllm] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

MODEL="${MIOS_VLLM_BAKE_MODEL:-Qwen/Qwen3-VL-4B-Instruct}"
SEED_DIR="/usr/share/mios/vllm/grounding"

if [[ -z "$MODEL" ]]; then
    log "[38-vllm] MIOS_VLLM_BAKE_MODEL empty -- skipping grounding-VLM bake"
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
