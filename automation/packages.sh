#!/bin/bash
# MiOS v0.2.0 — Package extraction library
# Parses PACKAGES.md fenced code blocks tagged with ```packages-<category>
#
# Usage:
#   source automation/lib/packages.sh
#   install_packages "gnome"
# shellcheck source=lib/common.sh
#   install_packages_strict "kernel"   # fails if section is empty/missing

get_packages() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"

    if [[ ! -f "$packages_file" ]]; then
        echo "[packages.sh] ERROR: $packages_file not found" >&2
        return 1
    fi

    # shellcheck disable=SC2001 # tr is intentionally used here to word-split packages
    sed -n "/^\`\`\`packages-${category}$/,/^\`\`\`$/{/^\`\`\`/d;/^$/d;/^#/d;p}" "$packages_file" \
        | tr '\n' ' '
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
        echo "[packages.sh] WARN: No packages in section '$category' — skipping"
    fi
}

install_packages_strict() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"
    local packages
    packages=$(get_packages_strict "$category" "$packages_file") || return 1
    echo "[packages.sh] Installing '$category' packages (strict section)..."
    # shellcheck disable=SC2086 # $packages is intentionally word-split here
    $DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages || {
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
        echo "[packages.sh] WARN: Section 'packages-${category}' not found — skipping"
        return 0
    fi

    # Check if ALL lines are comments (intentionally disabled)
    local uncommented
    uncommented=$(echo "$raw_section" | grep -v '^#' | grep -v '^$' || true)

    if [[ -z "$uncommented" ]]; then
        echo "[packages.sh] INFO: All packages in '${category}' are commented out (intentionally disabled)"
        return 0
    fi

    # Some packages are uncommented — install those
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
