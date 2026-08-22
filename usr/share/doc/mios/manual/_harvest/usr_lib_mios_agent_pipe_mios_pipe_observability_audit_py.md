<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: SEC-03 tamper-evident SHA-256 hash chain over the agent-plane `event` stream. Holds the PURE, dependency-free chain primitives (canonical_core over a row's immutable content fields, link_hash = sha256(prev || core), the EventChainer in-memory head that stamps each event with chain_seq/prev_hash/chain_hash at the single _db_create persist chokepoint, and verify_chain which walks rows in chain_seq order and reports the first broken link) PLUS the admin-gated GET /v1/audit/chain/verify route on its own co-located audit_router. The crypto is stdlib-only (hashlib/json) so the verifier reuses the SAME algorithm headless -- mios-chain-verify (a confined CLI) and the unit suite import it WITHOUT the web stack, mirroring mios_pg's lazy-psycopg testability (fastapi is imported behind a degrade-open shim). Degrade-open everywhere: a stamp/seed/verify failure NEVER breaks event logging (tamper-evidence is best-effort; the event must always land). The chain head is seeded once from max(chain_seq) at startup so the hot path never does a SELECT-max per insert.
AI-related: ./server.py, ./mios_pg.py, ./mios_http_caps.py, ./test_mios_audit.py, ../../../libexec/mios/mios-chain-verify, ../../../share/mios/postgres/schema-init.sql, ../../../share/mios/ai/v1/surface.generated.json
AI-functions: canonical_core, link_hash, EventChainer.seed, EventChainer.stamp, stamp, seed_from_db, verify_chain, chain_verify_logic, chain_verify, configure

<!-- mios-src:60ac2032bd69 from usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py:1-3 -->

