#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: MiOS AI model-weight bake for BOTH local /v1 lanes -- llama.cpp GGUFs and the vLLM snapshot. Folded from 38-llamacpp-prep + 38-vllm-prep; each block is independently env-gated (MIOS_LLAMACPP_BAKE_MODELS / MIOS_VLLM_BAKE_MODEL), writes a disjoint SEED_DIR, and only appends to sbom/models.tsv.
# AI-functions: (see blocks below)

# ===== folded from 38-llamacpp-prep.sh =====
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
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    mios_warn "lib/common.sh unavailable -- skipping"
    exit 0
}

SPEC="${MIOS_LLAMACPP_BAKE_MODELS:-}"
SEED_DIR="/usr/share/mios/llamacpp/models"

if [[ -z "$SPEC" ]]; then
    mios_log "MIOS_LLAMACPP_BAKE_MODELS empty -- symlink /var/lib/mios/llamacpp/models for runtime downloads"
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
        mios_warn "malformed entry '${entry}' (want dest.gguf=repo:file) -- skipping"
        continue
    fi
    if [[ -s "${SEED_DIR}/${dest}" ]]; then
        mios_skip "${dest} already present"
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
        mios_ok "baked ${repo}:${file} -> ${dest} (${_url})"

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
        mios_warn "download failed for ${repo}:${file} (no egress / upstream issue) -- continuing; 'mios update' can retry"
    fi
done

if [[ "$baked" -gt 0 ]]; then
    : > "${SEED_DIR}/.ready"   # the quadlet's ConditionPathExists gate -> lane eligible
    seed_size="$(du -sh "$SEED_DIR" 2>/dev/null | awk '{print $1}')"
    mios_ok "baked ${baked} GGUF(s) -> ${SEED_DIR} (${seed_size:-?}); .ready set -- mios-llm-light lane eligible"
else
    mios_log "no GGUFs baked -- lane gated (no .ready written)"
fi
exit 0

# ===== folded from 38-vllm-prep.sh =====
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
    mios_warn "lib/common.sh unavailable -- skipping"
    exit 0
}

MODEL="${MIOS_VLLM_BAKE_MODEL:-}"
SEED_DIR="/usr/share/mios/vllm/model"

if [[ -z "$MODEL" ]]; then
    mios_log "MIOS_VLLM_BAKE_MODEL empty -- symlink /var/lib/mios/vllm/model for runtime downloads"
    rm -rf "$SEED_DIR" 2>/dev/null || true
    ln -sf /var/lib/mios/vllm/model "$SEED_DIR"
    exit 0
fi

if [[ -L "$SEED_DIR" ]]; then
    rm -f "$SEED_DIR"
fi
if [[ -d "$SEED_DIR" ]] && [[ -n "$(ls -A "$SEED_DIR" 2>/dev/null)" ]]; then
    mios_skip "seed already present at ${SEED_DIR}"
    exit 0
fi

install -d -m 0755 "$SEED_DIR"

# huggingface_hub snapshot_download (FOSS). Pip-install it if the build
# image doesn't ship it yet. ignore_patterns drops the duplicate .pth /
# original weights so we only bake the safetensors vLLM actually loads.
if ! python3 - "$MODEL" "$SEED_DIR" <<'PY'
import sys, os
os.makedirs("/usr/local/lib", exist_ok=True)
try:
    from huggingface_hub import snapshot_download
except Exception:
    import subprocess
    os.makedirs("/tmp/hf_hub", exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", "/tmp/hf_hub",
                    "huggingface_hub"], check=False)
    sys.path.insert(0, "/tmp/hf_hub")
    import importlib
    importlib.invalidate_caches()
    from huggingface_hub import snapshot_download
model, dest = sys.argv[1], sys.argv[2]
snapshot_download(repo_id=model, local_dir=dest,
                  ignore_patterns=["*.pth", "original/*", "*.gguf"])
print(f"baked {model} -> {dest}")
PY
then
    mios_warn "download failed (no egress / upstream issue) -- skipping; 'mios update' can retry"
    # Leave the (empty) seed dir; the Quadlet's ConditionPathExists on
    # config.json keeps the unit from crash-looping without weights.
    exit 0
fi

# Record Safetensors files recursively to models SBOM (RELTOP-01 / T-251)
sbom_dir="/usr/share/mios/artifacts/sbom"
mkdir -p "$sbom_dir"
sbom_file="${sbom_dir}/models.tsv"
if [[ -d "$SEED_DIR" ]]; then
    find "$SEED_DIR" -type f | while read -r filepath; do
        relpath="${filepath#$SEED_DIR/}"
        sha=""
        if command -v sha256sum >/dev/null 2>&1; then
            sha="$(sha256sum "$filepath" | awk '{print $1}')"
        fi
        printf '%s\t%s\t%s\t%s\t%s\n' "$relpath" "safetensors" "$MODEL" "$relpath" "${sha:-unknown}" >> "$sbom_file"
    done
fi

seed_size="$(du -sh "$SEED_DIR" 2>/dev/null | awk '{print $1}')"
mios_ok "baked ${MODEL} -> ${SEED_DIR} (${seed_size:-?})"
exit 0
