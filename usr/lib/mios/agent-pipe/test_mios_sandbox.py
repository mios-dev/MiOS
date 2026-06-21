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


def t_bwrap():
    cmd = ["powershell_run", "--", "echo hi"]
    # 'read' tier (none) -> run direct, no wrapper
    none_argv = sb.build_bwrap_argv(sb.resolve_profile("read"), cmd)
    check("bwrap: none tier runs direct (cmd unchanged)", none_argv == cmd)
    # 'write' tier (workspace, ro-root, network) + a workspace
    wp = sb.resolve_profile("write")
    wa = sb.build_bwrap_argv(wp, cmd, workspace="/var/lib/mios/ai/dispatch/x-1")
    check("bwrap: write starts with bwrap", wa[0] == "bwrap")
    check("bwrap: write has --unshare-all + --die-with-parent", "--unshare-all" in wa and "--die-with-parent" in wa)
    check("bwrap: write re-adds net (--share-net)", "--share-net" in wa)
    check("bwrap: write read-only root (--ro-bind / /)", "--ro-bind" in wa and wa[wa.index("--ro-bind")+1:wa.index("--ro-bind")+3] == ["/", "/"])
    check("bwrap: write binds the workspace rw", "--bind" in wa and "/var/lib/mios/ai/dispatch/x-1" in wa)
    check("bwrap: write proc/dev/tmpfs", "--proc" in wa and "--dev" in wa and "--tmpfs" in wa)
    check("bwrap: cmd after the -- separator", wa[wa.index("--", 1):] == ["--"] + cmd)
    # 'interactive' tier (strict, NO network)
    sa = sb.build_bwrap_argv(sb.resolve_profile("interactive"), cmd, workspace="/ws")
    check("bwrap: strict has NO --share-net (no network)", "--share-net" not in sa)
    check("bwrap: strict still --unshare-all", "--unshare-all" in sa)
    # unknown tier fails CLOSED -> strict (no net)
    uk = sb.build_bwrap_argv(sb.resolve_profile("bogus"), cmd, workspace="/ws")
    check("bwrap: unknown tier fail-closed (confined, no net)", uk[0] == "bwrap" and "--share-net" not in uk)


def t_sandbox_exec_prefix():
    # 'read' tier (none) -> no prefix (run direct, unwrapped)
    check("prefix: none tier -> [] (no wrap)",
          sb.sandbox_exec_prefix(sb.resolve_profile("read")) == [])
    # 'write' tier (workspace, network) -> enforce + --net + --workspace, ends in --
    wp = sb.sandbox_exec_prefix(sb.resolve_profile("write"), workspace="/ws/x-1")
    check("prefix: write level enforce", wp[:3] == ["mios-sandbox-exec", "--level", "enforce"])
    check("prefix: write keeps net (--net)", "--net" in wp)
    check("prefix: write binds workspace", "--workspace" in wp and "/ws/x-1" in wp)
    check("prefix: write ends in -- separator", wp[-1] == "--")
    # 'interactive' tier (strict, NO network) -> enforce, no --net
    sp = sb.sandbox_exec_prefix(sb.resolve_profile("interactive"), workspace="/ws")
    check("prefix: strict no --net (no egress)", "--net" not in sp and sp[-1] == "--")
    # unknown tier fails CLOSED -> confined, no net
    uk = sb.sandbox_exec_prefix(sb.resolve_profile("bogus"), workspace="/ws")
    check("prefix: unknown tier fail-closed (confined, no net)",
          uk and uk[0] == "mios-sandbox-exec" and "--net" not in uk)


def main():
    t_tiers()
    t_fail_closed()
    t_explicit()
    t_workspace()
    t_shape()
    t_bwrap()
    t_sandbox_exec_prefix()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
