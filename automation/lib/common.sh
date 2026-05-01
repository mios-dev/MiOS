#!/usr/bin/env bash
# ============================================================================
# automation/lib/common.sh
# ----------------------------------------------------------------------------
# Shared helpers for MiOS build scripts.
# Safe to source multiple times (idempotent).
# ============================================================================

# shellcheck source=lib/masking.sh
source "$(dirname "${BASH_SOURCE[0]}")/masking.sh"

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
    declare -ga DNF_SETOPT=(--setopt=install_weak_deps=False)
fi
if [[ -z "${DNF_OPTS+x}" || "$(declare -p DNF_OPTS 2>/dev/null)" != "declare -a"* ]]; then
    declare -ga DNF_OPTS=(--allowerasing)
fi
# String variant for legacy/debug visibility only. Do NOT use in commands.
export DNF_SETOPT_STR="${DNF_SETOPT[*]}"
export DNF_OPTS_STR="${DNF_OPTS[*]}"
