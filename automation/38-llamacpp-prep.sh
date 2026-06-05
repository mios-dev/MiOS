#!/bin/bash
# automation/38-llamacpp-prep.sh -- bake GGUF weights for the llama-swap lane
# (WS-10) into the image so mios-llama-swap serves them OFFLINE (llama.cpp will
# NOT download air-gapped at runtime). Mirrors automation/38-vllm-prep.sh:
# build-time, best-effort, NEVER fails the build (exit 0 on any error).
#
# GGUFs land in /usr/share/mios/llamacpp/models (immutable composefs surface; the
# build's /var cleanup doesn't touch /usr/share). mios-llama-swap.container
# mounts that dir RO at /models and is gated by ConditionPathExists(
# .../models/.ready) -- this script touches .ready ONLY when at least one GGUF
# baked, so the lane stays inert until real weights exist.
#
# OPT-IN: MIOS_LLAMACPP_BAKE_MODELS (rendered from mios.toml [llamacpp].
# bake_models) defaults EMPTY so no multi-GB weights bloat every image. Format =
# CSV of  <dest.gguf>=<hf_repo_id>:<filename_in_repo>  matching the filenames the
# llama-swap.yaml model map expects, e.g.:
#   qwen3.5-4b.gguf=bartowski/Qwen2.5-3B-Instruct-GGUF:Qwen2.5-3B-Instruct-Q4_K_M.gguf,
#   nomic-embed-text.gguf=nomic-ai/nomic-embed-text-v1.5-GGUF:nomic-embed-text-v1.5.Q4_K_M.gguf
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
    log "[38-llamacpp] MIOS_LLAMACPP_BAKE_MODELS empty -- skipping GGUF bake (opt-in; the llama-swap lane stays gated/inert)"
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
    log "[38-llamacpp] baked ${baked} GGUF(s) -> ${SEED_DIR} (${seed_size:-?}); .ready set -- llama-swap lane eligible"
else
    log "[38-llamacpp] no GGUFs baked -- leaving the lane gated (no .ready written)"
fi
exit 0
