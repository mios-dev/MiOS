#!/bin/bash
# 'MiOS' v0.2.4 -- Package extraction library
#
# SSOT (definitive, v0.2.4+): mios.toml `[packages.<section>].pkgs`,
# resolved through the layered overlay chain (highest precedence first):
#   ~/.config/mios/mios.toml   per-user
#   /etc/mios/mios.toml        host/admin
#   /usr/share/mios/mios.toml  vendor defaults
#
# Legacy fallback: PACKAGES.md fenced ```packages-<category>``` blocks.
# Retained so during-transition installs from older bootstrap clones
# don't break, but every new package addition belongs in mios.toml.
#
# Usage:
#   source automation/lib/packages.sh
#   install_packages "gnome"
#   install_packages_strict "kernel"   # fails if section is empty/missing
# shellcheck source=lib/common.sh

# _resolve_mios_toml -- pick the highest-precedence mios.toml on disk.
# Honors $MIOS_TOML override for build-time staging (the build runs
# in a clean container that doesn't have ~/.config or /etc/mios yet
# so we point at /ctx/usr/share/mios/mios.toml from the build context).
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
# Empty output (return 0) means the section isn't defined in TOML --
# the caller's get_packages() falls back to PACKAGES.md in that case.
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

get_packages() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"

    # Tier 1: mios.toml SSOT (preferred -- every new addition lands here).
    local toml_pkgs
    toml_pkgs=$(get_packages_from_toml "$category" 2>/dev/null || true)
    if [[ -n "${toml_pkgs// }" ]]; then
        echo "$toml_pkgs"
        return 0
    fi

    # Tier 2: PACKAGES.md fallback (transition path; emits a deprecation
    # note via stderr so build logs surface the eventual cleanup).
    if [[ ! -f "$packages_file" ]]; then
        echo "[packages.sh] ERROR: TOML lookup empty for '$category' AND $packages_file not found" >&2
        return 1
    fi

    # shellcheck disable=SC2001 # tr is intentionally used here to word-split packages
    local md_pkgs
    md_pkgs=$(sed -n "/^\`\`\`packages-${category}$/,/^\`\`\`$/{/^\`\`\`/d;/^$/d;/^#/d;p}" "$packages_file" \
        | tr '\n' ' ')
    if [[ -n "${md_pkgs// }" ]]; then
        echo "[packages.sh] note: '$category' resolved via PACKAGES.md (legacy); migrate to mios.toml [packages.${category}].pkgs" >&2
        echo "$md_pkgs"
    fi
}

get_packages_strict() {
    local result
    result=$(get_packages "$@")
    if [[ -z "$result" ]]; then
        echo "[packages.sh] ERROR: No packages found in section '$1'" >&2
        return 1
    fi
    echo "$result"
}

_PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_PKG_DIR}/common.sh"

install_packages() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"
    local packages
    packages=$(get_packages "$category" "$packages_file")
    if [[ -n "$packages" ]]; then
        echo "[packages.sh] Installing '$category' packages..."
        # Use subshell so set -e in parent doesn't kill entire script on failure.
        # shellcheck disable=SC2086 # $packages is intentionally word-split here
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some '$category' packages failed to install" >&2
            echo "[packages.sh] Packages requested: $packages" >&2
        }
    else
        echo "[packages.sh] WARN: No packages in section '$category' -- skipping"
    fi
}

install_packages_strict() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"
    local packages
    packages=$(get_packages_strict "$category" "$packages_file") || return 1
    echo "[packages.sh] Installing '$category' packages (strict section)..."
    # shellcheck disable=SC2086 # $packages is intentionally word-split here
    # Note: --allowerasing without --best: allows conflict resolution by erasure
    # without requiring the "best" (newest) version -- avoids hard failures when
    # ucore base packages are newer than Fedora 44 versions.
    $DNF_BIN "${DNF_SETOPT[@]}" install -y --allowerasing --skip-unavailable --exclude=PackageKit $packages || {
        echo "[packages.sh] FATAL: Mandatory '$category' packages failed to install" >&2
        echo "[packages.sh] Packages requested: $packages" >&2
        return 1
    }
}

install_packages_optional() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"

    # Check if section exists at all
    local raw_section
    raw_section=$(sed -n "/^\`\`\`packages-${category}$/,/^\`\`\`$/{/^\`\`\`/d;p}" "$packages_file")

    if [[ -z "$raw_section" ]]; then
        echo "[packages.sh] WARN: Section 'packages-${category}' not found -- skipping"
        return 0
    fi

    # Check if ALL lines are comments (intentionally disabled)
    local uncommented
    uncommented=$(echo "$raw_section" | grep -v '^#' | grep -v '^$' || true)

    if [[ -z "$uncommented" ]]; then
        echo "[packages.sh] INFO: All packages in '${category}' are commented out (intentionally disabled)"
        return 0
    fi

    # Some packages are uncommented -- install those
    local packages
    packages=$(get_packages "$category" "$packages_file")
    if [[ -n "$packages" ]]; then
        echo "[packages.sh] Installing optional '$category' packages..."
        # shellcheck disable=SC2086 # $packages is intentionally word-split here
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some optional '$category' packages failed" >&2
        }
    fi
}
