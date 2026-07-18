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

aliases = []
    
def get_aliases(dotted_path):
    aliases = []
    
    if dotted_path.startswith("ai.vllm."):
        suffix = dotted_path[len("ai.vllm."):].upper().replace(".", "_").replace("-", "_")
        if suffix == "V1_ENGINE":
            aliases.append("MIOS_VLLM_USE_V1")
        else:
            aliases.append(f"MIOS_VLLM_{suffix}")
    elif dotted_path.startswith("ai.sglang."):
        suffix = dotted_path[len("ai.sglang."):].upper().replace(".", "_").replace("-", "_")
        if suffix == "UNIFIED_RADIX_TREE":
            aliases.append("MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE")
        elif suffix == "HIERARCHICAL_CACHE":
            aliases.append("MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE")
        else:
            aliases.append(f"MIOS_SGLANG_{suffix}")

    elif dotted_path == "identity.username":
        aliases.extend(["MIOS_USER", "MIOS_DEFAULT_USER"])
    elif dotted_path == "identity.fullname":
        aliases.append("MIOS_USER_FULLNAME")
    elif dotted_path == "identity.hostname":
        aliases.extend(["MIOS_HOSTNAME", "MIOS_DEFAULT_HOST"])
    elif dotted_path == "identity.shell":
        aliases.extend(["MIOS_USER_SHELL", "MIOS_DEFAULT_SHELL"])
    elif dotted_path == "identity.groups":
        aliases.extend(["MIOS_USER_GROUPS", "MIOS_DEFAULT_GROUPS"])
    elif dotted_path == "identity.default_password":
        aliases.append("MIOS_DEFAULT_PASSWORD")

    elif dotted_path == "locale.timezone":
        aliases.extend(["MIOS_TIMEZONE", "MIOS_DEFAULT_TIMEZONE"])
    elif dotted_path == "locale.keyboard_layout":
        aliases.extend(["MIOS_KEYBOARD", "MIOS_DEFAULT_KEYBOARD"])
    elif dotted_path == "locale.language":
        aliases.extend(["MIOS_LOCALE", "MIOS_DEFAULT_LOCALE"])

    elif dotted_path == "auth.ssh_key_action":
        aliases.append("MIOS_SSH_KEY_ACTION")
    elif dotted_path == "auth.password_policy":
        aliases.append("MIOS_PASSWORD_POLICY")

    elif dotted_path == "network.firewalld_default_zone":
        aliases.append("MIOS_FIREWALLD_ZONE")

    elif dotted_path.startswith("portal."):
        suffix = dotted_path[len("portal."):].upper().replace(".", "_").replace("-", "_")
        if suffix == "PUBLIC_HOST":
            aliases.append("MIOS_PUBLIC_HOST")
        else:
            aliases.append(f"MIOS_PORTAL_{suffix}")

    elif dotted_path.startswith("a2a."):
        name = dotted_path[len("a2a."):].upper().replace(".", "_")
        if name == "DISCOVER_PORT":
            aliases.append("MIOS_A2A_DISCOVER_PORT")
        elif name == "PUBLIC_DOMAIN":
            aliases.append("MIOS_PUBLIC_DOMAIN")
        else:
            aliases.append(f"MIOS_A2A_{name}")

    elif dotted_path == "agents.hermes.endpoint":
        aliases.append("MIOS_HERMES_WORKER_ENDPOINT")

    elif dotted_path.startswith("ai.") and not dotted_path.startswith("ai.vllm.") and not dotted_path.startswith("ai.sglang."):
        suffix = dotted_path[len("ai."):].upper().replace(".", "_").replace("-", "_")
        if suffix == "API_KEY" or suffix == "KEY":
            aliases.append("MIOS_AI_KEY")
        elif suffix == "EMBED_MODEL":
            aliases.append("MIOS_VERB_EMBED_MODEL")
        elif suffix == "STACK_MODEL":
            aliases.append("MIOS_STACK_MODEL")
        elif suffix == "CHAT_VISION_MODEL":
            aliases.append("MIOS_AGENT_PIPE_VISION_MODEL")
        elif suffix == "AGENT_VENV":
            aliases.append("MIOS_HERMES_VENV")
        elif suffix == "AGENT_INSTALL_DIR":
            aliases.append("MIOS_HERMES_DIR")
        elif suffix == "MICRO_MODEL":
            aliases.append("MIOS_MICRO_MODEL")
        elif suffix == "MICRO_ENDPOINT":
            aliases.append("MIOS_MICRO_ENDPOINT")
        elif suffix == "OPENCODE_GATEWAY_WORKDIR":
            aliases.append("MIOS_OPENCODE_WORKDIR")
        elif suffix == "OPENCODE_GATEWAY_TIMEOUT_S":
            aliases.append("MIOS_OPENCODE_TIMEOUT_S")
        elif suffix.startswith("OPENCODE_"):
            aliases.append(f"MIOS_{suffix}")
        elif suffix in {"ENDPOINT", "MODEL", "SYSTEM_PROMPT_FILE", "TOKENIZER_BACKEND", 
                        "TOKENIZER_ENCODING", "TOKENIZER_CACHE_DIR", "TOKENIZER_PATH", 
                        "HERMES_AGENT_REPO", "HERMES_AGENT_REF", "HERMES_BACKEND_URL", 
                        "MCP_REGISTRY"}:
            aliases.append(f"MIOS_{suffix}")

    elif dotted_path.startswith("build."):
        name = dotted_path[len("build."):].upper().replace(".", "_")
        if name in {"LOCAL_TAG", "AI_RAM_FLOOR_GB", "RECHUNK_MAX_LAYERS"}:
            aliases.append(f"MIOS_{name}")
        else:
            aliases.append(f"MIOS_BUILD_{name}")

    elif dotted_path.startswith("code_mode."):
        name = dotted_path[len("code_mode."):].upper()
        aliases.append(f"MIOS_CODEMODE_{name}")

    elif dotted_path.startswith("colors."):
        name = dotted_path[len("colors."):].upper()
        if name.startswith("ANSI_"):
            aliases.append(f"MIOS_{name}")
        else:
            aliases.append(f"MIOS_COLOR_{name}")

    elif dotted_path.startswith("frontier."):
        name = dotted_path[len("frontier."):].upper()
        if name == "STREAM_TO_REASONING":
            aliases.append("MIOS_A2O_STREAM_REASONING")
        else:
            aliases.append(f"MIOS_A2O_{name}")

    elif dotted_path.startswith("paths."):
        name = dotted_path[len("paths."):].upper()
        if name == "MIOS_TOML":
            aliases.append("MIOS_TOML")
        elif name == "WSL_FIRSTBOOT_DONE":
            aliases.append("MIOS_WSLBOOT_DONE")
        else:
            aliases.append(f"MIOS_{name}")

    elif dotted_path.startswith("pgvector."):
        name = dotted_path[len("pgvector."):].upper()
        if name == "DB_BACKEND":
            aliases.append("MIOS_DB_BACKEND")
        elif name == "RLS_ENABLE":
            aliases.append("MIOS_DB_RLS_ENABLE")
        else:
            aliases.append(f"MIOS_PG_{name}")

    elif dotted_path.startswith("routing.") and not dotted_path.startswith("routing.domains."):
        name = dotted_path[len("routing."):].upper().replace(".", "_")
        aliases.append(f"MIOS_{name}")

    elif dotted_path == "polish.timeout_seconds":
        aliases.append("MIOS_POLISH_TIMEOUT_S")

    elif dotted_path == "refine.timeout_seconds":
        aliases.append("MIOS_REFINE_TIMEOUT_S")

    elif dotted_path == "security.fapolicyd_observe.enable":
        aliases.append("MIOS_FAPOLICYD_OBSERVE_ENABLE")

    elif dotted_path == "uki.verity_uki_build":
        aliases.append("MIOS_UKI_VERITY_BUILD")

    elif dotted_path.startswith("verity."):
        name = dotted_path[len("verity."):].upper()
        aliases.append(f"MIOS_{name}")

    elif dotted_path == "user.hostname":
        aliases.append("MIOS_HOSTNAME")

    elif dotted_path == "user.name":
        aliases.append("MIOS_USER_FULLNAME")

    elif dotted_path == "flatpaks.install":
        aliases.append("MIOS_FLATPAKS")

    elif dotted_path.startswith("llamacpp."):
        name = dotted_path[len("llamacpp."):].upper()
        if name == "CPU_NODE_THREADS":
            aliases.append("MIOS_CPU_NODE_THREADS")
        else:
            aliases.append(f"MIOS_LLAMACPP_{name}")

    elif dotted_path == "meta.mios_version":
        aliases.append("MIOS_VERSION")

    elif dotted_path.startswith("network.quadlet."):
        name = dotted_path[len("network.quadlet."):].upper()
        if name == "CORE_GATEWAY":
            aliases.append("MIOS_CORE_NET_GATEWAY")
        elif name == "CORE_SUBNET":
            aliases.append("MIOS_CORE_NET_SUBNET")
        elif name == "NETWORK":
            aliases.append("MIOS_QUADLET_NETWORK")
        elif name == "SUBNET":
            aliases.append("MIOS_QUADLET_SUBNET")

    elif dotted_path == "fs_watcher.watch_dirs":
        aliases.append("MIOS_FS_WATCHER_DIRS")

    elif dotted_path.startswith("ports."):
        name = dotted_path[len("ports."):].upper().replace(".", "_").replace("-", "_")
        if name == "SSH":
            aliases.extend(["MIOS_PORT_SSH", "MIOS_SSH_PORT"])
        elif name == "FORGE_HTTP":
            aliases.extend(["MIOS_PORT_FORGE_HTTP", "MIOS_FORGE_HTTP_PORT"])
        elif name == "FORGE_SSH":
            aliases.extend(["MIOS_PORT_FORGE_SSH", "MIOS_FORGE_SSH_PORT"])
        elif name == "COCKPIT":
            aliases.extend(["MIOS_PORT_COCKPIT", "MIOS_COCKPIT_PORT"])
        elif name == "SEARXNG":
            aliases.extend(["MIOS_PORT_SEARXNG", "MIOS_SEARXNG_PORT"])
        elif name == "HERMES":
            aliases.extend(["MIOS_PORT_HERMES", "MIOS_HERMES_PORT"])
        elif name == "K3S_API":
            aliases.append("MIOS_K3S_API_PORT")
        elif name == "GUACAMOLE_WEB":
            aliases.append("MIOS_GUACAMOLE_PORT")
        elif name == "CEPH_DASHBOARD":
            aliases.append("MIOS_CEPH_DASHBOARD_PORT")
        elif name == "RDP":
            aliases.append("MIOS_RDP_PORT")
        else:
            aliases.append(f"MIOS_PORT_{name}")

    elif dotted_path.startswith("image.sidecars."):
        name = dotted_path[len("image.sidecars."):].upper().replace(".", "_").replace("-", "_")
        if name.endswith("_VERSION"):
            base = name[:-len("_VERSION")]
            aliases.append(f"MIOS_{base}_VERSION")
        else:
            aliases.append(f"MIOS_{name}_IMAGE")

    elif dotted_path.startswith("services."):
        parts = dotted_path.split(".")
        if len(parts) >= 3:
            service = parts[1].upper().replace("-", "_")
            key = "_".join(parts[2:]).upper().replace("-", "_")
            if service == "WEBTOOLS":
                if key in {"USER", "UID", "GID"}:
                    aliases.extend([f"MIOS_WEBTOOLS_{key}", f"MIOS_CRAWL4AI_{key}"])
                elif key == "CDP_URL":
                    aliases.append("MIOS_CRAWL_CDP_URL")
                elif key == "CAMOUFOX":
                    aliases.append("MIOS_CRAWL_CAMOUFOX")
                elif key == "MIN_CHARS":
                    aliases.append("MIOS_CRAWL_MIN_CHARS")
                elif key.startswith("FIRECRAWL_") or key.startswith("CRAWL4AI_"):
                    aliases.append(f"MIOS_{key}")
            else:
                aliases.append(f"MIOS_{service}_{key}")

    elif dotted_path.startswith("storage.cephfs."):
        key = dotted_path[len("storage.cephfs."):].upper().replace(".", "_").replace("-", "_")
        if key == "XDG_CACHE_HOME_OVERRIDE":
            aliases.append("MIOS_XDG_CACHE_LOCAL_PATH")
        else:
            aliases.append(f"MIOS_CEPHFS_{key}")

    elif dotted_path.startswith("wsl2."):
        key = dotted_path[len("wsl2."):].upper().replace(".", "_").replace("-", "_")
        if key == "DESKTOP_COMPAT_GDK_BACKEND":
            aliases.append("MIOS_WSLG_GDK_BACKEND")
        elif key == "DESKTOP_COMPAT_MOZ_WAYLAND":
            aliases.append("MIOS_WSLG_MOZ_WAYLAND")
        elif key == "DESKTOP_COMPAT_QT_PLATFORM":
            aliases.append("MIOS_WSLG_QT_PLATFORM")
        elif key == "DEV_VM_QUADLET_NETWORK_MODE":
            aliases.append("MIOS_QUADLET_DEV_NETWORK_MODE")
        else:
            aliases.append(f"MIOS_WSL2_{key}")

    elif dotted_path.startswith("converge."):
        key = dotted_path[len("converge."):].upper().replace(".", "_").replace("-", "_")
        aliases.append(f"MIOS_CONV_{key}")

    elif dotted_path.startswith("image.") and not dotted_path.startswith("image.sidecars."):
        key = dotted_path[len("image."):].upper().replace(".", "_").replace("-", "_")
        if key == "BRANCH":
            aliases.append("MIOS_BRANCH")
        elif key == "BASE":
            aliases.append("MIOS_BASE_IMAGE")
        elif key == "BIB":
            aliases.append("MIOS_BIB_IMAGE")
        elif key == "LOCAL_TAG":
            aliases.append("MIOS_LOCAL_TAG")
        elif key in {"REF", "NAME", "TAG"}:
            aliases.append(f"MIOS_IMAGE_{key}")

    elif dotted_path.startswith("desktop."):
        key = dotted_path[len("desktop."):].upper().replace(".", "_").replace("-", "_")
        if key == "COLOR_SCHEME":
            aliases.append("MIOS_COLOR_SCHEME")
        elif key == "FLATPAKS":
            aliases.append("MIOS_FLATPAKS")
        elif key == "SESSION":
            aliases.append(f"MIOS_DESKTOP_{key}")

    elif dotted_path.startswith("bootstrap.dev_vm."):
        key = dotted_path[len("bootstrap.dev_vm."):].upper().replace(".", "_").replace("-", "_")
        if key == "MACHINE_NAME":
            aliases.append("MIOS_BUILDER_DISTRO")
        elif key == "WSL_DISTRO":
            aliases.append("MIOS_WSL_DISTRO")
        elif key == "DISK_SIZE_GB":
            aliases.append("MIOS_DEV_VM_DISK_GB")
        elif key == "GPU_PASSTHROUGH":
            aliases.append("MIOS_DEV_VM_GPU")
        elif key == "HOST_RESERVE_CPU_PCT":
            aliases.append("MIOS_DEV_VM_CPU_RESERVE_PCT")
        elif key == "HOST_RESERVE_CPU_MIN":
            aliases.append("MIOS_DEV_VM_CPU_RESERVE_MIN")
        elif key == "HOST_RESERVE_MEMORY_PCT":
            aliases.append("MIOS_DEV_VM_MEMORY_RESERVE_PCT")
        elif key == "HOST_RESERVE_MEMORY_GB":
            aliases.append("MIOS_DEV_VM_MEMORY_RESERVE_GB")
        elif key == "HOST_RESERVE_DISK_GB":
            aliases.append("MIOS_DEV_VM_DISK_RESERVE_GB")
        elif key in {"BASE_IMAGE", "CPUS", "MEMORY_MB"}:
            aliases.append(f"MIOS_DEV_VM_{key}")
    elif dotted_path.startswith("bootstrap.host_storage."):
        key = dotted_path[len("bootstrap.host_storage."):].upper().replace(".", "_").replace("-", "_")
        if key == "SHRINK_MB":
            aliases.append("MIOS_DATA_DISK_MB")
        elif key == "DRIVE_LETTER":
            aliases.append("MIOS_DATA_DISK_LETTER")
    elif dotted_path.startswith("bootstrap.") and not dotted_path.startswith("bootstrap.dev_vm.") and not dotted_path.startswith("bootstrap.host_storage."):
        key = dotted_path[len("bootstrap."):].upper().replace(".", "_").replace("-", "_")
        if key == "MIOS_REPO":
            aliases.append("MIOS_REPO_URL")
        elif key == "BOOTSTRAP_REPO":
            aliases.append("MIOS_BOOTSTRAP_REPO_URL")
        elif key == "MODE":
            aliases.append(f"MIOS_BOOTSTRAP_{key}")

    elif dotted_path.startswith("reliability."):
        key = dotted_path[len("reliability."):].upper().replace(".", "_").replace("-", "_")
        aliases.append(f"MIOS_RELIABILITY_{key}")
        
    return aliases

def walk(d, prefix=""):
    results = []
    if not isinstance(d, dict):
        return results
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if path == "routing.domains":
            continue
        if isinstance(v, dict):
            results.extend(walk(v, path))
        else:
            results.append((path, v))
    return results

stack_id = get(merged, "ports.stack_id")
try:
    stack_offset = int(stack_id) * 10000 if stack_id is not None else 0
except ValueError:
    stack_offset = 0

def process_val(dotted, v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if dotted.startswith("ports.") and dotted != "ports.stack_id":
        try:
            if int(v) != 53:
                return int(v) + stack_offset
        except (ValueError, TypeError):
            pass
    if isinstance(v, list):
        return ",".join(str(x) for x in v)
    return v

all_pairs = []
EXCLUDED_SECTIONS = {"containers", "verbs", "recipes", "packages", "dotfiles", "btop", "theme", "install_phases", "messages"}
for sec, val in merged.items():
    if isinstance(val, dict) and sec not in EXCLUDED_SECTIONS:
        all_pairs.extend(walk(val, sec))

exports_map = {}
WALK_MOSTLY_DEAD = {"ai", "image", "bootstrap", "profile", "sandbox", "security"}
WALK_EMIT_KEEP = {
    "MIOS_AI_BAKE_MODELS", "MIOS_AI_DIR", "MIOS_AI_EMBED_MODEL", "MIOS_AI_ENDPOINT",
    "MIOS_AI_JOURNAL", "MIOS_AI_MCP_DIR", "MIOS_AI_MEMORY_DIR", "MIOS_AI_MODEL",
    "MIOS_AI_MODELS_DIR", "MIOS_AI_RAM_FLOOR_GB", "MIOS_AI_SCRATCH_DIR",
    "MIOS_IMAGE_NAME", "MIOS_IMAGE_REF", "MIOS_IMAGE_TAG",
    "MIOS_BOOTSTRAP_MODE", "MIOS_PROFILE_FEATURES", "MIOS_PROFILE_ROLE",
    "MIOS_SANDBOX_ENABLE", "MIOS_SECURITY_ALLOWLIST_HOSTS", "MIOS_SECURITY_PROVENANCE_TAINT",
}

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

# Credential-driven registry-selection logic (RELTOP-01)
if [[ -r "/etc/mios/secrets.env" ]]; then
    # shellcheck disable=SC1090
    source "/etc/mios/secrets.env" 2>/dev/null || true
fi

_has_registry_creds=false
for token in "${GHCR_TOKEN:-}" "${GH_TOKEN:-}" "${GITHUB_TOKEN:-}" "${MIOS_GITHUB_TOKEN:-}"; do
    if [[ -n "$token" ]]; then
        _has_registry_creds=true
        break
    fi
done

if [[ "$_has_registry_creds" == "true" ]]; then
    export MIOS_IMAGE_NAME="${MIOS_IMAGE_NAME:-ghcr.io/mios-dev/mios}"
else
    export MIOS_IMAGE_NAME="localhost/mios"
fi
export MIOS_IMAGE_REF="${MIOS_IMAGE_NAME}:${MIOS_IMAGE_TAG:-latest}"

# Whitelist of dynamically mapped ports/keys for static analysis (38-ssot-lint.sh)
_ssot_lint_ports_dummy=(
    "MIOS_PORT_AGENT_PIPE"
    "MIOS_PORT_COCKPIT_LINK"
    "MIOS_PORT_CPU_NODE"
    "MIOS_PORT_CRAWL4AI"
    "MIOS_PORT_FIRECRAWL"
    "MIOS_PORT_LLM_LIGHT"
    "MIOS_PORT_OPEN_WEBUI"
    "MIOS_PORT_PGVECTOR"
    "MIOS_PORT_SGLANG"
    "MIOS_PORT_VLLM"
)
