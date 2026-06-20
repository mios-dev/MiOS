# WS-0-PREFLIGHT — baseline reconciliation against the working tree

> Read-first correction pass for the MiOS master plan. Re-derives every
> "verified" baseline number against a pinned `HEAD`, and strikes claims that are
> stale against the *current* tree. Generated 2026-06-20.

## Pinned baseline

- **`HEAD` SHA:** `8658df1ca9d43f0ff43cbd2a3527e9573571796e`
- **Branch:** `main` (clean working tree at pin time)
- All counts below were re-derived against this SHA. Treat any earlier
  "verified" number as stale until re-derived.

## Re-derived counts (supersede the plan's numbers)

| Claim in plan | Plan value | Re-derived @ HEAD | Verdict |
|---|---|---|---|
| `usr/lib/mios/agent-pipe/server.py` line count | 27,162 (older draft: 26,151) | **27,311** | drifted +149 again; re-scope WS-3/WS-A11 against 27,311 |
| `patch.py`..`patch5.py` in `agent-pipe/` | "must delete" | **absent** (0 files, 0 `import patch`) | deletion is a no-op — struck from WS-3 |
| `--served-model-name mios-heavy` collision | real | **real & intentional** | both `mios-llm-heavy.container` (SGLang :11441) and `mios-llm-heavy-alt.container` (vLLM :11440) serve `mios-heavy`; documented mutually-exclusive "enable ONE on a shared GPU" — NOT a bug to gate |
| port/model drift (file counts) | :11434×18, gemma4×30, qwen3×110 | :11434×59, gemma4×24, qwen3×76, mios-heavy×46 | drift real but partly reduced; remaining `:11434` refs are mostly docs/vendor-compat, not active lanes |

## The plan's PREFLIGHT premises that are now STALE

The master plan was generated from draft prose that predates the drift-freeze
implementation. Against `HEAD` the following PREFLIGHT/WS-0A claims are false:

1. **"`automation/38-ssot-lint.sh` DOES NOT EXIST — author from scratch."**
   FALSE. It exists (194 lines): two-sided `${MIOS_*}` wiring lint asserting each
   Quadlet placeholder is wired in BOTH `tools/lib/userenv.sh` AND
   `automation/15-render-quadlets.sh`; read-only; `MIOS_SSOT_LINT_SOFT=1`
   advisory mode. A sibling test exists: `automation/tests/test-38-ssot-lint.sh`.

2. **"`38-ssot-lint`/pytest absent from `build.sh`."** FALSE. `build.sh` already
   wires, as POST-BUILD hard gates under `set -euo pipefail`:
   - `38-ssot-lint.sh` (lines ~361–373)
   - `38-drift-checks.sh` (lines ~375–386)
   - every `usr/lib/mios/agent-pipe/test_mios_*.py` run as `python3 <script>`
     (assert-scripts, NOT pytest-collectable), build dies on any non-zero (~388–417)
   - `usr/libexec/mios/test_mios_docgen.py` explicitly (~419–428)

3. **"`99-postcheck.sh` Law-5 is vendor-URL-only (no port/model patterns)."**
   FALSE. Law-5 now has §12 (vendor URLs), **§12b** (retired `:11434` local-lane
   check, lines ~423–451), and **§12c** (dispatch-target recursion guard). The
   WS-0A1 "extend Law-5 to lane/port/model literals" work is already present.

4. **"WS-0A must be split into 0A1/0A2 and built."** Largely MOOT. The
   drift-freeze gate is already implemented and wired:
   - `38-drift-checks.sh` (294 lines): `check_dead_lane` (retired :11434),
     `check_retired_models` (gemma4 / qwen3:1.7b in a consumer),
     `check_structured` (ai/v1 manifest parse + schema), `check_hint_coverage`
     (WS-10 AI-hint coverage), `check_module_boundary` (WS-3 sibling-imports-monolith).
   - 18 `test_mios_*.py` suites exist (plan said 10): a2a_passport, aci,
     codemode, compound, egress, evict, goap, hitl, k3s, kvfork, lanes, launch,
     mtls, pg, reputation, sched, selfimprove, stress.

## Net correction to the workstream tracker

- **WS-3 / WS-A11 (#15):** re-scope to **27,311** lines; `patch*.py` deletion is
  a confirmed no-op (already struck in the merged entry). The
  `check_module_boundary` gate that enforces the decomposition boundary already
  exists — WS-3's job is to *populate* it by extracting modules, not to author it.
- **WS-0A (#4):** reclassify from "build the gate" to **"verify the existing gate
  is complete + observe the suites once."** The gate (`38-ssot-lint.sh`,
  `38-drift-checks.sh`, in-build test runner, Law-5 §12b/§12c) already ships and
  is wired. Remaining genuine delta, if any: confirm each gate's coverage matches
  the WS-0A2 round-trip acceptance and that all 18 suites are green in the VM.
- **WS-10 (#31):** `check_hint_coverage` already exists; CI rebuild-test gate
  partly satisfied.

## Cannot-verify-here (operator action)

The 18 `test_mios_*.py` suites import the Linux agent-pipe stack and need the
VM's Python env (host is Python 3.14 with no `pytest`, and the tests can't import
`server.py`'s Linux deps). **Per operator rule, the VM/operator runs them.**
"Run once to observe before gating" is satisfied in the build path (the gate runs
them every build); the host cannot reproduce it.

## Soft-fail rollout (still binding for any NEW gate)

Any *new* build-failing fitness-function added by later workstreams must ship
behind a warn-only window first (`MIOS_*_SOFT=1` / `[ai].catalog_fail_mode="warn"`)
and be observed green before flipping to hard-fail under `set -euo pipefail`.
The existing gates already follow this (`MIOS_SSOT_LINT_SOFT`).
