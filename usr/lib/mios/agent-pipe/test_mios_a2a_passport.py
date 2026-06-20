# AI-hint: Standalone unit test for mios_a2a_principal (#60 WS-6 signed A2A delegation principal): claim shape, text-binding digest, and the send->verify roundtrip with injected fake sign/verify -- no server.py / live keys.
# AI-related: mios_a2a_principal
# AI-functions: _check, t_claims, t_roundtrip, t_tamper, t_unsigned, t_absent, main
"""Standalone unit test for mios_a2a_principal (WS-6 signed delegation principal).

Pure stdlib + the sibling module only -- no server.py / Ed25519 keys. The real
crypto is the agent passport's _passport_sign/_passport_verify (covered by the
passport tests + operator on MiOS-DEV); here we inject fakes to prove the
deterministic glue: claim shape, text-binding, and the absent/unsigned/tamper/ok
branches the receive path relies on.

Run:  python test_mios_a2a_passport.py
"""

import sys

import mios_a2a_principal as P

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# A fake passport pair: sign returns an opaque envelope binding (table, claims);
# verify accepts only an envelope this signer produced for the SAME (table, claims).
def _fake_sign(table, claims):
    return {"t": table, "h": P.text_digest(repr(sorted(claims.items()))), "sig": "FAKE"}


def _fake_verify(envelope, payload):
    table, claims = payload
    want = P.text_digest(repr(sorted(claims.items())))
    if envelope.get("t") == table and envelope.get("h") == want:
        return True, "ok"
    return False, "invalid_signature"


def _nokey_sign(table, claims):
    return None   # no key provisioned


def t_claims() -> None:
    c = P.build_claims("agent-pipe", "alice", "peerX", "ctx1", "open notepad")
    _check("claims: agent", c["agent"] == "agent-pipe")
    _check("claims: principal", c["principal"] == "alice")
    _check("claims: peer", c["peer"] == "peerX")
    _check("claims: context", c["context"] == "ctx1")
    _check("claims: text digest bound",
           c["text_sha256"] == P.text_digest("open notepad"))
    _check("claims: empty principal -> '' (autonomous)",
           P.build_claims("a", "", "p", "", "x")["principal"] == "")


def _msg(meta):
    return {P.METADATA_KEY: meta}


def t_roundtrip() -> None:
    md = P.build_metadata("agent-pipe", "alice", "peerX", "ctx1", "open notepad", _fake_sign)
    _check("send: signed (passport present)", isinstance(md.get("passport"), dict))
    v, reason, claims = P.verify(_msg(md), "open notepad", _fake_verify)
    _check("roundtrip: verdict True", v is True, reason)
    _check("roundtrip: claims carried", claims.get("principal") == "alice")


def t_tamper() -> None:
    md = P.build_metadata("agent-pipe", "alice", "peerX", "ctx1", "open notepad", _fake_sign)
    # deliver a DIFFERENT instruction than was signed
    v, reason, _ = P.verify(_msg(md), "rm -rf /", _fake_verify)
    _check("tamper: rejected", v is False)
    _check("tamper: caught by digest (before sig)", reason == "text_digest_mismatch", reason)
    # also: a valid-text but forged signature
    md["passport"]["sig"] = "FORGED"; md["passport"]["h"] = "wronghash"
    v2, r2, _ = P.verify(_msg(md), "open notepad", _fake_verify)
    _check("tamper: bad signature rejected", v2 is False, r2)


def t_unsigned() -> None:
    md = P.build_metadata("agent-pipe", "alice", "peerX", "ctx1", "hi", _nokey_sign)
    _check("unsigned: passport None when no key", md.get("passport") is None)
    v, reason, claims = P.verify(_msg(md), "hi", _fake_verify)
    _check("unsigned: verdict False", v is False)
    _check("unsigned: reason 'unsigned'", reason == "unsigned", reason)
    _check("unsigned: claims still readable", claims.get("agent") == "agent-pipe")


def t_absent() -> None:
    v, reason, claims = P.verify({}, "hi", _fake_verify)
    _check("absent: verdict None (legacy/non-MiOS peer)", v is None)
    _check("absent: reason 'absent'", reason == "absent")
    _check("absent: empty claims", claims == {})
    v2, r2, _ = P.verify(None, "hi", _fake_verify)
    _check("absent: None metadata tolerated", v2 is None and r2 == "absent")


def main() -> int:
    for t in (t_claims, t_roundtrip, t_tamper, t_unsigned, t_absent):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
