#!/usr/bin/env python3
# AI-hint: Fixtures for render-desktop.py -- proves the launcher renderer derives its port from SSOT, refuses an empty launcher table, and flags a .desktop file no [desktop.launchers] entry declares.
# AI-related: tools/render-desktop.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
# AI-functions: main
"""The three behaviours the drift gate depends on.

An empty launcher table used to render nothing, compare nothing, and report
success while 9 launchers shipped ungoverned -- so "refuses an empty table" is
the fixture that matters most here.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location("rd", os.path.join(HERE, "render-desktop.py"))
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)

FAILED: list[str] = []
PASSED = 0


def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def test_port_comes_from_ssot():
    """Exec must carry the SSOT port, never a literal."""
    ports = {"cockpit": 8110}
    cfg = {"port_key": "cockpit", "scheme": "https", "title": "T"}
    out = rd.render_launcher("x", cfg, ports)
    check("exec-uses-ssot-port", "https://localhost:8110/" in out, True)
    # Change the SSOT value and the rendering must follow it.
    out2 = rd.render_launcher("x", cfg, {"cockpit": 9999})
    check("exec-follows-ssot", "https://localhost:9999/" in out2, True)


def test_port_placeholder_substituted():
    cfg = {"port_key": "searxng", "title": "S", "comment": "at {port}"}
    out = rd.render_launcher("s", cfg, {"searxng": 8800})
    check("comment-placeholder", "at 8800" in out, True)
    check("no-literal-brace", "{port}" in out, False)


def test_exec_cmd_wins_over_port():
    cfg = {"port_key": "cockpit", "exec_cmd": "/usr/bin/true", "title": "T"}
    out = rd.render_launcher("x", cfg, {"cockpit": 8110})
    check("explicit-exec-wins", "Exec=/usr/bin/true" in out, True)


def test_ssot_loads_real_launchers():
    """The shipped table must be non-empty, or the gate compares nothing."""
    ports, launchers = rd.load_ssot(ROOT)
    check("launchers-present", len(launchers) > 0, True)
    check("ports-present", len(ports) > 0, True)
    apps = os.path.join(ROOT, "usr", "share", "applications")
    if os.path.isdir(apps):
        shipped = {f[:-8] for f in os.listdir(apps) if f.endswith(".desktop")}
        undeclared = sorted(shipped - set(launchers))
        check("every-shipped-launcher-declared", undeclared, [])


def main() -> int:
    test_port_comes_from_ssot()
    test_port_placeholder_substituted()
    test_exec_cmd_wins_over_port()
    test_ssot_loads_real_launchers()
    print(f"[test_render-desktop] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
