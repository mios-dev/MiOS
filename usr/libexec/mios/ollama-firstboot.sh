#!/usr/bin/env bash
# usr/libexec/mios/ollama-firstboot.sh
#
# Pull the default 'MiOS' inference models on first boot. Run by
# mios-ollama-firstboot.service after ollama.service is active. Models
# land in /var/lib/ollama (mutable, persistent across bootc upgrades),
# which is why this can't be done at build time -- the OCI build's
# final /var cleanup would delete them.
#
# Sentinel-guarded: writes /var/lib/mios/.ollama-firstboot-done so a
# re-fire (after a bootc rollback or service restart) is a no-op.
# Re-pulling specific models on demand is still possible via
# 'podman exec mios-ollama ollama pull <model>'.
#
# Default model set tracks the OpenAI-API-shaped surface advertised in
# usr/share/mios/ai/v1/models.json; keep them in sync.
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh 2>/dev/null || true
: "${MIOS_VAR_DIR:=/var/lib/mios}"

SENTINEL="${MIOS_VAR_DIR}/.ollama-firstboot-done"
CONTAINER="mios-ollama"
DEFAULT_MODELS=(
    "qwen2.5-coder:7b"
    "nomic-embed-text"
)

_log() { logger -t mios-ollama-firstboot "$*" 2>/dev/null || true; echo "[ollama-firstboot] $*" >&2; }

if [[ -f "$SENTINEL" ]]; then
    _log "sentinel exists ($SENTINEL); models already pulled -- nothing to do"
    exit 0
fi

# Wait for the ollama container to be running. The service unit has
# After=ollama.service so it should be up, but the container may need
# a few seconds to finish initializing the model store on first start.
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if podman exec "$CONTAINER" ollama list >/dev/null 2>&1; then
        break
    fi
    _log "waiting for $CONTAINER (attempt $attempt/10)"
    sleep 5
done

if ! podman exec "$CONTAINER" ollama list >/dev/null 2>&1; then
    _log "ERROR: $CONTAINER not reachable after 50s; aborting first-boot pull"
    exit 1
fi

failures=0
for model in "${DEFAULT_MODELS[@]}"; do
    _log "pulling $model"
    if podman exec "$CONTAINER" ollama pull "$model" 2>&1 | logger -t mios-ollama-firstboot; then
        _log "  [ok] $model"
    else
        _log "  [WARN] failed to pull $model -- continuing"
        failures=$((failures + 1))
    fi
done

# Drop the sentinel even when some pulls failed -- we don't want every
# boot to retry indefinitely. Operators can re-run by deleting the
# sentinel: rm /var/lib/mios/.ollama-firstboot-done && systemctl start
# mios-ollama-firstboot
install -d -m 0755 "$(dirname "$SENTINEL")"
touch "$SENTINEL"

if (( failures > 0 )); then
    _log "first-boot pull complete with $failures failure(s)"
    exit 0   # non-fatal so the boot doesn't degrade
fi
_log "first-boot pull complete -- all models present"
exit 0
