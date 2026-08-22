<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_kvgc -- KV slot-file GC planning (WS-A4, the AIOS...

mios_kvgc -- KV slot-file GC planning (WS-A4, the AIOS Context-Manager KV
lifecycle layer).

Pure stdlib. The agent-pipe pages each conversation's KV to disk and (WS-8) can
FORK a parent's KV into child files for a swarm fan-out. Without a GC those
files accumulate. plan_gc() is the deterministic decision: given the current
slot files (path/mtime/size), a TTL and a total-size cap, and a protected set
(the active slot / current conversation), return which to evict. The caller
deletes them (or relies on the tmpfiles age-out backstop).

<!-- mios-src:3d8f6b3bf4d6 from usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py:3-11 -->

### Decide which KV files to evict. files

Decide which KV files to evict.

    files: iterable of {"path": str, "mtime": float, "size": int}.
    ttl_s: evict any non-protected file older than this (0 -> no TTL pass).
    max_bytes: after the TTL pass, if the surviving total still exceeds this,
               evict oldest-first until it fits (0 -> no size cap).
    now: current epoch seconds (passed in -> pure/deterministic).
    protect: paths that are NEVER evicted (the active slot / live conversation).

<!-- mios-src:8a7d91922954 from usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py:40-48 -->
