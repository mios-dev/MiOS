<!-- AI-hint: Specifies the 2026 naming-refactor roadmap for MiOS, defining canonical conventions for code constants, system service identifiers, model/agent tags, and SSOT keys to ensure cross-component consistency across the immutable bootc image and the local agent stack.
     AI-related: mios-agent-pipe, mios-hermes, mios-opencode, mios-llm-light, mios-llm-heavy, mios-llm-heavy-alt, mios-llm-worker, mios-pgvector, mios-daemon-agent, mios-guacamole, mios-pxe-hub -->
# MiOS global-names + naming-conventions refactor (T26)

## Purpose and place in the whole system

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system** behind one
OpenAI-compatible endpoint. Because **the repo root IS the deployed system
root**, a name chosen in code, a Quadlet unit, a UID allocation, a `mios.toml`
key, and a served model tag all become *the same fact* on a booted host — and
that fact is carried forward, unchanged, by every `bootc upgrade`.

That is why naming is load-bearing rather than cosmetic. A drifted name is not a
style nit; it is a broken link in the chain **build pipeline → OCI image → bootc
lifecycle**, or in the AI chain **inference lanes → agent-pipe/Hermes
orchestration → pgvector memory → MCP/A2A**. When `[services.x]` in the SSOT, the
`mios-x.container` Quadlet, the `mios-x.service` unit, the `mios-x` user, and the
`tmpfiles.d/mios-x.conf` declaration all share **one stem**, the system is
self-describing and self-replicating; when they diverge, a firstboot `chown`
targets the wrong UID, an envsubst placeholder fails to expand, or a client
sends a model id no lane answers. This document is the canonical record of how
MiOS names every artifact so the whole — image, agent plane, security/virt/
cluster posture — stays coherent across rebuilds.

This is a cross-cutting refactor of a **live** distro, so the discipline is
**audit → canonical conventions → phased execution lowest-risk-first**, each
phase validated (`py_compile` / import-check / `bash -n` / `tomllib`) and
reversible, with the external-contract surface **frozen**. Audience: anyone
building or extending the image who must add or rename an artifact without
breaking the deployed lifecycle.

Operator directive (2026-06-04): *"refactor all Global Names and refactor naming
conventions."* Scope (operator-confirmed): all four areas — (1) agent-pipe code
globals, (2) system/service/user names, (3) model/agent/node IDs, (4) SSOT env +
mios.toml keys.

A four-way parallel read-only audit (2026-06-04) found the baseline is already
coherent; the work is mostly *convergence* + one real defect.

## Progress (2026-06-13)
- **Phase 1a — DONE.** The primary envsubst allow-list in `15-render-quadlets.sh`
  now carries `MIOS_PGVECTOR_*`/`MIOS_PG_*`/`MIOS_LLM_LIGHT_IMAGE`/`MIOS_PORT_LLM_LIGHT`/
  `MIOS_LLAMACPP_*`/`MIOS_VLLM_IMAGE` (placeholders expand on envsubst hosts).
- **Phase 1b — DONE.** `_JUDGE_EP`→`_JUDGE_ENDPOINT`, the `_RE_*`→`*_RE` unification,
  `kv_fork`→`_kv_fork`, `DCI_*`→`_DCI_*` (emitted JSON unchanged), `_PG_DOWN_UNTIL`→
  `_pg_down_until`, and the Phase-2 `_disp_num`→`_dispatch_num` are all live in server.py.
- **Phase 1c — partial.** Hardcoded `User=815/818` are already `${MIOS_*_UID}`.
  **CloudWS→MiOS consolidation DONE (2026-06-13):** the legacy `cloudws-guacamole`/
  `cloudws-pxe-hub` enable keys → `mios-guacamole`/`mios-pxe-hub` across `mios.toml`,
  `profile.toml`, bootstrap `mios.toml`/`profile.toml`/`profile-headless.toml` (headless
  `=false` preserved), the configurator quadlet-key array, and the `INDEX.md`/`sources.md`/
  `credits.md`/`system.md` references (`cloudws-ceph-bootstrap.service`→`ceph-bootstrap.service`).
  All edited TOMLs re-validated via `tomllib`. The `engineering-reference.md` CloudWS→MiOS
  deprecation table is kept as accurate migration history; `root-manifest.json` is a stale
  generated snapshot pending regeneration.
- **Phase 2 file/unit renames — DONE (superseded by the inference-engine refactor).**
  The Quadlet stems are now canonical on disk:
  `usr/share/containers/systemd/` ships `mios-llm-light.container` (`:11450`, the
  former `ollama`/`mios-mios-llm-light` lane), `mios-llm-heavy.container` (`:11441`,
  SGLang, was `mios-sglang`), `mios-llm-heavy-alt.container` (vLLM, was `mios-vllm`),
  `mios-llm-worker@.container` (was `mios-llama-worker@`), plus `mios-guacd`,
  `mios-guacamole-postgres`, and `mios-crowdsec-dashboard` (the CloudWS/inline-named
  units now carry `mios-` stems). The inference lanes were renamed by **function**,
  not upstream-tool name — see "Inference-engine rename" below.
- **Legacy backends REMOVED (postdates the original T26 plan).** Ollama, the legacy datastore,
  and Qdrant are gone from the live system (containers, firstboot, model-bake,
  Modelfiles, CLI shims). Inference + embeddings run on `mios-llm-light` (:11450);
  the unified agent datastore is **PostgreSQL + pgvector** (`mios-pgvector`, :5432).
  Remaining legacy-datastore/`[services.ollama_cpu]`/qdrant traces in `mios.toml` are
  stale snapshot residue pending an SSOT sweep — treat them as migration history,
  not live state (Phase 3 SSOT reconciliation below covers the cleanup).
- **Still pending:** Phase 1c `ContainerName=` audit on the renamed units, the
  remaining mutable-state casing pass (Phase 2), agent-id `mios-daemon-agent`→
  `daemon-agent`, and the operator-gated Phase 3 (SSOT reconciliation + chown/rebuild).

## Inference-engine rename (function-based, not upstream-tool names)

The inference lanes are now named by **what they do for MiOS**, decoupling the
unit/service identity from the swappable upstream engine inside it:

| Canonical MiOS identity | Port | Role | Was |
|---|---|---|---|
| `mios-llm-light` | `:11450` | **PRIMARY** local LLM lane — `llama.cpp` behind the `mios-llm-light` proxy image; multi-model auto-swap + KV-cache paging; serves everyday models, the `mios-opencode` coder model, **and embeddings** (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Config: `usr/share/mios/llamacpp/mios-llm-light.yaml` | `mios-mios-llm-light` |
| `mios-llm-heavy` | `:11441` | Heavy GPU lane (SGLang), served-name `mios-heavy`. Gated/off-by-default (VRAM) | `mios-sglang` |
| `mios-llm-heavy-alt` | `:11440` | Alternate heavy lane (vLLM, PagedAttention+APC), gated/off-by-default | `mios-vllm` |
| `mios-llm-worker@` | — | Single-model swarm workers (templated; dGPU swarm topology) | `mios-llama-worker@` |

`mios-llm-light` (the upstream tool/image `ghcr.io/mostlygeek/llama-swap:cuda`) and the
**Ollama-compatible API** the lanes speak are LEGITIMATE upstream references —
those stay. Only the MiOS *unit/service identity* was renamed. Per Law 5
(UNIFIED-AI-REDIRECTS) every agent and tool resolves the lane from
`MIOS_AI_ENDPOINT`; no vendor URL or port is hard-coded.

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
AI/SYS buckets. Live sidecar allocations (from `[services.*]`): forge 816,
open-webui 817, searxng 818, ceph 819, hermes 820, agent-pipe 822, crawl4ai 824,
adguard 825, pgvector 826, llamacpp 827, codemode 828. (UID 821 was the legacy datastore; it
is now free following the legacy datastore removal.)

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
- HTTP route paths (`/v1/...`, `/a2a`, `/.well-known/...`, `/portal/...`), OpenAI/SSE JSON keys (`reasoning_content`, `mios_status`, `mios_portal`), A2A/MCP/AGNTCY fields + error codes + state strings, DB identifiers (`"mios"`, `"knowledge"`, columns) — now backed by PostgreSQL + pgvector.
- Model ids clients send/select: **`MiOS-Agent`** (`/v1`), **`mios-sys-agent`** (OWUI face), **`mios-opencode:latest`** (4-way contract), raw base tags + mios-llm-light map keys, `mios-heavy`/`mios-igpu` served-names.
- UID/GID **numbers** (810–829/850/860/1000) — baked into `/var` ownership; changing one needs an offline `chown -R` migration.

## Phased execution

### Phase 1 — SAFE (no external break; validated; do first) — DONE
**1a. Real defect (not cosmetic):** add the missing `MIOS_PGVECTOR_*`/`MIOS_PG_*`/`MIOS_LLM_LIGHT_IMAGE`/`MIOS_PORT_LLM_LIGHT`/`MIOS_LLAMACPP_*`/`MIOS_VLLM_IMAGE` vars to the **primary envsubst allow-list** in `automation/15-render-quadlets.sh` (they were only in the bash-fallback list → placeholders didn't expand on envsubst hosts). Add `image.sidecars.vllm`→`MIOS_VLLM_IMAGE` slot (or drop the dangling render-list entry); the obsolete Ollama `{USER,UID,GID}` slot is retired with the Ollama removal.
**1b. Code quick-wins (internal-only):** `_JUDGE_EP`→`_JUDGE_ENDPOINT`; unify the 7 `_RE_*` regexes → `*_RE`; `kv_fork`→`_kv_fork`; `DCI_ACTS/_ACT_SCHEMA/_ACT_NAMES`→`_DCI_*` (keep emitted JSON unchanged); `_PG_DOWN_UNTIL`→`_pg_down_until`.
**1c. System config fixes:** dead `[quadlets.enable]` keys (`cloudws-guacamole`/`cloudws-pxe-hub`→`mios-*`) — DONE; fix wrong inline comments (`mios-agent-pipe.conf` 822→850); hardcoded `User=815/818` → `${MIOS_*_UID:-...}` — DONE; audit explicit `ContainerName=` on the renamed `mios-guacd`/`mios-guacamole-postgres`/`mios-crowdsec-dashboard` units. The qdrant references are dropped with its removal.
**1d. Catalog/Modelfile:** drop/mark the stale `[[ai.catalog]]` rows not in the current served fleet; the role models now resolve through the `mios-llm-light.yaml` alias map onto the served reasoning GGUF; unify the two agent-brain persona strings.

### Phase 2 — MODERATE (rename + lockstep consumer updates; validated) — file renames DONE
- `_disp_num`→`_dispatch_num` (33 refs, mechanical) — DONE; remaining: normalize all mutable module-state casing to `_lower_snake` (semaphores/caches/registries — dedicated pass).
- File/unit renames — DONE: the inference lanes are `mios-llm-light`/`mios-llm-heavy`/`mios-llm-heavy-alt`/`mios-llm-worker@`; `guacamole-postgres`/`guacd`/`crowdsec-dashboard` → `mios-*` (referencing scripts updated in lockstep).
- Agent id `mios-daemon-agent`→`daemon-agent` (grep-replace failover/model/env/registry refs) — PENDING.

### Phase 3 — RISKY (operator-gated; needs image rebuild + chown migration; via aliasing)
- **SSOT cleanup of the removed backends:** sweep the residual legacy-datastore config
  + service sections (UID 821), `[services.ollama_cpu]`, `enable_ollama`, the
  ollama seed/runtime-dir keys, and qdrant traces out of `mios.toml`/`profile.toml`,
  keeping a brief migration note. The `knowledge`/`agent_memory`/etc. tables now live
  in `usr/share/mios/postgres/schema-init.sql` on PostgreSQL + pgvector.
- Reconcile the SSOT lie: `[services.hermes]`/`[services.agent_pipe]` say users 820/822 but the live agent plane runs as `mios-ai`/850 — repoint SSOT to 850 OR retire the inert users (the "agent-plane consolidation phase 2": units + firstboot chown sites + tmpfiles + sudoers).
- Converge `MIOS_DB_*`/`MIOS_PG_*` vs `MIOS_PGVECTOR_*`, the port `_PORT`-suffix outliers, `timeout_seconds`→`timeout_s`, `[enhanced_session].enabled`→`enable` — all via **additive aliasing first** (keep both, flip canonical later), never in-place renames of the frozen contract.
- `[services.webtools]` user `mios-crawl4ai`/824 skew — rename user (chown) or section.

## Validation + deploy (every phase)
`py_compile` server.py + siblings; run the sibling unit suites; `tomllib` mios.toml + kargs; `bash -n` touched scripts; deploy via `automation/support/deploy-agent-pipe.sh` (import-check-before-restart gate). Live changes are reversible (`.bak` + git). No external-contract string is renamed without changing every consumer atomically.
