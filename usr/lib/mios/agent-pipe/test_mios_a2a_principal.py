#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_a2a_principal (#60 WS-6 signed A2A delegation principal). Pure stdlib, no server.py/DB/pytest/network. Verifies text_digest determinism + SHA-256 correctness + input sensitivity + None/empty/int coercion, build_claims/build_metadata required keys+shapes+digest binding, and verify() round-trip: valid->True, tampered text->False(text_digest_mismatch BEFORE sig check), no-key/unsigned degrade->False(unsigned), absent block->None, bad signature->False. Injects fake sign_fn/verify_fn (no external Ed25519 key material).
# AI-related: ./mios_a2a_principal.py
# AI-functions: check, main
"""Unit tests for mios_a2a_principal (signed A2A delegation principal helpers)."""

import hashlib
import sys

import mios_a2a_principal as ap

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# --- injected crypto doubles (no external Ed25519 key material) -------------

def sign_real(table, fields):
    """Deterministic fake passport: binds to a hash of (table, sorted-fields)."""
    blob = table + "|" + repr(sorted(fields.items()))
    return {"sig": hashlib.sha256(blob.encode("utf-8")).hexdigest(), "table": table}


def sign_nokey(table, fields):
    """No key provisioned -> degrade-open (unsigned)."""
    return None


def verify_real(passport, key):
    """Re-derive what sign_real would produce and compare."""
    table, fields = key
    if not isinstance(passport, dict):
        return False, "no_envelope"
    expect = sign_real(table, fields)
    if passport.get("sig") == expect["sig"]:
        return True, "ok"
    return False, "bad_signature"


def verify_always_true(passport, key):
    return True, "ok"


def verify_should_not_run(passport, key):
    raise AssertionError("verify_fn must NOT be invoked when text digest mismatches")


# --- text_digest -------------------------------------------------------------

def t_text_digest():
    d = ap.text_digest("hello world")
    check("digest: matches stdlib sha256 hexdigest",
          d == hashlib.sha256(b"hello world").hexdigest(), d)
    check("digest: 64 hex chars", len(d) == 64 and all(c in "0123456789abcdef" for c in d))
    check("digest: deterministic across calls",
          ap.text_digest("same input") == ap.text_digest("same input"))
    check("digest: sensitive to single-char change",
          ap.text_digest("delegate task A") != ap.text_digest("delegate task B"))
    check("digest: whitespace is significant",
          ap.text_digest("a b") != ap.text_digest("a  b"))
    # None / empty coerce to the empty-string digest (str(text or "")).
    empty = hashlib.sha256(b"").hexdigest()
    check("digest: None -> empty-string digest", ap.text_digest(None) == empty)
    check("digest: '' -> empty-string digest", ap.text_digest("") == empty)
    check("digest: None == '' (both falsy->'')", ap.text_digest(None) == ap.text_digest(""))
    # Non-string inputs are stringified (str(text)).
    check("digest: int coerced via str()",
          ap.text_digest(123) == hashlib.sha256(b"123").hexdigest())
    # 0 is falsy -> str(0 or "") == "" -> empty digest (NOT "0"). Document the quirk.
    check("digest: 0 is falsy -> empty digest (not '0')", ap.text_digest(0) == empty)
    # unicode round-trips through utf-8
    check("digest: unicode utf-8 encoded",
          ap.text_digest("éè") == hashlib.sha256("éè".encode("utf-8")).hexdigest())


# --- build_claims ------------------------------------------------------------

def t_build_claims():
    c = ap.build_claims("agentX", "alice", "peer1", "ctx42", "do the thing")
    check("claims: exactly the 5 required keys",
          set(c.keys()) == {"agent", "principal", "peer", "context", "text_sha256"},
          sorted(c.keys()))
    check("claims: all values are str", all(isinstance(v, str) for v in c.values()))
    check("claims: agent passthrough", c["agent"] == "agentX")
    check("claims: principal passthrough", c["principal"] == "alice")
    check("claims: peer passthrough", c["peer"] == "peer1")
    check("claims: context passthrough", c["context"] == "ctx42")
    check("claims: text bound as digest, not raw text",
          c["text_sha256"] == ap.text_digest("do the thing") and "do the thing" not in c["text_sha256"])
    # None/empty principal == autonomous ("")
    auto = ap.build_claims("agentX", None, "peer1", "ctx42", "t")
    check("claims: None principal -> '' (autonomous)", auto["principal"] == "")
    none_all = ap.build_claims(None, None, None, None, None)
    check("claims: all-None -> all '' except digest",
          none_all["agent"] == "" and none_all["peer"] == "" and none_all["context"] == "")
    check("claims: all-None text -> empty-string digest",
          none_all["text_sha256"] == ap.text_digest(""))
    # non-string ids stringified
    numc = ap.build_claims(7, 8, 9, 10, "x")
    check("claims: numeric ids stringified", numc["agent"] == "7" and numc["context"] == "10")


# --- build_metadata ----------------------------------------------------------

def t_build_metadata():
    m = ap.build_metadata("agentX", "alice", "peer1", "ctx42", "task text", sign_real)
    check("metadata: exactly {claims, passport}", set(m.keys()) == {"claims", "passport"}, sorted(m.keys()))
    check("metadata: claims is the build_claims dict",
          m["claims"] == ap.build_claims("agentX", "alice", "peer1", "ctx42", "task text"))
    check("metadata: passport present when key provisioned", isinstance(m["passport"], dict))
    check("metadata: passport signs the TABLE constant",
          m["passport"].get("table") == ap.TABLE == "a2a_delegation")
    check("metadata: passport sig binds to the exact claims",
          m["passport"]["sig"] == sign_real(ap.TABLE, m["claims"])["sig"])
    # degrade-open: no key -> passport None but claims still ride along
    mu = ap.build_metadata("agentX", "alice", "peer1", "ctx42", "task text", sign_nokey)
    check("metadata: unsigned passport is None when no key", mu["passport"] is None)
    check("metadata: claims still present when unsigned", isinstance(mu["claims"], dict) and mu["claims"]["agent"] == "agentX")


# --- verify round-trip -------------------------------------------------------

def _wrap(meta):
    """Wrap a build_metadata() result under the on-wire METADATA_KEY envelope."""
    return {ap.METADATA_KEY: meta}


def t_verify_valid_roundtrip():
    text = "please summarize the report"
    meta = ap.build_metadata("agentX", "alice", "peer1", "ctx42", text, sign_real)
    verdict, reason, claims = ap.verify(_wrap(meta), text, verify_real)
    check("verify: valid self-built claim accepted", verdict is True, reason)
    check("verify: reason ok on success", reason == "ok")
    check("verify: returns the claims dict", claims == meta["claims"])


def t_verify_tampered_text():
    text = "transfer $10 to alice"
    meta = ap.build_metadata("agentX", "alice", "peer1", "ctx42", text, sign_real)
    # MITM swaps the delivered instruction while keeping the original envelope.
    verdict, reason, claims = ap.verify(_wrap(meta), "transfer $10000 to mallory", verify_real)
    check("verify: tampered text rejected", verdict is False, reason)
    check("verify: reason is text_digest_mismatch", reason == "text_digest_mismatch")
    check("verify: claims still returned on mismatch", claims == meta["claims"])
    # The digest check MUST run BEFORE signature verification.
    v2, r2, _ = ap.verify(_wrap(meta), "totally different task", verify_should_not_run)
    check("verify: digest checked before signature (verify_fn not called)",
          v2 is False and r2 == "text_digest_mismatch")


def t_verify_unsigned_degrade():
    text = "low-trust task"
    meta = ap.build_metadata("agentX", "", "peer1", "ctx42", text, sign_nokey)
    check("setup: unsigned meta has passport None", meta["passport"] is None)
    verdict, reason, claims = ap.verify(_wrap(meta), text, verify_should_not_run)
    check("verify: unsigned -> rejected (not None)", verdict is False, reason)
    check("verify: reason is unsigned", reason == "unsigned")
    check("verify: claims returned even when unsigned", claims == meta["claims"])
    # text mismatch takes precedence over unsigned (digest checked first)
    v2, r2, _ = ap.verify(_wrap(meta), "different", verify_should_not_run)
    check("verify: mismatch beats unsigned ordering", v2 is False and r2 == "text_digest_mismatch")


def t_verify_bad_signature():
    text = "signed task"
    meta = ap.build_metadata("agentX", "alice", "peer1", "ctx42", text, sign_real)
    verdict, reason, claims = ap.verify(_wrap(meta), text, verify_real)
    check("setup: valid before tamper", verdict is True)
    # Forge the passport sig (text digest still matches, so it reaches verify_fn).
    forged = _wrap({"claims": dict(meta["claims"]), "passport": {"sig": "deadbeef", "table": ap.TABLE}})
    v2, r2, _ = ap.verify(forged, text, verify_real)
    check("verify: bad signature rejected", v2 is False, r2)
    check("verify: reason from verify_fn on bad sig", r2 == "bad_signature")


def t_verify_claims_tampered_under_valid_sig():
    """If a claim field is altered after signing, the re-derived signature no
    longer matches -> verify_fn rejects (signature binds the whole claim set)."""
    text = "audit task"
    meta = ap.build_metadata("agentX", "alice", "peer1", "ctx42", text, sign_real)
    bad = dict(meta["claims"])
    bad["principal"] = "mallory"  # privilege escalation attempt, text digest untouched
    forged = _wrap({"claims": bad, "passport": meta["passport"]})
    v, r, _ = ap.verify(forged, text, verify_real)
    check("verify: tampered principal under old sig rejected", v is False, r)
    check("verify: reason bad_signature for claim tamper", r == "bad_signature")


def t_verify_absent_and_malformed():
    text = "x"
    # No principal block at all (legacy / non-MiOS peer).
    v, r, c = ap.verify({}, text, verify_should_not_run)
    check("verify: absent block -> verdict None", v is None and r == "absent")
    check("verify: absent -> empty claims dict", c == {})
    v2, r2, c2 = ap.verify(None, text, verify_should_not_run)
    check("verify: None metadata -> None/absent", v2 is None and r2 == "absent" and c2 == {})
    # metadata present but the principal value is not a dict
    v3, r3, _ = ap.verify({ap.METADATA_KEY: "not-a-dict"}, text, verify_should_not_run)
    check("verify: non-dict principal block -> None/absent", v3 is None and r3 == "absent")
    # non-dict metadata entirely
    v4, r4, _ = ap.verify("garbage", text, verify_should_not_run)
    check("verify: non-dict metadata -> None/absent", v4 is None and r4 == "absent")
    # block present, claims missing entirely -> {} claims, digest of "" won't match real text
    v5, r5, c5 = ap.verify({ap.METADATA_KEY: {"passport": {"sig": "z"}}}, "real text", verify_should_not_run)
    check("verify: missing claims -> {} and text mismatch (verify_fn unused)",
          v5 is False and r5 == "text_digest_mismatch" and c5 == {})
    # block present, claims is the wrong type -> coerced to {}
    v6, r6, c6 = ap.verify({ap.METADATA_KEY: {"claims": ["bad"], "passport": {"sig": "z"}}}, "", verify_always_true)
    # claims->{} , text_sha256 None vs digest("") -> mismatch
    check("verify: non-dict claims coerced to {} -> mismatch", v6 is False and r6 == "text_digest_mismatch" and c6 == {})


def t_verify_empty_text_consistency():
    """A claim built over empty text verifies against delivered empty/None text."""
    meta = ap.build_metadata("agentX", "", "peer1", "ctx42", "", sign_real)
    v, r, _ = ap.verify(_wrap(meta), "", verify_real)
    check("verify: empty-text claim accepts empty delivered", v is True, r)
    vn, rn, _ = ap.verify(_wrap(meta), None, verify_real)
    check("verify: empty-text claim accepts None delivered (both -> '' digest)", vn is True, rn)
    vx, rx, _ = ap.verify(_wrap(meta), "nonempty", verify_real)
    check("verify: empty-text claim rejects nonempty delivered", vx is False and rx == "text_digest_mismatch")


def t_constants():
    check("const: TABLE", ap.TABLE == "a2a_delegation")
    check("const: METADATA_KEY", ap.METADATA_KEY == "mios_principal")


def main():
    t_text_digest()
    t_build_claims()
    t_build_metadata()
    t_verify_valid_roundtrip()
    t_verify_tampered_text()
    t_verify_unsigned_degrade()
    t_verify_bad_signature()
    t_verify_claims_tampered_under_valid_sig()
    t_verify_absent_and_malformed()
    t_verify_empty_text_consistency()
    t_constants()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
