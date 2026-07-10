# MiOS — Fresh-Context Execution Plan
> Hand-off for a NEW Claude Code session (clean context). Goal:
> **complete MiOS gaps to true AIOS + make plain-English multi-step launches/tools
> work, tested live.** You have full permission to launch apps / run tools to test.
> Repo root = system root. Deploy = `wsl -d podman-MiOS-DEV -u root` `install`/`cp`
> to `/usr/...` + `systemctl restart`. Push from `C:\MiOS` (Windows-side), to `main`.

## 0. Read first (full detail lives here)
- Memory: `mios-orchestrator-qwen3-and-consolidation-state`, `mios-hermes-mcp-registration-and-resilience` (in `C:\Users\mios\.claude\projects\C--\memory\`).
- Workflow outputs (complete designs, read these for exact edits):
  - AIOS gaps: `…\tasks\wooyqro5x.output`
  - Full lossless consolidation: `…\tasks\w9l97z8h5.output`
  - Prompt grounding: `…\tasks\wrf0rz3uz.output`; MCP resilience: `…\tasks\wkzdsyd3u.output`
  - (base dir: `C:\Users\mios\AppData\Local\Temp\claude\C--\53911777-1e6f-4f47-a7b0-d12c179c366f\tasks\`)

## 1. VERIFIED-DONE this session — do NOT redo (all on `main`)
- MCP server resilience (`19d2c00`): disk-warm prime, 30s bg refresher, SSOT floor, list_changed. `mios-mcp-server`.
- Client-tools path → Qwen3 health-gated (`12d5b90`) + `--reasoning-parser qwen3` on heavy lane (`e7c44aa`, desktop "Thinking" blocks render) + sequential/relevance-cap (`006762a`/`61bb242`).
- SGLang heavy lane (`:11441`, `mios-heavy` Qwen3-8B) RESTORED + running.
- Prompts perfected + grounded: `MiOS.md` (122L), `usr/share/mios/ai/agent-contract.md` (46L) — env/tool-patterns/routing/plan sections, deployable-anywhere, OpenAI-format. (`MiOS.md` is gitignored by the `/*` root rule — on-disk artifact; `agent-contract.md` is tracked.)
- **`hidden_aliases` mechanism (`44a757a`)**: `_load_verb_catalog` reads `hidden_aliases=[...]`; `_build_model_name_map` folds them → keeper; never on model/MCP/A2A surface. Lets redundant verbs be DELETED losslessly.
- **Launch cluster consolidated**: `launch_app`+`launch_verified` REMOVED; `open_app` (model_name `launch_windows_app`) absorbs them via `hidden_aliases`; verified `/v1/tools` shows ONE launch verb. (Routing domain cleaned.)
- `mios dash` → pgvector (retired SurrealDB gone).

## 2. WAVE 1 — the live failures (HIGHEST PRIORITY; operator's core test)
Live, via the `@` shell shortcut → agent-pipe orchestrator (`:8640`):
- `@ open notepad` → WORKS (deterministic route).
- `@ open notepad and type hello world` → FAILS: model emits MALFORMED parallel tool calls (`"arguments": {"name":"notepad"}} "arguments": {"text":"hello world"}}`), nothing executes, times out >120s.
- `@ research news` → FAILS: returns a source LIST from memory, skips `web_search`.
Root cause: the orchestrator native-loop generation runs on a non-reasoning model and mis-serializes multi-step calls + skips tools.

**Fix A (DO FIRST — low-risk, no latency cost): force sequential tool-calls on the native loop.**
- `_respond_native_loop_direct` (server.py:21227) builds `_tools` at 21417 (+ dispatch_to_nodes at 21424). Find its per-iteration chat-completion request body (the tool-loop driver — it posts `_msgs`+`_tools` to the backend; search downward from ~21536 / inside the emit/`_work` path for the request dict or the loop helper it calls).
- Add `parallel_tool_calls: False` to that request body (mirror the client-tools hybrid loop at server.py:20093). This stops the malformed PARALLEL `open_app`+`type` without changing the model.
- Deploy server.py, restart agent-pipe (`sleep 7`; check `is-active`), then VERIFY (step 4).

**Fix B (if A insufficient — quality, but a latency tradeoff): orchestrator → Qwen3 heavy lane.**
- Add `async def _pick_backend(light_ep, light_model)` near `_pick_tool_backend` (server.py:195), reusing cached `_heavy_lane_up()` (176): if heavy up AND `[ai].orch_heavy_pref` → return (`_TOOL_BACKEND_HEAVY` with trailing `/v1` STRIPPED, `_TOOL_BACKEND_HEAVY_MODEL`); else (light_ep, light_model). (Stage endpoints are BARE and append `/v1/chat/completions`; heavy const has `/v1` → strip.)
- Wire into: refine (REFINE_ENDPOINT/MODEL @2224/2223), polish (`_polish_post(ep,model)` @21056 — 2 call sites @ ~9885/21050), planner (PLANNER_ENDPOINT/MODEL @1387/1384), and the native-loop generation backend. LEAVE `/v1/embeddings` (19845) + `/v1/models` (19825) on light — **SGLang serves NO embeddings.**
- Add `[ai] orch_heavy_pref = true` to `usr/share/mios/mios.toml`.
- **TRADEOFF: the heavy lane (`--disable-cuda-graph`) is SLOWER per-token.** The multi-step path already times out, so add/raise NATIVE_LOOP_TIMEOUT_S and consider keeping refine on the fast light lane (only the GENERATION on heavy). Tune, don't blind-swap.
- Degrade-open by construction (heavy down → light). Verify each site; revert if the pipeline breaks.

## 3. WAVE 2 — full lossless consolidation (mechanism is shipped; use it)
Operator mandate: combine the FULL tools+skills+recipes surface, REMOVE redundant ENTIRELY (not hide), KEEP ALL functionality. Apply each merge from `w9l97z8h5.output` via: add `hidden_aliases=[old names]` to the keeper → DELETE the absorbed `[verbs.*]` blocks → fold any UNIQUE params/cmd into the keeper → if arg shapes differ (e.g. `winget_install(id)` vs `pkg(action,name)`) add arg-translation in dispatch. Remaining groups:
- `open_app` gains `node` + `verify` params, folding the removed `launch_verified` (route to daemon `/os_control` `{action:launch,app,node}` when set — `mios-daemon` ~3122/1768). Until then launch+verify = `open_app` then `verify_launch`.
- legacy pkg (13 `winget_*`/`flatpak_*`, already hidden) → `pkg` hidden_aliases + delete blocks + arg-map.
- web readers `web_scrape`/`crawl`/`web_extract`; recipes 19→15 (run-shell, power, open-location, open-windows-config); skills Store-1 11→7, Store-2 13→9.
- KEEP DISTINCT (do NOT merge): memory CRUD (remember/recall/memory_update/memory_forget), `pc_*` (Windows) vs `cu_*` (Linux VM), window-geometry verbs.
- After each merge: `MIOS_STRICT_VERB_ALIASES=1 python3 -c` collision check + `/v1/tools` shows no dupes; verify dispatch of an old name resolves.

## 4. WAVE 3 — remaining AIOS gaps (from `wooyqro5x.output`, near-zero-risk SSOT flips)
- KV-paging on the primary lane: `mios.toml [dispatch] kv_paging_hints "11436"` → `"11450,11436"` (degrade-open).
- agent_memory recall-into-context: server.py:9305 add `_toml_section("memory").get("agent_memory_recall_enable","false")` fallback + `[memory] agent_memory_recall_enable = true`.
- (Wave-1 security defaults provenance_taint / HITL are operator's call.)

## 5. TEST PROTOCOL (you have full permission to launch)
After each deploy, run the operator's exact plain-English tests against the LIVE agent and verify the OUTCOME, not just the response:
- `@ open notepad` → notepad launches (verify `Get-Process notepad`).
- `@ open notepad and type hello world` → notepad launches AND "hello world" is typed (no malformed `"arguments"` in content; check window text / a clean tool_call).
- `@ research todays top trending video game news` → runs `web_search` + returns ACTUAL current headlines (not a source list; check agent-pipe log shows a `/web_search`/searxng call).
Send via WSL: `python3` POST to `http://localhost:8640/v1/chat/completions` `{"model":"MiOS-Agent","stream":false,"messages":[{"role":"user","content":"..."}]}`. Watch `journalctl -u mios-agent-pipe.service` for the backend endpoint hit + tool dispatch.

## 6. DISCIPLINE (hard-won this session)
- mios-mcp is now resilient (cache+refresher) → agent-pipe restarts no longer strip the desktop app's tools; but STILL minimize restarts. The Hermes desktop app registers MCP tools ONCE at app-launch (no hot-reload) — operator restarts it to pick up surface changes.
- Deploy mios.toml/server.py edits then restart agent-pipe (+ mios-mcp re-warms in 30s). Syntax-check (`py_compile`) before deploy. Verify EACH change live before claiming it works. Never claim done unverified.
- No hardcoded keyword/app/topic lists. SSOT in mios.toml. Commit to `main`, push from `C:\MiOS`.
