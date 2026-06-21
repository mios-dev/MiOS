#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_crl (WS-A10 cert/token revocation list). Pure stdlib, no server.py/DB/pytest/network. Verifies the CRL class: revoke()->is_revoked True, restore()->False, ids() reflects the current sorted set, load() round-trips from list/tuple/set/dict-with-revoked/malformed (degrade-open to empty), merge() unions ids, __init__ normalization (str-coerce + strip + drop-empty + dedup), unknown-id negatives, and the whitespace/None/empty edge cases the verifier relies on.
# AI-related: ./mios_crl.py
# AI-functions: check, main
"""Unit tests for mios_crl (WS-A10 token/cert revocation list)."""

import sys

import mios_crl as crl

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_empty_default():
    c = crl.CRL()
    check("empty: len 0", len(c) == 0)
    check("empty: ids() == []", c.ids() == [])
    check("empty: unknown id not revoked", c.is_revoked("tok-xyz") is False)
    check("empty: None not revoked", c.is_revoked(None) is False)
    check("empty: blank not revoked", c.is_revoked("") is False)


def t_revoke_is_revoked():
    c = crl.CRL()
    check("revoke: not revoked before", c.is_revoked("t1") is False)
    c.revoke("t1")
    check("revoke: revoked after", c.is_revoked("t1") is True)
    check("revoke: len 1", len(c) == 1)
    check("revoke: ids has t1", c.ids() == ["t1"])
    # other ids stay unrevoked
    check("revoke: unrelated id still unrevoked", c.is_revoked("t2") is False)
    # idempotent: revoking again is a no-op on the set size
    c.revoke("t1")
    check("revoke: idempotent (no dup)", len(c) == 1)


def t_restore():
    c = crl.CRL(["a", "b", "c"])
    check("restore: a revoked before", c.is_revoked("a") is True)
    c.restore("a")
    check("restore: a not revoked after", c.is_revoked("a") is False)
    check("restore: others untouched", c.is_revoked("b") and c.is_revoked("c"))
    check("restore: len drops to 2", len(c) == 2)
    check("restore: ids drops a", c.ids() == ["b", "c"])
    # restoring an id that was never revoked is a safe no-op (discard semantics)
    c.restore("never-was-here")
    check("restore: unknown id no-op (no raise, len stable)", len(c) == 2)
    # revoke -> restore -> revoke round-trip
    c.revoke("a")
    check("restore: re-revoke works", c.is_revoked("a") is True)


def t_ids_sorted_and_current():
    c = crl.CRL()
    c.revoke("zeta")
    c.revoke("alpha")
    c.revoke("mike")
    check("ids: sorted", c.ids() == ["alpha", "mike", "zeta"])
    c.restore("mike")
    check("ids: reflects restore", c.ids() == ["alpha", "zeta"])
    # ids() returns a list (mutating it must not corrupt the CRL)
    got = c.ids()
    got.append("INJECTED")
    check("ids: returned list is a copy (no leak back)",
          c.is_revoked("INJECTED") is False and c.ids() == ["alpha", "zeta"])


def t_init_normalization():
    # str-coerce + strip + drop-empty + dedup at construction
    c = crl.CRL(["  pad  ", "dup", "dup", "", "   ", "x"])
    check("init: strips whitespace", c.is_revoked("pad") is True)
    check("init: padded lookup also strips", c.is_revoked("  pad  ") is True)
    check("init: dedups", c.ids().count("dup") == 1)
    check("init: drops empty + blank", "" not in c.ids() and len(c) == 3,
          detail=str(c.ids()))
    check("init: ids == sorted(dedup,strip)", c.ids() == ["dup", "pad", "x"])
    # non-string ids are coerced via str()
    c2 = crl.CRL([123, 456])
    check("init: int coerced to str", c2.is_revoked("123") is True and c2.is_revoked(123) is True)
    # None/empty iterable -> empty CRL
    check("init: None source -> empty", len(crl.CRL(None)) == 0)


def t_revoke_normalization():
    c = crl.CRL()
    c.revoke("  spaced  ")
    check("revoke: stores stripped", c.ids() == ["spaced"])
    check("revoke: padded lookup hits", c.is_revoked("spaced") is True)
    # blank / whitespace-only / None revoke is ignored (must not add empty string)
    c.revoke("")
    c.revoke("   ")
    c.revoke(None)
    check("revoke: blank/None ignored", c.ids() == ["spaced"] and "" not in c.ids())
    # int coercion
    c.revoke(999)
    check("revoke: int coerced", c.is_revoked("999") is True)


def t_load_list():
    c = crl.CRL.load(["t1", "t2"])
    check("load list: type CRL", isinstance(c, crl.CRL))
    check("load list: round-trips ids", c.ids() == ["t1", "t2"])
    check("load list: revoked", c.is_revoked("t1") and c.is_revoked("t2"))
    check("load tuple: works", crl.CRL.load(("a", "b")).ids() == ["a", "b"])
    check("load set: works", crl.CRL.load({"a", "b"}).ids() == ["a", "b"])


def t_load_dict():
    # the caller-tokens.json shape: a dict carrying a `revoked` list
    src = {"revoked": ["compromised-1", "retired-peer"], "issued": ["live-1"]}
    c = crl.CRL.load(src)
    check("load dict: pulls revoked[]", c.ids() == ["compromised-1", "retired-peer"])
    check("load dict: revoked id is revoked", c.is_revoked("compromised-1") is True)
    check("load dict: ignores non-revoked keys (issued not revoked)",
          c.is_revoked("live-1") is False)
    # dict with no revoked key -> empty (not a crash)
    check("load dict: missing revoked -> empty", len(crl.CRL.load({"issued": ["x"]})) == 0)
    # dict with revoked=None -> empty (the `or []` guard)
    check("load dict: revoked=None -> empty", len(crl.CRL.load({"revoked": None})) == 0)
    # dict with empty revoked list -> empty
    check("load dict: revoked=[] -> empty", len(crl.CRL.load({"revoked": []})) == 0)


def t_load_malformed_degrades_open():
    # degrade-open: a broken source must yield an EMPTY crl, never raise,
    # never block every caller.
    for bad in (None, "a-bare-string", 42, 3.14, object()):
        c = crl.CRL.load(bad)
        check(f"load malformed degrades open: {type(bad).__name__}",
              isinstance(c, crl.CRL) and len(c) == 0)
    # NOTE: a bare string is iterable; load() must NOT treat it as a list of
    # chars (that would revoke single letters). It is not list/tuple/set/dict
    # -> empty CRL.
    c = crl.CRL.load("abc")
    check("load malformed: bare string NOT char-exploded", len(c) == 0 and c.is_revoked("a") is False)


def t_merge_unions():
    c = crl.CRL(["a", "b"])
    c.merge(["b", "c", "d"])
    check("merge: unions (no dup on b)", c.ids() == ["a", "b", "c", "d"])
    check("merge: new ids revoked", c.is_revoked("c") and c.is_revoked("d"))
    check("merge: original ids retained", c.is_revoked("a") and c.is_revoked("b"))
    # merge normalizes too (strip/drop-empty), since it delegates to revoke()
    c.merge(["  e  ", "", "   ", None])
    check("merge: normalizes ids (strip + drop blank/None)",
          c.is_revoked("e") is True and "" not in c.ids())
    # merge None / empty iterable -> no-op
    before = c.ids()
    c.merge(None)
    c.merge([])
    check("merge: None/empty no-op", c.ids() == before)


def t_merge_two_crls():
    # union two CRLs via ids() -> merge(); models a refreshed CRL from disk
    a = crl.CRL(["x", "y"])
    b = crl.CRL(["y", "z"])
    a.merge(b.ids())
    check("merge two CRLs: union of both", a.ids() == ["x", "y", "z"])
    # b is unaffected by a's merge (no shared mutable state)
    check("merge two CRLs: source CRL unchanged", b.ids() == ["y", "z"])


def t_no_shared_state_between_instances():
    a = crl.CRL(["shared"])
    b = crl.CRL(["shared"])
    a.revoke("a-only")
    check("isolation: b has no a-only", b.is_revoked("a-only") is False)
    b.restore("shared")
    check("isolation: a still has shared after b restores it", a.is_revoked("shared") is True)


def main():
    t_empty_default()
    t_revoke_is_revoked()
    t_restore()
    t_ids_sorted_and_current()
    t_init_normalization()
    t_revoke_normalization()
    t_load_list()
    t_load_dict()
    t_load_malformed_degrades_open()
    t_merge_unions()
    t_merge_two_crls()
    t_no_shared_state_between_instances()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
