# AI-hint: BACKGROUND async daemon-loop bodies extracted VERBATIM from server.py
#   (strangler-fig refactor). These are the long-lived create_task() loops the
#   FastAPI startup hooks spawn: _membership_watch_loop (FED-G3 mtime hot-reload of
#   agent/node/peer membership), _gossip_loop (WS-A18 epidemic peer-discovery,
#   trust-gated over mios_gossip), _selfimprove_loop + _selfimprove_report (#64
#   proactive finding surfacing + the read-only outcome/reputation report it
#   consumes, via the mios_selfimprove analyzer), the WS-A10/A18
#   reputation-persistence helpers (_reputation_restore /
#   _reputation_flush) the reputation flush loop drives, and the WS-A4 KV slot-file GC
#   sweep+loop (_kv_gc_sweep_once / _kv_gc_loop) that reclaims on-disk KV paging/fork
#   files via the mios_kvgc planner. Every comment/heuristic/guard moved byte-
#   identically. The @app.on_event startup hooks STAY in server.py and create_task()
#   these re-imported names. Leaf deps (_toml_section, mios_gossip, mios_selfimprove,
#   mios_pg, the mios_kvgc planner + the mios_kvfork filename plan -- whose
#   _FILE_PREFIX/_FILE_SUFFIX are the ONE source for the KV slot-file naming, so the
#   sweep matches on those constants instead of restating the literal) are imported
#   directly; every server-side symbol (the live peer registry + lock, the reputation
#   object, _get_client, _reload_membership, the self-improve seen-set, the
#   membership-watch config, the KV-GC knobs + the live _KV_RESIDENT active-slot map)
#   is dependency-
#   INJECTED via configure() (one-way boundary -- this module NEVER imports server).
#   server.py re-imports every name under its exact original alias so the importable
#   surface is byte-identical.
# AI-related: ./server.py, ./mios_config.py, ./mios_gossip.py, ./mios_pg.py, ./mios_reputation.py, ./mios_selfimprove.py, ./mios_kvgc.py, ./mios_kvfork.py, ./test_mios_daemons.py
# AI-functions: _membership_watch_loop, _gossip_loop, _reputation_restore, _reputation_flush, _selfimprove_report, _selfimprove_loop, _kv_gc_sweep_once, _kv_gc_loop, daemons_router, selfimprove_report_ep, configure
"""BACKGROUND async daemon loops (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. These are the long-lived ``create_task()``
loop bodies the FastAPI startup hooks spawn: ``_membership_watch_loop`` (FED-G3
live membership hot-reload), ``_gossip_loop`` (WS-A18 trust-gated epidemic peer
discovery), ``_selfimprove_loop`` (#64 proactive finding surfacing), and the
``_reputation_restore`` / ``_reputation_flush`` persistence helpers the reputation
flush loop drives. Every heuristic/guard/comment stays byte-identical. Leaf deps
are imported directly; every server-side symbol is injected via :func:`configure`
(one-way boundary -- this module never imports ``server``). ``server.py`` keeps the
``@app.on_event`` startup hooks and re-imports each loop under its original alias so
the importable surface stays byte-identical.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from mios_config import _toml_section
import mios_gossip
import mios_selfimprove   # #64 outcome analyzer (read-only) -- consumed by _selfimprove_report
import mios_selfimprove_act   # #64 ACT-half decision core (isolation + solver-gap + pass^k non-regression)
import mios_pg as _mios_pg
import mios_kvgc
# The KV slot-file naming has ONE source (the fork plan); the GC sweep matches on
# these constants rather than restating the prefix/suffix literal.
from mios_kvfork import (kv_filename as _kv_filename,
                         _FILE_PREFIX as _KV_FILE_PREFIX,
                         _FILE_SUFFIX as _KV_FILE_SUFFIX)

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam ----------------------------------------
# These loops read server.py's live A2A peer registry (+ its lock), the outbound
# peer-reputation object, the shared httpx client getter, the membership-reload
# entrypoint + its watch config, the self-improve de-dup seen-set, and
# the _PG_PRIMARY flag. server.py calls configure() with those AFTER every one is
# defined (one-way boundary: this module never imports server). The placeholders
# below let a standalone import succeed; every consumer is async/runtime so nothing
# fires before configure() runs. The mutable registries (_A2A_PEERS, the lock, the
# reputation object, _SELFIMPROVE_SEEN) are injected BY REFERENCE so in-place
# mutations stay visible to server's own readers.

_get_client = None
_A2A_PEERS = None
_A2A_PEERS_LOCK = None
_A2A_REPUTATION = None
_reload_membership = None
_SELFIMPROVE_SEEN = None
_MEMBERSHIP_WATCH_PATHS = None
MEMBERSHIP_WATCH_INTERVAL_S = 30
_PG_PRIMARY = False

# WS-A4 KV slot-file GC. server resolves these from mios.toml/env (SSOT) and injects
# them; the sweep+loop read them at runtime. The placeholders are neutral sentinels
# (the loop never runs until configure() supplies real values + the startup gate
# checks them). _KV_RESIDENT is the live active-slot map, injected BY REFERENCE so the
# sweep protects whatever conversation is currently paged in.
KV_SLOTS_DIR = ""
KV_GC_TTL_S = 0.0
KV_GC_MAX_BYTES = 0
KV_GC_INTERVAL_S = 0
_KV_RESIDENT: dict = {}


_INJECTED = frozenset((
    "_get_client", "_A2A_PEERS", "_A2A_PEERS_LOCK", "_A2A_REPUTATION",
    "_reload_membership", "_SELFIMPROVE_SEEN",
    "_MEMBERSHIP_WATCH_PATHS", "MEMBERSHIP_WATCH_INTERVAL_S", "_PG_PRIMARY",
    "KV_SLOTS_DIR", "KV_GC_TTL_S", "KV_GC_MAX_BYTES", "KV_GC_INTERVAL_S",
    "_KV_RESIDENT",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called once from ``server.py`` after every injected symbol is defined. Each
    keyword equals the module global it sets; the mutable registries are injected by
    reference so in-place mutation stays shared with server.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


async def _membership_watch_loop() -> None:
    """Poll the mtime of the peer registry + layered mios.toml; on any change, hot-
    reload membership. Cheap (stat-only between reloads). Cancel-safe; degrade-open."""
    _seen: dict = {}
    for _p in _MEMBERSHIP_WATCH_PATHS:
        try:
            _seen[_p] = os.stat(_p).st_mtime
        except OSError:
            _seen[_p] = -1.0
    log.info("membership watch: ON (interval=%ds, %d paths)",
             MEMBERSHIP_WATCH_INTERVAL_S, len(_MEMBERSHIP_WATCH_PATHS))
    while True:
        try:
            await asyncio.sleep(max(5, MEMBERSHIP_WATCH_INTERVAL_S))
            _changed = []
            for _p in _MEMBERSHIP_WATCH_PATHS:
                try:
                    _m = os.stat(_p).st_mtime
                except OSError:
                    _m = -1.0
                if _seen.get(_p) != _m:
                    _seen[_p] = _m
                    _changed.append(os.path.basename(_p))
            if _changed:
                await _reload_membership(reason="mtime:" + ",".join(sorted(set(_changed))))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 -- never let a watch tick kill the loop
            log.debug("membership watch tick error: %s", e)


async def _gossip_loop() -> None:
    try:
        interval = int(_toml_section("gossip").get("interval_min", 0))
    except Exception:  # noqa: BLE001
        interval = 0
    if interval <= 0:
        return
    g = _toml_section("gossip")
    fanout = int(g.get("fanout", 3) or 3)
    min_trust = float(g.get("min_trust", 0.0) or 0.0)
    log.info("gossip: peer-discovery loop every %d min (fanout=%d, min_trust=%.2f)",
             interval, fanout, min_trust)
    rnd = 0
    while True:
        try:
            await asyncio.sleep(interval * 60)
            rnd += 1
            async with _A2A_PEERS_LOCK:
                local = {pid: mios_gossip.Peer(
                    pid, str(p.get("url") or ""), int(p.get("heartbeat", 1) or 1),
                    time.time(), _A2A_REPUTATION.score(pid))
                    for pid, p in _A2A_PEERS.items()}
            targets = mios_gossip.select_gossip_peers(list(local.keys()), fanout, seed=rnd)
            client = await _get_client()
            added = 0
            for tid in targets:
                url = (local[tid].endpoint or "").rstrip("/")
                if not url:
                    continue
                try:
                    r = await client.get(f"{url}/v1/peers", timeout=5.0)
                    if r.status_code != 200:
                        continue
                    incoming = [mios_gossip.Peer(
                        str(pp.get("id")), str(pp.get("endpoint") or ""),
                        int(pp.get("heartbeat", 1) or 1), time.time(),
                        _A2A_REPUTATION.score(str(pp.get("id"))))
                        for pp in (r.json().get("peers") or []) if pp.get("id")]
                    added += mios_gossip.merge_peer_set(
                        local, incoming, now=time.time(), min_trust=min_trust,
                        trust_of=lambda i: _A2A_REPUTATION.score(i))
                except Exception:  # noqa: BLE001 -- one bad peer never breaks the round
                    continue
            if added:
                async with _A2A_PEERS_LOCK:
                    for pid, peer in local.items():
                        if pid not in _A2A_PEERS and peer.endpoint:
                            _A2A_PEERS[pid] = {"url": peer.endpoint,
                                               "status": "discovered",
                                               "heartbeat": peer.heartbeat}
                log.info("gossip round %d: merged %d peer rumor(s)", rnd, added)
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001 -- the loop must never die
            log.debug("gossip loop: %s", e)
            await asyncio.sleep(5)


async def _reputation_restore() -> None:
    """Load persisted per-peer counters from pg into _A2A_REPUTATION (the inverse
    of the flush) so reliability survives a restart. Degrade-open -> start cold."""
    if not _PG_PRIMARY:
        return
    try:
        rows = await _mios_pg.execute(
            "SELECT peer_id, ok, bad, streak_bad FROM peer_reputation", {},
            fetch=True)
        if rows:
            _A2A_REPUTATION.restore(rows)
            log.info("peer reputation restored from pg: %d peer(s)", len(rows))
    except Exception:  # noqa: BLE001 -- degrade-open: start with no history
        pass


async def _reputation_flush() -> None:
    """Upsert the in-process reputation counters into peer_reputation so they
    persist. One idempotent upsert per peer; best-effort per row."""
    if not _PG_PRIMARY:
        return
    for r in _A2A_REPUTATION.rows():
        try:
            await _mios_pg.execute(
                "INSERT INTO peer_reputation (peer_id, ok, bad, streak_bad, ts) "
                "VALUES (%(peer_id)s, %(ok)s, %(bad)s, %(streak_bad)s, now()) "
                "ON CONFLICT (peer_id) DO UPDATE SET ok = EXCLUDED.ok, "
                "bad = EXCLUDED.bad, streak_bad = EXCLUDED.streak_bad, ts = now()",
                r, fetch=False)
        except Exception:  # noqa: BLE001 -- best-effort; a bad row never aborts the rest
            pass


# #64 self-improvement signals (read-only). Surfaces WHAT to improve from local
# outcome data; it does NOT act -- closing the loop (auto-tuning) is a separate,
# gated step (agent self-modification needs guardrails). Moved home from server.py
# (its sole runtime consumer is _selfimprove_loop, just below); the /v1/self-improve/
# report route still reaches it via server's re-import. Tunables all read the
# [selfimprove] SSOT section (the literals are the documented degrade-open fallbacks).
async def _selfimprove_report() -> dict:
    """Improvement findings from recent tool_call outcomes + peer reputation.
    Read-only; degrade-open -> {findings:[], error} if pgvector is unreachable."""
    try:
        sect = _toml_section("selfimprove")
        rows = await _mios_pg.execute(
            "SELECT tool, success, exit_code, latency_ms, tainted "
            "FROM tool_call ORDER BY ts DESC LIMIT %(k)s",
            {"k": int(sect.get("sample_size", 500))}, fetch=True) or []
        return mios_selfimprove.analyze(
            rows, reputation=_A2A_REPUTATION.snapshot(),
            min_samples=int(sect.get("min_samples", 5)),
            fail_threshold=float(sect.get("fail_threshold", 0.3)),
            slow_ms=float(sect.get("slow_ms", 10000)))
    except Exception as e:  # noqa: BLE001 -- degrade-open
        log.warning("self-improve report unavailable: %s", e)
        return {"findings": [], "tools_analyzed": 0, "samples": 0,
                "error": "unavailable"}


# ── #64 self-improvement ACT half (T-062) + proof-of-utility (T-064) ───────────
# The OBSERVE half (_selfimprove_report) surfaces WHAT to improve; the ACT half turns
# a finding into a bounded change PROPOSAL, PROVES it does not regress the baseline,
# and QUEUES it for HUMAN approval -- it NEVER auto-applies a self-modification. The
# pure decisions (structural anti-reward-hacking isolation, the Autodata solver-gap
# curation, the pass^k non-regression gate) live in mios_selfimprove_act; this module
# owns only the live orchestration (drafting via a model, running the solver lanes,
# writing the queue) -- all DEFAULT-OFF + degrade-open. The queue is an `event` row
# (kind below) the operator reviews via GET /v1/self-improve/proposals and approves
# out of band; applying an approved proposal is a separate path (out of scope here).
_PROPOSAL_EVENT_KIND = "self_improve_proposal"
# Result-set bound for the read-only proposals list (a query cap, like hitl_pending's
# LIMIT -- not a decision weight); the queue is append-only so the list shows the most
# recent first.
_PROPOSALS_LIST_LIMIT = 100


async def _act_draft_proposal(finding: dict) -> Optional[dict]:
    """Draft a bounded change PROPOSAL for one finding (the Autodata "implementer").

    A proposal is {target_kind, target_id, change, rationale}: the artifact to change
    (a prompt / skill / config entry IN the improvable surface), a described tweak,
    and the rationale. Mapping a finding to a CONCRETE improvable target + a change is
    a reasoning step that needs a live model -- and must NOT be a hardcoded
    finding->artifact heuristic (that would be an English gate banned by Law 7) -- so
    this seam is wired to a model-backed drafter validated by the operator. Until then
    it returns None: nothing is fabricated, so even a flipped act_enabled never queues
    a guessed change. Patched in tests to exercise the propose->prove->queue path."""
    return None


async def _act_evaluate_proposal(proposal: dict) -> Optional[tuple]:
    """Score the current baseline vs the proposed variant on a DISCRIMINATIVE held-out
    eval (T-064). Returns (baseline_score, proposed_score) as pass^k reliabilities, or
    None when no eval/solver is available (-> the proposal cannot be proven and is not
    queued). The live path fetches eval candidates, curates them with the solver-gap
    (mios_selfimprove_act.curate_eval over the SSOT weak/strong lane pair), runs each
    variant through the lanes, and scores via mios_selfimprove_act.pass_hat_k_score --
    a live, operator-validated step, so the offline default is None. Patched in tests
    to supply synthetic baseline/proposed scores."""
    return None


async def _act_queue_proposal(proposal: dict, verdict: dict) -> bool:
    """QUEUE a validated, non-regressing proposal for human review (an `event` row).
    NEVER applies it. Degrade-open: a pg miss logs + drops the proposal and returns
    False; live serving is never affected. Returns True iff the row was written."""
    try:
        payload = {"proposal": proposal, "delta": verdict.get("delta"),
                   "target_kind": verdict.get("target_kind"),
                   "target_id": verdict.get("target_id"),
                   "status": "pending_review"}
        await _mios_pg.execute(
            "INSERT INTO event (source, kind, severity, summary, payload) "
            "VALUES (%(source)s, %(kind)s, %(severity)s, %(summary)s, %(payload)s::jsonb)",
            {"source": "agent-pipe", "kind": _PROPOSAL_EVENT_KIND, "severity": "info",
             "summary": (f"self-improve proposal queued: "
                         f"{verdict.get('target_kind')}:{verdict.get('target_id')} "
                         f"(delta {verdict.get('delta')})"),
             "payload": json.dumps(payload)}, fetch=False)
        return True
    except Exception as e:  # noqa: BLE001 -- queue is best-effort; never break the loop
        log.warning("self-improve: proposal queue write skipped: %s", e)
        return False


async def _selfimprove_act_pass() -> dict:
    """One ACT pass: findings -> proposals -> proof-of-utility -> QUEUE (no apply).

    DEFAULT-OFF: returns a no-op summary unless [selfimprove].act_enabled. For each
    high/medium finding (bounded by max_proposals_per_pass): draft a proposal, REJECT
    it up front if it is not in the SSOT improvable surface / is in the protected
    surface (structural isolation -- it is never even scored), else prove utility
    (pass^k non-regression) and QUEUE only a non-regressing proposal. Every accept/
    reject is logged with the score delta (Autodata rejects ~half its own proposals).
    Degrade-open: any error drops the current proposal, never the loop. Returns a
    summary {acted, findings, drafted, queued, rejected}."""
    sect = _toml_section("selfimprove")
    if not bool(sect.get("act_enabled", False)):
        return {"acted": False, "reason": "disabled", "queued": 0, "rejected": 0}
    improvable = sect.get("improvable_targets") or []
    protected = sect.get("protected_targets") or []
    margin = float(sect.get("accept_margin", 0.0))
    require_improvement = bool(sect.get("require_improvement", False))
    max_props = int(sect.get("max_proposals_per_pass", 3))
    rep = await _selfimprove_report()
    findings = [f for f in rep.get("findings", [])
                if f.get("severity") in ("high", "medium")]
    queued = rejected = drafted = 0
    for finding in findings[:max(0, max_props)]:
        try:
            proposal = await _act_draft_proposal(finding)
            if not proposal:
                continue
            drafted += 1
            # Structural isolation FIRST: a proposal that targets the evaluator /
            # eval-data / lane-config (or anything outside the improvable surface) is
            # rejected before any solver compute is spent scoring it.
            ok, why = mios_selfimprove_act.validate_proposal(
                proposal, improvable=improvable, protected=protected)
            if not ok:
                rejected += 1
                log.warning("self-improve ACT: proposal REJECTED (isolation: %s) "
                            "target=%s:%s", why, proposal.get("target_kind"),
                            proposal.get("target_id"))
                continue
            scores = await _act_evaluate_proposal(proposal)
            if not scores:
                continue  # cannot prove utility -> do not queue
            verdict = mios_selfimprove_act.decide_proposal(
                proposal, baseline_score=scores[0], proposed_score=scores[1],
                improvable=improvable, protected=protected,
                margin=margin, require_improvement=require_improvement)
            if verdict.get("accept"):
                if await _act_queue_proposal(proposal, verdict):
                    queued += 1
                    log.info("self-improve ACT: proposal QUEUED (delta %.4f) "
                             "target=%s:%s -- awaiting human approval",
                             verdict.get("delta") or 0.0,
                             verdict.get("target_kind"), verdict.get("target_id"))
            else:
                rejected += 1
                log.info("self-improve ACT: proposal REJECTED (%s, delta %.4f) "
                         "target=%s:%s", verdict.get("reason"),
                         verdict.get("delta") or 0.0,
                         verdict.get("target_kind"), verdict.get("target_id"))
        except Exception as e:  # noqa: BLE001 -- one bad proposal never breaks the pass
            log.debug("self-improve ACT: proposal error: %s", e)
    return {"acted": True, "findings": len(findings), "drafted": drafted,
            "queued": queued, "rejected": rejected}


async def _selfimprove_proposals(limit: int = _PROPOSALS_LIST_LIMIT) -> dict:
    """The QUEUED self-improvement proposals awaiting human approval (read-only).
    Degrade-open -> {proposals:[], error} when pg is unreachable so the route stays
    up. These are validated + non-regressing (T-064) but NEVER auto-applied."""
    try:
        rows = await _mios_pg.execute(
            "SELECT id, severity, summary, payload, ts FROM event "
            "WHERE kind = %(kind)s ORDER BY ts DESC LIMIT %(lim)s",
            {"kind": _PROPOSAL_EVENT_KIND, "lim": int(limit)}, fetch=True) or []
        return {"proposals": rows, "count": len(rows)}
    except Exception as e:  # noqa: BLE001 -- degrade-open
        log.warning("self-improve proposals unavailable: %s", e)
        return {"proposals": [], "count": 0, "error": "unavailable"}


async def _selfimprove_loop() -> None:
    try:
        interval = int(_toml_section("selfimprove").get("interval_min", 0))
    except Exception:  # noqa: BLE001
        interval = 0
    if interval <= 0:
        return
    log.info("self-improve: proactive surfacing loop every %d min", interval)
    while True:
        try:
            await asyncio.sleep(interval * 60)
            rep = await _selfimprove_report()
            new = 0
            for f in rep.get("findings", []):
                if f.get("severity") not in ("high", "medium"):
                    continue
                key = (f.get("kind"), f.get("subject"))
                if key in _SELFIMPROVE_SEEN:
                    continue
                _SELFIMPROVE_SEEN.add(key)
                new += 1
                log.warning("self-improve [%s] %s: %s -- %s",
                            f.get("severity"), f.get("subject"),
                            f.get("detail"), f.get("suggestion"))
            if new:
                log.info("self-improve: surfaced %d new finding(s)", new)
            # ACT half (T-062/T-064): default-OFF no-op unless [selfimprove].act_enabled;
            # when on, propose->prove->QUEUE non-regressing changes for human approval
            # (never auto-applied). Self-gating + degrade-open inside the pass.
            await _selfimprove_act_pass()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 -- degrade-open; never crash the loop
            log.debug("self-improve loop: %s", e)


def _kv_gc_sweep_once() -> None:
    """WS-A4: one GC pass over the LOCAL KV slot dir (no-op when it's remote /
    unset / empty). Plans TTL+size eviction via mios_kvgc, protecting the file of
    whatever conversation is resident in the active slot, then removes evictees.
    Best-effort + degrade-open: any error leaves the files (the tmpfiles age-out
    is the backstop)."""
    d = KV_SLOTS_DIR
    if not (d and os.path.isdir(d)):
        return
    try:
        files = []
        for fn in os.listdir(d):
            if not (fn.startswith(_KV_FILE_PREFIX) and fn.endswith(_KV_FILE_SUFFIX)):
                continue
            p = os.path.join(d, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            files.append({"path": p, "mtime": st.st_mtime, "size": st.st_size})
        protect = {os.path.join(d, _kv_filename(c))
                   for c in _KV_RESIDENT.values() if c}
        plan = mios_kvgc.plan_gc(files, ttl_s=KV_GC_TTL_S,
                                 max_bytes=KV_GC_MAX_BYTES, now=time.time(),
                                 protect=protect)
        for p in plan.evict:
            try:
                os.remove(p)
            except OSError:
                pass
        if plan.evict:
            log.info("kv-gc: removed %d KV file(s), freed ~%d bytes",
                     len(plan.evict), plan.freed_bytes)
    except Exception:  # noqa: BLE001 -- GC is best-effort
        pass


async def _kv_gc_loop() -> None:
    """Periodic KV slot-file GC. Sleeps first (no boot sweep), then every
    KV_GC_INTERVAL_S. Survives errors (matches _knowledge_evict_loop)."""
    while True:
        try:
            await asyncio.sleep(max(60, int(KV_GC_INTERVAL_S)))
            _kv_gc_sweep_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            await asyncio.sleep(60)


# -- @app -> APIRouter migration (refactor R13 batch 3: self-improve OBSERVE) -----
# The read-only #64 self-improvement report (/v1/self-improve/report) -- the OBSERVE
# half whose analyzer (_selfimprove_report) lives in THIS module -- moved off
# server.py's @app onto this co-located daemons_router (the same routes->APIRouter
# pattern the /a2a wave established). server.py imports daemons_router +
# selfimprove_report_ep (re-imported there so its importable `provided` surface is
# unchanged) and mounts the router via app.include_router(daemons_router); the served
# path/method is identical (the live-app route gate proves it). The body calls the
# module-resident _selfimprove_report DIRECTLY (no sys.modules hop). One-way boundary:
# this module never imports server. APIRouter()/method decorators are structural.
daemons_router = APIRouter()


@daemons_router.get("/v1/self-improve/report")
async def selfimprove_report_ep() -> JSONResponse:
    """Read-only self-improvement signals (failing/slow tools, unreliable peers)
    from local outcome data -- the OBSERVE half of #64. Acting on them (closing
    the loop) is a separate, gated step."""
    return JSONResponse({"object": "mios.self_improve.report",
                         **(await _selfimprove_report())})


@daemons_router.get("/v1/self-improve/proposals")
async def selfimprove_proposals_ep() -> JSONResponse:
    """Read-only: the QUEUED self-improvement proposals awaiting human approval -- the
    ACT half of #64 (T-062). Each was validated for target isolation and proven
    non-regressing (T-064 proof-of-utility) before queuing, but is NEVER auto-applied:
    the operator reviews + approves out of band, then a separate path applies it."""
    return JSONResponse({"object": "mios.self_improve.proposals",
                         **(await _selfimprove_proposals())})
