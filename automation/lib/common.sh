#!/usr/bin/env bash
# ============================================================================
# automation/lib/common.sh
# ----------------------------------------------------------------------------
# Shared helpers for 'MiOS' build scripts.
# Safe to source multiple times (idempotent).
# ============================================================================

# shellcheck source=lib/masking.sh
source "$(dirname "${BASH_SOURCE[0]}")/masking.sh"
# shellcheck source=lib/paths.sh
source "$(dirname "${BASH_SOURCE[0]}")/paths.sh"

# tools/lib/userenv.sh -- TOML-as-singular-SSOT resolver. Sourced
# BEFORE globals.sh so that MIOS_* env vars emitted from the layered
# mios.toml (vendor < host < user) take precedence over globals.sh's
# `:=` shell-default fallbacks. Silently no-ops if the userenv.sh
# path can't be located (e.g. when automation/ runs outside a full
# repo checkout) or when python3 isn't available yet.
_mios_locate_userenv() {
    local self_dir="$(dirname "${BASH_SOURCE[0]}")"
    local candidates=(
        "${self_dir}/../../tools/lib/userenv.sh"
        "/tools/lib/userenv.sh"
        "/ctx/tools/lib/userenv.sh"
        "/usr/share/mios/tools/lib/userenv.sh"
    )
    for c in "${candidates[@]}"; do
        if [[ -f "$c" ]]; then
            printf '%s' "$c"
            return 0
        fi
    done
    return 1
}
_mios_userenv_path="$(_mios_locate_userenv 2>/dev/null || true)"
if [[ -n "$_mios_userenv_path" ]]; then
    # shellcheck source=/dev/null
    source "$_mios_userenv_path"
fi
unset _mios_userenv_path
unset -f _mios_locate_userenv

# shellcheck source=lib/globals.sh
# globals.sh is the registry for VERSION + USERS + IMAGES + PORTS +
# URLS + REPOS. Its `:=` assignments are fallbacks; userenv.sh above
# already exported the same names from mios.toml when the TOML had
# them. globals.sh fills in any gaps (e.g. if no TOML layer is
# present yet during early build).
source "$(dirname "${BASH_SOURCE[0]}")/globals.sh"

# --- Logging ----------------------------------------------------------------
log_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()  { printf '[%s] ==> %s\n' "$(log_ts)" "$*"; }
warn() { printf '[%s] WARN: %s\n' "$(log_ts)" "$*" >&2; }
die()  { printf '[%s] ERROR: %s\n' "$(log_ts)" "$*" >&2; exit 1; }
diag() { printf '[%s] DIAG: %s\n' "$(log_ts)" "$*"; }

# --- dnf flags --------------------------------------------------------------
# Select dnf binary (prefer dnf5 if available)
if command -v dnf5 &>/dev/null; then
    export DNF_BIN="dnf5"
else
    export DNF_BIN="dnf"
fi

# Defense-in-depth: /etc/dnf/dnf.conf already carries install_weak_deps=False,
# but passing it on every invocation guarantees behaviour even if a script or
# transaction overrides the global default. Array form so elements are one-
# argv-each under `set -u`, and future flags can be added in one place.
if [[ -z "${DNF_SETOPT+x}" || "$(declare -p DNF_SETOPT 2>/dev/null)" != "declare -a"* ]]; then
    declare -ga DNF_SETOPT=(
        --setopt=install_weak_deps=False
        --setopt=timeout=10          # cut per-mirror connection attempt at 10 s
        --setopt=minrate=1k          # drop any mirror delivering < 1 kB/s after timeout
        --setopt=max_parallel_downloads=10  # pull from 10 mirrors simultaneously
        --setopt=ip_resolve=4        # prefer IPv4; many Fedora IPv6 paths time out in WSL2
    )
fi
if [[ -z "${DNF_OPTS+x}" || "$(declare -p DNF_OPTS 2>/dev/null)" != "declare -a"* ]]; then
    declare -ga DNF_OPTS=(--allowerasing)
fi
# String variant for legacy/debug visibility only. Do NOT use in commands.
export DNF_SETOPT_STR="${DNF_SETOPT[*]}"
export DNF_OPTS_STR="${DNF_OPTS[*]}"

# --- Build-time version manifest --------------------------------------------
# Project policy: every dependency tracks :latest from upstream (no human
# pins). To keep day-0 builds reproducible-after-the-fact, every phase script
# that resolves a :latest tag MUST call record_version so the observed value
# is captured into the per-image manifest. build.sh promotes this file into
# /usr/lib/mios/logs/ at the end of the build, alongside the flattened log.
#
# Usage: record_version <component> <version_or_tag> [resolved_to]
#   component       short id, e.g. "aichat", "cosign", "quadlet:mios-k3s"
#   version_or_tag  what was observed, e.g. "v0.30.1" or "docker.io/x:latest"
#   resolved_to     optional: digest, source URL, or commit ref
export MIOS_VERSION_MANIFEST="${MIOS_VERSION_MANIFEST:-/tmp/mios-build-versions.tsv}"

record_version() {
    local component="$1" version="$2" resolved_to="${3:-}"
    if [[ ! -f "$MIOS_VERSION_MANIFEST" ]]; then
        printf 'component\tversion\tresolved_to\trecorded_at\n' > "$MIOS_VERSION_MANIFEST"
    fi
    printf '%s\t%s\t%s\t%s\n' \
        "$component" "$version" "$resolved_to" "$(log_ts)" \
        >> "$MIOS_VERSION_MANIFEST"
    log "version: ${component} = ${version}${resolved_to:+ (${resolved_to})}"
}
