#!/usr/bin/env bash
# automation/15-render-quadlets.sh
# ----------------------------------------------------------------------------
# In-place rendering of Quadlet container files: walks the deployed
# Quadlet directories and substitutes ${MIOS_*} placeholders with the
# values resolved from the layered mios.toml overlay (vendor < host <
# user) via tools/lib/userenv.sh. The placeholders use shell-style
# `${VAR:-default}` syntax so the source files remain valid Quadlet
# syntax (systemd Quadlet v257+ would substitute via EnvironmentFile=
# but most fields — Image=, User=, Group=, PublishPort=, Network= —
# don't support env-var substitution at unit-load time). This step
# resolves them once at image build time and bakes the values in.
#
# Per the TOML-as-singular-SSOT directive: editing mios.toml flows
# through to every Quadlet without touching the .container files.
# Hardcoded literals in .container files that COULD source from
# mios.toml are bugs — lift them to ${MIOS_*} placeholders + add the
# corresponding [services.<svc>] / [image.sidecars] / [ports] keys.
# ----------------------------------------------------------------------------
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "[15-render-quadlets] Rendering Quadlet placeholders from mios.toml..."

# Quadlet search paths: every directory systemd-generator-quadlet scans
# (per `man quadlet`). We walk them all so any .container, .network,
# .volume, .pod, .image, or .build file with ${MIOS_*} placeholders
# gets resolved.
QUADLET_DIRS=(
    /etc/containers/systemd
    /etc/containers/systemd/users
    /usr/share/containers/systemd
    /usr/share/containers/systemd/users
)

# envsubst is part of gettext; available in every Fedora/CentOS/RHEL
# bootc base. Fall back to a portable shell helper if not.
_render_with_envsubst() {
    local f="$1"
    # shellcheck disable=SC2016
    envsubst '${MIOS_LOCALAI_IMAGE} ${MIOS_K3S_IMAGE} ${MIOS_CEPH_IMAGE} ${MIOS_FORGE_IMAGE} ${MIOS_SEARXNG_IMAGE} ${MIOS_HERMES_IMAGE} ${MIOS_WEBUI_IMAGE} ${MIOS_OLLAMA_IMAGE} ${MIOS_GUACAMOLE_IMAGE} ${MIOS_BIB_ALPINE_IMAGE} ${MIOS_PORT_SSH} ${MIOS_PORT_FORGE_HTTP} ${MIOS_PORT_FORGE_SSH} ${MIOS_PORT_LOCALAI} ${MIOS_PORT_COCKPIT} ${MIOS_PORT_COCKPIT_LINK} ${MIOS_PORT_OLLAMA} ${MIOS_PORT_SEARXNG} ${MIOS_PORT_HERMES} ${MIOS_PORT_WEBUI} ${MIOS_K3S_API_PORT} ${MIOS_GUACAMOLE_PORT} ${MIOS_CEPH_DASHBOARD_PORT} ${MIOS_RDP_PORT} ${MIOS_FORGE_USER} ${MIOS_FORGE_UID} ${MIOS_FORGE_GID} ${MIOS_LOCALAI_USER} ${MIOS_LOCALAI_UID} ${MIOS_LOCALAI_GID} ${MIOS_SEARXNG_USER} ${MIOS_SEARXNG_UID} ${MIOS_SEARXNG_GID} ${MIOS_CEPH_USER} ${MIOS_CEPH_UID} ${MIOS_CEPH_GID} ${MIOS_HERMES_USER} ${MIOS_HERMES_UID} ${MIOS_HERMES_GID} ${MIOS_WEBUI_USER} ${MIOS_WEBUI_UID} ${MIOS_WEBUI_GID} ${MIOS_QUADLET_NETWORK} ${MIOS_QUADLET_SUBNET} ${MIOS_AI_DIR} ${MIOS_AI_MODELS_DIR} ${MIOS_AI_MCP_DIR}' < "$f"
}

# Bash-only fallback for hosts without envsubst. Walks the same allow-
# listed env vars and does sed-style ${VAR:-default} expansion.
_render_with_bash() {
    local f="$1"
    # Read the file, expand only ${MIOS_*} placeholders. Use eval-with-
    # double-quotes against a controlled variable list so we can't
    # accidentally execute embedded $(...) command substitutions in the
    # source file. The Quadlet allowlist below mirrors envsubst above.
    local content
    content="$(cat "$f")"
    # shellcheck disable=SC2016
    for var in MIOS_LOCALAI_IMAGE MIOS_K3S_IMAGE MIOS_CEPH_IMAGE MIOS_FORGE_IMAGE \
               MIOS_SEARXNG_IMAGE MIOS_HERMES_IMAGE MIOS_WEBUI_IMAGE \
               MIOS_OLLAMA_IMAGE MIOS_GUACAMOLE_IMAGE MIOS_BIB_ALPINE_IMAGE \
               MIOS_PORT_SSH MIOS_PORT_FORGE_HTTP MIOS_PORT_FORGE_SSH MIOS_PORT_LOCALAI \
               MIOS_PORT_COCKPIT MIOS_PORT_COCKPIT_LINK MIOS_PORT_OLLAMA MIOS_PORT_SEARXNG \
               MIOS_PORT_HERMES MIOS_PORT_WEBUI MIOS_K3S_API_PORT MIOS_GUACAMOLE_PORT \
               MIOS_CEPH_DASHBOARD_PORT MIOS_RDP_PORT \
               MIOS_FORGE_USER MIOS_FORGE_UID MIOS_FORGE_GID \
               MIOS_LOCALAI_USER MIOS_LOCALAI_UID MIOS_LOCALAI_GID \
               MIOS_SEARXNG_USER MIOS_SEARXNG_UID MIOS_SEARXNG_GID \
               MIOS_CEPH_USER MIOS_CEPH_UID MIOS_CEPH_GID \
               MIOS_HERMES_USER MIOS_HERMES_UID MIOS_HERMES_GID \
               MIOS_WEBUI_USER MIOS_WEBUI_UID MIOS_WEBUI_GID \
               MIOS_QUADLET_NETWORK MIOS_QUADLET_SUBNET \
               MIOS_AI_DIR MIOS_AI_MODELS_DIR MIOS_AI_MCP_DIR; do
        local val="${!var:-}"
        # ${VAR:-default} form: expand the default if VAR is empty
        content="${content//\$\{${var}\}/${val}}"
        # ${VAR:-default} placeholders: capture default and expand
        while [[ "$content" =~ \$\{${var}:-([^}]*)\} ]]; do
            local default="${BASH_REMATCH[1]}"
            local replacement="${val:-$default}"
            content="${content//${BASH_REMATCH[0]}/${replacement}}"
        done
    done
    printf '%s' "$content"
}

if command -v envsubst >/dev/null 2>&1; then
    _renderer=_render_with_envsubst
else
    echo "[15-render-quadlets] envsubst not found -- using bash fallback"
    _renderer=_render_with_bash
fi

rendered_count=0
skipped_count=0
for dir in "${QUADLET_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' f; do
        # Only rewrite files that actually contain a ${MIOS_*}
        # placeholder; idempotent re-runs leave already-rendered files
        # untouched (so this script is safe in iterative bootc upgrades).
        if ! grep -q '\${MIOS_' "$f" 2>/dev/null; then
            skipped_count=$((skipped_count + 1))
            continue
        fi
        local_tmp="$(mktemp)"
        $_renderer "$f" > "$local_tmp"
        # Only replace if the rendered content differs (avoids touching
        # the mtime when there's no change, which keeps systemd's
        # daemon-reload no-ops free).
        if ! cmp -s "$f" "$local_tmp"; then
            mv "$local_tmp" "$f"
            chmod 0644 "$f"
            echo "[15-render-quadlets]   rendered: $f"
            rendered_count=$((rendered_count + 1))
        else
            rm -f "$local_tmp"
        fi
    done < <(find "$dir" -maxdepth 2 -type f \( -name '*.container' -o -name '*.network' -o -name '*.volume' -o -name '*.pod' -o -name '*.image' -o -name '*.build' \) -print0 2>/dev/null)
done

echo "[15-render-quadlets] Done -- rendered $rendered_count, skipped $skipped_count (no placeholders)"
