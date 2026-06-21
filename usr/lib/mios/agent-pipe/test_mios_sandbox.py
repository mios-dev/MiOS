#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_sandbox (WS-A13 risk-tier dispatch sandbox). Pure stdlib, no server.py/bwrap/podman/pytest. Verifies the tier->profile mapping (read=none, write=workspace, interactive=strict), the explicit override, the FAIL-CLOSED stance (unknown/missing tier -> strictest, never none -- the security-critical property), and the per-dispatch workspace path (hashed verb, sanitized uniq, under the base).
# AI-related: ./mios_sandbox.py
# AI-functions: check, main
"""Unit tests for mios_sandbox (WS-A13)."""

import sys

import mios_sandbox as sb

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_tiers():
    r = sb.resolve_profile("read")
    check("read: mechanism none", r.mechanism == "none" and r.confined is False)
    check("read: has network", r.network is True)
    w = sb.resolve_profile("write")
    check("write: workspace mechanism", w.mechanism == "workspace" and w.confined is True)
    check("write: needs workspace + ro root", w.workspace is True and w.read_only_root is True)
    i = sb.resolve_profile("interactive")
    check("interactive: strict", i.mechanism == "strict")
    check("interactive: NO network", i.network is False)


def t_fail_closed():
    # THE security-critical property: an unknown/missing tier must NOT be 'none'.
    for bad in ["", None, "supervisor", "weird", "READ-ish"]:
        p = sb.resolve_profile(bad)
        check(f"fail-closed: {bad!r} -> strict (never none)", p.mechanism == "strict" and p.confined is True, p.to_dict())


def t_explicit():
    check("explicit: 'none' override", sb.resolve_profile("interactive", explicit="none").mechanism == "none")
    check("explicit: 'strict' override", sb.resolve_profile("read", explicit="strict").mechanism == "strict")
    check("explicit: tier-name override", sb.resolve_profile("read", explicit="write").mechanism == "workspace")
    check("explicit: unknown override -> strict (fail-closed)",
          sb.resolve_profile("read", explicit="yolo").mechanism == "strict")


def t_workspace():
    p = sb.workspace_path("powershell_run", "abc123")
    check("workspace: under base", p.startswith("/var/lib/mios/ai/dispatch/"))
    check("workspace: verb hashed (not raw)", "powershell_run" not in p)
    check("workspace: deterministic per (verb,uniq)", p == sb.workspace_path("powershell_run", "abc123"))
    check("workspace: distinct verbs differ", sb.workspace_path("a", "u") != sb.workspace_path("b", "u"))
    check("workspace: sanitizes uniq (no traversal)", "/" not in sb.workspace_path("v", "../../etc").rsplit("/", 1)[1])


def t_shape():
    d = sb.resolve_profile("write").to_dict()
    check("shape: keys", set(d) == {"tier", "mechanism", "workspace", "read_only_root", "network", "confined"})


def main():
    t_tiers()
    t_fail_closed()
    t_explicit()
    t_workspace()
    t_shape()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
