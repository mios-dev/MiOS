#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_blades (V4/V5 blade topology +
#   per-blade capacity model). Pure stdlib, no server.py/DB/network: monkeypatches the
#   module's _toml_section so [blades.*] / [identity] are served offline, then asserts the
#   DEFAULT-PRESERVING contract (no [blades.*] + no blade field -> one local blade at the
#   local VRAM scalar = today), the local-blade override, remote-blade capacities, the
#   endpoint->blade map (a node with no blade -> local), and -- the V5 headline -- that the
#   admission DECISION (used+est+reserve <= budget) DENIES a remote node over ITS blade's
#   budget yet ADMITS it under the local scalar (the default-off path), plus degrade-open
#   to the local scalar on any unknown blade/capacity.
# AI-related: ./mios_blades.py, ./mios_config.py, ./server.py
# AI-functions: check, t_local_blade_name, t_load_blade_pool_default, t_load_blade_pool_overrides, t_endpoint_blade_map, t_blade_for_endpoint, t_blade_vram_budget_degrade_open, t_admission_decision, main
"""Unit tests for mios_blades (V4 blade model + V5 per-blade admission capacity)."""

import os
import sys

import mios_blades as B

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _endpoint_key(ep):
    """host:port of an endpoint URL -- the same identity server._endpoint_key uses."""
    s = str(ep or "").split("://", 1)[-1]
    return s.split("/", 1)[0] or s


def t_local_blade_name():
    # env MIOS_HOSTNAME wins; else [identity].hostname; else the OS hostname (non-empty).
    _saved_env = os.environ.get("MIOS_HOSTNAME")
    _saved_toml = B._toml_section
    try:
        os.environ["MIOS_HOSTNAME"] = "blade-from-env"
        check("local_blade: env MIOS_HOSTNAME wins", B.local_blade_name() == "blade-from-env")
        os.environ.pop("MIOS_HOSTNAME", None)
        B._toml_section = lambda s: {"hostname": "blade-from-identity"} if s == "identity" else {}
        check("local_blade: falls to [identity].hostname",
              B.local_blade_name() == "blade-from-identity")
        B._toml_section = lambda s: {}            # no env, no identity -> OS hostname
        check("local_blade: OS hostname fallback non-empty", bool(B.local_blade_name()))
    finally:
        B._toml_section = _saved_toml
        if _saved_env is None:
            os.environ.pop("MIOS_HOSTNAME", None)
        else:
            os.environ["MIOS_HOSTNAME"] = _saved_env


def t_load_blade_pool_default():
    # DEFAULT-PRESERVING: no [blades.*] -> ONLY the local blade, at the local scalar +
    # local ceiling the caller passes (== today's VRAM_BUDGET_MB / ADMIT_LOAD_CEIL).
    _saved = B._toml_section
    B._toml_section = lambda s: {}
    try:
        pool = B.load_blade_pool("ws", 23000, 16.0)
    finally:
        B._toml_section = _saved
    check("pool: default has only the local blade", list(pool.keys()) == ["ws"], str(pool))
    check("pool: local vram defaults to the local scalar", pool["ws"]["vram_budget_mb"] == 23000)
    check("pool: local load_ceil carried", pool["ws"]["load_ceil"] == 16.0)


def t_load_blade_pool_overrides():
    _saved = B._toml_section
    blades = {
        "ws":     {"vram_budget_mb": 24000},        # OVERRIDE the local default
        "potato": {"vram_budget_mb": 8000, "load_ceil": 12},
        "bigbox": {"vram_budget_mb": 80000},
        "vague":  {},                                # declared, no capacity -> local scalar
        "bad":    "notadict",                        # ignored
    }
    B._toml_section = lambda s: blades if s == "blades" else {}
    try:
        pool = B.load_blade_pool("ws", 23000, None)
    finally:
        B._toml_section = _saved
    check("pool: local blade overridden by [blades.<local>]", pool["ws"]["vram_budget_mb"] == 24000)
    check("pool: remote blade vram carried", pool["potato"]["vram_budget_mb"] == 8000)
    check("pool: remote blade load_ceil carried", pool["potato"]["load_ceil"] == 12.0)
    check("pool: big blade carried", pool["bigbox"]["vram_budget_mb"] == 80000)
    check("pool: capacity-less declared blade degrades to local scalar",
          pool["vague"]["vram_budget_mb"] == 23000, str(pool.get("vague")))
    check("pool: non-dict blade entry ignored", "bad" not in pool)


def t_endpoint_blade_map():
    registry = {
        "node:a":   {"endpoint": "http://10.0.0.9:11434/v1", "blade": "potato"},
        "node:b":   {"endpoint": "http://10.0.0.9:11435/v1", "blade": "potato"},  # same machine
        "node:loc": {"endpoint": "http://localhost:11441/v1"},                    # no blade -> local
        "inert":    {"endpoint": ""},                                             # skipped
        "bad":      "notadict",                                                   # skipped
    }
    m = B.endpoint_blade_map(registry, _endpoint_key, "ws")
    check("ep_map: explicit blade mapped", m.get("10.0.0.9:11434") == "potato", str(m))
    check("ep_map: second node same machine -> same blade", m.get("10.0.0.9:11435") == "potato")
    check("ep_map: node without blade -> local blade", m.get("localhost:11441") == "ws")
    check("ep_map: endpoint-less node skipped", all("inert" not in k for k in m))
    check("ep_map: non-dict cfg skipped", len(m) == 3, str(m))


def t_blade_for_endpoint():
    m = {"10.0.0.9:11434": "potato"}
    check("blade_for_ep: known endpoint -> its blade",
          B.blade_for_endpoint(m, _endpoint_key, "http://10.0.0.9:11434/v1", "ws") == "potato")
    check("blade_for_ep: unknown endpoint -> local (degrade-open)",
          B.blade_for_endpoint(m, _endpoint_key, "http://1.2.3.4:9/v1", "ws") == "ws")


def t_blade_vram_budget_degrade_open():
    pool = {"ws": {"vram_budget_mb": 23000}, "potato": {"vram_budget_mb": 8000},
            "zero": {"vram_budget_mb": 0}}
    check("budget: known blade -> its budget", B.blade_vram_budget(pool, "potato", 23000) == 8000)
    check("budget: local blade -> its budget", B.blade_vram_budget(pool, "ws", 23000) == 23000)
    check("budget: UNKNOWN blade -> local scalar (degrade-open)",
          B.blade_vram_budget(pool, "ghost", 23000) == 23000)
    check("budget: zero/missing budget -> local scalar (degrade-open)",
          B.blade_vram_budget(pool, "zero", 23000) == 23000)


def t_admission_decision():
    """The V5 headline: the SAME co-load (used+est+reserve) is DENIED against a small
    remote blade's budget yet ADMITTED against the LOCAL scalar (the default-off path).
    Mirrors _admit's comparison `(used + est + reserve) <= budget` with synthetic data."""
    LOCAL_SCALAR = 23000          # == server VRAM_BUDGET_MB default (the default-off budget)
    pool = {"ws": {"vram_budget_mb": LOCAL_SCALAR}, "potato": {"vram_budget_mb": 8000}}
    ep_map = {"10.0.0.9:11434": "potato"}
    used, est, reserve = 6000, 2000, 1000     # co-load footprint = 9000 MB

    def admits(budget):
        return (used + est + reserve) <= budget

    # DEFAULT-OFF: budget is the LOCAL scalar regardless of which node -> 9000 <= 23000.
    off_budget = LOCAL_SCALAR
    check("admit(default-off): remote co-load fits the local scalar -> ADMIT",
          admits(off_budget) is True)

    # MULTIBLADE-ON: the remote node is admitted against ITS blade (potato=8000) -> DENY.
    on_blade = B.blade_for_endpoint(ep_map, _endpoint_key, "http://10.0.0.9:11434/v1", "ws")
    on_budget = B.blade_vram_budget(pool, on_blade, LOCAL_SCALAR)
    check("admit(multiblade-on): remote node resolves to its blade", on_blade == "potato")
    check("admit(multiblade-on): 9000 over potato's 8000 -> DENY", admits(on_budget) is False)

    # MULTIBLADE-ON, smaller footprint UNDER the blade budget -> ADMIT.
    used2 = 4000                              # 4000+2000+1000 = 7000 <= 8000
    check("admit(multiblade-on): 7000 under potato's 8000 -> ADMIT",
          (used2 + est + reserve) <= on_budget)

    # DEGRADE-OPEN: an unknown remote blade -> the local scalar -> ADMIT (never wedge).
    unk_budget = B.blade_vram_budget(pool, "ghost-blade", LOCAL_SCALAR)
    check("admit(degrade-open): unknown blade -> local scalar -> ADMIT",
          admits(unk_budget) is True and unk_budget == LOCAL_SCALAR)


def main():
    t_local_blade_name()
    t_load_blade_pool_default()
    t_load_blade_pool_overrides()
    t_endpoint_blade_map()
    t_blade_for_endpoint()
    t_blade_vram_budget_degrade_open()
    t_admission_decision()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
