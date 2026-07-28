# AI-hint: Authentication / caller-key helpers extracted from server.py (AGY-347).
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/access/authn.py
"""Authentication and caller key management module."""

from __future__ import annotations

import json
import os
from typing import Optional

_BACKEND_KEY: str = ""
_INGRESS_KEY: str = ""
_API_REQUIRE_AUTH: bool = False
_CALLER_KEYS_PATH: str = "/etc/mios/ai/v1/caller-keys.json"
_AUTH_HOSTPORTS: set = set()
_AGENT_AUTH_BY_HOSTPORT: dict = {}

_CALLER_KEYS_CACHE: dict = {"mtime": -1.0, "keys": {}}


def configure(*, backend_key=None, ingress_key=None, api_require_auth=None,
              caller_keys_path=None, auth_hostports=None,
              agent_auth_by_hostport=None) -> None:
    """Inject configuration scalars and auth registries."""
    global _BACKEND_KEY, _INGRESS_KEY, _API_REQUIRE_AUTH
    global _CALLER_KEYS_PATH, _AUTH_HOSTPORTS, _AGENT_AUTH_BY_HOSTPORT

    if backend_key is not None:
        _BACKEND_KEY = backend_key
    if ingress_key is not None:
        _INGRESS_KEY = ingress_key
    if api_require_auth is not None:
        _API_REQUIRE_AUTH = api_require_auth
    if caller_keys_path is not None:
        _CALLER_KEYS_PATH = caller_keys_path
    if auth_hostports is not None:
        _AUTH_HOSTPORTS = auth_hostports
    if agent_auth_by_hostport is not None:
        _AGENT_AUTH_BY_HOSTPORT = agent_auth_by_hostport


def _load_backend_key() -> str:
    """Loaded from MIOS_AGENT_PIPE_BACKEND_KEY env first, then /etc/mios/hermes/api.env."""
    env_key = os.environ.get("MIOS_AGENT_PIPE_BACKEND_KEY", "").strip()
    if env_key:
        return env_key
    try:
        with open("/etc/mios/hermes/api.env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("API_SERVER_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    except (OSError, PermissionError):
        pass
    return ""


def _apply_outbound_auth(hdrs: dict, ep: str) -> None:
    """Attach the correct OUTBOUND credential for a dispatch to `ep`."""
    _hp = ep.split("://")[-1].split("/")[0] if ep else ""
    if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
        for _k in [k for k in hdrs if k.lower() == "authorization"]:
            hdrs.pop(_k)
        hdrs["Authorization"] = f"Bearer {_BACKEND_KEY}"
        return
    _ahdr = _AGENT_AUTH_BY_HOSTPORT.get(_hp)
    if _ahdr and ":" in _ahdr:
        _hk, _hv = _ahdr.split(":", 1)
        _hk, _hv = _hk.strip(), _hv.strip()
        if _hk and _hv:
            for _k in [k for k in hdrs if k.lower() == _hk.lower()]:
                hdrs.pop(_k)
            hdrs[_hk] = _hv


def _load_caller_keys() -> dict:
    """mtime-cached caller-key store {token: {principal, scope/max_permission,...}}."""
    try:
        st = os.stat(_CALLER_KEYS_PATH)
    except OSError:
        _CALLER_KEYS_CACHE["keys"] = {}
        return {}
    if st.st_mtime != _CALLER_KEYS_CACHE["mtime"]:
        try:
            with open(_CALLER_KEYS_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            keys = data.get("keys", data) if isinstance(data, dict) else {}
            _CALLER_KEYS_CACHE["keys"] = keys if isinstance(keys, dict) else {}
            _CALLER_KEYS_CACHE["mtime"] = st.st_mtime
        except Exception:
            pass
    return _CALLER_KEYS_CACHE["keys"]


def _check_inbound_principal(token: str) -> Optional[dict]:
    """Resolve a bearer token to a scoped principal, or None if unrecognised."""
    t = (token or "").strip()
    if not t:
        return None
    if (_BACKEND_KEY and t == _BACKEND_KEY) or (_INGRESS_KEY and t == _INGRESS_KEY):
        return {"principal": "operator", "scope": "full", "via": "shared-key"}
    ent = _load_caller_keys().get(t)
    if not ent:
        return None
    entry = ent if isinstance(ent, dict) else {"principal": str(ent)}
    try:
        import mios_a2a
        if mios_a2a._caller_key_revoked(t, entry):
            return None
    except Exception:
        pass
    if isinstance(ent, dict):
        return {"principal": ent.get("principal") or "caller", "via": "caller-key", **ent}
    return {"principal": str(ent), "via": "caller-key"}


def _probe_auth_headers(ep: str) -> dict:
    """Bearer header for a liveness / model-list probe IFF the endpoint ENFORCES auth."""
    try:
        _hp = ep.split("://")[-1].split("/")[0] if ep else ""
        if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
            return {"Authorization": f"Bearer {_BACKEND_KEY}"}
        _ahdr = _AGENT_AUTH_BY_HOSTPORT.get(_hp)
        if _ahdr and ":" in _ahdr:
            _hk, _hv = _ahdr.split(":", 1)
            if _hk.strip() and _hv.strip():
                return {_hk.strip(): _hv.strip()}
    except Exception:
        pass
    return {}


def _bind_host(require_auth: bool, override: str = "") -> str:
    """FED-G9 bind posture: bind to LOOPBACK by default, ALL interfaces when auth is ON."""
    ov = (override or "").strip()
    if ov:
        return ov
    return "0.0.0.0" if require_auth else "127.0.0.1"
