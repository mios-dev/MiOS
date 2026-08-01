#!/bin/bash
# AI-hint: Provides shell functions to parse and extract package lists from mios.toml configuration files, supporting layered overrides and specific installation modes (strict/optional) for automated package management.
# AI-related: automation/lib/packages.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/configurator/mios.html, mios-bootstrap
# AI-functions: _resolve_mios_toml, get_packages_from_toml, get_packages, get_packages_strict, _is_section_enabled, install_packages, install_packages_strict, install_packages_optional

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

_get_pkgs_from_single_toml() {
    local category="$1"
    local file="$2"
    [[ -f "$file" ]] || return 1
    
    local auth
    auth=$(awk '/^[[:space:]]*build_catalog_authoritative[[:space:]]*=/ {
        if ($0 ~ /=[[:space:]]*true/) print "true"
    }' "$file" 2>/dev/null)

    if [[ "$auth" == "true" ]]; then
        local mat_json="$(dirname "$file")/package_sets.json"
        if [[ -f "$mat_json" ]]; then
            local pkgs
            pkgs=$(python3 -c "import json; d = json.load(open('$mat_json')); print(' '.join(next(p['pkgs'] for p in d if p['name'] == '$category')))" 2>/dev/null)
            if [[ -n "$pkgs" ]]; then
                echo "$pkgs"
                return 0
            fi
        fi
    fi

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
            line = $0
            sub(/#.*$/, "", line)
            print line
            if (line ~ /\]/) { collecting = 0 }
        }
    ' "$file" \
        | tr -d '[]' \
        | tr ',' '\n' \
        | sed -E 's/[[:space:]]*"([^"]*)"[[:space:]]*$/\1/' \
        | sed '/^[[:space:]]*$/d' \
        | sed -E 's/[[:space:]]*#.*$//' \
        | tr '\n' ' '
}

get_packages_from_toml() {
    local category="$1"
    local file="${2:-}"
    
    if [[ -n "$file" ]]; then
        _get_pkgs_from_single_toml "$category" "$file"
        return $?
    fi
    
    local cand
    for cand in \
        "${MIOS_TOML:-}" \
        "${HOME:-/root}/.config/mios/mios.toml" \
        "/etc/mios/mios.toml" \
        "/ctx/mios-bootstrap/mios.toml" \
        "/usr/share/mios/mios.toml" \
        "/ctx/usr/share/mios/mios.toml"; do
        [[ -n "$cand" && -f "$cand" ]] || continue
        if grep -q "^\[packages\.${category}\]" "$cand" 2>/dev/null; then
            local pkgs
            pkgs=$(_get_pkgs_from_single_toml "$category" "$cand")
            if [[ -n "${pkgs// }" ]]; then
                echo "$pkgs"
                return 0
            fi
        fi
    done
    return 1
}

get_packages() {
    local category="$1"
    local toml_pkgs
    toml_pkgs=$(get_packages_from_toml "$category" 2>/dev/null || true)
    if [[ -n "${toml_pkgs// }" ]]; then
        echo "$toml_pkgs"
        return 0
    fi
    return 0
}

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
source "${_PKG_DIR}/common.sh"

_is_section_enabled() {
    local section="$1"
    local cand result
    for cand in \
        "${MIOS_TOML:-}" \
        "${HOME:-/root}/.config/mios/mios.toml" \
        "/etc/mios/mios.toml" \
        "/ctx/mios-bootstrap/mios.toml" \
        "/usr/share/mios/mios.toml" \
        "/ctx/usr/share/mios/mios.toml"; do
        [[ -n "$cand" && -f "$cand" ]] || continue
        if grep -q "^\[packages\.${section}\]" "$cand" 2>/dev/null; then
            result=$(awk -v sect="[packages.$section]" '
                $0 == sect { in_section = 1; next }
                /^\[/ && in_section { in_section = 0 }
                in_section && /^[[:space:]]*enable[[:space:]]*=/ {
                    if ($0 ~ /=[[:space:]]*false[[:space:]]*($|#)/) print "false"
                    else print "true"
                    exit
                }
            ' "$cand" 2>/dev/null)
            if [[ "$result" == "false" ]]; then
                return 1
            elif [[ "$result" == "true" ]]; then
                return 0
            fi
            return 0
        fi
    done
    return 0
}

install_packages() {
    local category="$1"
    if ! _is_section_enabled "$category"; then
        echo "[packages.sh] [packages.${category}].enable=false"
        return 0
    fi
    local packages
    packages=$(get_packages "$category")
    if [[ -n "${packages// }" ]]; then
        echo "[packages.sh] Installing '$category' packages"
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --setopt=strict=0 --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some '$category' packages failed to install" >&2
            echo "[packages.sh] Packages requested: $packages" >&2
        }
    else
        echo "[packages.sh] WARN: [packages.${category}] is empty or undefined in mios.toml"
    fi
}

install_packages_strict() {
    local category="$1"
    local packages
    packages=$(get_packages_strict "$category") || return 1
    echo "[packages.sh] Installing '$category' packages"
    $DNF_BIN "${DNF_SETOPT[@]}" install -y --allowerasing --setopt=strict=0 --skip-unavailable --exclude=PackageKit $packages || {
        echo "[packages.sh] FATAL: Mandatory '$category' packages failed to install" >&2
        echo "[packages.sh] Packages requested: $packages" >&2
        return 1
    }
}

install_packages_optional() {
    local category="$1"
    if ! _is_section_enabled "$category"; then
        echo "[packages.sh] INFO: [packages.${category}].enable=false"
        return 0
    fi
    local packages
    packages=$(get_packages "$category")
    if [[ -z "${packages// }" ]]; then
        echo "[packages.sh] INFO: [packages.${category}] is empty or undefined"
        return 0
    fi
    echo "[packages.sh] Installing optional '$category' packages"
    ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
        echo "[packages.sh] WARNING: Some optional '$category' packages failed" >&2
    }
}
