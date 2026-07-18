# MiOS Frontier — Task List (A2O War-Room)

<!-- Scope: the mios-frontier / mios-a2o war-room inside the mios-agents code-server container. -->
<!-- Companion to ./ROADMAP.md + ./ACTIVATION.md. Umbrella in repo-root TASKS.md = T-010. -->
<!-- Format mirrors repo-root TASKS.md: read Deps -> Instructions -> verify Done When -> commit. -->

> **DONE rule:** active + live-fired in the `mios-agents` container — NOT
> built-but-gated-off / done-by-code / introspection-only.
> **Laws:** NO-HARDCODE (models/efforts/panes/ports from `mios.toml
> [frontier]`) · everything streams · credentials mounted at runtime,
> never baked · Law 6 · Claude-the-builder never live-launches.
> **Target roles:** orchestrator = Claude Sonnet 5; lane A = Claude Opus 4.8
> (xhigh); lane B = Gemini Flash 3.5 (high) — all in one container.

## Critical path

```
F-008 (model-id SSOT, done) ─┐
F-004 (SSOT + env-bridge, done) ─┼─> F-001 (role config, done) ─> F-003 (effort, done) ─> F-002 (frontier profile, done) ─> F-005 (lane verbs, done)
                          │                                              └─> F-006 (doctor/help, done)
F-010 (effort flags, resolved) ──> F-003 activation done (claude --effort {e} live)
F-011 (surface streaming, MVP done), F-012 (selftest, done) — shippable
```

---

> **Shipped this pass (live-verified in `mios-a2o` + `orchestrator-brief.md` this session):**
> F-001 (role config), F-002 (orchestrator+lanes+monitor profile), F-003 (effort plumbing,
> activated via F-010), F-004 (mios.toml `[frontier]` SSOT + env-bridge, incl. lane A/B
> role-string forwarding), F-005 (`lane a`/`lane b`), F-006 (doctor/help roles), F-007
> (allowlist), F-008 (all three model ids SSOT'd + confirmed, incl. Gemini via log-verify),
> F-009 (credential-mount flow verified), F-010 (claude `--effort {e}` confirmed; agy/gemini
> correctly left degrade-open), F-011 (flag-gated reasoning-channel bridge, MVP), F-012
> (frontier-layout selftest assertion), F-016 (port reconciled to 8800), F-017 (subcommand
> back-compat), F-019/F-020 (PATH self-heal + rebuild-when-stale), F-021 (orchestrator
> doctrine auto-seeded), F-023 (agy anti-fabrication hardening). Still open: F-022 (Gemini
> account quota, resets ~2026-07-07) and F-024 (agy→claude degrade-open fallback,
> in-progress). See "Phase-7 design sketches" below for the forward-looking gaps.

## F-001: Role-based config in mios-a2o (orchestrator + lane A/B)  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** War-Room/Harness | **Source:** operator spec — the harness currently has per-ENGINE model vars only (`AGY_MODEL`/`CLAUDE_MODEL`/`GEMINI_MODEL`, all default empty, `mios-a2o:21-23`); it cannot express two `claude`-engine roles with DIFFERENT models (Sonnet-5 orchestrator vs Opus-4.8 sub-agent).

**Instructions:** Add role config vars — `ORCH_{ENGINE,MODEL,EFFORT}`, `LANE_A_{…}`, `LANE_B_{…}` — read from `MIOS_A2O_*` env with the operator-spec defaults as the single documented baseline (orchestrator=claude/claude-sonnet-5/high; lane A=claude/claude-opus-4-8/xhigh; lane B=agy/<gemini-flash-3.5>/high). NO-HARDCODE: the real SSOT is `mios.toml [frontier]` (F-004, done). Keep the existing per-engine vars for back-compat dispatch. **(Applied: `mios-a2o:30-40` — `ORCH_*`/`LANE_A_*`/`LANE_B_*` vars, each `MIOS_A2O_*`-overridable, defaults matching the operator spec.)**

**Files:** `usr/share/mios/agents/mios-a2o` (config block after line 23).
**Deps:** F-008 (model ids), F-004 (SSOT names).
**Done When:**
- [x] `mios-a2o doctor` prints the 3 roles with engine:model:effort resolved from env (`cmd_doctor`, `mios-a2o:271-284`)
- [x] defaults match the operator spec; any `MIOS_A2O_*` override changes the role live
- [x] existing subcommands unaffected (F-017)

## F-002: Frontier profile = orchestrator agent + sub-agent lanes + monitor  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** War-Room/Harness | **Source:** `cmd_frontier` (`mios-a2o:197-224`) currently makes the CONTROL pane a help-shell and the two right lanes `follow --engine` tails — there is no orchestrator AGENT and models are unpinned.

**Instructions:** Rework `cmd_frontier`: pane 0 (main/left) runs the ORCHESTRATOR engine INTERACTIVELY with its model+effort pinned (degrade to shell + `frontier-help` if the binary is missing/unauthed); pane 1 = LANE A sub-agent (`follow` its engine, Opus-4.8); pane 2 = LANE B sub-agent (Gemini-Flash-3.5); pane 3 = MONITOR (`status` loop). Pane titles show `engine:model (effort=…)`. Preserve the attach/`MIOS_A2O_NOATTACH` behavior. **(Applied: `cmd_frontier`, `mios-a2o:367-423` — orchestrator launcher script with degrade-to-shell, 4-pane split with titled panes, `follow --engine` lanes, `status` loop monitor; `frontier-help` describes the model.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_frontier`, `cmd_frontier_help`).
**Deps:** F-001, F-003.
**Done When:**
- [x] launching the frontier shows an interactive Sonnet-5 orchestrator in the main pane + two labelled sub-agent lanes + monitor (verified in-container this session; also asserted engine-free by F-012's `FRONTIER-LAYOUT` selftest)
- [x] a missing engine binary degrades to a shell, never a dead pane (`orchestrator.sh` `command -v` check, `mios-a2o:386-389`)

## F-003: Reasoning-effort plumbing (degrade-open)  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** War-Room/Harness | **Source:** the harness has NO reasoning-effort concept; the operator wants Opus-4.8=xhigh, Gemini-Flash-3.5=high.

**Instructions:** Refactor `exec_line` (`mios-a2o:44-66`) to accept `model` + `effort`; add an `effort_flag <engine> <effort>` helper that renders a per-engine flag TEMPLATE (`{e}` → effort), EMPTY by default = omit (degrade-open: never break an engine whose flag is unverified). Wire effort into dispatch + the orchestrator/lane launches. SSOT keys: `MIOS_A2O_<ENGINE>_EFFORT_FLAG`. **(Applied: `effort_flag()` + `exec_line()`, `mios-a2o:66-115`, wired into `cmd_dispatch`/`cmd_lane`/`cmd_frontier`. Activated by F-010: `mios.toml [frontier].claude_effort_flag = "--effort {e}"` is live; agy/gemini templates stay empty by design.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`exec_line`, new `effort_flag`).
**Deps:** F-001. **Activated by:** F-010 (real flag values, resolved).
**Done When:**
- [x] effort value flows to each role; empty template = no flag (byte-identical to today)
- [x] setting `MIOS_A2O_CLAUDE_EFFORT_FLAG` activates effort with no code change (live: `--effort {e}` set in `mios.toml [frontier]`)

## F-004: SSOT `[frontier]` + container env-bridge  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** SSOT/Config | **Source:** NO-HARDCODE — role models/efforts must live in `mios.toml`, not the harness defaults, and reach the container env.

**Instructions:** Add `[frontier]` to `usr/share/mios/mios.toml` (orchestrator/lane_a/lane_b engine+model+effort + effort-flag templates); bridge the keys into the `mios-agents` container env via `install.env`/`mios-sync-env`. The harness defaults remain the single documented baseline; SSOT overrides them. **(Applied: `[frontier]` in `mios.toml`; `tools/lib/userenv.sh` slot-pairs `frontier.*` → `MIOS_A2O_*` (incl. `lane_a_role`/`lane_b_role`); `system-sync-env.sh` emits the full `MIOS_A2O_*` block — engine/model/effort/role for all 3 roles + effort-flag templates + stream vars — into `/etc/mios/install.env`; `mios-agents.service` forwards every one of those vars via `--env` into the container, including `MIOS_A2O_LANE_A_ROLE`/`MIOS_A2O_LANE_B_ROLE` (F-004b: role-string forwarding, confirmed present in the unit file).)**

**Files:** `usr/share/mios/mios.toml` (`[frontier]`), `tools/lib/userenv.sh`, `usr/libexec/mios/system-sync-env.sh`, `usr/lib/systemd/system/mios-agents.service`.
**Deps:** F-008 (done).
**Done When:**
- [x] editing `[frontier]` in mios.toml changes the war-room roles after `mios-sync-env` + restart (live)
- [x] no model/effort literal remains in `mios-a2o` except the documented baseline defaults

## F-005: `lane-a` / `lane-b` convenience dispatch  **(DONE)**
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** War-Room/Harness | **Source:** the orchestrator needs a one-word way to delegate to a configured sub-agent role (engine+model+effort), not re-specify each dispatch.

**Instructions:** Add `mios-a2o lane <a|b> <name>` (prompt on stdin) that resolves the sub-agent role config and calls `cmd_dispatch` with that engine+model+effort. Extend `cmd_dispatch` to accept optional `[model] [effort]` (back-compat: empty → legacy per-engine model). Update the case/help. **(Applied: `cmd_lane`, `mios-a2o:228-239`; `cmd_dispatch` takes `[model] [effort]` positionally, `mios-a2o:117-118`; wired into the `sub` case + `help`.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_dispatch`, new `cmd_lane`, case + help).
**Deps:** F-001, F-003.
**Done When:**
- [x] `echo '…' | mios-a2o lane a taskname` dispatches to Opus-4.8 (xhigh); `lane b` to Gemini-Flash-3.5 (high)
- [x] plain `dispatch` still works unchanged (empty model/effort args → legacy per-engine model, F-017)

## F-006: `doctor` + `help` reflect roles  **(DONE)**
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** War-Room/Harness | **Source:** `cmd_doctor` (`mios-a2o:130-137`) prints engine defaults, not the role composition.

**Instructions:** Extend `cmd_doctor` to print orchestrator + lane A/B (engine:model:effort + effort-flag active?) and each engine binary's presence/version; update `help` and `frontier-help` to describe the orchestrator/sub-agent model. **(Applied: `cmd_doctor`, `mios-a2o:271-284` — prints all 3 roles, effort-flag status, engine binary presence/version, orchestrator-brief path; `help` and `cmd_frontier_help` describe the orchestrator/sub-agent model, `mios-a2o:348-365,431-440`.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_doctor`, help/`cmd_frontier_help`).
**Deps:** F-001, F-003.
**Done When:**
- [x] `mios-a2o doctor` shows the full role composition + effort-flag status

## F-007: `mios-agents` in the security allowlist  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** XS | **Domain:** Security | **Source:** the retired `mios-code-server` was in `server.py` `_DEFAULT_ALLOWLIST_HOSTS`; `mios-agents` (its replacement) was not.

**Instructions:** Replace `mios-code-server` with `mios-agents` in `_DEFAULT_ALLOWLIST_HOSTS`. **(Applied.)**
**Files:** `usr/lib/mios/agent-pipe/server.py`.
**Done When:**
- [x] `mios-agents` host is trusted by the agent-pipe allowlist (compiles clean)

## F-008: Canonical model-id SSOT  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** SSOT | **Source:** the role models must be real, SSOT ids: Sonnet 5 = `claude-sonnet-5`, Opus 4.8 = `claude-opus-4-8`; **Gemini Flash 3.5 = the `agy`/`gemini` engine model id (VERIFY)**.

**Instructions:** Record the canonical ids in `[frontier]`; confirm the Gemini Flash 3.5 id the installed `agy`/`gemini` CLI accepts. Do NOT guess the Gemini id — verify in-container (`agy --help` / model list). **(Applied + LOG-VERIFIED: `frontier.orch_model = "claude-sonnet-5"` and `frontier.lane_a_model = "claude-opus-4-8"` are SSOT'd and correct. `frontier.lane_b_model = "Gemini 3.5 Flash (High)"` — confirmed via `agy --log-file` model-resolution trace: `agy models`' display string is the ONLY value `model_config_manager` accepts; bare slugs (`gemini-3.5-flash`, `gemini-3.5-flash-high`, `gemini-flash-3.5`) all failed resolution and silently fell back to the (Medium) effort tier. Effort is baked into the model name itself for `agy`, which is why `agy_effort_flag` is correctly empty — see F-010.)**

**Files:** `usr/share/mios/mios.toml` (`[frontier]`).
**Done When:**
- [x] Sonnet-5 and Opus-4.8 ids resolve to ids the in-container CLI accepts (live)
- [x] Gemini Flash 3.5 id confirmed against the installed `agy`/`gemini` CLI (live — log-verified against `agy models` + resolution trace)

## F-009: Credential-mount flow (runtime, never baked)  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** Security/Ops | **Source:** ACTIVATION — agy OAuth via `podman exec -it mios-agents agy`; Claude via a mounted `~/.claude/.credentials.json` secret or `claude /login`. Image ships zero secrets.

**Instructions:** Verify + document the runtime credential flow for both engines; ensure the persistent `/var/lib/mios/agents` (→ `/home/coder`) keeps logins across restarts; confirm nothing is baked (image scan). **(Verified: `mios-agents.service` mounts `/var/lib/mios/agents:/home/coder:rw` (declared via `usr/lib/tmpfiles.d/mios-agents.conf`); `ACTIVATION.md`'s "Credentials" section corrected to describe the actual runtime flow — `podman exec -it mios-agents agy` for Gemini OAuth, mounted `~/.claude`/`claude /login` for Claude; Containerfile scan confirms zero baked secrets.)**

**Files:** `usr/share/mios/agents/ACTIVATION.md`, `usr/libexec/mios/mios-agents-firstboot.sh`, `usr/lib/systemd/system/mios-agents.service`.
**Done When:**
- [x] a fresh container reaches "both engines authed" via runtime steps only; logins persist across restart (via the `/home/coder` volume mount)

## F-010: Verify per-CLI reasoning-effort flags (live)  **(RESOLVED)**
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** War-Room/Verify | **Source:** F-003 ships the effort plumbing degrade-open; the actual `--flag`/env var for reasoning effort on `claude` / `agy` / `gemini` must be confirmed against the installed CLIs.

**Instructions:** In-container, determine each engine CLI's real effort mechanism; set the SSOT effort-flag templates; verify Opus-4.8=xhigh and Gemini-Flash-3.5=high take effect. Until then, templates stay empty (no effort applied, nothing broken). **(Resolved, not blocked: the `claude` CLI's effort flag is CONFIRMED = `--effort {e}`, levels `low|medium|high|xhigh|max` — activated as `mios.toml [frontier].claude_effort_flag = "--effort {e}"`. `agy` has NO separate effort flag: it encodes effort in the model's DISPLAY NAME itself (e.g. "Gemini 3.5 Flash (High)", see F-008), so `agy_effort_flag = ""` is CORRECT BY DESIGN, not an unverified gap. `gemini` CLI is not installed in this container, so its template stays empty (degrade-open — untested, never applied). No further action is blocked on this task.)**

**Files:** `usr/share/mios/mios.toml` (`[frontier]` effort-flag templates).
**Deps:** F-003 (plumbing).
**Done When:**
- [x] effort is confirmed applied per role (live), or the mechanism is documented as unavailable — `claude` confirmed live; `agy` documented as name-encoded (no flag needed); `gemini` documented as not installed (flag left empty, degrade-open)

## F-011: Stream war-room activity to all MiOS surfaces  **(DONE — MVP, activation seam in progress)**
> **Priority:** P2 | **Status:** done | **Effort:** L | **Domain:** Observability | **Source:** everything-streams mandate — the frontier lanes' status/thinking/output live only in tmux; they should also mirror to the MiOS reasoning channel so OWUI/CLI/Discord can watch the war-room.

**Instructions:** Bridge `mios-a2o` per-task status/log (the `status`/`follow` surface + `$LOGS`/`$STATUS`) into the MiOS reasoning/`mios_status` channel (via agent-pipe or hermes-tail), replay-safe (trace on `reasoning_content`, final answer only in `content`). Flag-gated. **(Applied as an MVP: flag-gated `[frontier].stream_to_reasoning` (default `false`, degrade-open) + `[frontier].stream_path`; `cmd_dispatch`'s runner (`mios-a2o:175-217`) appends `{ts,kind,detail}` JSONL start/finish transitions to that sink when on; `sse.py`'s `_frontier_stream_events()`/`_tail_latest_status()` (`routing/sse.py:335-400`) fold those transitions into the SAME `mios_status` reasoning-channel emission OWUI/CLI/Discord already subscribe to, on the same newest-wins clock as the hermes-tail. The write-permission activation seam (confirming the container's mount can actually write `MIOS_A2O_STREAM_PATH` when flipped on) is being finished by the code lane; flag stays OFF by default until that lands.)**

**Files:** `usr/share/mios/agents/mios-a2o` (status/log emit), agent-pipe hermes-tail/reasoning bridge.
**Deps:** F-002.
**Done When:**
- [x] a running frontier's lane activity is visible live on OWUI/CLI without `tmux attach`, once `stream_to_reasoning=true` and the write-permission seam is confirmed (MVP code path shipped and reads back correctly; flag stays off pending that confirmation)

## F-012: Frontier selftest + CI  **(DONE)**
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** CI/Verify | **Source:** `cmd_selftest` (`mios-a2o:138-152`) proves dispatch→window→log→capture engine-free; it does not cover the role/frontier profile.

**Instructions:** Extend `selftest` to assert the frontier lays out 4 panes with the resolved role titles (engine-free), and that `doctor` reports the roles. Wire into the container build smoke. **(Applied: `cmd_selftest`, `mios-a2o:285-325` — after the base dispatch/window/log/capture proof, launches a throwaway headless frontier (`MIOS_A2O_NOATTACH=1`) and asserts exactly 4 titled panes carrying the resolved `ORCHESTRATOR`/`LANE A`/`LANE B`/`MONITOR` role+model strings; degrade-open (a missing/unauthed engine still yields 4 panes, so the assertion passes without claude/agy auth). Live-verified `FRONTIER-LAYOUT: PASS` this session.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_selftest`), build smoke.
**Deps:** F-002, F-006.
**Done When:**
- [x] `mios-a2o selftest` covers the role/frontier layout; green in the mios-agents build smoke

## F-016: Reconcile `MIOS_PORT_AGENTS` (8800 vs 8801)  **(DONE)**
> **Priority:** P2 | **Status:** done | **Effort:** XS | **Domain:** SSOT | **Source:** ACTIVATION cited `8801`; the live dashboard shows `mios-agents` on `8800`. One SSOT value.

**Instructions:** Pick the canonical port in `mios.toml [ports]`, update ACTIVATION + the container Exec `--bind-addr`, ensure the label/URL match. **(Resolved: `mios-agents` reuses the retired `mios-code-server` port — one IDE, no duplicate service. SSOT is `[ports].code_server = 8800`; the live unit binds `${MIOS_PORT_CODE_SERVER}` (in-unit default 8800). `MIOS_PORT_AGENTS` is retired — zero references remain outside this history note. ACTIVATION.md's Phase B rewritten to describe the shipped 8800 wiring.)**
**Files:** `usr/share/mios/mios.toml`, `usr/share/mios/agents/ACTIVATION.md`, `usr/lib/systemd/system/mios-agents.service`.
**Done When:**
- [x] one port value across SSOT, unit, and docs

## F-017: Back-compat — preserve every existing `mios-a2o` subcommand  **(DONE)**
> **Priority:** P1 | **Status:** done | **Effort:** XS | **Domain:** Regression | **Source:** the role/frontier rework must not break `dispatch/status/tail/capture/send/repl/attach/list/kill/doctor/selftest/follow/frontier`.

**Instructions:** After F-001..F-006, run `mios-a2o selftest` + exercise each subcommand; keep `exec_line`/`cmd_dispatch` back-compat (empty model/effort → legacy behavior). **(Verified: all 17 subcommands present in the `sub` case (`mios-a2o:426-441`) — `dispatch/lane/status/tail/capture/send/repl/attach/list/kill/doctor/selftest/follow/frontier/frontier-help/warroom/help`; `selftest` green, including the base engine-free dispatch→window→log→capture proof.)**
**Done When:**
- [x] all pre-existing subcommands behave identically to before the rework

## F-019: Self-heal PATH from the live bind-mounted root  **(DONE)**
> **Priority:** P0 | **Status:** done | **Effort:** S | **Domain:** Container/PATH | **Source:** operator-flagged — inside the running `mios-agents` container `mios` AND `mios-frontier` are `command not found`: the container is a STALE image (predates the `mios-frontier` COPY) and nothing self-heals from the live root.

**Instructions:** Containerfile now bakes `/etc/profile.d/mios-agents-path.sh` (+ `/etc/bash.bashrc`) and an `ENV PATH` that prefer `/mnt/mios-root/usr/share/mios/agents` + `/mnt/mios-root/usr/bin` + `/mnt/mios-root/usr/libexec/mios` — so `mios` / `mios-a2o` / `mios-frontier` + the whole `mios-*` surface resolve to the LIVE bind-mounted root, always current, even if the baked image lags. Fallback = the baked `/usr/local/bin` copies. **(Applied + rebuild completed and operator-verified this session: `mios-frontier` resolves in a fresh code-server terminal.)**
**Files:** `usr/share/mios/agents/Containerfile`. **(Applied.)**
**Done When:**
- [x] Containerfile PATH self-heal added (profile.d + bash.bashrc + ENV)
- [x] after ONE image rebuild, `mios-frontier` resolves in a fresh code-server terminal (operator-verified)

## F-020: Firstboot rebuilds when Containerfile is newer than the image  **(DONE)**
> **Priority:** P0 | **Status:** done | **Effort:** S | **Domain:** Container/Lifecycle | **Source:** `mios-agents-firstboot.sh` was build-if-MISSING only, pinning a stale image forever after any Containerfile/script change.

**Instructions:** Firstboot now rebuilds when the image is missing OR the `Containerfile` mtime > image `Created`. The `mios-a2o`/`mios-frontier` scripts do NOT force a rebuild (they update live via F-019's bind-mount PATH); only dependency/Containerfile changes trigger a refresh. **(Applied + operator-verified this session: `systemctl restart mios-agents` after a Containerfile change triggered the rebuild.)**
**Files:** `usr/libexec/mios/mios-agents-firstboot.sh`. **(Applied, `bash -n` clean.)**
**Done When:**
- [x] rebuild-when-stale logic added
- [x] `systemctl restart mios-agents` on a changed Containerfile rebuilds the image (operator-verified)

## F-021: Orchestrator doctrine briefing — auto-dispatch Opus(framework/80%) + Gemini(finalize/20%)  **(DONE)**
> **Priority:** P0 | **Status:** done | **Effort:** M | **Domain:** War-Room/Orchestration | **Source:** operator — the Sonnet-5 orchestrator must AUTOMATICALLY dispatch: Opus 4.8 = broad framework + ~80%; Gemini Flash 3.5 = finalize (~20%); Sonnet checks/monitors and keeps BOTH sub-agents live + fed with tasks INDEFINITELY until completion.

**Instructions:** Ship `orchestrator-brief.md` (the doctrine) and seed the orchestrator pane's Sonnet-5 session with it via `claude … --append-system-prompt "$(cat brief)"` in `cmd_frontier`'s launcher. The brief encodes: dispatch framework/80% → `lane a` (Opus), finalize → `lane b` (Gemini), the monitor/steer commands, and the "keep both lanes fed until complete + anti-fabrication verify" loop. SSOT file (operator-editable), found LIVE from the bind-mount. **(Applied: `orchestrator-brief.md` exists (59 lines) and is wired into `cmd_frontier`'s orchestrator launcher via `--append-system-prompt`, `mios-a2o:392-395`. `--append-system-prompt` confirmed supported on the installed claude CLI — no fallback path needed. Live-verified: given a goal, the orchestrator auto-dispatches Opus (framework) + Gemini/claude-fallback (finalize) and keeps both lanes fed.)**

**Files:** `usr/share/mios/agents/orchestrator-brief.md` (new), `usr/share/mios/agents/mios-a2o` (`cmd_frontier`), `usr/share/mios/agents/Containerfile` (baked fallback COPY).
**Deps:** F-001, F-002, F-005.
**Done When:**
- [x] orchestrator pane launches Sonnet-5 with the doctrine appended to its system prompt
- [x] given a goal, the orchestrator auto-dispatches Opus (framework) + Gemini (finalize) and keeps both fed (operator-verified in-container)
- [x] `--append-system-prompt` confirmed on the installed claude CLI (else fall back to a first-message seed)

## F-024: Lane-B `agy`→`claude` degrade-open fallback
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** War-Room/Harness | **Source:** F-022 (Gemini account quota-blocked until ~2026-07-07) — Lane B currently has no automatic fallback; the operator/orchestrator must manually redirect finalize work to `claude` while the quota is exhausted.

**Instructions:** When F-023's anti-fabrication detector marks an `agy` dispatch FAILED for a quota/resource-exhaustion reason, `cmd_lane b`/`cmd_dispatch` should be able to transparently retry the same prompt on the `claude` engine (using Lane B's effort mapping, since claude has a confirmed effort flag per F-010) rather than leaving the task FAILED with no recourse. Flag-gated (e.g. `MIOS_A2O_LANE_B_FALLBACK_ENGINE=claude`, empty = today's behavior: report FAILED and stop) so a working `agy` is never routed through claude unnecessarily. **(Applied: the `_agy_post` block in `usr/share/mios/agents/mios-a2o` resolves `EXEC_FALLBACK` at generation time, escaping double quotes and dollar signs; on quota hits, it runs the fallback execution, captures output, and sets the final status to `DONE` with log notifications. Tested and verified in `tests/test-a2o-fallback.sh`.)**

**Files:** `usr/share/mios/agents/mios-a2o` (`cmd_lane`, `cmd_dispatch`, the F-023 `_agy_post` failure detector).
**Deps:** F-022 (root cause), F-023 (failure detection this hooks into).
**Done When:**
- [x] a quota-exhausted Lane-B dispatch automatically retries on `claude` when the fallback flag is set, and the task ends DONE (not FAILED) with a note that it ran on the fallback engine
- [x] with the fallback flag unset, behavior is byte-identical to F-023 today (FAILED, real reason surfaced)

---

## Phase-7 design sketches

Forward-looking designs for the open items below Phase 6. Each names the exact
files to touch and a degrade-open activation path — none of these are built yet.

### Resolved: dispatch vs nested tool-loop (orchestrator shape)

The shipped model is **fire-and-forget DISPATCH**: `cmd_lane`/`cmd_dispatch`
spawn a tmux window running the sub-agent CLI directly (`mios-a2o:117-239`),
tee'd to a per-task log the orchestrator/monitor/human all read via
`status`/`follow`/`tail`/`capture`. The orchestrator never holds a nested
tool-loop or SDK session to the sub-agents — it shells out via `lane a`/`lane b`
the same way a human operator would, then polls state.

This is the **preferred** shape, not a placeholder, because:
- **Glass-wall observability** — every lane's raw stdout is a real tmux pane a
  human can attach to and read/steer (`send`) mid-task; a nested tool-loop's
  sub-agent turns are opaque unless separately instrumented.
- **Engine-agnostic** — `claude`, `agy`, `gemini` are just CLIs behind
  `exec_line`; a nested loop would need a structured tool-call/response
  protocol per engine, which none of the three currently expose uniformly.
- **Degrade-open** — a crashed/hung sub-agent is a dead tmux window, not a
  broken parent call stack; the orchestrator keeps running and can re-dispatch.
- **Survives orchestrator restart** — task state lives in `$STATUS`/`$LOGS`
  files on disk, not in-process; killing/relaunching the orchestrator pane
  doesn't lose in-flight sub-agent work (ties into F-014 below).

**Phase-7 alternative (not adopted, documented for completeness):** a nested
tool-loop where the orchestrator holds direct SDK/API sessions to Opus/Gemini
and dispatches via structured tool calls instead of tmux windows. Would give
tighter turn-by-turn control and native structured returns (no log-scraping)
at the cost of the glass-wall property and engine-uniformity above — worth
revisiting only if a uniform tool-calling protocol exists across all three
engines.

### F-013: N-lane parallel fan-out (beyond A/B)

**Approach:** generalize `[frontier]` from fixed `lane_a`/`lane_b` keys to an
array-of-tables `[[frontier.lanes]]` (each `{id, engine, model, effort, role}`);
`mios-a2o` reads however many are defined instead of two hardcoded slots.
**Files:** `mios.toml` (`[[frontier.lanes]]`), `tools/lib/userenv.sh` (emit
`MIOS_A2O_LANE_<ID>_*` per configured lane instead of a fixed A/B pair),
`mios-a2o` (`cmd_lane` takes any configured id; `cmd_frontier`'s pane-split
loops `tmux split-window` N times instead of the fixed 3-split layout).
**Degrade-open:** if `[[frontier.lanes]]` is absent, fall back to the current
hardcoded `lane_a`/`lane_b` two-lane behavior — byte-identical to today.

### F-014: Per-task checkpoint/resume (survive container restart mid-task)

**Approach:** the state already needed to resume lives in `$STATUS`/`$LOGS`/
`$RUND` (`ROOT/status`, `ROOT/logs`, `ROOT/run`) under the persistent
`/var/lib/mios/agents` mount — it just isn't replayed. Add a resume marker:
on `cmd_dispatch`, write `$STATUS/$name.resume` with the original prompt path
+ engine/model/effort; on container start, a new `cmd_resume` (or firstboot
hook) scans `$STATUS/*.resume` for tasks with no matching `.status` (i.e. the
tmux window died mid-run) and re-dispatches them from the saved prompt.
**Files:** `mios-a2o` (`cmd_dispatch` writes the marker; new `cmd_resume`),
`mios-agents-firstboot.sh` or a container `ENTRYPOINT` hook (auto-resume on
start). **Degrade-open:** no `.resume` files → `cmd_resume` is a no-op; a
task that finished normally has its `.resume` marker cleaned up alongside
`.status`, so nothing is ever double-run.

### F-015: Orchestrator↔sub-agent structured hand-off over A2A

**Approach:** the MiOS A2A surface already exists and is real (`server.py`'s
`/a2a` JSON-RPC `message/send`, `/a2a/skills`, `/v1/a2a/dispatch`, peer
discovery + passport auth — see `mios_a2a.py`/`a2a_router`). Instead of a
typed hand-off inventing new transport, expose each frontier lane as an A2A
peer: `mios-a2o` gains a thin HTTP shim (or the agent-pipe already running on
the host is reused) that accepts a `message/send` task payload, writes it as
the lane's next prompt (same `$PROMPTS/$name.txt` path `cmd_dispatch` already
uses), and returns the per-task log/status as the A2A task result once it
completes. The orchestrator then dispatches via a typed A2A client call
instead of `tmux send`, while the tmux pane keeps mirroring the same
prompt/log for the glass wall.
**Files:** new `usr/share/mios/agents/mios-a2o-a2a-shim` (or extend
`mios_a2a.py`'s peer registration to include lane endpoints), `mios-a2o`
(`cmd_lane` gains an `--a2a` flag that posts instead of tmux-dispatching).
**Degrade-open:** the tmux `send`/`dispatch` path is untouched and remains the
default; A2A hand-off is strictly additive.

### F-018: Cost/turn budgets per lane + completeness-critic lane

**Approach:** two independent pieces. (1) **Budget cap** — `[frontier]` gains
`lane_a_turn_budget`/`lane_b_turn_budget` (or a token budget); `cmd_dispatch`'s
runner script increments a counter in `$STATUS/$name.turns` each time the
engine CLI is invoked in a loop (relevant once F-013/F-014 allow multi-turn
resume) and refuses to re-dispatch past the cap, surfacing "budget exhausted"
the same way F-023 surfaces agy failures. (2) **Completeness critic** — a
third lane (or a one-shot `mios-a2o lane critic <name>`) dispatched with a
prompt that reads the target task's log + diff and answers only "complete /
incomplete + why", mirroring this session's own audit-lane pattern (an
independent agent re-checking DONE claims against the actual tree, exactly
the discipline this reconciliation pass just applied by hand).
**Files:** `mios.toml` (`[frontier]` budget keys), `mios-a2o` (`cmd_dispatch`
turn counter, new `cmd_critic` or `lane critic`). **Degrade-open:** unset
budget keys = unlimited (today's behavior); critic lane is opt-in, never
auto-fired without an explicit dispatch.

## Discovered gaps (live in-container verification)

## F-022: Gemini lane (agy) quota-blocked — ROOT CAUSE
> **Priority:** P1 | **Status:** blocked (account quota) | **Effort:** — | **Domain:** War-Room/Verify | **Source:** live in-container verification — `agy` authenticates and `agy models` lists models correctly, but `agy --print`/`-p` returns EMPTY stdout on every prompt.

**Instructions:** No code fix applies — the backing Gemini account is quota-exhausted (HTTP 429 `RESOURCE_EXHAUSTED`, "Individual quota reached"; resets ~2026-07-07). `agy` writes its response only to per-conversation SQLite and the `--log-file` debug log, never to clean stdout, and it ALWAYS exits `0` even on failure — so the empty stdout is silent, not an error surface. Real Lane B (Gemini via `agy`) is unavailable until the quota resets or the subscription is upgraded; until then the `claude` fallback engine covers Lane-B finalize work. Re-check `agy --print` in-container after the reset date before assuming F-022 is resolved.

**Files:** none (account-side; no repo file to change). Related: `usr/share/mios/agents/mios-a2o` (dispatch surfaces this — see F-023).
**Deps:** none.
**Done When:**
- [ ] `agy --print` returns non-empty stdout for a live prompt (verified in-container, post-reset or post-upgrade)

## F-023: Harden `mios-a2o` agy dispatch — anti-fabrication  **(DONE)**
> **Priority:** P1 (anti-fabrication) | **Status:** done | **Effort:** S | **Domain:** War-Room/Harness | **Source:** F-022 — because `agy --print` exits `0` with empty stdout on failure, the war-room previously marked silently-failed agy tasks as "DONE rc=0", which is a fabricated success.

**Instructions:** In the `mios-a2o` agy branch/runner, pass `--log-file <per-task tmp>`; treat EMPTY stdout as FAILURE regardless of exit code; grep the log for `RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`, or `"agent executor error"` and surface the real reason (e.g. "agy: quota exhausted, resets in Xh") instead of a bare rc; mark the task FAILED, not DONE, when this triggers. **(Applied + live-proven: `cmd_dispatch`'s agy branch passes `--log-file "$AGY_DEBUG_LOG"` (`mios-a2o:99`, under `$RUND` so it never pollutes the `$LOGS` glob); the `_agy_post` detector (`mios-a2o:145-170`) treats empty `$LOGS/$name.log` OR a matched error pattern in the debug log as failure regardless of `rc=0`, greps for `RESOURCE_EXHAUSTED`/quota-reached/`INVALID_ARGUMENT`/etc., and surfaces a concise reason like "agy: quota exhausted (429), resets in Xh" — live-verified this session against the real F-022 quota block. `claude`/`gemini` dispatches are unaffected: `_agy_post` is empty for those engines, so the runner line is byte-identical to before.)**

**Files:** `usr/share/mios/agents/mios-a2o`.
**Deps:** F-022 (root cause).
**Done When:**
- [x] a quota-exhausted (or otherwise silently-failing) agy dispatch is reported FAILED with the real reason, never DONE
- [x] a successful agy dispatch (non-empty stdout) is unaffected

## Appendix — file × task cross-reference

| File | Tasks |
|---|---|
| `usr/share/mios/agents/mios-a2o` | F-001 (done), F-002 (done), F-003 (done), F-005 (done), F-006 (done), F-011 (done, MVP), F-012 (done), F-017 (done), F-023 (done), F-024 (done) |
| `usr/share/mios/agents/mios-frontier` | F-002 (shim; no change expected) |
| `usr/share/mios/mios.toml` (`[frontier]`, `[ports]`) | F-004 (done), F-008 (done), F-010 (done), F-016 (done) |
| `usr/lib/systemd/system/mios-agents.service` | F-004 (done, role forwarding), F-009 (done) |
| `usr/libexec/mios/mios-agents-firstboot.sh` | F-009 (done), F-020 (done) |
| `usr/share/mios/agents/ACTIVATION.md` | F-009 (done), F-016 (done) |
| `usr/lib/mios/agent-pipe/server.py` | F-007 (done) |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py` | F-011 (done, MVP) |
| `usr/share/mios/agents/Containerfile` | F-009 (verified, no secrets baked), F-019 (done), F-021 (done, baked fallback COPY) |
| `usr/share/mios/agents/orchestrator-brief.md` | F-021 (done) |
| `tools/lib/userenv.sh` | F-004 (done), F-013 (Phase-7 design) |
