<!-- AI-hint: Spinoff task list handed to Gemini AGY to execute in the IDE, in parallel with Claude. Derived from the deploy + DB-driven workstreams Claude started (WS-DEPLOY runtime, WS-HEAVY runtime). AGY takes the CODE-ONLY half (no live-VM dependency) so the two agents don't collide. Each task is self-contained with Who/What/Where/When/How + Start-here + Done-When. -->

# AGY-TASKS — Gemini AGY spinoff (parallel to Claude)

**Handoff 2026-07-10.** Claude is executing the **runtime/deploy** half live on
`podman-MiOS-DEV` (webtools image build in progress; vLLM heavy-model provisioning
next). AGY takes the **code-only** half below — no live-VM needed, fully doable in
this IDE. These are derived from **WS-DEPLOY** (T-166), **WS-HEAVY** (T-178), and
**WS-VECTOR** (T-242) in `TASKS.md`. Work top-down; each is independent.

**Ground rules for AGY**
- Repo: `C:\MiOS` (the FHS overlay; `/usr`, `/etc`, `automation/` map to `/`). Read `CLAUDE.md` + `AGENTS.md` first.
- Match surrounding code; complete replacement files (no `# ... unchanged ...`).
- `bash -n` / PowerShell parse every script you touch; run `just drift-gate` before proposing done.
- Commit each task separately; prefix the subject `agy:` and end with your Co-Authored-By line. Do NOT touch the files Claude has open (the webtools builder, live install runs).
- The reference pattern for every "producer" fix is `automation/38-hermes-agent.sh` (commit 31a52fb1): install the COMPLETE set in ONE transaction, **retried 3x with backoff**, **verified** present, non-fatal to siblings.

---

## AGY-1  (WS-DEPLOY, P1) — atomic+retried+verified for the remaining firstboot producers
**Who:** you (bash/systemd). **When:** first — it mirrors the webtools/venv fixes Claude already landed.
**What + How:** apply the 38-hermes-agent reference pattern to the producers that still "run once, give up":
- `usr/libexec/mios/mios-ai-firstboot` — the vLLM/GGUF weights fetch (the `snapshot_download` blocks, ~L111-124 + L371): wrap in a 3x retry-with-backoff loop, verify the target `config.json`/`.ready` exists after, non-fatal per-model, log clearly. (This is the code half of **T-178**; the heavy lane is skipped today purely because this fetch had no retry and ran through the then-missing venv.)
- `usr/libexec/mios/forge-firstboot.sh` — replace the fixed `300s` timeout abort with a **readiness poll** (poll the forge health/socket, generous cap, `Restart=on-failure` on the unit) so a slow forge under load never hard-fails.
- Any other `*-firstboot` producer with a bare one-shot build/fetch (grep `usr/libexec/mios/*firstboot*`).
**Where:** `usr/libexec/mios/mios-ai-firstboot`, `usr/libexec/mios/forge-firstboot.sh`, their `usr/lib/systemd/system/*.service` (`Restart=on-failure` + `StartLimit*`).
**Done When:** each producer is atomic+retried+verified+idempotent; `bash -n` clean; a fresh reinstall would deploy them without manual retries.

## AGY-2  (WS-DEPLOY, P1) — DAG-integrity drift-gate (consumer-before-producer = build error)
**Who:** you (bash + the drift-gate framework). **When:** after AGY-1.
**What + How:** add a new check to `automation/38-drift-checks.sh` (next free check number, currently 25-28 exist → add 29) that parses the producer→consumer map and FAILS when a consumer unit/step can start before its producer's readiness artifact exists — i.e. a consumer `.container`/`.service` that depends on a built image / seeded row / fetched model but lacks `After=`/`Requires=`/`ConditionPathExists=` on its producer. Follow the existing `check_*` function style in that file; wire it into `main`; keep it read-only + fast (no built image needed). Full spec: `usr/share/doc/mios/reference/install-ordering.md` (WS-DEPLOY).
**Where:** `automation/38-drift-checks.sh`.
**Done When:** the gate flags at least the known-good edges (webtools pod After webtools-firstboot; agent-pipe After the venv) and passes on the current tree; `just drift-gate` green.

## AGY-3  (WS-VECTOR V0, P1) — DB projection foundation (no behavior change)
**Who:** you (SQL + Python, no live DB needed — static SQL/codegen). **When:** independent; can start immediately.
**What + How:** lay the foundation for `everything-db-driven.md` V0 WITHOUT flipping any authority:
- `usr/share/mios/postgres/schema-init.sql` — add the `config_layer(rank,name)` precedence table (seed {0:vendor,1:host,2:user,3:machine}) and `config_kv(scope,key,value jsonb,layer FK,owner_user,description,emb vector(768),emb_model,emb_version)` with an HNSW index on `emb` (mirror the `knowledge`/`agent_memory` DDL exactly — same `vector_cosine_ops m=16 ef_construction=64`). Idempotent (`CREATE TABLE IF NOT EXISTS` / guarded index).
- Write a **DB→TOML materialize** peer of `usr/libexec/mios/seed-db-config.py` (e.g. `usr/libexec/mios/materialize-config-toml.py`) that reads `config_kv`/`verb`/`domain_verb` and regenerates a TOML the drift-gate can diff — the inverse of today's TOML→DB seeding. Keep it read-only w.r.t. the DB.
- Make the existing `verb` round-trip **lossless**: ensure `seed-db-config.py` + the new materializer preserve section/examples/model_name/hidden/aliases/conflict_group/parallel_limit/max_result_chars.
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/libexec/mios/seed-db-config.py`, new `usr/libexec/mios/materialize-config-toml.py`.
**Done When:** schema applies idempotently; `seed-db-config.py` TOML→DB then materialize DB→TOML round-trips a verb losslessly (diff clean); nothing reads the new tables at runtime yet (V1 flips that — leave it).

## AGY-4  (WS-NAME, P2) — the unified names/keys registry generator + gate
**Who:** you (Python + drift-gate). **When:** independent.
**What + How:** per `usr/share/doc/mios/reference/naming-unification.md`: write the generator that emits `usr/share/mios/names.generated.txt` (one `section.key  MIOS_SECTION_KEY` per line) from `mios.toml`, and a drift-gate check (in `38-drift-checks.sh`) that regenerates + diffs it and fails on any NEW translation/duplicate (an env var that renames a native key, or a second name for one capability). Do NOT yet delete the `userenv.sh` table — this is the enforcement scaffold only (T-165 Phase 0).
**Where:** new `tools/generate-names-registry.py`, `automation/38-drift-checks.sh`, `usr/share/mios/names.generated.txt`.
**Done When:** the registry generates deterministically; the gate is green on the current tree and would fail on an injected duplicate; `just drift-gate` passes.

---

### Reporting back
Commit each task as `agy: <task-id> <summary>` and push to `main`. Claude is monitoring
`main` for your commits + will integrate/verify. If blocked, leave a `TODO(agy):` note in
the file and move to the next task. Full context for every item is in `TASKS.md`
(T-166, T-178, T-242, T-165) and the `usr/share/doc/mios/reference/*.md` workstream docs.
