# AI-hint: Standalone unit test for tools/generate-egress-firewall (#54 egress firewall): build_ruleset emits a uid-scoped nftables ruleset with the always-allowed nets, per-mode final action (off=no-op, audit=log+accept, enforce=log+drop), and v4/v6 allowlist rules. Pure string assertions -- no nft binary needed (a separate nft -c check covers syntax on hosts that have it).
# AI-related: tools/generate-egress-firewall.py
# AI-functions: _check, _load_tool, t_always, t_modes, t_allow, t_scope, main
"""Standalone unit test for the #54 egress-firewall generator.

Pure: asserts the structure of build_ruleset's output (uid scoping, always-allowed
nets, per-mode final rule, allowlist) without invoking nft, so it runs anywhere in
the drift-gate. nft *syntax* is validated separately with `nft -c` where the
binary exists. Loads the generator from tools/ via SourceFileLoader.

Run:  python test_mios_egress.py
"""

import importlib.machinery
import importlib.util
import os
import sys

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _load_tool():
    p = os.environ.get("MIOS_EGRESS_TOOL")
    if not p:
        here = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
        p = os.path.join(repo, "tools", "generate-egress-firewall.py")
    if not os.path.isfile(p):
        print(f"[SKIP] generate-egress-firewall.py not found at {p}")
        print("\nskipped (0 checks)")
        sys.exit(0)
    loader = importlib.machinery.SourceFileLoader("egw", p)
    spec = importlib.util.spec_from_loader("egw", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


M = _load_tool()


def t_always() -> None:
    rs = M.build_ruleset("off", [], "mios-ai")
    _check("always: table inet mios_egress", "table inet mios_egress" in rs)
    _check("always: hook output", "type filter hook output" in rs)
    _check("always: loopback iface", 'oifname "lo" accept' in rs)
    _check("always: v4 loopback", "ip daddr 127.0.0.0/8 accept" in rs)
    _check("always: v6 loopback", "ip6 daddr ::1 accept" in rs)
    _check("always: tailnet", "ip daddr 100.64.0.0/10 accept" in rs)
    _check("always: WSL gateway", "ip daddr 172.16.0.0/12 accept" in rs)
    _check("always: AI-hint header", rs.splitlines()[0].startswith("# AI-hint:"))


def t_modes() -> None:
    off = M.build_ruleset("off", [], "mios-ai")
    _check("off: no-op accept, no drop", "mode=off -> no-op" in off and "drop" not in off)
    audit = M.build_ruleset("audit", [], "mios-ai")
    _check("audit: log + accept, no drop",
           "mios-egress-audit" in audit and " drop" not in audit)
    enforce = M.build_ruleset("enforce", [], "mios-ai")
    _check("enforce: log + drop",
           "mios-egress-drop" in enforce and enforce.rstrip().endswith("}"))
    _check("enforce: drop present", "drop" in enforce)
    # unknown mode falls back to off (no-op) -- never accidentally enforce
    weird = M.build_ruleset("banana", [], "mios-ai")
    _check("unknown mode -> off no-op", "no-op" in weird and "drop" not in weird)


def t_allow() -> None:
    rs = M.build_ruleset("enforce", ["203.0.113.0/24", "198.51.100.7", "2001:db8::/32"], "mios-ai")
    _check("allow: v4 set rule", "ip daddr {" in rs and "203.0.113.0/24" in rs)
    _check("allow: v6 set rule", "ip6 daddr {" in rs and "2001:db8::/32" in rs)
    _check("allow: empty -> no allow rule",
           "ip daddr {" not in M.build_ruleset("enforce", [], "mios-ai"))


def t_scope() -> None:
    rs = M.build_ruleset("enforce", [], "mios-agent")
    _check("scope: uid-scoped to the agent user",
           'meta skuid != "mios-agent" accept' in rs)
    _check("scope: other users pass untouched (rule precedes drop)",
           rs.index("skuid") < rs.index("drop"))


def main() -> int:
    for t in (t_always, t_modes, t_allow, t_scope):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
