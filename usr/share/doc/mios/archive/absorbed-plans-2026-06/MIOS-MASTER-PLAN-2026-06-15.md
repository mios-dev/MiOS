<!-- AI-hint: MASTER plan (2026-06-15) — the single index that sequences EVERY MiOS hardening task to completion: what's shipped, what remains, the definitive execution order, done-criteria per item, and the operator-default decisions I proceed on unless told otherwise. Detail lives in the 4 companion plan docs; this is the spine. -->

# MiOS Master Plan — all tasks to completion (2026-06-15)

One spine for everything directed this session. Detail in: `MIOS-COMPLETION-PLAN`, `MIOS-AWARENESS-GROUNDING-PLAN`, `MIOS-TOOL-CONSOLIDATION-PLAN`, `MIOS-NATIVE-OPENAI-PATTERNS-PLAN` (all dated 2026-06-15). **Decisions are pre-resolved to the recommended default below — I proceed on them; override any by telling me.** Plan docs are local by the repo's top-level `.gitignore` allowlist; code ships to `main` (operator's no-branch rule).

Legend: ✅ done+verified · 🔜 next · ⏳ queued · 🧰 operator-action (deploy/verify) · 🔑 decision (defaulted).

## EXECUTION LOG (live)
Shipped to `main` + verified this run: WS-A env-aware (`49009c1`) · WS-B-C Zen contract (`3c729b2`) · WS-E conformance (`3c729b2`) · pkg firewall gate (`870e4a7`) · WS-G web-grounding interim (`02cd51e`) · **WS-H1 refine→Structured Outputs + lean interim prose** (`41aa11a`) · **WS-H2 router→Structured Outputs** (`41aa11a`) · **WS-D Zen-discoverable** (`08aaced`) · **WS-B-B slow-lane contract pin** (`08a4e22`) · **MCP tools/list cache — restarts no longer zero a clients tools** (`ee23bc7`) · **Hermes reasoning streams (dual reasoning/reasoning_content)** (`f81ec93`) · **WS-C bake root MDs into image** (`21b09a6`).
Assessed: `/MiOS.md` already lean + MiOS-specific (WS-H3 contract target MET). Router verb-table NOT a safe delete (it carries verb-selection guidance, not just structure). 
REMAINING (large, fresh-context): WS-F (14-verb enum merges + high-priv pairing + re-tiering/per-turn cap), WS-H3 (47KB hermes-soul.md trim; surgical refine Fields-block / router-table trims), WS-D-remainder ([[desktop.app_types]] per-type OS-pref schema + mios-app-type/mios-app-default shims + open_url default-browser consumer).

## ✅ DONE + verified (on `main`)
1. Zen Smart Window identity + tools — hybrid loop (`4402b80`)
2. Hermes desktop launch skill — MCP-first + env-hint + pinned (host-local)
3. SoM UIA lane — `/ui/find` `/ui/click` `/ui/list` + verbs (`4402b80`)
4. **WS-A** env-awareness — `system_status.os` → real Windows 11; SOUL/OWUI/Zen "never assume OS" (`49009c1`)
5. **WS-B-C** Zen grounds in full `/MiOS.md` contract (`3c729b2`)
6. **WS-E** OpenAI conformance — tool_call id-synth + tool_choice/parallel forward (`3c729b2`)
7. **pkg** firewall gate — closed live install-bypass (`870e4a7`)
8. **WS-G** web-grounding (interim) — recency/knowledge-gap fires web search, verified (`02cd51e`)

## Execution sequence to COMPLETION (definitive order)

### 1. 🔜 WS-H1 — Refine → Structured Outputs
Copy the proven `_route_domain` template (`server.py:11598-11638`) to refine: `_refine_response_format()` (enums from `_VERB_CATALOG`/agents/`_ROUTING_DOMAINS`), payload `response_format`+`chat_template_kwargs:{enable_thinking:False}`, drop `/no_think`, refusal-guard, collapse 3-tier parse, gate `MIOS_REFINE_STRUCTURED` (degrade-open). Then delete the `Fields:` prose block **and** the interim WS-G recency prose.
**Done when:** curl battery to `:11450` returns 200 + valid JSON + `intent` in-enum across chat/dispatch/agent/multi_task/local/news/web; journal refine `parse_fail`→~0; interim prose gone; OWUI routing unbroken (operator spot-check).

### 2. ⏳ WS-H2 — Router → Structured Outputs
`json_object`→strict `json_schema` `{action,tool?,args?}` + `enable_thinking:False`; delete the hand-written `[WRITE]/[READ]` verb table in `_ROUTER_SYSTEM` (~1400 tok, SSOT violation); gate `MIOS_ROUTER_STRUCTURED`.
**Done when:** router emits in-enum `action`; prose table gone; `"action" not in parsed` branch removed; routing verified.

### 3. ⏳ WS-D — App-type aliases + Zen reachable (fixes "open a tab"→Chrome / "zen not found")
`[[desktop.app_types]]` SSOT (🔑 **default:** games=windows, settings/system=both, else linux-first; browser default Epiphany + `windows_default=zen`); new `mios-app-type` resolver + `mios-app-default` switch verb; `mios-apps` generative default-browser scan (🔑 **read Zen ProgId live**, don't bake); `mios-windows` url-protocol resolve; `mios-open-url`/`mios-launch`/`mios-find` delegate.
**Done when:** `mios-find "zen"` resolves to real zen.exe; "open a tab"/"open zen" opens Zen; per-type policy honored; user can switch a default by telling the AI.

### 4. ⏳ WS-F — Tool consolidation (Phases 0-3)
Delete the 13 hidden legacy `pkg` blocks (87→74). Merge enum/mode verbs (window_op, find_file, apps, fetch_page, system, file_edit, memory, vault, windows_input, linux_input, run_code, agent_route, document, search_store) with old keys kept `hidden=true tier=rare` (back-compat at the dispatch chokepoint); **pair every high-priv merge with the `_HIGH_PRIVILEGE_VERBS` edit**; re-tier core/common/rare + set the per-turn cap so visible tools ≈ 12-18.
**Done when:** old+new names both dispatch; high-priv merges firewall-gate (tainted→block); rare verbs absent from `/v1/verbs/openai-tools`, present via `/v1/tool-search`; visible per-turn count in band.

### 5. ⏳ WS-C — Root MDs into the sealed image + Hermes root symlinks
🔑 **default:** bake real `MiOS.md`/`AGENTS.md`/`CLAUDE.md`/… via `Containerfile` COPY+install (safe on git-worktree AND image-only); add `usr/lib/tmpfiles.d/mios-ai-links.conf` for Hermes-asset aliases (vendor-SSOT targets only); keep the FHS install (no `HOME=/`).
**Done when:** root MDs exist on a clean OCI build (contract no longer degrades to `""`); `just lint`/`bootc container lint` pass; SELinux contexts correct.

### 6. ⏳ WS-H3 — Lean, MiOS-specific prompts
Trim `hermes-soul.md` (~11.9k→~3k tok; long-form to `hermes-soul-full.md`), `_AGENT_CONTRACT` (~1355→~400 tok, cut generic half), consolidate generic identity into one developer-role message. Keep MiOS-specific facts; delete generic agent-behavior prose.
**Done when:** token targets met; behavior held on the known cases (operator spot-check); revert path = prose rollback.

### 7. ⏳ WS-B-B — Slow-lane contract pin
Mark the contract block `_mios_pin`; `_trim_sys_prefix` skips pinned blocks so iGPU/phone/remote council secondaries get the full `/MiOS.md` (not truncated to ~25%), while still trimming the research block.
**Done when:** slow-lane council members receive the full contract; web-research trim unaffected.

### 8. ⏳ Cleanup pass (P3-P4)
WS-F Phase 4 (`tools-as-code` skill) · WS-B A/D/F (layer INDEX/system.md as trimmable block; `_lead_system_blocks` chokepoint; mtime-reload) · WS-E #3/#1 (parallel_tool_calls already; doc the SSE invariant) · WS-C `/etc/mios/hermes/config.yaml` dead-seed reconcile · delete dead `mios-hermes-init-hook` · WS-G proper removal confirmation.
**Done when:** dead code/config removed; durability items in place.

### Decided (no work): WS-H4 — stay on Chat Completions + `response_format`; keep agent-pipe internal loop Responses-shaped for a future cloud lane.

## Operator-default decisions (I proceed on these)
- Heavy GPU lane: **off by default** (chat-responsive). · WS-C: **bake real MDs**, FHS install + symlinks. · WS-D: per-type policy as above, **Zen ProgId read live**. · WS-B: fold INDEX/system.md as a separate trimmable block; `/AGENTS.md`,`/CLAUDE.md` stay build-time stubs. · uid drift in `hermes-agent.service`: out of scope, tracked separately.

## Cross-cutting rules (every item)
SSOT in `mios.toml`→`install.env`→`${MIOS_*:-default}`; enums projected from `_VERB_CATALOG` (no hardcoded verb/topic lists); deploy = `wsl cp` + `systemctl restart mios-agent-pipe.service`, push to `main` from the Windows repo; **VM `/usr` is a copy** → edits are source-only, need operator deploy+verify; no live app launches (operator verifies visibly); minimize agent-pipe restarts during live testing.

## Done = all of §1-8 shipped to `main` + verified, interim WS-G prose removed, the 5 plan docs reconciled into this spine.
