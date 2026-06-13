<!-- AI-hint: Specifies the 2026 naming-refactor roadmap for MiOS, defining canonical conventions for code constants, system service identifiers, model/agent tags, and SSOT keys to ensure cross-component consistency.
     AI-related: mios-sys-agent, mios-opencode, mios-heavy, mios-igpu, mios-agent-pipe, mios-surrealdb, mios-hermes, mios-ollama, mios-daemon-agent, mios-ai -->
# MiOS global-names + naming-conventions refactor (T26)

Operator directive (2026-06-04): *"refactor all Global Names and refactor naming
conventions."* Scope (operator-confirmed): all four areas — (1) agent-pipe code
globals, (2) system/service/user names, (3) model/agent/node IDs, (4) SSOT env +
mios.toml keys. This is a cross-cutting refactor of a **live** distro, so the
plan is **audit → canonical conventions → phased execution lowest-risk-first**,
each phase validated (`py_compile` / import-check / `bash -n` / `tomllib`) and
reversible, with the external-contract surface **frozen**.

A four-way parallel read-only audit (2026-06-04) found the baseline is already
coherent; the work is mostly *convergence* + one real defect.

## Canonical conventions (the target)

**Code (server.py + mios_*):**
- env-bound immutable constant → `UPPER_SNAKE`, name = env var minus `MIOS_` (keep).
- derived/import-time singleton (catalog, regex, prompt) → `_UPPER_SNAKE`; regex
  uses the **`_FOO_RE` suffix** form (the majority).
- mutable module state (caches/locks/sems/registries) → **`_lower_snake`**
  (UPPER implies do-not-mutate). This is the single biggest consistency choice.
- private fn → `_lower_snake`, namespaced by an established prefix family
  (`_db_/_pg_/_a2a_/_mcp_/_kv_/_sse_/_skill_/_dci_/_hitl_/_portal_/_agent_/
  _execute_dag_/_respond_/_render_/_load_`).
- public/pipeline fn (routed handler or cross-module verb) → `lower_snake`, no `_`.
- class / type alias → `CapWords`.

**System:** every MiOS artifact `mios-<component>` (lowercase-kebab) with ONE stem:
`mios-<x>.container` ⇒ `ContainerName=mios-<x>` ⇒ `mios-<x>.service` ⇒ user
`mios-<x>` ⇒ `[services.x]` ⇒ `tmpfiles.d/mios-<x>.conf`. Pod members
`mios-<pod>-<member>`. `User=`/`Group=` always `${MIOS_<SVC>_UID:-NNN}` (no bare
literals/names) except documented Law-6 root exceptions. UID tiers: 1000 operator,
800–809 privileged, **810–829 sidecars (sequential, never reuse)**, 850/860
AI/SYS buckets.

**Models/agents/nodes:** model tags lowercase-kebab `mios-<role>[-<lane>]`, NO
`:latest` in config (let `_norm_model_tag` add it); raw bases verbatim (upstream).
Agent ids lowercase-kebab, NO `mios-` prefix (table namespace already says it):
`hermes`, `opencode`, `daemon-agent`, `ai-local`. Node ids `<host>-<lane>` (already
canonical — the model to copy). Persona strings Title-case `MiOS <Role>`.

**SSOT:** section `snake_case`; key `snake_case` with short unit suffix
(`_s`/`_ms`/`_mb`/`_gb`/`_pct`); boolean toggle always `enable`. Env =
`MIOS_<SECTION>_<KEY>` with two documented collapses (`services.<svc>`→`MIOS_<SVC>_*`,
`image.sidecars.<svc>`→`MIOS_<SVC>_{IMAGE,VERSION}`). Port env always
`MIOS_PORT_<X>` (prefix form).

## FREEZE — external contracts (rename only with coordinated multi-site + client migration)
- Env **strings** `MIOS_*` (the Python constant is renamable; keep the string paired), esp. `MIOS_USER/HOSTNAME/AI_ENDPOINT/TOML/DB_*` + every quadlet-consumed `MIOS_PORT_*`/`MIOS_*_IMAGE`/`MIOS_*_{USER,UID,GID}`.
- HTTP route paths (`/v1/...`, `/a2a`, `/.well-known/...`, `/portal/...`), OpenAI/SSE JSON keys (`reasoning_content`, `mios_status`, `mios_portal`), A2A/MCP/AGNTCY fields + error codes + state strings, DB identifiers (`"mios"`, `"knowledge"`, columns).
- Model ids clients send/select: **`MiOS-Agent`** (`/v1`), **`mios-sys-agent`** (OWUI face), **`mios-opencode:latest`** (4-way contract), raw base tags + llama-swap map keys, `mios-heavy`/`mios-igpu` served-names.
- UID/GID **numbers** (810–829/850/860/1000) — baked into `/var` ownership; changing one needs an offline `chown -R` migration.

## Phased execution

### Phase 1 — SAFE (no external break; validated; do first)
**1a. Real defect (not cosmetic):** add the missing `MIOS_PGVECTOR_*`/`MIOS_PG_*`/`MIOS_LLAMA_SWAP_IMAGE`/`MIOS_PORT_LLAMA_SWAP`/`MIOS_LLAMACPP_*`/`MIOS_VLLM_IMAGE` vars to the **primary envsubst allow-list** in `automation/15-render-quadlets.sh` (they're only in the bash-fallback list → placeholders don't expand on envsubst hosts). Add `image.sidecars.vllm`→`MIOS_VLLM_IMAGE` slot (or drop the dangling render-list entry); drop/justify `MIOS_OLLAMA_{USER,UID,GID}` (no `services.ollama.*` slot produces them).
**1b. Code quick-wins (internal-only):** `_JUDGE_EP`→`_JUDGE_ENDPOINT`; unify the 7 `_RE_*` regexes → `*_RE`; `kv_fork`→`_kv_fork`; `DCI_ACTS/_ACT_SCHEMA/_ACT_NAMES`→`_DCI_*` (keep emitted JSON unchanged); `_PG_DOWN_UNTIL`→`_pg_down_until`.
**1c. System config fixes:** dead `[quadlets.enable]` keys (`cloudws-guacamole`/`cloudws-pxe-hub`→`mios-*`); wrong inline comments (`mios-agent-pipe.conf` 822→850, `mios-surrealdb.conf` 819→821); hardcoded `User=815/818` (ollama/vllm/searxng) → `${MIOS_*_UID:-...}`; add explicit `ContainerName=` to guacd/guacamole-postgres/crowdsec-dashboard; decide qdrant (prefix or remove).
**1d. Catalog/Modelfile:** drop/mark the stale `[[ai.catalog]]` rows not in the 4-model fleet; reconcile `mios-hermes.Modelfile` `FROM qwen3.5:9b` vs the "4b GPU half" docs; unify the two agent-brain persona strings.

### Phase 2 — MODERATE (rename + lockstep consumer updates; validated)
- `_disp_num`→`_dispatch_num` (33 refs, mechanical); normalize all mutable module-state casing to `_lower_snake` (semaphores/caches/registries — dedicated pass).
- File/unit renames: `ollama.container`→`mios-ollama.container` (ContainerName already `mios-ollama`; update preset/firstboot After=/Wants=); `guacamole-postgres`/`guacd`/`crowdsec-dashboard` → `mios-*` (update referencing scripts in lockstep).
- Agent id `mios-daemon-agent`→`daemon-agent` (grep-replace failover/model/env/registry refs).

### Phase 3 — RISKY (operator-gated; needs image rebuild + chown migration; via aliasing)
- Reconcile the SSOT lie: `[services.hermes]`/`[services.agent_pipe]` say users 820/822 but reality is `mios-ai`/850 — repoint SSOT to 850 OR retire the inert users (the "agent-plane consolidation phase 2": 8 units + 7 firstboot chown sites + tmpfiles + sudoers).
- Converge `MIOS_DB_*`/`MIOS_PG_*` vs `MIOS_PGVECTOR_*`, the port `_PORT`-suffix outliers, `timeout_seconds`→`timeout_s`, `[enhanced_session].enabled`→`enable` — all via **additive aliasing first** (keep both, flip canonical later), never in-place renames of the frozen contract.
- `[services.webtools]` user `mios-crawl4ai`/824 skew — rename user (chown) or section.

## Validation + deploy (every phase)
`py_compile` server.py + siblings; run the sibling unit suites; `tomllib` mios.toml + kargs; `bash -n` touched scripts; deploy via `automation/support/deploy-agent-pipe.sh` (import-check-before-restart gate). Live changes are reversible (`.bak` + git). No external-contract string is renamed without changing every consumer atomically.
