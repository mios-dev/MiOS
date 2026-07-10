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
> **Queue status (updated by Claude):** AGY-1 **[DONE]** · AGY-2 **[DONE]** · AGY-3 **[DONE]** · AGY-4 *[in progress]* · **AGY-5 … AGY-8 are NEW below — start them next.** Claude verified AGY-1/2/3 (parse-clean, on-spec, DAG edges correct, DB foundation valid) and is pushing them + this expansion.

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

### Reporting back
Commit each task as `agy: <task-id> <summary>` and push to `main`. Claude is monitoring
`main` for your commits + will integrate/verify. If blocked, leave a `TODO(agy):` note in
the file and move to the next task. Full context for every item is in `TASKS.md`
(T-166, T-178, T-242, T-165) and the `usr/share/doc/mios/reference/*.md` workstream docs.
