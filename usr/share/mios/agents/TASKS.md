# MiOS Frontier — Task List (A2O War-Room)

<!-- Scope: the mios-frontier / mios-a2o war-room inside the mios-agents code-server container. -->
<!-- Companion to ./ROADMAP.md + ./ACTIVATION.md. Umbrella in repo-root TASKS.md = T-010. -->
<!-- Format mirrors repo-root TASKS.md: read Deps -> Instructions -> verify Done When -> commit. -->

> **DONE rule:** active + live-fired in the `mios-agents` container — NOT
> built-but-gated-off / done-by-code / introspection-only.
> **Laws:** NO-HARDCODE (models/efforts/panes/ports from `mios.toml
> [agents.frontier]`) · everything streams · credentials mounted at runtime,
> never baked · Law 6 · Claude-the-builder never live-launches.
> **Target roles:** orchestrator = Claude Sonnet 5; lane A = Claude Opus 4.8
> (xhigh); lane B = Gemini Flash 3.5 (high) — all in one container.

## Critical path

```
F-008 (model-id SSOT) ─┐
F-004 (SSOT + env-bridge) ─┼─> F-001 (role config) ─> F-003 (effort) ─> F-002 (frontier profile) ─> F-005 (lane verbs)
                          │                                              └─> F-006 (doctor/help)
F-010 (verify effort flags, live) ┄┄> unblocks F-003 activation
F-011 (surface streaming), F-012 (selftest) gate "shippable"
```

---

> **Shipped this pass (code-complete in `mios-a2o` + `orchestrator-brief.md`; live-verify pending):**
> F-001 (role config), F-002 (orchestrator+lanes+monitor profile), F-003 (effort plumbing,
> degrade-open), F-005 (`lane a`/`lane b`), F-006 (doctor/help roles), F-021 (orchestrator
> doctrine), F-019/F-020 (PATH self-heal + rebuild-when-stale). Remaining live-gated:
> F-004 (mios.toml SSOT), F-008 (Gemini id), F-010 (effort flags), F-009/F-016.

## F-001: Role-based config in mios-a2o (orchestrator + lane A/B)
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** War-Room/Harness | **Source:** operator spec — the harness currently has per-ENGINE model vars only (`AGY_MODEL`/`CLAUDE_MODEL`/`GEMINI_MODEL`, all default empty, `mios-a2o:21-23`); it cannot express two `claude`-engine roles with DIFFERENT models (Sonnet-5 orchestrator vs Opus-4.8 sub-agent).

**Instructions:** Add role config vars — `ORCH_{ENGINE,MODEL,EFFORT}`, `LANE_A_{…}`, `LANE_B_{…}` — read from `MIOS_A2O_*` env with the operator-spec defaults as the single documented baseline (orchestrator=claude/claude-sonnet-5/high; lane A=claude/claude-opus-4-8/xhigh; lane B=agy/<gemini-flash-3.5>/high). NO-HARDCODE: the real SSOT is `mios.toml [agents.frontier]` (F-004). Keep the existing per-engine vars for back-compat dispatch.

**Files:** `usr/share/mios/agents/mios-a2o` (config block after line 23).
**Deps:** F-008 (model ids), F-004 (SSOT names).
**Done When:**
- [ ] `mios-a2o doctor` prints the 3 roles with engine:model:effort resolved from env
- [ ] defaults match the operator spec; any `MIOS_A2O_*` override changes the role live
- [ ] existing subcommands unaffected (F-017)

## F-002: Frontier profile = orchestrator agent + sub-agent lanes + monitor
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** War-Room/Harness | **Source:** `cmd_frontier` (`mios-a2o:197-224`) currently makes the CONTROL pane a help-shell and the two right lanes `follow --engine` tails — there is no orchestrator AGENT and models are unpinned.

**Instructions:** Rework `cmd_frontier`: pane 0 (main/left) runs the ORCHESTRATOR engine INTERACTIVELY with its model+effort pinned (degrade to shell + `frontier-help` if the binary is missing/unauthed); pane 1 = LANE A sub-agent (`follow` its engine, Opus-4.8); pane 2 = LANE B sub-agent (Gemini-Flash-3.5); pane 3 = MONITOR (`status` loop). Pane titles show `engine:model (effort=…)`. Preserve the attach/`MIOS_A2O_NOATTACH` behavior.

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_frontier`, `cmd_frontier_help`).
**Deps:** F-001, F-003.
**Done When:**
- [ ] launching the frontier shows an interactive Sonnet-5 orchestrator in the main pane + two labelled sub-agent lanes + monitor (verified in-container by the operator)
- [ ] a missing engine binary degrades to a shell, never a dead pane

## F-003: Reasoning-effort plumbing (degrade-open)
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** War-Room/Harness | **Source:** the harness has NO reasoning-effort concept; the operator wants Opus-4.8=xhigh, Gemini-Flash-3.5=high.

**Instructions:** Refactor `exec_line` (`mios-a2o:44-66`) to accept `model` + `effort`; add an `effort_flag <engine> <effort>` helper that renders a per-engine flag TEMPLATE (`{e}` → effort), EMPTY by default = omit (degrade-open: never break an engine whose flag is unverified). Wire effort into dispatch + the orchestrator/lane launches. SSOT keys: `MIOS_A2O_<ENGINE>_EFFORT_FLAG`.

**Files:** `usr/share/mios/agents/mios-a2o` (`exec_line`, new `effort_flag`).
**Deps:** F-001. **Blocked-activation-by:** F-010 (real flag values).
**Done When:**
- [ ] effort value flows to each role; empty template = no flag (byte-identical to today)
- [ ] setting `MIOS_A2O_CLAUDE_EFFORT_FLAG` activates effort with no code change

## F-004: SSOT `[agents.frontier]` + container env-bridge
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** SSOT/Config | **Source:** NO-HARDCODE — role models/efforts must live in `mios.toml`, not the harness defaults, and reach the container env.

**Instructions:** Add `[agents.frontier]` to `usr/share/mios/mios.toml` (orchestrator/lane_a/lane_b engine+model+effort + effort-flag templates); bridge the keys into `[containers.mios-agents.Container].Environment` (per ACTIVATION Phase-B pattern) and/or `install.env` via `mios-sync-env`. The harness defaults remain the single documented baseline; SSOT overrides them.

**Files:** `usr/share/mios/mios.toml` (`[agents.frontier]`, `[containers.mios-agents].Environment`); `mios-sync-env`.
**Deps:** F-008.
**Done When:**
- [ ] editing `[agents.frontier]` in mios.toml changes the war-room roles after `mios-sync-env` + restart (live)
- [ ] no model/effort literal remains in `mios-a2o` except the documented baseline defaults

## F-005: `lane-a` / `lane-b` convenience dispatch
> **Priority:** P2 | **Status:** pending | **Effort:** S | **Domain:** War-Room/Harness | **Source:** the orchestrator needs a one-word way to delegate to a configured sub-agent role (engine+model+effort), not re-specify each dispatch.

**Instructions:** Add `mios-a2o lane <a|b> <name>` (prompt on stdin) that resolves the sub-agent role config and calls `cmd_dispatch` with that engine+model+effort. Extend `cmd_dispatch` to accept optional `[model] [effort]` (back-compat: empty → legacy per-engine model). Update the case/help.

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_dispatch`, new `cmd_lane`, case + help).
**Deps:** F-001, F-003.
**Done When:**
- [ ] `echo '…' | mios-a2o lane a taskname` dispatches to Opus-4.8 (xhigh); `lane b` to Gemini-Flash-3.5 (high)
- [ ] plain `dispatch` still works unchanged

## F-006: `doctor` + `help` reflect roles
> **Priority:** P2 | **Status:** pending | **Effort:** S | **Domain:** War-Room/Harness | **Source:** `cmd_doctor` (`mios-a2o:130-137`) prints engine defaults, not the role composition.

**Instructions:** Extend `cmd_doctor` to print orchestrator + lane A/B (engine:model:effort + effort-flag active?) and each engine binary's presence/version; update `help` and `frontier-help` to describe the orchestrator/sub-agent model.

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_doctor`, help/`cmd_frontier_help`).
**Deps:** F-001, F-003.
**Done When:**
- [ ] `mios-a2o doctor` shows the full role composition + effort-flag status

## F-007: `mios-agents` in the security allowlist  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** XS | **Domain:** Security | **Source:** the retired `mios-code-server` was in `server.py` `_DEFAULT_ALLOWLIST_HOSTS`; `mios-agents` (its replacement) was not.

**Instructions:** Replace `mios-code-server` with `mios-agents` in `_DEFAULT_ALLOWLIST_HOSTS`. **(Applied.)**
**Files:** `usr/lib/mios/agent-pipe/server.py`.
**Done When:**
- [x] `mios-agents` host is trusted by the agent-pipe allowlist (compiles clean)

## F-008: Canonical model-id SSOT
> **Priority:** P1 | **Status:** pending | **Effort:** S | **Domain:** SSOT | **Source:** the role models must be real, SSOT ids: Sonnet 5 = `claude-sonnet-5`, Opus 4.8 = `claude-opus-4-8`; **Gemini Flash 3.5 = the `agy`/`gemini` engine model id (VERIFY)**.

**Instructions:** Record the canonical ids in `[agents.frontier]`; confirm the Gemini Flash 3.5 id the installed `agy`/`gemini` CLI accepts. Do NOT guess the Gemini id — verify in-container (`agy --help` / model list).

**Files:** `usr/share/mios/mios.toml` (`[agents.frontier]`).
**Done When:**
- [ ] all three role models resolve to ids the in-container CLIs accept (live)

## F-009: Credential-mount flow (runtime, never baked)
> **Priority:** P1 | **Status:** partial | **Effort:** S | **Domain:** Security/Ops | **Source:** ACTIVATION — agy OAuth via `podman exec -it mios-agents agy`; Claude via a mounted `~/.claude/.credentials.json` secret or `claude /login`. Image ships zero secrets.

**Instructions:** Verify + document the runtime credential flow for both engines; ensure the persistent `/var/lib/mios/agents` (→ `/home/coder`) keeps logins across restarts; confirm nothing is baked (image scan).

**Files:** `usr/share/mios/agents/ACTIVATION.md`, `usr/libexec/mios/mios-agents-firstboot.sh`, `usr/lib/systemd/system/mios-agents.service`.
**Done When:**
- [ ] a fresh container reaches "both engines authed" via runtime steps only; logins persist across restart

## F-010: Verify per-CLI reasoning-effort flags (live)  **[BLOCKED — needs container]**
> **Priority:** P1 | **Status:** blocked | **Effort:** S | **Domain:** War-Room/Verify | **Source:** F-003 ships the effort plumbing degrade-open; the actual `--flag`/env var for reasoning effort on `claude` / `agy` / `gemini` must be confirmed against the installed CLIs.

**Instructions:** In-container, determine each engine CLI's real effort mechanism; set the SSOT effort-flag templates; verify Opus-4.8=xhigh and Gemini-Flash-3.5=high take effect. Until then, templates stay empty (no effort applied, nothing broken).

**Files:** `usr/share/mios/mios.toml` (`[agents.frontier]` effort-flag templates).
**Deps:** F-003 (plumbing).
**Done When:**
- [ ] effort is confirmed applied per role (live), or the mechanism is documented as unavailable

## F-011: Stream war-room activity to all MiOS surfaces
> **Priority:** P2 | **Status:** pending | **Effort:** L | **Domain:** Observability | **Source:** everything-streams mandate — the frontier lanes' status/thinking/output live only in tmux; they should also mirror to the MiOS reasoning channel so OWUI/CLI/Discord can watch the war-room.

**Instructions:** Bridge `mios-a2o` per-task status/log (the `status`/`follow` surface + `$LOGS`/`$STATUS`) into the MiOS reasoning/`mios_status` channel (via agent-pipe or hermes-tail), replay-safe (trace on `reasoning_content`, final answer only in `content`). Flag-gated.

**Files:** `usr/share/mios/agents/mios-a2o` (status/log emit), agent-pipe hermes-tail/reasoning bridge.
**Deps:** F-002.
**Done When:**
- [ ] a running frontier's lane activity is visible live on OWUI/CLI without `tmux attach`

## F-012: Frontier selftest + CI
> **Priority:** P2 | **Status:** partial | **Effort:** S | **Domain:** CI/Verify | **Source:** `cmd_selftest` (`mios-a2o:138-152`) proves dispatch→window→log→capture engine-free; it does not cover the role/frontier profile.

**Instructions:** Extend `selftest` to assert the frontier lays out 4 panes with the resolved role titles (engine-free), and that `doctor` reports the roles. Wire into the container build smoke.

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_selftest`), build smoke.
**Deps:** F-002, F-006.
**Done When:**
- [ ] `mios-a2o selftest` covers the role/frontier layout; green in the mios-agents build smoke

## F-016: Reconcile `MIOS_PORT_AGENTS` (8800 vs 8801)
> **Priority:** P2 | **Status:** pending | **Effort:** XS | **Domain:** SSOT | **Source:** ACTIVATION cites `8801`; the live dashboard shows `mios-agents` on `8800`. One SSOT value.

**Instructions:** Pick the canonical port in `mios.toml [ports]`, update ACTIVATION + the container Exec `--bind-addr`, ensure the label/URL match.
**Files:** `usr/share/mios/mios.toml`, `usr/share/mios/agents/ACTIVATION.md`, `[containers.mios-agents]`.
**Done When:**
- [ ] one port value across SSOT, unit, and docs

## F-017: Back-compat — preserve every existing `mios-a2o` subcommand
> **Priority:** P1 | **Status:** pending | **Effort:** XS | **Domain:** Regression | **Source:** the role/frontier rework must not break `dispatch/status/tail/capture/send/repl/attach/list/kill/doctor/selftest/follow/frontier`.

**Instructions:** After F-001..F-006, run `mios-a2o selftest` + exercise each subcommand; keep `exec_line`/`cmd_dispatch` back-compat (empty model/effort → legacy behavior).
**Done When:**
- [ ] all pre-existing subcommands behave identically to before the rework

## F-019: Self-heal PATH from the live bind-mounted root  **(DONE — needs one rebuild)**
> **Priority:** P0 | **Status:** done-by-code (rebuild-gated) | **Effort:** S | **Domain:** Container/PATH | **Source:** operator-flagged — inside the running `mios-agents` container `mios` AND `mios-frontier` are `command not found`: the container is a STALE image (predates the `mios-frontier` COPY) and nothing self-heals from the live root.

**Instructions:** Containerfile now bakes `/etc/profile.d/mios-agents-path.sh` (+ `/etc/bash.bashrc`) and an `ENV PATH` that prefer `/mnt/mios-root/usr/share/mios/agents` + `/mnt/mios-root/usr/bin` + `/mnt/mios-root/usr/libexec/mios` — so `mios` / `mios-a2o` / `mios-frontier` + the whole `mios-*` surface resolve to the LIVE bind-mounted root, always current, even if the baked image lags. Fallback = the baked `/usr/local/bin` copies.
**Files:** `usr/share/mios/agents/Containerfile`. **(Applied.)**
**Done When:**
- [x] Containerfile PATH self-heal added (profile.d + bash.bashrc + ENV)
- [ ] after ONE image rebuild, `mios-frontier` resolves in a fresh code-server terminal (operator-verified)

## F-020: Firstboot rebuilds when Containerfile is newer than the image  **(DONE)**
> **Priority:** P0 | **Status:** done | **Effort:** S | **Domain:** Container/Lifecycle | **Source:** `mios-agents-firstboot.sh` was build-if-MISSING only, pinning a stale image forever after any Containerfile/script change.

**Instructions:** Firstboot now rebuilds when the image is missing OR the `Containerfile` mtime > image `Created`. The `mios-a2o`/`mios-frontier` scripts do NOT force a rebuild (they update live via F-019's bind-mount PATH); only dependency/Containerfile changes trigger a refresh.
**Files:** `usr/libexec/mios/mios-agents-firstboot.sh`. **(Applied, `bash -n` clean.)**
**Done When:**
- [x] rebuild-when-stale logic added
- [ ] `systemctl restart mios-agents` on a changed Containerfile rebuilds the image (operator-verified)

## F-021: Orchestrator doctrine briefing — auto-dispatch Opus(framework/80%) + Gemini(finalize/20%)  **(DONE — live-verify)**
> **Priority:** P0 | **Status:** done-by-code | **Effort:** M | **Domain:** War-Room/Orchestration | **Source:** operator — the Sonnet-5 orchestrator must AUTOMATICALLY dispatch: Opus 4.8 = broad framework + ~80%; Gemini Flash 3.5 = finalize (~20%); Sonnet checks/monitors and keeps BOTH sub-agents live + fed with tasks INDEFINITELY until completion.

**Instructions:** Ship `orchestrator-brief.md` (the doctrine) and seed the orchestrator pane's Sonnet-5 session with it via `claude … --append-system-prompt "$(cat brief)"` in `cmd_frontier`'s launcher. The brief encodes: dispatch framework/80% → `lane a` (Opus), finalize → `lane b` (Gemini), the monitor/steer commands, and the "keep both lanes fed until complete + anti-fabrication verify" loop. SSOT file (operator-editable), found LIVE from the bind-mount. **(Applied.)**

**Files:** `usr/share/mios/agents/orchestrator-brief.md` (new), `usr/share/mios/agents/mios-a2o` (`cmd_frontier`), `usr/share/mios/agents/Containerfile` (baked fallback COPY).
**Deps:** F-001, F-002, F-005.
**Done When:**
- [x] orchestrator pane launches Sonnet-5 with the doctrine appended to its system prompt
- [ ] given a goal, the orchestrator auto-dispatches Opus (framework) + Gemini (finalize) and keeps both fed (operator-verified in-container)
- [ ] `--append-system-prompt` confirmed on the installed claude CLI (else fall back to a first-message seed)

---

## Future (Phase 7)
- **F-013** parallel fan-out beyond two lanes (N sub-agent lanes, dynamic).
- **F-014** per-task checkpoint / resume (survive container restart mid-task).
- **F-015** orchestrator↔sub-agent structured hand-off over A2A (typed tasks, not tmux `send`).
- **F-018** cost / turn budgets per lane; a "completeness critic" lane.

## Appendix — file × task cross-reference

| File | Tasks |
|---|---|
| `usr/share/mios/agents/mios-a2o` | F-001, F-002, F-003, F-005, F-006, F-011, F-012, F-017 |
| `usr/share/mios/agents/mios-frontier` | F-002 (shim; no change expected) |
| `usr/share/mios/mios.toml` (`[agents.frontier]`, `[containers.mios-agents]`, `[ports]`) | F-004, F-008, F-010, F-016 |
| `usr/lib/systemd/system/mios-agents.service` | F-009 |
| `usr/libexec/mios/mios-agents-firstboot.sh` | F-009 |
| `usr/share/mios/agents/ACTIVATION.md` | F-009, F-016 |
| `usr/lib/mios/agent-pipe/server.py` | F-007 (done) |
| `usr/share/mios/agents/Containerfile` | F-009 (verify installs) |
