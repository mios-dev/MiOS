#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_arbiter (WS-9 out-of-process policy-arbiter decision core). Pure stdlib, no server.py/HTTP/DB/pytest. Verifies the rule order (deny-list always wins; exclusive allow-list; risk-tier ceiling; default allow), fail-closed handling of an unknown tier (ranks above top -> blocked when a block_tier is set), and the Verdict shape.
# AI-related: ./mios_arbiter.py
# AI-functions: check, main
"""Unit tests for mios_arbiter (WS-9)."""

import sys

import mios_arbiter as arb

_fails = 0
TIERS = ("read", "write", "interactive")


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_default_allow():
    v = arb.decide("list_windows", "read", tiers=TIERS)
    check("default: no policy -> allow", v.allow and v.rule == "ok")


def t_deny_list():
    v = arb.decide("powershell_run", "interactive", deny=["powershell_run"], tiers=TIERS)
    check("deny: deny-list refuses", not v.allow and v.rule == "deny_list")
    # deny wins even if also on allow-list.
    v2 = arb.decide("x", "read", deny=["x"], allow=["x"], tiers=TIERS)
    check("deny: deny beats allow", not v2.allow and v2.rule == "deny_list")


def t_allow_list():
    v = arb.decide("web_search", "read", allow=["web_search"], tiers=TIERS)
    check("allow: listed verb allowed", v.allow and v.rule == "allow_list")
    v2 = arb.decide("open_app", "write", allow=["web_search"], tiers=TIERS)
    check("allow: exclusive -> unlisted denied", not v2.allow and v2.rule == "allow_list")
    v3 = arb.decide("anything", "read", allow=[], tiers=TIERS)
    check("allow: empty allow-list denies all", not v3.allow)
    v4 = arb.decide("anything", "read", tiers=TIERS)  # allow=None -> no allow-list
    check("allow: None means no allow-list (default allow)", v4.allow)


def t_block_tier():
    v = arb.decide("pc_type", "interactive", block_tier="interactive", tiers=TIERS)
    check("tier: at block tier -> deny", not v.allow and v.rule == "block_tier")
    v2 = arb.decide("open_app", "write", block_tier="interactive", tiers=TIERS)
    check("tier: below block tier -> allow", v2.allow)
    v3 = arb.decide("anything", "write", block_tier="write", tiers=TIERS)
    check("tier: at/above block tier (write>=write) -> deny", not v3.allow)


def t_fail_closed():
    # An unknown tier ranks above the top -> blocked when any block_tier is set.
    v = arb.decide("mystery", "superuser", block_tier="interactive", tiers=TIERS)
    check("fail-closed: unknown tier ranks above top -> deny", not v.allow, f"{v.to_dict()}")


def t_shape():
    d = arb.decide("x", "read", tiers=TIERS).to_dict()
    check("shape: verdict dict", set(d) == {"allow", "reason", "rule"} and d["allow"] is True)


def main():
    t_default_allow()
    t_deny_list()
    t_allow_list()
    t_block_tier()
    t_fail_closed()
    t_shape()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
