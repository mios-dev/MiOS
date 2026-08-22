#!/usr/bin/env bash
# AI-hint: Parses layered TOML configuration files (vendor, host, and user) to export unified MIOS_ environment variables for identity, locale, network, AI, and image build settings used by all system tools and scripts.
# AI-related: ./tools/lib/userenv.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/env.defaults, /usr/lib/mios/mios.d, mios-bootstrap, mios-colors, mios-opencode-gateway, mios-llm-heavy-alt, mios-llm-heavy
# AI-functions: _mios_load_unified, _mios_legacy_get
# MIOS_* environment variables. Sourced by Justfile, /etc/profile.d, every

MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-/usr/share/mios/mios.toml}"
MIOS_HOST_TOML="${MIOS_HOST_TOML:-/etc/mios/mios.toml}"
MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"
MIOS_USER_TOML="${MIOS_USER_TOML:-${MIOS_CONFIG_DIR}/mios.toml}"

MIOS_ROOT="${MIOS_ROOT:-}"
if [[ -z "$MIOS_ROOT" ]]; then
    if [[ "$MIOS_VENDOR_TOML" == *usr/share/mios/mios.toml ]]; then
        MIOS_ROOT="${MIOS_VENDOR_TOML%/usr/share/mios/mios.toml}"
        MIOS_ROOT="${MIOS_ROOT:-.}"
    else
        MIOS_ROOT="."
    fi
fi

_mios_load_unified() {
    local _use_rust=1
    if [[ "${MIOS_MIGRATION_USE_RUST_RESOLVER_SHELL:-true}" == "false" || "${MIOS_MIGRATION_USE_RUST_RESOLVER_SHELL:-true}" == "0" ]]; then
        _use_rust=0
    fi
    if [[ "$_use_rust" -eq 1 ]] && command -v mios-resolver >/dev/null 2>&1; then
        local _native_exports=""
        if _native_exports=$(mios-resolver --emit=shell 2>/dev/null) && [[ -n "$_native_exports" ]]; then
            eval "$_native_exports" && return 0
        fi
    fi
    if command -v miosd >/dev/null 2>&1; then
        eval "$(miosd resolve --shell 2>/dev/null)" || true
    fi
    local py_cmd=""
    if python3 -c "import sys" >/dev/null 2>&1; then
        py_cmd="python3"
    elif python -c "import sys" >/dev/null 2>&1; then
        py_cmd="python"
    else
        return 0
    fi
    local vendor_d="${MIOS_VENDOR_TOML_D:-/usr/lib/mios/mios.d}"
    local host_d="${MIOS_HOST_TOML_D:-$(dirname "$MIOS_HOST_TOML")/mios.d}"
    local user_d="${MIOS_USER_TOML_D:-${MIOS_CONFIG_DIR}/mios.d}"
    local exports
    local _mios_xtrace_was_on=0; case "$-" in *x*) _mios_xtrace_was_on=1 ;; esac; set +x
    exports=$(MIOS_VENDOR_TOML="$MIOS_VENDOR_TOML" MIOS_HOST_TOML="$MIOS_HOST_TOML" \
              MIOS_USER_TOML="$MIOS_USER_TOML" MIOS_VENDOR_TOML_D="$vendor_d" \
              MIOS_HOST_TOML_D="$host_d" MIOS_USER_TOML_D="$user_d" MIOS_ROOT="$MIOS_ROOT" \
              PYTHONIOENCODING="utf-8" \
              "$py_cmd" - <<'PY'
import os, sys, shlex, re, glob
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)

ROOT = os.environ.get("MIOS_ROOT", ".")

def normalize_path(p):
    if not p:
        return p
    if os.name == "nt" or sys.platform == "win32":
        m = re.match(r"^/([a-zA-Z])/(.*)", p)
        if m:
            return f"{m.group(1)}:/{m.group(2)}"
    return p

ROOT = normalize_path(ROOT)

def _frags(d):
    if not d or not os.path.isdir(d):
        return []
    return sorted(glob.glob(os.path.join(d, "*.toml")), key=os.path.basename)

layers = ([normalize_path(os.environ.get("MIOS_VENDOR_TOML", ""))] + [normalize_path(x) for x in _frags(normalize_path(os.environ.get("MIOS_VENDOR_TOML_D", "")))]
          + [normalize_path(os.environ.get("MIOS_HOST_TOML", ""))] + [normalize_path(x) for x in _frags(normalize_path(os.environ.get("MIOS_HOST_TOML_D", "")))]
          + [normalize_path(os.environ.get("MIOS_USER_TOML", ""))] + [normalize_path(x) for x in _frags(normalize_path(os.environ.get("MIOS_USER_TOML_D", "")))])

def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        elif isinstance(v, str) and v == "" and dst.get(k) not in (None, ""):
            continue  # empty string never overrides a non-empty value (parity with mios_toml.py:52)
        else:
            dst[k] = v

merged = {}
for path in layers:
    if not path or not os.path.isfile(path):
        continue
    try:
        with open(path, "rb") as f:
            deep_merge(merged, tomllib.load(f))
    except Exception as e:
        sys.stderr.write(f"userenv: failed to parse {path}: {e}\n")

def get(d, dotted):
    for p in dotted.split("."):
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d

stack_id = get(merged, "ports.stack_id")
try:
    stack_offset = int(stack_id) * 10000 if stack_id is not None else 0
except ValueError:
    stack_offset = 0

try:
    sys.path.insert(0, os.environ.get("MIOS_ROOT_LIB", os.path.join(ROOT, "usr/lib/mios")))
    import mios_toml
    get_aliases = mios_toml.get_aliases
    walk = mios_toml.walk
    def process_val(dotted, v):
        return mios_toml.process_val(dotted, v, stack_offset)
    EXCLUDED_SECTIONS = mios_toml.EXCLUDED_SECTIONS
    WALK_MOSTLY_DEAD = mios_toml.WALK_MOSTLY_DEAD
    WALK_EMIT_KEEP = mios_toml.WALK_EMIT_KEEP
except ImportError:
    sys.exit(0)

all_pairs = []
for sec, val in merged.items():
    if isinstance(val, dict) and sec not in EXCLUDED_SECTIONS:
        all_pairs.extend(walk(val, sec))

import re as _re
_re_unsafe = _re.compile(r"[^A-Za-z0-9_]")

exports_map = {}

for path, val in all_pairs:
    val_processed = process_val(path, val)
    if val_processed is None or val_processed == "":
        continue
    
    if path.startswith("converge."):
        _cbody = "CONV_" + path[len("converge."):].upper().replace(".", "_").replace("-", "_").replace("/", "_")
    else:
        _cbody = path.upper().replace(".", "_").replace("-", "_").replace("/", "_")
    # Same sanitization as tools/render-globals.py: a key like `mios-llm-worker@`
    # is otherwise neither a legal sh nor PowerShell identifier (Law 13 twins).
    canonical = _cbody if _cbody.startswith("MIOS_") else "MIOS_" + _cbody
    canonical = _re_unsafe.sub("_", canonical)
    
    sec_name = path.split(".", 1)[0]
    if sec_name in WALK_MOSTLY_DEAD and canonical not in WALK_EMIT_KEEP:
        pass
    else:
        exports_map[canonical] = val_processed
            
    for leg in get_aliases(path):
        if leg.endswith("_VERSION") and path.startswith("image.sidecars."):
            exports_map[leg] = str(val_processed).rsplit(":", 1)[1] if ":" in str(val_processed) else "latest"
        else:
            exports_map[leg] = val_processed

_env_tbl = merged.get("env")
if isinstance(_env_tbl, dict):
    for _k, _v in sorted(_env_tbl.items()):
        _vp = process_val("env." + _k, _v)
        if _vp is not None and _vp != "":
            exports_map[_k] = _vp

for env_name, val_processed in sorted(exports_map.items()):
    print(f"export {env_name}={shlex.quote(str(val_processed))}")

ref_path = os.path.join(ROOT, "usr/share/mios/referenced_names.txt")
if os.path.isfile(ref_path):
    try:
        with open(ref_path, "r", encoding="utf-8") as f:
            for line in f:
                v = line.strip()
                if v and v not in exports_map:
                    print(f"export {v}=\"${{{v}:-}}\"")
    except Exception:
        pass
PY
    )
    if [[ -n "$exports" ]]; then
        eval "$exports"
    fi
    if [[ "$_mios_xtrace_was_on" -eq 1 ]]; then set -x; fi
}
_mios_load_unified

case "${MIOS_PG_LISTEN_LOOPBACK:-true}" in
    false|False|FALSE|0|no|off) export MIOS_PG_BIND_ADDR="0.0.0.0" ;;
    *)                          export MIOS_PG_BIND_ADDR="127.0.0.1" ;;
esac

_mios_legacy_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null \
        | head -1 \
        | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' \
        | tr -d '"' || true
}

if [[ -z "${MIOS_USER:-}" && ! -f "$MIOS_USER_TOML" && ! -f "$MIOS_HOST_TOML" ]]; then
    if [[ -f "${MIOS_CONFIG_DIR}/env.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/env.toml"
        for key in MIOS_USER MIOS_HOSTNAME MIOS_FLATPAKS MIOS_BASE_IMAGE MIOS_LOCAL_TAG; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -z "$val" ]] || export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/images.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/images.toml"
        for key in MIOS_BASE_IMAGE MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -z "$val" ]] || export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/build.toml" ]]; then
        val="$(_mios_legacy_get "${MIOS_CONFIG_DIR}/build.toml" MIOS_LOCAL_TAG)"
        [[ -z "$val" ]] || export "MIOS_LOCAL_TAG=$val"
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/flatpaks.list" ]]; then
        flat=$(grep -vE '^\s*(#|$)' "${MIOS_CONFIG_DIR}/flatpaks.list" 2>/dev/null | paste -sd,)
        [[ -z "$flat" ]] || export "MIOS_FLATPAKS=$flat"
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/env" ]]; then
        set -a
        source "${MIOS_CONFIG_DIR}/env"
        set +a
    fi
fi

_ssot_lint_ports_dummy=(
    "MIOS_PORT_AGENT_PIPE"
    "MIOS_PORT_CHROME_CDP"
    "MIOS_PORT_COCKPIT_LINK"
    "MIOS_PORT_CPU_NODE"
    "MIOS_PORT_CRAWL4AI"
    "MIOS_PORT_FIRECRAWL"
    "MIOS_PORT_FORGE_HTTP"
    "MIOS_PORT_FORGE_SSH"
    "MIOS_PORT_GUACD"
    "MIOS_PORT_LLM_LIGHT"
    "MIOS_PORT_OPEN_WEBUI"
    "MIOS_PORT_OTELCOL_OTLP"
    "MIOS_PORT_OTELCOL_UI"
    "MIOS_PORT_PGVECTOR"
    "MIOS_PORT_PXE_HUB_API"
    "MIOS_PORT_REDIS"
    "MIOS_PORT_SEARXNG"
    "MIOS_PORT_SGLANG"
    "MIOS_PORT_VLLM"
)
