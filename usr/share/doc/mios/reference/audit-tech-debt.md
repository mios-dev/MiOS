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
exist as split targets. This is the *seam infrastructure* the `server.py` split plugs
into — it does not need to be invented.

### M3 — Second-largest module: `mios_dispatch.py` = 1475 lines

`grep -cE '^(class |def |async def )' mios_dispatch.py` → 17 defs. Cleanly separable:
cmd-build (`_build_dispatch_cmd` `mios_dispatch.py:383`, `normalize_container_exec:351`,
`_sandbox_wrap_cmd:308`), gates (`_rule_of_two_gate:947`, `_quarantine_gate:1042`),
live dispatch (`_dispatch_mios_verb_live:748`, `_dispatch_mios_verb_inner_raw:1164`),
and the router (`dispatch_verb:1459`).

### M4 — Remaining >500-line modules

```
mios_skills.py   720   mios_surface.py  686   mios_gateway_queue.py 486
```

### M5 — The three `mios.toml` are a layered overlay, not a conflict

| File | Lines | Role | `mios_version` |
|---|---|---|---|
| `usr/share/mios/mios.toml` | 11508 | **base SSOT** | `= "0.3.0"` (`:376`) |
| `etc/mios/mios.toml` | 18 | system override stub | *(none — inherits)* |
| `etc/skel/.config/mios/mios.toml` | 39 | per-user skel overlay | *(none — inherits)* |

`grep -rn 'mios_version\s*=' --include='*.toml'` returns **exactly one** hit. The
"conflicting versions" debt is gone; this is the intended base→system→user overlay
(the SSOT-as-dotfiles model, ADR-0010). No action beyond documenting it.

### M6 — `eval` inventory (the dangerous path is already gone)

`grep -rn '\beval\b'` across `usr/bin`, `usr/lib/mios`, `usr/libexec/mios`:

| Site | Kind | Verdict |
|---|---|---|
| `usr/lib/mios/userenv.sh:245` `eval "$exports"` | evals the SSOT-walk-generated `KEY=val` export block | **contained** (generated, not agent input) — convert to `source <(...)` |
| `usr/libexec/mios/mios-ai-clear:65` `eval "$@"` | dry-run runner over self-composed commands | **benign** — array `"$@"` exec |
| `usr/libexec/mios/mios-ai-reset:91` `eval "$@"` | same pattern | **benign** — array exec |
| `usr/libexec/mios/mios-launch:507` `eval exec "$_hit_cmd" '"$@"'` | evals a resolved launch command | **contained** — resolve to `argv` array |
| `usr/libexec/mios/mios-window:386` `eval "$(python3 - ...)"` | evals python-emitted shell | **contained** — emit `argv`, not a shell string |

There is **no** Python `eval(`/`exec(` in `server.py` or `mios_dispatch.py`. Agent
verb args flow through `mios_template.CompiledTemplate` (`mios_template.py:37`), which
`shlex.quote`s every substitution, then `mios_dispatch._build_dispatch_cmd`
(`mios_dispatch.py:383`) + `normalize_container_exec` (`mios_dispatch.py:351`). The
"9 eval-on-agent-args verbs" belonged to the retired shell-dispatch era.

### M7 — shellcheck ratchet already exists (and is a true modified-files ratchet)

`automation/lint-shell.sh`:
- **auto-provisions** shellcheck (dnf/apt), exits `2`=WARN if it cannot, so a skipped
  lint is never a false-green (`lint-shell.sh:17-33`).
- **error-level, repo-wide** hard gate over all shell (`lint-shell.sh:80-83`).
- **warning-level on modified/new files** vs `origin/main` (`lint-shell.sh:85-116`) —
  new debt cannot be introduced.

Wired at `.github/workflows/mios-ci.yml:53-56` (drift-gate job). **Gap:** the
warning-level check only covers files touched in the diff; the *stock* of
warning-level findings in unmodified files is never driven down. TD-4 upgrades this to
a declining whole-repo baseline.

### M8 — Compiled templates + template-conformance law already shipped

`mios_template.py:37` `class CompiledTemplate` (pre-parsed segments + placeholder-name
reflection + fast render). Template **registry** at `usr/share/mios/templates/`
(21 templates: `python-module`, `bash-verb`, `rust`, `markdown-doc`, `adr`, …).
Enforced by **Law 16 (ONE-TEMPLATE-PER-TYPE)** (`mios.toml:723`) → drift-check 46
`check_template_conformance` (`98-drift-checks.sh:3196`) via
`usr/libexec/mios/check-template-conformance`.

### M9 — Language policy already codified as Law 14

`usr/share/mios/mios.toml:708-713`:

> **Law 14 — TARGET-LANGUAGES:** Rust for native tooling/orchestration/services/
> validation; Python for the AI plane; Bun/TS for the web Portal; bash is thin GLUE
> ONLY. No NEW C#, Batch, PowerShell-as-program, or Go native code — grandfathered-
> for-port, not a licence for more. Minimise languages; convert shell → machine code.

Enforced by `check_target_languages`; grandfather list `[laws.target_languages]`
(`mios.toml:730-733`) may only **shrink**. Current footprint (measured):
`py 500, sh 265, rs 14 (7 native crates under tools/native/ + src/mios-rs/), go 0,
ts 0`. Rust is real and growing (`mios-ssot-walk`, `mios-ssot-lint`, `mios-bake-plan`,
`mios-version-check`, `mios-wallpaperd`, …). **Policy = follow Law 14; the debt is
that server.py/dispatch orchestration is still Python-heavy shell-glue-adjacent — no
new-language action, only the module split below.**

---

## Remaining debt, sequenced

### TD-1 — Split `server.py` (7810 → composition root <800) — **HIGH**

Extract cohesive helper clusters into `mios_pipe/*` (dirs mostly exist), leaving
`server.py` as a thin composition root: imports, app creation, `lifespan`,
`configure()` passes, `include_router` mounts, `main()`.

**Drop-in split manifest** (target module ← source span; every target ≤ ~500 lines):

| # | Target module | Source span in `server.py` | Anchor symbols | Approx |
|---|---|---|---|---|
| 1 | `mios_pipe/observability/tracing.py` | 376-470 | `_current_trace_id`, `_traced_stage`, `_trace_span` | 95 |
| 2 | `mios_pipe/runtime/endpoints.py` | 571-582, 5589-5680 | `_is_remote_endpoint`, `_should_health_probe`, `_is_local_endpoint`, `_offline_posture` | 200 |
| 3 | `mios_pipe/kernel/hop_guard.py` | 970-1050 | `_dispatch_depth`, `_enter_dispatch_hop`, `_depth_exhausted`, `_hop_via_headers`, `_seed_hop_from_headers` | 80 |
| 4 | `mios_pipe/runtime/lifespan.py` | 1451-1646 | `lifespan`, `_warm`, `_flush_loop` | 200 |
| 5 | `mios_pipe/routing/storage_cephfs.py` | 1647-1730 | `_check_user_cephfs`, `cephfs_users`, `cephfs_health` (→ real router) | 90 |
| 6 | `mios_pipe/routing/inference_lora.py` | 1732-1795 | `lora_load`, `lora_list` (→ real router) | 65 |
| 7 | `mios_pipe/agents/binding.py` | 2027-2544 | `_agent_engines`, `_cap_cpu_lane_model`, `_is_slow_lane_ep`, `_agent_binding`, `_load_dispatch_cfg`, `_agent_skill_tags`, `_rebuild_blade_topology` | 520 → split 2 |
| 8 | `mios_pipe/agents/contract.py` | 2544-3116 | `_strip_agent_chrome`, `_is_trivial_bypass`, `_load_agent_contract`, `_agent_contract` | 570 → split 2 |
| 9 | `mios_pipe/context/enrich.py` | 3476-4454 | `_rag_enrich`, `_read_tool_enrich` | 950 → split (rag / tool) |
| 10 | `mios_pipe/routing/compute_gate.py` | 4454-5152 | `_is_action_domain`, `_needs_compute`, `_cap_skills` | 700 → split 2 |
| 11 | `mios_pipe/kernel/stages.py` | 5503-5589 | `_kernel_dag_handler`, `_kernel_stage2b` | 90 |
| 12 | `mios_pipe/identity/membership.py` | 5884-6144 | `_reload_membership` | 260 |
| 13 | `mios_pipe/memory/embed.py` | 6144-6600 | `_embed_one` | 200 |
| 14 | `mios_pipe/context/polish.py` | 7077-7793 | `_polish_post`, endpoint-URL formatters | 716 → split (polish / endpoint-fmt) |
| — | **`server.py` residual** | app + `configure()` + `include_router` + `main()` | | **≤ 800** |

**Method (per row, safe & reversible):** move the functions verbatim into the target
module; expose the shared state each needs as `configure(...)`-injected module globals
(the exact pattern already used by every `mios_pipe.routing.*` module — e.g.
`mios_routing.configure(...)` at `server.py:2950`); import back into `server.py` for
`provided`-parity. Land one row per PR; `test_server_import.py` (16.9 KB, already
present) is the regression guard that the import surface stays byte-identical.

**Sequence:** rows 1→4 first (leaf helpers, no back-refs) to prove the injection
pattern, then 5-6 (routes → real routers, deleting the last 4 inline `@app` decos),
then the thick chat-pipeline clusters 7-14. Each row drops server.py by its "Approx"
column; after row 14 the residual is the ≤800-line composition root.

### TD-1G — Add the missing module-size fitness function — **HIGH** (unblocks TD-1 durability)

No gate today prevents a module from re-growing past 800 lines. Add
`check_module_size` to `98-drift-checks.sh` with a **grandfathered, shrink-only**
ceiling list (server.py etc. exceed 800 today — they ratchet down as TD-1 lands).
Drop-in in the Artifacts section below. Register as candidate **Law 17 (MODULE-SIZE)**
alongside the existing `[laws]` table (`mios.toml:695-724`).

### TD-2 — Split `mios_dispatch.py` (1475) — **MEDIUM**

Into `mios_pipe/kernel/dispatch/` : `cmd_build.py` (`_build_dispatch_cmd:383`,
`normalize_container_exec:351`, `_sandbox_wrap_cmd:308`), `gates.py`
(`_rule_of_two_gate:947`, `_quarantine_gate:1042`), `live.py`
(`_dispatch_mios_verb_live:748`, `_dispatch_mios_verb_inner_raw:1164`), `router.py`
(`dispatch_verb:1459`). Same `configure()` injection + shim pattern.

### TD-3 — `mios_skills.py` (720), `mios_surface.py` (686), `mios_gateway_queue.py` (486) — **LOW**

Below the pain threshold; fold into TD-1G's ratchet so they cannot grow, split
opportunistically when next touched.

### TD-4 — Upgrade shellcheck to a declining whole-repo warning baseline — **MEDIUM**

Keep the existing error-level + modified-files-warning gates; **add** a declining
whole-repo warning-count baseline so accumulated warning debt in untouched files can
only fall. Drop-in script + CI step below.

### TD-5 — `eval` hardening — **LOW**

Convert the 3 "contained" evals (M6) to `argv` arrays / `source <(...)`; leave the 2
benign runner evals. Not a security hole today (no agent input reaches them) — hygiene.

### TD-6 — Generalize `CompiledTemplate` to non-verb surfaces — **LOW**

`CompiledTemplate` serves verb command lines; theme/dotfiles rendering
(`mios-theme-render`, `mios-sync-toml`) still uses ad-hoc substitution. Route those
through the same compiled engine so Law 16 covers every projected surface. Tracked by
ADR-0010; no new debt, an extension.

---

## Drop-in artifact 1 — module-size fitness function (TD-1G)

Add to `automation/98-drift-checks.sh` (registered in the `run` dispatcher next to the
other `check_*`), plus the shrink-only ceiling list in `mios.toml`.

```bash
# --- (NEW) Module-size ratchet (candidate Law 17 MODULE-SIZE). ---------------
# FAILS if any Python/shell module exceeds its ceiling. Files in the grandfather
# map carry a per-file ceiling that may only SHRINK (mirrors target_languages).
# Default ceiling for un-listed files is 800 lines; a NEW file over 800 fails.
check_module_size() {
    local default_ceiling=800
    local -a roots=(
        "$ROOT/usr/lib/mios/agent-pipe"
        "$ROOT/usr/lib/mios/agent-pipe/mios_pipe"
    )
    # Grandfathered ceilings (file:ceiling). MUST only ever shrink. Seeded from
    # today's measured reality so the gate goes green now and ratchets with TD-1.
    local -A ceiling=(
        ["usr/lib/mios/agent-pipe/server.py"]=7810
        ["usr/lib/mios/agent-pipe/mios_dispatch.py"]=1475
        ["usr/lib/mios/agent-pipe/mios_skills.py"]=720
        ["usr/lib/mios/agent-pipe/mios_surface.py"]=686
    )
    local violated=0 f rel n cap
    while IFS= read -r -d '' f; do
        rel="${f#"$ROOT"/}"
        case "$rel" in */__pycache__/*|*/test_*|*/tests/*) continue;; esac
        n=$(wc -l < "$f")
        cap="${ceiling[$rel]:-$default_ceiling}"
        if (( n > cap )); then
            _violation "module-size: $rel is $n lines (ceiling $cap). Split it (see usr/share/doc/mios/reference/audit-tech-debt.md TD-1) or, if grandfathered, the ceiling may only shrink."
            violated=1
        fi
    done < <(find "${roots[@]}" -maxdepth 2 -name '*.py' -print0 2>/dev/null)
    (( violated == 0 )) && echo "[98-drift-checks]   (NEW) module-size: all modules within ceiling"
}
```

```toml
# Append to usr/share/mios/mios.toml, mirroring [laws.target_languages].
# Candidate Law 17 (MODULE-SIZE) enforcement data. Ceilings SHRINK-ONLY.
[laws.module_size]
default_ceiling = 800
grandfathered = [
  { path = "usr/lib/mios/agent-pipe/server.py",        ceiling = 7810 },
  { path = "usr/lib/mios/agent-pipe/mios_dispatch.py", ceiling = 1475 },
  { path = "usr/lib/mios/agent-pipe/mios_skills.py",   ceiling = 720  },
  { path = "usr/lib/mios/agent-pipe/mios_surface.py",  ceiling = 686  },
]
```

## Drop-in artifact 2 — declining-baseline shellcheck warning ratchet (TD-4)

`automation/lint-shell-warn-ratchet.sh` — counts repo-wide warning-or-above findings,
compares against a committed baseline, **fails on growth**, and auto-tightens the
baseline when the count drops (so debt can only fall).

```bash
#!/usr/bin/env bash
# AI-hint: Declining-baseline shellcheck WARNING ratchet -- repo-wide warning count may only fall.
# AI-related: automation/lint-shell.sh, automation/.shellcheck-warn-baseline, .github/workflows/mios-ci.yml
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASELINE="${ROOT}/automation/.shellcheck-warn-baseline"

command -v shellcheck >/dev/null 2>&1 || { echo "[warn-ratchet] shellcheck absent -- SKIP (not a pass)"; exit 2; }

# Reuse lint-shell.sh's file-selection contract: all tracked shell scripts.
mapfile -t files < <(
  { ls "${ROOT}"/automation/*.sh "${ROOT}"/tools/*.sh "${ROOT}"/installation/*.sh \
       "${ROOT}"/tests/*.sh "${ROOT}"/usr/lib/mios/*.sh 2>/dev/null || true; }
  for f in "${ROOT}"/usr/libexec/mios/mios-*; do
    [ -f "$f" ] && read -r l < "$f" && [[ "$l" =~ ^#\!.*(bash|sh) ]] && echo "$f"
  done
)
[ "${#files[@]}" -gt 0 ] || { echo "[warn-ratchet] no shell files"; exit 0; }

# Count warning+ findings machine-readably (gcc format: one line per finding).
current=$(shellcheck --severity=warning --format=gcc "${files[@]}" 2>/dev/null | grep -c ': warning:\|: error:' || true)
baseline=$(cat "$BASELINE" 2>/dev/null || echo 0)

echo "[warn-ratchet] shellcheck warnings: current=${current} baseline=${baseline}"
if (( current > baseline )); then
  echo "[warn-ratchet] FAIL: warning count grew (${baseline} -> ${current}). Fix new warnings." >&2
  exit 1
fi
if (( current < baseline )); then
  echo "${current}" > "$BASELINE"
  echo "[warn-ratchet] baseline tightened ${baseline} -> ${current} (commit automation/.shellcheck-warn-baseline)."
fi
echo "[warn-ratchet] PASS"
```

CI wiring — add one step to the `drift-gate` job in `.github/workflows/mios-ci.yml`
(directly after the existing "Shell linting (lint-shell.sh)" step at line ~63):

```yaml
      - name: Shell warning ratchet (declining baseline)
        run: bash ./automation/lint-shell-warn-ratchet.sh
```

Seed the baseline once (repo root): `bash automation/lint-shell-warn-ratchet.sh` then
`git add automation/.shellcheck-warn-baseline`.

---

## Details — verification commands (reproduce this audit)

```bash
wc -l usr/lib/mios/agent-pipe/server.py                                  # 7810
grep -cE '^\s*@app\.(get|post|put|delete|patch|websocket)' \
     usr/lib/mios/agent-pipe/server.py                                   # 5
find usr/lib/mios/agent-pipe/mios_pipe/routing -name '*.py' | xargs wc -l | tail -1   # 24108
grep -rn 'mios_version[[:space:]]*=' --include='*.toml' .                # 1 hit -> :376
grep -rnE '\beval\(|\bexec\(' usr/lib/mios/agent-pipe/server.py \
     usr/lib/mios/agent-pipe/mios_dispatch.py                            # 0 hits
grep -n 'severity=warning' automation/lint-shell.sh                      # ratchet exists
grep -n 'CompiledTemplate' usr/lib/mios/agent-pipe/mios_template.py      # :37
sed -n '708,713p' usr/share/mios/mios.toml                               # Law 14
```

### Priority summary

| Item | Effort | Risk | Priority |
|---|---|---|---|
| TD-1G module-size gate | S | low | **1st** (locks the ceiling before splitting) |
| TD-1 server.py split (rows 1-6) | M | low | **2nd** |
| TD-4 shellcheck declining baseline | S | low | **3rd** |
| TD-1 server.py split (rows 7-14) | L | med | 4th |
| TD-2 mios_dispatch split | M | low | 5th |
| TD-5 eval hardening | S | low | 6th |
| TD-3 / TD-6 opportunistic | S | low | as-touched |
