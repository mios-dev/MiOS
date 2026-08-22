<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_memory -- pluggable agent-memory provider seam...

mios_memory -- pluggable agent-memory provider seam (WS-A15, the AIOS
Memory-Manager abstraction).

Pure stdlib so it unit-tests in isolation (the default provider takes its
backend by INJECTION, so a fake stands in for mios_pg with no DB). server.py
owns the wiring (SSOT [pgvector].memory_provider, the module-global _MEMORY, and
routing the recall call sites through it); this module owns only the interface +
the pgvector-backed default.

Why a seam
==========
Before WS-A15 the recall path called mios_pg.recall(...) directly at each site,
so the storage backend was hard-wired. The MemoryProvider interface (retrieve /
add) lets the backend be swapped -- a different vector DB, a remote memory
service, or a test double -- behind ONE resolution point, without editing the
recall logic. The default (pgvector) is a verbatim pass-through to mios_pg, so
behaviour is byte-identical until a different provider is configured.

<!-- mios-src:4d3f14779fe0 from usr/lib/mios/agent-pipe/mios_pipe/memory/memory.py:3-20 -->
