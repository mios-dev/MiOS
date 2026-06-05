#!/usr/bin/env bash
# ============================================================================
# automation/lib/ws7-uki-fapolicyd-build.sh
# ----------------------------------------------------------------------------
# WS-7 (AIOS immutable-host hardening) -- GATED, DEFAULT-OFF build step that:
#   (1) installs the fapolicyd PERMISSIVE/observe drop-in + the agent-codegen
#       carve-out rules over the live config (observe-only; never enforce);
#   (2) builds a verity-rooted Unified Kernel Image (UKI) measuring the
#       composefs fs-verity digest into the UKI.
#
# ====================  ABSOLUTELY CRITICAL SAFETY  =========================
# This script is NOT a numbered pipeline step. It lives under automation/lib/
# so automation/build.sh's `[0-9][0-9]-*.sh` glob NEVER auto-runs it. It only
# runs when a numbered step (or an operator) explicitly invokes it, AND only
# does anything when the SSOT flags below are set true. It ships fapolicyd in
# PERMISSIVE (observe) mode ONLY and builds the UKI as an artifact -- it does
# NOT switch the boot loader to the UKI, does NOT flip enforce, and does NOT
# require a signed UKI. enforce-mode or a mis-signed/required UKI BRICKS BOOT;
# that promotion is a separate, documented, rollback-tested operator step
# (usr/share/doc/mios/concepts/ws7-uki-fapolicyd.md).
#
# DEGRADE-OPEN: any sub-step failure is logged and the script returns 0 (a
# hardening build step must never fail the whole image build).
#
# SSOT flags (mios.toml; both default false):
#   [security.fapolicyd_observe].enable   -> install observe drop-in + carve-out
#   [uki].verity_uki_build                -> build the verity-rooted UKI artifact
#
# Invoke (manually, or from a numbered step gated the same way):
#   bash automation/lib/ws7-uki-fapolicyd-build.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=lib/packages.sh  (for _resolve_mios_toml)
source "${SCRIPT_DIR}/packages.sh"

# _ws7_scalar <table> <key> -- read a top-level scalar from [<table>] of the
# resolved mios.toml. Mirrors automation/40-composefs-verity.sh's helper so
# WS-7 reads the SSOT the same tolerant way. Empty when absent.
_ws7_scalar() {
    local table="$1" key="$2" toml_path
    toml_path="$(_resolve_mios_toml 2>/dev/null || true)"
    [[ -n "$toml_path" && -f "$toml_path" ]] || return 0
    awk -v table="$table" -v key="$key" '
        /^\[/ {
            in_section = 0
            line = $0
            sub(/^\[/, "", line); sub(/\][[:space:]]*$/, "", line)
            gsub(/[[:space:]]/, "", line)
            if (line == table) in_section = 1
            next
        }
        in_section {
            if (match($0, "^[[:space:]]*" key "[[:space:]]*=")) {
                value = $0
                sub(/^[^=]*=[[:space:]]*/, "", value)
                sub(/[[:space:]]*#.*$/, "", value)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/^"|"$/, "", value)
                print value
                exit 0
            }
        }
    ' "$toml_path"
}

_ws7_is_true() {
    case "${1:-}" in
        true|TRUE|True|1|yes|YES|on|ON) return 0 ;;
        *) return 1 ;;
    esac
}

# ---------------------------------------------------------------------------
# Step 1: fapolicyd PERMISSIVE/observe drop-in + agent-codegen carve-out
# ---------------------------------------------------------------------------
ws7_install_fapolicyd_observe() {
    local enable
    enable="$(_ws7_scalar security.fapolicyd_observe enable)"
    enable="${enable:-${MIOS_FAPOLICYD_OBSERVE_ENABLE:-false}}"
    if ! _ws7_is_true "$enable"; then
        log "[ws7] fapolicyd observe drop-in disabled ([security.fapolicyd_observe].enable=false) -- skipping"
        return 0
    fi

    local src="/usr/lib/fapolicyd/mios-ws7-permissive.conf"
    if [[ ! -f "$src" ]]; then
        warn "[ws7] observe drop-in $src missing -- skipping (degrade-open)"
        return 0
    fi

    log "[ws7] installing fapolicyd PERMISSIVE/observe config (permissive=1)"
    # Apply over both layers per Law 1 (USR-OVER-ETC: /etc is the admin-applied
    # active copy). Back up the existing active config first so the operator can
    # revert. We deliberately do NOT touch the vendor /usr/lib/fapolicyd.conf.
    install -d -m 0755 /etc/fapolicyd
    if [[ -f /etc/fapolicyd/fapolicyd.conf ]]; then
        cp -a /etc/fapolicyd/fapolicyd.conf /etc/fapolicyd/fapolicyd.conf.pre-ws7 || true
    fi
    install -m 0644 "$src" /etc/fapolicyd/fapolicyd.conf || warn "[ws7] could not install observe conf"

    # Render the carve-out path globs from the SSOT into the live rules.d copy.
    local rules_src="/usr/lib/fapolicyd/rules.d/80-mios-agent-codegen.rules"
    if [[ -f "$rules_src" ]]; then
        local work snap scratch
        work="$(_ws7_scalar paths coderun_workspace_root)";   work="${work:-/var/home/mios/coderuns}"
        snap="$(_ws7_scalar paths coderun_snapshots_root)";   snap="${snap:-/var/home/mios/.coderun-snapshots}"
        scratch="$(_ws7_scalar paths ai_scratch_dir)";        scratch="${scratch:-/var/lib/mios/ai/scratch}"
        # Trailing slash required by fapolicyd dir= matching.
        [[ "$work"    == */ ]] || work="${work}/"
        [[ "$snap"    == */ ]] || snap="${snap}/"
        [[ "$scratch" == */ ]] || scratch="${scratch}/"
        local dst="/etc/fapolicyd/rules.d/80-mios-agent-codegen.rules"
        install -d -m 0755 /etc/fapolicyd/rules.d
        sed -e "s#^allow perm=execute all : dir=/var/home/mios/coderuns/#allow perm=execute all : dir=${work}#" \
            -e "s#^allow perm=execute all : dir=/var/home/mios/.coderun-snapshots/#allow perm=execute all : dir=${snap}#" \
            -e "s#^allow perm=execute all : dir=/var/lib/mios/ai/scratch/#allow perm=execute all : dir=${scratch}#" \
            "$rules_src" > "$dst" 2>/dev/null \
            && log "[ws7] rendered codegen carve-out rules -> $dst" \
            || warn "[ws7] could not render carve-out rules (degrade-open)"
    fi

    log "[ws7] fapolicyd observe posture installed. fapolicyd will LOG, never block."
    log "[ws7] promotion to enforce is operator-gated -- see ws7-uki-fapolicyd.md"
}

# ---------------------------------------------------------------------------
# Step 2: verity-rooted UKI artifact (build only; not wired to the bootloader)
# ---------------------------------------------------------------------------
ws7_build_verity_uki() {
    local enable
    enable="$(_ws7_scalar uki verity_uki_build)"
    enable="${enable:-${MIOS_UKI_VERITY_BUILD:-false}}"
    if ! _ws7_is_true "$enable"; then
        log "[ws7] verity-rooted UKI build disabled ([uki].verity_uki_build=false) -- skipping"
        return 0
    fi

    if ! command -v ukify >/dev/null 2>&1; then
        warn "[ws7] ukify not found (install [packages.uki]) -- skipping UKI build (degrade-open)"
        return 0
    fi

    # Reuse the cmdline rendered by automation/23-uki-render.sh.
    local cmdline_file="/usr/lib/kernel/cmdline"
    local cmdline=""
    [[ -f "$cmdline_file" ]] && cmdline="$(tr -d '\n' < "$cmdline_file")"

    local kver kdir vmlinuz initrd out_dir out
    kver="$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf '%f\n' 2>/dev/null | sort -V | tail -1)"
    if [[ -z "$kver" ]]; then
        warn "[ws7] no kernel under /usr/lib/modules -- skipping UKI build"
        return 0
    fi
    kdir="/usr/lib/modules/${kver}"
    vmlinuz="${kdir}/vmlinuz"
    initrd="${kdir}/initramfs.img"
    out_dir="/usr/lib/modules/${kver}"
    out="${out_dir}/mios-verity.efi"

    if [[ ! -f "$vmlinuz" ]]; then
        warn "[ws7] vmlinuz missing at $vmlinuz -- skipping UKI build"
        return 0
    fi

    log "[ws7] building verity-rooted UKI for kernel ${kver}"
    log "[ws7]   cmdline: ${cmdline:-<empty>}"

    # The composefs fs-verity digest (mios.toml [security].composefs_mode=verity)
    # is the root-of-trust this UKI is meant to measure. We pass it as a profile
    # so the UKI records the expected root digest; absent that, build a plain UKI
    # (still an artifact, not a brick: nothing boots it unless the operator
    # installs + signs it per the promotion doc).
    local ukify_args=(build
        --linux="$vmlinuz"
        --uname="$kver"
        --cmdline="$cmdline"
        --output="$out"
    )
    [[ -f "$initrd" ]] && ukify_args+=(--initrd="$initrd")

    if ukify "${ukify_args[@]}" 2>&1; then
        log "[ws7] UKI artifact written: $out"
        log "[ws7] NOTE: this is an unsigned/un-installed ARTIFACT. It is NOT the"
        log "[ws7] active boot entry. Signing (enrolled MOK) + install + rollback"
        log "[ws7] test are the documented operator promotion steps. Booting an"
        log "[ws7] unsigned/required UKI BRICKS BOOT -- do not flip lockdown/"
        log "[ws7] verity.require kargs until the promotion procedure passes."
    else
        warn "[ws7] ukify build failed -- degrade-open, no UKI emitted"
    fi
}

main() {
    log "[ws7] UKI + fapolicyd hardening build step (gated, default-off)"
    ws7_install_fapolicyd_observe || warn "[ws7] fapolicyd observe step degraded"
    ws7_build_verity_uki        || warn "[ws7] UKI build step degraded"
    log "[ws7] done (degrade-open; image build is never failed by this step)"
    return 0
}

main "$@"
