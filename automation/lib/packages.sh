#!/bin/bash
# 'MiOS' v0.2.4 -- Package extraction library
#
# SSOT: mios.toml `[packages.<section>].pkgs`, resolved through the layered
# overlay chain (highest precedence first):
#   ~/.config/mios/mios.toml        per-user override
#   /etc/mios/mios.toml             host/admin override
#   /ctx/mios-bootstrap/mios.toml   bootstrap-side override (build-time)
#   /usr/share/mios/mios.toml       vendor defaults
#   /ctx/usr/share/mios/mios.toml   build context (during OCI build)
#
# As of 2026-05-05 the legacy PACKAGES.md fenced-block fallback is REMOVED.
# mios.toml is the only runtime source of truth. PACKAGES.md is retained
# under usr/share/doc/mios/reference/ as human-readable documentation
# (the mios.toml [packages.*] tables are the canonical machine-readable
# encoding). The HTML configurator at /usr/share/mios/configurator/mios.html
# is the operator-facing editor for the same TOML.
#
# Usage:
#   source automation/lib/packages.sh
#   install_packages "gnome"
#   install_packages_strict "kernel"   # fail if section is empty/missing
#   install_packages_optional "ai"     # silent skip if empty/missing
# shellcheck source=lib/common.sh

# _resolve_mios_toml -- pick the highest-precedence mios.toml on disk.
# Honors $MIOS_TOML override for build-time staging (the build runs
# in a clean container that doesn't have ~/.config or /etc/mios yet
# so the build orchestrator can point at /ctx/usr/share/mios/mios.toml
# from the build context).
_resolve_mios_toml() {
    local cand
    if [[ -n "${MIOS_TOML:-}" && -f "$MIOS_TOML" ]]; then
        echo "$MIOS_TOML"
        return 0
    fi
    for cand in \
        "${HOME:-/root}/.config/mios/mios.toml" \
        "/etc/mios/mios.toml" \
        "/ctx/mios-bootstrap/mios.toml" \
        "/usr/share/mios/mios.toml" \
        "/ctx/usr/share/mios/mios.toml"; do
        [[ -f "$cand" ]] || continue
        echo "$cand"
        return 0
    done
    return 1
}

# get_packages_from_toml <section> [<toml-path>]
# Emits a space-separated package list from [packages.<section>].pkgs.
# Empty output (return 0) means the section isn't defined in TOML or
# the pkgs array is empty.
get_packages_from_toml() {
    local category="$1"
    local toml_path
    toml_path="${2:-$(_resolve_mios_toml)}" || return 1
    [[ -f "$toml_path" ]] || return 1

    # Tolerant TOML scrape: catches both
    #   [packages.foo]
    #   pkgs = ["a","b"]
    # and the inline-table shape
    #   pkgs = [
    #       "a",
    #       "b",
    #   ]
    # Returns empty if [packages.<category>] table is absent or has no pkgs.
    awk -v section="packages.${category}" '
        /^\[/ {
            in_section = 0
            collecting = 0
            line = $0
            sub(/^\[/, "", line); sub(/\][[:space:]]*$/, "", line)
            gsub(/[[:space:]]/, "", line)
            if (line == section) in_section = 1
            next
        }
        in_section && /^[[:space:]]*pkgs[[:space:]]*=/ {
            sub(/^[^=]*=[[:space:]]*/, "", $0)
            collecting = 1
        }
        collecting {
            print
            if ($0 ~ /\][[:space:]]*$/) { collecting = 0 }
        }
    ' "$toml_path" \
        | tr -d '[]' \
        | tr ',' '\n' \
        | sed -E 's/[[:space:]]*"([^"]*)"[[:space:]]*$/\1/' \
        | sed '/^[[:space:]]*$/d' \
        | sed -E 's/[[:space:]]*#.*$//' \
        | tr '\n' ' '
}

# get_packages <section>
# Resolves [packages.<section>].pkgs from mios.toml. TOML-only as of
# 2026-05-05 (legacy PACKAGES.md fenced-block fallback removed).
get_packages() {
    local category="$1"
    local toml_pkgs
    toml_pkgs=$(get_packages_from_toml "$category" 2>/dev/null || true)
    if [[ -n "${toml_pkgs// }" ]]; then
        echo "$toml_pkgs"
        return 0
    fi
    # Section absent or pkgs empty -- caller decides what that means via
    # get_packages / get_packages_strict / install_packages_optional.
    return 0
}

# get_packages_strict <section>
# Same as get_packages but fails when the section is absent / empty.
get_packages_strict() {
    local category="$1"
    local result
    result=$(get_packages "$category")
    if [[ -z "${result// }" ]]; then
        echo "[packages.sh] ERROR: [packages.${category}] is empty or undefined in mios.toml" >&2
        return 1
    fi
    echo "$result"
}

_PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automation/lib/common.sh
source "${_PKG_DIR}/common.sh"

# _is_section_enabled <section>
# Returns 0 (enabled) if [packages.<section>].enable is missing OR true.
# Returns 1 (disabled) only when explicitly set to false in the toml.
# This is the runtime side of the configurator HTML's package toggles --
# the operator unchecks a box, the configurator writes
# `[packages.<name>].enable = false` to mios.toml, and this helper
# tells install_packages* to skip that group's dnf install.
#
# Parses with awk (no python3 dependency -- safe even at very-early
# build phases before python is layered in).
_is_section_enabled() {
    local section="$1"
    local toml result
    toml=$(_resolve_mios_toml) || return 0  # no toml at all -> default enabled
    result=$(awk -v sect="[packages.$section]" '
        $0 == sect { in_section = 1; next }
        /^\[/ && in_section { in_section = 0 }
        in_section && /^[[:space:]]*enable[[:space:]]*=/ {
            # match "enable = false" or "enable = true" (any whitespace).
            # Anything other than literal "false" is treated as enabled
            # (covers "true", missing-quote variants, comments after the
            # value, etc.) since the schema default is true.
            if ($0 ~ /=[[:space:]]*false[[:space:]]*($|#)/) print "false"
            else print "true"
            exit
        }
    ' "$toml" 2>/dev/null)
    [[ "$result" != "false" ]]
}

# install_packages <section>
# Best-effort: warns on per-package install failures, doesn't return non-zero.
# Honors [packages.<section>].enable -- if the operator unchecked the
# group in /configurator.html, this is a no-op.
install_packages() {
    local category="$1"
    if ! _is_section_enabled "$category"; then
        echo "[packages.sh] [packages.${category}].enable=false -- skipping (operator disabled via /configurator.html)"
        return 0
    fi
    local packages
    packages=$(get_packages "$category")
    if [[ -n "${packages// }" ]]; then
        echo "[packages.sh] Installing '$category' packages..."
        # shellcheck disable=SC2086 # $packages is intentionally word-split here
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some '$category' packages failed to install" >&2
            echo "[packages.sh] Packages requested: $packages" >&2
        }
    else
        echo "[packages.sh] WARN: [packages.${category}] is empty or undefined in mios.toml -- skipping"
    fi
}

# install_packages_strict <section>
# Hard fail when the section is absent / empty / install fails.
# Used for the foundation set (base, security, build-toolchain, etc.)
# where a missing package is an unrecoverable build error.
install_packages_strict() {
    local category="$1"
    local packages
    packages=$(get_packages_strict "$category") || return 1
    echo "[packages.sh] Installing '$category' packages (strict section)..."
    # shellcheck disable=SC2086 # $packages is intentionally word-split here
    # Note: --allowerasing without --best -- allows conflict resolution by
    # erasure without requiring the "best" (newest) version. Avoids hard
    # failures when ucore base packages are newer than Fedora 44 versions.
    $DNF_BIN "${DNF_SETOPT[@]}" install -y --allowerasing --skip-unavailable --exclude=PackageKit $packages || {
        echo "[packages.sh] FATAL: Mandatory '$category' packages failed to install" >&2
        echo "[packages.sh] Packages requested: $packages" >&2
        return 1
    }
}

# install_packages_optional <section>
# Silent skip when the section is absent / empty / disabled.
# Otherwise behaves like install_packages (best-effort).
install_packages_optional() {
    local category="$1"
    if ! _is_section_enabled "$category"; then
        echo "[packages.sh] INFO: [packages.${category}].enable=false -- skipping (operator disabled via /configurator.html)"
        return 0
    fi
    local packages
    packages=$(get_packages "$category")
    if [[ -z "${packages// }" ]]; then
        echo "[packages.sh] INFO: [packages.${category}] is empty or undefined -- skipping (intentional)"
        return 0
    fi
    echo "[packages.sh] Installing optional '$category' packages..."
    # shellcheck disable=SC2086 # $packages is intentionally word-split here
    ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
        echo "[packages.sh] WARNING: Some optional '$category' packages failed" >&2
    }
}
