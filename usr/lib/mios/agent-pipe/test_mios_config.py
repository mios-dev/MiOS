#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_config (refactor WS R1 config-constants extraction). Pure stdlib, no server.py/DB...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_config_py.md
"""Unit tests for mios_config (refactor R1)."""

import os
import sys

import mios_config as c

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_import():
    check("import: module loaded", c is not None)
    check("import: log name", c.log.name == "mios-agent-pipe")


def t_toml_section():
    d = c._toml_section("ai")
    check("toml_section: returns dict", isinstance(d, dict), type(d).__name__)
    miss = c._toml_section("definitely_not_a_real_section_xyz")
    check("toml_section: missing -> {}", miss == {})


def t_cfg_num():
    env = "MIOS_TEST_CFG_NUM_XYZ"
    os.environ.pop(env, None)
    os.environ[env] = "5"
    check("cfg_num: env override wins", c._cfg_num({"k": 3}, env, "k", 1) == 5)
    os.environ.pop(env, None)
    check("cfg_num: table value", c._cfg_num({"k": 3}, env, "k", 1) == 3)
    check("cfg_num: literal default", c._cfg_num({}, env, "k", 7) == 7)
    check("cfg_num: preserves table 0", c._cfg_num({"k": 0}, env, "k", 7) == 0)
    check("cfg_num: preserves default 0", c._cfg_num({}, env, "k", 0) == 0)
    check("cfg_num: float cast", c._cfg_num({"k": "1.5"}, env, "k", 0.0, float) == 1.5)
    os.environ[env] = "notanumber"
    check("cfg_num: bad env -> table", c._cfg_num({"k": 9}, env, "k", 1) == 9)
    os.environ.pop(env, None)


def t_dispatch_num():
    env = "MIOS_TEST_DISPATCH_NUM_XYZ"
    os.environ.pop(env, None)
    check("dispatch_num: literal default",
          c._dispatch_num(env, "no_such_dispatch_key_xyz", 4) == 4)
    os.environ[env] = "11"
    check("dispatch_num: env override",
          c._dispatch_num(env, "no_such_dispatch_key_xyz", 4) == 11)
    os.environ.pop(env, None)
    check("dispatch_num: preserves default 0",
          c._dispatch_num(env, "no_such_dispatch_key_xyz", 0) == 0)
    check("dispatch_num: _DISPATCH_TOML is dict", isinstance(c._DISPATCH_TOML, dict))


def t_constants():
    check("const: PORT int", isinstance(c.PORT, int))
    check("const: MCP_SERVER_PORT int", isinstance(c.MCP_SERVER_PORT, int))
    check("const: _LIGHT_BASE localhost",
          isinstance(c._LIGHT_BASE, str) and c._LIGHT_BASE.startswith("http://localhost:"),
          c._LIGHT_BASE)
    check("const: BACKEND str no trailing slash",
          isinstance(c.BACKEND, str) and not c.BACKEND.endswith("/"), c.BACKEND)
    check("const: BACKEND_MODEL str", isinstance(c.BACKEND_MODEL, str))
    check("const: _BACKEND_HOSTPORT derived from BACKEND",
          c._BACKEND_HOSTPORT == c.BACKEND.split("://")[-1].split("/")[0])
    check("const: _BACKEND_IS_LIGHT bool", isinstance(c._BACKEND_IS_LIGHT, bool))
    check("const: _AUTH_HOSTPORTS is set with backend",
          isinstance(c._AUTH_HOSTPORTS, set) and c._BACKEND_HOSTPORT in c._AUTH_HOSTPORTS)
    check("const: _AGENT_AUTH_BY_HOSTPORT dict", isinstance(c._AGENT_AUTH_BY_HOSTPORT, dict))
    check("const: CLIENT_TOOLS_PASSTHROUGH bool", isinstance(c.CLIENT_TOOLS_PASSTHROUGH, bool))
    check("const: _TOOL_BACKEND str", isinstance(c._TOOL_BACKEND, str))
    check("const: _TOOL_BACKEND_MODEL str", isinstance(c._TOOL_BACKEND_MODEL, str))
    check("const: _HEAVY_PROBE_TTL float", isinstance(c._HEAVY_PROBE_TTL, float))
    check("const: _INGRESS_KEY str", isinstance(c._INGRESS_KEY, str))
    check("const: _STACK_MODEL str", isinstance(c._STACK_MODEL, str))
    check("const: _MICRO_MODEL str", isinstance(c._MICRO_MODEL, str))
    check("const: _MICRO_ENDPOINT str no trailing slash",
          isinstance(c._MICRO_ENDPOINT, str) and not c._MICRO_ENDPOINT.endswith("/"))
    check("const: _MICRO_BASE no trailing /v1",
          isinstance(c._MICRO_BASE, str) and not c._MICRO_BASE.endswith("/v1"))


def main():
    t_import()
    t_toml_section()
    t_cfg_num()
    t_dispatch_num()
    t_constants()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
