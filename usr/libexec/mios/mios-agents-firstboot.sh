#!/usr/bin/env bash
# AI-hint: Build-if-missing bootstrap for the mios-agents A2O super-container image
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, mios-agents.service, mios-code-server.service, mios-forge-firstboot
set -euo pipefail

IMG="${MIOS_AGENTS_IMAGE:-localhost/mios-agents:latest}"
CTX="/usr/share/mios/agents"
CF="$CTX/Containerfile"
SETTINGS_SOURCE="$CTX/code-server-mobile-settings.json"
SETTINGS_TARGET="/var/lib/mios/agents/.local/share/code-server/User/settings.json"
TOML_GET="/usr/libexec/mios/mios-toml-get"
CSS="/usr/share/mios/themes/code-server-terminal.css"
PATCHER="/usr/libexec/mios/mios-vscode-custom-css"

log() { logger -t mios-agents-firstboot "$*" 2>/dev/null || true; echo "[mios-agents-firstboot] $*" >&2; }

seed_code_server_settings() {
    [ -f "$SETTINGS_SOURCE" ] || return 0

    install -d -m 0755 "$(dirname "$SETTINGS_TARGET")"
    if [ ! -e "$SETTINGS_TARGET" ]; then
        install -m 0644 "$SETTINGS_SOURCE" "$SETTINGS_TARGET"
        log "Seeded portrait code-server settings"
        return 0
    fi

    python3 - "$SETTINGS_SOURCE" "$SETTINGS_TARGET" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
defaults = json.loads(source.read_text(encoding="utf-8"))
settings = json.loads(target.read_text(encoding="utf-8"))
if not isinstance(settings, dict):
    raise ValueError(f"{target} must contain a JSON object")

updated = False
for key, value in defaults.items():
    if key not in settings:
        settings[key] = value
        updated = True

if updated:
    target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY
    log "Merged missing portrait code-server defaults"
}

seed_code_server_extensions() {
    local ext_src="/usr/share/mios/extensions/be5invis.vscode-custom-css"
    local ext_target="/var/lib/mios/agents/.local/share/code-server/extensions/be5invis.vscode-custom-css"
    [ -d "$ext_src" ] || return 0

    install -d -m 0755 "$(dirname "$ext_target")"
    if [ ! -d "$ext_target" ]; then
        cp -r "$ext_src" "$ext_target"
        log "Seeded custom CSS extension into code-server extensions"
    fi
}

# The same layered-loader reads and build-context as miosd run_build_if_missing; an unpinned tag fails.
resolve_build_args() {
    local img tag sb pm
    img="$("$TOML_GET" image.sidecars code_server)"; tag="${img##*:}"
    case "$img" in *:*) ;; *) tag="" ;; esac
    case "$tag" in ""|latest|*/*) log "ERROR: [image.sidecars].code_server '$img' has no pinned tag"; return 1 ;; esac
    sb="$("$TOML_GET" theme.edge code_server_scrollbar_px)"; pm="$("$TOML_GET" theme.edge code_server_perimeter_px)"
    [ -n "$sb" ] && [ -n "$pm" ] || { log "ERROR: [theme.edge] code_server_scrollbar_px/code_server_perimeter_px unresolved"; return 1; }
    BUILD_ARGS=(--build-arg "MIOS_CODE_SERVER_VERSION=$tag" --build-arg "CODE_SERVER_SCROLLBAR_PX=$sb"
                --build-arg "CODE_SERVER_PERIMETER_PX=$pm" --build-context mios=/)
}

seed_code_server_settings
seed_code_server_extensions

if command -v miosd >/dev/null 2>&1; then
    miosd build-if-missing agents
    exit 0
fi

[ -f "$CF" ] || { log "ERROR: $CF missing"; exit 1; }

NEED_BUILD=0
if ! podman image exists "$IMG"; then
    NEED_BUILD=1; log "Image $IMG missing -> build"
else
    _img_epoch="$(date -d "$(podman image inspect -f '{{.Created}}' "$IMG" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    for _src in "$CF" "$CSS" "$PATCHER"; do
        _src_epoch="$(stat -c %Y "$_src" 2>/dev/null || echo 0)"
        if [ "$_img_epoch" -gt 0 ] && [ "$_src_epoch" -gt "$_img_epoch" ]; then
            NEED_BUILD=1; log "$_src newer than image -> rebuild"; break
        fi
    done
    [ "$NEED_BUILD" = 1 ] || log "Image $IMG current; nothing to build"
fi
[ "$NEED_BUILD" = 1 ] || exit 0

resolve_build_args
log "Building $IMG from $CF "
if ! podman build --network=host "${BUILD_ARGS[@]}" -t "$IMG" -f "$CF" "$CTX"; then
    log "ERROR: $IMG build failed. Cleaning up intermediate containers/images"
    podman image prune --force >/dev/null 2>&1 || true
    exit 1
fi
log "Built $IMG"
