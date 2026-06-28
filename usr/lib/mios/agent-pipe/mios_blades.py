# AI-hint: Pure-stdlib BLADE/topology model for the agent-pipe (V4 + V5 multi-blade
#   admission). A BLADE is a physical machine; a NODE (mios.toml [nodes.*]) is a compute
#   unit (CPU/iGPU/dGPU/NPU + engines) that lives ON a blade. This module owns the SSOT
#   readers that turn [blades.*] + the [nodes.*]/[agents.*] registry into the maps the
#   admission gate consumes: local_blade_name() resolves THIS machine's blade from the
#   [identity] hostname SSOT (never a baked literal); load_blade_pool() builds
#   {blade: {vram_budget_mb, load_ceil}} with the LOCAL blade defaulting to the existing
#   VRAM_BUDGET_MB scalar (so a config with NO [blades.*] reproduces today's single-blade
#   capacity exactly); endpoint_blade_map() maps each registry endpoint (host:port) to its
#   blade (a node with no `blade` field belongs to the local blade -> today); and
#   blade_vram_budget() looks a blade's VRAM budget up, degrading OPEN to the local scalar
#   when the blade/capacity is unknown (admission is never wedged/locked out). Magic
#   capacity numbers come from the CALLER (server's VRAM_BUDGET_MB / load ceiling SSOT) or
#   [blades.*], never baked here. Pure: stdlib + mios_config._toml_section only; this
#   module NEVER imports server (one-way boundary), so it unit-tests in isolation.
# AI-related: ./mios_config.py, ./mios_agentreg.py, ./server.py, ./test_mios_blades.py, /usr/share/mios/mios.toml
# AI-functions: _as_int, local_blade_name, load_blade_pool, endpoint_blade_map, blade_for_endpoint, blade_vram_budget
"""mios_blades -- blade (machine) topology + per-blade capacity model.

V4 makes "nodes X, Y, Z are one machine" EXPRESSIBLE: each [nodes.*] may carry an
optional `blade` (which physical machine it lives on), and [blades.<name>] declares
that machine's capacity. V5 gives the model a real consumer: the admission gate
compares a node's residents against ITS blade's VRAM budget instead of the single
LOCAL scalar (the "remote residents vs one local VRAM scalar" bug).

DEFAULT-PRESERVING by construction: a node with no `blade` belongs to the LOCAL blade
(name from the [identity] hostname SSOT), whose capacity defaults to the caller's
existing VRAM_BUDGET_MB. So a config with no [blades.*] and no blade fields resolves
every endpoint to one local blade at the local budget -- i.e. exactly today. Every
lookup degrades OPEN (unknown blade/capacity -> the local scalar) so admission can
never wedge on a missing blade.
"""

from __future__ import annotations

import os
import socket
from typing import Callable, Optional

from mios_config import _toml_section


def _as_int(v, default: int = 0) -> int:
    """Coerce an optional capacity value to int, falling back to ``default`` when it
    is unset/blank/non-numeric (mirrors server._opt_int_mb's tolerant coercion)."""
    try:
        if v is None or str(v).strip() == "":
            return int(default)
        return int(float(v))
    except (TypeError, ValueError):
        try:
            return int(default)
        except (TypeError, ValueError):
            return 0


def local_blade_name() -> str:
    """Resolve THIS machine's blade name from SSOT, NOT a baked literal.

    Precedence: env ``MIOS_HOSTNAME`` (the install.env bridge derived from
    [identity].hostname) -> [identity].hostname -> the OS hostname
    (``socket.gethostname()``) as the degrade-open fallback. Always returns a
    non-empty name when the OS can report one; only a total failure yields ''.
    """
    try:
        h = str(os.environ.get("MIOS_HOSTNAME") or "").strip()
        if not h:
            h = str((_toml_section("identity") or {}).get("hostname") or "").strip()
        if not h:
            h = str(socket.gethostname() or "").strip()
        return h or str(socket.gethostname() or "").strip()
    except Exception:  # noqa: BLE001 -- degrade-open: a hostname probe must never raise
        try:
            return str(socket.gethostname() or "").strip()
        except Exception:  # noqa: BLE001
            return ""


def load_blade_pool(local_blade: str, local_vram_budget_mb,
                    local_load_ceil: Optional[float] = None) -> dict:
    """Build ``{blade_name: {"vram_budget_mb": int, "load_ceil": float|None}}``.

    The LOCAL blade is ALWAYS present and defaults to the caller's existing
    VRAM_BUDGET_MB scalar (and optional local load ceiling), so a config with NO
    [blades.*] section reproduces today's single-blade capacity byte-for-byte. A
    declared [blades.<local>] may OVERRIDE the local capacity; remote blades carry
    their own. A declared blade that omits ``vram_budget_mb`` degrades OPEN to the
    local scalar (unknown capacity is never a wedge). Degrade-open: a malformed or
    absent section -> just the local blade at the local scalar.
    """
    _local_vram = _as_int(local_vram_budget_mb)
    _local_ceil = None
    if local_load_ceil is not None:
        try:
            _local_ceil = float(local_load_ceil)
        except (TypeError, ValueError):
            _local_ceil = None
    pool: dict = {local_blade: {"vram_budget_mb": _local_vram, "load_ceil": _local_ceil}}
    try:
        blades = _toml_section("blades")
    except Exception:  # noqa: BLE001 -- degrade-open: absent/broken section -> local only
        blades = {}
    if isinstance(blades, dict):
        for name, cfg in blades.items():
            if not isinstance(cfg, dict):
                continue
            entry = dict(pool.get(name) or {})
            vb = cfg.get("vram_budget_mb")
            if vb is not None and str(vb).strip() != "":
                entry["vram_budget_mb"] = _as_int(vb, entry.get("vram_budget_mb", _local_vram))
            elif "vram_budget_mb" not in entry:
                # A declared blade with no capacity -> the local scalar (degrade-open).
                entry["vram_budget_mb"] = _local_vram
            lc = cfg.get("load_ceil")
            if lc is not None and str(lc).strip() != "":
                try:
                    entry["load_ceil"] = float(lc)
                except (TypeError, ValueError):
                    entry.setdefault("load_ceil", None)
            else:
                entry.setdefault("load_ceil", None)
            pool[name] = entry
    return pool


def endpoint_blade_map(registry: dict, endpoint_key: Callable[[str], str],
                       local_blade: str) -> dict:
    """Map each registry endpoint (``host:port`` via ``endpoint_key``) to its blade.

    A [nodes.*]/[agents.*] entry with an explicit ``blade`` carries it; one WITHOUT a
    blade belongs to the LOCAL blade -- so a config with no blade fields makes every
    endpoint local (today). Returns ``{endpoint_key: blade_name}``. Endpoints absent
    from this map resolve to the local blade at lookup time (see blade_for_endpoint).
    """
    out: dict = {}
    if not isinstance(registry, dict):
        return out
    for _name, cfg in registry.items():
        if not isinstance(cfg, dict):
            continue
        ep = str(cfg.get("endpoint") or "").strip()
        if not ep:
            continue
        try:
            key = endpoint_key(ep)
        except Exception:  # noqa: BLE001 -- a bad endpoint string just isn't mapped
            continue
        if not key:
            continue
        out[key] = str(cfg.get("blade") or "").strip() or local_blade
    return out


def blade_for_endpoint(ep_blade_map: dict, endpoint_key: Callable[[str], str],
                       ep: str, local_blade: str) -> str:
    """The blade an endpoint lives on; degrade-open to the LOCAL blade when unknown."""
    try:
        return str(ep_blade_map.get(endpoint_key(ep)) or local_blade)
    except Exception:  # noqa: BLE001 -- degrade-open: unknown endpoint -> local blade
        return local_blade


def blade_vram_budget(blade_pool: dict, blade_name: str, local_vram_budget_mb) -> int:
    """The VRAM budget (MB) for a blade, degrading OPEN to the LOCAL scalar when the
    blade (or its capacity) is unknown -- so an endpoint whose blade can't be resolved
    is admitted against today's local budget, never wedged or locked out."""
    try:
        cap = (blade_pool.get(blade_name) or {}).get("vram_budget_mb")
        if cap:
            return int(cap)
    except Exception:  # noqa: BLE001 -- degrade-open
        pass
    return _as_int(local_vram_budget_mb)
