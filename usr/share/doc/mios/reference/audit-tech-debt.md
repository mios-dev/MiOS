<!-- AI-hint: Measured refresh of the MiOS tech-debt map (ADR-0011 territory) -- server.py split-seam manifest, kill-eval status, shellcheck warning-ratchet upgrade, compiled-template + Law-14 language-policy status, with a drop-in module-size gate and declining-baseline shellcheck ratchet. -->
<!-- AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_dispatch.py, usr/lib/mios/agent-pipe/mios_template.py, automation/lint-shell.sh, automation/98-drift-checks.sh, usr/share/mios/mios.toml, .github/workflows/mios-ci.yml -->

# MiOS Tech-Debt Map — Measured Refresh (2026-07-31)

## Overview

This is a **measured** refresh of the ADR-0011 tech-debt map. Every claim below was
verified against the working tree at `C:\MiOS` (the git root). The headline finding:
**most of the ADR-0011 debt map has already been executed.** The stale assertions
carried in memory (server.py ~26k then ~9k; 3× `mios.toml` at conflicting versions;
9 eval-on-agent-args verbs; "no shellcheck CI"; "add a compiled-template system";
"define a language policy") are, one after another, **already resolved or already
codified as law.** What remains is a *narrower, concrete* set of items — chiefly the
`server.py` composition-root split and one genuinely-missing fitness function
(module-size). This document measures the reality, then sequences the remaining work.

### Claim-vs-reality scorecard

| ADR-0011 claim (from memory) | Measured reality | Status |
|---|---|---|
| `server.py` ~9k lines, split <800/module | **7810 lines** (`wc -l`), but routes already migrated to `mios_pipe.routing`; it is now a composition root + chat-pipeline helpers | **PARTIAL — real work remains** |
| 3× `mios.toml` at conflicting 0.3.0/0.2.4 | Only `usr/share/mios/mios.toml:376` carries `mios_version = "0.3.0"`; the other two are a **designed 3-layer overlay** with no version key | **RESOLVED** |
| 9 eval-on-agent-args verbs | Agent-arg dispatch now renders via `mios_template.CompiledTemplate` + `shlex` quoting + `mios_dispatch.normalize_container_exec`; **zero** `eval(`/`exec(` in `server.py`/`mios_dispatch.py`; 5 benign internal-command `eval`s remain in shell | **RESOLVED (dangerous path gone)** |
| No shellcheck in CI | `automation/lint-shell.sh` runs error-level repo-wide **and** warning-level on modified files; wired at `.github/workflows/mios-ci.yml:53-56` + auto-provisions shellcheck | **RESOLVED — ratchet exists** |
| Add a compiled-template system | `mios_template.CompiledTemplate` exists; `usr/share/mios/templates/` registry + Law 16 (ONE-TEMPLATE-PER-TYPE) + drift-check 46 `check_template_conformance` | **RESOLVED — generalize only** |
| Define Rust/Go/Bun/Python policy | **Law 14 (TARGET-LANGUAGES)** at `usr/share/mios/mios.toml:708-713` + `check_target_languages` + `[laws.target_languages]` grandfather list | **RESOLVED — codified as law** |
| (not in memory) Module-size fitness function | **No** `max-lines` / module-size drift gate exists (`grep` of `98-drift-checks.sh` = none) | **MISSING — new gate proposed (TD-1G)** |

---

## Measurements (file:line evidence)

### M1 — `server.py` is 7810 lines, not a route bag

```
wc -l usr/lib/mios/agent-pipe/server.py   -> 7810
grep -cE '^\s*@app\.(get|post|put|delete|patch|websocket)' server.py -> 5
```

Only **5** live `@app.*` route decorators remain in `server.py`
(`server.py:1675,1700,1732,1760,5306`). The per-route handlers were migrated into
`mios_pipe/routing/` (**24108 lines**, 44 modules) and mounted via ~30
`app.include_router(...)` calls (e.g. `server.py:4895,4903,5303,5747,6624,6715,6781,
7315,7649,7773`). The capstone `POST /v1/chat/completions` + `POST /v1/responses`
already migrated onto `mios_chat.chat_router` (`server.py:7469-7470`,
`app.include_router(chat_router)` at `server.py:7649`).

So the 7810 lines are **not** routes — they are (a) the FastAPI app + `lifespan`,
(b) ~40 `configure(...)` dependency-injection passes that thread shared state into each
routing module, (c) the ~30 `include_router` mounts, and (d) a thick belt of
cross-cutting **chat-pipeline helpers** that the routing modules call back into.

The largest inline helper spans (gap between consecutive top-level defs):

| Span | Lines | Anchor def | Cohesion |
|---|---|---|---|
| `server.py:3607-4454` | 847 | `async def _read_tool_enrich` (`server.py:3607`) | context enrichment |
| `server.py:6144-7077` | 933 | `async def _embed_one` (`server.py:6144`) + router mounts | embed + wiring |
| `server.py:7077-7793` | 716 | `def _polish_post` (`server.py:7077`) | output polish |
| `server.py:4484-5152` | 668 | `async def _needs_compute` (`server.py:4484`) | compute gate |
| `server.py:2544-3054` | 510 | `def _strip_agent_chrome` (`server.py:2544`) | agent chrome |
| `server.py:1020-1451` | 431 | hop-guard + `lifespan` (`server.py:1451`) | runtime bootstrap |
| `server.py:582-970` | 388 | endpoint posture + dispatch-depth | runtime |

### M2 — `mios_pipe/` is an already-extracted package

```
mios_pipe/routing   24108 lines (44 modules)
mios_pipe/federation 3938
mios_pipe/scheduler  2493
mios_pipe/access     2274
mios_pipe/kernel     2015
mios_pipe/context    1972
mios_pipe/lifecycle  1291
```

Top-level `usr/lib/mios/agent-pipe/mios_*.py` files are **~850-byte re-export shims**
(`_ShimModule` lazily importing the real `mios_pipe.*` module — see `mios_arbiter.py`).
Empty landing dirs `mios_pipe/runtime/` and `mios_pipe/gateway/` (0 lines) already

*Note: Findings resolved and verified in active repository implementations.*
