#!/usr/bin/env bash
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
MIOS_VENDOR_DEFAULTS="${MIOS_VENDOR_DEFAULTS:-/usr/share/mios/env.defaults}"

# 0. Vendor env-defaults (lowest priority, shell-format KEY="VALUE" file).
# Surfaces port numbers, paths, and infrastructure constants that don't
# belong in the TOML schema.
if [[ -f "$MIOS_VENDOR_DEFAULTS" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$MIOS_VENDOR_DEFAULTS"
    set +a
fi

# 1. TOML overlay (vendor -> host -> per-user). Use python tomllib (3.11+
# stdlib; tomli fallback for older). The Python block prints shell-safe
# 'export' lines that the surrounding shell evals.
_mios_load_unified() {
    local layers=("$MIOS_VENDOR_TOML" "$MIOS_HOST_TOML" "$MIOS_USER_TOML")
    command -v python3 >/dev/null 2>&1 || return 0
    local exports
    exports=$(MIOS_LAYERS="${layers[*]}" python3 - <<'PY'
import os, sys, shlex, re
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)

layers = os.environ["MIOS_LAYERS"].split()

def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
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

# Typed slot map. Pairs of "section.field=ENV_VAR".
slots = [
    # identity
    ("identity.username",       "MIOS_USER"),
    ("identity.fullname",       "MIOS_USER_FULLNAME"),
    ("identity.hostname",       "MIOS_HOSTNAME"),
    ("identity.shell",          "MIOS_USER_SHELL"),
    ("identity.groups",         "MIOS_USER_GROUPS"),
    # locale
    ("locale.timezone",         "MIOS_TIMEZONE"),
    ("locale.keyboard_layout",  "MIOS_KEYBOARD"),
    ("locale.language",         "MIOS_LOCALE"),
    # auth
    ("auth.ssh_key_action",     "MIOS_SSH_KEY_ACTION"),
    ("auth.password_policy",    "MIOS_PASSWORD_POLICY"),
    # network
    ("network.firewalld_default_zone", "MIOS_FIREWALLD_ZONE"),
    # ai
    ("ai.endpoint",             "MIOS_AI_ENDPOINT"),
    ("ai.model",                "MIOS_AI_MODEL"),
    ("ai.embed_model",          "MIOS_AI_EMBED_MODEL"),
    ("ai.api_key",              "MIOS_AI_KEY"),
    ("ai.system_prompt_file",   "MIOS_SYSTEM_PROMPT_FILE"),
    ("ai.mcp_registry",         "MIOS_MCP_REGISTRY"),
    # desktop
    ("desktop.session",         "MIOS_DESKTOP_SESSION"),
    ("desktop.color_scheme",    "MIOS_COLOR_SCHEME"),
    ("desktop.flatpaks",        "MIOS_FLATPAKS"),
    # image
    ("image.ref",               "MIOS_IMAGE_REF"),
    ("image.branch",            "MIOS_BRANCH"),
    ("image.base",              "MIOS_BASE_IMAGE"),
    ("image.bib",               "MIOS_BIB_IMAGE"),
    ("image.name",              "MIOS_IMAGE_NAME"),
    ("image.tag",               "MIOS_IMAGE_TAG"),
    ("image.local_tag",         "MIOS_LOCAL_TAG"),
    # bootstrap
    ("bootstrap.mode",          "MIOS_BOOTSTRAP_MODE"),
    ("bootstrap.mios_repo",     "MIOS_REPO_URL"),
    ("bootstrap.bootstrap_repo","MIOS_BOOTSTRAP_REPO_URL"),
    # profile
    ("profile.role",            "MIOS_PROFILE_ROLE"),
    ("profile.features",        "MIOS_PROFILE_FEATURES"),
    # colors -- Hokusai + operator-neutrals palette, applied across every
    # console / terminal / oh-my-posh / Cockpit / configurator HTML.
    # /etc/profile.d/mios-colors.sh emits OSC-4 / OSC-10 / OSC-11 / OSC-12
    # at every interactive shell start using these MIOS_COLOR_* values.
    # The configurator HTML's :root CSS variables also bind to these
    # tokens via applyColorsToRoot(), so an edit there re-skins every
    # surface that resolves through this slot map.
    ("colors.bg",               "MIOS_COLOR_BG"),
    ("colors.fg",               "MIOS_COLOR_FG"),
    ("colors.accent",           "MIOS_COLOR_ACCENT"),
    ("colors.cursor",           "MIOS_COLOR_CURSOR"),
    ("colors.success",          "MIOS_COLOR_SUCCESS"),
    ("colors.warning",          "MIOS_COLOR_WARNING"),
    ("colors.error",            "MIOS_COLOR_ERROR"),
    ("colors.info",             "MIOS_COLOR_INFO"),
    ("colors.muted",            "MIOS_COLOR_MUTED"),
    ("colors.subtle",           "MIOS_COLOR_SUBTLE"),
    ("colors.earth",            "MIOS_COLOR_EARTH"),
    ("colors.silver",           "MIOS_COLOR_SILVER"),
    ("colors.ansi_0_black",            "MIOS_ANSI_0_BLACK"),
    ("colors.ansi_1_red",              "MIOS_ANSI_1_RED"),
    ("colors.ansi_2_green",            "MIOS_ANSI_2_GREEN"),
    ("colors.ansi_3_yellow",           "MIOS_ANSI_3_YELLOW"),
    ("colors.ansi_4_blue",             "MIOS_ANSI_4_BLUE"),
    ("colors.ansi_5_magenta",          "MIOS_ANSI_5_MAGENTA"),
    ("colors.ansi_6_cyan",             "MIOS_ANSI_6_CYAN"),
    ("colors.ansi_7_white",            "MIOS_ANSI_7_WHITE"),
    ("colors.ansi_8_bright_black",     "MIOS_ANSI_8_BRIGHT_BLACK"),
    ("colors.ansi_9_bright_red",       "MIOS_ANSI_9_BRIGHT_RED"),
    ("colors.ansi_10_bright_green",    "MIOS_ANSI_10_BRIGHT_GREEN"),
    ("colors.ansi_11_bright_yellow",   "MIOS_ANSI_11_BRIGHT_YELLOW"),
    ("colors.ansi_12_bright_blue",     "MIOS_ANSI_12_BRIGHT_BLUE"),
    ("colors.ansi_13_bright_magenta",  "MIOS_ANSI_13_BRIGHT_MAGENTA"),
    ("colors.ansi_14_bright_cyan",     "MIOS_ANSI_14_BRIGHT_CYAN"),
    ("colors.ansi_15_bright_white",    "MIOS_ANSI_15_BRIGHT_WHITE"),
    # legacy/lightweight aliases (keep older mios.toml drafts working)
    ("user.name",               "MIOS_USER"),
    ("user.hostname",           "MIOS_HOSTNAME"),
    ("build.local_tag",         "MIOS_LOCAL_TAG"),
    ("ai.key",                  "MIOS_AI_KEY"),
    ("flatpaks.install",        "MIOS_FLATPAKS"),
]

for dotted, env in slots:
    v = get(merged, dotted)
    if v is None or v == "":
        continue
    if isinstance(v, list):
        v = ",".join(str(x) for x in v)
    print(f"export {env}={shlex.quote(str(v))}")

# Free-form [env] table: arbitrary KEY=VALUE exports. POSIX-compliant
# names only; silently skip otherwise so 'eval' below doesn't choke.
ev = merged.get("env") if isinstance(merged.get("env"), dict) else {}
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
_mios_load_unified

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
    if [[ -f "${MIOS_CONFIG_DIR}/env" ]]; then
        set -a
        # shellcheck disable=SC1091
        source "${MIOS_CONFIG_DIR}/env"
        set +a
    fi
fi
