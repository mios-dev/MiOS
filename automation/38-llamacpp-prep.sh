#!/bin/bash
# AI-hint: Bakes GGUF weights into /usr/share/mios/llamacpp/models based on MIOS_LLAMACPP_BAKE_MODELS config to enable the offline mios-llm-light lane; agents use this to ensure local model availability.
# AI-related: /usr/share/mios/llamacpp/models, mios-llm-light, mios-llm-light.container
# automation/38-llamacpp-prep.sh -- bake GGUF weights for the mios-llm-light lane
# (WS-10) into the image so mios-llm-light serves them OFFLINE (llama.cpp will
# NOT download air-gapped at runtime). Mirrors automation/38-vllm-prep.sh:
# build-time, best-effort, NEVER fails the build (exit 0 on any error).
#
# GGUFs land in /usr/share/mios/llamacpp/models (immutable composefs surface; the
# build's /var cleanup doesn't touch /usr/share). mios-llm-light.container
# mounts that dir RO at /models and is gated by ConditionPathExists(
# .../models/.ready) -- this script touches .ready ONLY when at least one GGUF
# baked, so the lane stays inert until real weights exist.
#
# OPT-IN: MIOS_LLAMACPP_BAKE_MODELS (rendered from mios.toml [llamacpp].
# bake_models) defaults EMPTY so no multi-GB weights bloat every image. Format =
# CSV of  <dest.gguf>=<hf_repo_id>:<filename_in_repo>  matching the filenames the
# mios-llm-light.yaml model map expects, e.g.:
#   granite-4.1-8b.gguf=unsloth/granite-4.1-8b-GGUF:granite-4.1-8b-Q4_K_M.gguf,
#   embeddinggemma-300m-qat-q8_0.gguf=ggml-org/embeddinggemma-300m-qat-q8_0-GGUF:embeddinggemma-300m-qat-Q8_0.gguf
# Pre-quantized GGUFs are downloaded directly (no convert step). All FOSS repos.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[38-llamacpp] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

SPEC="${MIOS_LLAMACPP_BAKE_MODELS:-}"
SEED_DIR="/usr/share/mios/llamacpp/models"

if [[ -z "$SPEC" ]]; then
    log "[38-llamacpp] MIOS_LLAMACPP_BAKE_MODELS empty -- skipping GGUF bake (opt-in; the mios-llm-light lane stays gated/inert)"
    exit 0
fi

install -d -m 0755 "$SEED_DIR"

baked=0
IFS=',' read -ra _entries <<< "$SPEC"
for entry in "${_entries[@]}"; do
    entry="$(printf '%s' "$entry" | tr -d '[:space:]')"
    [[ -z "$entry" ]] && continue
    # parse dest.gguf=repo:file
    dest="${entry%%=*}"
    rest="${entry#*=}"
    repo="${rest%%:*}"
    file="${rest#*:}"
    if [[ -z "$dest" || -z "$repo" || -z "$file" || "$dest" == "$entry" || "$repo" == "$rest" ]]; then
        log "[38-llamacpp] malformed entry '${entry}' (want dest.gguf=repo:file) -- skipping"
        continue
    fi
    if [[ -s "${SEED_DIR}/${dest}" ]]; then
        log "[38-llamacpp] ${dest} already present -- skipping"
        baked=$((baked + 1))
        continue
    fi
    # huggingface_hub hf_hub_download (FOSS) -- fetch ONE pre-quantized GGUF.
    # Pip-install it if the build image doesn't ship it yet.
    if python3 - "$repo" "$file" "${SEED_DIR}/${dest}" <<'PY'
import shutil, sys
try:
    from huggingface_hub import hf_hub_download
except Exception:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "huggingface_hub"], check=False)
    from huggingface_hub import hf_hub_download
repo, fname, dest = sys.argv[1], sys.argv[2], sys.argv[3]
path = hf_hub_download(repo_id=repo, filename=fname)
shutil.copyfile(path, dest)
print(f"baked {repo}:{fname} -> {dest}")
PY
    then
        baked=$((baked + 1))
    else
        log "[38-llamacpp] download failed for ${repo}:${file} (no egress / upstream issue) -- continuing; 'mios update' can retry"
    fi
done

if [[ "$baked" -gt 0 ]]; then
    : > "${SEED_DIR}/.ready"   # the quadlet's ConditionPathExists gate -> lane eligible
    seed_size="$(du -sh "$SEED_DIR" 2>/dev/null | awk '{print $1}')"
    log "[38-llamacpp] baked ${baked} GGUF(s) -> ${SEED_DIR} (${seed_size:-?}); .ready set -- mios-llm-light lane eligible"
else
    log "[38-llamacpp] no GGUFs baked -- leaving the lane gated (no .ready written)"
fi
exit 0
