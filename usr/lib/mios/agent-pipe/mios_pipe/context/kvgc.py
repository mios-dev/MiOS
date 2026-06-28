# AI-hint: WS-A4 KV-cache file garbage-collection PLANNER. Pure-stdlib decision core for reclaiming the on-disk KV slot-save files the agent-pipe writes for conversation paging + WS-8 KV-forks (mios-kv-*.bin / fork children) under the llama.cpp --slot-save-path. plan_gc() decides which files to evict by TTL (age) THEN a total-size cap (oldest-first), never touching protected/active-slot files -- so an unbounded fork fan-out can't fill the disk. server.py owns the actual deletion (when the slots dir is FS-accessible) + the background loop; the systemd-tmpfiles age-out is the OS-level backstop. This module is pure (no fs/network) so it unit-tests in isolation.
# AI-related: ./mios_kvfork.py, ./server.py, /usr/lib/tmpfiles.d/, /usr/share/mios/mios.toml, ./test_mios_kvgc.py
# AI-functions: plan_gc, class GcPlan
"""mios_kvgc -- KV slot-file GC planning (WS-A4, the AIOS Context-Manager KV
lifecycle layer).

Pure stdlib. The agent-pipe pages each conversation's KV to disk and (WS-8) can
FORK a parent's KV into child files for a swarm fan-out. Without a GC those
files accumulate. plan_gc() is the deterministic decision: given the current
slot files (path/mtime/size), a TTL and a total-size cap, and a protected set
(the active slot / current conversation), return which to evict. The caller
deletes them (or relies on the tmpfiles age-out backstop)."""

from __future__ import annotations

from typing import Iterable, List, Optional


class GcPlan:
    """A GC decision: which files to evict, which to keep, and bytes freed."""

    __slots__ = ("evict", "kept", "freed_bytes", "reasons")

    def __init__(self, evict: list, kept: list, freed_bytes: int, reasons: dict) -> None:
        self.evict = evict
        self.kept = kept
        self.freed_bytes = freed_bytes
        self.reasons = reasons  # path -> "ttl" | "size_cap"

    def to_dict(self) -> dict:
        return {
            "evict": len(self.evict),
            "kept": len(self.kept),
            "freed_bytes": self.freed_bytes,
            "reasons": dict(self.reasons),
        }


def plan_gc(files: Iterable[dict], *, ttl_s: float, max_bytes: int,
            now: float, protect: Optional[Iterable[str]] = None) -> GcPlan:
    """Decide which KV files to evict.

    files: iterable of {"path": str, "mtime": float, "size": int}.
    ttl_s: evict any non-protected file older than this (0 -> no TTL pass).
    max_bytes: after the TTL pass, if the surviving total still exceeds this,
               evict oldest-first until it fits (0 -> no size cap).
    now: current epoch seconds (passed in -> pure/deterministic).
    protect: paths that are NEVER evicted (the active slot / live conversation).
    """
    prot = {str(p) for p in (protect or [])}
    items = []
    for f in files or []:
        try:
            items.append({
                "path": str(f.get("path")),
                "mtime": float(f.get("mtime") or 0.0),
                "size": int(f.get("size") or 0),
            })
        except (TypeError, ValueError):
            continue
    evict: List[str] = []
    reasons: dict = {}

    # (1) TTL pass.
    survivors = []
    for it in items:
        if it["path"] in prot:
            survivors.append(it)
            continue
        if ttl_s and (now - it["mtime"]) > float(ttl_s):
            evict.append(it["path"])
            reasons[it["path"]] = "ttl"
        else:
            survivors.append(it)

    # (2) Size cap on the TTL survivors (oldest-first), never evicting protected.
    if max_bytes and sum(s["size"] for s in survivors) > int(max_bytes):
        # oldest first; protected files counted against the cap but never evicted.
        evictable = sorted((s for s in survivors if s["path"] not in prot),
                           key=lambda s: s["mtime"])
        total = sum(s["size"] for s in survivors)
        ev_set = set()
        for s in evictable:
            if total <= int(max_bytes):
                break
            ev_set.add(s["path"])
            evict.append(s["path"])
            reasons[s["path"]] = "size_cap"
            total -= s["size"]
        survivors = [s for s in survivors if s["path"] not in ev_set]

    freed = sum(it["size"] for it in items if it["path"] in set(evict))
    kept = [s["path"] for s in survivors]
    return GcPlan(evict, kept, freed, reasons)
