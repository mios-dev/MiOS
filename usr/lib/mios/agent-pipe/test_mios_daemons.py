# AI-hint: stdlib unit test for mios_daemons -- single-iteration behaviour of the
#   extracted background daemon loops with injected stubs (no real sleep / network /
#   DB). Asserts the gossip loop merges a discovered peer into the shared registry,
#   the self-improve loop surfaces a high-severity finding exactly once, the
#   membership-watch loop fires a reload on an mtime change, and the reputation
#   flush/restore helpers no-op when pg is not primary.
# AI-related: ./mios_daemons.py
# AI-functions: (tests)
"""Stdlib unit tests for the mios_daemons background loops (no network/DB)."""

import asyncio
import os
import tempfile
import time
import unittest

import mios_daemons


def _run(coro):
    # The membership/self-improve loops re-raise CancelledError (the gossip loop
    # breaks); the stub sleeper uses it to stop after one observable pass, so a
    # propagated cancel is the expected end-of-test, not a failure.
    try:
        return asyncio.new_event_loop().run_until_complete(coro)
    except asyncio.CancelledError:
        return None


class _CancelAfter:
    """A fake asyncio.sleep that lets the loop run N iterations then cancels it
    (raising CancelledError) so a single pass is observable without a real wait."""

    def __init__(self, fire_after=1):
        self.calls = 0
        self.fire_after = fire_after

    async def __call__(self, _delay):
        self.calls += 1
        if self.calls >= self.fire_after:
            raise asyncio.CancelledError()


class _Rep:
    def __init__(self):
        self._scores = {}

    def score(self, pid):
        return self._scores.get(pid, 0.5)


class GossipLoopTest(unittest.TestCase):
    def test_merges_discovered_peer(self):
        # One known peer that, when pulled, advertises a brand-new peer -> the loop
        # should merge it into the shared _A2A_PEERS dict with status=discovered.
        peers = {"known": {"url": "http://known", "status": "active", "heartbeat": 1}}

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"peers": [{"id": "fresh", "endpoint": "http://fresh",
                                   "heartbeat": 2}]}

        class _Client:
            async def get(self, _url, timeout=5.0):
                return _Resp()

        async def _get_client():
            return _Client()

        # Force exactly one round then break via CancelledError on the 2nd sleep.
        sleeper = _CancelAfter(fire_after=2)
        orig_sleep = mios_daemons.asyncio.sleep
        orig_toml = mios_daemons._toml_section
        mios_daemons.asyncio.sleep = sleeper
        mios_daemons._toml_section = lambda _s: {"interval_min": 1, "fanout": 3,
                                                 "min_trust": 0.0}
        mios_daemons.configure(
            _get_client=_get_client, _A2A_PEERS=peers,
            _A2A_PEERS_LOCK=asyncio.Lock(), _A2A_REPUTATION=_Rep())
        try:
            _run(mios_daemons._gossip_loop())
        finally:
            mios_daemons.asyncio.sleep = orig_sleep
            mios_daemons._toml_section = orig_toml

        self.assertIn("fresh", peers)
        self.assertEqual(peers["fresh"]["status"], "discovered")

    def test_interval_zero_is_noop(self):
        orig_toml = mios_daemons._toml_section
        mios_daemons._toml_section = lambda _s: {"interval_min": 0}
        try:
            # returns immediately, never sleeps / touches the network
            _run(mios_daemons._gossip_loop())
        finally:
            mios_daemons._toml_section = orig_toml


class SelfImproveLoopTest(unittest.TestCase):
    def test_surfaces_high_finding_once(self):
        seen = set()
        calls = {"n": 0}

        async def _report():
            calls["n"] += 1
            return {"findings": [{"severity": "high", "kind": "k", "subject": "s",
                                  "detail": "d", "suggestion": "fix"}]}

        sleeper = _CancelAfter(fire_after=2)
        orig_sleep = mios_daemons.asyncio.sleep
        orig_toml = mios_daemons._toml_section
        orig_report = mios_daemons._selfimprove_report
        mios_daemons.asyncio.sleep = sleeper
        mios_daemons._toml_section = lambda _s: {"interval_min": 1}
        # _selfimprove_report now lives in this module (no longer injected) -- patch the
        # module global directly, the same way the loop's other deps are stubbed above.
        mios_daemons._selfimprove_report = _report
        mios_daemons.configure(_SELFIMPROVE_SEEN=seen)
        try:
            _run(mios_daemons._selfimprove_loop())
        finally:
            mios_daemons.asyncio.sleep = orig_sleep
            mios_daemons._toml_section = orig_toml
            mios_daemons._selfimprove_report = orig_report

        self.assertIn(("k", "s"), seen)


class _PG:
    """Minimal stand-in for the injected pg module (just an async execute)."""

    def __init__(self, fn):
        self.execute = fn


class SelfImproveReportTest(unittest.TestCase):
    def test_degrades_open_when_pg_unreachable(self):
        # A pg miss -> the read-only report returns the documented empty envelope
        # and never raises, so both the loop and the /v1/self-improve/report route
        # stay up. (Verifies the moved-home helper keeps its degrade-open contract.)
        async def _boom(*_a, **_k):
            raise RuntimeError("pg unreachable")

        orig_pg = mios_daemons._mios_pg
        orig_toml = mios_daemons._toml_section
        mios_daemons._mios_pg = _PG(_boom)
        mios_daemons._toml_section = lambda _s: {}
        try:
            out = _run(mios_daemons._selfimprove_report())
        finally:
            mios_daemons._mios_pg = orig_pg
            mios_daemons._toml_section = orig_toml
        self.assertEqual(out, {"findings": [], "tools_analyzed": 0,
                               "samples": 0, "error": "unavailable"})

    def test_reads_selfimprove_ssot_tunables(self):
        # The analyzer is driven ENTIRELY from the [selfimprove] SSOT section -- the
        # sample_size bounds the query LIMIT and min_samples/fail_threshold/slow_ms
        # flow through to mios_selfimprove.analyze with no values baked into the
        # helper. Synthetic (non-dictionary) section values prove the plumbing.
        captured = {}

        async def _rows(_sql, params, fetch=False):
            captured["limit"] = params["k"]
            return [{"tool": "x"}]

        def _analyze(rows, **kw):
            captured["kw"] = kw
            return {"findings": [], "ok": True}

        class _Rep2:
            def snapshot(self):
                return {"peer": 0.9}

        orig_pg = mios_daemons._mios_pg
        orig_toml = mios_daemons._toml_section
        orig_analyze = mios_daemons.mios_selfimprove.analyze
        orig_rep = mios_daemons._A2A_REPUTATION
        mios_daemons._mios_pg = _PG(_rows)
        mios_daemons._toml_section = lambda _s: {
            "sample_size": 42, "min_samples": 7,
            "fail_threshold": 0.25, "slow_ms": 9999}
        mios_daemons.mios_selfimprove.analyze = _analyze
        mios_daemons._A2A_REPUTATION = _Rep2()
        try:
            out = _run(mios_daemons._selfimprove_report())
        finally:
            mios_daemons._mios_pg = orig_pg
            mios_daemons._toml_section = orig_toml
            mios_daemons.mios_selfimprove.analyze = orig_analyze
            mios_daemons._A2A_REPUTATION = orig_rep
        self.assertEqual(out, {"findings": [], "ok": True})
        self.assertEqual(captured["limit"], 42)
        self.assertEqual(captured["kw"]["min_samples"], 7)
        self.assertEqual(captured["kw"]["fail_threshold"], 0.25)
        self.assertEqual(captured["kw"]["slow_ms"], 9999)
        self.assertEqual(captured["kw"]["reputation"], {"peer": 0.9})


class MembershipWatchLoopTest(unittest.TestCase):
    def test_reload_fires_on_mtime_change(self):
        import os as _os
        reloads = []

        async def _reload(reason="manual"):
            reloads.append(reason)

        mtimes = {"p": [1.0, 2.0]}  # mtime changes between the seed read and tick 1

        def _fake_stat(_p):
            class _S:
                st_mtime = mtimes["p"].pop(0) if mtimes["p"] else 2.0
            return _S()

        sleeper = _CancelAfter(fire_after=2)
        orig_sleep = mios_daemons.asyncio.sleep
        orig_stat = mios_daemons.os.stat
        mios_daemons.asyncio.sleep = sleeper
        mios_daemons.os.stat = _fake_stat
        mios_daemons.configure(
            _reload_membership=_reload, _MEMBERSHIP_WATCH_PATHS=["p"],
            MEMBERSHIP_WATCH_INTERVAL_S=30)
        try:
            _run(mios_daemons._membership_watch_loop())
        finally:
            mios_daemons.asyncio.sleep = orig_sleep
            mios_daemons.os.stat = orig_stat

        self.assertTrue(reloads)
        self.assertTrue(reloads[0].startswith("mtime:"))


class ReputationHelpersTest(unittest.TestCase):
    def test_flush_and_restore_noop_when_not_primary(self):
        mios_daemons.configure(_PG_PRIMARY=False)
        # both must return without touching _mios_pg (which would fail with no DB)
        _run(mios_daemons._reputation_flush())
        _run(mios_daemons._reputation_restore())


class KvGcSweepTest(unittest.TestCase):
    def test_evicts_old_unprotected_matching_only(self):
        # Filenames are built from the module's filename plan (SSOT) -- no baked
        # prefix/suffix literal -- with synthetic non-dictionary conversation tokens.
        old = time.time() - 100000.0
        with tempfile.TemporaryDirectory() as d:
            evictable = os.path.join(d, mios_daemons._kv_filename("zqx7slotA"))
            resident = os.path.join(d, mios_daemons._kv_filename("zqx7resB"))
            # A stale file that does NOT match the KV prefix/suffix -> never a candidate.
            unrelated = os.path.join(d, "zqx7unrelated.tmp")
            for p in (evictable, resident, unrelated):
                with open(p, "wb") as f:
                    f.write(b"\x00\x00")
                os.utime(p, (old, old))
            mios_daemons.configure(
                KV_SLOTS_DIR=d, KV_GC_TTL_S=1.0, KV_GC_MAX_BYTES=0,
                _KV_RESIDENT={"slot": "zqx7resB"})
            mios_daemons._kv_gc_sweep_once()
            self.assertFalse(os.path.exists(evictable),
                             "stale unprotected KV file should be evicted")
            self.assertTrue(os.path.exists(resident),
                            "the active-slot (resident) file must be protected")
            self.assertTrue(os.path.exists(unrelated),
                            "a non-KV file must never be touched")

    def test_missing_dir_is_noop(self):
        mios_daemons.configure(KV_SLOTS_DIR=os.path.join(
            tempfile.gettempdir(), "zqx7-does-not-exist"))
        mios_daemons._kv_gc_sweep_once()  # must not raise


class KvGcLoopTest(unittest.TestCase):
    def test_loop_invokes_sweep_then_survives(self):
        calls = {"n": 0}

        def _fake_sweep():
            calls["n"] += 1

        sleeper = _CancelAfter(fire_after=2)  # 1st sleep returns -> sweep, 2nd cancels
        orig_sleep = mios_daemons.asyncio.sleep
        orig_sweep = mios_daemons._kv_gc_sweep_once
        mios_daemons.asyncio.sleep = sleeper
        mios_daemons._kv_gc_sweep_once = _fake_sweep
        mios_daemons.configure(KV_GC_INTERVAL_S=0)
        try:
            _run(mios_daemons._kv_gc_loop())
        finally:
            mios_daemons.asyncio.sleep = orig_sleep
            mios_daemons._kv_gc_sweep_once = orig_sweep
        self.assertEqual(calls["n"], 1)


class SelfImproveActPassTest(unittest.TestCase):
    """The T-062/T-064 ACT pass: propose -> prove utility -> QUEUE for human approval,
    never auto-apply. Synthetic non-dictionary surfaces/ids + stubbed solver scores
    (no live models / DB) -- the structure is what is validated offline."""

    def _restore(self, saved):
        for k, v in saved.items():
            setattr(mios_daemons, k, v)

    def test_disabled_is_noop(self):
        # DEFAULT-OFF: act_enabled false -> a pure no-op; the drafter is never invoked.
        drafted = {"called": False}

        async def _draft(_f):
            drafted["called"] = True
            return {"target_kind": "zq_ok", "target_id": "z", "change": "zc",
                    "rationale": "zr"}

        saved = {"_toml_section": mios_daemons._toml_section,
                 "_act_draft_proposal": mios_daemons._act_draft_proposal}
        mios_daemons._toml_section = lambda _s: {"act_enabled": False}
        mios_daemons._act_draft_proposal = _draft
        try:
            out = _run(mios_daemons._selfimprove_act_pass())
        finally:
            self._restore(saved)
        self.assertEqual(out["acted"], False)
        self.assertEqual(out["queued"], 0)
        self.assertFalse(drafted["called"], "a disabled pass must not draft or act")

    def test_queues_non_regressing_proposal(self):
        # Enabled + a non-regressing proposal -> QUEUED exactly once. The single write
        # is an append to the event queue with a pending_review status (queue-not-apply:
        # nothing is dispatched/mutated).
        captured = []

        async def _report():
            return {"findings": [{"severity": "high", "kind": "zk", "subject": "zs",
                                  "detail": "zd", "suggestion": "zfix"}]}

        async def _draft(_f):
            return {"target_kind": "zq_ok", "target_id": "zt1", "change": "zc",
                    "rationale": "zr"}

        async def _evaluate(_p):
            return (0.4, 0.6)              # proposed > baseline -> non-regressing

        async def _execute(sql, params, fetch=False):
            captured.append((sql, params))
            return None

        saved = {"_toml_section": mios_daemons._toml_section,
                 "_selfimprove_report": mios_daemons._selfimprove_report,
                 "_act_draft_proposal": mios_daemons._act_draft_proposal,
                 "_act_evaluate_proposal": mios_daemons._act_evaluate_proposal,
                 "_mios_pg": mios_daemons._mios_pg}
        mios_daemons._toml_section = lambda _s: {
            "act_enabled": True, "improvable_targets": ["zq_ok"],
            "protected_targets": ["zp_no"], "accept_margin": 0.0,
            "max_proposals_per_pass": 3}
        mios_daemons._selfimprove_report = _report
        mios_daemons._act_draft_proposal = _draft
        mios_daemons._act_evaluate_proposal = _evaluate
        mios_daemons._mios_pg = _PG(_execute)
        try:
            out = _run(mios_daemons._selfimprove_act_pass())
        finally:
            self._restore(saved)
        self.assertEqual(out["queued"], 1)
        self.assertEqual(out["rejected"], 0)
        self.assertEqual(len(captured), 1, "exactly one queue write")
        sql, params = captured[0]
        self.assertIn("INSERT INTO event", sql)
        self.assertNotIn("UPDATE", sql.upper())          # nothing applied/mutated
        self.assertEqual(params["kind"], mios_daemons._PROPOSAL_EVENT_KIND)
        self.assertIn("pending_review", params["payload"])  # awaits human approval

    def test_rejects_regressing_proposal(self):
        # A regressing proposal is REJECTED and NEVER queued; the delta is in the result.
        captured = []

        async def _report():
            return {"findings": [{"severity": "high", "kind": "zk", "subject": "zs"}]}

        async def _draft(_f):
            return {"target_kind": "zq_ok", "target_id": "zt1", "change": "zc",
                    "rationale": "zr"}

        async def _evaluate(_p):
            return (0.7, 0.5)              # proposed < baseline -> regression

        async def _execute(sql, params, fetch=False):
            captured.append((sql, params))

        saved = {"_toml_section": mios_daemons._toml_section,
                 "_selfimprove_report": mios_daemons._selfimprove_report,
                 "_act_draft_proposal": mios_daemons._act_draft_proposal,
                 "_act_evaluate_proposal": mios_daemons._act_evaluate_proposal,
                 "_mios_pg": mios_daemons._mios_pg}
        mios_daemons._toml_section = lambda _s: {
            "act_enabled": True, "improvable_targets": ["zq_ok"],
            "protected_targets": ["zp_no"], "accept_margin": 0.0,
            "max_proposals_per_pass": 3}
        mios_daemons._selfimprove_report = _report
        mios_daemons._act_draft_proposal = _draft
        mios_daemons._act_evaluate_proposal = _evaluate
        mios_daemons._mios_pg = _PG(_execute)
        try:
            out = _run(mios_daemons._selfimprove_act_pass())
        finally:
            self._restore(saved)
        self.assertEqual(out["queued"], 0)
        self.assertEqual(out["rejected"], 1)
        self.assertEqual(len(captured), 0, "a regressing proposal is never queued")

    def test_rejects_isolation_violation_before_scoring(self):
        # A proposal targeting the PROTECTED surface (the evaluator/eval/lane-config) is
        # rejected on isolation BEFORE it is scored -- the evaluator is never even run --
        # and is never queued. This is the anti-reward-hacking structural guarantee.
        eval_called = {"n": 0}
        captured = []

        async def _report():
            return {"findings": [{"severity": "high", "kind": "zk", "subject": "zs"}]}

        async def _draft(_f):
            return {"target_kind": "zp_no", "target_id": "zt1", "change": "zc",
                    "rationale": "zr"}    # targets a PROTECTED kind

        async def _evaluate(_p):
            eval_called["n"] += 1
            return (0.0, 1.0)             # a perfect "improvement" -- must NOT be reached

        async def _execute(sql, params, fetch=False):
            captured.append((sql, params))

        saved = {"_toml_section": mios_daemons._toml_section,
                 "_selfimprove_report": mios_daemons._selfimprove_report,
                 "_act_draft_proposal": mios_daemons._act_draft_proposal,
                 "_act_evaluate_proposal": mios_daemons._act_evaluate_proposal,
                 "_mios_pg": mios_daemons._mios_pg}
        mios_daemons._toml_section = lambda _s: {
            "act_enabled": True, "improvable_targets": ["zq_ok"],
            "protected_targets": ["zp_no"], "accept_margin": 0.0,
            "max_proposals_per_pass": 3}
        mios_daemons._selfimprove_report = _report
        mios_daemons._act_draft_proposal = _draft
        mios_daemons._act_evaluate_proposal = _evaluate
        mios_daemons._mios_pg = _PG(_execute)
        try:
            out = _run(mios_daemons._selfimprove_act_pass())
        finally:
            self._restore(saved)
        self.assertEqual(out["queued"], 0)
        self.assertEqual(out["rejected"], 1)
        self.assertEqual(eval_called["n"], 0,
                         "an isolation-violating proposal must never be scored")
        self.assertEqual(len(captured), 0, "never queued")

    def test_loop_runs_act_pass_each_iteration(self):
        # Wiring proof: the surfacing loop invokes the ACT pass every iteration (the pass
        # itself self-gates on act_enabled, so this stays default-off in production).
        calls = {"n": 0}

        async def _report():
            return {"findings": []}

        async def _act():
            calls["n"] += 1
            return {"acted": False}

        sleeper = _CancelAfter(fire_after=2)
        saved = {"asyncio": mios_daemons.asyncio.sleep,
                 "_toml_section": mios_daemons._toml_section,
                 "_selfimprove_report": mios_daemons._selfimprove_report,
                 "_selfimprove_act_pass": mios_daemons._selfimprove_act_pass}
        mios_daemons.asyncio.sleep = sleeper
        mios_daemons._toml_section = lambda _s: {"interval_min": 1}
        mios_daemons._selfimprove_report = _report
        mios_daemons._selfimprove_act_pass = _act
        try:
            _run(mios_daemons._selfimprove_loop())
        finally:
            mios_daemons.asyncio.sleep = saved["asyncio"]
            mios_daemons._toml_section = saved["_toml_section"]
            mios_daemons._selfimprove_report = saved["_selfimprove_report"]
            mios_daemons._selfimprove_act_pass = saved["_selfimprove_act_pass"]
        self.assertEqual(calls["n"], 1)


class SelfImproveProposalsReadTest(unittest.TestCase):
    def test_degrades_open_when_pg_unreachable(self):
        # The read-only proposals queue returns the documented empty envelope on a pg
        # miss so GET /v1/self-improve/proposals stays up.
        async def _boom(*_a, **_k):
            raise RuntimeError("pg unreachable")

        saved = mios_daemons._mios_pg
        mios_daemons._mios_pg = _PG(_boom)
        try:
            out = _run(mios_daemons._selfimprove_proposals())
        finally:
            mios_daemons._mios_pg = saved
        self.assertEqual(out["proposals"], [])
        self.assertEqual(out["count"], 0)
        self.assertEqual(out["error"], "unavailable")

    def test_reads_queued_proposal_rows(self):
        # Reads back the queued proposal event rows, bounded + filtered by the proposal
        # event kind (no apply -- read-only review surface).
        captured = {}

        async def _rows(_sql, params, fetch=False):
            captured["kind"] = params["kind"]
            captured["sql"] = _sql
            return [{"id": 1, "summary": "zsum", "payload": {"status": "pending_review"}}]

        saved = mios_daemons._mios_pg
        mios_daemons._mios_pg = _PG(_rows)
        try:
            out = _run(mios_daemons._selfimprove_proposals())
        finally:
            mios_daemons._mios_pg = saved
        self.assertEqual(out["count"], 1)
        self.assertEqual(captured["kind"], mios_daemons._PROPOSAL_EVENT_KIND)
        self.assertIn("FROM event", captured["sql"])


if __name__ == "__main__":
    unittest.main()
