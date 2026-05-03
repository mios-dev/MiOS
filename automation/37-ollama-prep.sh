#!/bin/bash
# 37-ollama-prep -- bake the default 'MiOS' model set into the image.
#
# Models land in /usr/share/ollama/models (immutable composefs surface,
# FHS-correct for "architecture-independent immutable data"). The
# build-time /var cleanup at the end of the Containerfile RUN does NOT
# touch /usr/share, so the seed survives into the deployed image.
#
# At first boot, mios-ollama-firstboot.service hardlink-copies the seed
# into /var/lib/ollama/models (the writable runtime location ollama.
# container reads/writes via OLLAMA_MODELS). Hardlinks keep the on-disk
# footprint single-copy until ollama mutates a model file.
#
# Default model set (researched for the 12 GB RAM workstation baseline):
#   qwen2.5-coder:7b   -- chat / code primary (~4.7 GB Q4_K_M)
#                          best open-source coder in the 7B class as of
#                          2026; 128K context; Apache 2.0
#   nomic-embed-text   -- embedding (~270 MB Q4_K_M)
#                          768-dim, 8192-token context, MTEB-competitive
#
# Override the set with MIOS_OLLAMA_BAKE_MODELS=<csv> at build time --
# e.g. MIOS_OLLAMA_BAKE_MODELS="qwen2.5-coder:14b,nomic-embed-text" for
# the 24 GB+ profile. Empty value disables baking entirely (useful for
# CI builds that only validate the pipeline).
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

DEFAULT_MODELS="qwen2.5-coder:7b,nomic-embed-text"
BAKE_MODELS="${MIOS_OLLAMA_BAKE_MODELS:-${DEFAULT_MODELS}}"
BAKE_DIR="/usr/share/ollama/models"

if [[ -z "$BAKE_MODELS" ]]; then
    log "MIOS_OLLAMA_BAKE_MODELS empty -- skipping build-time model bake"
    exit 0
fi

# Idempotency guard: if the seed dir already has manifests, assume a
# previous bake step in this build already populated it.
if [[ -d "${BAKE_DIR}/manifests" ]] && [[ -n "$(ls -A "${BAKE_DIR}/manifests" 2>/dev/null)" ]]; then
    log "Seed models already present at ${BAKE_DIR}; skipping re-bake"
    exit 0
fi

# ollama is installed as part of packages-ai (see usr/share/mios/PACKAGES.md).
# If it's not on PATH the build context didn't include the AI pack -- skip
# rather than fail so unrelated CI builds still pass.
if ! command -v ollama >/dev/null 2>&1; then
    log "ollama binary not found -- skipping bake (AI pack missing from this build)"
    exit 0
fi

# Bake destination; OLLAMA_MODELS is the canonical override env var
# the upstream binary respects.
install -d -m 0755 "${BAKE_DIR}"
export OLLAMA_MODELS="${BAKE_DIR}"

# Start a temporary ollama serve instance just for the duration of the
# pull. Detach it ourselves so we keep stable control over its lifetime.
log "Starting transient ollama serve (host=127.0.0.1:11434, store=${BAKE_DIR})"
OLLAMA_HOST="127.0.0.1:11434" ollama serve >/tmp/ollama-bake.log 2>&1 &
OLLAMA_PID=$!

# Wait up to 30 s for the API. If it never comes up, log + skip rather
# than fail the build.
for attempt in $(seq 1 15); do
    if scurl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
if ! scurl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    log "WARN: ollama serve never became reachable -- skipping bake"
    kill "$OLLAMA_PID" 2>/dev/null || true
    wait "$OLLAMA_PID" 2>/dev/null || true
    exit 0
fi

# Pull each requested model. A failure on one model is non-fatal (build
# continues; first-boot service catches up).
failures=0
IFS=',' read -ra MODELS <<< "$BAKE_MODELS"
for raw_model in "${MODELS[@]}"; do
    model="${raw_model// /}"
    [[ -z "$model" ]] && continue
    log "Pulling ${model} into ${BAKE_DIR}"
    if OLLAMA_HOST="127.0.0.1:11434" ollama pull "$model"; then
        log "  [ok] ${model}"
    else
        log "  [WARN] ${model} pull failed -- first-boot service will retry"
        failures=$((failures + 1))
    fi
done

# Stop the transient serve cleanly.
kill "$OLLAMA_PID" 2>/dev/null || true
wait "$OLLAMA_PID" 2>/dev/null || true

# Report the on-disk size so build logs make the +N GB cost obvious.
seed_size="$(du -sh "${BAKE_DIR}" 2>/dev/null | awk '{print $1}')"
log "Bake complete -- ${BAKE_DIR} = ${seed_size:-?} (failures: ${failures})"
exit 0
