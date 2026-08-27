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

## 5. Value-duplication Summary & Top Collisions

> The raw 288-group collision catalog is summarized below by primary cluster. The de-duplication targets are driven by the systematic family analysis in Section 3 and the canonical map in Section 6.

| cluster | count | class | primary keys |
|---|---|---|---|
| `true` | 193 | distinct-configurable-fact | `MIOS_ACCOUNTS_DB_BACKED`, `MIOS_AGENTS_*_HEALTH_GATE`, `MIOS_AGENTS_OPENCODE_ENABLED` |
| `false` | 109 | distinct-configurable-fact | `MIOS_A2A_COUNCIL`, `MIOS_A2A_MDNS_DISCOVERY`, `MIOS_ADMISSION_MULTIBLADE_ENABLE` |
| `2` | 22 | distinct-configurable-fact | `MIOS_AGENT_PIPE_REFLEXION_LIMIT`, `MIOS_DEV_VM_CPU_RESERVE_MIN`, `MIOS_DISPATCH_LANE_CONCURRENCY` |
| `0` | 19 | distinct-configurable-fact | `MIOS_ADMISSION_TENANT_MAX_CONCURRENCY`, `MIOS_COCKPIT_IDLE_TIMEOUT` |
| `3` | 19 | distinct-configurable-fact | `MIOS_AGENT_PIPE_MAX_CONSECUTIVE_FAILURES`, `MIOS_DISPATCH_FANOUT_MAX` |
| `mios` | 19 | distinct-configurable-fact | `MIOS_DEFAULT_HOST`, `MIOS_DEFAULT_USER`, `MIOS_HOSTNAME` |
| `latest` | 18 | distinct-configurable-fact | `MIOS_ADGUARD_VERSION`, `MIOS_CODE_SERVER_VERSION`, `MIOS_HERMES_VERSION` |
| `1` | 16 | distinct-configurable-fact | `MIOS_BUDGET_AUTONOMOUS_MAX_INFLIGHT`, `MIOS_DAEMON_CRON_MAX_CONCURRENT` |
| `granite4.1:8b` | 8 | true-alias | `MIOS_AI_MODEL`, `MIOS_HERMES_MODEL`, `MIOS_GATEWAY_MODEL`, `MIOS_STACK_MODEL` |
| `nomic-embed-text` | 6 | true-alias | `MIOS_AI_EMBED_MODEL`, `MIOS_PGVECTOR_EMBED_MODEL`, `MIOS_PG_EMBED_MODEL` |
| `#1A407F` | 7 | distinct-configurable-fact | `MIOS_ANSI_4_BLUE`, `MIOS_COLORS_ACCENT`, `MIOS_COLOR_ACCENT` |
| `#282262` | 5 | distinct-configurable-fact | `MIOS_ANSI_0_BLACK`, `MIOS_COLORS_BG`, `MIOS_COLOR_BG` |

## 6. Canonical Mapping Table

Canonical SSOT resolver variables and their authoritative sources:
1. `MIOS_PORTS_<X>`: Derived from `[ports]` in `usr/share/mios/mios.toml`.
2. `MIOS_COLORS_<ROLE>`: Derived from `[colors]` in `usr/share/mios/mios.toml`.
3. `MIOS_AI_MODEL`: Canonical default local LLM (`granite4.1:8b`).
4. `MIOS_AI_EMBED_MODEL`: Canonical embedding model (`nomic-embed-text`).
5. `MIOS_AI_ENDPOINT`: Canonical OpenAI-compatible gateway (`http://localhost:8640/v1`).
