#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_route_reload sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_route_reload."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_route_reload import RouteTableManager

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    mgr = RouteTableManager({"mios-light": {"port": 11450}})
    check("initial version is 1", mgr.version == 1)
    check("get route returns light", mgr.get_route("mios-light") == {"port": 11450})

    v2 = mgr.reload_routes({"mios-heavy": {"port": 11441}})
    check("version incremented to 2", v2 == 2)
    check("new route loaded", mgr.get_route("mios-heavy") == {"port": 11441})
    check("old route cleared", mgr.get_route("mios-light") is None)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
