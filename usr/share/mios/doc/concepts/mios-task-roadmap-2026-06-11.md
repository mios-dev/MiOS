<!-- AI-hint: Historical (post-P0–P4) MiOS roadmap recording the completion of a 7-task hardening pass over the agent-pipe orchestrator — MCP tool-ranking fixes, the P6 untrusted-web taint→mask firewall, P3 tool tiering, DuckDB/Postgres MCP enablement, hardware-aware swarm concurrency, and WSL always-on for reproducible measurement. Kept as a record of WHY each change serves the whole MiOS agentic-OS pipeline.
     AI-related: mios-wsl-keepalive, mios-mcp-enable-tier0, mios-ai, mios-wsl-session-task, mios-agent-pipe, mios-agent-pipe.service, mios-llm-light, mios-llm-heavy, mios-pgvector -->
# MiOS Task Roadmap — 2026-06-11 (post P0–P4)

> **Status: HISTORICAL / COMPLETE.** This is the record of a single hardening
> pass (2026-06-11) over the MiOS agent pipeline. All 8 tasks below are done (see
> EXECUTION STATUS). It is retained for rationale and sequencing history, not as
> open work. Names current as of 2026-06-13 (inference lanes are
> `mios-llm-light`/`mios-llm-heavy`/`mios-llm-heavy-alt`; the agent datastore is
> PostgreSQL + pgvector).

## Where this fits in MiOS

MiOS is one image built two ways at once: an immutable bootc/OCI Fedora
workstation *and* a local, self-replicating agentic AI OS. The AI half is a
single OpenAI-compatible pipeline — a front-end (OWUI :3030, the Discord
gateway, the `mios` CLI) feeds **agent-pipe** (`:8640`), which refines a request,
fans it out across a council/swarm, and dispatches tool/verb calls; **MiOS-Hermes**
(`:8642`) is the tool-loop gateway; **pgvector** (`mios-pgvector`, `:5432`) is the
unified memory (sessions, tool_call, knowledge, skills, RAG embeddings); and the
**inference lanes** (`mios-llm-light` `:11450` primary, `mios-llm-heavy` SGLang
`:11441`, `mios-llm-heavy-alt` vLLM `:11440`) do the generation and embeddings.

This roadmap is the hardening pass that made that pipeline **safe and
measurable** before scaling the tool/server surface: it closed the untrusted-web
security gap (P6 taint→mask), fixed MCP tool retrieval (double-prefix + TDWA +
tiering), enabled the SQL MCP servers against pgvector, made swarm concurrency
fit the single shared GPU, and stopped the WSL session-detach cycle that made
every latency/VRAM/eval number non-reproducible. Each task is justified by how it
serves that whole.

## EXECUTION STATUS (goal: complete all tasks) — 2026-06-11
- ✅ **#1 always-on** — DONE: `mios-wsl-keepalive.ps1` registered + running (`MiOS-WSL-KeepAlive` task, `sleep infinity` holder); service cycling stopped (1 restart/3min, was ~6). Persists across logon.
- ✅ **#2 MCP double-prefix** — DONE+verified: `_mcp_embed_new_tools` de-dups the namespace; playwright now surfaces for web queries that returned nothing before.
- ✅ **#3 P6 taint→mask** — DONE+verified: `mcp.*` branch in `_classify_verb_taint`; `_record_mcp_tool_call` persists MCP taint; `_exec_tool_calls` firewall-prechecks high-priv verbs when the session is tainted (reads session from `_orch_ctx_var`).
- ✅ **#4 TDWA for MCP** — DONE: per-server `examples` field folded into the MCP embed text (playwright examples shipped).
- ✅ **#5 P3 tiering** — DONE+verified: `tool_search` gained `namespace`/`tier` filters + `detail_level` (full|brief|names), `full` default = back-compat.
- ✅ **#8 P5 code-mode heavy** — DONE: `[code_mode] heavy_lane_only` (default true) gates `code_mode` to the heavy orchestrator (refused on light workers via `_orch_ctx_var`).
- ✅ **#6 DuckDB+Postgres** — DONE (operator authorized 2026-06-11 "finish! I authorize you"): `usr/libexec/mios/mios-mcp-enable-tier0.sh` installs both servers into the mios-ai venv (DuckDB needs `--db-path :memory: --read-write`; postgres-mcp's `pglast` needs `python3-devel` for py3.14; Postgres connects to the unified **pgvector** datastore via the EXISTING `mios` pg role in `--access-mode restricted`), enables them in the overlay, restarts, verifies. LIVE: **duckdb (4) + playwright (23) + postgres (9) = 36 MCP tools**, semantically reachable (tool_search routes "sql query"→postgres/duckdb, namespaces scope cleanly).
- ✅ **#7 node-consolidation** — DONE (swarm-safety): `lane_concurrency_gpu` reverted 4→**2** (the known-safe ceiling) so a broad `dispatch_to_nodes` swarm QUEUES instead of OOM-cycling the SGLang heavy lane (`mios-llm-heavy`, :11441); no VRAM change, no engine retopo. (Full per-engine spreading — routing agents off the gpu lane — remains an optional later refinement needing the operator's model-placement decisions.)

---

Prioritized from a 7-task research workflow (each plan code-grounded against
`usr/lib/mios/agent-pipe/server.py`, verified at cited anchors). Ranking principle:
do the cheap, high-leverage, **security- and measurement-foundational** work first.
The anchors below reflect the pre-fix line numbers as captured during the pass.

## NOW — assistant-doable quick wins

1. **WSL always-on (stop the ~30s service cycling)** — *S, high.* FOUNDATIONAL: WSL
   tears down the distro's systemd services on session detach every ~30s, which
   re-probes MCP, swaps the resident model in/out of the shared GPU's VRAM, and
   **destroys the P0 RadixAttention prefix** on the heavy lane — and makes every
   latency/VRAM/eval measurement non-reproducible. Fix = a Windows KeepAlive
   scheduled task running `wsl … --exec /usr/bin/sleep infinity`
   (mirrors the existing `mios-wsl-session-task.ps1`; assistant writes the script,
   operator runs it once + optional one-time `wsl --shutdown` to load
   `.wslconfig vmIdleTimeout=-1`).

2. **mcp-ranking: double-prefix bug** — *S, high.* **VERIFIED at server.py:16890**:
   `f"{namespace}{tool}"` with namespace `browser_` + tool `browser_navigate` embeds
   `browser_browser_navigate`, corrupting the embedding text for all 23 Playwright
   tools → they surface only on browser-explicit intents. One-line, degrade-open fix
   (`tool[len(ns):] if tool.startswith(ns) else tool`). Highest value/effort ratio.
   (Embeddings come from `nomic-embed-text` on the primary `mios-llm-light` lane.)

3. **P6 taint→mask wiring** — *M, high, SECURITY-CRITICAL.* Hard precondition for any
   untrusted-web MCP use: Playwright is `taint=untrusted_web` and loads
   attacker-controllable HTML; without this, browsing does NOT gate downstream
   exfil/high-priv verbs (lethal trifecta open). Add an `mcp.*` branch to
   `_classify_verb_taint` (10638) — the firewall precheck (14076),
   `_session_is_tainted` (10671), `_HIGH_PRIVILEGE_VERBS` (10538) and the row-write
   (14199) are all already present. **Must verify** the MCP dispatch path
   (`_exec_tool_calls` branch b2 ~3665 → `_mcp_call_tool`) persists a tainted
   `tool_call` row to pgvector — the one unverified link.

## NEXT — pure code, no gates

4. **mcp-ranking: TDWA examples for MCP** — *S.* Fold synthetic example queries into
   `_mcp_embed_new_tools` embed text (mirrors the P1 `_verb_embed_text` pattern).
5. **P3 tiering + per-namespace/`detail_level` tool_search** — *M.* Scope `tool_search`
   (17015) by namespace/tier + progressive disclosure. Compounds with more MCP servers.
   ⚠️ keep a `detail_level=full` back-compat fallback (grep existing callers first).

## OPERATOR-GATED

6. **Enable DuckDB + Postgres MCP** — *M, high.* Code is fully ready (Playwright proved
   the pattern). Gates: install `uv`/`uvx` (absent); point postgres-mcp at the unified
   **pgvector** datastore using the EXISTING `mios` pg role (`--access-mode restricted`);
   mkdir+chown `/var/lib/mios/ai/{tmp,.npm,.cache,.duckdb}` to mios-ai (the EACCES trap).
   Do AFTER #2 (clean embeds) + #3 (taint).
7. **Per-node model consolidation (swarm prerequisite)** — *M, high, RISKY.* Assistant
   implements the lane-routing split; operator owns VRAM tuning (mem_fraction 0.45→0.50),
   `qwen3:1.7b` CPU-only confirmation, `mios-llm-worker@` enable, gemma4 21-alias
   retirement (after a SOUL.md/A2A hardcode scan), live 4-agent validation.

## LATER

8. **P5 Code Mode → heavy lane** — *M.* Hardens a default-off feature; cap the
   lane-routing work after #7 establishes the per-lane topology.

## Recommended sequence
`1 always-on → 2 double-prefix → 3 taint-mask → 4 TDWA → 5 p3-tiering →
[operator] 6 duckdb/postgres → 7 node-consolidation → 8 p5-codemode`

## Biggest risks
- **Lethal trifecta open** until P6 lands — sequence P6 before heavy Playwright/postgres use.
- **Measurement unreliable** until the 30s cycle stops — any eval/VRAM number before #1 is non-reproducible.
- **Unverified link:** does the b2 MCP dispatch path persist a tainted `tool_call` row to pgvector? (P6 assumes it.)
- **Breaking changes:** p3 `detail_level=brief` default drops `sig` for callers; node-consolidation alias retirement can 404 hardcoded refs.
- **Postgres MCP ordering:** confirm the `mios` pg role + grants before enabling (postgres-mcp probes ready then fails at call-time on a missing role/permission).

## Deploy discipline
Sync `server.py` + `mios.toml` + `mcp.json` overlay **together** (the P1 "hidden field
unread" gotcha), strip CRLF into `/usr`, then `systemctl restart mios-agent-pipe.service`.
This is the standard MiOS deploy contract — the repo root IS the deployed system root,
so edits land in `/usr` and only take effect after the service restart. Assistant cannot
push — operator pushes from `C:\MiOS`.
