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
    log "[38-llamacpp] MIOS_LLAMACPP_BAKE_MODELS empty -- creating symlink to /var/lib/mios/llamacpp/models for runtime downloads"
    rm -rf "$SEED_DIR" 2>/dev/null || true
    ln -sf /var/lib/mios/llamacpp/models "$SEED_DIR"
    exit 0
fi

if [[ -L "$SEED_DIR" ]]; then
    rm -f "$SEED_DIR"
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
    # Fetch ONE pre-quantized GGUF via a plain curl of the HF resolve URL.
    # NO huggingface_hub / runtime `pip install` (the old path's pip-install
    # failed silently on locked/air-gapped build images -> no GGUFs -> the
    # llm-light lane skipped;). --fail (no 200 -> non-zero), -L
    # (follow the CDN redirect), -C - (resume a partial .part). Download to a
    # .part + atomic rename so a truncated file never trips the .ready gate.
    _url="https://huggingface.co/${repo}/resolve/main/${file}"
    if curl -fL -C - --retry 3 --max-time 1800 \
            -o "${SEED_DIR}/${dest}.part" "$_url" \
       && [[ -s "${SEED_DIR}/${dest}.part" ]]; then
        mv -f "${SEED_DIR}/${dest}.part" "${SEED_DIR}/${dest}"
        baked=$((baked + 1))
        log "[38-llamacpp] baked ${repo}:${file} -> ${dest} (${_url})"

        # Record to models SBOM (RELTOP-01 / T-251)
        sbom_dir="/usr/share/mios/artifacts/sbom"
        mkdir -p "$sbom_dir"
        sha=""
        if command -v sha256sum >/dev/null 2>&1; then
            sha="$(sha256sum "${SEED_DIR}/${dest}" | awk '{print $1}')"
        fi
        printf '%s\t%s\t%s\t%s\t%s\n' "$dest" "gguf" "$repo" "$file" "${sha:-unknown}" >> "${sbom_dir}/models.tsv"
    else
        rm -f "${SEED_DIR}/${dest}.part" 2>/dev/null || true
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
