#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_principal (WS-A10 scoped tokens) + mios_crl (revocation). Pure stdlib, no server.py/HTTP/DB/pytest. Verifies issue->verify round-trip, signature tamper rejection, wrong-secret rejection, expiry (deterministic `now`), required-scope enforcement, CRL revocation (is_revoked refuses a valid token), and the CRL.load shapes.
# AI-related: ./mios_principal.py, ./mios_crl.py
# AI-functions: check, main
"""Unit tests for mios_principal + mios_crl (WS-A10)."""

import sys

import mios_principal as mp
import mios_crl as crl

_fails = 0
SECRET = "test-secret-key"


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_roundtrip():
    tok = mp.issue_token("alice", ["dispatch", "read"], secret=SECRET, ttl_s=100, now=1000)
    ok, claims = mp.verify_token(tok, secret=SECRET, now=1050)
    check("roundtrip: verifies", ok is True, str(claims))
    check("roundtrip: subject", claims["sub"] == "alice")
    check("roundtrip: scopes sorted+deduped", claims["scopes"] == ["dispatch", "read"])
    check("roundtrip: exp = iat+ttl", claims["exp"] == 1100 and claims["iat"] == 1000)
    check("roundtrip: has token id", bool(claims.get("tid")))


def t_tamper():
    tok = mp.issue_token("bob", ["x"], secret=SECRET, ttl_s=100, now=0)
    payload, _, sig = tok.partition(".")
    forged = payload[:-2] + ("AA" if not payload.endswith("AA") else "BB") + "." + sig
    ok, reason = mp.verify_token(forged, secret=SECRET, now=1)
    check("tamper: altered payload rejected", ok is False, reason)
    ok2, r2 = mp.verify_token(tok, secret="wrong-secret", now=1)
    check("tamper: wrong secret rejected", ok2 is False and "signature" in str(r2))
    check("tamper: malformed token rejected", mp.verify_token("garbage", secret=SECRET)[0] is False)


def t_expiry():
    tok = mp.issue_token("c", ["s"], secret=SECRET, ttl_s=10, now=1000)
    check("expiry: valid before exp", mp.verify_token(tok, secret=SECRET, now=1009)[0] is True)
    ok, reason = mp.verify_token(tok, secret=SECRET, now=1010)
    check("expiry: rejected at exp", ok is False and reason == "expired")
    check("expiry: rejected after exp", mp.verify_token(tok, secret=SECRET, now=99999)[0] is False)


def t_scope():
    tok = mp.issue_token("d", ["dispatch"], secret=SECRET, ttl_s=100, now=0)
    check("scope: required present -> ok", mp.verify_token(tok, secret=SECRET, now=1, required_scope="dispatch")[0] is True)
    ok, reason = mp.verify_token(tok, secret=SECRET, now=1, required_scope="admin")
    check("scope: required missing -> deny", ok is False and "scope" in str(reason))


def t_revocation():
    tok = mp.issue_token("e", ["s"], secret=SECRET, ttl_s=100, now=0, tid="tok-e")
    c = crl.CRL()
    check("crl: not revoked initially", mp.verify_token(tok, secret=SECRET, now=1, revoked=c.is_revoked)[0] is True)
    c.revoke("tok-e")
    ok, reason = mp.verify_token(tok, secret=SECRET, now=1, revoked=c.is_revoked)
    check("crl: revoked token refused", ok is False and reason == "revoked")
    c.restore("tok-e")
    check("crl: restored token ok again", mp.verify_token(tok, secret=SECRET, now=1, revoked=c.is_revoked)[0] is True)


def t_crl_load():
    check("crl.load: list", crl.CRL.load(["a", "b"]).is_revoked("a"))
    check("crl.load: dict revoked[]", crl.CRL.load({"revoked": ["x"]}).is_revoked("x"))
    check("crl.load: malformed -> empty", len(crl.CRL.load("nonsense")) == 0)
    c = crl.CRL(["a"]); c.merge(["b", "c"])
    check("crl: merge unions", c.ids() == ["a", "b", "c"])


def main():
    t_roundtrip()
    t_tamper()
    t_expiry()
    t_scope()
    t_revocation()
    t_crl_load()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
