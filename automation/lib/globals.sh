#!/usr/bin/env bash
# automation/lib/globals.sh
#
# Single-source-of-truth registry for MiOS-wide constants. Source this
# (transitively via common.sh) instead of hardcoding values in every
# script. Every variable is :-default assigned so an environment
# override always wins -- making this safe to source from any script
# without surprising existing callers.
#
# Categories:
#   VERSION   -- derived from the canonical /VERSION file (or
#                /ctx/VERSION at build time, or /usr/share/mios/VERSION
#                on a deployed host) so a single bump propagates.
#   USERS     -- mios + sidecar service accounts. UIDs/GIDs pinned in
#                /usr/lib/sysusers.d/*.conf; centralized here so shell
#                scripts and Quadlet User= directives can reference
#                the same numbers without re-grepping.
#   IMAGES    -- OCI refs (this image, base image, bib image, the
#                local-build tag).
#   PORTS     -- host loopback ports for every Quadlet/host service,
#                so URL constants below can be derived once.
#   URLS      -- common endpoints (AI, Forgejo, Cockpit, Ollama).
#   REPOS     -- git remotes for the self-replication loop.
#
# Idempotent. Safe to source multiple times.

# ── VERSION ──────────────────────────────────────────────────────────
_mios_resolve_version() {
    local v=""
    if   [[ -n "${MIOS_VERSION:-}" ]];        then v="$MIOS_VERSION"
    elif [[ -f /ctx/VERSION ]];               then v="$(cat /ctx/VERSION)"
    elif [[ -f /usr/share/mios/VERSION ]];    then v="$(cat /usr/share/mios/VERSION)"
    else
        # Walk up from this lib file to find the repo-root VERSION.
        local _root
        _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
        if [[ -n "$_root" && -f "${_root}/VERSION" ]]; then
            v="$(cat "${_root}/VERSION")"
        fi
    fi
    printf '%s' "${v:-0.2.4}" | tr -d '[:space:]'
}
: "${MIOS_VERSION:=$(_mios_resolve_version)}"
export MIOS_VERSION

# ── USERS / GROUPS ───────────────────────────────────────────────────
# Service-account UIDs are reserved in the 800-829 range per
# /usr/lib/sysusers.d/50-mios-services.conf. The login user is uid 1000
# (pinned in /usr/lib/sysusers.d/10-mios.conf so logind XDG_RUNTIME_DIR
# allocation works -- system-uid auto-allocation under 1000 silently
# breaks the Wayland/dbus user session).
: "${MIOS_USER:=mios}"
: "${MIOS_GROUP:=mios}"
: "${MIOS_UID:=1000}"
: "${MIOS_GID:=1000}"

: "${MIOS_FORGE_USER:=mios-forge}"
: "${MIOS_FORGE_UID:=816}"
: "${MIOS_FORGE_GID:=816}"

: "${MIOS_AI_USER:=mios-ai}"
: "${MIOS_AI_UID:=817}"
: "${MIOS_AI_GID:=817}"

: "${MIOS_OLLAMA_USER:=mios-ollama}"
: "${MIOS_OLLAMA_UID:=818}"
: "${MIOS_OLLAMA_GID:=818}"

: "${MIOS_CEPH_USER:=mios-ceph}"
: "${MIOS_CEPH_UID:=819}"
: "${MIOS_CEPH_GID:=819}"

: "${MIOS_SEARXNG_USER:=mios-searxng}"
: "${MIOS_SEARXNG_UID:=818}"
: "${MIOS_SEARXNG_GID:=818}"

: "${MIOS_HERMES_USER:=mios-hermes}"
: "${MIOS_HERMES_UID:=820}"
: "${MIOS_HERMES_GID:=820}"

: "${MIOS_WEBUI_USER:=mios-webui}"
: "${MIOS_WEBUI_UID:=821}"
: "${MIOS_WEBUI_GID:=821}"

# Rootless-container subuid/subgid range. Standard Fedora useradd -m
# allocates 100000:65536; we keep the same so /etc/subuid + /etc/subgid
# stay consistent with stock Fedora workflows.
: "${MIOS_SUBUID_START:=100000}"
: "${MIOS_SUBUID_COUNT:=65536}"

export MIOS_USER MIOS_GROUP MIOS_UID MIOS_GID
export MIOS_FORGE_USER MIOS_FORGE_UID MIOS_FORGE_GID
export MIOS_AI_USER MIOS_AI_UID MIOS_AI_GID
export MIOS_OLLAMA_USER MIOS_OLLAMA_UID MIOS_OLLAMA_GID
export MIOS_CEPH_USER MIOS_CEPH_UID MIOS_CEPH_GID
export MIOS_SEARXNG_USER MIOS_SEARXNG_UID MIOS_SEARXNG_GID
export MIOS_HERMES_USER MIOS_HERMES_UID MIOS_HERMES_GID
export MIOS_WEBUI_USER MIOS_WEBUI_UID MIOS_WEBUI_GID
export MIOS_SUBUID_START MIOS_SUBUID_COUNT

# ── IMAGES ───────────────────────────────────────────────────────────
: "${MIOS_IMAGE_NAME:=ghcr.io/mios-dev/mios}"
: "${MIOS_IMAGE_TAG:=latest}"
: "${MIOS_IMAGE_REF:=${MIOS_IMAGE_NAME}:${MIOS_IMAGE_TAG}}"
: "${MIOS_LOCAL_IMAGE:=localhost/mios:latest}"
: "${MIOS_BASE_IMAGE:=ghcr.io/ublue-os/ucore-hci:stable-nvidia}"
: "${MIOS_BIB_IMAGE:=quay.io/centos-bootc/bootc-image-builder:latest}"
export MIOS_IMAGE_NAME MIOS_IMAGE_TAG MIOS_IMAGE_REF
export MIOS_LOCAL_IMAGE MIOS_BASE_IMAGE MIOS_BIB_IMAGE

# ── PORTS ────────────────────────────────────────────────────────────
: "${MIOS_PORT_SSH:=22}"
: "${MIOS_PORT_FORGE_HTTP:=3000}"
: "${MIOS_PORT_FORGE_SSH:=2222}"
: "${MIOS_PORT_LOCALAI:=8080}"
: "${MIOS_PORT_COCKPIT:=9090}"
: "${MIOS_PORT_OLLAMA:=11434}"
: "${MIOS_PORT_SEARXNG:=8888}"
: "${MIOS_PORT_HERMES:=8642}"
: "${MIOS_PORT_WEBUI:=3030}"
: "${MIOS_PORT_COCKPIT_LINK:=19090}"   # podman-desktop discovery shim
export MIOS_PORT_SSH MIOS_PORT_FORGE_HTTP MIOS_PORT_FORGE_SSH
export MIOS_PORT_LOCALAI MIOS_PORT_COCKPIT MIOS_PORT_OLLAMA
export MIOS_PORT_SEARXNG MIOS_PORT_HERMES MIOS_PORT_WEBUI MIOS_PORT_COCKPIT_LINK

# ── URLS ─────────────────────────────────────────────────────────────
# Derived from PORTS so a single port change propagates. MIOS_AI_ENDPOINT
# is the unified-AI-redirects target (Architectural Law 5).
: "${MIOS_AI_ENDPOINT:=http://localhost:${MIOS_PORT_LOCALAI}/v1}"
: "${MIOS_FORGE_URL:=http://localhost:${MIOS_PORT_FORGE_HTTP}}"
: "${MIOS_COCKPIT_URL:=https://localhost:${MIOS_PORT_COCKPIT}}"
: "${MIOS_OLLAMA_URL:=http://localhost:${MIOS_PORT_OLLAMA}}"
: "${MIOS_SEARXNG_URL:=http://localhost:${MIOS_PORT_SEARXNG}}"
: "${MIOS_HERMES_URL:=http://localhost:${MIOS_PORT_HERMES}/v1}"
: "${MIOS_WEBUI_URL:=http://localhost:${MIOS_PORT_WEBUI}/}"
export MIOS_AI_ENDPOINT MIOS_FORGE_URL MIOS_COCKPIT_URL MIOS_OLLAMA_URL
export MIOS_SEARXNG_URL MIOS_HERMES_URL MIOS_WEBUI_URL

# ── REPOS ────────────────────────────────────────────────────────────
: "${MIOS_REPO_URL:=https://github.com/mios-dev/MiOS.git}"
: "${MIOS_BOOTSTRAP_REPO_URL:=https://github.com/mios-dev/mios-bootstrap.git}"
: "${MIOS_LOCAL_FORGE_REPO:=http://localhost:${MIOS_PORT_FORGE_HTTP}/mios/mios.git}"
export MIOS_REPO_URL MIOS_BOOTSTRAP_REPO_URL MIOS_LOCAL_FORGE_REPO

# ── PATHS / DIRECTORIES ──────────────────────────────────────────────
# /usr/share/mios/* -- vendor, immutable, image-baked
: "${MIOS_SHARE_AI_DIR:=${MIOS_SHARE_DIR}/ai}"
: "${MIOS_SHARE_DISTROBOX_DIR:=${MIOS_SHARE_DIR}/distrobox}"
: "${MIOS_SHARE_BRANDING_DIR:=${MIOS_SHARE_DIR}/branding}"
: "${MIOS_SHARE_FASTFETCH_DIR:=${MIOS_SHARE_DIR}/fastfetch}"
: "${MIOS_SHARE_KB_DIR:=${MIOS_SHARE_DIR}/kb}"
: "${MIOS_SHARE_CONFIGURATOR_DIR:=${MIOS_SHARE_DIR}/configurator}"
: "${MIOS_SHARE_K3S_MANIFESTS_DIR:=${MIOS_SHARE_DIR}/k3s-manifests}"

# /etc/mios/* -- admin override surface
: "${MIOS_ETC_AI_DIR:=${MIOS_ETC_DIR}/ai}"
: "${MIOS_ETC_FORGE_DIR:=${MIOS_ETC_DIR}/forge}"
: "${MIOS_ETC_ENVD_DIR:=${MIOS_ETC_DIR}/env.d}"

# /var/lib/mios/* -- runtime mutable
: "${MIOS_VAR_AI_DIR:=${MIOS_VAR_DIR}/ai}"
: "${MIOS_VAR_MCP_DIR:=${MIOS_VAR_DIR}/mcp}"
: "${MIOS_VAR_BACKUPS_DIR:=${MIOS_VAR_DIR}/backups}"
: "${MIOS_VAR_CACHE_DIR:=${MIOS_VAR_DIR}/cache}"

# /srv/ai/* -- LocalAI bind targets (model store, generated outputs)
: "${MIOS_SRV_AI_DIR:=/srv/ai}"
: "${MIOS_SRV_AI_MODELS_DIR:=${MIOS_SRV_AI_DIR}/models}"
: "${MIOS_SRV_AI_OUTPUTS_DIR:=${MIOS_SRV_AI_DIR}/outputs}"
: "${MIOS_SRV_AI_COLLECTIONS_DIR:=${MIOS_SRV_AI_DIR}/collections}"
: "${MIOS_SRV_AI_MCP_DIR:=${MIOS_SRV_AI_DIR}/mcp}"

# Ollama model store (writable runtime + immutable build-baked seed)
: "${MIOS_OLLAMA_RUNTIME_DIR:=/var/lib/ollama/models}"
: "${MIOS_OLLAMA_SEED_DIR:=/usr/share/ollama/models}"

export MIOS_SHARE_AI_DIR MIOS_SHARE_DISTROBOX_DIR MIOS_SHARE_BRANDING_DIR
export MIOS_SHARE_FASTFETCH_DIR MIOS_SHARE_KB_DIR MIOS_SHARE_CONFIGURATOR_DIR
export MIOS_SHARE_K3S_MANIFESTS_DIR
export MIOS_ETC_AI_DIR MIOS_ETC_FORGE_DIR MIOS_ETC_ENVD_DIR
export MIOS_VAR_AI_DIR MIOS_VAR_MCP_DIR MIOS_VAR_BACKUPS_DIR MIOS_VAR_CACHE_DIR
export MIOS_SRV_AI_DIR MIOS_SRV_AI_MODELS_DIR MIOS_SRV_AI_OUTPUTS_DIR
export MIOS_SRV_AI_COLLECTIONS_DIR MIOS_SRV_AI_MCP_DIR
export MIOS_OLLAMA_RUNTIME_DIR MIOS_OLLAMA_SEED_DIR

# ── FILES ────────────────────────────────────────────────────────────
# mios.toml chain (vendor < host < user; resolved by tools/lib/userenv.sh)
: "${MIOS_TOML_VENDOR:=${MIOS_SHARE_DIR}/mios.toml}"
: "${MIOS_TOML_HOST:=${MIOS_ETC_DIR}/mios.toml}"
: "${MIOS_TOML_USER:=${HOME:-/root}/.config/mios/mios.toml}"

# install.env -- bootstrap-staged identity + AI defaults sourced at runtime
: "${MIOS_INSTALL_ENV:=${MIOS_ETC_DIR}/install.env}"

# Sentinel files (presence => first-boot work already done)
: "${MIOS_FIRSTBOOT_SENTINEL:=${MIOS_VAR_DIR}/.wsl-firstboot-done}"
: "${MIOS_OLLAMA_SENTINEL:=${MIOS_VAR_DIR}/.ollama-firstboot-done}"

# Distrobox aichat config files
: "${MIOS_AICHAT_DISTROBOX_INI:=${MIOS_SHARE_DISTROBOX_DIR}/aichat/distrobox.ini}"
: "${MIOS_AICHAT_CONFIG_DEFAULT:=${MIOS_SHARE_DISTROBOX_DIR}/aichat/config.yaml}"

# Operator-side aichat config (per-user, seeded from default on first run)
: "${MIOS_AICHAT_USER_CONFIG:=${HOME:-/root}/.config/aichat/config.yaml}"

# AI system prompt + MCP registry
: "${MIOS_AI_SYSTEM_PROMPT:=${MIOS_SHARE_AI_DIR}/system.md}"
: "${MIOS_MCP_REGISTRY:=${MIOS_SHARE_AI_DIR}/v1/mcp.json}"

# Bootstrap-time saved env (persists operator selections between runs)
: "${MIOS_BUILD_ENV_FILE:=${HOME:-/root}/.config/mios/mios-build.env}"

export MIOS_TOML_VENDOR MIOS_TOML_HOST MIOS_TOML_USER
export MIOS_INSTALL_ENV MIOS_FIRSTBOOT_SENTINEL MIOS_OLLAMA_SENTINEL
export MIOS_AICHAT_DISTROBOX_INI MIOS_AICHAT_CONFIG_DEFAULT MIOS_AICHAT_USER_CONFIG
export MIOS_AI_SYSTEM_PROMPT MIOS_MCP_REGISTRY MIOS_BUILD_ENV_FILE

# ── SYSTEMD UNITS ────────────────────────────────────────────────────
# Quadlet-generated service names (one per .container/.build/.image file)
: "${MIOS_UNIT_AI:=mios-ai.service}"
: "${MIOS_UNIT_FORGE:=mios-forge.service}"
: "${MIOS_UNIT_FORGE_RUNNER:=mios-forgejo-runner.service}"
: "${MIOS_UNIT_OLLAMA:=ollama.service}"
: "${MIOS_UNIT_CEPH:=mios-ceph.service}"
: "${MIOS_UNIT_K3S:=mios-k3s.service}"
: "${MIOS_UNIT_AICHAT_BUILD:=mios-aichat-build.service}"
: "${MIOS_UNIT_AICHAT_IMAGE:=mios-aichat-image.service}"
: "${MIOS_UNIT_COCKPIT_LINK:=mios-cockpit-link.service}"
: "${MIOS_UNIT_SEARXNG:=mios-searxng.service}"
: "${MIOS_UNIT_HERMES:=mios-hermes.service}"
: "${MIOS_UNIT_WEBUI:=mios-webui.service}"
: "${MIOS_UNIT_HERMES_FIRSTBOOT:=mios-hermes-firstboot.service}"

# Hand-written units
: "${MIOS_UNIT_FIRSTBOOT_TARGET:=mios-firstboot.target}"
: "${MIOS_UNIT_OLLAMA_FIRSTBOOT:=mios-ollama-firstboot.service}"
: "${MIOS_UNIT_WSL_FIRSTBOOT:=mios-wsl-firstboot.service}"
: "${MIOS_UNIT_USER_SESSION:=user@${MIOS_UID}.service}"

export MIOS_UNIT_AI MIOS_UNIT_FORGE MIOS_UNIT_FORGE_RUNNER MIOS_UNIT_OLLAMA
export MIOS_UNIT_CEPH MIOS_UNIT_K3S MIOS_UNIT_AICHAT_BUILD MIOS_UNIT_AICHAT_IMAGE
export MIOS_UNIT_COCKPIT_LINK MIOS_UNIT_SEARXNG MIOS_UNIT_FIRSTBOOT_TARGET
export MIOS_UNIT_HERMES MIOS_UNIT_WEBUI MIOS_UNIT_HERMES_FIRSTBOOT
export MIOS_UNIT_OLLAMA_FIRSTBOOT MIOS_UNIT_WSL_FIRSTBOOT MIOS_UNIT_USER_SESSION

# ── CONTAINERS / DISTROBOX ───────────────────────────────────────────
: "${MIOS_DISTROBOX_AICHAT:=mios-aichat}"
: "${MIOS_CONTAINER_AICHAT_IMAGE:=localhost/mios/aichat:latest}"
: "${MIOS_CONTAINER_FORGE_IMAGE:=codeberg.org/forgejo/forgejo:12}"
: "${MIOS_CONTAINER_LOCALAI_IMAGE:=docker.io/localai/localai:latest}"
: "${MIOS_CONTAINER_OLLAMA_IMAGE:=docker.io/ollama/ollama:latest}"
: "${MIOS_CONTAINER_SEARXNG_IMAGE:=docker.io/searxng/searxng:latest}"
: "${MIOS_CONTAINER_HERMES_IMAGE:=docker.io/nousresearch/hermes-agent:latest}"
: "${MIOS_CONTAINER_WEBUI_IMAGE:=docker.io/openwebui/open-webui:latest}"

export MIOS_DISTROBOX_AICHAT MIOS_CONTAINER_AICHAT_IMAGE
export MIOS_CONTAINER_FORGE_IMAGE MIOS_CONTAINER_LOCALAI_IMAGE
export MIOS_CONTAINER_OLLAMA_IMAGE MIOS_CONTAINER_SEARXNG_IMAGE
export MIOS_CONTAINER_HERMES_IMAGE MIOS_CONTAINER_WEBUI_IMAGE

# ── COLOR PALETTE ────────────────────────────────────────────────────
# Hokusai + operator-neutrals palette. Resolved from mios.toml [colors]
# at runtime by tools/lib/userenv.sh (operator overrides win); these are
# the vendor defaults so any consumer that doesn't go through userenv
# still gets a coherent palette. The configurator HTML, profile.d color
# emitter (/etc/profile.d/mios-colors.sh), and fastfetch all reference
# these names.
: "${MIOS_COLOR_BG:=#282262}"        # deep indigo  (Hokusai sky)
: "${MIOS_COLOR_FG:=#E7DFD3}"        # foam cream
: "${MIOS_COLOR_ACCENT:=#1A407F}"    # operator blue
: "${MIOS_COLOR_CURSOR:=#F35C15}"    # sunset orange
: "${MIOS_COLOR_SUCCESS:=#3E7765}"   # wave green
: "${MIOS_COLOR_WARNING:=#F35C15}"   # sunset orange
: "${MIOS_COLOR_ERROR:=#DC271B}"     # coral red
: "${MIOS_COLOR_INFO:=#1A407F}"      # operator blue
: "${MIOS_COLOR_MUTED:=#948E8E}"     # warm grey
: "${MIOS_COLOR_SUBTLE:=#B7C9D7}"    # pale blue-grey
: "${MIOS_COLOR_EARTH:=#734F39}"     # brown
: "${MIOS_COLOR_SILVER:=#E0E0E0}"    # operator silver

export MIOS_COLOR_BG MIOS_COLOR_FG MIOS_COLOR_ACCENT MIOS_COLOR_CURSOR
export MIOS_COLOR_SUCCESS MIOS_COLOR_WARNING MIOS_COLOR_ERROR MIOS_COLOR_INFO
export MIOS_COLOR_MUTED MIOS_COLOR_SUBTLE MIOS_COLOR_EARTH MIOS_COLOR_SILVER
