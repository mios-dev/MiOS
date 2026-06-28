#!/usr/bin/env python3
# AI-hint: Unit tests for mios_audit, the SEC-03 SHA-256 tamper-evident event-bus hash chain. Exercises the PURE primitives headless (no DB, no web stack): deterministic chaining (two independent chainers seeded at genesis produce identical hashes; chain_seq is monotonic; the first prev_hash is the genesis sha256), clean-chain verification, tamper DETECTION (a content-edited middle event, a corrupted chain_hash, and a deleted row are all caught with the right first_broken_seq), degrade-open behaviour (disabled chainer and unseeded chainer both return the row unchanged so event logging never breaks), idempotent stamping (re-stamping an already-stamped row does not advance the chain -- the _emit_session_event pre-stamp contract), and NON-dictionary payloads (string/int/list). Stdlib unittest only.
# AI-related: ./mios_audit.py, ../../../libexec/mios/mios-chain-verify, ./server.py
# AI-functions: TestEventChain.* (deterministic/verify/tamper/degrade-open/idempotent/non-dict-payload)
"""Unit tests for the SEC-03 event-bus hash chain (mios_audit)."""

import copy
import json
import unittest

import mios_audit as A


def _synthetic_events():
    """Synthetic events with deliberately NON-dictionary payloads (a string, an int, a
    list) plus a nested dict -- the chain must canonicalize any JSON payload shape."""
    return [
        {"source": "agentpipe", "kind": "dispatch", "payload": "a plain string payload"},
        {"source": "agentpipe", "kind": "tool_call", "severity": "info", "payload": 42},
        {"source": "swarm", "kind": "node_done", "payload": [1, 2, {"k": "v"}]},
        {"source": "agentpipe", "kind": "synthesis",
         "summary": "done", "payload": {"nested": {"b": 2, "a": 1}}},
    ]


def _fresh_chainer():
    c = A.EventChainer()
    c.seed(0, A.GENESIS)   # fresh table -> genesis, chain active
    return c


class TestEventChain(unittest.TestCase):
    def setUp(self):
        # Tests toggle the module-global flag; snapshot + restore so order can't leak.
        self._enable = A.CHAIN_ENABLE
        A.CHAIN_ENABLE = True

    def tearDown(self):
        A.CHAIN_ENABLE = self._enable

    def test_deterministic_and_monotonic(self):
        """Two independent chainers seeded at genesis produce IDENTICAL chain_hash
        sequences over the same events; chain_seq is 1..n; the first prev_hash is the
        genesis sha256."""
        evs = _synthetic_events()
        c1, c2 = _fresh_chainer(), _fresh_chainer()
        s1 = [c1.stamp(dict(e)) for e in evs]
        s2 = [c2.stamp(dict(e)) for e in evs]
        self.assertEqual([r["chain_hash"] for r in s1],
                         [r["chain_hash"] for r in s2])
        self.assertEqual([r["chain_seq"] for r in s1], [1, 2, 3, 4])
        self.assertEqual(s1[0]["prev_hash"], A.GENESIS)
        # each link's prev_hash is the predecessor's chain_hash
        for prev, cur in zip(s1, s1[1:]):
            self.assertEqual(cur["prev_hash"], prev["chain_hash"])

    def test_clean_chain_verifies(self):
        c = _fresh_chainer()
        rows = [c.stamp(dict(e)) for e in _synthetic_events()]
        res = A.verify_chain(rows)
        self.assertTrue(res["ok"])
        self.assertEqual(res["checked"], len(rows))
        self.assertIsNone(res["first_broken_seq"])

    def test_tampered_middle_content_detected(self):
        """Editing the CONTENT (payload) of a middle event breaks the chain at that
        event's chain_seq."""
        c = _fresh_chainer()
        rows = [c.stamp(dict(e)) for e in _synthetic_events()]
        tampered = copy.deepcopy(rows)
        tampered[1] = dict(tampered[1])
        tampered[1]["payload"] = 999999          # was 42 -> content tamper
        res = A.verify_chain(tampered)
        self.assertFalse(res["ok"])
        self.assertEqual(res["first_broken_seq"], rows[1]["chain_seq"])
        self.assertEqual(res["checked"], 1)      # seq 1 verified, seq 2 caught

    def test_corrupted_chain_hash_detected(self):
        """Rewriting a stored chain_hash (without recomputing the rest) is caught."""
        c = _fresh_chainer()
        rows = [c.stamp(dict(e)) for e in _synthetic_events()]
        tampered = copy.deepcopy(rows)
        tampered[2]["chain_hash"] = "0" * 64
        res = A.verify_chain(tampered)
        self.assertFalse(res["ok"])
        self.assertEqual(res["first_broken_seq"], rows[2]["chain_seq"])

    def test_deleted_row_detected(self):
        """Removing a middle row breaks the successor's prev_hash linkage."""
        c = _fresh_chainer()
        rows = [c.stamp(dict(e)) for e in _synthetic_events()]
        spliced = [rows[0], rows[2], rows[3]]    # row seq=2 deleted
        res = A.verify_chain(spliced)
        self.assertFalse(res["ok"])
        self.assertEqual(res["first_broken_seq"], rows[2]["chain_seq"])

    def test_non_dict_payloads_roundtrip(self):
        """A string / int / list payload chains and verifies (canonical_core handles
        any JSON value under the payload key)."""
        c = _fresh_chainer()
        rows = [c.stamp({"source": "s", "kind": "k", "payload": p})
                for p in ("text", 7, [1, 2, 3])]
        self.assertTrue(A.verify_chain(rows)["ok"])
        # and a content edit to a non-dict payload is still detected
        rows[0] = dict(rows[0]); rows[0]["payload"] = "TEXT"
        self.assertFalse(A.verify_chain(rows)["ok"])

    def test_string_vs_dict_payload_same_hash(self):
        """NG-3: a payload handed in as a pre-serialised JSON STRING and the SAME payload
        as a parsed dict must canonicalize identically. payload is a jsonb column;
        psycopg reads it back as the parsed object at verify time, so write-time (which
        may see either form) must not diverge from verify-time (which always sees the
        parsed object) -- else the chain reports a spurious "broken" link."""
        payload_dict = {"b": 2, "a": 1, "nested": [3, {"z": 9}]}
        payload_str = json.dumps(payload_dict)        # pre-serialised JSON string form
        # canonical_core agrees on both shapes ...
        self.assertEqual(
            A.canonical_core({"source": "s", "kind": "k", "payload": payload_str}),
            A.canonical_core({"source": "s", "kind": "k", "payload": payload_dict}))
        # ... so two chainers stamp the SAME chain_hash for the two forms.
        c1, c2 = _fresh_chainer(), _fresh_chainer()
        r_str = c1.stamp({"source": "s", "kind": "k", "payload": payload_str})
        r_dict = c2.stamp({"source": "s", "kind": "k", "payload": payload_dict})
        self.assertEqual(r_str["chain_hash"], r_dict["chain_hash"])
        # WRITE sees the string, VERIFY sees the dict the DB round-trips back -> verifies.
        verify_row = dict(r_str); verify_row["payload"] = payload_dict
        self.assertTrue(A.verify_chain([verify_row])["ok"])
        # a genuine free-text (non-JSON) string payload is untouched and still verifies.
        free = _fresh_chainer().stamp({"source": "s", "kind": "k", "payload": "hello world"})
        self.assertTrue(A.verify_chain([free])["ok"])

    def test_idempotent_stamp_no_double_advance(self):
        """Re-stamping an already-stamped row is a no-op (the _emit_session_event
        pre-stamp contract): same columns, the chain does NOT advance twice."""
        c = _fresh_chainer()
        first = c.stamp({"source": "s", "kind": "k", "payload": "x"})
        again = c.stamp(first)                   # already has chain_hash
        self.assertEqual(again["chain_seq"], first["chain_seq"])
        self.assertEqual(again["chain_hash"], first["chain_hash"])
        # the next genuinely-new event is seq+1 (chain advanced exactly once)
        nxt = c.stamp({"source": "s", "kind": "k", "payload": "y"})
        self.assertEqual(nxt["chain_seq"], first["chain_seq"] + 1)
        self.assertEqual(nxt["prev_hash"], first["chain_hash"])

    def test_degrade_open_when_disabled(self):
        """With the feature off, stamp returns the row UNCHANGED (no chain columns) so
        event logging proceeds normally."""
        A.CHAIN_ENABLE = False
        c = _fresh_chainer()
        ev = {"source": "s", "kind": "k", "payload": "x"}
        out = c.stamp(ev)
        self.assertNotIn("chain_hash", out)
        self.assertNotIn("chain_seq", out)
        self.assertEqual(out, ev)

    def test_degrade_open_when_unseeded(self):
        """An unseeded chainer (startup DB miss) returns the row unchanged rather than
        restarting the chain at seq=1."""
        c = A.EventChainer()                     # NOT seeded
        ev = {"source": "s", "kind": "k", "payload": "x"}
        out = c.stamp(ev)
        self.assertNotIn("chain_hash", out)
        self.assertFalse(c.seeded)

    def test_empty_chain_is_ok(self):
        res = A.verify_chain([])
        self.assertTrue(res["ok"])
        self.assertEqual(res["checked"], 0)
        self.assertIsNone(res["first_broken_seq"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
