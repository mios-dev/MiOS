#!/usr/bin/env bash
# usr/libexec/mios/ollama-firstboot.sh
#
# First-boot model bootstrap for the mios-ollama Quadlet.
#
# Build-time path (preferred): automation/37-ollama-prep.sh has already
# baked the default model set into /usr/share/ollama/models on the
# immutable composefs surface. This script hardlink-copies that seed
# into /var/lib/ollama/models on first boot so ollama can both read
# AND write models there (the writable runtime store), without paying
# a second on-disk copy until ollama itself mutates a manifest.
#
# Network fallback: if the seed dir is empty (e.g. CI built the image
# with MIOS_OLLAMA_BAKE_MODELS= to keep image size down), pull the
# user-configured model set via 'podman exec mios-ollama ollama pull'.
# The model list is read from /etc/mios/install.env (MIOS_AI_MODEL,
# MIOS_AI_EMBED_MODEL) so the build's globally-defaulted set carries
# through to runtime, with operator overrides taking precedence.
#
# Sentinel: /var/lib/mios/.ollama-firstboot-done -- delete to force
# a re-run.
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh 2>/dev/null || true
: "${MIOS_VAR_DIR:=/var/lib/mios}"

SENTINEL="${MIOS_VAR_DIR}/.ollama-firstboot-done"
SEED_DIR="/usr/share/ollama/models"
RUNTIME_DIR="/var/lib/ollama/models"
CONTAINER="mios-ollama"

_log() { logger -t mios-ollama-firstboot "$*" 2>/dev/null || true; echo "[ollama-firstboot] $*" >&2; }

if [[ -f "$SENTINEL" ]]; then
    _log "sentinel exists ($SENTINEL); first-boot already done"
    exit 0
fi

# ── Layer 1: hardlink-copy the build-baked seed into the runtime dir ──
# 'cp -al' tries hardlinks first and falls back to a regular copy when
# the source/destination cross filesystems. Models then occupy a single
# inode-level copy until ollama mutates one of the manifest files.
if [[ -d "$SEED_DIR" ]] && [[ -n "$(ls -A "$SEED_DIR" 2>/dev/null)" ]]; then
    if [[ ! -d "$RUNTIME_DIR" ]] || [[ -z "$(ls -A "$RUNTIME_DIR" 2>/dev/null)" ]]; then
        _log "Seeding $RUNTIME_DIR from $SEED_DIR (hardlink-copy)"
        install -d -m 0755 "$RUNTIME_DIR"
        # Two-pass: try hardlink first, fall back to plain copy if it
        # crosses a filesystem boundary (likely between /usr composefs
        # and /var ext4 on bootc deployments).
        if cp -al "${SEED_DIR}/." "${RUNTIME_DIR}/" 2>/dev/null; then
            _log "  [ok] hardlink-copy succeeded"
        else
            _log "  [info] hardlink crossed FS boundary; falling back to cp -a"
            cp -a "${SEED_DIR}/." "${RUNTIME_DIR}/"
        fi
        chown -R mios-ollama:mios-ollama "$RUNTIME_DIR" 2>/dev/null || true
    else
        _log "Runtime dir $RUNTIME_DIR already populated; skipping seed copy"
    fi
else
    _log "No build-baked seed at $SEED_DIR -- network pull fallback"
fi

# ── Layer 2: ensure the configured models are present, pulling any gaps ──
# Read the runtime model selection from install.env so operators can
# override the build-baked default without rebuilding the image.
DEFAULT_CHAT="qwen2.5-coder:7b"
DEFAULT_EMBED="nomic-embed-text"
MIOS_AI_MODEL="$DEFAULT_CHAT"
MIOS_AI_EMBED_MODEL="$DEFAULT_EMBED"
if [[ -f /etc/mios/install.env ]]; then
    # shellcheck disable=SC1091
    source /etc/mios/install.env 2>/dev/null || true
fi

# Wait for the ollama container to be up. After=ollama.service in the
# unit, but the model store may need a few seconds to settle on first
# start.
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if podman exec "$CONTAINER" ollama list >/dev/null 2>&1; then
        break
    fi
    _log "waiting for $CONTAINER (attempt $attempt/10)"
    sleep 5
done
if ! podman exec "$CONTAINER" ollama list >/dev/null 2>&1; then
    # Do NOT touch the sentinel here. Earlier revisions did; symptom
    # 2026-05-11: if the ollama container crash-looped during first
    # boot (e.g. UID mismatch with /var/lib/ollama bind-mount), this
    # script gave up after 50 s, wrote the sentinel as if successful,
    # and the unit's ConditionPathExists permanently blocked any
    # retry. The operator's `mios hello` then hit a chat-completions
    # endpoint with zero models loaded and got 500s forever. Exit
    # non-zero so systemd's Restart= (or the next boot's
    # ConditionPathExists=!sentinel) retries until the container is
    # actually reachable.
    _log "WARN: $CONTAINER not reachable after 50 s -- exiting non-zero to retry on next start (sentinel NOT written)"
    exit 1
fi

failures=0
for model in "$MIOS_AI_MODEL" "$MIOS_AI_EMBED_MODEL"; do
    [[ -z "$model" ]] && continue
    # If 'ollama list' already shows it, skip the pull -- saves a long
    # network round-trip when the build-baked seed already supplied it.
    if podman exec "$CONTAINER" ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$model"; then
        _log "  [present] $model"
        continue
    fi
    _log "pulling $model"
    if podman exec "$CONTAINER" ollama pull "$model" 2>&1 | logger -t mios-ollama-firstboot; then
        _log "  [ok] $model"
    else
        _log "  [WARN] failed to pull $model -- continuing"
        failures=$((failures + 1))
    fi
done

# Drop the sentinel even when some pulls fail -- avoid an indefinite
# retry loop on every boot. Manual recovery: delete the sentinel and
# restart mios-ollama-firstboot.service.
install -d -m 0755 "$(dirname "$SENTINEL")"
touch "$SENTINEL"

if (( failures > 0 )); then
    _log "first-boot complete with $failures pull failure(s)"
    exit 0   # non-fatal; don't degrade the boot
fi
_log "first-boot complete -- model set ready at $RUNTIME_DIR"
exit 0
