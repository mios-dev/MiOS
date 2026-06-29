#!/bin/bash
# AI-hint: Compile/render mios-llm-light.yaml into /etc/mios/llamacpp/mios-llm-light.yaml overlay based on MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS.
# automation/firstboot/mios-conv-inference-setup.sh
set -euo pipefail

ENV_FILE="/etc/mios/install.env"
SRC_YAML="/usr/share/mios/llamacpp/mios-llm-light.yaml"
DST_DIR="/etc/mios/llamacpp"
DST_YAML="${DST_DIR}/mios-llm-light.yaml"

mkdir -p "$DST_DIR"

tokens=0
slots=1

if [[ -r "$ENV_FILE" ]]; then
    set +u
    . "$ENV_FILE"
    set -u
    tokens="${MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS:-0}"
    slots="${MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS:-1}"
fi

if [[ "$tokens" -gt 0 ]]; then
    # Render with cache-reuse and slots
    sed "s/--parallel \${MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS:-1} --cache-reuse \${MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS:-0}/--parallel ${slots} --cache-reuse ${tokens}/g" "$SRC_YAML" > "$DST_YAML"
else
    # Render without cache-reuse, parallel 1
    sed "s/--parallel \${MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS:-1} --cache-reuse \${MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS:-0}/--parallel 1/g" "$SRC_YAML" > "$DST_YAML"
fi
echo "[mios-conv-inference-setup] Rendered $DST_YAML (cache-reuse=$tokens, parallel=$slots)"
