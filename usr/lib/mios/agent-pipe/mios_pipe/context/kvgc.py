# AI-hint: WS-A4 KV-cache file garbage-collection PLANNER. Pure-stdlib decision core for reclaiming the on-disk KV slot-save files the agent-pipe writes...
# AI-doc: usr/share/doc/mios/manual/context.md

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

    if max_bytes and sum(s["size"] for s in survivors) > int(max_bytes):
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
