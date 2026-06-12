# MiOS: "A Lot of Tools, but Optimized" — MCP scaling plan (2026-06-11)

Research-grounded plan (4-strand workflow vs the live code) for growing the tool
surface 5x without the 8B drowning or the SGLang prefix cache thrashing. **MiOS
already has the hard parts** — `tool_search` meta-tool (server.py:16583), Code
Mode (`mios_codemode.py`), cosine verb-RAG (`_select_child_tools`), MCP serve
(`mios-mcp` :8765/mcp + stdio) AND consume (`_MCP_CLIENT_TOOLS`, vendor-empty
`mcp.json`). What's missing is the architecture that lets it scale.

## The core problem (and the single biggest fix)
`_select_child_tools` returns `out[:cap]` — a **variable** tool set placed at the
**front** of the prompt (native loop, ~server.py:19394). Different intent → different
tool prefix → the RadixAttention radix subtree invalidates → full re-prefill. The
worst place for variable content. **Fix: stable tool definitions in the cached
prefix; per-turn selection by logit-MASK (SGLang constrained decode), not by editing
the prefix.** (Manus context-engineering; Anthropic Tool Search; RAG-MCP.)

## Three-zone tool context
```
A — STABLE CORE (~8-15 tools, byte-identical every turn) ──── RadixAttention hit
    read, web_search, tool_search, dispatch_to_nodes, system_status, open_app,
    pc_type, remember, recall + top-frequency verbs. NEVER varies.
B — CORE+COMMON DEFINITIONS (~50-70 schemas, defined ONCE, stable) ── also cached
    per-turn selection = logit-mask the disallowed; cosine+rerank picks what is
    UNMASKED, not what is PRESENT.
C — RARE TIER + ALL external MCP servers ─────────────────── NEVER in prompt
    reached via tool_search(query, detail_level) + Code Mode sandbox.
```
Consistent **namespace prefixes** (`browser_`, `pg_`, `mios_`, `pkg_`) so whole tool
groups mask cheaply with one rule.

## Part 1 — MCP servers to add first (local-first → offline-first; cloud opt-in)
Prefer wrapping native verbs over importing redundant servers (127 already served).
Skip official filesystem/git/memory/time/fetch (MiOS has equivalents) + archived
Postgres/Slack refs (disclosed CVEs — do not resurrect).

**Tier 0 (offline, first):** Playwright (`@playwright/mcp`, ~20-25 tools — biggest
capability gap, headless browser) · DuckDB (`mcp-server-motherduck`, analytical SQL)
· SearXNG-MCP (optional; `web_search` already covers it).
**Tier 1:** Postgres (`crystaldba/postgres-mcp` maintained fork, `--access-mode
restricted` → query pgvector) · shell/code-exec (route through existing
coderun-sandbox, no 2nd sandbox) · Docker/K8s MCP.
**Tier 3 (cloud, opt-in, key-gated, commented-out):** GitHub vendor server, Context7,
Exa, Tavily/Brave, Discord.

Wire into `/etc/mios/ai/v1/mcp.json` overlay (vendor ships `servers:[]`). stdio for
co-located; ONE streamable-HTTP (`:8765/mcp`) across host↔VM (point at the local WSL
gateway 172.x, NOT the tailnet). New per-server fields: `tier` (core/common/rare),
`namespace`, `taint`. Example:
```json
{ "object":"mios.mcp.registry","version":"v1","servers":[
  {"name":"playwright","transport":"stdio","command":"npx","args":["-y","@playwright/mcp@latest","--headless"],"tier":"common","namespace":"browser_","taint":"untrusted_web"},
  {"name":"duckdb","transport":"stdio","command":"uvx","args":["mcp-server-motherduck","--db-path",":memory:"],"tier":"rare","namespace":"duckdb_"},
  {"name":"postgres","transport":"stdio","command":"uvx","args":["postgres-mcp","--access-mode","restricted"],"env":{"DATABASE_URI":"postgresql://mios-ai@127.0.0.1:5432/mios"},"tier":"rare","namespace":"pg_"}
]}
```

## Part 2 — Fixing the 8B's tool-confusion (pkg vs mios_apps = "Functional Confusion")
1. **PA-Tool naming alignment** (arXiv 2510.07248): rename confusable model-facing
   names to lexically-unambiguous, pretraining-familiar ones. Measured on Llama-3.1-8B:
   schema errors −80%, functional-confusion −24%, multi-tool 78.7%→88.3%. Highest
   leverage, zero model change. Disambiguate via the OpenAI-projection name +
   description (keep the internal verb key stable to avoid breaking callers).
2. **Two-stage retrieve→rerank** (RAG-MCP): current selection is single-stage cosine.
   Add a reranker stage 2 — separates near-duplicate tools far better than raw cosine.
   Never leave two confusable tools both unmasked at high confidence.
3. **TDWA description weighting** (ScaleMCP): augment each verb's description with
   synthetic example queries; weight names/examples in the embedding. The accuracy
   ceiling rides on descriptions more than on the model.

## Part 3 — Gateway: YES, but MiOS already IS the gateway
`mios-mcp` is the local aggregator (the Q1-2026 "flat aggregation with RBAC" pattern).
Extend it — do NOT add a second hop (MetaMCP/Docker-Gateway/ContextForge) on a single
node. Namespace-prefix to kill collisions; route all servers through the universal
`dispatch_mios_verb` chokepoint for one policy/audit/RBAC point + per-namespace
allow-lists. Cross-node: use the existing A2A peer mechanism, not federated MCP
(largely unimplemented in the ecosystem).

## Part 4 — Token + security as tools grow
- ~1000 tokens/tool → 5 servers × 30 ≈ 30-60K before the user types. Three-zone caps
  what the 8B sees; rare/external never enter the prefix.
- **Progressive disclosure** via `tool_search(query, detail_level)`: name → name+desc
  → schema on demand (Anthropic Tool Search: ~85% token cut, +25pt on large libraries).
- **Code Mode → the HEAVY lane only** (14B): 98.7% token cut but needs a capable
  code-writer; the 8B uses Zones A/B + tool_search, never authors code over 100 tools.
- **Lethal trifecta by construction**: the `taint` field breaks data-flow (a context
  tainted `untrusted_web` masks-out exfil-capable tools — wire to the existing
  taint-firewall). Tool annotations (`destructiveHint`) are UNTRUSTED UX hints — gate
  destructive ops on host policy + the HITL gate, never the server's self-assertion.
  Pull binaries from the signed Docker MCP Catalog; pin versions (2026 MCP-SDK RCE).

## Part 5 — Prioritized implementation (all SSOT-driven via mios.toml)
- **P0 — DONE + ENABLED 2026-06-11** (Approach b = prefix-stability, since SGLang has no
  clean tool-mask). Stop the prefix thrash: `_is_core_tool` (tier==`core`, 23 verbs)
  splits the 113-tool surface into a byte-stable core + non-core at cache-build
  (`_WORKER_TOOLS_CORE_CACHE`); `_select_child_tools` emits the core verbatim + a small
  cosine TAIL (`[dispatch] stable_prefix_tail=10`); the native loop sizes `eff_cap =
  len(core)+tail` (33) so the core is never truncated, and splices `dispatch_to_nodes`
  between core and tail (stays cached). Cap-safe: small-cap nodes get `core[:cap]`. The
  per-turn relevance signal rides the TAIL, not the prefix order; the text hint
  (`stable_prefix_hint`) is default-off (it regressed recall). `[dispatch]
  stable_tool_prefix=true` (degrade-open: false == byte-for-byte legacy). VERIFIED: 33/33
  byte-identical tool prefix across unrelated intents (legacy diverges at 6/36); zero
  accuracy regression on the 7 capabilities. NOT metered: exact hit-rate % (SGLang
  `--enable-metrics` off; restart risks the cuda-graph VM-crash) — deterministic given the
  proven byte-stability. The logit-mask/constrained-decode variant remains a future option
  if SGLang adds clean tool-masking.
- **P1 — DONE + ENABLED 2026-06-11** (multi-agent workflow design, adversarially
  verified). Added a model-facing NAME ALIAS layer: `[verbs.*]` gets optional
  `model_name` (the unambiguous name the 8B sees) + `examples` (TDWA queries folded into
  the retrieval embedding) + `hidden` (drop legacy deadweight off the surface). Internal
  KEYS never change; `_resolve_verb_key` maps alias→key at the dispatch chokepoint
  (`dispatch_mios_verb`), the native-loop permission gate (`_exec_tool_calls`), the
  tier/selection lookups, and `/v1/dispatch` (external/MCP). Embeddings carry a
  `__fingerprint__` so a desc/name/example edit auto-rebuilds. Applied: **40 renames**
  (cu_*→`linux_desktop_*`, pc_*→`windows_desktop_*`, the file-find trio
  `find_file_fast`/`windows_file_search`/`linux_file_search`, the page-fetchers
  `fetch_url_text`/`fetch_url_markdown`/`fetch_index_markdown`, viking_*→`notes_vault_*`,
  the launch quartet, text_*→`create_file`/`read_file`/…), **31 keep-but-improve**
  (desc+examples), **13 legacy flatpak_/winget_ hidden** (surface 113→100). VERIFIED:
  alias round-trip executes; apps disambiguation 3/3; zero regression on the 7
  capabilities; all 40 model_names globally unique.
- **P2 — DONE + ENABLED 2026-06-11** (judge-panel workflow: 4 approaches → 3 diverse-lens
  judges → synthesis; the pure-compute design won on all three lenses). A two-stage
  retrieve→rerank inside `_select_child_tools`, default-ON behind `[dispatch] tool_rerank`:
  stage-1 widens today's cosine to an over-fetch window (K = max(`rerank_fanout`*N,
  `rerank_min_k`)); stage-2a RRF-fuses the cosine rank with an in-process **BM25 lexical
  arm** over the same `_verb_embed_text` corpus (`_ensure_verb_lexicon`, fingerprint-keyed
  -- an orthogonal signal that reliably surfaces the single right tool); stage-2b runs
  greedy **MMR** (incremental max-sim, `rerank_mmr_lambda`=0.8) so two confusable
  near-duplicates don't both crowd the top-N tail. No model, **+~3ms** over the embed
  already paid, **4-layer degrade-open** to the exact cosine slice. MEASURED on an offline
  eval (P1 example queries as ground truth): tail-rank-1 **0.883→0.912** (+2.9pp), recall
  held at 0.993 (no regression at λ=0.8), latency 7.6→10.7ms. NOTE: P1 had already lifted
  cosine to 91% rank-1 / 99% recall, so P2 is a small, free polish (largest gains expected
  on ambiguous/paraphrased intents, untested). FOLLOW-UP (operator-gated, default OFF): a
  bge-reranker-v2-m3 cross-encoder stage-2c behind a `rerank_xenc` flag for the hard-
  paraphrase tail -- needs a GGUF + a llama-swap `--reranking` lane + VRAM; inert until
  deployed.
- **P3** — Tier the registry (core/common/rare) + scope `tool_search` per-namespace/tier
  + add `detail_level`; move rare + ALL external MCP off-prefix into the tool_search path.
- **P4 — IN PROGRESS 2026-06-11.** Increment-1 DONE + verified: the vendor
  `usr/share/mios/ai/v1/mcp.json` now ships the 3 Tier-0 servers (Playwright
  `@playwright/mcp@0.0.41` ns=`browser_` taint=`untrusted_web`; DuckDB
  `mcp-server-motherduck@0.6.1` ns=`duckdb_`; Postgres `postgres-mcp@0.3.0
  --access-mode restricted` ns=`pg_`) all `enabled:false` -> **inert** (no binary baked;
  the loader reads tier/namespace/taint but skips disabled servers -> zero behavior
  change). Operator enables after `npx/uvx` install. **KEY DISCOVERY (mock-verified):**
  MCP tools today are *present-but-unreachable* — `_is_core_tool` correctly excludes
  `mcp.*` from the cached core, but they are NOT embedded (so the tail's cosine can't rank
  them; they leak in only by a coincidental name-keyword match in `_priority_fallback_score`)
  and are INVISIBLE to `tool_search` (which searches `_VERB_EMBEDDINGS` only). So the
  remaining P4 code-side (Increment-2, the real reachability) is: (1) `_MCP_EMBEDDINGS`
  dict; embed each tool's description at registration in `_mcp_probe_server/_mcp_probe_stdio`
  (best-effort async) keyed by `mcp.<id>.<tool>`; (2) `_select_child_tools` embedding
  lookup consults `_VERB_EMBEDDINGS` THEN `_MCP_EMBEDDINGS` so MCP tools rank by semantic
  relevance (not keyword luck); (3) a `mcp_tail_cap` SSOT sub-cap so MCP tools never crowd
  native verbs out of the ~10-slot tail; (4) `tool_search` also searches `_MCP_EMBEDDINGS`
  (explicit discovery); (5) loader stores `tier/namespace/taint` onto each tool's
  `_MCP_CLIENT_TOOLS` entry; (6) TAINT: a tool from a `taint!=""` server becomes a taint
  source (like `open_url`) -> the existing `_HIGH_PRIVILEGE_VERBS` Semantic Firewall
  (~10522) refuses exfil verbs while tainted; destructive ops gate on HITL, never the
  server's `destructiveHint`. Verify Increment-2 with the mock-MCP harness (no live
  server): tool reachable by semantic intent + found by tool_search + still out of core +
  taint-source refuses high-priv after. Increment-2 deferred to a fresh budget (the design
  workflow's judges/synth hit the session limit; this spec IS the synthesis).
- **P5** — Route Code Mode to the heavy lane (`[code_mode] heavy_lane_only`).
- **P6** — Taint→mask wiring (tainted context masks exfil tools); destructive→HITL.

Key files: `server.py` (`_worker_tools_surface_async` ~5253, `_select_child_tools`
~5309, `_mcp_tool_to_openai_tool` ~9432, native-loop tool assembly ~19394,
`tool_search` 16583) · `mios_codemode.py` · `usr/share/mios/ai/v1/mcp.json` (vendor)
→ `/etc/mios/ai/v1/mcp.json` (overlay) · `mios.toml` (new `[tools]`/`[code_mode]` keys).

Patterns: Manus context-engineering · Anthropic Tool Search + Code Execution with MCP
· RAG-MCP · ScaleMCP/TDWA · PA-Tool (arXiv 2510.07248) · MetaTool taxonomy · lethal
trifecta (Willison) · MCP flat-aggregation-with-RBAC.
