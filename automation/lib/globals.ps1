# automation/lib/globals.ps1
#
# PowerShell sibling of automation/lib/globals.sh. Single registry for
# MiOS-wide constants (VERSION, USERS, IMAGES, PORTS, URLS, REPOS).
# Dot-source from any PowerShell entry point:
#
#     . (Join-Path $PSScriptRoot 'automation/lib/globals.ps1')
#
# Variables land in the caller's $script: scope (PowerShell scoping
# rules: dot-sourced scripts run in the caller's scope, so everything
# below is visible to the caller without further ceremony). Override
# any constant with an environment variable BEFORE dot-sourcing -- e.g.
# `$env:MIOS_VERSION = '0.3.0-rc1'; . globals.ps1`.

# ── VERSION ──────────────────────────────────────────────────────────
function Resolve-MiosVersion {
    if ($env:MIOS_VERSION) { return ([string]$env:MIOS_VERSION).Trim() }
    foreach ($p in @(
        '/ctx/VERSION',
        '/usr/share/mios/VERSION',
        (Join-Path $PSScriptRoot '..\..\VERSION')
    )) {
        if ($p -and (Test-Path $p)) {
            $v = (Get-Content $p -EA SilentlyContinue | Out-String).Trim()
            if ($v) { return $v }
        }
    }
    return '0.2.4'
}
$script:MIOS_VERSION = Resolve-MiosVersion

# ── USERS / GROUPS ───────────────────────────────────────────────────
$script:MIOS_USER         = if ($env:MIOS_USER)         { $env:MIOS_USER }         else { 'mios' }
$script:MIOS_GROUP        = if ($env:MIOS_GROUP)        { $env:MIOS_GROUP }        else { 'mios' }
$script:MIOS_UID          = if ($env:MIOS_UID)          { [int]$env:MIOS_UID }     else { 1000 }
$script:MIOS_GID          = if ($env:MIOS_GID)          { [int]$env:MIOS_GID }     else { 1000 }

$script:MIOS_FORGE_USER   = if ($env:MIOS_FORGE_USER)   { $env:MIOS_FORGE_USER }   else { 'mios-forge' }
$script:MIOS_FORGE_UID    = if ($env:MIOS_FORGE_UID)    { [int]$env:MIOS_FORGE_UID } else { 816 }
$script:MIOS_FORGE_GID    = if ($env:MIOS_FORGE_GID)    { [int]$env:MIOS_FORGE_GID } else { 816 }

$script:MIOS_AI_USER      = if ($env:MIOS_AI_USER)      { $env:MIOS_AI_USER }      else { 'mios-ai' }
$script:MIOS_AI_UID       = if ($env:MIOS_AI_UID)       { [int]$env:MIOS_AI_UID }  else { 817 }
$script:MIOS_AI_GID       = if ($env:MIOS_AI_GID)       { [int]$env:MIOS_AI_GID }  else { 817 }

$script:MIOS_OLLAMA_USER  = if ($env:MIOS_OLLAMA_USER)  { $env:MIOS_OLLAMA_USER }  else { 'mios-ollama' }
# 815 -- MUST match usr/lib/sysusers.d/50-mios-services.conf. Was 818
# (typo, collided with mios-searxng). Caused ollama container to start
# as UID 818 and `mkdir /var/lib/ollama/.ollama` -> permission denied
# because the host bind-mount is chowned to UID 815 (mios-ollama).
$script:MIOS_OLLAMA_UID   = if ($env:MIOS_OLLAMA_UID)   { [int]$env:MIOS_OLLAMA_UID } else { 815 }
$script:MIOS_OLLAMA_GID   = if ($env:MIOS_OLLAMA_GID)   { [int]$env:MIOS_OLLAMA_GID } else { 815 }

$script:MIOS_CEPH_USER    = if ($env:MIOS_CEPH_USER)    { $env:MIOS_CEPH_USER }    else { 'mios-ceph' }
$script:MIOS_CEPH_UID     = if ($env:MIOS_CEPH_UID)     { [int]$env:MIOS_CEPH_UID }  else { 819 }
$script:MIOS_CEPH_GID     = if ($env:MIOS_CEPH_GID)     { [int]$env:MIOS_CEPH_GID }  else { 819 }

$script:MIOS_SEARXNG_USER = if ($env:MIOS_SEARXNG_USER) { $env:MIOS_SEARXNG_USER } else { 'mios-searxng' }
$script:MIOS_SEARXNG_UID  = if ($env:MIOS_SEARXNG_UID)  { [int]$env:MIOS_SEARXNG_UID } else { 818 }
$script:MIOS_SEARXNG_GID  = if ($env:MIOS_SEARXNG_GID)  { [int]$env:MIOS_SEARXNG_GID } else { 818 }

$script:MIOS_HERMES_USER  = if ($env:MIOS_HERMES_USER)  { $env:MIOS_HERMES_USER }  else { 'mios-hermes' }
$script:MIOS_HERMES_UID   = if ($env:MIOS_HERMES_UID)   { [int]$env:MIOS_HERMES_UID } else { 820 }
$script:MIOS_HERMES_GID   = if ($env:MIOS_HERMES_GID)   { [int]$env:MIOS_HERMES_GID } else { 820 }

$script:MIOS_WEBUI_USER   = if ($env:MIOS_WEBUI_USER)   { $env:MIOS_WEBUI_USER }   else { 'mios-webui' }
$script:MIOS_WEBUI_UID    = if ($env:MIOS_WEBUI_UID)    { [int]$env:MIOS_WEBUI_UID } else { 821 }
$script:MIOS_WEBUI_GID    = if ($env:MIOS_WEBUI_GID)    { [int]$env:MIOS_WEBUI_GID } else { 821 }

$script:MIOS_SUBUID_START = if ($env:MIOS_SUBUID_START) { [int]$env:MIOS_SUBUID_START } else { 100000 }
$script:MIOS_SUBUID_COUNT = if ($env:MIOS_SUBUID_COUNT) { [int]$env:MIOS_SUBUID_COUNT } else { 65536 }

# ── IMAGES ───────────────────────────────────────────────────────────
$script:MIOS_IMAGE_NAME   = if ($env:MIOS_IMAGE_NAME)   { $env:MIOS_IMAGE_NAME }   else { 'ghcr.io/mios-dev/mios' }
$script:MIOS_IMAGE_TAG    = if ($env:MIOS_IMAGE_TAG)    { $env:MIOS_IMAGE_TAG }    else { 'latest' }
$script:MIOS_IMAGE_REF    = if ($env:MIOS_IMAGE_REF)    { $env:MIOS_IMAGE_REF }    else { "$($script:MIOS_IMAGE_NAME):$($script:MIOS_IMAGE_TAG)" }
$script:MIOS_LOCAL_IMAGE  = if ($env:MIOS_LOCAL_IMAGE)  { $env:MIOS_LOCAL_IMAGE }  else { 'localhost/mios:latest' }
$script:MIOS_BASE_IMAGE   = if ($env:MIOS_BASE_IMAGE)   { $env:MIOS_BASE_IMAGE }   else { 'ghcr.io/ublue-os/ucore-hci:stable-nvidia' }
$script:MIOS_BIB_IMAGE    = if ($env:MIOS_BIB_IMAGE)    { $env:MIOS_BIB_IMAGE }    else { 'quay.io/centos-bootc/bootc-image-builder:latest' }

# ── PORTS ────────────────────────────────────────────────────────────
$script:MIOS_PORT_SSH           = if ($env:MIOS_PORT_SSH)           { [int]$env:MIOS_PORT_SSH }           else { 22 }
$script:MIOS_PORT_FORGE_HTTP    = if ($env:MIOS_PORT_FORGE_HTTP)    { [int]$env:MIOS_PORT_FORGE_HTTP }    else { 3000 }
$script:MIOS_PORT_FORGE_SSH     = if ($env:MIOS_PORT_FORGE_SSH)     { [int]$env:MIOS_PORT_FORGE_SSH }     else { 2222 }
$script:MIOS_PORT_LOCALAI       = if ($env:MIOS_PORT_LOCALAI)       { [int]$env:MIOS_PORT_LOCALAI }       else { 8080 }
$script:MIOS_PORT_COCKPIT       = if ($env:MIOS_PORT_COCKPIT)       { [int]$env:MIOS_PORT_COCKPIT }       else { 9090 }
$script:MIOS_PORT_OLLAMA        = if ($env:MIOS_PORT_OLLAMA)        { [int]$env:MIOS_PORT_OLLAMA }        else { 11434 }
$script:MIOS_PORT_SEARXNG       = if ($env:MIOS_PORT_SEARXNG)       { [int]$env:MIOS_PORT_SEARXNG }       else { 8888 }
$script:MIOS_PORT_HERMES        = if ($env:MIOS_PORT_HERMES)        { [int]$env:MIOS_PORT_HERMES }        else { 8642 }
$script:MIOS_PORT_WEBUI         = if ($env:MIOS_PORT_WEBUI)         { [int]$env:MIOS_PORT_WEBUI }         else { 3030 }
$script:MIOS_PORT_COCKPIT_LINK  = if ($env:MIOS_PORT_COCKPIT_LINK)  { [int]$env:MIOS_PORT_COCKPIT_LINK }  else { 19090 }

# ── URLS ─────────────────────────────────────────────────────────────
$script:MIOS_AI_ENDPOINT  = if ($env:MIOS_AI_ENDPOINT)  { $env:MIOS_AI_ENDPOINT }  else { "http://localhost:$($script:MIOS_PORT_LOCALAI)/v1" }
$script:MIOS_FORGE_URL    = if ($env:MIOS_FORGE_URL)    { $env:MIOS_FORGE_URL }    else { "http://localhost:$($script:MIOS_PORT_FORGE_HTTP)" }
$script:MIOS_COCKPIT_URL  = if ($env:MIOS_COCKPIT_URL)  { $env:MIOS_COCKPIT_URL }  else { "https://localhost:$($script:MIOS_PORT_COCKPIT)" }
$script:MIOS_OLLAMA_URL   = if ($env:MIOS_OLLAMA_URL)   { $env:MIOS_OLLAMA_URL }   else { "http://localhost:$($script:MIOS_PORT_OLLAMA)" }
$script:MIOS_SEARXNG_URL  = if ($env:MIOS_SEARXNG_URL)  { $env:MIOS_SEARXNG_URL }  else { "http://localhost:$($script:MIOS_PORT_SEARXNG)" }
$script:MIOS_HERMES_URL   = if ($env:MIOS_HERMES_URL)   { $env:MIOS_HERMES_URL }   else { "http://localhost:$($script:MIOS_PORT_HERMES)/v1" }
$script:MIOS_WEBUI_URL    = if ($env:MIOS_WEBUI_URL)    { $env:MIOS_WEBUI_URL }    else { "http://localhost:$($script:MIOS_PORT_WEBUI)/" }

# ── REPOS ────────────────────────────────────────────────────────────
$script:MIOS_REPO_URL           = if ($env:MIOS_REPO_URL)           { $env:MIOS_REPO_URL }           else { 'https://github.com/mios-dev/MiOS.git' }
$script:MIOS_BOOTSTRAP_REPO_URL = if ($env:MIOS_BOOTSTRAP_REPO_URL) { $env:MIOS_BOOTSTRAP_REPO_URL } else { 'https://github.com/mios-dev/mios-bootstrap.git' }
$script:MIOS_LOCAL_FORGE_REPO   = if ($env:MIOS_LOCAL_FORGE_REPO)   { $env:MIOS_LOCAL_FORGE_REPO }   else { "http://localhost:$($script:MIOS_PORT_FORGE_HTTP)/mios/mios.git" }

# ── PATHS / DIRECTORIES ──────────────────────────────────────────────
# Vendor (deployed image)
$script:MIOS_USR_DIR                    = '/usr/lib/mios'
$script:MIOS_LIBEXEC_DIR                = '/usr/libexec/mios'
$script:MIOS_SHARE_DIR                  = '/usr/share/mios'
$script:MIOS_SHARE_AI_DIR               = "$($script:MIOS_SHARE_DIR)/ai"
$script:MIOS_SHARE_DISTROBOX_DIR        = "$($script:MIOS_SHARE_DIR)/distrobox"
$script:MIOS_SHARE_BRANDING_DIR         = "$($script:MIOS_SHARE_DIR)/branding"
$script:MIOS_SHARE_FASTFETCH_DIR        = "$($script:MIOS_SHARE_DIR)/fastfetch"
$script:MIOS_SHARE_KB_DIR               = "$($script:MIOS_SHARE_DIR)/kb"
$script:MIOS_SHARE_CONFIGURATOR_DIR     = "$($script:MIOS_SHARE_DIR)/configurator"
$script:MIOS_SHARE_K3S_MANIFESTS_DIR    = "$($script:MIOS_SHARE_DIR)/k3s-manifests"
# Admin overrides
$script:MIOS_ETC_DIR                    = '/etc/mios'
$script:MIOS_ETC_AI_DIR                 = "$($script:MIOS_ETC_DIR)/ai"
$script:MIOS_ETC_FORGE_DIR              = "$($script:MIOS_ETC_DIR)/forge"
$script:MIOS_ETC_ENVD_DIR               = "$($script:MIOS_ETC_DIR)/env.d"
# Runtime mutable
$script:MIOS_VAR_DIR                    = '/var/lib/mios'
$script:MIOS_VAR_AI_DIR                 = "$($script:MIOS_VAR_DIR)/ai"
$script:MIOS_VAR_MCP_DIR                = "$($script:MIOS_VAR_DIR)/mcp"
$script:MIOS_VAR_BACKUPS_DIR            = "$($script:MIOS_VAR_DIR)/backups"
$script:MIOS_VAR_CACHE_DIR              = "$($script:MIOS_VAR_DIR)/cache"
# LocalAI bind targets
$script:MIOS_SRV_AI_DIR                 = '/srv/ai'
$script:MIOS_SRV_AI_MODELS_DIR          = "$($script:MIOS_SRV_AI_DIR)/models"
$script:MIOS_SRV_AI_OUTPUTS_DIR         = "$($script:MIOS_SRV_AI_DIR)/outputs"
$script:MIOS_SRV_AI_COLLECTIONS_DIR     = "$($script:MIOS_SRV_AI_DIR)/collections"
$script:MIOS_SRV_AI_MCP_DIR             = "$($script:MIOS_SRV_AI_DIR)/mcp"
# Ollama
$script:MIOS_OLLAMA_RUNTIME_DIR         = '/var/lib/ollama/models'
$script:MIOS_OLLAMA_SEED_DIR            = '/usr/share/ollama/models'
# Windows-side dev paths
$script:MIOS_WIN_APPDATA_DIR            = if ($env:APPDATA)      { Join-Path $env:APPDATA 'MiOS' }      else { $null }
$script:MIOS_WIN_DOCS_DIR               = if ($env:USERPROFILE)  { Join-Path $env:USERPROFILE 'Documents\MiOS' } else { $null }
$script:MIOS_WIN_REPO_DIR               = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'MiOS\repo' }     else { $null }

# ── FILES ────────────────────────────────────────────────────────────
# mios.toml chain (vendor < host < user)
$script:MIOS_TOML_VENDOR        = "$($script:MIOS_SHARE_DIR)/mios.toml"
$script:MIOS_TOML_HOST          = "$($script:MIOS_ETC_DIR)/mios.toml"
$script:MIOS_TOML_USER          = if ($env:HOME) { "$env:HOME/.config/mios/mios.toml" } else { '~/.config/mios/mios.toml' }
$script:MIOS_INSTALL_ENV        = "$($script:MIOS_ETC_DIR)/install.env"
$script:MIOS_FIRSTBOOT_SENTINEL = "$($script:MIOS_VAR_DIR)/.wsl-firstboot-done"
$script:MIOS_OLLAMA_SENTINEL    = "$($script:MIOS_VAR_DIR)/.ollama-firstboot-done"
$script:MIOS_AICHAT_DISTROBOX_INI    = "$($script:MIOS_SHARE_DISTROBOX_DIR)/aichat/distrobox.ini"
$script:MIOS_AICHAT_CONFIG_DEFAULT   = "$($script:MIOS_SHARE_DISTROBOX_DIR)/aichat/config.yaml"
$script:MIOS_AICHAT_USER_CONFIG      = if ($env:HOME) { "$env:HOME/.config/aichat/config.yaml" } else { '~/.config/aichat/config.yaml' }
$script:MIOS_AI_SYSTEM_PROMPT        = "$($script:MIOS_SHARE_AI_DIR)/system.md"
$script:MIOS_MCP_REGISTRY            = "$($script:MIOS_SHARE_AI_DIR)/v1/mcp.json"
$script:MIOS_BUILD_ENV_FILE          = if ($env:HOME) { "$env:HOME/.config/mios/mios-build.env" } else { '~/.config/mios/mios-build.env' }

# ── SYSTEMD UNITS ────────────────────────────────────────────────────
$script:MIOS_UNIT_AI                = 'mios-ai.service'
$script:MIOS_UNIT_FORGE             = 'mios-forge.service'
$script:MIOS_UNIT_FORGE_RUNNER      = 'mios-forgejo-runner.service'
$script:MIOS_UNIT_OLLAMA            = 'ollama.service'
$script:MIOS_UNIT_CEPH              = 'mios-ceph.service'
$script:MIOS_UNIT_K3S               = 'mios-k3s.service'
$script:MIOS_UNIT_AICHAT_BUILD      = 'mios-aichat-build.service'
$script:MIOS_UNIT_AICHAT_IMAGE      = 'mios-aichat-image.service'
$script:MIOS_UNIT_COCKPIT_LINK      = 'mios-cockpit-link.service'
$script:MIOS_UNIT_SEARXNG           = 'mios-searxng.service'
$script:MIOS_UNIT_HERMES            = 'mios-hermes.service'
$script:MIOS_UNIT_WEBUI             = 'mios-webui.service'
$script:MIOS_UNIT_HERMES_FIRSTBOOT  = 'mios-hermes-firstboot.service'
$script:MIOS_UNIT_FIRSTBOOT_TARGET  = 'mios-firstboot.target'
$script:MIOS_UNIT_OLLAMA_FIRSTBOOT  = 'mios-ollama-firstboot.service'
$script:MIOS_UNIT_WSL_FIRSTBOOT     = 'mios-wsl-firstboot.service'
$script:MIOS_UNIT_USER_SESSION      = "user@$($script:MIOS_UID).service"

# ── CONTAINERS / DISTROBOX ───────────────────────────────────────────
$script:MIOS_DISTROBOX_AICHAT           = 'mios-aichat'
$script:MIOS_CONTAINER_AICHAT_IMAGE     = 'localhost/mios/aichat:latest'
$script:MIOS_CONTAINER_FORGE_IMAGE      = 'codeberg.org/forgejo/forgejo:12'
$script:MIOS_CONTAINER_LOCALAI_IMAGE    = 'docker.io/localai/localai:latest'
$script:MIOS_CONTAINER_OLLAMA_IMAGE     = 'docker.io/ollama/ollama:latest'
$script:MIOS_CONTAINER_SEARXNG_IMAGE    = 'docker.io/searxng/searxng:latest'
$script:MIOS_CONTAINER_HERMES_IMAGE     = 'docker.io/nousresearch/hermes-agent:latest'
$script:MIOS_CONTAINER_WEBUI_IMAGE      = 'docker.io/openwebui/open-webui:latest'

# ── COLOR PALETTE ────────────────────────────────────────────────────
# Hokusai + operator-neutrals palette. Vendor defaults; resolved from
# mios.toml [colors] at runtime by tools/lib/userenv.sh (operator
# overrides win). The configurator HTML and other consumers reference
# these by name. Override any single token via $env:MIOS_COLOR_*.
$script:MIOS_COLOR_BG       = if ($env:MIOS_COLOR_BG)       { $env:MIOS_COLOR_BG }       else { '#282262' }
$script:MIOS_COLOR_FG       = if ($env:MIOS_COLOR_FG)       { $env:MIOS_COLOR_FG }       else { '#E7DFD3' }
$script:MIOS_COLOR_ACCENT   = if ($env:MIOS_COLOR_ACCENT)   { $env:MIOS_COLOR_ACCENT }   else { '#1A407F' }
$script:MIOS_COLOR_CURSOR   = if ($env:MIOS_COLOR_CURSOR)   { $env:MIOS_COLOR_CURSOR }   else { '#F35C15' }
$script:MIOS_COLOR_SUCCESS  = if ($env:MIOS_COLOR_SUCCESS)  { $env:MIOS_COLOR_SUCCESS }  else { '#3E7765' }
$script:MIOS_COLOR_WARNING  = if ($env:MIOS_COLOR_WARNING)  { $env:MIOS_COLOR_WARNING }  else { '#F35C15' }
$script:MIOS_COLOR_ERROR    = if ($env:MIOS_COLOR_ERROR)    { $env:MIOS_COLOR_ERROR }    else { '#DC271B' }
$script:MIOS_COLOR_INFO     = if ($env:MIOS_COLOR_INFO)     { $env:MIOS_COLOR_INFO }     else { '#1A407F' }
$script:MIOS_COLOR_MUTED    = if ($env:MIOS_COLOR_MUTED)    { $env:MIOS_COLOR_MUTED }    else { '#948E8E' }
$script:MIOS_COLOR_SUBTLE   = if ($env:MIOS_COLOR_SUBTLE)   { $env:MIOS_COLOR_SUBTLE }   else { '#B7C9D7' }
$script:MIOS_COLOR_EARTH    = if ($env:MIOS_COLOR_EARTH)    { $env:MIOS_COLOR_EARTH }    else { '#734F39' }
$script:MIOS_COLOR_SILVER   = if ($env:MIOS_COLOR_SILVER)   { $env:MIOS_COLOR_SILVER }   else { '#E0E0E0' }
