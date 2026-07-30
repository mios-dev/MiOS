#!/usr/bin/env bash
# AI-hint: Parses layered TOML configuration files (vendor, host, and user) to export unified MIOS_ environment variables for identity, locale, network, AI, and image build settings used by all system tools and scripts.
# AI-related: ./tools/lib/userenv.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/env.defaults, /usr/lib/mios/mios.d, mios-bootstrap, mios-colors, mios-opencode-gateway, mios-llm-heavy-alt, mios-llm-heavy
# AI-functions: _mios_load_unified, _mios_legacy_get
# tools/lib/userenv.sh -- read the unified 'MiOS' user config and export
# MIOS_* environment variables. Sourced by Justfile, /etc/profile.d, every
# entry-point script, and any tool that needs the user-overridden values.
#
# THERE IS ONE CANONICAL FILE PATH PER LAYER. Higher layers shadow lower
# layers field-by-field; the user-edit copy lives in mios-bootstrap and is
# staged into /etc/mios/mios.toml at install time.
#
#   1. /usr/share/mios/mios.toml   (vendor defaults; baked into image)        lowest
#   2. /etc/mios/mios.toml         (host-local; bootstrap-staged)
#   3. ~/.config/mios/mios.toml    (per-user; XDG)                            highest
#
# Schema is the same in all three layers (TOML 1.0; section names below).
# Resolution mode: deep merge by section.field. The Python helper below
# reads each layer in order and writes one consolidated set of MIOS_*
# exports back to the calling shell.
#
# Section -> MIOS_* env mapping (typed slots; non-typed fields can still
# be reached via the [env] table for free-form injection):
#
#   [identity]    .username/.fullname/.hostname/.shell/.groups
#                 -> MIOS_USER, MIOS_USER_FULLNAME, MIOS_HOSTNAME,
#                    MIOS_USER_SHELL, MIOS_USER_GROUPS (CSV)
#   [locale]      .timezone/.keyboard_layout/.language
#                 -> MIOS_TIMEZONE, MIOS_KEYBOARD, MIOS_LOCALE
#   [auth]        .ssh_key_action/.password_policy
#                 -> MIOS_SSH_KEY_ACTION, MIOS_PASSWORD_POLICY
#   [network]     .firewalld_default_zone
#                 -> MIOS_FIREWALLD_ZONE
#   [ai]          .endpoint/.model/.embed_model/.api_key/.system_prompt_file/.mcp_registry
#                 -> MIOS_AI_ENDPOINT, MIOS_AI_MODEL, MIOS_AI_EMBED_MODEL,
#                    MIOS_AI_KEY, MIOS_SYSTEM_PROMPT_FILE, MIOS_MCP_REGISTRY
#   [desktop]     .session/.color_scheme/.flatpaks
#                 -> MIOS_DESKTOP_SESSION, MIOS_COLOR_SCHEME,
#                    MIOS_FLATPAKS (CSV; consumed by Containerfile build arg)
#   [image]       .ref/.branch/.base/.bib/.name/.tag/.local_tag
#                 -> MIOS_IMAGE_REF, MIOS_BRANCH, MIOS_BASE_IMAGE,
#                    MIOS_BIB_IMAGE, MIOS_IMAGE_NAME, MIOS_IMAGE_TAG,
#                    MIOS_LOCAL_TAG
#   [bootstrap]   .mode/.mios_repo/.bootstrap_repo
#                 -> MIOS_BOOTSTRAP_MODE, MIOS_REPO_URL, MIOS_BOOTSTRAP_REPO_URL
#   [profile]     .role/.features
#                 -> MIOS_PROFILE_ROLE, MIOS_PROFILE_FEATURES (CSV)
#   [colors]      .bg/.fg/.accent/.cursor/.success/.warning/.error/.info/
#                 .muted/.subtle/.earth/.silver/.ansi_*
#                 -> MIOS_COLOR_BG, MIOS_COLOR_FG, MIOS_COLOR_ACCENT, ...
#                    MIOS_ANSI_0_BLACK, MIOS_ANSI_1_RED, ...
#                 (consumed by /etc/profile.d/mios-colors.sh, the
#                 oh-my-posh theme, the configurator HTML's :root,
#                 and globals.{sh,ps1} as default overrides)
#   [env]         arbitrary KEY = "VALUE" pairs                exported verbatim
#
# Backwards compat:
#   - The legacy lightweight schema ([user]/[build]/[flatpaks].install) is
#     still understood as a fallback when [identity]/[image]/[desktop] are
#     absent. 'just init-user-space' migrates the legacy split files.
#   - The legacy split files (env.toml, images.toml, build.toml,
#     flatpaks.list, the bare 'env' file) are still read when no
#     mios.toml is present in any layer.
#
# Usage: source ./tools/lib/userenv.sh
# Note: must be sourced (not executed) to affect the calling shell.

MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-/usr/share/mios/mios.toml}"
MIOS_HOST_TOML="${MIOS_HOST_TOML:-/etc/mios/mios.toml}"
MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"
MIOS_USER_TOML="${MIOS_CONFIG_DIR}/mios.toml"

MIOS_ROOT="${MIOS_ROOT:-}"
if [[ -z "$MIOS_ROOT" ]]; then
    if [[ "$MIOS_VENDOR_TOML" == *usr/share/mios/mios.toml ]]; then
        MIOS_ROOT="${MIOS_VENDOR_TOML%/usr/share/mios/mios.toml}"
        MIOS_ROOT="${MIOS_ROOT:-.}"
    else
        MIOS_ROOT="."
    fi
fi

# 1. TOML overlay (vendor -> host -> per-user). Use python tomllib (3.11+
# stdlib; tomli fallback for older). The Python block prints shell-safe
# 'export' lines that the surrounding shell evals.
_mios_load_unified() {
    local py_cmd=""
    if python3 -c "import sys" >/dev/null 2>&1; then
        py_cmd="python3"
    elif python -c "import sys" >/dev/null 2>&1; then
        py_cmd="python"
    else
        return 0
    fi
    # Drop-in discovery (R1): each tier = monolith + its mios.d/*.toml fragments.
    # Vendor fragments live in /usr/lib/mios/mios.d (Law 1 USR-OVER-ETC); admin/
    # user fragments sit in a mios.d/ beside their monolith. Tier-major precedence
    # (vendor < host < user); the Python block globs + orders them exactly like the
    # peer resolver usr/lib/mios/mios_toml.py. No-op until the first fragment exists.
    local vendor_d="${MIOS_VENDOR_TOML_D:-/usr/lib/mios/mios.d}"
    local host_d="${MIOS_HOST_TOML_D:-$(dirname "$MIOS_HOST_TOML")/mios.d}"
    local user_d="${MIOS_USER_TOML_D:-${MIOS_CONFIG_DIR}/mios.d}"
    local exports
    # LOG-HYGIENE: the resolved SSOT is thousands of MIOS_* exports. Under a caller's `set -x`
    # (e.g. the OCI bake's `set -ex`) the `exports=` capture traces as ONE multi-KB line and the
    # eval below traces thousands of `+ export MIOS_...` lines -- flooding the build log to where
    # it is unreadable/un-pasteable past this point. Suppress xtrace for the resolution + eval,
    # then restore the caller's xtrace state (set -e safe: if-form, never a failing last cmd).
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

exports_map = {}

for path, val in all_pairs:
    val_processed = process_val(path, val)
    if val_processed is None or val_processed == "":
        continue
    
    canonical = "MIOS_" + path.upper().replace(".", "_").replace("-", "_")
    
    sec_name = path.split(".", 1)[0]
    if sec_name in WALK_MOSTLY_DEAD and canonical not in WALK_EMIT_KEEP:
        pass
    else:
        exports_map[canonical] = val_processed
            
    for leg in get_aliases(path):
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
    # `if`-form so set -e treats the test as a conditional, not a fatal.
    if [[ -n "$exports" ]]; then
        eval "$exports"
    fi
    if [[ "$_mios_xtrace_was_on" -eq 1 ]]; then set -x; fi
}
_mios_load_unified

# WS-0 pgvector bind hardening (Wave 0): derive the concrete listener bind
# address the quadlet renders from the [pgvector].listen_loopback boolean.
# true (default) -> 127.0.0.1 (loopback-only; the confined agent-pipe reaches
# it over loopback, nothing off-box can). false -> 0.0.0.0 (off-box exposure;
# deliberately federated deployments only). Degrade-open: if the key is unset
# we default to the safe loopback bind. The slot map can only copy a value
# verbatim, so this boolean->address transform lives here as a post-load step.
case "${MIOS_PG_LISTEN_LOOPBACK:-true}" in
    false|False|FALSE|0|no|off) export MIOS_PG_BIND_ADDR="0.0.0.0" ;;
    *)                          export MIOS_PG_BIND_ADDR="127.0.0.1" ;;
esac

# 2. Backwards-compat: legacy split files (per-user only). Read only when
# none of the three TOML layers contain a [identity] or [user] section --
# i.e., the user is on a pre-unified-schema deployment. Each is shallow
# KEY="VALUE", grep-friendly.
_mios_legacy_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null \
        | head -1 \
        | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' \
        | tr -d '"' || true
}

if [[ -z "${MIOS_USER:-}" && ! -f "$MIOS_USER_TOML" && ! -f "$MIOS_HOST_TOML" ]]; then
    # `[[ ... ]] && cmd` returns 1 when the test is false; under set -e
    # in callers like mios-build-driver, that's fatal even though
    # "key not present in legacy file" is the expected case for fresh
    # installs. Use `[[ -z ... ]] || cmd` form so set -e treats the
    # whole expression as a guard, not a hard fail.
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
        # shellcheck disable=SC1091
        source "${MIOS_CONFIG_DIR}/env"
        set +a
    fi
fi

# Whitelist of dynamically mapped ports/keys for static analysis (38-ssot-lint.sh)
_ssot_lint_ports_dummy=(
    "MIOS_PORT_AGENT_PIPE"
    "MIOS_PORT_COCKPIT_LINK"
    "MIOS_PORT_CPU_NODE"
    "MIOS_PORT_CRAWL4AI"
    "MIOS_PORT_FIRECRAWL"
    "MIOS_PORT_FORGE_HTTP"
    "MIOS_PORT_LLM_LIGHT"
    "MIOS_PORT_OPEN_WEBUI"
    "MIOS_PORT_PGVECTOR"
    "MIOS_PORT_SEARXNG"
    "MIOS_PORT_SGLANG"
    "MIOS_PORT_VLLM"
)
