# AI-hint: The single shared Python resolver for the layered mios.toml SSOT -- the Python peer of tools/lib/userenv.sh. Collapses the ~13 independently re-rolled `try: import tomllib except: import tomli` + `deep_merge` + hardcoded-layer-path copies scattered across usr/libexec/mios/* and the agent-pipe tree into ONE overlay implementation with ONE set of semantics (vendor < host < user, highest wins, empty strings do not override). load_merged() gives the full three-layer overlay; load_vendor() gives the vendor-only view the offline drift-gates intentionally read; colors() is the ONE canonical palette-default map (mirrors mios.toml [colors]) so no tool re-declares the 12 hexes. Importers add usr/lib/mios to sys.path and `import mios_toml`. Pairs with mios-theme-render + mios-sync-theme (palette projection) and the drift-gates.
# AI-related: ../../libexec/mios/mios-theme-render, ../../libexec/mios/mios-sync-theme, ../../share/mios/mios.toml, ../../../tools/lib/userenv.sh, ../../../automation/38-drift-checks.sh
# AI-functions: load_merged, load_vendor, deep_merge, section, get, colors, layer_paths
"""Shared layered mios.toml resolver (vendor < host < user) + canonical palette defaults."""

from __future__ import annotations

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
_ROOT = os.environ.get("MIOS_TOML_ROOT", "")
VENDOR = os.environ.get("MIOS_VENDOR_TOML") or (
    os.path.join(_ROOT, "usr/share/mios/mios.toml") if _ROOT else "/usr/share/mios/mios.toml")
HOST = os.environ.get("MIOS_HOST_TOML", "/etc/mios/mios.toml")
USER = os.environ.get("MIOS_USER_TOML") or os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "mios/mios.toml")


def layer_paths():
    """The overlay layer paths, lowest precedence first."""
    return [VENDOR, HOST, USER]


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


def load_merged(layers=None):
    """Full three-layer overlay (vendor < host < user), highest wins."""
    merged = {}
    for p in (layers if layers is not None else layer_paths()):
        deep_merge(merged, _load_one(p))
    return merged


def load_vendor():
    """Vendor-only view -- what the offline drift-gates intentionally read."""
    return _load_one(VENDOR)


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
    c = section(data if data is not None else load_merged(), "colors")
    return {k: str(c.get(k, v)) for k, v in PALETTE_DEFAULTS.items()}
