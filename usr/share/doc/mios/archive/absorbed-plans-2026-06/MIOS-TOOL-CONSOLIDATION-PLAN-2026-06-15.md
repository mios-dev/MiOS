<!-- AI-hint: Tool-surface consolidation plan (2026-06-15), synthesized by the mios-tool-consolidation-plan ultracode workflow (4 agents). Merge ~74 narrow verbs into ~14 enum/mode multi-use verbs + tier/tool_search gating so the per-turn VISIBLE set lands in the ~12-18 band. Back-compat for free via the dispatch chokepoint. File-grounded, phased, security-aware. -->

# MiOS Tool-Surface Consolidation Plan (2026-06-15)

## Principle (cited)
Per-turn **visible** tool count drives selection accuracy, not catalog size: gpt-4o 43%(4 tools)→2%(51) (LangChain ReAct bench); OpenAI guidance "<20 functions at start of a turn"; MCP Tool Search ~85% token cut + Opus 49%→74%. MiOS today = 87 verbs (74 non-hidden) — far past the danger zone. Fix = consolidate narrow verbs into enum/mode verbs (Anthropic "writing tools") + progressive-disclose the rest via `tool_search`. All edits are `mios.toml` data + tier changes; only 3 code constructs need paired edits (below).

## Back-compat is FREE
The model only ever sees `model_name`/key; `dispatch_mios_verb` (`server.py:14732`) resolves alias→key at one chokepoint (`_resolve_verb_key` `:4922`). So: **never rename a key**; add the merged verb with a new `model_name`; keep each superseded key as a real `hidden=true tier=rare` verb (its `cmd`/branch stays dispatchable). Old tool_calls still resolve; no client edits.

## ⚠️ Security: gates key off literal verb KEYS, not permission/enum
`_HIGH_PRIVILEGE_VERBS` (`server.py:11193`), `_MEMORY_VERBS` (`:5048`), and literal branches in `_build_dispatch_cmd` (`tool=="open_app"`/`focus_window`/`os_recipe`/`pkg`/`resize_window`) are name-keyed. Merging a high-priv verb into a new key **silently disables the firewall on the new key** unless the new key is added to the set. **LIVE GAP (pre-existing):** `pkg(action=install)` is NOT in `_HIGH_PRIVILEGE_VERBS` → bypasses the taint firewall today. Fix in Phase 0.

## Merge table (recommended/conservative variants)
| New verb (enum) | Replaces | Δ | Security note |
|---|---|---|---|
| `window_op` (op=move-region\|move-pixel\|resize\|min\|max\|restore\|close\|focus) | 8 window verbs | 8→1 | add to `_HIGH_PRIVILEGE_VERBS`; keep `focus_window` branch |
| `launch_app` (verify bool, position/monitor/args) | open_app, launch_app, launch_verified, verify_launch | 4→1 | rework `open_app`/`launch_app`/`focus_window` literal branches |
| `find_file` (scope=fast\|windows\|linux) | directory_lookup, everything_search, fs_search | 3→1 | read-only |
| `apps` (mode=list\|semantic\|resolve) | mios_apps, app_search, mios_find | 3→1 | resolve = no-launch |
| `fetch_page` (format=text\|index-md\|article-md) | web_extract, web_scrape, crawl | 3→1 | web_search stays separate |
| `search_store` (store=knowledge\|vault) | knowledge_search, notes_vault_search | 2→1 | do NOT fold `tool_search` (escape hatch) |
| `system` (query=status\|env\|env-refresh\|logs\|service-status\|processes\|containers) | 7 sys verbs (status/read) | 7→1 | restarts stay separate (see unit_control) |
| `windows_input` (action=type\|key\|click\|find/click/list-element) | 6 pc_* | 6→1 | add to `_HIGH_PRIVILEGE_VERBS` |
| `linux_input` (action=click\|type\|key\|screenshot\|ground\|atspi\|window-list) | 8 cu_* | 8→1 | add to high-priv (posture confirm) |
| `file_edit` (op=create\|replace\|insert; writes only) | text_create/replace/insert | 3→1 | add to high-priv; leave `text_view` standalone |
| `memory` (op=add\|list\|update\|forget) | remember, recall, memory_update, memory_forget | 4→1 | add to `_MEMORY_VERBS` |
| `vault` (op=list\|read\|search\|ingest) | viking_ls/cat/find, ingest | 4→1 | owns vault-search |
| `run_code` (mode=sandbox\|orchestrate) | coderun, code_mode | 2→1 | keep orchestrate (verbs-as-code) |
| `agent_route` (mode=handoff\|delegate) | handoff, a2a_delegate | 2→1 | |
| `document` (op=build\|convert) | docgen_build, docgen_convert | 2→1 | |
| `pkg` (DONE) | 13 legacy winget_/flatpak_ | 14→1 | **delete the 13 hidden blocks; add `pkg` to high-priv (LIVE GAP)** |
| ~~powershell_run→recipe~~ | — | — | **DEFER** (loses firewall gate unless os_recipe gated) |

Net: ~74 non-hidden → ~38 verbs (±4); **per-turn visible target ~12-18** after re-tiering (the metric that matters).

## Re-tiering + lazy loading (highest-impact, even before merges)
`core` = always-visible byte-stable block; `common` = per-turn cosine tail; `rare` = NOT embedded, reachable only via `tool_search`. Set the per-turn cap (`[dispatch]` `CHILD_TOOL_SELECT`/cap) so core+tail ≈ 15-18.
- **core:** launch_app, find_file, apps, window_op, web_search, fetch_page, system, file_edit (or text_view), memory, tool_search (mandatory), run_code, open_url.
- **common:** search_store, vault, pkg, agent_route, document, windows_input, linux_input, schedule, discord_send, screen_layout.
- **rare (tool_search only):** all hidden legacy keys; sys_env_refresh, summarize, folded element-query verbs. Never rare-tier a hot-path verb (it becomes invisible to cosine).

## Verb↔Recipe↔Skill
- Verb→Recipe: `system` facets that are pure shell one-liners (network/processes) could be recipes; keep status/env as verbs (structured JSON). Defer powershell_run→recipe (security).
- Verb→Skill: add a **`tools-as-code`** skill documenting the `run_code(orchestrate)` pattern (import mios_tools, keep data in sandbox, return summaries — ~98% token cut). Skill metadata ~100 tok always-loaded, body on trigger.
- Recipes/Skills→Verb: none.

## Phased rollout (zero-regression; pair data+code edits)
- **Phase 0 (security, first):** add `pkg` to `_HIGH_PRIVILEGE_VERBS` (closes the live install-bypass); delete the 13 hidden legacy package blocks (87→74 total, 0 model-facing change). ← **starting now (pkg high-priv)**
- **Phase 1 (pure-data merges, low risk):** find_file, apps, fetch_page, search_store, vault, memory(+_MEMORY_VERBS), document, agent_route, run_code.
- **Phase 2 (high-priv/branch-paired):** window_op, windows_input, linux_input, file_edit, system, launch_app (+_build_dispatch_cmd branch rework).
- **Phase 3 (re-tiering data):** apply core/common/rare + tune the per-turn cap.
- **Phase 4:** add tools-as-code skill; (optional/gated) powershell_run→recipe.
- **Verify per phase:** old+new name both dispatch (back-compat); `_validate_enum_args` rejects bad enum; tainted-session → firewall_block for each high-priv add; rare verbs absent from `/v1/verbs/openai-tools`, present via `/v1/tool-search`; end-to-end selection-accuracy at core-only vs core+tail vs full.

## Risks
Name-keyed security gates (the footgun) · over-gating read facets of a merged write verb (keep reads separate: text_view standalone, status folds but restarts separate) · rare-tier hides from cosine · literal `_build_dispatch_cmd` branches need paired edits · missing `section` ⇒ verb silently dropped (`server.py:4724`) · model_name==real-key silently dropped · two-doors ambiguity (vault-search vs search_store) · strict-schema optionals must render nullable (the projection does it from `default`) · post-merge count ~38±4 (variant-dependent; per-turn ceiling is the real metric).
