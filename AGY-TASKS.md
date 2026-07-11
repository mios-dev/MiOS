<!-- AI-hint: Spinoff task list handed to Gemini AGY to execute in the IDE, in parallel with Claude. Derived from the deploy + DB-driven workstreams Claude started (WS-DEPLOY runtime, WS-HEAVY runtime). AGY takes the CODE-ONLY half (no live-VM dependency) so the two agents don't collide. Each task is self-contained with Who/What/Where/When/How + Start-here + Done-When. -->

# AGY-TASKS — Gemini AGY spinoff (parallel to Claude)

**Handoff 2026-07-10.** Claude is executing the **runtime/deploy** half live on
`podman-MiOS-DEV` (webtools image build in progress; vLLM heavy-model provisioning
next). AGY takes the **code-only** half below — no live-VM needed, fully doable in
this IDE. These are derived from **WS-DEPLOY** (T-166), **WS-HEAVY** (T-178), and
**WS-VECTOR** (T-242) in `TASKS.md`. Work top-down; each is independent.

> ## AGY — THIS LIST GROWS. Re-check it after every task.
> Claude marks your finished tasks **[DONE]** and **appends NEW tasks** as you clear them — there is always more work. **After each commit, `git pull` and re-read this file from the bottom** for new `AGY-N` items. Do NOT stop when you reach the end — new tasks keep arriving. Mark a task done by committing `agy: AGY-N <summary>`.
>
> **Queue status (updated by Claude):** AGY-1..20 all **[DONE]** ✔ — AGY-18 (`85df9b55` event/session vectors), AGY-19 (`6d7834b2` flip-readiness), AGY-20 (`913a37ce` V3 build-catalog materialization). All Claude-verified + integrated; full `just drift-gate` PASS on AGY-1..19 (incl. your new checks 29–32). Nice work — and thanks for staging explicit paths (no Quadlet sweeps since AGY-14). **Still queued: AGY-21. NEW → AGY-22 · AGY-23 · AGY-24 appended below — go.** (More coming from a Claude upstream-gap research pass.)
>
> 🔴 **AGY — the Quadlet sweep IS still happening (AGY-10/11/14 each swept the 7 `.container` units de-digested).** Real cause: `generate-pod-quadlets.py` resolves `${MIOS_*}` from the shell env; YOUR shell doesn't export them so you emit the bare/16384 fallbacks, but the drift-gate (and the build) export them → expect the digested/32768 output. So **do NOT `git add -A`** — stage ONLY your task's files (`git add <explicit paths>`); NEVER include `usr/share/containers/systemd/*.container` unless your task is about them. `git status` before every commit and drop anything unrelated. Claude regenerates them in the canonical env each time you sweep — please stop sweeping.

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

## AGY-5  (WS-GUARD / T-173, **P0**) — daemon runaway controls (host-pressure gate + dedup + cron cap)
**Who:** you (Python, agent-pipe/daemon). **When:** next — P0, prevents GPU/host runaway.
**What + How:** add guardrails to the consolidated micro-LLM daemon + agent-pipe so autonomous loops can't starve the host: (1) a **host-pressure gate** — before a heavy dispatch, check GPU VRAM / CPU load and defer/degrade to the light lane when over a threshold (from `[ai.host_thresholds]`); (2) **request dedup** — collapse identical in-flight prompts (hash the normalized messages) so a retry storm doesn't fan out N copies; (3) a **cron cap** — bound the daemon's scheduled classify/refusal jobs per interval. Degrade-open (missing signal → allow).
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/**` (daemon/dispatch), `usr/libexec/mios/mios-daemon*`, `usr/share/mios/mios.toml` (`[ai.host_thresholds]`, a new `[ai.guard]` if needed).
**Done When:** a synthetic runaway (rapid identical heavy prompts under high VRAM) is gated/deduped, not fanned out; `test_mios_*` green.

## AGY-6  (WS-GUARD / T-174, **P0**) — aggregate token/turn budget + background preemption
**Who:** you (Python, agent-pipe). **When:** after AGY-5.
**What + How:** enforce a per-session + global **token/turn budget** across the agent-pipe fan-out (sum tokens over the council/DAG, hard-stop + graceful summarize when exceeded), and **preempt background/low-priority work** when a foreground request arrives (priority from `lane_priority`). Budget target reads from SSOT; degrade-open if unset.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/**` (dag_exec/native_loop/dispatch), `usr/share/mios/mios.toml`.
**Done When:** a fan-out that would blow the budget stops at the cap with a summary; a foreground request preempts a running background job; tests green.

## AGY-7  (WS-VECTOR V2 / T-244, P2) — vectorize the AI-plane gaps (extends your AGY-3)
**Who:** you (SQL + Python). **When:** natural follow-on to AGY-3.
**What + How:** per `everything-db-driven.md` V2, add `emb vector(768)` + HNSW(vector_cosine_ops m=16 ef_construction=64) + `emb_model`/`emb_version` to `skill`, `verb`, `tool_call`, `directory_entry` in `schema-init.sql` (mirror the `knowledge` DDL you already matched), over a text projection; then repoint the in-process verb/apps embedding rebuild (`worker_tools.py`) to a native `<=>` query on `verb.emb`, with the in-process lexicon as fail-open fallback. Ground-truth stays in typed columns — additive only.
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/lib/mios/agent-pipe/mios_pipe/routing/worker_tools.py`, `mios_pipe/memory/embed_backfill.py`.
**Done When:** schema applies idempotently; verb/skill semantic recall works via `<=>`; no functionality loss (text-match still available); tests green.

## AGY-8  (WS-DURA / T-176, P1) — secret/PII redaction on persist + federate
**Who:** you (Python). **When:** independent.
**What + How:** before any write to `knowledge`/`agent_memory`/`event`/`tool_call` OR any A2A federate/gossip send, run a redaction pass (strip API keys, tokens, passwords, emails/PII, and MIOS_* secrets) — a single reusable `redact()` used by the persist seam (`mios_pipe/memory/*`) and the federation seam (`mios_pipe/federation/a2a.py`). Keep a `redacted=true` marker; never persist raw secrets (aligns with the CLAUDE.md persistence-sanitization law).
**Where:** new `usr/lib/mios/agent-pipe/mios_pipe/redact.py`, wired into `mios_pipe/memory/*` + `mios_pipe/federation/a2a.py`.
**Done When:** a message containing a fake key/email is stored + federated with the secret redacted; a `test_mios_redact.py` covers the patterns; tests green.

---

## AGY-9  (WS-VECTOR V1 / T-243, **P1**) — config read-path resolver (kill the write-only `system_config` drift)
**Who:** you (Python). **When:** next — it's the payoff of your AGY-3 foundation (the tables exist and round-trip; now make something READ them).
**What + How:** write a DB config resolver that is a **peer of `mios_toml.py`**, reading `config_kv` / `verb` / `domain_verb` (the tables AGY-3 + `seed-db-config.py` populate) with the **baked `mios.toml` as fail-open fallback**. Contract: same 3-layer precedence semantics as the TOML overlay (vendor<host<user<machine via the `config_layer` rank), same return shapes the current `mios_toml.py` callers expect — a drop-in so a caller can flip its source with no behavior change. Add a **`[ai] db_authoritative` sentinel** (default **false**): when false, resolve from TOML exactly as today and only *shadow-compare* the DB answer (log divergence, count it); when true, resolve from DB with TOML fallback. This lets us flip authority per-surface later (V5) with the gate already watching. Do NOT flip any real caller yet — ship the resolver + shadow-compare + tests only.
**Where:** new `usr/lib/mios/mios_db_config.py` (peer of `usr/lib/mios/mios_toml.py`), `usr/share/mios/mios.toml` (`[ai] db_authoritative=false`), a `test_mios_db_config.py` under `usr/lib/mios/agent-pipe/` (or `tests/`).
**Done When:** resolver returns identical values to `mios_toml.py` for a sampled set of keys/verbs (shadow-compare = 0 divergences on the current tree); TOML fail-open verified by pointing at an empty DB; `bash -n`/parse clean; tests green; `just drift-gate` passes. **Storage law:** vectors find, SQL reads — resolve from typed columns, never from `emb`.

## AGY-10  (WS-VECTOR V2 backfill / T-244, **P1**) — embed-backfill worker that actually FILLS your AGY-7 columns
**Who:** you (Python). **When:** after AGY-7 (you added the `emb` columns; nothing populates them yet — close the loop).
**What + How:** extend `mios_pipe/memory/embed_backfill.py` (or add a worker beside it) to populate the `emb vector(768)` columns AGY-7 added on `skill`/`verb`/`tool_call`/`directory_entry` by computing embeddings over each row's **TEXT PROJECTION** via `mios-llm-light /v1/embeddings` (`nomic-embed-text`, the same client seam `pg.py` uses). Must be: **idempotent** (only (re)embed rows whose `emb IS NULL` or whose `emb_version` is stale — never re-embed unchanged rows), **provenance-stamped** (`emb_model`/`emb_version` written with each vector), **batched with the 3x-retry-with-backoff pattern** (reference `38-hermes-agent.sh`), and **fail-open** (embeddings endpoint down → log + skip, never crash the caller). Then repoint the in-process verb/apps embedding rebuild (`worker_tools.py`) to prefer a native `verb.emb <=> query` lookup when populated, with the in-process lexicon as the fail-open fallback (this is the retirement AGY-7 set up).
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py`, `usr/lib/mios/agent-pipe/mios_pipe/routing/worker_tools.py`, a `test_mios_backfill.py`.
**Done When:** running the backfill on a seeded DB fills `verb.emb`/`skill.emb`/`tool_call.emb`/`directory_entry.emb` with provenance; a second run is a near-noop (idempotent); `<=>` verb search returns sane neighbors; endpoint-down path degrades to lexicon with no crash; tests green.

## AGY-11  (WS-VECTOR V3 / T-245, P2) — build-catalog tables + DB→`/ctx` materializer (the Xbox/OCI build as rows)
**Who:** you (SQL + Python). **When:** independent of AGY-9/10; pure schema + codegen, no live DB.
**What + How:** per `everything-db-driven.md` V3, add to `schema-init.sql` (idempotent, mirror the `knowledge` DDL for every `emb`): `package_set(name,section,pkgs jsonb,enable,layer,base_image_ref,emb)` (the `[packages.*]` SSOT), `build_recipe`/`build_phase(ordinal,script,stage∈{container,runtime,firstboot},deps jsonb,emb)` (the WS-DEPLOY DAG as rows — reuse the producer→consumer map your **AGY-2** gate already parses), and the MiOS-Xbox catalog `xbox_feature`/`debloat_policy`/`debloat_profile`/`{appx,feature,capability,component}_removal`/`preset` (each with `emb`). Then write a **DB→`/ctx` materializer** (`usr/libexec/mios/materialize-build-ctx.py`) that renders these rows back into the files the clean build container consumes (package lists, phase order, debloat XML/JSON) — this is what solves the empty-`/var` chicken-and-egg: the image bakes the TOML seed, the DB materializes `/ctx` at build time. Additive only — nothing reads these at runtime yet (V5 flips authority).
**Where:** `usr/share/mios/postgres/schema-init.sql`, new `usr/libexec/mios/materialize-build-ctx.py`, extend `usr/libexec/mios/seed-db-config.py` to seed `package_set`/`build_phase` from `mios.toml` + the `automation/NN-*.sh` order.
**Done When:** schema applies idempotently; seed `[packages.*]` + the `automation/` numeric order → DB → materialize `/ctx` round-trips the package sets and phase order losslessly (diff clean vs the current `packages.sh` resolution); `emb` columns present w/ HNSW; `just drift-gate` green.

## AGY-12  (WS-NAME T-165 Phase 1, P2) — fold the `userenv.sh` translation table onto your generated registry
**Who:** you (bash/Python + the AGY-4 gate). **When:** after AGY-4 (the gate exists; now do the fold it was scaffolding for).
**What + How:** your AGY-4 gate proves no NEW translations creep in; Phase 1 removes the EXISTING ones. Walk `usr/lib/mios/userenv.sh` (and any peer that re-exports a native key under a second `MIOS_*` name): for each entry that is a pure **translation** (an env var that merely renames a native/native-derived key already in `names.generated.txt`), **fold** callers onto the single generated name and delete the duplicate export — **no loss of names, no loss of function** (this is the operator's "fold similar, minimal names combined" law). For any export that is **load-bearing** (has logic, a default, or a consumer that can't take the native name yet — e.g. the `winget_*`/`flatpak_*` re-dispatch verbs, `memory_append`/`memory_replace`), leave it and add a `# WS-NAME: load-bearing, keep` note rather than blind-dropping (per the mios-flatten caution). Update `naming-unification.md` Phase-1 status with the fold count + the explicit keep-list.
**Where:** `usr/lib/mios/userenv.sh`, callers across `usr/lib/mios/**` + `usr/libexec/mios/**`, `automation/38-drift-checks.sh` (AGY-4 gate should still be green after the fold), `usr/share/doc/mios/reference/naming-unification.md`.
**Done When:** every folded name resolves to one generated key; grep shows no caller references a deleted alias; the keep-list is documented with reasons; AGY-4's names gate + `just drift-gate` stay green; `bash -n` clean.

---

## AGY-13  (WS-VECTOR V2 runtime / T-244, **P1**) — schedule + wire your AGY-10 backfill worker
**Who:** you (Python + systemd). **When:** next — AGY-10 built `embed_backfill.py` but nothing RUNS it; close the loop.
**What + How:** (1) Add a systemd **timer + oneshot service** that runs the AGY-10 backfill on a cadence (mirror `mios-skills-miner.{service,timer}` structure — `User=`/`Group=`, low privilege, `After=mios-pgvector.service mios-llm-light.service`, non-fatal). It should call the backfill entrypoint to populate `emb` on the AGY-7 columns (`verb`/`skill`/`tool_call`/`directory_entry`) idempotently. (2) Confirm `toolsearch.py`'s verb search prefers a native `verb.emb <=>` query when populated and falls back to the in-process lexicon when not (this is the retirement AGY-7/AGY-10 set up) — add the fallback branch if missing. Fail-open throughout (embeddings endpoint down → skip, never crash).
**Where:** new `usr/lib/systemd/system/mios-embed-backfill.{service,timer}`, `usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py`, `usr/lib/tmpfiles.d/` if a state dir is needed. **Gitignore-whitelist any new unit** and add it to the relevant `automation/NN-*.sh` enable list if there is one.
**Done When:** the timer unit is valid (`systemd-analyze verify` clean if runnable, else `bash -n`/structure matches the miner unit); backfill is idempotent (2nd run near-noop); `<=>` verb search returns sane neighbors with lexicon fallback intact; `test_mios_backfill` still green; `just drift-gate` passes. **Stage only your files** (see the ⚠️ note up top).

## AGY-14  (WS-VECTOR V1 / T-243, **P1**) — shadow-compare telemetry + projection drift-gate
**Who:** you (Python + the drift-gate framework). **When:** after AGY-13; builds on your AGY-9 resolver.
**What + How:** your AGY-9 `mios_db_config.py` shadow-compares DB vs TOML but the divergence goes nowhere. (1) Make the shadow-compare **count + log** divergences (structured log + an in-memory counter the health endpoint can expose), so we can measure when the DB projection is safe to make authoritative. (2) Add **drift-check 31 `drift_projection`** to `automation/38-drift-checks.sh` (next free number after AGY's 29/30): statically assert the DB→TOML materialize round-trip (from AGY-3's `materialize-config-toml.py`) is lossless for `verb`/`config_kv` — regenerate + diff, fail on drift, same pattern as the theme check 25. Read-only, no live DB (operate on the seed + materializer output).
**Where:** `usr/lib/mios/mios_db_config.py`, `automation/38-drift-checks.sh`, a `test_mios_db_config.py` case for the counter.
**Done When:** shadow-compare divergences are observable (0 on the current tree); check 31 flags an injected verb-field drop and passes clean on HEAD; `just drift-gate` green; tests green.

## AGY-15  (WS-A2 module hygiene, P2) — sibling-test + modular-boundary compliance for your new modules
**Who:** you (Python). **When:** independent; quick hygiene pass.
**What + How:** drift-check 11 requires every `agent-pipe/mios_*.py` to have a sibling `test_mios_*.py`, and check 6 requires siblings to be **server.py-free** (one-way import). Audit YOUR new/changed modules (`mios_db_config.py`, `mios_pipe/memory/embed_backfill.py`, `mios_pipe/routing/toolsearch.py`) + any peer you touched: ensure each has a sibling unit test (add minimal ones where missing) and that none imports the `server.py` monolith (refactor to a shared helper if one does). Then run the full `test_mios_*` suite and confirm all green.
**Where:** `usr/lib/mios/agent-pipe/test_mios_*.py`, the modules above.
**Done When:** checks 6 + 11 pass; the whole `test_mios_*` suite is green; `just drift-gate` passes; no new server.py import edges.

---

## AGY-16  (WS-VECTOR V1 authority-flip prep / T-243, **P1**) — DB verb-catalog read-path behind the sentinel
**Who:** you (Python). **When:** after AGY-14 (needs the shadow-compare); builds on your AGY-9 resolver.
**What + How:** wire the runtime verb/config read-path to your AGY-9 `mios_db_config.py` behind the **`[ai] db_authoritative` sentinel** (default false — you added it in AGY-9). When the sentinel is **false** (default): keep resolving the verb catalog + config from `mios.toml` exactly as today, but ALSO shadow-read the DB and record divergences (reuse AGY-14's telemetry). When **true**: resolve the verb catalog + config from the DB (`verb`/`domain_verb`/`config_kv`), TOML fail-open. Flip NOTHING by default — this just makes the DB read-path *available and measured* so a later per-surface flip is a one-line sentinel change. Kill the "write-only `system_config`/`verb` drift" by making the DB copy actually readable.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py` (or wherever the catalog loads), `usr/lib/mios/mios_db_config.py`, `usr/share/mios/mios.toml` (`[ai] db_authoritative`).
**Done When:** with sentinel false, behavior is byte-identical to today + shadow-divergence count is 0 on the seeded tree; with sentinel true (test only), the catalog resolves from the DB with TOML fallback; `test_mios_db_config` extended; `just drift-gate` green. **Stage only your files.**

## AGY-17  (WS-VECTOR V3 seeding / T-245, P2) — seed + round-trip your AGY-11 build-catalog
**Who:** you (Python + SQL). **When:** after AGY-11 (the tables exist but are empty).
**What + How:** extend `usr/libexec/mios/seed-db-config.py` to POPULATE the AGY-11 build-catalog tables from the SSOT: `package_set` from `mios.toml [packages.*]`, `build_phase` from the `automation/NN-*.sh` numeric order (ordinal = NN, stage∈{container,runtime,firstboot} by heuristic), `xbox_feature`/`debloat_policy` from the bootstrap Xbox catalog if reachable (skip gracefully if not in this repo). Then make your `materialize-build-ctx.py` (AGY-11) round-trip: seed → materialize `/ctx` → diff against the source package lists / phase order, and add **drift-check 32 `drift_build_catalog`** to `38-drift-checks.sh` asserting the round-trip is lossless. Additive only; nothing reads these at runtime yet.
**Where:** `usr/libexec/mios/seed-db-config.py`, `usr/libexec/mios/materialize-build-ctx.py`, `automation/38-drift-checks.sh`, `test_mios_build_catalog.py`.
**Done When:** seed populates the tables from `[packages.*]` + `automation/` order; round-trip diff is clean; check 32 flags an injected package-set drop and passes on HEAD; tests + `just drift-gate` green.

## AGY-18  (WS-VECTOR V2 completion / T-244, P2) — vectorize the last AI-plane tables + extend backfill
**Who:** you (SQL + Python). **When:** after AGY-13 (extends the backfill worker).
**What + How:** per `everything-db-driven.md` V2, add `emb vector(768)` + HNSW(`vector_cosine_ops`) + `emb_model`/`emb_version` to the remaining recallable tables the roadmap lists — **`event`** and **`session`** (mirror the exact DDL pattern you used for verb/skill in AGY-7/AGY-11; idempotent `ALTER … ADD COLUMN IF NOT EXISTS` + guarded index). Extend your AGY-10/AGY-13 backfill worker to also populate these over a sensible text projection (event: act_type+summary; session: title/first-prompt), same idempotent+fail-open pattern. Ground-truth stays in typed columns — additive only.
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py`, `test_mios_backfill.py`.
**Done When:** schema applies idempotently; backfill fills `event.emb`/`session.emb` with provenance; 2nd run near-noop; tests + `just drift-gate` green.

---

## AGY-19  (WS-VECTOR V1 flip-readiness / T-243, **P1**) — prove the DB read-path is flip-safe (do NOT flip yet)
**Who:** you (Python). **When:** after AGY-16 (the read-path + sentinel exist) + AGY-18.
**What + How:** make the AGY-16 DB verb-catalog read-path *provably* ready for an operator to flip `[ai] db_authoritative=true` per-surface: (1) broaden AGY-14's shadow-compare so it covers `verb` + `domain_verb` + `config_kv` + `recipe`/`routing_phrase` over a full sample, asserting **0 divergence** on the seeded tree (a real assertion in `test_mios_db_config.py`, not just a log); (2) expose the shadow-divergence counter on the agent-pipe health/status surface so it's observable at runtime; (3) write the exact **flip + rollback runbook** into `everything-db-driven.md` (which sentinel value flips which surface, how to revert, what to watch). **Leave the sentinel FALSE** — the flip is an operator action; you're delivering the confidence + the button, not pressing it.
**Where:** `usr/lib/mios/mios_db_config.py`, `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py`, health endpoint, `test_mios_db_config.py`, `usr/share/doc/mios/reference/everything-db-driven.md`.
**Done When:** shadow-divergence == 0 across all listed surfaces (asserted by tests); the counter is visible on the health surface; the runbook documents the per-surface flip + rollback; `just drift-gate` green. **Stage only your files (NOT the Quadlets).**

## AGY-20  (WS-VECTOR V3 build wiring / T-245, P2) — materialize `/ctx` from the seeded build-catalog
**Who:** you (Python + bash). **When:** after AGY-17 (seed + materializer exist).
**What + How:** wire your AGY-11/17 `materialize-build-ctx.py` into an **additive, gated build step**: an `automation/NN-*.sh` (or a hook in the existing package/build phase) that — WHEN `[ai].build_catalog_authoritative` (new, default false) is true — materializes the package sets + phase order from the seeded DB into the `/ctx` files the clean build container consumes, else no-ops. This closes the empty-`/var` chicken-and-egg (image bakes the TOML seed → DB → materialize `/ctx` at build). Keep it 100% additive + fail-open (DB unreachable → fall back to today's `packages.sh` TOML path). Do NOT flip the default.
**Where:** new `automation/NN-materialize-build-ctx.sh` (pick the right ordinal, after seed), `usr/libexec/mios/materialize-build-ctx.py`, `usr/share/mios/mios.toml` (`[ai] build_catalog_authoritative=false`).
**Done When:** with the flag false, the build is byte-identical to today; with it true (test), `/ctx` package lists + phase order match the `packages.sh`/`automation` resolution (diff clean); fail-open verified with DB down; `just drift-gate` green.

## AGY-21  (WS-NAME Phase 2 / T-165, P2) — fold the next translation tranche onto the registry
**Who:** you (bash/Python + the AGY-4/AGY-12 gates). **When:** after AGY-12 (Phase 1 folded the first tranche).
**What + How:** continue the `userenv.sh` de-translation: take the NEXT tranche of pure-translation env exports (an env var that merely renames a native/native-derived key already in `names.generated.txt`) and fold callers onto the single generated name, deleting the duplicate. Same law as AGY-12: **no loss of names/functions**, leave load-bearing exports (logic/default/legacy-verb re-dispatch) with a `# WS-NAME: load-bearing, keep` note. Regenerate `names.generated.txt`; keep drift-27 (userenv.sh == tools/lib/userenv.sh) + drift-30 (names registry) green. Update `naming-unification.md` Phase-2 status with the fold count + keep-list.
**Where:** `usr/lib/mios/userenv.sh` + `tools/lib/userenv.sh` (keep in sync!), callers across `usr/lib/mios/**`+`usr/libexec/mios/**`, `usr/share/mios/names.generated.txt`, `usr/share/doc/mios/reference/naming-unification.md`.
**Done When:** the tranche folds with no caller referencing a deleted alias; drift-27 + drift-30 + `just drift-gate` green; `bash -n` clean; keep-list documented.

---

## AGY-22  (WS-VECTOR V4 accounts / T-246, P2) — DB-owned account identity + per-user prefs
**Who:** you (SQL + Python). **When:** after AGY-17 (build-catalog patterns); independent of the flip work.
**What + How:** per `everything-db-driven.md` V4, extend `schema-init.sql` (idempotent): add `home_dir`+`shell` columns to `account` (`ALTER … ADD COLUMN IF NOT EXISTS`); add a `uid_alloc` SEQUENCE + `allocate_uid()`/`allocate_gid()` SQL functions (start above the reserved range; `CREATE … IF NOT EXISTS`/`CREATE OR REPLACE FUNCTION`); add `account_preference(account_id FK account(id), layer int, key text, value jsonb, emb vector(768), emb_model, emb_version, PRIMARY KEY(account_id,layer,key))` with the standard HNSW index. Extend `seed-db-config.py` to backfill `home_dir`/`shell` for existing accounts from sane defaults. Ground-truth in typed columns; additive only — nothing renders from `account_preference` yet (AGY-23 does).
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/libexec/mios/seed-db-config.py`, `test_mios_db_config.py` (or a new `test_mios_accounts.py`).
**Done When:** schema applies idempotently (2nd run noop); `allocate_uid()` returns monotonically-increasing ids above the reserved floor; `account_preference` accepts a row + is HNSW-indexed; seed fills home_dir/shell; tests + `just drift-gate` green. **Stage only your files (never the Quadlets).**

## AGY-23  (WS-VECTOR V4 dotfile render / T-246, P2) — render per-user dotfiles from the DB
**Who:** you (Python). **When:** after AGY-22 (needs `account_preference`).
**What + How:** write a **DB→dotfiles materializer** (`usr/libexec/mios/materialize-user-config.py`) that, per account, reads `account_preference` (3-layer precedence via `layer`) and renders the user's `~/.config/mios/*` (+ any owned dotfiles) — the DB-driven successor to static `etc/skel`. **Gated + additive + fail-open**: behind `[accounts] db_render_prefs` (new, default **false**); when false, today's static skel path is untouched; when true, render from the DB with skel as the fallback if a pref is absent. Do NOT delete `etc/skel` — leave it as the fail-open seed. Idempotent (only rewrite changed files).
**Where:** new `usr/libexec/mios/materialize-user-config.py`, `usr/share/mios/mios.toml` (`[accounts] db_render_prefs=false`), a `test_mios_user_config.py`.
**Done When:** with the flag false, first-login skel seeding is byte-identical to today; with it true (test), a user's `~/.config/mios/mios.toml` renders from `account_preference` with skel fallback; idempotent 2nd run; tests + `just drift-gate` green.

## AGY-24  (WS-VECTOR V5 event-sourcing prep / T-247, P2) — append-only config_event audit
**Who:** you (SQL + Python). **When:** after AGY-9/16 (config_kv exists + is read).
**What + How:** lay the foundation for V5 time-travel/rollback WITHOUT inverting authority: add `config_event(id bigserial PK, ts timestamptz default now(), scope, key, old_value jsonb, new_value jsonb, actor, source)` (idempotent) to `schema-init.sql`; make every write to `config_kv`/`verb`/`domain_verb` (in `seed-db-config.py` + any DB writer) ALSO append a `config_event` row (old→new), so the config history is reconstructable. Read-only replay helper `config-history.py` that prints the event log for a key. Additive; authority stays with TOML (V5 flips it later).
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/libexec/mios/seed-db-config.py`, new `usr/libexec/mios/config-history.py`, `test_mios_db_config.py`.
**Done When:** a config_kv write appends a well-formed config_event (old→new captured); `config-history.py` prints a key's event log in order; schema idempotent; tests + `just drift-gate` green.

---

## AGY-25  (AUDIT FIXES, **P0/P1**) — resolve 10 defects a Claude adversarial audit CONFIRMED in your WS-VECTOR code
**Who:** you (Python + bash + SQL). **When:** NEXT — these are real, verified bugs in code you shipped (each independently code-traced + verified). Claude already fixed 2 (redact.py unquoted-secret leak + mios_db_config.py port fail-open) — do NOT redo those. Fix these 10:
**HIGH:**
1. **`verbcatalog.py` ~148-215 — the `db_authoritative` sentinel is a NO-OP.** The T-126 "Database Overlay" block runs UNCONDITIONALLY (only try/except-guarded), so with the sentinel FALSE (default) + pgvector up, the DB silently overlays/deletes verbs (`cat.pop` on is_active=false, overwrites sig/desc/tier/permission/cmd/params) — the returned catalog is NOT byte-identical to TOML. **Fix:** gate the entire T-126 overlay behind `is_db_authoritative()` so sentinel-FALSE returns the pure TOML catalog; keep only the shadow-compare (read-only) running when false.
2. **`embed_backfill.py` ~209-248 + `toolsearch.py` ~206-231 — emb_version PING-PONG on `verb`.** Backfill stamps `emb_version='nomic-768-v1'`; toolsearch treats a verb vector valid only if `emb_version == <sha256 fp>` and re-stamps fp. The two writers perpetually invalidate each other -> every core/common verb re-embeds every 15-min timer run (never idempotent). **Fix:** unify to ONE scheme on `verb.emb_version` (make backfill compute+store the SAME fingerprint toolsearch uses, OR make toolsearch honor backfill's version) so a stamped vector satisfies both readers.
3. **`agent_call.py` ~93/436/543 — token guard permanently WEDGES a session.** `_SESSION_TOKENS[session_id]` is cumulative-only, never windowed/reset; once a session crosses `conversation_token_ceil` (2M) `used > conv_ceil` raises `ValueError` on EVERY later dispatch for the process lifetime -> the user can never get another answer until daemon restart. **Fix:** make it a rolling window + graceful summarize (mirror `chat.py`'s `_budget_admit`/`_BUDGET_LEDGER`), not a permanent hard-raise.
**MEDIUM:**
4. **`mios_db_config.py` ~13/197 — `DIVERGENCES` counts read-observations, never resets** -> the health `config_divergences` gauge climbs unbounded on any persistent mismatch read on hot paths. **Fix:** track a SET of distinct divergent `scope.key`s (or reset per rebuild) so the gauge = number of divergent settings.
5. **`verbcatalog.py` ~234 — shadow-compare feeds the ALREADY-DB-OVERLAID `cat`** into `_compare_catalogs`, masking real TOML-vs-DB drift on shared verbs AND firing a false divergence for every TOML-only verb during partial migration. **Fix:** snapshot a PRE-overlay pure-TOML copy and compare THAT vs `db_cat`.
**LOW:**
6. `verbcatalog.py` ~225 — redundant SECOND blocking `psycopg.connect(connect_timeout=2)` on the sentinel-FALSE path (~4s dead wait when DB down). Skip/cache when not db_authoritative.
7. `toolsearch.py` ~231 — stamps `emb_model='qwen2.5-coder:1.5b'` on nomic-produced verb vectors (false provenance, disagrees with backfill's `nomic-embed-text`). Stamp the actual embed model.
8. `embed_backfill.py` ~243-249 — `embedded_count += 1` runs even when the degrade-open `mios_pg.execute()` UPDATE returned None (silent DB failure over-reported as success). Check the return; count only real writes.
9. `automation/38-drift-checks.sh` check 32 (~2707-2770) — "lossless" round-trip only diffs pkgs + phase ordinal/deps/stage; add `enable`/`layer`/`base_image_ref`/`section` + `debloat_profile.description` + `preset.debloat_profile_name` to the diff.
10. `materialize-build-ctx.py` ~59 — same-ordinal `build_phase` tie-breaks by DB `id`, so an incremental re-seed sorts a new same-prefix script after older peers instead of lexically. **Fix:** `ORDER BY stage, ordinal NULLS LAST, script` (lexical), not `id`.
**Where/Done When:** fix each at the cited file:line; add/extend tests (`test_mios_db_config`/`test_mios_backfill`/`test_mios_verbcatalog`) to cover the fixed behavior; `just drift-gate` green; **stage only your files (never the Quadlets).**

---

## AGY-26  (RAG quality / research-gap #4+#5, **P1**) — hybrid BM25+vector fusion + cross-encoder rerank on knowledge/RAG
**Who:** you (Python + SQL). **When:** after AGY-18 (vectors exist). Source: `usr/share/doc/mios/reference/upstream-gaps-2026-07.md` gaps 4+5.
**What + How:** the RAG recall path (`mios_pipe/memory/pg.py` knowledge/mios_rag queries) does pure dense `<=>` search even though the schema is hybrid-capable and an **RRF helper already exists** (used only for tool selection today). (1) Add **hybrid retrieval**: run the pgvector dense query AND a Postgres FTS/`ts_rank` BM25-style query over the same rows, fuse with **Reciprocal Rank Fusion** (reuse the existing RRF helper), return the fused top-k. (2) Add an optional **cross-encoder reranking** stage over the fused candidates (a local reranker served through the light lane, or a small bge-reranker-v2-m3 / Qwen3-Reranker GGUF via mios-llm-light) — gated (`[ai] rag_rerank`, default false), fail-open to the fused order. Ground-truth stays typed; additive.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py`, the RRF helper's module, `usr/share/mios/mios.toml` (`[ai] rag_hybrid`/`rag_rerank`), `test_mios_*`.
**Done When:** hybrid recall returns fused dense+lexical results; rerank (when enabled) reorders sanely + fails open; recall quality is not worse than today with flags off; tests + `just drift-gate` green.

## AGY-27  (embedding hygiene / research-gap #6+#7, **P1**) — fix the emb_version space-collision + add EmbeddingGemma task prefixes
**Who:** you (Python + SQL). **When:** NEXT after AGY-25 — this OVERLAPS AGY-25 finding #2 (unify the emb_version scheme first). Source: gaps 6+7.
**What + How:** two real embedding-correctness bugs: (a) the served embedding model was swapped **nomic-embed-text → EmbeddingGemma-300m under the SAME served name AND same emb_version**, so two incompatible 768-d vector spaces now collide in one namespace — **bump the emb_version** (a new fingerprint that includes the actual model+revision) so old-space vectors are treated stale and re-embedded, and make backfill + toolsearch agree on that ONE fingerprint (this IS the AGY-25 #2 unification — do them together). (b) EmbeddingGemma REQUIRES task prompt templates (`task: search result | query: …` / document prefixes) — the embed call path (`server.py` embed seam + `embed_backfill.py`) sends **raw text**, degrading recall. Add the EmbeddingGemma query/document prefixes at the embed seam (gated by the active embed model so nomic-only setups are unaffected). Then trigger a one-time full re-embed via the backfill worker.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py` + `routing/toolsearch.py` (emb_version unify), the embed seam in `server.py`, `usr/share/mios/mios.toml` (embed model/version), `test_mios_backfill.py`.
**Done When:** old-space vectors are invalidated + re-embedded once (not ping-ponging — see AGY-25 #2); EmbeddingGemma requests carry the task prefixes; nomic path unchanged; recall verified sane; tests + `just drift-gate` green.

---

## AGY-28  (AGY-25 RESIDUALS, **P1**) — close the 4 residual defects a Claude verification pass found still open after AGY-25
**Who:** you (Python). **When:** NEXT. A Claude adversarial re-verify confirmed AGY-25 landed 10/10 but left these tails:
1. **`agent_call.py` — D3 still HARD-RAISES.** The rolling-window is in (good, permanent-wedge gone) but once the 1h-windowed total exceeds `conversation_token_ceil` it still raises `ValueError` (500-style) instead of the **graceful summarize** the defect asked for. **Fix:** mirror `chat.py`'s `_budget_admit` degrade — summarize/trim + admit, never a hard raise on a live session.
2. **`mios_db_config.py` + `verbcatalog.py:~246` — D4 not airtight.** `get_divergences()` sums the deduped `_DIVERGENT_KEYS` set PLUS the raw int `DIVERGENCES`, and `verbcatalog.py` still does `mios_db_config.DIVERGENCES += 1` per divergent reload. **Fix:** route the verbcatalog contributor into the SAME `_DIVERGENT_KEYS` set (scope.key granularity) and drop the raw-int path so the gauge = distinct divergent settings.
3. **`embed_backfill.py` — D2 co-residency assumption.** `_verb_embed_fingerprint()` reads toolsearch's module-global `_VERB_CATALOG`; if the 15-min worker runs in a process where `configure()` never populated it, the fp is computed over an empty catalog → churn returns. **Fix:** guard/assert the catalog is populated before fingerprinting (skip the run + log if empty), or compute the fp from the same SSOT source both processes read.
4. **`verbcatalog.py` — D6 first-load blocking connect.** On the sentinel-FALSE path the FIRST load still does one blocking `psycopg.connect(connect_timeout=2)` before `_DB_UNREACHABLE` caches. **Fix:** short-circuit the very first probe too (cache the unreachable state across the initial call, or make the probe non-blocking/background).
**Done When:** each fixed at cited file:line; tests extended; `just drift-gate` green; stage only your files.

## AGY-29  (WS-VECTOR V4 hardening / T-246, **P2**) — fix the two AGY-22/23 residuals a Claude verify pass flagged
**Who:** you (Python). **When:** after AGY-28.
1. **`materialize-user-config.py:~176` home-escape.** The path guard uses `startswith('/home/bob')`, so a seeded `file:`-pref like `../bob-evil/.bashrc` resolves to `/home/bob-evil/.bashrc` and PASSES. **Fix:** `os.path.commonpath([home, resolved]) == home` (or trailing-separator compare). Active only when `db_render_prefs=true` (default false) but fix before that flag is ever flipped.
2. **`materialize-user-config.py:~37` lossy `parse_simple_toml`.** Rendering `~/.config/mios/mios.toml` via parse→reserialize drops comments and cannot represent inline tables / arrays-of-tables / multiline arrays. **Fix:** read with `tomllib` (never the naive parser) and, if you must re-emit, use a real TOML writer or a preserve-comments strategy; otherwise render only the typed pref slots, not the whole file.
**Done When:** guard uses commonpath; user-config render is lossless or slot-scoped; tests cover both; `just drift-gate` green.

## AGY-30  (VALUE/VERB MINIFICATION / WS-NAME sibling, **P1**) — canonicalize value + verb representation across the SSOT + verb tables
**Who:** you (Python + SQL + TOML). **When:** parallel-safe. Operator campaign: MINIFY + canonicalize verbs, keys, AND values to ONE form — collapse `True`/`1`/`"yes"` → canonical lowercase `true`/`false`, dedupe redundant verb aliases, fold key-case variants. **SCOPE (avoid collision):** the **verbs tables** (`[verbs.*]` in mios.toml + the `verb`/`domain_verb` DB rows + `verbcatalog.py` normalization) and **non-quadlet config values**. **DO NOT touch** `tools/lib/userenv.sh` / `usr/lib/mios/userenv.sh` or `tools/generate-pod-quadlets.py` / the generated `*.container` (Claude owns the key-library + quadlet value-render collapse). **How:** add a canonicalizer in the verb-catalog load path that normalizes bool/int/enum arg-values + de-dupes aliases deterministically; sweep `[verbs.*]` for `True`/`1`/mixed-case bools and fold them; add a drift-check that asserts no non-canonical bool literal re-appears. Coordinate the shared-name registry via the existing names-registry generator.
**Done When:** verbs + config values are single-canonical-form; a new drift-check guards it; behavior byte-identical at the consumer (parsers already `.lower()`); tests + `just drift-gate` green; stage only your files (NOT userenv.sh/quadlets).

## AGY-31  (USR-OVER-ETC reconciliation, **P2**) — audit + reconcile the duplicate `etc/containers/systemd/*.container` copies
**Who:** you (bash + audit). **When:** after Claude's #12 digest root-fix lands (DONE, commit 852b605). A Claude verify pass flagged that `etc/containers/systemd/*.container` duplicate copies exist alongside the generated `usr/share/...` units; if the `etc/` copies carry **stale digests** they defeat the digest-determinism fix at DEPLOY time (systemd prefers `/etc`). **How:** enumerate every `etc/containers/systemd/*.container`, diff against its `usr/share/...` generated twin; per LAW USR-OVER-ETC, `/etc` is admin-override only — either (a) delete the redundant `etc/` copy if it's just a stale mirror, or (b) if it's a deliberate override, reduce it to a `.d/` drop-in carrying ONLY the overridden keys (never a full duplicate with a pinned Image). Add a drift-check that fails if an `etc/` full-unit duplicate reappears.
**Done When:** no full-unit `etc/` duplicate shadows a generated unit with a divergent/stale Image; overrides are drop-ins; drift-check added; `just drift-gate` green.

## AGY-32  (audit-redaction test coverage, **P2**) — prove the config_event secret-redaction holds
**Who:** you (SQL + Python test). **When:** after AGY-28. Claude added `mios_redact_config_value()` + wrapped `log_config_kv_change()` (commit 3abc92f) so seeded secrets (`identity.default_password`, `[security].*`, `[agent_passport].*`) are masked to `[REDACTED_SECRET]` in `config_event`. **How:** add a test (extend `test_mios_pg` or a new `test_mios_config_audit`) that: seeds a config_kv row with a secret-bearing key, asserts the resulting `config_event` row's `new_value` = `"[REDACTED_SECRET]"`, and a non-secret key passes through verbatim. ALSO audit the `verb`/`domain_verb` audit triggers (`log_verb_change`/`log_domain_verb_change`, `to_jsonb(NEW)`) — if any verb field can carry a credential (e.g. a cmd with an inline token), apply the same redaction; otherwise document why they're secret-free.
**Done When:** redaction test green (secret masked, non-secret passes); verb-trigger secret-safety confirmed or fixed; `just drift-gate` green.

---

### Reporting back
Commit each task as `agy: <task-id> <summary>` and push to `main`. Claude is monitoring
`main` for your commits + will integrate/verify. If blocked, leave a `TODO(agy):` note in
the file and move to the next task. Full context for every item is in `TASKS.md`
(T-166, T-178, T-242, T-165) and the `usr/share/doc/mios/reference/*.md` workstream docs.
