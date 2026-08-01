# AI-hint: The single shared Python resolver for the layered mios.toml SSOT -- the Python peer of tools/lib/userenv.sh. Collapses the ~13 independently re-rolled `try: import tomllib except: import tomli` + `deep_merge` + hardcoded-layer-path copies scattered across usr/libexec/mios/* and the agent-pipe tree into ONE overlay implementation with ONE set of semantics (vendor < host < user, highest wins, empty strings do not override). load_merged() gives the full three-layer overlay; load_vendor() gives the vendor-only view the offline drift-gates intentionally read; colors() is the ONE canonical palette-default map (mirrors mios.toml [colors]) so no tool re-declares the 12 hexes. Importers add usr/lib/mios to sys.path and `import mios_toml`. Pairs with mios-theme-render + mios-sync-theme (palette projection) and the drift-gates.
# AI-related: ../../libexec/mios/mios-theme-render, ../../libexec/mios/mios-sync-theme, ../../share/mios/mios.toml, ../../../tools/lib/userenv.sh, ../../../automation/98-drift-checks.sh
# AI-functions: load_merged, load_vendor, deep_merge, section, get, colors, layer_paths
"""Shared layered mios.toml resolver (vendor < host < user) + canonical palette defaults."""

from __future__ import annotations

import glob
import os

try:
    import tomllib as _toml
except ImportError:  # py < 3.11
    try:
        import tomli as _toml  # type: ignore
    except ImportError:  # pragma: no cover
        _toml = None

# Canonical three-layer overlay paths (lowest precedence first). Every element is
# overridable so a caller (or a test/CI on a non-FHS host) can retarget without
# editing this file. VENDOR is repo-relative when MIOS_TOML_ROOT is set.
def _default_vendor(root=""):
    """Vendor mios.toml path when no explicit override is set: root-relative when
    MIOS_TOML_ROOT is given; else the FHS install if present; else repo-relative to
    THIS file (source checkout / CI unit tests, where /usr/share/mios is absent) so
    SSOT reads still resolve. Only the PATH is derived here -- no value is hardcoded."""
    if root:
        return os.path.join(root, "usr/share/mios/mios.toml")
    fhs = "/usr/share/mios/mios.toml"
    if os.path.exists(fhs):
        return fhs
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "share", "mios", "mios.toml"))


_ROOT = os.environ.get("MIOS_TOML_ROOT", "")
VENDOR = os.environ.get("MIOS_VENDOR_TOML") or os.environ.get("MIOS_TOML") or _default_vendor(_ROOT)
HOST = os.environ.get("MIOS_HOST_TOML", "/etc/mios/mios.toml")
USER = os.environ.get("MIOS_USER_TOML") or os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "mios/mios.toml")


def _frags(dirpath):
    """The *.toml drop-in fragments in dirpath, sorted lexically by BASENAME
    (systemd .d ordering), or [] if the dir is absent. A missing mios.d/ makes
    this a no-op -- the whole drop-in layer collapses to nothing."""
    if not dirpath or not os.path.isdir(dirpath):
        return []
    return sorted(glob.glob(os.path.join(dirpath, "*.toml")),
                  key=os.path.basename)


def _tier_dirs():
    """(vendor, vendor_d, host, host_d, user, user_d) resolved from the env at
    CALL time. Vendor FRAGMENTS live in /usr/lib/mios/mios.d (Law 1 USR-OVER-ETC
    + systemd's /usr/lib vendor convention), NOT beside the /usr/share monolith;
    admin/user fragments sit in a mios.d/ beside their monolith."""
    root = os.environ.get("MIOS_TOML_ROOT", "")
    vendor = os.environ.get("MIOS_VENDOR_TOML") or os.environ.get("MIOS_TOML") or _default_vendor(root)
    host = os.environ.get("MIOS_HOST_TOML", "/etc/mios/mios.toml")
    user = os.environ.get("MIOS_USER_TOML") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "mios/mios.toml")
    vendor_d = os.environ.get("MIOS_VENDOR_TOML_D") or (
        os.path.join(root, "usr/lib/mios/mios.d") if root else "/usr/lib/mios/mios.d")
    host_d = os.environ.get("MIOS_HOST_TOML_D") or os.path.join(os.path.dirname(host), "mios.d")
    user_d = os.environ.get("MIOS_USER_TOML_D") or os.path.join(os.path.dirname(user), "mios.d")
    return vendor, vendor_d, host, host_d, user, user_d


def layer_paths():
    """The overlay layer paths, lowest precedence first, EXPANDED to include
    drop-in fragments. Resolved from the environment at CALL time (not import
    time) so a caller / test / CI on a non-FHS host can retarget a layer via
    MIOS_VENDOR_TOML / MIOS_HOST_TOML / MIOS_USER_TOML / MIOS_TOML_ROOT (and the
    *_TOML_D fragment-dir overrides) AFTER this module is imported.

    Ordering is TIER-MAJOR (vendor < host < user); within each tier the monolith
    seeds LOWEST, then that tier's mios.d/*.toml fragments (lexical basename)
    deep-merge over it. Tier is the primary precedence key -- a vendor fragment
    can NEVER outrank a higher tier (the XDG/git-config scope model, not
    systemd's global flat sort). NO-OP when no mios.d/ exists: every _frags()
    glob is empty and this returns exactly [vendor, host, user] as before."""
    vendor, vendor_d, host, host_d, user, user_d = _tier_dirs()
    return ([vendor] + _frags(vendor_d)
            + [host] + _frags(host_d)
            + [user] + _frags(user_d))


def deep_merge(dst, src):
    """Recursively merge src into dst. Non-empty scalars/lists overwrite; an empty
    string never overrides a non-empty value below it (the mios.toml overlay rule)."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        elif isinstance(v, str) and v == "" and dst.get(k) not in (None, ""):
            continue
        else:
            dst[k] = v
    return dst


def _load_one(path):
    if not path or not os.path.isfile(path) or _toml is None:
        return {}
    try:
        with open(path, "rb") as fh:
            return _toml.load(fh)
    except Exception:  # noqa: BLE001 -- a broken overlay layer must not crash a reader
        return {}


_LOAD_MERGED_CACHE = None

def clear_cache():
    global _LOAD_MERGED_CACHE
    _LOAD_MERGED_CACHE = None

def load_merged(layers=None):
    """Full three-layer overlay (vendor < host < user), highest wins."""
    global _LOAD_MERGED_CACHE
    if layers is None and _LOAD_MERGED_CACHE is not None:
        return _LOAD_MERGED_CACHE

    merged = {}
    for p in (layers if layers is not None else layer_paths()):
        deep_merge(merged, _load_one(p))

    if layers is None:
        try:
            import mios_db_config
            if mios_db_config.is_db_authoritative():
                db_cfg = mios_db_config.load_db_config()
                if db_cfg:
                    deep_merge(merged, db_cfg)
        except Exception:
            pass

    if layers is None:
        _LOAD_MERGED_CACHE = merged
    return merged


def load_vendor():
    """Vendor-only view (monolith + /usr/lib/mios/mios.d fragments) -- what the
    offline drift-gates intentionally read. Includes vendor fragments so that a
    section migrated out of the monolith into a mios.d/ fragment (R6) stays
    visible to the gates. No-op vs the old monolith-only view until the first
    vendor fragment exists."""
    vendor, vendor_d, *_ = _tier_dirs()
    merged = {}
    deep_merge(merged, _load_one(vendor))
    for p in _frags(vendor_d):
        deep_merge(merged, _load_one(p))
    return merged


def section(data, name):
    """A [table] (or dotted [a.b]) sub-dict, or {} if absent."""
    cur = data
    for part in name.split("."):
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(part, {})
    return cur if isinstance(cur, dict) else {}


def get(sect, key, default=None, data=None):
    """One [sect].key value from the merged overlay (or a supplied `data`)."""
    if data is None:
        try:
            import mios_db_config
            if mios_db_config.is_db_authoritative():
                db_cfg = mios_db_config.load_db_config()
                if db_cfg:
                    sect_dict = section(db_cfg, sect)
                    if key in sect_dict:
                        return sect_dict[key]
        except Exception:
            pass

    d = data if data is not None else load_merged()
    return section(d, sect).get(key, default)


# The ONE canonical palette-default map -- mirrors mios.toml [colors] verbatim so
# no tool re-declares the 12 semantic hexes (+ ansi slots). resolve = SSOT over these.
PALETTE_DEFAULTS = {
    "bg": "#282262", "fg": "#E7DFD3", "accent": "#1A407F", "cursor": "#F35C15",
    "success": "#3E7765", "warning": "#F35C15", "error": "#DC271B", "info": "#1A407F",
    "muted": "#948E8E", "subtle": "#B7C9D7", "earth": "#734F39", "silver": "#E0E0E0",
    "ansi_0_black": "#282262", "ansi_1_red": "#DC271B", "ansi_2_green": "#3E7765",
    "ansi_3_yellow": "#F35C15", "ansi_4_blue": "#1A407F", "ansi_5_magenta": "#734F39",
    "ansi_6_cyan": "#B7C9D7", "ansi_7_white": "#E7DFD3", "ansi_8_bright_black": "#948E8E",
    "ansi_9_bright_red": "#FF6B5C", "ansi_10_bright_green": "#5FAA8E",
    "ansi_11_bright_yellow": "#FF8540", "ansi_12_bright_blue": "#3D6BA8",
    "ansi_13_bright_magenta": "#9D7660", "ansi_14_bright_cyan": "#E0E0E0",
    "ansi_15_bright_white": "#FFFFFF",
}


def colors(data=None):
    """Resolved palette: mios.toml [colors] over PALETTE_DEFAULTS (SSOT wins)."""
    if data is None:
        try:
            import mios_db_config
            if mios_db_config.is_db_authoritative():
                db_cfg = mios_db_config.load_db_config()
                if db_cfg:
                    c = section(db_cfg, "colors")
                    return {k: str(c.get(k, v)) for k, v in PALETTE_DEFAULTS.items()}
        except Exception:
            pass

    c = section(data if data is not None else load_merged(), "colors")
    return {k: str(c.get(k, v)) for k, v in PALETTE_DEFAULTS.items()}


def float_allowlist(data=None):
    """Resolved float allowlist table from mios.toml [build.float]."""
    d = data if data is not None else load_vendor()
    return section(d, "build.float")


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
    elif dotted_path == "accounts.db_backed":
        aliases.append("MIOS_ACCOUNTS_DB_BACKED")

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
        elif suffix in {"ENDPOINT", "MODEL"}:
            aliases.extend([f"MIOS_AI_{suffix}", f"MIOS_{suffix}"])
        elif suffix in {"SYSTEM_PROMPT_FILE", "TOKENIZER_BACKEND", 
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
        elif name in ("LAUNCHER_SOCKET", "MIOS_LAUNCHER_SOCKET"):
            aliases.append("MIOS_LAUNCHER_SOCKET")
        else:
            aliases.append(f"MIOS_{name}")

    elif dotted_path.startswith("pgvector.") or dotted_path.startswith("pg."):
        prefix_len = len("pgvector.") if dotted_path.startswith("pgvector.") else len("pg.")
        name = dotted_path[prefix_len:].upper()
        if name == "DB_BACKEND":
            aliases.append("MIOS_DB_BACKEND")
        elif name == "RLS_ENABLE":
            aliases.append("MIOS_DB_RLS_ENABLE")
        else:
            aliases.append(f"MIOS_PG_{name}")
            aliases.append(f"MIOS_PGVECTOR_{name}")

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
        # UNIFIED PORTS (operator directive: every port floats from SSOT, one scheme):
        # each [ports].<x> emits BOTH canonical alias forms -- MIOS_PORT_<x> AND
        # MIOS_<x>_PORT -- alongside the section-generic MIOS_PORTS_<x>, so NO consumer
        # ever hardcodes a port number; the value is operator-defined in mios.toml [ports].
        # A few keys carry a historical service-canonical name that differs from the raw key.
        _canon = {"GUACAMOLE_WEB": "GUACAMOLE"}.get(name, name)
        aliases.extend([f"MIOS_PORT_{_canon}", f"MIOS_{_canon}_PORT"])

    elif dotted_path.startswith("image.sidecars."):
        name = dotted_path[len("image.sidecars."):].upper().replace(".", "_").replace("-", "_")
        if name.endswith("_VERSION"):
            base = name[:-len("_VERSION")]
            aliases.append(f"MIOS_{base}_VERSION")
        else:
            aliases.extend([f"MIOS_{name}_IMAGE", f"MIOS_{name}_VERSION"])

    elif dotted_path.startswith("services."):
        parts = dotted_path.split(".")
        if len(parts) >= 3:
            service = parts[1].upper().replace("-", "_")
            key = "_".join(parts[2:]).upper().replace("-", "_")
            if service == "WEBTOOLS":
                if key in {"USER", "UID", "GID"}:
                    aliases.append(f"MIOS_WEBTOOLS_{key}")
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
        pass

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
        
    elif dotted_path.startswith("routing."):
        key = dotted_path[len("routing."):].upper().replace(".", "_").replace("-", "_")
        aliases.append(f"MIOS_ROUTING_{key}")
        if key.startswith("LAUNCH_"):
            aliases.append(f"MIOS_{key}")

    elif dotted_path.startswith("mios-find.") or dotted_path.startswith("mios_find."):
        prefix_len = len("mios-find.") if dotted_path.startswith("mios-find.") else len("mios_find.")
        key = dotted_path[prefix_len:].upper().replace(".", "_").replace("-", "_")
        aliases.append(f"MIOS_FIND_{key}")

    return aliases

def _toml_walk_common(d, prefix=""):
    """Canonical recursive section-walk helper shared across TOML resolvers."""
    return walk(d, prefix)


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

def process_val(dotted, v, stack_offset=0):
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

EXCLUDED_SECTIONS = {"containers", "verbs", "recipes", "packages", "dotfiles", "btop", "theme", "install_phases", "messages"}
WALK_MOSTLY_DEAD = {"ai", "image", "bootstrap", "profile", "sandbox", "security"}
WALK_EMIT_KEEP = {
    "MIOS_AI_BAKE_MODELS", "MIOS_AI_DIR", "MIOS_AI_EMBED_MODEL", "MIOS_AI_ENDPOINT",
    "MIOS_AI_JOURNAL", "MIOS_AI_MCP_DIR", "MIOS_AI_MEMORY_DIR", "MIOS_AI_MODEL",
    "MIOS_AI_MODELS_DIR", "MIOS_AI_RAM_FLOOR_GB", "MIOS_AI_SCRATCH_DIR",
    "MIOS_IMAGE_NAME", "MIOS_IMAGE_REF", "MIOS_IMAGE_TAG",
    "MIOS_BOOTSTRAP_MODE", "MIOS_PROFILE_FEATURES", "MIOS_PROFILE_ROLE",
    "MIOS_SANDBOX_ENABLE", "MIOS_SECURITY_ALLOWLIST_HOSTS", "MIOS_SECURITY_PROVENANCE_TAINT",
    "MIOS_HEADLESS", "MIOS_MONITOR_RUNNING", "MIOS_NO_COLOR", "MIOS_NO_MONITOR",
}
