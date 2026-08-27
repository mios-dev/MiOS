<!-- AI-hint: Measured MIOS_* value-duplication audit feeding the AGY de-dup campaign (AGY-856..930); groups the 2416 resolver-emitted env vars by VALUE, classifies every >=2-key group {true-alias | distinct-configurable-fact | intentional-many-to-one | unset-default}, quantifies 13 systematic prefix-alias families (408 keys), and lists cross-surface hardcoded literals that duplicate SSOT values. Regenerate via usr/libexec/mios/mios-env-snapshot. -->
<!-- AI-related: usr/libexec/mios/mios-env-snapshot, usr/lib/mios/userenv.sh, usr/share/mios/mios.toml, usr/share/mios/configurator/mios.html, usr/share/mios/knowledge/mios-knowledge-graph.json, MiOS-SBOM.csv, usr/share/doc/mios/reference/audit-value-dup-report.md -->

# MiOS Value-Duplication Audit (AGY-856..930 feed)

**Generated:** 2026-07-31 &nbsp;|&nbsp; **Source of truth:** live resolver snapshot &nbsp;|&nbsp; **Method:** measured, not estimated.

This report is the grounded input for the AGY de-duplication campaign. It answers one
question exhaustively: *of the `MIOS_*` variables the resolver emits from `mios.toml`,
which distinct configuration values are carried by two or more keys, and which of those
collisions are true aliases that should collapse to a single SSOT-derived value versus
independent facts that merely coincide today?*

## 1. How this was measured (reproducible)

```bash
# Hermetic: mios-env-snapshot pins LC_ALL=C + HOME=/nonexistent internally, resolves
# ONLY the version-controlled vendor SSOT (+ in-tree mios.d), and sorts deterministically.
bash /usr/libexec/mios/mios-env-snapshot > snapshot.txt      # 2416 KEY=VALUE lines
# On this Windows working tree the resolver was run through WSL:
#   wsl bash -c 'bash /mnt/c/MiOS/usr/libexec/mios/mios-env-snapshot' > snapshot.txt
```

Every number below is derived from that snapshot (`grep -c '^MIOS_' = 2416`). Grouping,
classification and the family analysis were computed programmatically over the raw lines;
nothing here is hand-tallied.

## 2. Headline numbers

| metric | value |
|---|---|
| Total `MIOS_*` keys resolved | **2416** |
| Distinct values | **684** |
| Values carried by >=2 keys (duplicate groups) | **289** |
| Keys participating in a duplicate group | **2021** (83.6% of all keys) |
| Keys with a unique value | 395 |
| Keys resolving to the **empty string** | **774** (`unset-default`) |
| Keys inside a **systematic prefix-alias family** | **408** (16.9% of all keys) |

### Classification of the 289 duplicate groups

| class | groups | keys | meaning |
|---|---|---|---|
| **true-alias** | 142 | 312 | Same SSOT fact under >=2 names; **collapse to one derived value.** Primary campaign target. |
| **distinct-configurable-fact** | 138 | 903 | Independently-configurable facts that only *coincide* today (booleans, small ints, shared colors/UIDs); collapsing would wrongly couple them. |
| **intentional-many-to-one** | 8 | 32 | Deliberate many->one maps (`mios-find` launcher alias tables); by design, leave as-is. |
| **unset-default** | 1 | 774 | All resolve to `""` (feature-flag / optional keys left blank in the vendor layer). |

> **Methodology caveat (read before acting).** Grouping purely *by value* both over- and
> under-counts real aliasing. It **under**-counts when one value is shared by an alias
> pair *and* a coincidental collision — e.g. `816` is carried by `MIOS_FORGE_UID`,
> `MIOS_FORGE_GID`, `MIOS_SERVICES_FORGE_UID`, `MIOS_SERVICES_FORGE_GID`: two true-alias
> pairs (`*_UID`/`SERVICES_*_UID`, `*_GID`/`SERVICES_*_GID`) that also happen to equal each
> other, so the value-group is labelled *distinct* even though it contains aliases. It
> **over**-counts when unrelated facts share a default. **The precise, actionable de-dup
> signal is the prefix-alias *family* analysis in section 3**, which keys off name-stems,
> not values. Use section 3 to drive AGY-856..930; use section 5 as the exhaustive backing
> data.

## 3. Systematic prefix-alias families (the actual de-dup targets)

Thirteen naming transforms account for **408 distinct keys** (~17% of the namespace). Each
row is a *rewrite rule*: the two spellings resolve to the same value and should be reduced
to one canonical key whose consumers read a single SSOT-derived variable. `pairs` counts
verified same-valued variant/canonical key pairs; `value-drift` flags pairs whose values
already **disagree** (silent divergence — a bug the collapse fixes).

| # | alias family (variant = canonical) | keys | pairs | value-drift | notes |
|---|---|---:|---:|---:|---|
| 1 | `MIOS_PORTS_<X>` = `MIOS_PORT_<X>` (plural vs singular) | 62 | 31 | **4** | Ports also have a 3rd spelling `MIOS_<SVC>_PORT`; see section 4.2. |
| 2 | `MIOS_SERVICES_<svc>_*` = `MIOS_<svc>_*` (UID/GID/USER) | 60 | 30 | 0 | Service-account identity duplicated under two namespaces. |
| 3 | `MIOS_PGVECTOR_*` = `MIOS_PG_*` | 52 | 26 | **1** | `*_USER` is a false-friend (see 4.1) — do **not** blind-collapse. |
| 4 | `MIOS_ROUTING_*` = `MIOS_*` (NL routing phrase lists) | 40 | 20 | 0 | Long comma-lists duplicated verbatim. |
| 5 | `MIOS_STORAGE_CEPHFS_*` = `MIOS_CEPHFS_*` | 38 | 19 | 0 | Entire CephFS config carried twice. |
| 6 | `MIOS_A2O_*` = `MIOS_FRONTIER_*` | 34 | 17 | 0 | Lane/orchestration config under two plane names. |
| 7 | `MIOS_PATHS_*` = `MIOS_*` (filesystem paths) | 34 | 17 | 0 | Path SSOT emitted under both bare and `PATHS_` prefix. |
| 8 | `MIOS_COLORS_ANSI_<n>` = `MIOS_ANSI_<n>` | 32 | 16 | 0 | Theme projection; see section 4.3. |
| 9 | `MIOS_COLORS_<role>` = `MIOS_COLOR_<role>` | 24 | 12 | 0 | Singular/plural color prefix. |
| 10 | `MIOS_ENV_MIOS_URL_*` = `MIOS_URL_*` | 14 | 7 | 0 | Repo/download URLs duplicated. |
| 11 | `MIOS_EDITIONS_MIOS_*_MINI_*` = `MIOS_METAL_*` | 8 | 6 | 0 | Edition overlays re-emit the base MINI keys. |
| 12 | `MIOS_WSL2_DESKTOP_COMPAT_*` = `MIOS_WSLG_*` | 6 | 3 | 0 | GDK/QT backend duplicated. |
| 13 | `*_TIMEOUT_SECONDS` = `*_TIMEOUT_S` | 4 | 2 | 0 | `MIOS_POLISH_*`, `MIOS_REFINE_*` carry both suffix forms. |
| | **TOTAL (distinct keys touched)** | **408** | **176** | **5** | |

Beyond these families, section 5 contains additional non-systematic true-aliases — e.g.
`granite4.1:8b` across **8** model keys (`MIOS_AI_MODEL`, `MIOS_MODEL`, `MIOS_HERMES_MODEL`,
`MIOS_GATEWAY_MODEL`, `MIOS_STACK_MODEL`, `MIOS_FINETUNE_BASE_MODEL`,
`MIOS_FINETUNE_TEACHER_MODEL`, `MIOS_AGENT_PIPE_TOOL_BACKEND_MODEL`), `/bin/bash` across the
three shell keys, and the identity group-list across `MIOS_{DEFAULT,IDENTITY,USER}_GROUPS`.

## 4. Notable findings

### 4.1 False-friends: alias-shaped pairs whose values already DISAGREE

These look like aliases by name but resolve to **different** values — proof that some are
distinct facts and that others have already silently drifted. A blind name-based collapse
would corrupt them; the canonical map (section 6) must special-case them.

```
[PGVECTOR_ = PG_]  MIOS_PGVECTOR_USER='mios-pgvector'  !=  MIOS_PG_USER='mios'
[PORTS_  = PORT_]  MIOS_PORTS_CEPH_DASHBOARD='8444'    !=  MIOS_PORT_CEPH_DASHBOARD=''   (singular empty)
[PORTS_  = PORT_]  MIOS_PORTS_GUACAMOLE_WEB='8080'     !=  MIOS_PORT_GUACAMOLE_WEB=''     (singular empty)
[PORTS_  = PORT_]  MIOS_PORTS_K3S_API='8443'           !=  MIOS_PORT_K3S_API=''           (singular empty)
[PORTS_  = PORT_]  MIOS_PORTS_RDP='8389'               !=  MIOS_PORT_RDP=''               (singular empty)
```

`MIOS_PGVECTOR_USER` (the `mios-pgvector` service account) genuinely differs from
`MIOS_PG_USER` (the `mios` Postgres role) — **distinct fact, keep both.** The four empty
singular ports are an *incomplete* alias family: the value lives only in the plural table
plus a bespoke `MIOS_<SVC>_PORT` form, leaving `MIOS_PORT_<X>` unpopulated.

### 4.2 Ports are spelled up to three ways

`MIOS_COCKPIT_PORT` = `MIOS_PORTS_COCKPIT` = `MIOS_PORT_COCKPIT` = `8090` (full 3-way alias).
Forge (`8300`/`8301`) and SearXNG (the `searxng` port) follow the same triple. The de-dup should pick
ONE canonical port spelling (recommend the `[ports]`-table-native `MIOS_PORTS_<X>`) and
derive the other two — or delete them — closing the section-4.1 empties in the process.

### 4.3 Theme palette: SSOT-projected keys are correct; the surfaces that COPY them are not

`MIOS_COLORS_ANSI_4_BLUE = MIOS_ANSI_4_BLUE = MIOS_COLOR_ACCENT = MIOS_COLORS_INFO = #1A407F`
is the theme SSOT projection working as intended (one `[colors]` slot fanned to role +
ANSI + prefix-variant surfaces). Those are *derived*, so they are not the problem. The
problem is the non-SSOT surfaces that **hard-copy** the same hexes — see section 4.4.

### 4.4 Cross-surface hardcoded literals (duplicate an SSOT value in a non-SSOT file)

| # | value | SSOT key it equals | hardcoded at | verdict |
|---|---|---|---|---|
| H1 | 28-colour palette (`#282262`,`#E7DFD3`,`#1A407F`,`#F35C15`,`#3E7765`,`#DC271B`,`#948E8E`,`#B7C9D7`,`#734F39`,`#E0E0E0`, + 16 ANSI) | `MIOS_COLORS_*` / `[colors]` | `usr/share/mios/configurator/mios.html:55-67` (`:root` CSS), `:3728-3751` (`const COLOR_DEFAULTS`), `:3756-3790` (`const COLOR_HOKUSAI`) | **DRIFT RISK.** Palette hand-copied **three times**; comment at `:3725` even admits *"Defaults match the canonical [colors] block in mios.toml SSOT."* Should be theme-rendered at build. |
| H2 | `ghcr.io/mostlygeek/llama-swap:cuda` | `MIOS_LLM_LIGHT_IMAGE` / `MIOS_CUDA_IMAGE` | `usr/share/mios/knowledge/mios-knowledge-graph.json:134,178` | **DRIFT RISK.** Descriptive KG duplicates the image ref. |
| H3 | `nomic-embed-text` | `MIOS_AI_EMBED_MODEL` | `mios-knowledge-graph.json:112,141,168` | **DRIFT RISK.** |
| H4 | `http://localhost:8642/v1` (port `8642`) | `MIOS_HERMES_PORT`=`8642` **but** `MIOS_AI_ENDPOINT` resolves to `:8640` | `mios-knowledge-graph.json:6,109,139` | **DRIFT + INCONSISTENCY.** KG's `ai_endpoint` literal disagrees with the resolved `MIOS_AI_ENDPOINT`; hand-copy cannot track whichever the operator sets. |
| H5 | `qwen2.5-coder:7b` | *(stale)* SSOT `MIOS_AI_MODEL` now = `granite4.1:8b` | `mios-knowledge-graph.json:111,140,167` | **STALE HARDCODE.** No longer equals SSOT — the exact hazard this campaign removes. |
| H6 | `MIOS_LOCALAI_VERSION`, `MIOS_AI_PORT:8080`, `quay.io/ceph/ceph:v18` | *(retired / drifted)* — `LOCALAI` no longer resolved; ceph bound image is `:v19` | `mios-knowledge-graph.json:133,142,138` | **STALE HARDCODE.** References purged/retired keys. |
| — | `ghcr.io/mostlygeek/llama-swap:cuda` + `sha256:a8e56d…` | `MIOS_LLM_LIGHT_IMAGE` | `MiOS-SBOM.csv:402`, `usr/share/mios/artifacts/sbom/bound-images.tsv` | **LEGITIMATE (not a target).** Per ADR-0003 the SBOM is the *correct* surface to record the resolved ref+digest at build; excluded from de-dup. |

The `mios-knowledge-graph.json` `env` block (lines ~130-170) is effectively a second,
hand-maintained copy of a slice of `mios.toml` and has **already drifted** (H5/H6). It is
the highest-value non-color hardcode to convert to a generated projection.

## 5. Full value-duplication table (all 288 non-empty groups, sorted by count desc)

> The `unset-default` group (774 keys all = `""`) is omitted from the table for length and
> listed as row 1 of the TSV in section 7. Key lists >8 are abbreviated `(+N more)`; the
> complete membership is in the TSV.

| value | count | class | keys |
|---|---|---|---|
| `true` | 193 | distinct-configurable-fact | MIOS_A2O_LANE_B_PREFER_FALLBACK, MIOS_ACCOUNTS_DB_BACKED, MIOS_AGENTS_AI_LOCAL_HEALTH_GATE, MIOS_AGENTS_HERMES_HEALTH_GATE, MIOS_AGENTS_MIOS_DAEMON_AGENT_FANOUT, MIOS_AGENTS_MIOS_DAEMON_AGENT_HEALTH_GATE, MIOS_AGENTS_OPENCODE_ENABLED, MIOS_AGENTS_OPENCODE_FANOUT (+185 more) |
| `false` | 109 | distinct-configurable-fact | MIOS_A2A_COUNCIL, MIOS_A2A_MDNS_ADVERTISE, MIOS_A2A_MDNS_DISCOVERY, MIOS_A2A_ROUTE_ON_CARD_SKILLS, MIOS_A2O_STREAM_REASONING, MIOS_ACCOUNTS_DB_RENDER_PREFS, MIOS_ADMISSION_MULTIBLADE_ENABLE, MIOS_ADMISSION_TENANT_QUOTA_ENABLE (+101 more) |
| `2` | 22 | distinct-configurable-fact | MIOS_AGENT_PIPE_NO_PROGRESS_WINDOW, MIOS_AGENT_PIPE_REFLEXION_LIMIT, MIOS_DEV_VM_CPU_RESERVE_MIN, MIOS_DISPATCH_AUTONOMY_MAX_DISPATCH_DEPTH, MIOS_DISPATCH_DEFAULT_HOP_BUDGET, MIOS_DISPATCH_LANE_CONCURRENCY_CPU, MIOS_DISPATCH_LANE_CONCURRENCY_GPU, MIOS_DISPATCH_SWARM_MAX_CPU_NODES (+14 more) |
| `0` | 19 | distinct-configurable-fact | MIOS_ADMISSION_TENANT_MAX_CONCURRENCY, MIOS_AGENTS__DEFAULTS_TIMEOUT_S, MIOS_AI_TAG_MAX_UNCONFORMING, MIOS_COCKPIT_IDLE_TIMEOUT, MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS, MIOS_DISPATCH_KV_PAGING_SLOT, MIOS_GOSSIP_INTERVAL_MIN, MIOS_OS_CONTROL_DEFAULT_MONITOR (+11 more) |
| `3` | 19 | distinct-configurable-fact | MIOS_AGENT_PIPE_MAX_CONSECUTIVE_FAILURES, MIOS_ANTIFAB_MIN_ENTITIES, MIOS_DAEMON_ESCALATION_MAX_ATTEMPTS, MIOS_DISPATCH_AGENT_CONCURRENCY, MIOS_DISPATCH_FANOUT_MAX, MIOS_DISPATCH_LANE_CONCURRENCY, MIOS_DISPATCH_RERANK_FANOUT, MIOS_DISPATCH_SWARM_MAX_WIDTH (+11 more) |
| `mios` | 19 | distinct-configurable-fact | MIOS_AUTH_PASSWORD, MIOS_CEPHFS_TENANT_ID, MIOS_DEFAULT_HOST, MIOS_DEFAULT_PASSWORD, MIOS_DEFAULT_USER, MIOS_FIRECRAWL_BULL_KEY, MIOS_HOSTNAME, MIOS_IDENTITY_DEFAULT_PASSWORD (+11 more) |
| `latest` | 18 | distinct-configurable-fact | MIOS_ADGUARD_VERSION, MIOS_BIB_ALPINE_VERSION, MIOS_CAT_VENTOY_VERSION, MIOS_CODE_SERVER_VERSION, MIOS_CROWDSEC_VERSION, MIOS_GUACAMOLE_VERSION, MIOS_GUACD_VERSION, MIOS_HERMES_VERSION (+10 more) |
| `1` | 16 | distinct-configurable-fact | MIOS_BUDGET_AUTONOMOUS_MAX_INFLIGHT, MIOS_CONV_IMAGE_RECHUNK_FORMAT_VERSION, MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS, MIOS_DAEMON_CRON_MAX_CONCURRENT, MIOS_DISPATCH_DAG_NODE_RETRY, MIOS_DISPATCH_FANOUT_MIN, MIOS_DISPATCH_REQUEST_CANCEL_ENABLE, MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_APP (+8 more) |
| `4` | 14 | distinct-configurable-fact | MIOS_CEPHFS_MDS_CACHE_MEMORY_LIMIT_GIB, MIOS_CONV_GATEWAY_WORKER_CONCURRENCY, MIOS_DEV_VM_MEMORY_RESERVE_GB, MIOS_DISPATCH_COUNCIL_MAX, MIOS_DISPATCH_ENDPOINT_CONCURRENCY, MIOS_DISPATCH_KV_FORK_MAX_BRANCHES, MIOS_DISPATCH_LANE_CONCURRENCY_GPU0, MIOS_DISPATCH_RR_MAX_SUSPENDED (+6 more) |
| `hash` | 14 | distinct-configurable-fact | MIOS_TEMPLATES_AUTOMATION_STEP_COMMENT, MIOS_TEMPLATES_BASH_COMMENT, MIOS_TEMPLATES_BASH_TOOL_COMMENT, MIOS_TEMPLATES_BASH_VERB_COMMENT, MIOS_TEMPLATES_DRIFT_CHECK_COMMENT, MIOS_TEMPLATES_JSON_SCHEMA_COMMENT, MIOS_TEMPLATES_POWERSHELL_COMMENT, MIOS_TEMPLATES_PYTHON_MODULE_COMMENT (+6 more) |
| `8` | 10 | distinct-configurable-fact | MIOS_DISPATCH_BATCH_MAX_SIZE, MIOS_DISPATCH_FANOUT_SELECT_TIMEOUT_S, MIOS_DISPATCH_MAX_SOURCES, MIOS_FINETUNE_GRAD_ACCUM, MIOS_OS_CONTROL_TILE_GAP_PX, MIOS_PGVECTOR_POOL_MAX, MIOS_PG_POOL_MAX, MIOS_PREFLIGHT_MIN_RAM_GB (+2 more) |
| `mios-heavy` | 10 | distinct-configurable-fact | MIOS_AGENTS_HERMES_CPU_MODEL, MIOS_AGENTS_HERMES_MODEL, MIOS_AGENTS_MIOS_DAEMON_AGENT_MODEL, MIOS_NODES_LOCAL_CPU_MODEL, MIOS_NODES_LOCAL_DGPU_MODEL, MIOS_NODES_LOCAL_LLAMASWAP_MODEL, MIOS_NODES_LOCAL_SGLANG_MODEL, MIOS_NODES_LOCAL_VLLM_MODEL (+2 more) |
| `12` | 8 | distinct-configurable-fact | MIOS_AI_RAM_FLOOR_GB, MIOS_BUILD_AI_RAM_FLOOR_GB, MIOS_DISPATCH_CUA_MAX_STEPS, MIOS_DISPATCH_DEEPEN_ITERS, MIOS_DISPATCH_SLOW_LANE_TOOL_CAP, MIOS_FORGE_VERSION, MIOS_VM_WIN11_VCPUS, MIOS_WEB_RESEARCH_SLUG_MIN_LEN |
| `5` | 8 | distinct-configurable-fact | MIOS_AGENT_PIPE_QUALITY_MIN_LENGTH, MIOS_AGENT_PIPE_REPLAN_MAX, MIOS_FIND_CATEGORY_PRIORITY_AGENT_CLI, MIOS_KNOWLEDGE_HOT_THRESHOLD, MIOS_MEMORY_TOOL_RESULT_TTL_TURNS, MIOS_RELIABILITY_PASS_AND_K_DGM_COUNT, MIOS_SCHED_URGENCY_DEFAULT, MIOS_SELFIMPROVE_MIN_SAMPLES |
| `auto` | 8 | distinct-configurable-fact | MIOS_BOOTSTRAP_MODE, MIOS_COMPUTER_USE_CAPTURE_BACKEND, MIOS_COMPUTER_USE_INPUT_BACKEND, MIOS_ENHANCED_SESSION_RESOLUTION, MIOS_FINETUNE_DEVICE, MIOS_FINETUNE_LOAD_IN_4BIT, MIOS_FINETUNE_TARGET_MODULES, MIOS_POWER_UPS_PORT |
| `gpu` | 8 | distinct-configurable-fact | MIOS_AGENTS_HERMES_LANE, MIOS_AGENTS_OPENCODE_LANE, MIOS_AGENTS__DEFAULTS_LANE, MIOS_NODES_LOCAL_CPU_LANE, MIOS_NODES_LOCAL_DGPU_LANE, MIOS_NODES_LOCAL_LLAMASWAP_LANE, MIOS_NODES_LOCAL_SGLANG_LANE, MIOS_NODES_LOCAL_VLLM_LANE |
| `granite4.1:8b` | 8 | true-alias | MIOS_AGENT_PIPE_TOOL_BACKEND_MODEL, MIOS_AI_MODEL, MIOS_FINETUNE_BASE_MODEL, MIOS_FINETUNE_TEACHER_MODEL, MIOS_GATEWAY_MODEL, MIOS_HERMES_MODEL, MIOS_MODEL, MIOS_STACK_MODEL |
| `#1A407F` | 7 | distinct-configurable-fact | MIOS_ANSI_4_BLUE, MIOS_COLORS_ACCENT, MIOS_COLORS_ANSI_4_BLUE, MIOS_COLORS_INFO, MIOS_COLOR_ACCENT, MIOS_COLOR_INFO, MIOS_EDITIONS_MIOS_COLORS_ACCENT |
| `high` | 7 | distinct-configurable-fact | MIOS_A2O_LANE_B_EFFORT, MIOS_A2O_LANE_B_FALLBACK_EFFORT, MIOS_A2O_ORCH_EFFORT, MIOS_COMPLIANCE_SEVERITY_GATE, MIOS_FRONTIER_LANE_B_EFFORT, MIOS_FRONTIER_LANE_B_FALLBACK_EFFORT, MIOS_FRONTIER_ORCH_EFFORT |
| `http` | 7 | distinct-configurable-fact | MIOS_AGENTS__DEFAULTS_TRANSPORT, MIOS_CONV_GATEWAY_MODE, MIOS_DESKTOP_START_MENU_CODE_SERVER_SCHEME, MIOS_DESKTOP_START_MENU_FORGE_SCHEME, MIOS_DESKTOP_START_MENU_GUACAMOLE_WEB_SCHEME, MIOS_DESKTOP_START_MENU_HERMES_DASHBOARD_SCHEME, MIOS_DESKTOP_START_MENU_SEARXNG_SCHEME |
| `model` | 7 | distinct-configurable-fact | MIOS_DAEMON_LAUNCH_CLAIM_DETECT, MIOS_DAEMON_REFUSAL_DETECT, MIOS_DISPATCH_FANOUT_SELECT_MODE, MIOS_PGVECTOR_MEMGUARD_JUDGE_MODE, MIOS_PG_MEMGUARD_JUDGE_MODE, MIOS_PREFILTER_CONVERSATIONAL_BYPASS_MODE, MIOS_ROUTING_PREFILTER_CONVERSATIONAL_BYPASS_MODE |
| `#F35C15` | 6 | distinct-configurable-fact | MIOS_ANSI_3_YELLOW, MIOS_COLORS_ANSI_3_YELLOW, MIOS_COLORS_CURSOR, MIOS_COLORS_WARNING, MIOS_COLOR_CURSOR, MIOS_COLOR_WARNING |
| `0.0` | 6 | distinct-configurable-fact | MIOS_AGENTS__DEFAULTS_TRUST_MIN_REPUTATION, MIOS_COST_BUDGET_USD, MIOS_COST_REMOTE_USD_PER_MTOK, MIOS_COST_USD_PER_KWH, MIOS_GOSSIP_MIN_TRUST, MIOS_SELFIMPROVE_ACCEPT_MARGIN |
| `6` | 6 | distinct-configurable-fact | MIOS_DAEMON_INDEX_MAX_DEPTH, MIOS_DISPATCH_DEEPEN_JUDGE_TIMEOUT_S, MIOS_FIND_CATEGORY_PRIORITY_MIOS_SHIM, MIOS_PREFILTER_CLASSIFY_TIMEOUT_S, MIOS_ROUTING_PREFILTER_CLASSIFY_TIMEOUT_S, MIOS_WEB_RESEARCH_TOP_N |
| `60` | 6 | distinct-configurable-fact | MIOS_ADGUARD_CACHE_MIN_TTL, MIOS_DISPATCH_DEEPEN_DEADLINE_S, MIOS_DISPATCH_RERANK_RRF_K, MIOS_PLANNER_SHORT_PROMPT_CHARS, MIOS_REFINE_DISPATCH_CHARS, MIOS_SKILLS_MINE_INTERVAL_MINUTES |
| `90` | 6 | distinct-configurable-fact | MIOS_AGENTS_OPENCODE_TIMEOUT_S, MIOS_AGENT_PIPE_WALL_CLOCK_BUDGET_S, MIOS_CONV_MEMORY_COLD_RETENTION_DAYS, MIOS_DAEMON_PRESSURE_GPU_UTIL_CEIL, MIOS_KNOWLEDGE_EVICT_TTL_DAYS, MIOS_OPENCODE_TIMEOUT_S |
| `claude` | 6 | distinct-configurable-fact | MIOS_A2O_LANE_A_ENGINE, MIOS_A2O_LANE_B_FALLBACK_ENGINE, MIOS_A2O_ORCH_ENGINE, MIOS_FRONTIER_LANE_A_ENGINE, MIOS_FRONTIER_LANE_B_FALLBACK_ENGINE, MIOS_FRONTIER_ORCH_ENGINE |
| `http://localhost:\${MIOS_PORT_SGLANG}/v1` | 6 | true-alias | MIOS_AGENTS_HERMES_CPU_ENDPOINT, MIOS_AGENTS_MIOS_DAEMON_AGENT_ENDPOINT, MIOS_NODES_LOCAL_CPU_ENDPOINT, MIOS_NODES_LOCAL_DGPU_ENDPOINT, MIOS_NODES_LOCAL_LLAMASWAP_ENDPOINT, MIOS_NODES_LOCAL_SGLANG_ENDPOINT |
| `nomic-embed-text` | 6 | true-alias | MIOS_AI_EMBED_MODEL, MIOS_PGVECTOR_EMBED_MODEL, MIOS_PGVECTOR_EMB_MODEL, MIOS_PG_EMBED_MODEL, MIOS_PG_EMB_MODEL, MIOS_VERB_EMBED_MODEL |
| `#282262` | 5 | distinct-configurable-fact | MIOS_ANSI_0_BLACK, MIOS_COLORS_ANSI_0_BLACK, MIOS_COLORS_BG, MIOS_COLOR_BG, MIOS_EDITIONS_MIOS_XBOX_COLORS_ACCENT |
| `--new-window` | 5 | distinct-configurable-fact | MIOS_BROWSER_FLAGS_CHROMIUM_NEW_WINDOW, MIOS_BROWSER_FLAGS_CHROMIUM_WINDOW, MIOS_BROWSER_FLAGS_EPIPHANY_NEW_WINDOW, MIOS_BROWSER_FLAGS_EPIPHANY_WINDOW, MIOS_BROWSER_FLAGS_FIREFOX_WINDOW |
| `10` | 5 | distinct-configurable-fact | MIOS_CONV_MEMORY_COLD_ZSTD_LEVEL, MIOS_DAEMON_CLASSIFY_LIMIT_PER_MIN, MIOS_DAEMON_QUIESCENCE_WINDOW_MIN, MIOS_PLANNER_SHORT_PROMPT_WORDS, MIOS_SCHED_COMPLEXITY_CAP |
| `127.0.0.1` | 5 | distinct-configurable-fact | MIOS_COMPUTER_USE_BIND_ADDRESS, MIOS_PGVECTOR_HOST, MIOS_PG_BIND_ADDR, MIOS_PG_HOST, MIOS_TTYD_BIND |
| `20` | 5 | distinct-configurable-fact | MIOS_AGENT_PIPE_TOOL_LOOP_LIMIT, MIOS_DAEMON_REFUSAL_LIMIT_PER_MIN, MIOS_DISPATCH_DEEPEN_WEB_TIMEOUT_S, MIOS_MEMORY_COMPACTION_INTERVAL, MIOS_TERMINAL_ROWS |
| `8.0` | 5 | distinct-configurable-fact | MIOS_DAEMON_PRESSURE_LOAD_CEIL, MIOS_DISPATCH_ADMIT_MAX_WAIT, MIOS_DISPATCH_RR_QUANTUM_S, MIOS_SCHEDULER_QUANTUM_S, MIOS_SLO_INTERACTIVE_BUDGET_S |
| `80` | 5 | distinct-configurable-fact | MIOS_BRANDING_DASHBOARD_FRAME_WIDTH_COLS, MIOS_MEMORY_COMPACTION_THRESHOLD_PCT, MIOS_TERMINAL_COLS, MIOS_TERMINAL_FRAME_WIDTH, MIOS_TERMINAL_INSTALL_COLS |
| `hermes` | 5 | distinct-configurable-fact | MIOS_AGENTS_MIOS_DAEMON_AGENT_FAILOVER_AGENTS, MIOS_AGENTS_OPENCODE_FAILOVER_AGENTS, MIOS_LANES_LIGHT_TOOL_CALL_PARSER, MIOS_LANES_VLLM_TOOL_CALL_PARSER, MIOS_VLLM_TOOL_CALL_PARSER |
| `host` | 5 | distinct-configurable-fact | MIOS_PODS_MIOS_AI_NETWORK, MIOS_PODS_MIOS_SYSTEM_NETWORK, MIOS_PODS_MIOS_WEBTOOLS_NETWORK, MIOS_QUADLET_DEV_NETWORK_MODE, MIOS_WSL2_DEV_VM_QUADLET_NETWORK_MODE |
| `main` | 5 | distinct-configurable-fact | MIOS_BRANCH, MIOS_BUILD_BAKE_REFS_HYPRLAND, MIOS_GITCONFIG_INIT_DEFAULT_BRANCH, MIOS_HERMES_AGENT_REF, MIOS_OPEN_WEBUI_VERSION |
| `mios-html` | 5 | intentional-many-to-one | MIOS_FIND_ALIASES_CONFIGURATOR, MIOS_FIND_ALIASES_CUSTOMIZE, MIOS_FIND_ALIASES_MIOSCONFIG, MIOS_FIND_ALIASES_MIOS_HTML, MIOS_FIND_ALIASES_MIOS_SETTINGS |
| `mios-md` | 5 | intentional-many-to-one | MIOS_FIND_ALIASES_MARKDOWN, MIOS_FIND_ALIASES_MD, MIOS_FIND_ALIASES_NOTES, MIOS_FIND_ALIASES_PREVIEW_MD, MIOS_FIND_ALIASES_RENDER_MD |
| `mios-screenshot` | 5 | intentional-many-to-one | MIOS_FIND_ALIASES_PRTSCR, MIOS_FIND_ALIASES_SCREENCAP, MIOS_FIND_ALIASES_SCREENSHOT, MIOS_FIND_ALIASES_SCREEN_CAPTURE, MIOS_FIND_ALIASES_SNAP |
| `mios-window` | 5 | intentional-many-to-one | MIOS_FIND_ALIASES_CENTER_WINDOW, MIOS_FIND_ALIASES_FOCUS_WINDOW, MIOS_FIND_ALIASES_MOVE_WINDOW, MIOS_FIND_ALIASES_WINDOW, MIOS_FIND_ALIASES_WINDOWS_MGR |
| `openai` | 5 | distinct-configurable-fact | MIOS_NODES_LOCAL_CPU_API, MIOS_NODES_LOCAL_DGPU_API, MIOS_NODES_LOCAL_LLAMASWAP_API, MIOS_NODES_LOCAL_SGLANG_API, MIOS_NODES_LOCAL_VLLM_API |
| `#3E7765` | 4 | distinct-configurable-fact | MIOS_ANSI_2_GREEN, MIOS_COLORS_ANSI_2_GREEN, MIOS_COLORS_SUCCESS, MIOS_COLOR_SUCCESS |
| `#734F39` | 4 | distinct-configurable-fact | MIOS_ANSI_5_MAGENTA, MIOS_COLORS_ANSI_5_MAGENTA, MIOS_COLORS_EARTH, MIOS_COLOR_EARTH |
| `#948E8E` | 4 | distinct-configurable-fact | MIOS_ANSI_8_BRIGHT_BLACK, MIOS_COLORS_ANSI_8_BRIGHT_BLACK, MIOS_COLORS_MUTED, MIOS_COLOR_MUTED |
| `#B7C9D7` | 4 | distinct-configurable-fact | MIOS_ANSI_6_CYAN, MIOS_COLORS_ANSI_6_CYAN, MIOS_COLORS_SUBTLE, MIOS_COLOR_SUBTLE |
| `#DC271B` | 4 | distinct-configurable-fact | MIOS_ANSI_1_RED, MIOS_COLORS_ANSI_1_RED, MIOS_COLORS_ERROR, MIOS_COLOR_ERROR |
| `#E0E0E0` | 4 | distinct-configurable-fact | MIOS_ANSI_14_BRIGHT_CYAN, MIOS_COLORS_ANSI_14_BRIGHT_CYAN, MIOS_COLORS_SILVER, MIOS_COLOR_SILVER |
| `#E7DFD3` | 4 | distinct-configurable-fact | MIOS_ANSI_7_WHITE, MIOS_COLORS_ANSI_7_WHITE, MIOS_COLORS_FG, MIOS_COLOR_FG |
| `0000:01:00.0` | 4 | true-alias | MIOS_EDITIONS_MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST, MIOS_EDITIONS_MIOS_XBOX_ARM_MINI_GPU_ASSIGNMENTS_MIOS_GUEST, MIOS_EDITIONS_MIOS_XBOX_MINI_GPU_ASSIGNMENTS_MIOS_GUEST, MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST |
| `10.89.0.0/24` | 4 | true-alias | MIOS_CORE_NET_SUBNET, MIOS_NETWORK_QUADLET_CORE_SUBNET, MIOS_NETWORK_QUADLET_SUBNET, MIOS_QUADLET_SUBNET |
| `15` | 4 | distinct-configurable-fact | MIOS_AGENT_PIPE_TOOL_MAX_ITERS, MIOS_DAEMON_INDEX_INTERVAL_MIN, MIOS_DEV_VM_CPU_RESERVE_PCT, MIOS_DEV_VM_MEMORY_RESERVE_PCT |
| `24` | 4 | distinct-configurable-fact | MIOS_APPEARANCE_CURSOR_SIZE, MIOS_DISPATCH_RERANK_MIN_K, MIOS_FINETUNE_MIN_EXAMPLES, MIOS_REFINE_BYPASS_CHARS |
| `300` | 4 | distinct-configurable-fact | MIOS_A2A_MDNS_REFRESH_SEC, MIOS_DAEMON_CALM_MAX_TICK_S, MIOS_GATEWAY_MCP_REFRESH_SECONDS, MIOS_GATEWAY_SKILL_REFRESH_SECONDS |
| `45` | 4 | distinct-configurable-fact | MIOS_POLISH_TIMEOUT_S, MIOS_POLISH_TIMEOUT_SECONDS, MIOS_REFINE_TIMEOUT_S, MIOS_REFINE_TIMEOUT_SECONDS |
| `600` | 4 | distinct-configurable-fact | MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S, MIOS_DAEMON_CLASSIFY_DEDUP_S, MIOS_DISPATCH_TURN_DEADLINE_S, MIOS_STORAGE_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S |
| `7` | 4 | distinct-configurable-fact | MIOS_FIND_CATEGORY_PRIORITY_SERVICE_URL, MIOS_FORGE_RUNNER_VERSION, MIOS_PGVECTOR_BACKUP_KEEP, MIOS_PG_BACKUP_KEEP |
| `816` | 4 | distinct-configurable-fact | MIOS_FORGE_GID, MIOS_FORGE_UID, MIOS_SERVICES_FORGE_GID, MIOS_SERVICES_FORGE_UID |
| `817` | 4 | distinct-configurable-fact | MIOS_OPEN_WEBUI_GID, MIOS_OPEN_WEBUI_UID, MIOS_SERVICES_OPEN_WEBUI_GID, MIOS_SERVICES_OPEN_WEBUI_UID |
| `818` | 4 | distinct-configurable-fact | MIOS_SEARXNG_GID, MIOS_SEARXNG_UID, MIOS_SERVICES_SEARXNG_GID, MIOS_SERVICES_SEARXNG_UID |
| `819` | 4 | distinct-configurable-fact | MIOS_CEPH_GID, MIOS_CEPH_UID, MIOS_SERVICES_CEPH_GID, MIOS_SERVICES_CEPH_UID |
| `820` | 4 | distinct-configurable-fact | MIOS_HERMES_GID, MIOS_HERMES_UID, MIOS_SERVICES_HERMES_GID, MIOS_SERVICES_HERMES_UID |
| `822` | 4 | distinct-configurable-fact | MIOS_AGENT_PIPE_GID, MIOS_AGENT_PIPE_UID, MIOS_SERVICES_AGENT_PIPE_GID, MIOS_SERVICES_AGENT_PIPE_UID |
| `824` | 4 | distinct-configurable-fact | MIOS_SERVICES_WEBTOOLS_GID, MIOS_SERVICES_WEBTOOLS_UID, MIOS_WEBTOOLS_GID, MIOS_WEBTOOLS_UID |
| `825` | 4 | distinct-configurable-fact | MIOS_ADGUARD_GID, MIOS_ADGUARD_UID, MIOS_SERVICES_ADGUARD_GID, MIOS_SERVICES_ADGUARD_UID |
| `826` | 4 | distinct-configurable-fact | MIOS_PGVECTOR_GID, MIOS_PGVECTOR_UID, MIOS_SERVICES_PGVECTOR_GID, MIOS_SERVICES_PGVECTOR_UID |
| `827` | 4 | distinct-configurable-fact | MIOS_LLAMACPP_GID, MIOS_LLAMACPP_UID, MIOS_SERVICES_LLAMACPP_GID, MIOS_SERVICES_LLAMACPP_UID |
| `828` | 4 | distinct-configurable-fact | MIOS_CODEMODE_GID, MIOS_CODEMODE_UID, MIOS_CODE_MODE_GID, MIOS_CODE_MODE_UID |
| `8642` | 4 | distinct-configurable-fact | MIOS_GATEWAY_PORT, MIOS_HERMES_PORT, MIOS_PORTS_HERMES, MIOS_PORT_HERMES |
| `MiOS` | 4 | distinct-configurable-fact | MIOS_APPS_HUB_SHORTCUT_NAME, MIOS_APPS_START_MENU_FOLDER, MIOS_DEVELOPER, MIOS_WSL_DISTRO |
| `claude-sonnet-5` | 4 | true-alias | MIOS_A2O_LANE_B_FALLBACK_MODEL, MIOS_A2O_ORCH_MODEL, MIOS_FRONTIER_LANE_B_FALLBACK_MODEL, MIOS_FRONTIER_ORCH_MODEL |
| `http://localhost:\${MIOS_PORT_LLM_LIGHT}` | 4 | distinct-configurable-fact | MIOS_FINETUNE_TEACHER_ENDPOINT, MIOS_HERMES_BACKEND, MIOS_POLISH_ENDPOINT, MIOS_REFINE_ENDPOINT |
| `max` | 4 | distinct-configurable-fact | MIOS_DEV_VM_CPUS, MIOS_DEV_VM_DISK_GB, MIOS_DEV_VM_GPU, MIOS_DEV_VM_MEMORY_MB |
| `md` | 4 | distinct-configurable-fact | MIOS_TEMPLATES_ADR_COMMENT, MIOS_TEMPLATES_MARKDOWN_DOC_COMMENT, MIOS_TEMPLATES_ROADMAP_COMMENT, MIOS_TEMPLATES_ROADMAP_WS_COMMENT |
| `mios-installer` | 4 | intentional-many-to-one | MIOS_FIND_ALIASES_INSTALL, MIOS_FIND_ALIASES_INSTALLER, MIOS_FIND_ALIASES_PACKAGE, MIOS_FIND_ALIASES_WINGET |
| `mios-steamcmd` | 4 | intentional-many-to-one | MIOS_FIND_ALIASES_STEAMCMD, MIOS_FIND_ALIASES_STEAM_CMD, MIOS_FIND_ALIASES_STEAM_GAME, MIOS_FIND_ALIASES_STEAM_INSTALL |
| `network-online.target` | 4 | distinct-configurable-fact | MIOS_PODS_MIOS_AI_AFTER, MIOS_PODS_MIOS_AI_WANTS, MIOS_PODS_MIOS_SYSTEM_AFTER, MIOS_PODS_MIOS_SYSTEM_WANTS |
| `reasoning` | 4 | distinct-configurable-fact | MIOS_AGENTS_MIOS_DAEMON_AGENT_ROLE, MIOS_OBSERVABILITY_CHANNELS_PLAN, MIOS_OBSERVABILITY_CHANNELS_THINKING, MIOS_OBSERVABILITY_CHANNELS_TOOL_RESULT |
| `static` | 4 | true-alias | MIOS_EDITIONS_MIOS_METAL_GPU_ARBITRATION, MIOS_EDITIONS_MIOS_XBOX_ARM_MINI_GPU_ARBITRATION, MIOS_EDITIONS_MIOS_XBOX_MINI_GPU_ARBITRATION, MIOS_METAL_GPU_ARBITRATION |
| `window_visible` | 4 | distinct-configurable-fact | MIOS_DAEMON_POST_CHECK_FOCUS_WINDOW, MIOS_DAEMON_POST_CHECK_LAUNCH_APP, MIOS_DAEMON_POST_CHECK_OPEN_APP, MIOS_DAEMON_POST_CHECK_OPEN_URL |
| `/bin/bash` | 3 | true-alias | MIOS_DEFAULT_SHELL, MIOS_IDENTITY_SHELL, MIOS_USER_SHELL |
| `0.05` | 3 | distinct-configurable-fact | MIOS_DISPATCH_BATCH_INTERVAL_S, MIOS_FINETUNE_LORA_DROPOUT, MIOS_KNOWLEDGE_RANK_OUTCOME |
| `0.34` | 3 | distinct-configurable-fact | MIOS_ANTIFAB_GROUND_MIN, MIOS_FIND_RANKER_FUZZY_MAX_EDIT_RATIO, MIOS_VERITY_ANTIFAB_GROUND_MIN |
| `0.85` | 3 | distinct-configurable-fact | MIOS_SGLANG_MEM_FRACTION, MIOS_SKILLS_AUTO_PROMOTE_THRESHOLD, MIOS_VLLM_GPU_UTIL |
| `14` | 3 | distinct-configurable-fact | MIOS_CPU_NODE_THREADS, MIOS_LLAMACPP_CPU_NODE_THREADS, MIOS_TTYD_FONT_SIZE |
| `16` | 3 | distinct-configurable-fact | MIOS_DISPATCH_DEFAULT_TOOL_CAP, MIOS_DISPATCH_GLOBAL_CONCURRENCY, MIOS_FINETUNE_LORA_R |
| `200` | 3 | distinct-configurable-fact | MIOS_CRAWL_MIN_CHARS, MIOS_PKG_BOOTSTRAP_PER_SOURCE_CAP, MIOS_SERVICES_WEBTOOLS_MIN_CHARS |
| `30` | 3 | distinct-configurable-fact | MIOS_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL, MIOS_GATEWAY_MAX_STEPS, MIOS_STORAGE_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL |
| `40` | 3 | distinct-configurable-fact | MIOS_BUILD_BAKE_RUNNER_DISK_BUDGET_GB, MIOS_REFINE_CHAT_CHARS, MIOS_TERMINAL_INSTALL_ROWS |
| `50` | 3 | distinct-configurable-fact | MIOS_PGVECTOR_BACKFILL_BATCH, MIOS_PG_BACKFILL_BATCH, MIOS_TERMINAL_READING_ROWS |
| `512` | 3 | distinct-configurable-fact | MIOS_CAT_DATA_PARTITION_MIN_DISK_GB, MIOS_DISPATCH_LLM_NUM_PREDICT_CAP_CPU, MIOS_DISPATCH_RR_SLICE_TOKENS |
| `64` | 3 | distinct-configurable-fact | MIOS_CONV_GATEWAY_QUEUE_MAXSIZE, MIOS_DISPATCH_SOURCES_REGISTRY_CAP, MIOS_SCHEDULER_QUEUE_MAX_TURNS |
| `7.0` | 3 | distinct-configurable-fact | MIOS_KNOWLEDGE_RECALL_HALFLIFE_DAYS, MIOS_SLO_DEFAULT_PRIORITY, MIOS_SLO_INTERACTIVE_PRIORITY |
| `8000` | 3 | distinct-configurable-fact | MIOS_CODEMODE_MAX_OUTPUT_CHARS, MIOS_CODE_MODE_MAX_OUTPUT_CHARS, MIOS_MEMORY_N_CTX |
| `8090` | 3 | distinct-configurable-fact | MIOS_COCKPIT_PORT, MIOS_PORTS_COCKPIT, MIOS_PORT_COCKPIT |
| `8300` | 3 | distinct-configurable-fact | MIOS_FORGE_HTTP_PORT, MIOS_PORTS_FORGE_HTTP, MIOS_PORT_FORGE_HTTP |
| `8301` | 3 | distinct-configurable-fact | MIOS_FORGE_SSH_PORT, MIOS_PORTS_FORGE_SSH, MIOS_PORT_FORGE_SSH |
| `8640` | 3 | distinct-configurable-fact | MIOS_A2A_DISCOVER_PORT, MIOS_PORTS_AGENT_PIPE, MIOS_PORT_AGENT_PIPE |
| `8899` | 3 | distinct-configurable-fact | MIOS_PORTS_SEARXNG, MIOS_PORT_SEARXNG, MIOS_SEARXNG_PORT |
| `UTC` | 3 | distinct-configurable-fact | MIOS_DEFAULT_TIMEZONE, MIOS_LOCALE_TIMEZONE, MIOS_TIMEZONE |
| `cuda` | 3 | distinct-configurable-fact | MIOS_BUILD_BAKE_GROUP_MEMBERS_CUDA, MIOS_CUDA_VERSION, MIOS_LLM_LIGHT_VERSION |
| `en_US.UTF-8` | 3 | distinct-configurable-fact | MIOS_DEFAULT_LOCALE, MIOS_LOCALE, MIOS_LOCALE_LANGUAGE |
| `log` | 3 | distinct-configurable-fact | MIOS_HITL_MODE, MIOS_PGVECTOR_MEMORY_GUARD_MODE, MIOS_PG_MEMORY_GUARD_MODE |
| `multi-user.target,default.target` | 3 | true-alias | MIOS_PODS_MIOS_AI_WANTED_BY, MIOS_PODS_MIOS_SYSTEM_WANTED_BY, MIOS_PODS_MIOS_WEBTOOLS_WANTED_BY |
| `prefer-dark` | 3 | true-alias | MIOS_APPEARANCE_ADW_COLOR_SCHEME, MIOS_COLOR_SCHEME, MIOS_DESKTOP_COLOR_SCHEME |
| `qwen3` | 3 | true-alias | MIOS_LANES_LIGHT_REASONING_PARSER, MIOS_LANES_SGLANG_REASONING_PARSER, MIOS_LANES_VLLM_REASONING_PARSER |
| `us` | 3 | distinct-configurable-fact | MIOS_DEFAULT_KEYBOARD, MIOS_KEYBOARD, MIOS_LOCALE_KEYBOARD_LAYOUT |
| `wheel,libvirt,kvm,video,render,input,dialout,…` | 3 | true-alias | MIOS_DEFAULT_GROUPS, MIOS_IDENTITY_GROUPS, MIOS_USER_GROUPS |
| `x11` | 3 | true-alias | MIOS_GRAPHICS_GDK_BACKEND, MIOS_WSL2_DESKTOP_COMPAT_GDK_BACKEND, MIOS_WSLG_GDK_BACKEND |
| `#3D6BA8` | 2 | true-alias | MIOS_ANSI_12_BRIGHT_BLUE, MIOS_COLORS_ANSI_12_BRIGHT_BLUE |
| `#5FAA8E` | 2 | true-alias | MIOS_ANSI_10_BRIGHT_GREEN, MIOS_COLORS_ANSI_10_BRIGHT_GREEN |
| `#9D7660` | 2 | true-alias | MIOS_ANSI_13_BRIGHT_MAGENTA, MIOS_COLORS_ANSI_13_BRIGHT_MAGENTA |
| `#FF6B5C` | 2 | true-alias | MIOS_ANSI_9_BRIGHT_RED, MIOS_COLORS_ANSI_9_BRIGHT_RED |
| `#FF8540` | 2 | true-alias | MIOS_ANSI_11_BRIGHT_YELLOW, MIOS_COLORS_ANSI_11_BRIGHT_YELLOW |
| `#FFFFFF` | 2 | true-alias | MIOS_ANSI_15_BRIGHT_WHITE, MIOS_COLORS_ANSI_15_BRIGHT_WHITE |
| `--effort {e}` | 2 | true-alias | MIOS_A2O_CLAUDE_EFFORT_FLAG, MIOS_FRONTIER_CLAUDE_EFFORT_FLAG |
| `--new-tab` | 2 | distinct-configurable-fact | MIOS_BROWSER_FLAGS_EPIPHANY_TAB, MIOS_BROWSER_FLAGS_FIREFOX_TAB |
| `/etc/ceph/keyring.d` | 2 | true-alias | MIOS_CEPHFS_KEYRING_DIR, MIOS_STORAGE_CEPHFS_KEYRING_DIR |
| `/etc/mios/install.env` | 2 | true-alias | MIOS_INSTALL_ENV, MIOS_PATHS_INSTALL_ENV |
| `/etc/mios/profile.toml` | 2 | true-alias | MIOS_PATHS_PROFILE_TOML_HOST, MIOS_PROFILE_TOML_HOST |
| `/mnt/c/Windows/System32/WindowsPowerShell/v1.…` | 2 | true-alias | MIOS_PATHS_POWERSHELL_EXE, MIOS_POWERSHELL_EXE |
| `/mnt/c/Windows/System32/cmd.exe` | 2 | true-alias | MIOS_CMD_EXE, MIOS_PATHS_CMD_EXE |
| `/usr/share/mios/*` FHS paths | 24 | true-alias | `MIOS_AI_DIR`, `MIOS_PATHS_AI_DIR`, `MIOS_PATHS_MIOS_TOML`, `MIOS_TOML` |
| `/var/lib/mios/*` state paths | 28 | true-alias | `MIOS_AI_MEMORY_DIR`, `MIOS_PATHS_AI_MEMORY_DIR`, `MIOS_PGVECTOR_DATA_DIR`, `MIOS_PG_DATA_DIR` |
| Port bindings (`8033`..`8800`) | 42 | true-alias | `MIOS_PORTS_OPEN_WEBUI`, `MIOS_PORT_OPEN_WEBUI`, `MIOS_PORTS_LLM_LIGHT`, `MIOS_PORT_LLM_LIGHT` |
| Service accounts (`mios-*`) | 32 | true-alias | `MIOS_PGVECTOR_USER`, `MIOS_SERVICES_PGVECTOR_USER`, `MIOS_HERMES_USER`, `MIOS_SERVICES_HERMES_USER` |
| Storage & CephFS params | 16 | true-alias | `MIOS_CEPHFS_CLUSTER_NAME`, `MIOS_STORAGE_CEPHFS_CLUSTER_NAME`, `MIOS_CEPHFS_FS_NAME` |
| Numerical defaults (`100`..`20000`) | 38 | distinct-configurable-fact | `MIOS_REFINE_PROMOTE_CHARS`, `MIOS_TERMINAL_READING_COLS`, `MIOS_FINETUNE_MAX_SEQ_LEN` |

## 6. Drop-in artifact — alias-drift drift-gate + canonical map

Two pieces the campaign lands together: (a) a canonical-spelling map that *declares* which
member of each alias family is the SSOT key, and (b) a drift-check that fails CI if any
declared alias pair diverges (so the section-4.1 empties and future drift are caught).

### 6a. `usr/share/mios/value-aliases.tsv` (campaign SSOT for canonicalization)

```tsv
# canonical<TAB>alias<TAB>disposition   (disposition: derive|delete|keep-distinct)
# --- family 2: SERVICES_<svc>_ = <svc>_ (identity) -----------------------------
MIOS_SERVICES_FORGE_UID	MIOS_FORGE_UID	derive
MIOS_SERVICES_FORGE_GID	MIOS_FORGE_GID	derive
MIOS_SERVICES_FORGE_USER	MIOS_FORGE_USER	derive
# ... (repeat for open_webui, searxng, ceph, hermes, agent_pipe, webtools, adguard,
#      pgvector, llamacpp, codemode — 30 pairs total, generated from section 3 row 2)
# --- family 1/4.2: ports — pick the [ports]-native plural as canonical ----------
MIOS_PORTS_COCKPIT	MIOS_PORT_COCKPIT	derive
MIOS_PORTS_COCKPIT	MIOS_COCKPIT_PORT	derive
MIOS_PORTS_CEPH_DASHBOARD	MIOS_PORT_CEPH_DASHBOARD	derive   # fills the empty singular
# --- family 3: PGVECTOR_ = PG_ — MOSTLY derive, but USER is keep-distinct -------
MIOS_PGVECTOR_DATA_DIR	MIOS_PG_DATA_DIR	derive
MIOS_PGVECTOR_USER	MIOS_PG_USER	keep-distinct   # mios-pgvector != mios (role)
# --- family 6: A2O_ = FRONTIER_ (recommend FRONTIER_ canonical per stream path) -
MIOS_FRONTIER_STREAM_PATH	MIOS_A2O_STREAM_PATH	derive
# ... full generated list from section 3 / section 7 TSV
```

### 6b. `usr/libexec/mios/mios-check-value-aliases` (new drift-check, gate ~47)

```bash
#!/usr/bin/env bash
# AI-hint: Drift-gate — every declared alias pair in value-aliases.tsv must resolve to the
#          SAME value (except disposition=keep-distinct); prevents silent SSOT divergence.
# AI-related: usr/share/mios/value-aliases.tsv, usr/libexec/mios/mios-env-snapshot
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MAP="${ROOT}/usr/share/mios/value-aliases.tsv"
SNAP="$(mktemp)"; trap 'rm -f "$SNAP"' EXIT
bash "${ROOT}/usr/libexec/mios/mios-env-snapshot" > "$SNAP"
val() { grep -m1 "^$1=" "$SNAP" | cut -d= -f2- ; }   # empty if unset
rc=0
while IFS=$'\t' read -r canon alias disp; do
  [[ "$canon" =~ ^#|^$ ]] && continue
  cv="$(val "$canon")"; av="$(val "$alias")"
  case "$disp" in
    keep-distinct) [[ "$cv" == "$av" ]] && { echo "WARN: $canon and $alias marked keep-distinct but are EQUAL ($cv)"; } ;;
    derive|delete)
      if [[ "$cv" != "$av" ]]; then
        echo "DRIFT: $canon='$cv'  !=  $alias='$av'  (disposition=$disp)"; rc=1
      fi ;;
  esac
done < "$MAP"
[[ $rc -eq 0 ]] && echo "OK: all derive/delete alias pairs agree"
exit $rc
```

Wire it into the drift-check registry the same way gates 25/46 are registered, and add its
number to `mios.toml [laws]`/checks numbering. Run against the current tree it immediately
reports the five section-4.1 drifts — turning this audit into an enforced invariant.

## 7. Exhaustive TSV (machine-readable — feeds AGY tooling)

`value<TAB>count<TAB>class<TAB>keys` for **all 289 groups** (row 1 = the 774-key
`unset-default` group; key lists capped at 20 members for the coincidental mega-groups —
every `true-alias` / `intentional-many-t```tsv
value	count	class	keys
(EMPTY)	774	unset-default	MIOS_A2A_*;MIOS_A2O_*;MIOS_ADMIT_*;MIOS_AGENT_*;...(+754 more)
true	193	distinct-configurable-fact	MIOS_A2O_LANE_B_PREFER_FALLBACK;MIOS_ACCOUNTS_DB_BACKED;MIOS_AGENTS_AI_LOCAL_HEALTH_GATE;...(+173 more)
false	109	distinct-configurable-fact	MIOS_A2A_COUNCIL;MIOS_A2A_MDNS_ADVERTISE;MIOS_A2A_MDNS_DISCOVERY;...(+89 more)
2	22	distinct-configurable-fact	MIOS_AGENT_PIPE_NO_PROGRESS_WINDOW;MIOS_AGENT_PIPE_REFLEXION_LIMIT;...(+20 more)
0	19	distinct-configurable-fact	MIOS_ADMISSION_TENANT_MAX_CONCURRENCY;MIOS_AGENTS__DEFAULTS_TIMEOUT_S;...(+17 more)
3	19	distinct-configurable-fact	MIOS_AGENT_PIPE_MAX_CONSECUTIVE_FAILURES;MIOS_ANTIFAB_MIN_ENTITIES;...(+17 more)
mios	19	distinct-configurable-fact	MIOS_AUTH_PASSWORD;MIOS_CEPHFS_TENANT_ID;MIOS_DEFAULT_HOST;...(+16 more)
latest	18	distinct-configurable-fact	MIOS_ADGUARD_VERSION;MIOS_BIB_ALPINE_VERSION;MIOS_CAT_VENTOY_VERSION;...(+15 more)
1	16	distinct-configurable-fact	MIOS_BUDGET_AUTONOMOUS_MAX_INFLIGHT;MIOS_CONV_IMAGE_RECHUNK_FORMAT_VERSION;...(+14 more)
4	14	distinct-configurable-fact	MIOS_CEPHFS_MDS_CACHE_MEMORY_LIMIT_GIB;MIOS_CONV_GATEWAY_WORKER_CONCURRENCY;...(+12 more)
hash	14	distinct-configurable-fact	MIOS_TEMPLATES_AUTOMATION_STEP_COMMENT;MIOS_TEMPLATES_BASH_COMMENT;...(+12 more)
8	10	distinct-configurable-fact	MIOS_DISPATCH_BATCH_MAX_SIZE;MIOS_DISPATCH_FANOUT_SELECT_TIMEOUT_S;...(+8 more)
mios-heavy	10	distinct-configurable-fact	MIOS_AGENTS_HERMES_CPU_MODEL;MIOS_AGENTS_HERMES_MODEL;...(+8 more)
granite4.1:8b	8	true-alias	MIOS_AGENT_PIPE_TOOL_BACKEND_MODEL;MIOS_AI_MODEL;MIOS_FINETUNE_BASE_MODEL;...(+6 more)
nomic-embed-text	6	true-alias	MIOS_AI_EMBED_MODEL;MIOS_PGVECTOR_EMBED_MODEL;MIOS_PGVECTOR_EMB_MODEL;...(+3 more)
```GHT_CYAN;MIOS_COLORS_SILVER;MIOS_COLOR_SILVER
#E7DFD3	4	distinct-configurable-fact	MIOS_ANSI_7_WHITE;MIOS_COLORS_ANSI_7_WHITE;MIOS_COLORS_FG;MIOS_COLOR_FG
0000:01:00.0	4	true-alias	MIOS_EDITIONS_MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST;MIOS_EDITIONS_MIOS_XBOX_ARM_MINI_GPU_ASSIGNMENTS_MIOS_GUEST;MIOS_EDITIONS_MIOS_XBOX_MINI_GPU_ASSIGNMENTS_MIOS_GUEST;MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST
10.89.0.0/24	4	true-alias	MIOS_CORE_NET_SUBNET;MIOS_NETWORK_QUADLET_CORE_SUBNET;MIOS_NETWORK_QUADLET_SUBNET;MIOS_QUADLET_SUBNET
15	4	distinct-configurable-fact	MIOS_AGENT_PIPE_TOOL_MAX_ITERS;MIOS_DAEMON_INDEX_INTERVAL_MIN;MIOS_DEV_VM_CPU_RESERVE_PCT;MIOS_DEV_VM_MEMORY_RESERVE_PCT
24	4	distinct-configurable-fact	MIOS_APPEARANCE_CURSOR_SIZE;MIOS_DISPATCH_RERANK_MIN_K;MIOS_FINETUNE_MIN_EXAMPLES;MIOS_REFINE_BYPASS_CHARS
300	4	distinct-configurable-fact	MIOS_A2A_MDNS_REFRESH_SEC;MIOS_DAEMON_CALM_MAX_TICK_S;MIOS_GATEWAY_MCP_REFRESH_SECONDS;MIOS_GATEWAY_SKILL_REFRESH_SECONDS
45	4	distinct-configurable-fact	MIOS_POLISH_TIMEOUT_S;MIOS_POLISH_TIMEOUT_SECONDS;MIOS_REFINE_TIMEOUT_S;MIOS_REFINE_TIMEOUT_SECONDS
600	4	distinct-configurable-fact	MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S;MIOS_DAEMON_CLASSIFY_DEDUP_S;MIOS_DISPATCH_TURN_DEADLINE_S;MIOS_STORAGE_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S
7	4	distinct-configurable-fact	MIOS_FIND_CATEGORY_PRIORITY_SERVICE_URL;MIOS_FORGE_RUNNER_VERSION;MIOS_PGVECTOR_BACKUP_KEEP;MIOS_PG_BACKUP_KEEP
816	4	distinct-configurable-fact	MIOS_FORGE_GID;MIOS_FORGE_UID;MIOS_SERVICES_FORGE_GID;MIOS_SERVICES_FORGE_UID
817	4	distinct-configurable-fact	MIOS_OPEN_WEBUI_GID;MIOS_OPEN_WEBUI_UID;MIOS_SERVICES_OPEN_WEBUI_GID;MIOS_SERVICES_OPEN_WEBUI_UID
818	4	distinct-configurable-fact	MIOS_SEARXNG_GID;MIOS_SEARXNG_UID;MIOS_SERVICES_SEARXNG_GID;MIOS_SERVICES_SEARXNG_UID
819	4	distinct-configurable-fact	MIOS_CEPH_GID;MIOS_CEPH_UID;MIOS_SERVICES_CEPH_GID;MIOS_SERVICES_CEPH_UID
820	4	distinct-configurable-fact	MIOS_HERMES_GID;MIOS_HERMES_UID;MIOS_SERVICES_HERMES_GID;MIOS_SERVICES_HERMES_UID
822	4	distinct-configurable-fact	MIOS_AGENT_PIPE_GID;MIOS_AGENT_PIPE_UID;MIOS_SERVICES_AGENT_PIPE_GID;MIOS_SERVICES_AGENT_PIPE_UID
824	4	distinct-configurable-fact	MIOS_SERVICES_WEBTOOLS_GID;MIOS_SERVICES_WEBTOOLS_UID;MIOS_WEBTOOLS_GID;MIOS_WEBTOOLS_UID
825	4	distinct-configurable-fact	MIOS_ADGUARD_GID;MIOS_ADGUARD_UID;MIOS_SERVICES_ADGUARD_GID;MIOS_SERVICES_ADGUARD_UID
826	4	distinct-configurable-fact	MIOS_PGVECTOR_GID;MIOS_PGVECTOR_UID;MIOS_SERVICES_PGVECTOR_GID;MIOS_SERVICES_PGVECTOR_UID
827	4	distinct-configurable-fact	MIOS_LLAMACPP_GID;MIOS_LLAMACPP_UID;MIOS_SERVICES_LLAMACPP_GID;MIOS_SERVICES_LLAMACPP_UID
828	4	distinct-configurable-fact	MIOS_CODEMODE_GID;MIOS_CODEMODE_UID;MIOS_CODE_MODE_GID;MIOS_CODE_MODE_UID
8642	4	distinct-configurable-fact	MIOS_GATEWAY_PORT;MIOS_HERMES_PORT;MIOS_PORTS_HERMES;MIOS_PORT_HERMES
MiOS	4	distinct-configurable-fact	MIOS_APPS_HUB_SHORTCUT_NAME;MIOS_APPS_START_MENU_FOLDER;MIOS_DEVELOPER;MIOS_WSL_DISTRO
claude-sonnet-5	4	true-alias	MIOS_A2O_LANE_B_FALLBACK_MODEL;MIOS_A2O_ORCH_MODEL;MIOS_FRONTIER_LANE_B_FALLBACK_MODEL;MIOS_FRONTIER_ORCH_MODEL
http://localhost:${MIOS_PORT_LLM_LIGHT}	4	distinct-configurable-fact	MIOS_FINETUNE_TEACHER_ENDPOINT;MIOS_HERMES_BACKEND;MIOS_POLISH_ENDPOINT;MIOS_REFINE_ENDPOINT
max	4	distinct-configurable-fact	MIOS_DEV_VM_CPUS;MIOS_DEV_VM_DISK_GB;MIOS_DEV_VM_GPU;MIOS_DEV_VM_MEMORY_MB
md	4	distinct-configurable-fact	MIOS_TEMPLATES_ADR_COMMENT;MIOS_TEMPLATES_MARKDOWN_DOC_COMMENT;MIOS_TEMPLATES_ROADMAP_COMMENT;MIOS_TEMPLATES_ROADMAP_WS_COMMENT
mios-installer	4	intentional-many-to-one	MIOS_FIND_ALIASES_INSTALL;MIOS_FIND_ALIASES_INSTALLER;MIOS_FIND_ALIASES_PACKAGE;MIOS_FIND_ALIASES_WINGET
mios-steamcmd	4	intentional-many-to-one	MIOS_FIND_ALIASES_STEAMCMD;MIOS_FIND_ALIASES_STEAM_CMD;MIOS_FIND_ALIASES_STEAM_GAME;MIOS_FIND_ALIASES_STEAM_INSTALL
network-online.target	4	distinct-configurable-fact	MIOS_PODS_MIOS_AI_AFTER;MIOS_PODS_MIOS_AI_WANTS;MIOS_PODS_MIOS_SYSTEM_AFTER;MIOS_PODS_MIOS_SYSTEM_WANTS
reasoning	4	distinct-configurable-fact	MIOS_AGENTS_MIOS_DAEMON_AGENT_ROLE;MIOS_OBSERVABILITY_CHANNELS_PLAN;MIOS_OBSERVABILITY_CHANNELS_THINKING;MIOS_OBSERVABILITY_CHANNELS_TOOL_RESULT
static	4	true-alias	MIOS_EDITIONS_MIOS_METAL_GPU_ARBITRATION;MIOS_EDITIONS_MIOS_XBOX_ARM_MINI_GPU_ARBITRATION;MIOS_EDITIONS_MIOS_XBOX_MINI_GPU_ARBITRATION;MIOS_METAL_GPU_ARBITRATION
window_visible	4	distinct-configurable-fact	MIOS_DAEMON_POST_CHECK_FOCUS_WINDOW;MIOS_DAEMON_POST_CHECK_LAUNCH_APP;MIOS_DAEMON_POST_CHECK_OPEN_APP;MIOS_DAEMON_POST_CHECK_OPEN_URL
/bin/bash	3	true-alias	MIOS_DEFAULT_SHELL;MIOS_IDENTITY_SHELL;MIOS_USER_SHELL
0.05	3	distinct-configurable-fact	MIOS_DISPATCH_BATCH_INTERVAL_S;MIOS_FINETUNE_LORA_DROPOUT;MIOS_KNOWLEDGE_RANK_OUTCOME
0.34	3	distinct-configurable-fact	MIOS_ANTIFAB_GROUND_MIN;MIOS_FIND_RANKER_FUZZY_MAX_EDIT_RATIO;MIOS_VERITY_ANTIFAB_GROUND_MIN
0.85	3	distinct-configurable-fact	MIOS_SGLANG_MEM_FRACTION;MIOS_SKILLS_AUTO_PROMOTE_THRESHOLD;MIOS_VLLM_GPU_UTIL
14	3	distinct-configurable-fact	MIOS_CPU_NODE_THREADS;MIOS_LLAMACPP_CPU_NODE_THREADS;MIOS_TTYD_FONT_SIZE
16	3	distinct-configurable-fact	MIOS_DISPATCH_DEFAULT_TOOL_CAP;MIOS_DISPATCH_GLOBAL_CONCURRENCY;MIOS_FINETUNE_LORA_R
200	3	distinct-configurable-fact	MIOS_CRAWL_MIN_CHARS;MIOS_PKG_BOOTSTRAP_PER_SOURCE_CAP;MIOS_SERVICES_WEBTOOLS_MIN_CHARS
30	3	distinct-configurable-fact	MIOS_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL;MIOS_GATEWAY_MAX_STEPS;MIOS_STORAGE_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL
40	3	distinct-configurable-fact	MIOS_BUILD_BAKE_RUNNER_DISK_BUDGET_GB;MIOS_REFINE_CHAT_CHARS;MIOS_TERMINAL_INSTALL_ROWS
50	3	distinct-configurable-fact	MIOS_PGVECTOR_BACKFILL_BATCH;MIOS_PG_BACKFILL_BATCH;MIOS_TERMINAL_READING_ROWS
512	3	distinct-configurable-fact	MIOS_CAT_DATA_PARTITION_MIN_DISK_GB;MIOS_DISPATCH_LLM_NUM_PREDICT_CAP_CPU;MIOS_DISPATCH_RR_SLICE_TOKENS
64	3	distinct-configurable-fact	MIOS_CONV_GATEWAY_QUEUE_MAXSIZE;MIOS_DISPATCH_SOURCES_REGISTRY_CAP;MIOS_SCHEDULER_QUEUE_MAX_TURNS
7.0	3	distinct-configurable-fact	MIOS_KNOWLEDGE_RECALL_HALFLIFE_DAYS;MIOS_SLO_DEFAULT_PRIORITY;MIOS_SLO_INTERACTIVE_PRIORITY
8000	3	distinct-configurable-fact	MIOS_CODEMODE_MAX_OUTPUT_CHARS;MIOS_CODE_MODE_MAX_OUTPUT_CHARS;MIOS_MEMORY_N_CTX
8090	3	distinct-configurable-fact	MIOS_COCKPIT_PORT;MIOS_PORTS_COCKPIT;MIOS_PORT_COCKPIT
8300	3	distinct-configurable-fact	MIOS_FORGE_HTTP_PORT;MIOS_PORTS_FORGE_HTTP;MIOS_PORT_FORGE_HTTP
8301	3	distinct-configurable-fact	MIOS_FORGE_SSH_PORT;MIOS_PORTS_FORGE_SSH;MIOS_PORT_FORGE_SSH
8640	3	distinct-configurable-fact	MIOS_A2A_DISCOVER_PORT;MIOS_PORTS_AGENT_PIPE;MIOS_PORT_AGENT_PIPE
8899	3	distinct-configurable-fact	MIOS_PORTS_SEARXNG;MIOS_PORT_SEARXNG;MIOS_SEARXNG_PORT
UTC	3	distinct-configurable-fact	MIOS_DEFAULT_TIMEZONE;MIOS_LOCALE_TIMEZONE;MIOS_TIMEZONE
cuda	3	distinct-configurable-fact	MIOS_BUILD_BAKE_GROUP_MEMBERS_CUDA;MIOS_CUDA_VERSION;MIOS_LLM_LIGHT_VERSION
en_US.UTF-8	3	distinct-configurable-fact	MIOS_DEFAULT_LOCALE;MIOS_LOCALE;MIOS_LOCALE_LANGUAGE
log	3	distinct-configurable-fact	MIOS_HITL_MODE;MIOS_PGVECTOR_MEMORY_GUARD_MODE;MIOS_PG_MEMORY_GUARD_MODE
multi-user.target,default.target	3	true-alias	MIOS_PODS_MIOS_AI_WANTED_BY;MIOS_PODS_MIOS_SYSTEM_WANTED_BY;MIOS_PODS_MIOS_WEBTOOLS_WANTED_BY
prefer-dark	3	true-alias	MIOS_APPEARANCE_ADW_COLOR_SCHEME;MIOS_COLOR_SCHEME;MIOS_DESKTOP_COLOR_SCHEME
qwen3	3	true-alias	MIOS_LANES_LIGHT_REASONING_PARSER;MIOS_LANES_SGLANG_REASONING_PARSER;MIOS_LANES_VLLM_REASONING_PARSER
us	3	distinct-configurable-fact	MIOS_DEFAULT_KEYBOARD;MIOS_KEYBOARD;MIOS_LOCALE_KEYBOARD_LAYOUT
wheel,libvirt,kvm,video,render,input,dialout,docker	3	true-alias	MIOS_DEFAULT_GROUPS;MIOS_IDENTITY_GROUPS;MIOS_USER_GROUPS
x11	3	true-alias	MIOS_GRAPHICS_GDK_BACKEND;MIOS_WSL2_DESKTOP_COMPAT_GDK_BACKEND;MIOS_WSLG_GDK_BACKEND
#3D6BA8	2	true-alias	MIOS_ANSI_12_BRIGHT_BLUE;MIOS_COLORS_ANSI_12_BRIGHT_BLUE
#5FAA8E	2	true-alias	MIOS_ANSI_10_BRIGHT_GREEN;MIOS_COLORS_ANSI_10_BRIGHT_GREEN
#9D7660	2	true-alias	MIOS_ANSI_13_BRIGHT_MAGENTA;MIOS_COLORS_ANSI_13_BRIGHT_MAGENTA
#FF6B5C	2	true-alias	MIOS_ANSI_9_BRIGHT_RED;MIOS_COLORS_ANSI_9_BRIGHT_RED
#FF8540	2	true-alias	MIOS_ANSI_11_BRIGHT_YELLOW;MIOS_COLORS_ANSI_11_BRIGHT_YELLOW
#FFFFFF	2	true-alias	MIOS_ANSI_15_BRIGHT_WHITE;MIOS_COLORS_ANSI_15_BRIGHT_WHITE
--effort {e}	2	true-alias	MIOS_A2O_CLAUDE_EFFORT_FLAG;MIOS_FRONTIER_CLAUDE_EFFORT_FLAG
--new-tab	2	distinct-configurable-fact	MIOS_BROWSER_FLAGS_EPIPHANY_TAB;MIOS_BROWSER_FLAGS_FIREFOX_TAB
/etc/ceph/keyring.d	2	true-alias	MIOS_CEPHFS_KEYRING_DIR;MIOS_STORAGE_CEPHFS_KEYRING_DIR
/etc/mios/install.env	2	true-alias	MIOS_INSTALL_ENV;MIOS_PATHS_INSTALL_ENV
/etc/mios/profile.toml	2	true-alias	MIOS_PATHS_PROFILE_TOML_HOST;MIOS_PROFILE_TOML_HOST
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe	2	true-alias	MIOS_PATHS_POWERSHELL_EXE;MIOS_POWERSHELL_EXE
/mnt/c/Windows/System32/cmd.exe	2	true-alias	MIOS_CMD_EXE;MIOS_PATHS_CMD_EXE
/mnt/m/Programs/Everything/es.exe,/mnt/c/Program Files/Everything/es.exe,/mnt/c/Program Files (x86)/Everything/es.exe,/mnt/c/Tools/Everything/es.exe,/mnt/c/Users/mios/AppData/Local/Programs/Everything/es.exe	2	true-alias	MIOS_EVERYTHING_CLI;MIOS_PATHS_EVERYTHING_CLI
/run/mios-launcher/launcher.sock	2	true-alias	MIOS_LAUNCHER_SOCKET;MIOS_PATHS_LAUNCHER_SOCKET
/run/user/{uid}/.cache	2	distinct-configurable-fact	MIOS_STORAGE_CEPHFS_XDG_CACHE_HOME_OVERRIDE;MIOS_XDG_CACHE_LOCAL_PATH
/srv/ai/mcp	2	true-alias	MIOS_AI_MCP_DIR;MIOS_PATHS_AI_MCP_DIR
/srv/ai/models	2	true-alias	MIOS_AI_MODELS_DIR;MIOS_PATHS_AI_MODELS_DIR
/usr/libexec/mios/mios-cephfs-provision	2	true-alias	MIOS_CEPHFS_PROVISION_SCRIPT;MIOS_STORAGE_CEPHFS_PROVISION_SCRIPT
/usr/share/mios/ai	2	true-alias	MIOS_AI_DIR;MIOS_PATHS_AI_DIR
/usr/share/mios/mios.toml	2	true-alias	MIOS_PATHS_MIOS_TOML;MIOS_TOML
/usr/share/mios/postgres/schema-init.sql	2	true-alias	MIOS_PGVECTOR_SCHEMA_INIT;MIOS_PG_SCHEMA_INIT
/usr/share/mios/profile.toml	2	true-alias	MIOS_PATHS_PROFILE_TOML_VENDOR;MIOS_PROFILE_TOML_VENDOR
/var/home/mios/.coderun-snapshots	2	true-alias	MIOS_CODERUN_SNAPSHOTS_ROOT;MIOS_PATHS_CODERUN_SNAPSHOTS_ROOT
/var/home/mios/coderuns	2	true-alias	MIOS_CODERUN_WORKSPACE_ROOT;MIOS_PATHS_CODERUN_WORKSPACE_ROOT
/var/lib/mios/.wsl-firstboot-done	2	true-alias	MIOS_PATHS_WSL_FIRSTBOOT_DONE;MIOS_WSLBOOT_DONE
/var/lib/mios/ai/journal.md	2	true-alias	MIOS_AI_JOURNAL;MIOS_PATHS_AI_JOURNAL
/var/lib/mios/ai/memory	2	true-alias	MIOS_AI_MEMORY_DIR;MIOS_PATHS_AI_MEMORY_DIR
/var/lib/mios/ai/scratch	2	true-alias	MIOS_AI_SCRATCH_DIR;MIOS_PATHS_AI_SCRATCH_DIR
/var/lib/mios/backups	2	true-alias	MIOS_PGVECTOR_BACKUP_DIR;MIOS_PG_BACKUP_DIR
/var/lib/mios/codemode	2	true-alias	MIOS_CODEMODE_WORKSPACE_ROOT;MIOS_PATHS_CODEMODE_WORKSPACE_ROOT
/var/lib/mios/hermes-tail,/var/lib/mios/delegation-prefilter,/var/lib/mios/log-watcher,/var/lib/mios/daemon,/var/lib/mios/scratch,/var/lib/mios/agent-nudger,/var/lib/mios/cron-director,/var/lib/mios/ai/scratch	2	true-alias	MIOS_FS_WATCHER_DIRS;MIOS_FS_WATCHER_WATCH_DIRS
/var/lib/mios/hermes-tail/frontier/frontier.jsonl	2	true-alias	MIOS_A2O_STREAM_PATH;MIOS_FRONTIER_STREAM_PATH
/var/lib/mios/pgvector	2	true-alias	MIOS_PGVECTOR_DATA_DIR;MIOS_PG_DATA_DIR
0.03	2	distinct-configurable-fact	MIOS_FINETUNE_WARMUP_RATIO;MIOS_KNOWLEDGE_RANK_HOT
0.3	2	distinct-configurable-fact	MIOS_KNOWLEDGE_RANK_AGE;MIOS_SELFIMPROVE_FAIL_THRESHOLD
0.3.0	2	true-alias	MIOS_META_MIOS_VERSION;MIOS_VERSION
0.6	2	distinct-configurable-fact	MIOS_ACI_HEAD_FRAC;MIOS_SCHED_SCORE_URGENCY_WEIGHT
0.92	2	true-alias	MIOS_AGENT_PIPE_COUNCIL_DIVERSITY_THRESHOLD;MIOS_COUNCIL_DIVERSITY_THRESHOLD
0.95	2	true-alias	MIOS_AGENT_PIPE_COUNCIL_AGGREGATOR_BYPASS_THRESHOLD;MIOS_COUNCIL_AGGREGATOR_BYPASS_THRESHOLD
0700	2	true-alias	MIOS_CEPHFS_SUBVOLUME_MODE;MIOS_STORAGE_CEPHFS_SUBVOLUME_MODE
1.1.0.37	2	true-alias	MIOS_EVERYTHING_CLI_VERSION;MIOS_PATHS_EVERYTHING_CLI_VERSION
10.89.0.1	2	true-alias	MIOS_CORE_NET_GATEWAY;MIOS_NETWORK_QUADLET_CORE_GATEWAY
100	2	distinct-configurable-fact	MIOS_REFINE_PROMOTE_CHARS;MIOS_TERMINAL_READING_COLS
1024	2	true-alias	MIOS_CEPHFS_MDS_SESSION_CAP_MAX;MIOS_STORAGE_CEPHFS_MDS_SESSION_CAP_MAX
11436	2	distinct-configurable-fact	MIOS_DISPATCH_KV_PAGING_HINTS;MIOS_DISPATCH_NO_TOOL_CHOICE_HINTS
11437	2	distinct-configurable-fact	MIOS_PORTS_OSCONTROL;MIOS_PORT_OSCONTROL
11438	2	distinct-configurable-fact	MIOS_COMPUTER_USE_SERVER_PORT;MIOS_FINETUNE_SERVE_PORT
120	2	distinct-configurable-fact	MIOS_COMPUTER_USE_DOCGEN_TIMEOUT_S;MIOS_NETWORK_RETRY_TOTAL_TIMEOUT_SEC
120.0	2	distinct-configurable-fact	MIOS_DISPATCH_RR_SLICE_TIMEOUT_S;MIOS_SLO_BEST_EFFORT_BUDGET_S
127.0.0.1:6789	2	true-alias	MIOS_CEPHFS_MONITORS;MIOS_STORAGE_CEPHFS_MONITORS
16384	2	true-alias	MIOS_CEPHFS_CLIENT_CACHE_SIZE;MIOS_STORAGE_CEPHFS_CLIENT_CACHE_SIZE
20000	2	true-alias	MIOS_PGVECTOR_HNSW_MAX_SCAN_TUPLES;MIOS_PG_HNSW_MAX_SCAN_TUPLES
2048	2	distinct-configurable-fact	MIOS_DISPATCH_LLM_NUM_PREDICT_CAP;MIOS_FINETUNE_MAX_SEQ_LEN
256	2	distinct-configurable-fact	MIOS_DISPATCH_TRACE_MAX_TRACES;MIOS_SCHEDULER_SLICE_TOKENS
262144	2	true-alias	MIOS_SGLANG_MAX_MODEL_LEN;MIOS_VLLM_MAX_MODEL_LEN
32	2	distinct-configurable-fact	MIOS_DEV_VM_DISK_RESERVE_GB;MIOS_FINETUNE_LORA_ALPHA
33554432	2	true-alias	MIOS_CEPHFS_CLIENT_READAHEAD_MAX_BYTES;MIOS_STORAGE_CEPHFS_CLIENT_READAHEAD_MAX_BYTES
3600	2	distinct-configurable-fact	MIOS_BUDGET_WINDOW_S;MIOS_KNOWLEDGE_EVICT_INTERVAL_S
500	2	distinct-configurable-fact	MIOS_KNOWLEDGE_EVICT_BATCH;MIOS_SELFIMPROVE_SAMPLE_SIZE
50000	2	distinct-configurable-fact	MIOS_DAEMON_INDEX_MAX_ENTRIES;MIOS_KNOWLEDGE_EVICT_MAX_ROWS
53	2	true-alias	MIOS_PORTS_ADGUARD_DNS;MIOS_PORT_ADGUARD_DNS
67	2	true-alias	MIOS_BUILD_RECHUNK_MAX_LAYERS;MIOS_RECHUNK_MAX_LAYERS
800	2	true-alias	MIOS_DISPATCH_DAG_NODE_MAX_TOKENS;MIOS_POLISH_MAX_TOKENS
8033	2	true-alias	MIOS_PORTS_OPEN_WEBUI;MIOS_PORT_OPEN_WEBUI
8053	2	true-alias	MIOS_PORTS_ADGUARD_UI;MIOS_PORT_ADGUARD_UI
8080	2	distinct-configurable-fact	MIOS_GUACAMOLE_PORT;MIOS_PORTS_GUACAMOLE_WEB
8091	2	true-alias	MIOS_PORTS_COCKPIT_LINK;MIOS_PORT_COCKPIT_LINK
8119	2	true-alias	MIOS_PORTS_HERMES_DASHBOARD;MIOS_PORT_HERMES_DASHBOARD
8222	2	distinct-configurable-fact	MIOS_PORTS_SSH;MIOS_PORT_SSH
8235	2	distinct-configurable-fact	MIOS_PORTS_CRAWL4AI;MIOS_PORT_CRAWL4AI
8302	2	distinct-configurable-fact	MIOS_PORTS_FIRECRAWL;MIOS_PORT_FIRECRAWL
8389	2	distinct-configurable-fact	MIOS_PORTS_RDP;MIOS_RDP_PORT
8432	2	distinct-configurable-fact	MIOS_PORTS_PGVECTOR;MIOS_PORT_PGVECTOR
8441	2	distinct-configurable-fact	MIOS_PORTS_VLLM;MIOS_PORT_VLLM
8442	2	distinct-configurable-fact	MIOS_PORTS_SGLANG;MIOS_PORT_SGLANG
8443	2	distinct-configurable-fact	MIOS_K3S_API_PORT;MIOS_PORTS_K3S_API
8444	2	distinct-configurable-fact	MIOS_CEPH_DASHBOARD_PORT;MIOS_PORTS_CEPH_DASHBOARD
8450	2	true-alias	MIOS_PORTS_LLM_LIGHT;MIOS_PORT_LLM_LIGHT
8458	2	true-alias	MIOS_PORTS_CPU_NODE;MIOS_PORT_CPU_NODE
8460	2	distinct-configurable-fact	MIOS_PORTS_MCP;MIOS_PORT_MCP
85	2	distinct-configurable-fact	MIOS_METAL_GUEST_CPU_PERCENT;MIOS_METAL_GUEST_RAM_PERCENT
8633	2	true-alias	MIOS_PORTS_OPENCODE_GATEWAY;MIOS_PORT_OPENCODE_GATEWAY
86400	2	distinct-configurable-fact	MIOS_ADGUARD_CACHE_MAX_TTL;MIOS_DISPATCH_KV_GC_TTL_S
8641	2	distinct-configurable-fact	MIOS_PORTS_PREFILTER;MIOS_PORT_PREFILTER
8643	2	true-alias	MIOS_PORTS_HERMES_WORKER;MIOS_PORT_HERMES_WORKER
8644	2	true-alias	MIOS_PORTS_DAEMON_AGENT;MIOS_PORT_DAEMON_AGENT
8645	2	true-alias	MIOS_PORTS_MODEL_ROUTER;MIOS_PORT_MODEL_ROUTER
8650	2	distinct-configurable-fact	MIOS_PORTS_ARBITER;MIOS_PORT_ARBITER
8681	2	true-alias	MIOS_PORTS_TTYD_BASH;MIOS_PORT_TTYD_BASH
8682	2	true-alias	MIOS_PORTS_TTYD_POWERSHELL;MIOS_PORT_TTYD_POWERSHELL
8800	2	true-alias	MIOS_PORTS_CODE_SERVER;MIOS_PORT_CODE_SERVER
C	2	true-alias	MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_POSTURE;MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_POSTURE
Gemini 3.5 Flash (High)	2	true-alias	MIOS_A2O_LANE_B_MODEL;MIOS_FRONTIER_LANE_B_MODEL
INFO	2	true-alias	MIOS_FIRECRAWL_LOG_LEVEL;MIOS_SERVICES_WEBTOOLS_FIRECRAWL_LOG_LEVEL
MiOS Operator	2	distinct-configurable-fact	MIOS_IDENTITY_FULLNAME;MIOS_USER_FULLNAME
MiOS-DEV	2	distinct-configurable-fact	MIOS_APPS_SHORTCUTS_MIOS_DEV_NAME;MIOS_BUILDER_DISTRO
My Personal Operating System	2	distinct-configurable-fact	MIOS_BRANDING_TAGLINE;MIOS_BRANDING_TAGLINE_APP
admin	2	distinct-configurable-fact	MIOS_ADGUARD_ADMIN_USER;MIOS_IDENTITY_IPA_ENROLL_PRINCIPAL
agy	2	true-alias	MIOS_A2O_LANE_B_ENGINE;MIOS_FRONTIER_LANE_B_ENGINE
amd64	2	true-alias	MIOS_EDITIONS_MIOS_AUTOUNATTEND_UUP_ARCH;MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_UUP_ARCH
and,then	2	true-alias	MIOS_COMPOUND_CONJUNCTIONS;MIOS_ROUTING_COMPOUND_CONJUNCTIONS
application,program,app,window	2	true-alias	MIOS_LAUNCH_TARGET_TRAIL_PHRASES;MIOS_ROUTING_LAUNCH_TARGET_TRAIL_PHRASES
approx.,Approx.,e.g.,i.e.,vs.,etc.,U.S.,U.K.,a.m.,p.m.,No.,Inc.,Co.,Ltd.,St.,Mt.	2	true-alias	MIOS_SENTENCE_ABBREVIATIONS;MIOS_VERITY_SENTENCE_ABBREVIATIONS
attempt to launch and verify,launch and verify,launch it and verify,try to launch and verify,open and verify,open it and verify,try launching it again,try launching again,try opening it again,try opening again,launch it again,open it again,start it again,run it again,try again,attempt again,retry,relaunch,re-launch,reopen,re-open,try once more,one more time,attempt to launch,attempt the launch,verify the launch,launch and confirm,open and confirm	2	true-alias	MIOS_LAUNCH_RETRY_PHRASES;MIOS_ROUTING_LAUNCH_RETRY_PHRASES
ceph	2	true-alias	MIOS_CEPHFS_CLUSTER_NAME;MIOS_STORAGE_CEPHFS_CLUSTER_NAME
cephfs	2	true-alias	MIOS_CEPHFS_FS_NAME;MIOS_STORAGE_CEPHFS_FS_NAME
cephfs_data_bulk	2	true-alias	MIOS_CEPHFS_DATA_POOL_BULK;MIOS_STORAGE_CEPHFS_DATA_POOL_BULK
cephfs_data_hot	2	true-alias	MIOS_CEPHFS_DATA_POOL_HOT;MIOS_STORAGE_CEPHFS_DATA_POOL_HOT
cephfs_metadata	2	true-alias	MIOS_CEPHFS_METADATA_POOL;MIOS_STORAGE_CEPHFS_METADATA_POOL
claude-opus-4-8	2	true-alias	MIOS_A2O_LANE_A_MODEL;MIOS_FRONTIER_LANE_A_MODEL
cli	2	distinct-configurable-fact	MIOS_AGENTS_OPENCODE_KIND;MIOS_AGENTS_OPENCODE_TRANSPORT
dev	2	true-alias	MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_UUP_CHANNEL;MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_UUP_CHANNEL
didn't launch,did not launch,didn't open,did not open,didn't start,did not start,didn't come up,did not come up,didn't work,did not work,wouldn't open,would not open,no window,nothing happened,nothing opened,never opened,never launched,not opening,not launching,isn't open,is not open,isn't running,is not running,won't open,won't launch,doesn't open,does not open,failed to open,failed to launch	2	true-alias	MIOS_LAUNCH_FOLLOWUP_PHRASES;MIOS_ROUTING_LAUNCH_FOLLOWUP_PHRASES
diffuse,flux,dall,midjourney,sd	2	true-alias	MIOS_MODEL_MODALITIES_IMAGE;MIOS_ROUTING_MODEL_MODALITIES_IMAGE
drop	2	distinct-configurable-fact	MIOS_FIREWALLD_ZONE;MIOS_NETWORK_FIREWALLD_DEFAULT_ZONE
ed25519	2	distinct-configurable-fact	MIOS_AUTH_SSH_KEY_TYPE;MIOS_PASSPORT_ALGO
embed,bert,text-embedding,bge	2	true-alias	MIOS_MODEL_MODALITIES_EMBEDDINGS;MIOS_ROUTING_MODEL_MODALITIES_EMBEDDINGS
enable,force,success,active,dryrun	2	true-alias	MIOS_BOOLEAN_PARAM_KEYWORDS;MIOS_ROUTING_BOOLEAN_PARAM_KEYWORDS
explorer	2	intentional-many-to-one	MIOS_FIND_ALIASES_FILE_EXPLORER;MIOS_FIND_ALIASES_WINDOWS_EXPLORER
finalize (last ~20%)	2	true-alias	MIOS_A2O_LANE_B_ROLE;MIOS_FRONTIER_LANE_B_ROLE
for me please,on my desktop,on the desktop,right now,real quick,thank you,for me,please,thanks,now	2	true-alias	MIOS_LAUNCH_FILLER_PHRASES;MIOS_ROUTING_LAUNCH_FILLER_PHRASES
framework + ~80%	2	true-alias	MIOS_A2O_LANE_A_ROLE;MIOS_FRONTIER_LANE_A_ROLE
gaming	2	true-alias	MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_DEBLOAT_PROFILE;MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_DEBLOAT_PROFILE
general	2	distinct-configurable-fact	MIOS_AGENTS_HERMES_ROLE;MIOS_AGENTS__DEFAULTS_ROLE
generate	2	true-alias	MIOS_AUTH_SSH_KEY_ACTION;MIOS_SSH_KEY_ACTION
ghcr.io/mostlygeek/llama-swap:cuda	2	true-alias	MIOS_CUDA_IMAGE;MIOS_LLM_LIGHT_IMAGE
http://127.0.0.1:9222	2	true-alias	MIOS_CRAWL_CDP_URL;MIOS_SERVICES_WEBTOOLS_CDP_URL
http://localhost:${MIOS_PORT_AGENT_PIPE}/v1	2	true-alias	MIOS_AGENT_PIPE_ENDPOINT;MIOS_HERMES_ENDPOINT
http://localhost:${MIOS_PORT_HERMES_WORKER}/v1	2	true-alias	MIOS_AGENTS_HERMES_ENDPOINT;MIOS_HERMES_WORKER_ENDPOINT
http://localhost:${MIOS_PORT_LLM_LIGHT}/v1	2	distinct-configurable-fact	MIOS_AGENT_PIPE_TOOL_BACKEND;MIOS_HERMES_BACKEND_URL
http://localhost:8640/v1	2	true-alias	MIOS_AI_ENDPOINT;MIOS_ENDPOINT
https://api.github.com/repos/ful1e5/Bibata_Cursor/releases/latest	2	true-alias	MIOS_ENV_MIOS_URL_BIBATA_API;MIOS_URL_BIBATA_API
https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-44/ublue-os-packages-fedora-44.repo	2	true-alias	MIOS_ENV_MIOS_URL_UBLUE_REPO;MIOS_URL_UBLUE_REPO
https://github.com/ful1e5/Bibata_Cursor/releases/download/v{}/Bibata-Modern-Classic.tar.xz	2	true-alias	MIOS_ENV_MIOS_URL_BIBATA_DL;MIOS_URL_BIBATA_DL
https://github.com/ful1e5/Bibata_Cursor/releases/download/v{}/sha256-{}.txt	2	true-alias	MIOS_ENV_MIOS_URL_BIBATA_SUM;MIOS_URL_BIBATA_SUM
https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo	2	true-alias	MIOS_ENV_MIOS_URL_TERRA_REPO;MIOS_URL_TERRA_REPO
https://packagecloud.io/crowdsec/crowdsec/config_file.repo?os=fedora&dist=44&source=script	2	true-alias	MIOS_ENV_MIOS_URL_CROWDSEC_REPO;MIOS_URL_CROWDSEC_REPO
https://pkgs.tailscale.com/stable/fedora/tailscale.repo	2	true-alias	MIOS_ENV_MIOS_URL_TAILSCALE_REPO;MIOS_URL_TAILSCALE_REPO
in,and,then,with,on,to	2	true-alias	MIOS_COMPOUND_CONNECTIVES;MIOS_ROUTING_COMPOUND_CONNECTIVES
limit,count,timeout,port,every,concurrency,maxsize	2	true-alias	MIOS_INTEGER_PARAM_KEYWORDS;MIOS_ROUTING_INTEGER_PARAM_KEYWORDS
mios-adguard	2	true-alias	MIOS_ADGUARD_USER;MIOS_SERVICES_ADGUARD_USER
mios-agent	2	distinct-configurable-fact	MIOS_POLISH_MODEL;MIOS_REFINE_MODEL
mios-agent-pipe	2	true-alias	MIOS_AGENT_PIPE_USER;MIOS_SERVICES_AGENT_PIPE_USER
mios-ceph	2	true-alias	MIOS_CEPH_USER;MIOS_SERVICES_CEPH_USER
mios-crawl4ai	2	true-alias	MIOS_SERVICES_WEBTOOLS_USER;MIOS_WEBTOOLS_USER
mios-forge	2	true-alias	MIOS_FORGE_USER;MIOS_SERVICES_FORGE_USER
mios-hermes	2	true-alias	MIOS_HERMES_USER;MIOS_SERVICES_HERMES_USER
mios-llamacpp	2	true-alias	MIOS_LLAMACPP_USER;MIOS_SERVICES_LLAMACPP_USER
mios-open-webui	2	true-alias	MIOS_OPEN_WEBUI_USER;MIOS_SERVICES_OPEN_WEBUI_USER
mios-opencode:latest	2	true-alias	MIOS_AGENTS_OPENCODE_MODEL;MIOS_OPENCODE_MODEL
mios-pgvector	2	true-alias	MIOS_PGVECTOR_USER;MIOS_SERVICES_PGVECTOR_USER
mios-searxng	2	true-alias	MIOS_SEARXNG_USER;MIOS_SERVICES_SEARXNG_USER
mios.network	2	true-alias	MIOS_NETWORK_QUADLET_NETWORK;MIOS_QUADLET_NETWORK
mobi.phosh.MobileSettings	2	intentional-many-to-one	MIOS_FIND_ALIASES_MOBILE_CONTROL_PANEL;MIOS_FIND_ALIASES_MOBILE_SETTINGS
mobile	2	distinct-configurable-fact	MIOS_AGENTS_AI_LOCAL_LANE;MIOS_AGENTS_AI_LOCAL_ROLE
network-online.target,mios-hermes-browser.service,mios-webtools-firstboot.service	2	distinct-configurable-fact	MIOS_PODS_MIOS_WEBTOOLS_AFTER;MIOS_PODS_MIOS_WEBTOOLS_WANTS
noatime,fsc,_netdev	2	true-alias	MIOS_CEPHFS_MOUNT_OPTIONS;MIOS_STORAGE_CEPHFS_MOUNT_OPTIONS
nomic-768-v1	2	true-alias	MIOS_PGVECTOR_EMB_VERSION;MIOS_PG_EMB_VERSION
off	2	true-alias	MIOS_PGVECTOR_RLS_MODE;MIOS_PG_RLS_MODE
org.gtk.Gtk3theme.adw-gtk3-dark,org.gtk.Gtk3theme.adw-gtk3,app.devsuite.Ptyxis,gnome-nightly:org.gnome.Nautilus.Devel,fedora:org.gnome.Epiphany,com.github.tchx84.Flatseal,com.mattjakeman.ExtensionManager,com.google.ChromeDev	2	true-alias	MIOS_DESKTOP_FLATPAKS;MIOS_FLATPAKS
pgvector	2	true-alias	MIOS_PGVECTOR_MEMORY_PROVIDER;MIOS_PG_MEMORY_PROVIDER
plain	2	true-alias	MIOS_AUTH_PASSWORD_POLICY;MIOS_PASSWORD_POLICY
postgres	2	true-alias	MIOS_DB_BACKEND;MIOS_PGVECTOR_DB_BACKEND
quote,read,tell,summarise,summarize,what is,what does,what say,what says,first sentence,the content,browse,extract,scrape,headline,article,say	2	true-alias	MIOS_BROWSER_ACTION_VERBS;MIOS_ROUTING_BROWSER_ACTION_VERBS
qwen25	2	distinct-configurable-fact	MIOS_LANES_SGLANG_TOOL_CALL_PARSER;MIOS_SGLANG_TOOL_PARSER
remember,note,save,keep in mind,don't forget,make a note	2	true-alias	MIOS_REMEMBER_TRIGGER_PHRASES;MIOS_ROUTING_REMEMBER_TRIGGER_PHRASES
search,look up,google,find,search the web,search online	2	true-alias	MIOS_ROUTING_WEB_SEARCH_TRIGGER_PHRASES;MIOS_WEB_SEARCH_TRIGGER_PHRASES
slash	2	distinct-configurable-fact	MIOS_TEMPLATES_RUST_COMMENT;MIOS_TEMPLATES_TYPESCRIPT_COMMENT
stelterlab/Qwen3-30B-A3B-Instruct-2507-AWQ	2	true-alias	MIOS_SGLANG_BAKE_MODEL;MIOS_VLLM_BAKE_MODEL
strict_order	2	true-alias	MIOS_PGVECTOR_HNSW_ITERATIVE_SCAN;MIOS_PG_HNSW_ITERATIVE_SCAN
the,a,an,my	2	true-alias	MIOS_LAUNCH_TARGET_LEAD_PHRASES;MIOS_ROUTING_LAUNCH_TARGET_LEAD_PHRASES
type,write,enter,input,paste,put	2	true-alias	MIOS_COMPOUND_ACTIONS;MIOS_ROUTING_COMPOUND_ACTIONS
weather,forecast,near me,nearby,near here,around here,local news,local,my area,things to do,restaurants,closest,directions to	2	true-alias	MIOS_LOCATION_SENSITIVE_PHRASES;MIOS_ROUTING_LOCATION_SENSITIVE_PHRASES
web,internet,online	2	true-alias	MIOS_ROUTING_WEB_SEARCH_TRIGGER_CONTEXTS;MIOS_WEB_SEARCH_TRIGGER_CONTEXTS
xcb	2	true-alias	MIOS_WSL2_DESKTOP_COMPAT_QT_PLATFORM;MIOS_WSLG_QT_PLATFORM
xhigh	2	true-alias	MIOS_A2O_LANE_A_EFFORT;MIOS_FRONTIER_LANE_A_EFFORT
```

## 8. Sequenced next actions (AGY-856..930)

1. **Land the canonical map + drift-gate (section 6)** first, disposition every family-3
   `PGVECTOR_/PG_` pair explicitly (`keep-distinct` for `*_USER`). This makes the invariant
   enforceable before any key is moved. *(AGY-856..862)*
2. **Collapse the low-risk, zero-drift families** in ascending blast-radius order:
   `_TIMEOUT_SECONDS`/`_S` (13), `WSLG_` (12), `EDITIONS_*_MINI_` (11), `ENV_MIOS_URL_` (10),
   color prefixes (9,8), then `PATHS_` (7). Each: make the alias derive from the canonical
   in `userenv.sh`, repoint consumers, re-run `mios-env-snapshot` and confirm the lossless
   diff is empty. *(AGY-863..890)*
3. **Fix the four incomplete-port drifts (section 4.1)** by making `MIOS_PORT_<X>` derive
   from `MIOS_PORTS_<X>`; then collapse the 3-way port spellings to the plural canonical. *(AGY-891..900)*
4. **Collapse the large planes** `SERVICES_` (2), `STORAGE_CEPHFS_` (5), `A2O_/FRONTIER_` (6),
   `ROUTING_` (4), `PGVECTOR_/PG_` (3) — highest key-count, do last with full diff gating. *(AGY-901..918)*
5. **Convert the hardcoded surfaces (section 4.4)** to build-time projections: theme-render
   the configurator palette from `[colors]` (kill the 3 hand-copies), and regenerate the
   `mios-knowledge-graph.json` `env` block from the resolver so H2–H6 can never drift. *(AGY-919..930)*
6. **Guard the empty-value surface**: 774 keys resolve to `""`. Confirm each is an
   intentional optional/flag default, not an accidental unset, before the namespace collapse
   changes their provenance.

## 9. Provenance

- Snapshot: `usr/libexec/mios/mios-env-snapshot` (2416 lines; `LC_ALL=C`, `HOME=/nonexistent`, vendor-only).
- Analysis scripts (grouping, classification, family/false-friend detection) are deterministic over the raw snapshot; rerun to reproduce every table.
- SSOT: `usr/share/mios/mios.toml` (`[colors]` at line 8760); resolver `usr/lib/mios/userenv.sh` (325 lines).
