# AI-hint: BACKGROUND async daemon-loop bodies extracted VERBATIM from server.py AI-related: ./server.py, ./mios_config.py, ./mios_gossip.py, ./mios_p...
# AI-doc: usr/share/doc/mios/manual/kernel.md

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
from mios_kvfork import (kv_filename as _kv_filename,
                         _FILE_PREFIX as _KV_FILE_PREFIX,
                         _FILE_SUFFIX as _KV_FILE_SUFFIX)

log = logging.getLogger("mios-agent-pipe")

_get_client = None
_A2A_PEERS = None
_A2A_PEERS_LOCK = None
_A2A_REPUTATION = None
_reload_membership = None
_SELFIMPROVE_SEEN = None
_MEMBERSHIP_WATCH_PATHS = None
MEMBERSHIP_WATCH_INTERVAL_S = 30
_PG_PRIMARY = False

MEMORY_CONSOLIDATE_ENABLED = True
MEMORY_CONSOLIDATE_INTERVAL_S = 3600
MEMORY_CONSOLIDATE_MAX_GROUPS = 200

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
    "_KV_RESIDENT", "MEMORY_CONSOLIDATE_ENABLED",
    "MEMORY_CONSOLIDATE_INTERVAL_S", "MEMORY_CONSOLIDATE_MAX_GROUPS",
))

def configure(**deps) -> None:
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

_PROPOSAL_EVENT_KIND = "self_improve_proposal"
_PROPOSALS_LIST_LIMIT = 100

async def _act_draft_proposal(finding: dict) -> Optional[dict]:
    return None

async def _act_evaluate_proposal(proposal: dict) -> Optional[tuple]:
    return None

async def _act_queue_proposal(proposal: dict, verdict: dict) -> bool:
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
            await _selfimprove_act_pass()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 -- degrade-open; never crash the loop
            log.debug("self-improve loop: %s", e)

def _kv_gc_sweep_once() -> None:
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

async def _consolidate_memory_sweep_once() -> dict:
    """One consolidation pass over `knowledge`: collapse same-question rows into
    the newest, folding counters in. Postgres-only. Details in ch54."""
    stats = {"groups": 0, "merged": 0, "skipped": 0}
    if not (_PG_PRIMARY and _mios_pg):
        stats["skipped"] = 1
        return stats
    limit = max(1, int(MEMORY_CONSOLIDATE_MAX_GROUPS))
    # One statement per group keeps each merge atomic; a single mega-CTE would
    # roll the whole sweep back on one bad row.
    sql_groups = (
        "SELECT lower(btrim(q)) AS nq, count(*) AS n "
        "FROM knowledge WHERE pinned IS NOT TRUE "
        "GROUP BY lower(btrim(q)) HAVING count(*) > 1 "
        "ORDER BY count(*) DESC LIMIT %(lim)s"
    )
    try:
        groups = await _mios_pg.execute(sql_groups, {"lim": limit}, fetch=True)
    except Exception:  # noqa: BLE001 -- consolidation is best-effort
        log.debug("consolidate: could not list duplicate groups")
        stats["skipped"] = 1
        return stats
    for row in (groups or []):
        nq = (row or {}).get("nq")
        if not nq:
            continue
        stats["groups"] += 1
        try:
            merged = await _consolidate_group(str(nq))
            stats["merged"] += merged
        except Exception:  # noqa: BLE001
            stats["skipped"] += 1
    if stats["merged"]:
        log.info("consolidate: merged %d duplicate knowledge row(s) across %d group(s)",
                 stats["merged"], stats["groups"])
    return stats

async def _consolidate_group(nq: str) -> int:
    """Merge one normalized-question group into its newest row. Returns the
    number of rows removed (0 when the group turned out to be unmergeable)."""
    rows = await _mios_pg.execute(
        "SELECT id, access_count, recall_hits, last_access, pinned "
        "FROM knowledge WHERE lower(btrim(q)) = %(nq)s "
        "ORDER BY ts DESC, id DESC", {"nq": nq}, fetch=True)
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if len(rows) < 2:
        return 0
    if any(r.get("pinned") for r in rows):
        # A pinned row in the group means an operator asked for that exact
        # entry to survive; merging could delete it, so leave the group whole.
        return 0
    keep = rows[0]
    losers = []
    for r in rows[1:]:
        try:
            losers.append(int(r["id"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not losers:
        return 0
    access = sum(int(r.get("access_count") or 0) for r in rows)
    recall = sum(int(r.get("recall_hits") or 0) for r in rows)
    await _mios_pg.execute(
        "UPDATE knowledge SET access_count = %(a)s, recall_hits = %(r)s, "
        "last_access = GREATEST(coalesce(last_access, ts), "
        "  (SELECT max(coalesce(last_access, ts)) FROM knowledge "
        "   WHERE lower(btrim(q)) = %(nq)s)) "
        "WHERE id = %(id)s",
        {"a": access, "r": recall, "nq": nq, "id": int(keep["id"])}, fetch=False)
    await _mios_pg.execute(
        "DELETE FROM knowledge WHERE id = ANY(%(ids)s)",
        {"ids": losers}, fetch=False)
    return len(losers)

async def _consolidate_memory_loop() -> None:
    """Periodic knowledge-memory consolidation. Sleeps first (no boot sweep),
    then every MEMORY_CONSOLIDATE_INTERVAL_S. Survives errors."""
    while True:
        try:
            await asyncio.sleep(max(60, int(MEMORY_CONSOLIDATE_INTERVAL_S)))
            if not MEMORY_CONSOLIDATE_ENABLED:
                continue
            await _consolidate_memory_sweep_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            await asyncio.sleep(60)

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
    return JSONResponse({"object": "mios.self_improve.proposals",
                         **(await _selfimprove_proposals())})
