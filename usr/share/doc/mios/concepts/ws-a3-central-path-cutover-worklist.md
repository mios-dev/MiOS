<!-- AI-hint: WS-A3 follow-up worklist -- the precise, code-grounded SurrealDB->pg cutover checklist for the CENTRAL chat path (agent-pipe server.py + the OWUI pipe), which is intentionally NOT edited blind (live path; edits are inert until the dual->postgres flip, so they must be done WITH the VM build/boot loop and verified live as each gate flips). Corrects two audit overstatements, lists genuinely-broken vs cosmetic-redundant sites with exact pg translations + per-site risk, and the one activating decision.
     AI-related: ../../../../../usr/lib/mios/agent-pipe/server.py, ../../../../../usr/share/mios/owui/pipes/mios_agent_pipe.py, ../../../../../usr/share/mios/postgres/schema-init.sql, ./ws-a3-surreal-to-pg-cutover.md -->
# WS-A3 — central-path (server.py + OWUI pipe) SurrealDB→pg cutover worklist

Status: **audited + planned, NOT yet applied.** The CLI/daemon halves of WS-A3 are
done ([[ws-a3-surreal-to-pg-cutover]]); this is the remaining central-path surface.
It is deliberately left for the **VM build/boot loop**, not edited blind, because:

- The default backend is **`dual`** (`mios.toml [pgvector].db_backend`). In dual,
  `_PG_PRIMARY` is False, so the pg path of `_db_read`/`_db_update` and the
  `_PG_PRIMARY`-gated writes are **inert** — edits here change nothing until the
  flip. By the codebase's own design ("INERT in surreal/dual, read translations
  added incrementally + go live at the flip"), so doing them now (compile-verified
  only) is strictly *worse* than doing them during the flip session where each is
  verified live. This is the live chat path; the operator live-tests it.

## The one activating decision (do this in the VM, verify live)

Pick how to go pg-primary, then verify a chat end-to-end:
- **Option A (recommended, matches the daemon fix):** flip the READ/UPDATE gates
  `_PG_PRIMARY` → `_PG_ENABLED` in server.py `_db_read`/`_db_update` (so dual-mode
  reads/updates use the pg translation). Non-regressive (missing translation →
  SurrealDB → `[]`, same as now). Then the un-mirrored writes below still need
  their pg path added.
- **Option B:** flip `[pgvector].db_backend` `dual`→`postgres`. Activates
  `_PG_PRIMARY`; writes already mirrored via `_db_create`/`_pg_mirror` go pg-only;
  but the un-mirrored writes below are STILL lost (they bypass `_db_create`) — so
  the per-site fixes are required either way.

Whichever: the daemon already runs `_PG_ENABLED`-gated reads (done), so Option A
keeps daemon + agent-pipe consistent.

## Corrections to the raw audit (verified against the source)

- **NOT broken (cosmetic-redundant):** `_store_knowledge` (server.py ~11106-11111),
  `_hitl_record_pending` (~14167-14178), `_record_run_template_open`
  (~15247-15263). Each calls `_pg_mirror(...)` (or `_db_create` with mirror) FIRST,
  so **pg already gets the row**; the trailing `if not _PG_PRIMARY: await
  _db_post(sql)` is just a wasted dead-surreal write in dual. Fix = drop the
  `if not _PG_PRIMARY: _db_post(...)` line (cosmetic; no data loss today).
- The OWUI pipe writes ARE genuinely unmirrored (that file has no `_pg_mirror`).

## Genuinely-broken sites (raw `_db_post`/`_db_update` — NO pg mirror → data loss when pg-primary, and the UPDATEs are lost in dual too)

server.py (target columns ALL already exist in schema-init.sql unless noted):
| lines | func | fix (pg) | risk |
|---|---|---|---|
| 12414-12415, 12472-12473 | `execute_skill` success | `UPDATE skill SET last_used_at = now() WHERE id = %(id)s` (col exists L160) via `_db_update(surreal, pg_sql=…, pg_params=…)` | safe-mechanical |
| 12254-12257 | `_skill_invocation_close` | `UPDATE skill_invocation SET ended_at = now(), success = %(s)s WHERE id = %(id)s` (cols exist L172) — needs the invocation's pg bigint id (thread it from the INSERT … RETURNING id at open, via `_SKILL_INV_META`) | vm-verify |
| 12268-12272 | `_skill_attribute_tool_call` (RELATE edge) | **schema gap**: no `tool_call_emissions` table. Either add `CREATE TABLE tool_call_emissions(skill_invocation_id bigint, tool_call_id bigint, step_index int, PRIMARY KEY(skill_invocation_id, tool_call_id))` + insert, OR add `emitted_by_invocation bigint` to `tool_call` and set it. Decide the model first. | vm-verify |
| 14251, 14255 | `hitl_approve` | `UPDATE pending_action SET status=%(st)s, decided_at=now(), approver=%(apr)s, approval_passport=%(p)s::jsonb WHERE id=%(id)s` (cols exist L196-199) | vm-verify (audit-critical) |

OWUI pipe `usr/share/mios/owui/pipes/mios_agent_pipe.py` (NO pg path at all today;
all fire-and-forget `_db_fire` writes to dead :8000). Simplest faithful fix: give
it a `_pg_mirror`/`mios_pg.insert` helper (or route these through the agent-pipe
which already logs them — confirm topology first to avoid double-logging):
| lines | func | stream | fix |
|---|---|---|---|
| 1394-1403 | `_classify_intent` | router `event` (classify verdict) | mirror-only → pg `event` insert |
| 1620-1646 | `_dispatch_mios_verb` | `tool_call` + latency_ms | pg `tool_call` insert (needs session_id below) |
| 1910-1930 | `_critic_via_cpu` | critic `event` | pg `event` insert |
| 2310-2341 | `pipe` | `session` create + id (blocking `await`) | pg `INSERT INTO session(platform, owui_chat_id, model, started_at) VALUES('owui', %(c)s, %(m)s, now()) RETURNING id` |

NB: confirm whether the agent-pipe (:8640) already records `event`/`tool_call`/
`session` for OWUI turns — if so, these owui-pipe writes are duplicate observability
and can simply be dropped (mirror-only stub) rather than re-homed to pg.

## Recommended VM sequence
1. Apply the cosmetic drops + the safe-mechanical `last_used_at` `_db_update`s.
2. Decide the RELATE-edge model; add the schema table/column if kept.
3. Add the invocation-id threading + the `_skill_invocation_close` / `hitl_approve`
   updates; resolve OWUI-pipe duplication.
4. Flip per Option A; `just build` → boot → run a chat that mines a skill, an HITL
   approval, and an OWUI turn; verify rows land in pg (`mios-db --pg "SELECT … "`).
