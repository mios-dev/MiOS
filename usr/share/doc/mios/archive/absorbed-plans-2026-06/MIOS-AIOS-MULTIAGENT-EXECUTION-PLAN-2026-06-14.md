<!-- AI-hint: Multi-agent, multi-wave execution plan to close the AIOS/MiOS capability gaps found by the 11-agent code-grounded audit (2026-06-14). Each wave is a workflow fan-out; tasks carry file-ownership for conflict-free parallelism. Supersedes the gap sections of AIOS-MIOS-MASTER-PLAN-2026-06-14.md with verified findings. -->

# MiOS → Full AIOS: Multi-Agent Execution Plan (2026-06-14)

**Provenance.** Built from an 11-agent, code-grounded audit of `C:\MiOS` (10 capability dimensions + a completeness critic). Raw structured findings: `…/tasks/w8frlwcdi.output` (1.2M-token run; keep as the backing appendix). This plan **supersedes the gap analysis** in `AIOS-MIOS-MASTER-PLAN-2026-06-14.md` and `AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md` with verified, file:line evidence.

## Executive reality-check (what the audit overturned)

MiOS is **~70–80% built** — far more than prior notes assumed. The audit confirmed, in source, that MiOS already has: an enabled DAG planner (gemma4, not VRAM-gated), a userspace **PriorityGate + admission controller + circuit breakers + swarm width/deadline caps + autonomous de-escalation + inline satisfaction-halt**; **full A2A** (publish *and* consume: discover, fetch cards, dispatch by peer/skill, `delegate`, `handoff`, tailnet autodiscovery, AGNTCY manifest); **MCP serve *and* consume** (both agent-pipe and Hermes are MCP clients) with a taint firewall, `tool_search` progressive disclosure, and resources; **ed25519 agent passports** + HITL gate + permission-typed verbs + semantic firewall + a seccomp+Landlock coderun sandbox; **pgvector-primary** memory (the legacy datastore migration effectively done) with knowledge store/recall, outcome-ranked tiers, eviction, RAG, scratchpad/blackboard, agent self-edit memory, episodic SKILL.md; client-side **RadixAttention** exploitation (`stable_tool_prefix`), tool rerank, KV paging/fork, Code Mode; and a **DCI critic/judge**, eval harness, run-template **replay** engine, skill lifecycle, and a finetune/LoRA subsystem.

**So this is not a build-from-scratch effort. The gaps cluster into five recurring themes:**

1. **"Declared but not rendered" (SSOT-render disconnect)** — ~6 `mios.toml` keys (SGLang HiCache, `tool_parser`, `kv_cache_dtype`, DCI_*, SCRATCHPAD_*/RAG_*/AGENT_MEMORY_*) never reach the running process because a `userenv.sh` mapping or a `15-render-quadlets.sh` allowlist entry is missing. **No conformance test exists → whack-a-mole.**
2. **"Capable but inert by default"** — HiCache, HITL (`mode=log`), agent-memory recall (`=0`), KV demand-paging (pointed at the dead `:11436` lane), priority→SGLang (computed then dropped at the pipe queue), coderun sandbox (image never built). The **safety** halves were the inert halves while the **capability** halves were live — which is exactly how the GPU runaway slipped through.
3. **"Identity recorded, never enforced"** — `_passport_verify` has one caller (a debug endpoint); inbound A2A/MCP run the full pipeline with no auth gate. Federation is unsafe to expand.
4. **No global GPU-pressure / aggregate-budget signal** — five dimensions guard the shared 4090 with their own local heuristic; they don't compose. The daemon→swarm runaway had no cumulative token/turn tripwire and no host-pressure circuit breaker.
5. **Mutable AI state is unprotected** — pgvector (the entire "brain": knowledge, memory, passports, audit) has no backup, binds `0.0.0.0` on default creds `mios/mios`, no PII redaction, and is not bootc-rollback-versioned — while the OS half is immutable. Inverse-asymmetry risk.

Greenfield (genuinely new): replay **reliability gate** (G3), **closed self-improvement** (G5), **weighted consensus** (K4), **JSD drift**, **distributed tracing/observability**, **schema-versioned rollback**.

---

## Guiding constraints (binding on every task)

- **Architectural Laws:** USR-OVER-ETC · NO-MKDIR-IN-VAR (tmpfiles.d) · BOUND-IMAGES · BOOTC-LINT · UNIFIED-AI-REDIRECTS (everything → `MIOS_AI_ENDPOINT`, no vendor URLs) · UNPRIVILEGED-QUADLETS.
- **mios.toml SSOT** — every new knob flows `mios.toml → userenv.sh → 15-render-quadlets.sh allowlist → ${MIOS_*:-default}`, mirrored in the configurator HTML. **No hardcoded literals.**
- **Degrade-open / default-off-until-verified** — new safety gates ship in a safe mode (log/off) with a documented enable path; new features default off.
- **Operator rules:** Claude **edits source**; the operator **git-pushes from the Windows-side repos** (`C:\MiOS`, `C:\mios-bootstrap`). **No live app launches.** Don't vendor the research-flagged fabrications (ProbeLogits, Cerebrum, enterprise/MCPS passports).
- **Quadlet caveat:** `Exec=` cannot express conditional flags; a render-time **`MIOS_SGLANG_EXTRA_ARGS`** helper must precede all SGLang flag work (else bare `${VAR:-}` injects empty tokens that crash `launch_server`).

## Multi-agent orchestration model (how to task agents conflict-free)

Most tasks touch a small set of **hot shared files** (`server.py`, `mios.toml`, `tools/lib/userenv.sh`, `automation/15-render-quadlets.sh`). Naive parallel edits collide. The model:

- **File-ownership partition.** Each wave's tasks are grouped so that within a parallel batch, **agents own disjoint files**. The hot shared files get a **single owning agent per wave** that batches all of that wave's edits to them (e.g., one "SSOT-chain owner" applies all `mios.toml`+`userenv.sh`+`15-render` deltas for the wave).
- **Worktree isolation** (`isolation: "worktree"`) for any agents that must edit overlapping trees, then a **serial integration agent** merges.
- **Per-wave verify stage** (barrier): run the new SSOT-conformance lint + `py_compile server.py` + the `test_mios_*.py` sibling suites + `bootc container lint` (where applicable) before the wave is "done."
- **Pipeline shape:** `implement (parallel, disjoint files) → integrate (serial, hot files) → verify (barrier)`. Each wave is one `Workflow` run; the operator reviews the diff and pushes.

---

## WAVE 0 — Foundation & safety (no new infra; fixes the live incident; unblocks all waves)

*Rationale (critic sequencing): land the SSOT lint FIRST; in parallel ship the cheap operational guards that need no new infra. These are the runaway / durability / exposure quick-wins + the install self-assembly fixes + capturing this session's live fixes into source.*

| ID | Task | Files (owner) | Sev/Effort | Acceptance |
|----|------|---------------|-----------|------------|
| **W0-T1** | **SSOT-render conformance lint** (the meta-fix). A build step + test asserting every `MIOS_*` in any Quadlet `Exec=` has a `userenv.sh` export AND a `15-render-quadlets.sh` allowlist entry, and documented flags appear in the rendered unit. | `automation/NN-ssot-lint.sh` (new), `tools/lib/userenv.sh`, `automation/15-render-quadlets.sh`, a `test_*.py` | P0/S | Lint fails the build on any orphaned key; retroactively flags the 6 known dead keys. |
| **W0-T2** | **Daemon runaway controls.** `_host_pressure_gate()` (cached loadavg + nvidia-smi, ~5s TTL) guarding classify/refusal/cron/suggestions loops; per-`(source,kind,summary-hash)` **dedup+cooldown**; **cron concurrency cap** (track Popen); **quiescence/auto-halt** feeding cadence backoff. | `usr/libexec/mios/mios-daemon` (owner), `mios.toml [daemon]`, configurator | P0/M | Repeated identical high-sev classifications suppressed; loops skip a tick under host pressure; cron actions can't stack. |
| **W0-T3** | **Aggregate token/turn budget** — cumulative ceiling debited per-conversation and per-autonomous-source, hard-halt on exhaustion; `mios_autonomous` gets its own low budget + lowest dispatch priority. | `usr/lib/mios/agent-pipe/server.py` (owner), `mios.toml [dispatch]/[budget]` | P0/M | A background loop self-limits; foreground turn preempts background for the next GPU slot. |
| **W0-T4** | **pgvector durability + exposure.** Nightly `pg_dump` timer → `/var/lib/mios/backups` (tmpfiles); bind `5432`→`127.0.0.1`; require non-default password off-loopback; **embed-on-write in `mios-ingest`** (currently leaves `emb` NULL → ingested docs never recalled). | `usr/lib/systemd/system/mios-pgvector-backup.{service,timer}` (new), `usr/libexec/mios/mios-ingest`, pgvector quadlet, tmpfiles, `mios.toml [pgvector]` | P0/M | Backup runs; DB not network-reachable on defaults; ingested rows are vector-recallable. |
| **W0-T5** | **Install self-assembly fixes.** BOM-aware `mios-ai-tag` (relocate U+FEFF to byte 0) + re-encode `Get-MiOS.ps1`; `restart --no-block` in `mios-hermes-firstboot` (420,1256) + `mios-ai-firstboot` (157-159); hermes firstboot **off the retired ollama stack** (probe `:11450/v1/models`, pull model names from SSOT, not hardcoded `qwen3*`); venv-recovery path typo (`hermes-agent/.venv`→`agents/.venv`, line 404); `generate_env` completeness + drifted defaults; llamacpp bake `curl`-not-`pip`. | `usr/libexec/mios/mios-ai-tag`, `Get-MiOS.ps1`, `…/mios-hermes-firstboot`, `…/mios-ai-firstboot`, `…/system-sync-env.sh`, `automation/38-llamacpp-prep.sh` (disjoint owners) | P0/M | `irm\|iex` parses on a clean install; no firstboot deadlock; hermes seeds against the live fleet; no per-boot venv re-install. |
| **W0-T6** | **Capture this session's live fixes into source.** SGLang `Environment=SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1`, reconcile `max_model_len` 131072→**65536** (live-validated) pending HiCache+fp8, `mem-fraction` SSOT; hermes `model.max_tokens=16384` + the `local-sglang` provider in vendor `config.yaml`. | `usr/share/containers/systemd/mios-llm-heavy.container`, `mios.toml [ai.sglang]`, `usr/share/mios/hermes/config.yaml` | P0/S | A fresh build reproduces the working fast-chat config with no manual recovery. |

**Wave-0 verify:** SSOT lint green · `py_compile` · `test_mios_daemon`/`test_mios_hitl` green · a dry `mios build` reaches `bootc container lint`.

---

## WAVE 1 — Enable the inert + relieve the GPU (engine-side, gated)

*Sequence the engine-GPU work as ONE unit behind the `MIOS_SGLANG_EXTRA_ARGS` helper. Flip the already-built-but-off safety/features.*

| ID | Task | Files (owner) | Sev/Effort | Acceptance |
|----|------|---------------|-----------|------------|
| **W1-T1** | **SGLang agentic-serving flags** via the render-time `MIOS_SGLANG_EXTRA_ARGS` helper: `--enable-hierarchical-cache` (+`--hicache-ratio`, +`--kv-cache-dtype fp8_e5m2`), `--enable-priority-scheduling`, `--radix-eviction-policy priority`, `--enable-streaming-session`, `--enable-metrics`, optional `--speculative-algorithm NGRAM`. Reconcile `max_model_len` (131072 only WITH HiCache+fp8). `tool_parser`/`reasoning_parser` SSOT. | `tools/lib/userenv.sh` + `automation/15-render-quadlets.sh` + `mios.toml [ai.sglang]` + `mios-llm-heavy.container` (single SSOT-chain owner) | P0–P1/M | Flags appear in the rendered unit; lane boots; `:11441/metrics` exposes prefix/HiCache hit-rate. |
| **W1-T2** | **Forward priority + isolate sub-agents at the engine.** Inject `nvext.agent_hints.priority` (from existing `_sched_priority`/`_dispatch_priority`) on SGLang-lane POSTs only; open a **streaming session per sub-agent** so swarm children get isolated KV and can't evict the parent prefix; `mios_autonomous`→lowest priority; add `max_dispatch_depth` recursion bound. | `server.py` (owner), `mios.toml [dispatch]` | P1/M | Foreground turn preempts background on the shared lane; sub-agent KV no longer evicts parent. |
| **W1-T3** | **Memory/RAG activation.** RAG corpus = `/usr/share/mios/docs` **+ repo-root MDs (MiOS.md/AGENTS.md/CLAUDE.md/AIOS-*.md) + the memory dir** (operator-required); re-ingest `.path` trigger; flip `MIOS_AGENT_MEMORY_RECALL` **on**; persist scratchpad to the existing `scratch` table. | `usr/libexec/mios/mios-rag`, `server.py` (scratchpad), `mios.toml [rag]/[agent_memory]/[scratchpad]`, new `mios-rag-ingest.{service,path}` | P0–P1/S–M | Agent grounds in its own identity/plans; durable facts are recalled; scratchpad survives restart. |
| **W1-T4** | **Hermes prefill diet (the 35.7K → ~25K cut).** Make `mios-mcp-server` `tools/list` request a **tier-scoped** feed (`include_rare=false`, `&tiers=core,common`); stop double-counting skills; expose `tool_search` as an MCP tool; per-consumer profiles (`[mcp_serve.profiles]`). | `usr/libexec/mios/mios-mcp-server`, `server.py` (`list_tools`), `mcp-server-runner`, `mios.toml [mcp_serve]`, hermes `config.yaml` | P0/M | Hermes prefill drops ~25–35%; rare tools reachable via `tool_search`/resources. |
| **W1-T5** | **SSOT-ify orphaned env knobs** ([dci],[scratchpad],[rag],[agent_memory],[mcp_serve]); route via `_toml_section` + userenv; configurator cards. | `mios.toml`, `tools/lib/userenv.sh`, `server.py` (env-read sites), configurator | P2/S | SSOT lint green for these sections; configurator exposes them. |

**Wave-1 verify:** SGLang boots with flags + metrics; measure prefill before/after; foreground-preempts-background confirmed via metrics/trace.

---

## WAVE 2 — Identity enforcement + observability (MUST precede any federation)

| ID | Task | Files (owner) | Sev/Effort | Acceptance |
|----|------|---------------|-----------|------------|
| **W2-T1** | **Passport trust gate.** Wire `_passport_verify` into inbound A2A (`/a2a`,`/a2a/jsonrpc`) + MCP-consume dispatch (modes off\|log\|enforce); sign outbound A2A envelopes (reuse `_passport_sign`); advertise `securitySchemes`; **per-peer tool scoping** (default read-only); auto-taint external sessions; add envelope TTL + replay-nonce cache. | `server.py` (owner), `usr/libexec/mios/mios-passport` (peer pubkey import), `mios.toml [passport]/[a2a]` | P0/L | Unverified peer rejected in enforce mode; external peer gets read-only surface + auto-taint. |
| **W2-T2** | **HITL log→gate** for a narrow always-block high-privilege set (`powershell_run`, `winget_install`, `service_restart`, reboot/shutdown) regardless of mode; smoke-test the approve path; surface pending in portal. | `mios_hitl.py`, `server.py` (`_hitl_gate`), `mios.toml [hitl]` | P1/S | Destructive verbs block pending approval; `/v1/hitl/approve` retry-passes. |
| **W2-T3** | **Distributed tracing + metrics.** Thread a `trace_id`/correlation-id `pipe→prefilter→hermes→lane`; per-hop latency + queue-depth events; scrape SGLang `/metrics`; portal panel. (Diagnostic substrate to *prove* the runaway fixes + priority forwarding work.) | `server.py` (owner), `mios-delegation-prefilter`, portal, read-only metrics collector | P1/M | A turn is reconstructable end-to-end; runaway pattern is now observable. |
| **W2-T4** | **Ingress + offline + redaction.** Per-client rate-limit/backpressure/queue-shed on `:8640/:8642`; web_search→local-RAG **circuit breaker** when egress/SearXNG down; **secret/PII redaction** before pgvector write, scratchpad broadcast, and A2A echo. | `server.py` (owner), `mios.toml [ingress]/[security]` | P1/M | External flood is shed; egress-down degrades to grounded-local with a stated caveat; secrets scrubbed on persist/federate. |

---

## WAVE 3 — Reliability foundation (G3) + rollback safety (greenfield, gated)

*Build the scorer ONCE; consume it in three places (reliability gate, drift, eval-CI). G3 precedes G5/K4.*

| ID | Task | Files (owner) | Sev/Effort | Acceptance |
|----|------|---------------|-----------|------------|
| **W3-T1** | **Replay reliability gate.** `mios_reliability.py` (pass@k/pass^k/TH@50/AUC, flip-centered regression) + `mios-eval-run` shared scorer + `reliability_case`/`reliability_run` tables + **frozen held-out suites** (knowledge + routing) + replay via existing `execute_skill`/`_execute_dag_bounded` (`replay_dangerous=false`) + `mios-eval.timer` as a build/CI gate. | `mios_reliability.py`+test (new), `usr/libexec/mios/mios-eval-run`+`mios-reliability` (new), `schema-init.sql`, `var/lib/mios/evals/routing.*` (new), `mios.toml [reliability]`, timers, tmpfiles | P1/L | Held-out score gates promotion; regression flips fail the gate; timer writes baseline rows. |
| **W3-T2** | **Weighted judge consensus** (`mios_consensus.py`: weighted_vote + RRF) over 2–3 lanes, weights optionally from `reliability_run`; degrade-open to single-judge. | `mios_consensus.py`+test (new), `server.py` (judge/synthesis), `mios.toml [consensus]` | P2/M | Multi-judge DoD with quorum; fast CPU path stays single-judge. |
| **W3-T3** | **JSD drift monitor** (`mios_drift.py`) over intent/score/verdict distributions vs a frozen baseline; `drift_snapshot` table; `/v1/drift` + alert event. | `mios_drift.py`+test (new), `schema-init.sql`, `mios.toml [drift]` | P2/M | JSD>threshold emits a drift_alert. |
| **W3-T4** | **Rollback safety + supply-chain.** `schema_version` table + forward/back migration framework + snapshot-DB-before-`bootc upgrade` hook; sha256/sigstore pins on bake/firstboot model-weight fetch. | `schema-init.sql`, `usr/libexec/mios/` migration runner (new), `38-*-prep.sh`, `mios-ai-firstboot` | P1/M | bootc rollback can't desync code/DB; truncated/poisoned weights caught at provision. |

---

## WAVE 4 — Self-improvement, federation, advanced (heavy / dependent)

| ID | Task | Files (owner) | Sev/Effort | Acceptance |
|----|------|---------------|-----------|------------|
| **W4-T1** | **Closed self-improvement (G5)** on the G3 gate (baseline→propose→validate-held-out→promote-on-win, frozen suite); **DPO trainer** consuming `dpo.jsonl` + critic-refine before/after pairs. | `usr/libexec/mios/mios-self-improve` (new), `mios-finetune` (DPO branch), `schema-init.sql`, `mios.toml [self_improve]/[finetune]` | P1/L | A proposal promotes only after a held-out win; DPO consumes live preference signal. |
| **W4-T2** | **Activate A2A federation** (now safe post-W2-T1): auto-synthesize loopback self-peer, mtime-reload `a2a-peers.json`, periodic re-probe loop, scored skill dispatch (NEGOTIATE), AGNTCY directory register/search on pgvector. | `server.py` (owner), `mios-a2a-discover`, `mios.toml [a2a]/[agntcy]` | P2/M–L | Peers join without restart; dead peers drop; multi-peer skill routing scores. |
| **W4-T3** | **Per-action sandboxing + SE loop + memory-relay.** Bake the coderun sandbox image (BOUND-IMAGES) + route untrusted-origin high-risk verbs through it; plan-critic + Planner/Coder/Reviewer/Test loop; memory-relay middleware (per-agent buffers + promote-to-durable); context compression on the cold prefix. | `automation/NN-coderun-sandbox.sh` (new), bound-images, `server.py`, `mios.toml` | P1–P2/L–XL | Untrusted actions sandboxed; long turns compress instead of truncate. |
| **W4-T4** | **SSOT completion.** Migrate the 12 remaining hardcoded dispatch verbs → `[verbs.*].cmd` templates; create/retire `38-sglang-prep.sh`; fix `mios-hermes-firstboot` skills chown 820→850. | `mios.toml [verbs.*]`, `server.py` (`_build_dispatch_cmd`), OWUI pipe, `automation/`, `mios-hermes-firstboot` | P2/M | No hardcoded verb literals; no dangling bake-script reference. |

---

## Cross-cutting risk register (from the critic)

1. **SSOT-render disconnect is systemic** → W0-T1 lint MUST land before any wave adds toml sections, else every new key risks silent death.
2. **"Capable but inert"** → the safety halves were off; Waves 0–2 flip them on (gated).
3. **Shared 4090 has no global pressure signal** → W0-T2 (host-pressure gate) + W1-T1 (HiCache/eviction) + W1-T2 (engine priority) must compose into one signal the daemon, admission controller, swarm width, and SGLang all read.
4. **Identity recorded, never enforced** → W2-T1 must precede any non-loopback exposure (W4-T2).
5. **Autonomous work not first-class isolated** → isolate at queue (W0-T3) + engine (W1-T2) + budget (W0-T3) + admission simultaneously.
6. **Mutable brain unprotected** → W0-T4 (backup/bind/redact) + W3-T4 (schema version/rollback).

## Sequencing summary

```
Wave 0 (foundation+safety, no new infra) ── must complete first; W0-T1 lint gates the rest
   │
Wave 1 (enable inert + GPU relief) ──┐ engine work as one unit behind EXTRA_ARGS helper
   │                                 │
Wave 2 (identity + observability) ───┘ W2-T1 gates Wave-4 federation; W2-T3 validates W1
   │
Wave 3 (reliability gate G3 + rollback) ── G3 scorer gates Wave-4 self-improve/consensus
   │
Wave 4 (self-improve G5, federation, sandboxing, SSOT cleanup)
```

## Execution note (how this plan tasks the agents)

Each wave is run as one `Workflow`: `parallel implementers (disjoint file owners, worktree-isolated) → serial integrator (hot shared files: server.py / mios.toml / userenv.sh / 15-render) → barrier verify (SSOT lint + py_compile + test_mios_* + bootc lint)`. The operator reviews each wave's diff and pushes from the Windows-side repo. Claude makes the source edits; Claude does not push and does not launch apps.
