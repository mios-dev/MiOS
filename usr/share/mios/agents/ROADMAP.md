# MiOS Frontier — Roadmap (A2O War-Room)

> Scoped roadmap for the **mios-frontier** workflow: the Architect→Operator (A2O)
> tmux war-room that runs **inside the `mios-agents` code-server container**, in
> which an orchestrator agent delegates build/debug work to operator sub-agents,
> each in its own live lane, with humans watching/steering through the same
> code-server terminal (the "glass wall"). Companion to `ACTIVATION.md` (bring-up)
> and the repo-root `ROADMAP.md` / `TASKS.md`. Detailed tasks: `./TASKS.md`.
>
> **Honesty rule (inherited):** DONE = **active + live-fired** in the container,
> not "built + gated-off", not "done-by-code", not introspection-only. Anything
> shipped-but-inert is a gap, tracked as such.
>
> **Binding laws:** NO-HARDCODE (models / efforts / panes / ports flow from
> `mios.toml [agents.frontier]`, never literals in the harness) · everything
> streams natively to every surface · credentials mounted at runtime, **never
> baked** · Law 6 (Quadlet `User=/Group=/Delegate`) · Claude-the-builder never
> live-launches — it extends the code paths; the operator opens the war-room.

---

## 1. What mios-frontier is

`mios-frontier` is a thin shim over `mios-a2o frontier`. `mios-a2o` is an
engine-aware terminal-muxer harness (dispatch / status / tail / capture / send /
repl / follow / doctor / selftest / frontier). The **frontier** profile lays out
a persistent tmux session as a **war-room**:

```
┌──────────────────────────┬─────────────────────────────┐
│                          │  LANE A  — sub-agent (live) │
│  ORCHESTRATOR            ├─────────────────────────────┤
│  (main panel, interactive)│  LANE B  — sub-agent (live) │
│                          ├─────────────────────────────┤
│                          │  MONITOR — all tasks/status  │
└──────────────────────────┴─────────────────────────────┘
```

The whole thing runs in **one container** (`mios-agents`) whose base image *is*
code-server, so the browser IDE and the tmux war-room share one filesystem and
one tmux socket — a human at the code-server terminal sees and steers exactly
what the agents see (the "glass wall"). `mios-agents` replaces the retired
`mios-code-server` (one IDE, no duplicate service).

**Engines** the harness can drive per role: `claude` (Claude Code CLI),
`agy` (Antigravity CLI → Gemini), `gemini` (Gemini CLI). Each is installed in the
image at a system path (`/usr/local/bin`) so the persistent `/home/coder` mount
cannot shadow it.

## 2. Target composition (operator spec)

| Role | Pane | Engine | Model | Reasoning effort |
|---|---|---|---|---|
| **Orchestrator** | main (left) | `claude` | Claude **Sonnet 5** (`claude-sonnet-5`) | high |
| **Sub-agent A** | right-top | `claude` | Claude **Opus 4.8** (`claude-opus-4-8`) | **xhigh** |
| **Sub-agent B** | right-mid | `agy` | **Gemini Flash 3.5** *(engine model id — verify)* | high |
| Monitor | right-bottom | — | — | — |

The orchestrator (Sonnet 5) runs interactively in the main panel and **delegates**
to the two sub-agent lanes (Opus 4.8, Gemini Flash 3.5) via `mios-a2o dispatch` /
the `lane-a` / `lane-b` convenience verbs; the lanes stream live; the monitor
shows all task state. Two `claude`-engine roles with **distinct models** (Sonnet 5
orchestrator vs Opus 4.8 sub-agent) is why the harness must key config on **role**,
not just engine.

## 3. Architecture & design principles

- **Role-based config, SSOT.** Each role = `{engine, model, effort}`, read from
  `MIOS_A2O_*` env, whose single documented baseline is the operator spec above,
  and whose real source of truth is `mios.toml [agents.frontier]` bridged into
  the container `Environment=`. No model/effort literal ever lives in the harness.
- **Reasoning effort is degrade-open.** Effort is passed via a per-engine flag
  *template* (`{e}` → the effort value); an empty template omits the flag, so an
  engine/CLI whose exact effort flag is unverified never breaks. Activation is a
  one-line SSOT change once the flag is confirmed in-container.
- **Orchestrator degrade-open.** If a role's engine binary is missing/unauthed,
  its pane falls back to a shell + `frontier-help` rather than a dead pane.
- **Credentials at runtime, never baked.** `agy` OAuth and Claude login are
  entered/mounted at run time (`podman exec -it … agy` / a mounted
  `~/.claude/.credentials.json` secret). The image ships zero secrets.
- **Glass wall.** One container, one tmux socket, one workspace (`/mnt/mios-root`
  = the deployed root, so the agents develop MiOS from within itself).
- **Everything streams.** Each lane's activity (dispatch, tool use, output,
  status) is live in its pane and tee'd to a per-task log; the war-room's state is
  observable via `status` / `follow` / `tail` / `capture` without attaching.
- **Least privilege.** The Quadlet honors Law 6 where the base image allows;
  `MIOS_A2O_AUTO=1` (auto-approve operator tools) is confined to this container
  and requires explicit operator authorization.

## 4. Phases

**Phase 0 — Super-container baked ✅ (verify live).** `mios-agents` image
(Containerfile: code-server + tmux + Claude CLI + agy + `mios-a2o` + `mios-frontier`),
`[containers.mios-agents.*]` SSOT, pod membership, tmpfiles `/var/lib/mios/agents`,
bound-images symlink, `mios-agents.service` enabled (replacing `mios-code-server`).
*Status: assets present + service enabled; confirm the image builds and the
container serves the IDE + a working `mios-a2o doctor` in-container.*

**Phase 1 — Role-based harness (F-001, F-003).** Replace the per-engine-only model
vars with `{orchestrator, lane_a, lane_b}` roles each carrying engine+model+effort;
refactor `exec_line` to accept model+effort; add the degrade-open effort-flag
template. *Status: designed; not yet coded.*

**Phase 2 — Frontier profile = orchestrator + sub-agent lanes (F-002, F-005).**
Rework `cmd_frontier`: main pane runs the orchestrator engine interactively
(model+effort pinned, degrade to shell if missing); lanes A/B follow the two
sub-agent roles; monitor unchanged. Add `lane-a`/`lane-b` convenience dispatch that
resolves to the sub-agent role config. Pane titles show `engine:model (effort=…)`.
*Status: designed; not yet coded.*

**Phase 3 — SSOT + env-bridge (F-004, F-008).** Add `[agents.frontier]` to
`mios.toml`; bridge the keys into `[containers.mios-agents].Environment` via
`install.env` / `mios-sync-env`; SSOT the canonical model ids. *Status: not built.*

**Phase 4 — Reasoning-effort activation (F-010).** Confirm each engine CLI's real
effort flag in-container and set the SSOT template; verify Opus 4.8 = xhigh,
Gemini Flash 3.5 = high actually take effect. *Status: blocked on live verify.*

**Phase 5 — Full-surface streaming (F-011).** Surface the war-room's live activity
beyond the tmux panes: mirror lane status/thinking to the MiOS reasoning channel
so OWUI/CLI/Discord can watch the frontier (ties into the everything-streams
mandate). *Status: not built.*

**Phase 6 — Identity, security, hardening (F-007, F-009, F-012).** `mios-agents`
in the security allowlist ✅; credential-mount flow; `MIOS_A2O_AUTO` confinement;
Law-6 posture; selftest/CI. *Status: allowlist done; rest partial.*

**Phase 7 — Advanced orchestration (F-013+).** Parallel fan-out beyond two lanes,
per-task checkpointing/resume, orchestrator↔sub-agent structured hand-off (A2A),
cost/turn budgets, and a "completeness critic" lane. *Status: future.*

## 5. Relationship to the MiOS roadmap

mios-frontier is the human-facing face of the A2O program: the repo-root
`TASKS.md` **T-010** (war-room rework) is the umbrella; the sub-agent
visibility work (FV-*) and constrained-tool-calling (T-111) apply to the lanes;
the native-typed-launch-args mandate (T-119) governs how the harness exposes its
own verbs. This file decomposes the war-room into shippable frontier tasks.

## 6. Open questions / verify points (do NOT guess — confirm in-container)

- **Gemini Flash 3.5 model id** for the `agy`/`gemini` engine (`--model` value).
- **Per-CLI reasoning-effort flag** for `claude`, `agy`, `gemini` (the F-010
  blocker; kept degrade-open until confirmed).
- **Port**: `MIOS_PORT_AGENTS` — ACTIVATION cites `8801`, the live dashboard shows
  `8800`; reconcile the SSOT.
- Whether the orchestrator should **dispatch** to lanes or run a nested tool-loop
  that spawns them (Phase 2 vs Phase 7 shape).
