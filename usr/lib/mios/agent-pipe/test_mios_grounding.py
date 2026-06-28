#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_grounding (refactor R2 leaf extraction of the per-turn ENV-GROUNDING cluster). Pure stdlib, no server.py/DB/network/pytest. Stubs the injected _client_env_var ContextVar + _current_date_str helper via configure(), then pins the grounding invariants: _env_block() emits a parseable <env> key:value block carrying current_date/surface/host/cwd/location/location_source from the live forwarded env; _env_grounding() composes the <env> block + the non-negotiable local-only identity guard + self-architecture + temporal + client prose; _capability_grounding() renders the live verb catalog as 'section: names' lines; _client_env() normalises OWUI metadata.variables (braced keys, sentinels dropped) into the flat env dict; _host_timezone()/_get_os_info() return strings. Guards the extracted leaf so a later move can't silently change the system-role grounding shape.
# AI-related: ./mios_grounding.py
# AI-functions: check, FakeVar, FakeHeaders, t_capability, t_host_os, t_client_env, t_env_block, t_env_grounding, t_principal_bind, main
"""Unit tests for mios_grounding (refactor R2)."""

import logging
import os
import sys

import mios_grounding as g

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


class FakeVar:
    """Minimal ContextVar stand-in (only .get() is used by the cluster)."""

    def __init__(self, value):
        self._v = value

    def get(self):
        return self._v


def t_capability():
    cat = {
        "open_app": {"section": "Apps", "model_name": "open_app"},
        "close_app": {"section": "Apps", "model_name": "close_app"},
        "rare_one": {"section": "Apps", "model_name": "rare_one", "tier": "rare"},
        "web_search": {"section": "Web"},
    }
    out = g._capability_grounding(cat)
    check("capability: is str", isinstance(out, str))
    check("capability: header present", "YOUR ACTUAL CAPABILITIES" in out)
    check("capability: shows section", "Apps:" in out and "Web:" in out)
    check("capability: shows verb name", "open_app" in out and "web_search" in out)
    check("capability: omits rare-tier verb", "rare_one" not in out)
    check("capability: empty catalog -> ''", g._capability_grounding({}) == "")


def t_host_os():
    tz = g._host_timezone()
    check("host_timezone: returns str", isinstance(tz, str))
    osi = g._get_os_info()
    check("get_os_info: non-empty str", isinstance(osi, str) and len(osi) > 0, repr(osi))


def t_client_env():
    body = {
        "metadata": {
            "variables": {
                "{{USER_LOCATION}}": "Paris, France",
                "{{CURRENT_TIMEZONE}}": "Europe/Paris",
                "{{USER_LANGUAGE}}": "fr-FR",
                "{{CURRENT_DATE}}": "2026-06-25",
                "{{USER_NAME}}": "Unknown",  # sentinel -> must be dropped
            }
        },
        "user": "fallback-name",
    }
    out = g._client_env(body)
    check("client_env: is dict", isinstance(out, dict))
    check("client_env: location", out.get("location") == "Paris, France")
    check("client_env: timezone", out.get("timezone") == "Europe/Paris")
    check("client_env: language", out.get("language") == "fr-FR")
    check("client_env: date", out.get("date") == "2026-06-25")
    # 'Unknown' is an env sentinel -> dropped, so the OpenAI `user` field fills in.
    check("client_env: sentinel dropped, user fallback", out.get("user_name") == "fallback-name")
    check("client_env: non-dict body -> {}", g._client_env(None) == {})


def t_env_block():
    g.configure(
        client_env_var=FakeVar({
            "surface": "cli", "host": "mios-host", "cwd": "/srv/work",
            "location": "Testville", "user_name": "Ada", "language": "en-US",
        }),
        current_date_str=lambda: "2026-06-25",
    )
    blk = g._env_block()
    check("env_block: is str", isinstance(blk, str))
    check("env_block: opens <env>", blk.lstrip().startswith("<env>"))
    check("env_block: closes </env>", blk.rstrip().endswith("</env>"))
    for k, v in (("current_date", "2026-06-25"), ("surface", "cli"),
                 ("host", "mios-host"), ("cwd", "/srv/work"),
                 ("location", "Testville"), ("location_source", "client"),
                 ("user", "Ada"), ("language", "en-US")):
        check(f"env_block: {k}:{v}", f"{k}: {v}" in blk, blk)
    # No location forwarded + no config -> explicit UNKNOWN, never a fabricated city.
    g.configure(client_env_var=FakeVar({"surface": "cli"}))
    blk2 = g._env_block()
    check("env_block: unknown location is explicit", "location: UNKNOWN" in blk2, blk2)


def t_env_grounding():
    g.configure(
        client_env_var=FakeVar({"surface": "owui", "location": "Testville"}),
        current_date_str=lambda: "2026-06-25",
    )
    out = g._env_grounding()
    check("env_grounding: is str", isinstance(out, str))
    check("env_grounding: includes <env> block", "<env>" in out)
    check("env_grounding: identity guard (local)", "LOCAL" in out and "Identity" in out)
    check("env_grounding: self-architecture", "MiOS" in out)
    check("env_grounding: temporal grounding", "Temporal grounding" in out)
    check("env_grounding: anti-stale warning", "stale" in out.lower())


def main():
    t_capability()
    t_host_os()
    t_client_env()
    t_env_block()
    t_env_grounding()
    print(f"\n{'ALL PASS' if _fails == 0 else str(_fails) + ' FAIL(S)'}")
    sys.exit(1 if _fails else 0)


if __name__ == "__main__":
    main()
