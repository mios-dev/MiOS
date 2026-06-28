#!/usr/bin/env python3
# AI-hint: Admission-WIRING gate for V5 (per-blade capacity + per-tenant fair-share) as
#   wired in server.py. Reuses test_server_import's stub harness so `import server`
#   EXECUTES every module-level statement (incl. the real _rebuild_blade_topology() against
#   the vendor mios.toml), then drives the server-resident helpers with synthetic flags/maps:
#   asserts _blade_vram_budget is the LOCAL VRAM scalar when MULTIBLADE_ENABLE is off
#   (byte-identical) and the endpoint's blade budget when on (remote->its budget, unknown->
#   local scalar = degrade-open); _over_blade_ceiling delegates to _over_global_ceiling() with
#   NO arg when off (byte-identical), passes the LOCAL blade's load_ceil when on, and does NOT
#   gate a REMOTE blade on the local loadavg (degrade-open); and _turn_tenant resolves the V2
#   verified owner (None when no principal -> never capped). No DB/network: _over_global_ceiling
#   is stubbed to capture its arg, so this needs no host stats.
# AI-related: ./server.py, ./mios_blades.py, ./test_server_import.py
# AI-functions: check, t_blade_vram_budget_wiring, t_over_blade_ceiling_wiring, t_turn_tenant_wiring, t_default_off_byte_identical, main
"""Wiring gate for V5 per-blade + per-tenant admission as integrated in server.py."""

import sys

# Reuse the proven import-stub harness so `import server` works on a bare checkout
# (stubs httpx/fastapi/... ; points MIOS_TOML at the vendor file).
import test_server_import as _tsi

_tsi._resolve_toml()
_tsi._install_stubs()

import server as S  # noqa: E402

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_blade_vram_budget_wiring():
    """_blade_vram_budget: local scalar when off (byte-identical); blade budget when on;
    unknown endpoint -> local scalar (degrade-open)."""
    _saved = (S.MULTIBLADE_ENABLE, S._BLADE_POOL, S._ENDPOINT_BLADE, S._LOCAL_BLADE,
              S.VRAM_BUDGET_MB)
    try:
        S.VRAM_BUDGET_MB = 23000
        S._LOCAL_BLADE = "ws"
        S._BLADE_POOL = {"ws": {"vram_budget_mb": 23000, "load_ceil": None},
                         "potato": {"vram_budget_mb": 8000, "load_ceil": 12.0}}
        S._ENDPOINT_BLADE = {"10.0.0.9:11434": "potato"}
        S.MULTIBLADE_ENABLE = False                       # DEFAULT-OFF
        check("budget off: remote ep -> LOCAL scalar (byte-identical)",
              S._blade_vram_budget("http://10.0.0.9:11434/v1") == 23000)
        check("budget off: local ep -> LOCAL scalar",
              S._blade_vram_budget("http://localhost:11441/v1") == 23000)
        S.MULTIBLADE_ENABLE = True                        # multiblade ON
        check("budget on: remote ep -> ITS blade budget",
              S._blade_vram_budget("http://10.0.0.9:11434/v1") == 8000)
        check("budget on: unknown ep -> LOCAL scalar (degrade-open)",
              S._blade_vram_budget("http://1.2.3.4:9/v1") == 23000)
    finally:
        (S.MULTIBLADE_ENABLE, S._BLADE_POOL, S._ENDPOINT_BLADE, S._LOCAL_BLADE,
         S.VRAM_BUDGET_MB) = _saved


def t_over_blade_ceiling_wiring():
    """_over_blade_ceiling: off -> _over_global_ceiling() with NO arg (byte-identical);
    on+local -> the local blade's load_ceil; on+remote -> not gated (degrade-open)."""
    _saved_fn = S._over_global_ceiling
    _saved = (S.MULTIBLADE_ENABLE, S._BLADE_POOL, S._ENDPOINT_BLADE, S._LOCAL_BLADE)
    calls = []

    def _stub(load_ceil=None):
        calls.append(load_ceil)
        return True                                       # pretend "over the ceiling"

    try:
        S._over_global_ceiling = _stub
        S._LOCAL_BLADE = "ws"
        S._BLADE_POOL = {"ws": {"vram_budget_mb": 23000, "load_ceil": 16.0},
                         "potato": {"vram_budget_mb": 8000, "load_ceil": 12.0}}
        S.MULTIBLADE_ENABLE = False                       # DEFAULT-OFF
        S._ENDPOINT_BLADE = {"10.0.0.9:11434": "potato"}
        calls.clear()
        r = S._over_blade_ceiling("http://10.0.0.9:11434/v1")
        check("ceiling off: delegates to _over_global_ceiling() no-arg (byte-identical)",
              r is True and calls == [None], f"r={r} calls={calls}")
        S.MULTIBLADE_ENABLE = True                        # multiblade ON
        S._ENDPOINT_BLADE = {"localhost:11441": "ws"}     # local-blade endpoint
        calls.clear()
        r = S._over_blade_ceiling("http://localhost:11441/v1")
        check("ceiling on+local: passes the local blade's load_ceil",
              r is True and calls == [16.0], f"r={r} calls={calls}")
        S._ENDPOINT_BLADE = {"10.0.0.9:11434": "potato"}  # remote-blade endpoint
        calls.clear()
        r = S._over_blade_ceiling("http://10.0.0.9:11434/v1")
        check("ceiling on+remote: NOT gated by local loadavg (degrade-open)",
              r is False and calls == [], f"r={r} calls={calls}")
    finally:
        S._over_global_ceiling = _saved_fn
        (S.MULTIBLADE_ENABLE, S._BLADE_POOL, S._ENDPOINT_BLADE, S._LOCAL_BLADE) = _saved


def t_turn_tenant_wiring():
    """_turn_tenant: the verified owner from _client_env_var; None when no principal."""
    tok = S._client_env_var.set({"user_name": "alice"})
    try:
        check("tenant: owner from user_name", S._turn_tenant() == "alice")
    finally:
        S._client_env_var.reset(tok)
    tok = S._client_env_var.set({"user_email": "bob@example"})
    try:
        check("tenant: owner from user_email", S._turn_tenant() == "bob@example")
    finally:
        S._client_env_var.reset(tok)
    tok = S._client_env_var.set(None)
    try:
        check("tenant: no principal -> None (never capped)", S._turn_tenant() is None)
    finally:
        S._client_env_var.reset(tok)


def t_default_off_byte_identical():
    """Prove the SHIPPED defaults are inert: both V5 flags default off, the global gate's
    tenant cap is 0, and the helpers reproduce the local-scalar / global-ceiling path."""
    check("default: MULTIBLADE_ENABLE off", S.MULTIBLADE_ENABLE is False)
    check("default: TENANT_QUOTA_ENABLE off", S.TENANT_QUOTA_ENABLE is False)
    check("default: global gate tenant cap is 0 (inert)",
          S._GLOBAL_PRIORITY_GATE._tenant_cap == 0,
          f"cap={S._GLOBAL_PRIORITY_GATE._tenant_cap}")
    # With the flag off, the blade budget is EXACTLY the local scalar for any endpoint.
    check("default: _blade_vram_budget == VRAM_BUDGET_MB for any ep",
          S._blade_vram_budget("http://anything:1234/v1") == S.VRAM_BUDGET_MB)
    # The real import ran _rebuild_blade_topology() against the vendor mios.toml: with no
    # [blades.*] + no `blade` fields, only the local blade exists at the local scalar.
    check("default: local blade resolved + present in the pool",
          bool(S._LOCAL_BLADE) and S._LOCAL_BLADE in S._BLADE_POOL,
          f"local={S._LOCAL_BLADE!r} pool_keys={list(S._BLADE_POOL)}")
    check("default: local blade vram == VRAM_BUDGET_MB (single-blade today)",
          S._BLADE_POOL[S._LOCAL_BLADE]["vram_budget_mb"] == S.VRAM_BUDGET_MB,
          str(S._BLADE_POOL.get(S._LOCAL_BLADE)))


def main():
    t_default_off_byte_identical()
    t_blade_vram_budget_wiring()
    t_over_blade_ceiling_wiring()
    t_turn_tenant_wiring()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
