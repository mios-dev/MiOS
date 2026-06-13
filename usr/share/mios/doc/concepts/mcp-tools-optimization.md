<!-- AI-hint: Architectural roadmap for scaling the MiOS agent tool surface — stable prefix caching, two-stage retrieve+rerank selection, and a three-zone tool context — so the local agent stack can expose 5x more tools without the reasoning model drowning or the SGLang heavy-lane prefix cache thrashing. Frames MCP tool optimization within the whole MiOS agentic-OS pipeline (agent-pipe -> inference lanes -> pgvector memory -> MCP/A2A).
     AI-related: /usr/share/mios/ai/v1/mcp.json (vendor), /etc/mios/ai/v1/mcp.json (overlay), mios-mcp, mios-agent-pipe, mios.toml [dispatch] -->
# MiOS: "A Lot of Tools, but Optimized" — MCP tool-scaling plan

_Status: P0/P1/P2 SHIPPED + ENABLED (2026-06-11); P3–P6 staged; P4 in progress.
Research-grounded plan (4-strand workflow vs. the live code) for growing the
agent tool surface ~5x without the reasoning model drowning or the SGLang heavy
lane's prefix cache thrashing._

## Why this matters to MiOS as a whole

MiOS is one system built two ways at once: an immutable, bootc/OCI Fedora
workstation (the whole OS is a single container image — boot it, `bootc upgrade`
it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is *also* a local,
self-replicating, agentic AI operating system. The "agentic" half is a full
local stack behind one OpenAI-compatible endpoint: a request enters through a
front-end (OWUI :3030, the Discord/Hermes gateway, the `mios` CLI), the
**agent-pipe** orchestrator (:8640) refines and fans it out across a
council/swarm, **MiOS-Hermes** (:8642) runs the OpenAI-compatible tool-loop,
**pgvector** (:5432) is the unified agent memory, and the **inference lanes**
generate: `mios-llm-light` (:11450, the primary llama.cpp/llama-swap lane —
everyday models, the `mios-opencode` coder model, AND embeddings via
`nomic-embed-text` on `/v1/embeddings`), with the gated heavy lanes
`mios-llm-heavy` (SGLang, :11441, served-name `mios-heavy`) and
`mios-llm-heavy-alt` (vLLM) for the big reasoning work.

The agent's leverage over that whole machine is its **tools** — typed verbs,
recipes, skills, and external MCP servers. The more capability MiOS can reach
(browse, query the agent DB, run code, drive the desktop), the more of the OS
the agent can actually operate. But tools are not free: every tool definition
costs context the reasoning model must read, and the way they are placed in the
prompt decides whether the SGLang heavy lane gets a RadixAttention cache hit or
re-prefills from scratch. **This doc is the plan for adding a lot of tools while
keeping the model accurate and the lanes fast** — the discipline that lets the
tool surface grow with the system instead of choking it.

**MiOS already has the hard parts.** A `tool_search` meta-tool
(`server.py` ~16583), Code Mode (`mios_codemode.py`), cosine verb-RAG
(`_select_child_tools`), and an MCP layer that both SERVES the universal MiOS
tool surface (`mios-mcp` on `:8765/mcp` + stdio) AND CONSUMES external servers
(`_MCP_CLIENT_TOOLS`, fed by the vendor `mcp.json`). What was missing — and what
P0–P6 below build — is the *architecture that lets all of that scale*.

## The core problem (and the single biggest fix)
`_select_child_tools` returned `out[:cap]` — a **variable** tool set placed at
the **front** of the prompt (native loop, ~`server.py`:19394). Different intent
→ different tool prefix → the heavy lane's RadixAttention radix subtree
invalidates → full re-prefill. The worst place for variable content. **Fix:
stable tool definitions in the cached prefix; per-turn selection by relevance
signal in a small TAIL (and, where SGLang gains a clean tool-mask, by logit
mask), not by editing the prefix.** (Manus context-engineering; Anthropic Tool
Search; RAG-MCP.)

## Three-zone tool context
```
A — STABLE CORE (~8-15 tools, byte-identical every turn) ──── RadixAttention hit
    read, web_search, tool_search, dispatch_to_nodes, system_status, open_app,
    pc_type, remember, recall + top-frequency verbs. NEVER varies.
B — CORE+COMMON DEFINITIONS (~50-70 schemas, defined ONCE, stable) ── also cached
    per-turn selection = relevance over the TAIL (cosine + rerank picks what is
    surfaced, not by reordering the cached prefix).
C — RARE TIER + ALL external MCP servers ─────────────────── NEVER in prompt
    reached via tool_search(query, detail_level) + Code Mode sandbox.
```
Consistent **namespace prefixes** (`browser_`, `pg_`, `mios_`, `pkg_`) so whole
tool groups mask/scope cheaply with one rule.

## Part 1 — MCP servers to add first (local-first → offline-first; cloud opt-in)
Prefer wrapping native verbs over importing redundant servers (127 capabilities
already served by the universal MiOS surface). Skip official
filesystem/git/memory/time/fetch (MiOS has equivalents) + archived Postgres/Slack
refs with disclosed CVEs — do not resurrect those.

**Tier 0 (offline, first):** Playwright (`@playwright/mcp`, ~23 tools — biggest
capability gap, headless browser) · DuckDB (`mcp-server-motherduck`, in-process
analytical SQL over local CSV/Parquet/JSON) · SearXNG-MCP (optional; the native
`web_search` tool, backed by `mios-searxng` :8888, already covers it).
**Tier 1:** Postgres (`crystaldba/postgres-mcp` maintained fork, `--access-mode
restricted` → safe SQL against the EXISTING local pgvector agent DB) · shell/code
-exec (route through the existing coderun-sandbox, no 2nd sandbox) · Docker/K8s
MCP (MiOS ships a k3s one-node-cluster path).
**Tier 3 (cloud, opt-in, key-gated, commented-out):** GitHub vendor server,
Context7, Exa, Tavily/Brave, Discord.

Wire into the registry the agent-pipe MCP client reads: vendor
`/usr/share/mios/ai/v1/mcp.json` (ships `servers:[]` of DISABLED entries) with
admin/user overlays at `/etc/mios/ai/v1/mcp.json` and
`~/.config/mios/ai/v1/mcp.json` (USR-OVER-ETC, Law 1). stdio for co-located
servers; ONE streamable-HTTP (`:8765/mcp`) across host↔VM (point at the local WSL
gateway 172.x, NOT the tailnet). Per-server fields: `tier` (core/common/rare),
`namespace`, `taint`. The base image bakes **no** MCP server binaries, so every
entry is INERT until an operator installs the binary (`npx`/`uvx`) and flips
`enabled:true` — nothing connects out without explicit operator action. The
shipped vendor entries (all `enabled:false`):
```json
{ "object":"mios.mcp.registry","version":"v1","servers":[
  {"id":"playwright","enabled":false,"transport":"stdio","command":"npx","args":["-y","@playwright/mcp@0.0.76","--headless","--isolated"],"tier":"rare","namespace":"browser_","taint":"untrusted_web"},
  {"id":"duckdb","enabled":false,"transport":"stdio","command":"uvx","args":["mcp-server-motherduck","--db-path",":memory:","--read-write"],"tier":"rare","namespace":"duckdb_","taint":""},
  {"id":"postgres","enabled":false,"transport":"stdio","command":"uvx","args":["postgres-mcp@0.3.0","--access-mode","restricted"],"env":{"DATABASE_URI":"postgresql://mios-ai@127.0.0.1:5432/mios"},"tier":"rare","namespace":"pg_","taint":""}
]}
```
PIN every version (no `@latest` — 2026 MCP-SDK supply-chain RCE). The
`mios-ai`-owned writable paths (cwd/HOME/cache/TMPDIR) matter: the agent-pipe
spawns each stdio server as `mios-ai`, which de-escalates `npm`, so all writable
paths must be `mios-ai`-owned or `npm` dies with EACCES.

## Part 2 — Fixing the reasoning model's tool-confusion (e.g. pkg vs mios_apps = "Functional Confusion")
1. **PA-Tool naming alignment** (arXiv 2510.07248): rename confusable model-facing
   names to lexically-unambiguous, pretraining-familiar ones. Measured on
   Llama-3.1-8B: schema errors −80%, functional-confusion −24%, multi-tool
   78.7%→88.3%. Highest leverage, zero model change. Disambiguate via the
   OpenAI-projection name + description (keep the internal verb key stable to
   avoid breaking callers).
2. **Two-stage retrieve→rerank** (RAG-MCP): the old selection was single-stage
   cosine. Add a reranker stage 2 — separates near-duplicate tools far better
   than raw cosine. Never leave two confusable tools both surfaced at high
   confidence.
3. **TDWA description weighting** (ScaleMCP): augment each verb's description with
   synthetic example queries; weight names/examples in the embedding. The
   accuracy ceiling rides on descriptions more than on the model.

## Part 3 — Gateway: YES, but MiOS already IS the gateway
`mios-mcp` is the local aggregator (the Q1-2026 "flat aggregation with RBAC"
pattern). Extend it — do NOT add a second hop (MetaMCP/Docker-Gateway/
ContextForge) on a single node. Namespace-prefix to kill collisions; route all
servers through the universal `dispatch_mios_verb` chokepoint for one policy/
audit/RBAC point + per-namespace allow-lists. Cross-node: use the existing **A2A
peer** mechanism (agents federate via A2A; tools federate via MCP), not federated
MCP (largely unimplemented in the ecosystem).

## Part 4 — Token + security as tools grow
- ~1000 tokens/tool → 5 servers × 30 ≈ 30-60K before the user types. Three-zone
  caps what the reasoning model sees; rare/external never enter the prefix.
- **Progressive disclosure** via `tool_search(query, detail_level)`: name →
  name+desc → schema on demand (Anthropic Tool Search: ~85% token cut, +25pt on
  large libraries).
- **Code Mode → the HEAVY lane only** (`mios-llm-heavy`, SGLang :11441): 98.7%
  token cut but needs a capable code-writer; the everyday light-lane model uses
  Zones A/B + `tool_search`, never authors code over 100 tools.
- **Lethal trifecta by construction**: the `taint` field breaks data-flow (a
  context tainted `untrusted_web` masks-out exfil-capable tools — wired to the
  existing taint-firewall / Semantic Firewall). Tool annotations
  (`destructiveHint`) are UNTRUSTED UX hints — gate destructive ops on host
  policy + the HITL gate, never the server's self-assertion. Pull binaries from
  the signed Docker MCP Catalog; pin versions.

## Part 5 — Prioritized implementation (all SSOT-driven via `mios.toml`)
- **P0 — DONE + ENABLED 2026-06-11** (Approach b = prefix-stability, since SGLang
  has no clean tool-mask yet). Stop the prefix thrash: `_is_core_tool`
  (tier==`core`, 23 verbs) splits the surface into a byte-stable core + non-core
  at cache-build (`_WORKER_TOOLS_CORE_CACHE`); `_select_child_tools` emits the
  core verbatim + a small cosine TAIL (`[dispatch] stable_prefix_tail=10`); the
  native loop sizes `eff_cap = len(core)+tail` (33) so the core is never
  truncated, and splices `dispatch_to_nodes` between core and tail (stays
  cached). Cap-safe: small-cap nodes get `core[:cap]`. The per-turn relevance
  signal rides the TAIL, not the prefix order; the text hint
  (`stable_prefix_hint`) is default-off (it regressed recall). `[dispatch]
  stable_tool_prefix=true` (degrade-open: false == byte-for-byte legacy).
  VERIFIED: 33/33 byte-identical tool prefix across unrelated intents (legacy
  diverges at 6/36); zero accuracy regression on the 7 capabilities. NOT metered:
  exact hit-rate % (SGLang `--enable-metrics` off; restart risks the cuda-graph
  VM-crash) — deterministic given the proven byte-stability. The logit-mask/
  constrained-decode variant remains a future option if SGLang adds clean
  tool-masking.
- **P1 — DONE + ENABLED 2026-06-11** (multi-agent workflow design, adversarially
  verified). Added a model-facing NAME ALIAS layer: `[verbs.*]` gets optional
  `model_name` (the unambiguous name the model sees) + `examples` (TDWA queries
  folded into the retrieval embedding) + `hidden` (drop legacy deadweight off the
  surface). Internal KEYS never change; `_resolve_verb_key` maps alias→key at the
  dispatch chokepoint (`dispatch_mios_verb`), the native-loop permission gate
  (`_exec_tool_calls`), the tier/selection lookups, and `/v1/dispatch`
  (external/MCP). Embeddings carry a `__fingerprint__` so a desc/name/example
  edit auto-rebuilds. Applied: **40 renames** (cu_*→`linux_desktop_*`,
  pc_*→`windows_desktop_*`, the file-find trio
  `find_file_fast`/`windows_file_search`/`linux_file_search`, the page-fetchers
  `fetch_url_text`/`fetch_url_markdown`/`fetch_index_markdown`,
  viking_*→`notes_vault_*`, the launch quartet,
  text_*→`create_file`/`read_file`/…), **31 keep-but-improve** (desc+examples),
  **13 legacy flatpak_/winget_ hidden** (surface 113→100). VERIFIED: alias
  round-trip executes; apps disambiguation 3/3; zero regression on the 7
  capabilities; all 40 model_names globally unique.
- **P2 — DONE + ENABLED 2026-06-11** (judge-panel workflow: 4 approaches → 3
  diverse-lens judges → synthesis; the pure-compute design won on all three
  lenses). A two-stage retrieve→rerank inside `_select_child_tools`, default-ON
  behind `[dispatch] tool_rerank`: stage-1 widens the cosine slice to an
  over-fetch window (K = max(`rerank_fanout`*N, `rerank_min_k`)); stage-2a
  RRF-fuses the cosine rank with an in-process **BM25 lexical arm** over the same
  `_verb_embed_text` corpus (`_ensure_verb_lexicon`, fingerprint-keyed — an
  orthogonal signal that reliably surfaces the single right tool); stage-2b runs
  greedy **MMR** (incremental max-sim, `rerank_mmr_lambda`=0.8) so two confusable
  near-duplicates don't both crowd the top-N tail. No model, **+~3ms** over the
  embed already paid, **4-layer degrade-open** to the exact cosine slice.
  MEASURED on an offline eval (P1 example queries as ground truth): tail-rank-1
  **0.883→0.912** (+2.9pp), recall held at 0.993 (no regression at λ=0.8),
  latency 7.6→10.7ms. NOTE: P1 had already lifted cosine to 91% rank-1 / 99%
  recall, so P2 is a small, free polish (largest gains expected on ambiguous/
  paraphrased intents, untested). FOLLOW-UP (operator-gated, default OFF): a
  bge-reranker-v2-m3 cross-encoder stage-2c behind a `rerank_xenc` flag for the
  hard-paraphrase tail — needs a GGUF + a `mios-llm-light` `--reranking` lane +
  VRAM; inert until deployed.
- **P3** — Tier the registry (core/common/rare) + scope `tool_search`
  per-namespace/tier + add `detail_level`; move rare + ALL external MCP off-prefix
  into the `tool_search` path.
- **P4 — IN PROGRESS 2026-06-11.** Increment-1 DONE + verified: the vendor
  `/usr/share/mios/ai/v1/mcp.json` now ships the 3 Tier-0 servers (Playwright
  `@playwright/mcp@0.0.76` ns=`browser_` taint=`untrusted_web`; DuckDB
  `mcp-server-motherduck` ns=`duckdb_`; Postgres `postgres-mcp@0.3.0
  --access-mode restricted` ns=`pg_`) all `enabled:false` → **inert** (no binary
  baked; the loader reads tier/namespace/taint but skips disabled servers → zero
  behavior change). Operator enables after `npx/uvx` install. **KEY DISCOVERY
  (mock-verified):** MCP tools today are *present-but-unreachable* —
  `_is_core_tool` correctly excludes `mcp.*` from the cached core, but they are
  NOT embedded (so the tail's cosine can't rank them; they leak in only by a
  coincidental name-keyword match in `_priority_fallback_score`) and are INVISIBLE
  to `tool_search` (which searches `_VERB_EMBEDDINGS` only). So the remaining P4
  code-side (Increment-2, the real reachability) is: (1) `_MCP_EMBEDDINGS` dict;
  embed each tool's description at registration in `_mcp_probe_server/
  _mcp_probe_stdio` (best-effort async) keyed by `mcp.<id>.<tool>` (embeddings
  served by `mios-llm-light` `nomic-embed-text`); (2) `_select_child_tools`
  embedding lookup consults `_VERB_EMBEDDINGS` THEN `_MCP_EMBEDDINGS` so MCP tools
  rank by semantic relevance (not keyword luck); (3) a `mcp_tail_cap` SSOT sub-cap
  so MCP tools never crowd native verbs out of the ~10-slot tail; (4)
  `tool_search` also searches `_MCP_EMBEDDINGS` (explicit discovery); (5) loader
  stores `tier/namespace/taint` onto each tool's `_MCP_CLIENT_TOOLS` entry; (6)
  TAINT: a tool from a `taint!=""` server becomes a taint source (like
  `open_url`) → the existing `_HIGH_PRIVILEGE_VERBS` Semantic Firewall (~10522)
  refuses exfil verbs while tainted; destructive ops gate on HITL, never the
  server's `destructiveHint`. Verify Increment-2 with the mock-MCP harness (no
  live server): tool reachable by semantic intent + found by `tool_search` + still
  out of core + taint-source refuses high-priv after. Increment-2 deferred to a
  fresh budget (this spec IS the synthesis).
- **P5** — Route Code Mode to the heavy lane (`[code_mode] heavy_lane_only` →
  `mios-llm-heavy`/`mios-heavy`).
- **P6** — Taint→mask wiring (tainted context masks exfil tools); destructive→HITL.

Key files: `server.py` (`_worker_tools_surface_async` ~5253, `_select_child_tools`
~5309, `_mcp_tool_to_openai_tool` ~9432, native-loop tool assembly ~19394,
`tool_search` 16583) · `mios_codemode.py` · `/usr/share/mios/ai/v1/mcp.json`
(vendor) → `/etc/mios/ai/v1/mcp.json` (overlay) · `mios.toml`
(`[dispatch]` keys + `[verbs.*]` aliases; future `[tools]`/`[code_mode]` keys).

Patterns: Manus context-engineering · Anthropic Tool Search + Code Execution with
MCP · RAG-MCP · ScaleMCP/TDWA · PA-Tool (arXiv 2510.07248) · MetaTool taxonomy ·
lethal trifecta (Willison) · MCP flat-aggregation-with-RBAC.
