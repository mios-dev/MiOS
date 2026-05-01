#!/usr/bin/env bash
# MiOS load-user-env — reads XDG TOML configs and exports MIOS_* variables
# LAW 3: Defaults are sourced from /usr/share/mios/user-preferences.md (the
# JSON-embedded preferences card). User overrides in env.toml take precedence.
# Usage: source ./tools/load-user-env.sh
# Note: must be sourced (not executed) to affect the calling shell.

MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"
_PREFS_CARD="${_PREFS_CARD:-/usr/share/mios/user-preferences.md}"

_mios_toml_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null | head -1 | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' | tr -d '"'
}

_mios_card_default() {
    local key="$1"
    if [[ -f "${_PREFS_CARD}" ]] && command -v python3 &>/dev/null; then
        python3 -c "
import json, re, sys
text = open('${_PREFS_CARD}').read()
m = re.search(r'\`\`\`json\s*(\{.*?\})\s*\`\`\`', text, re.DOTALL)
if not m: sys.exit(0)
d = json.loads(m.group(1))
f = d.get('fields', {}).get('${key}', {})
val = f.get('value') or f.get('default', '')
print(val, end='')
" 2>/dev/null
    fi
}

_ALL_KEYS=(MIOS_USER MIOS_HOSTNAME MIOS_FLATPAKS MIOS_BASE_IMAGE MIOS_LOCAL_TAG MIOS_BIB_IMAGE MIOS_IMAGE_NAME)

# 1. Seed defaults from the preferences card (LAW 3)
for key in "${_ALL_KEYS[@]}"; do
    if [[ -z "${!key:-}" ]]; then
        _default="$(_mios_card_default "$key")"
        [[ -n "${_default}" ]] && export "${key}=${_default}"
    fi
done

# 2. User overrides from XDG env.toml (highest priority)
if [[ -f "${MIOS_CONFIG_DIR}/env.toml" ]]; then
    f="${MIOS_CONFIG_DIR}/env.toml"
    for key in "${_ALL_KEYS[@]}"; do
        val="$(_mios_toml_get "$f" "$key")"
        [[ -n "$val" ]] && export "$key=$val"
    done
fi

if [[ -f "${MIOS_CONFIG_DIR}/images.toml" ]]; then
    f="${MIOS_CONFIG_DIR}/images.toml"
    for key in MIOS_BASE_IMAGE MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
        val="$(_mios_toml_get "$f" "$key")"
        [[ -n "$val" ]] && export "$key=$val"
    done
fi
