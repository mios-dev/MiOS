#!/usr/bin/env bash
# tools/lib/userenv.sh -- read the unified 'MiOS' user config and export
# MIOS_* environment variables. Sourced by Justfile, /etc/profile.d, and
# any tool that needs the user-overridden values.
#
# Single source of user truth: ~/.config/mios/mios.toml
#   [user]      identity
#   [image]     base/builder/registry refs
#   [build]     local tag
#   [flatpaks]  array of refs
#   [ai]        model, endpoint, key, optional system_prompt_file
#   [profile]   role + features (replaces ~/.config/mios/profile.toml)
#   [env]       free-form KEY = "VALUE" exports (replaces ~/.config/mios/env)
#
# Resolution order (first non-empty wins):
#   1. ~/.config/mios/mios.toml          (user, unified)
#   2. /etc/mios/install.env             (host, written by Windows installer)
#   3. /etc/mios/env.d/*.env             (admin drop-ins, alphabetical)
#   4. /usr/share/mios/env.defaults      (vendor)
#
# Backwards-compat: if mios.toml is absent the legacy split files
# (env.toml / images.toml / build.toml / flatpaks.list / profile.toml /
# the bare `env` file) are still read. `just init-user-space` migrates them.
#
# Usage: source ./tools/lib/userenv.sh
# Note: must be sourced (not executed) to affect the calling shell.

MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"
MIOS_UNIFIED_TOML="${MIOS_CONFIG_DIR}/mios.toml"
MIOS_VENDOR_DEFAULTS="${MIOS_VENDOR_DEFAULTS:-/usr/share/mios/env.defaults}"

# Typed-slot map: TOML "section.field" -> MIOS_* env var name.
# Keep aligned with usr/share/mios/mios.toml.example.
_mios_keymap=(
    "user.name=MIOS_USER"
    "user.hostname=MIOS_HOSTNAME"
    "image.base=MIOS_BASE_IMAGE"
    "image.bib=MIOS_BIB_IMAGE"
    "image.name=MIOS_IMAGE_NAME"
    "image.tag=MIOS_IMAGE_TAG"
    "build.local_tag=MIOS_LOCAL_TAG"
    "ai.model=MIOS_AI_MODEL"
    "ai.endpoint=MIOS_AI_ENDPOINT"
    "ai.key=MIOS_AI_KEY"
    "ai.system_prompt_file=MIOS_SYSTEM_PROMPT_FILE"
    "profile.role=MIOS_PROFILE_ROLE"
)

# 1. Vendor defaults (lowest priority). Shell-format KEY="VALUE".
if [[ -f "$MIOS_VENDOR_DEFAULTS" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$MIOS_VENDOR_DEFAULTS"
    set +a
fi

# 2. Unified mios.toml -- highest priority. Use python tomllib (3.11+ stdlib).
_mios_load_toml() {
    local toml="$1"
    [[ -f "$toml" ]] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    local exports
    exports=$(MIOS_TOML="$toml" python3 - "${_mios_keymap[@]}" <<'PY'
import os, sys, shlex
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)
path = os.environ["MIOS_TOML"]
try:
    with open(path, "rb") as f:
        data = tomllib.load(f)
except Exception as e:
    sys.stderr.write(f"userenv: failed to parse {path}: {e}\n")
    sys.exit(0)

def get(d, dotted):
    for p in dotted.split("."):
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d

# Typed slots
for arg in sys.argv[1:]:
    dotted, env = arg.split("=", 1)
    v = get(data, dotted)
    if v is None or v == "":
        continue
    if isinstance(v, list):
        v = ",".join(str(x) for x in v)
    print(f"export {env}={shlex.quote(str(v))}")

# Flatpaks list -> MIOS_FLATPAKS
fl = get(data, "flatpaks.install")
if isinstance(fl, list) and fl:
    print(f"export MIOS_FLATPAKS={shlex.quote(','.join(str(x) for x in fl))}")

# Profile features list -> MIOS_PROFILE_FEATURES (comma-joined)
pf = get(data, "profile.features")
if isinstance(pf, list) and pf:
    print(f"export MIOS_PROFILE_FEATURES={shlex.quote(','.join(str(x) for x in pf))}")

# [env] table -> export each key=value verbatim. Keys must match
# POSIX env-var rules ([A-Za-z_][A-Za-z0-9_]*); silently skip anything else
# rather than emit an export line bash will error on.
import re
ev = data.get("env") if isinstance(data.get("env"), dict) else {}
for k, v in ev.items():
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
        sys.stderr.write(f"userenv: skipping invalid [env] key: {k!r}\n")
        continue
    if v is None:
        continue
    if isinstance(v, list):
        v = ",".join(str(x) for x in v)
    print(f"export {k}={shlex.quote(str(v))}")
PY
    )
    [[ -n "$exports" ]] && eval "$exports"
}
_mios_load_toml "$MIOS_UNIFIED_TOML"

# 3. Backwards compat: if mios.toml is absent, fall back to the legacy split
# files. Each is shallow KEY = "VALUE" (no sections), so a regex grep works.
_mios_legacy_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null \
        | head -1 \
        | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' \
        | tr -d '"' || true
}

if [[ ! -f "$MIOS_UNIFIED_TOML" ]]; then
    if [[ -f "${MIOS_CONFIG_DIR}/env.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/env.toml"
        for key in MIOS_USER MIOS_HOSTNAME MIOS_FLATPAKS MIOS_BASE_IMAGE MIOS_LOCAL_TAG; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -n "$val" ]] && export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/images.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/images.toml"
        for key in MIOS_BASE_IMAGE MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -n "$val" ]] && export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/build.toml" ]]; then
        val="$(_mios_legacy_get "${MIOS_CONFIG_DIR}/build.toml" MIOS_LOCAL_TAG)"
        [[ -n "$val" ]] && export "MIOS_LOCAL_TAG=$val"
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/flatpaks.list" ]]; then
        flat=$(grep -vE '^\s*(#|$)' "${MIOS_CONFIG_DIR}/flatpaks.list" 2>/dev/null | paste -sd,)
        [[ -n "$flat" ]] && export "MIOS_FLATPAKS=$flat"
    fi
    # Legacy bare `env` file -- shell-format KEY=VALUE, source it directly.
    if [[ -f "${MIOS_CONFIG_DIR}/env" ]]; then
        set -a
        # shellcheck disable=SC1091
        source "${MIOS_CONFIG_DIR}/env"
        set +a
    fi
fi
