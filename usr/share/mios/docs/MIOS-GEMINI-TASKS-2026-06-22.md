<!-- AI-hint: Task list for Antigravity/Gemini (Gemini 3.2 Pro, High). The pod-consolidation + build-pipeline + docs + low-residual half of MIOS-ROADMAP-2026-06-22.md, chosen to be DISJOINT from the files Claude is editing concurrently (server.py + mios.toml [agents]/[ai]/[cost] + the opencode gateway + hermes-worker). Read MIOS-ROADMAP-2026-06-22.md for full per-task detail.
     AI-related: ./MIOS-ROADMAP-2026-06-22.md, ../mios.toml, ../../../../tools/generate-pod-quadlets.py, ../../../containers/systemd -->
# MiOS — Gemini (Antigravity) task list — 2026-06-22

Companion to **`MIOS-ROADMAP-2026-06-22.md`** (read it for full per-task detail,
acceptance criteria, and the honest claim-vs-reality register). These are the
tasks chosen for **Gemini 3.2 Pro (High)** — structural refactors, the build
pipeline, docs, and the low-risk residual.

## ⛔ File ownership boundary (avoid clobbering the concurrent Claude session)

Claude is **concurrently editing** these — **DO NOT touch them**:
- `usr/lib/mios/agent-pipe/server.py`
- `usr/share/mios/mios.toml` **sections** `[agents.*]`, `[agents._defaults]`, `[ai]`, `[cost]`
- `usr/libexec/mios/opencode-gateway/server.py`
- `usr/lib/systemd/system/hermes-worker.service`
- `automation/38-drift-checks.sh`
- the OWUI firstboot wiring (`mios-open-webui-firstboot` / `mios-hermes-firstboot`)

**Gemini owns** (these files, no overlap): all `usr/share/containers/systemd/*.container`
+ `*.pod` quadlets, `mios.toml` section **`[pods.*]`** only, `tools/generate-pod-quadlets.py`,
the build-pipeline render scripts, `usr/share/doc/mios/**` docs, `usr/libexec/mios/mios-window`,
`C:\mios-bootstrap\build-mios.ps1`, and the A2A `agent.json`/card source.

> When editing `mios.toml`, ONLY add/edit the `[pods.*]` block(s). Leave every
> other section alone — Claude is rewriting `[agents.*]` in the same file.

---

## G-TASK 1 — Pod consolidation (WS-C) — the main one (DONE)

Goal: collapse standalone containers into 7 capability pods, minimize the external
port surface, all driven from the EXISTING `tools/generate-pod-quadlets.py` (which
already reads `[pods.*]` and renders only `mios-webtools.pod` today).

### 1a (do FIRST, standalone) — code-server `:8080` → `:8800`
- `usr/share/containers/systemd/mios-code-server.container`: set `Environment=BIND_ADDR=0.0.0.0:8800` **and** add the entrypoint arg override `--bind-addr 0.0.0.0:8800` (the image ENTRYPOINT wins over the env var — it MUST be at the arg layer), update the 3 `:8080` Labels + header comment to `:8800`. `[ports].code_server=8800` already matches.
- **Accept:** `ss -ltnp | grep 8800` binds; `:8080` is free; editor reachable. This unblocks all pod co-residency (it's the lone live `:8080` squatter).

### 1b — Add the `[pods.*]` SSOT blocks to `mios.toml` (the `[pods.*]` section ONLY)
Mirror `[pods.mios-webtools]`'s schema (`description / network / after / wants / wanted_by / members[] / doc`). Create:
- `[pods.mios-ai-inference]` — members: `mios-llm-light` (+ `mios-cpu-node`◇, `mios-llm-worker@`◇)
- `[pods.mios-ai-heavy]`◇ — `mios-llm-heavy`, `mios-llm-heavy-alt`
- `[pods.mios-ai-data]` — `mios-pgvector`
- `[pods.mios-devforge]` — `mios-forge`, `mios-forgejo-runner`, `mios-code-server`
- `[pods.mios-netinfra-dns]` — `mios-adguard`
- `[pods.mios-remote-desktop]`◇ — `mios-guacamole`, `mios-guacd`, `mios-guacamole-postgres`
Keep `mios-webtools`. Leave `mios-open-webui` + `mios-searxng` **standalone** (front door / lifecycle).

### 1c — `Pod=` membership on each member `.container` + render
Add `Pod=<pod>.pod` to each member `.container`; run `python3 tools/generate-pod-quadlets.py` to render the new `.pod` quadlets; `systemctl daemon-reload`.
- **Accept:** `generate-pod-quadlets.py --check` → no drift; `podman pod ls` shows the pods (the un-gated ones) Running with their members; every health check green. **Hard constraints:** two containers in one pod may NOT bind the same port; `mios-ai-data` (pgvector :5432) must NOT co-pod with `mios-guacamole-postgres` (also :5432). The AI **brains** (hermes-agent, agent-pipe, mcp, prefilter, opencode-gateway, hermes-browser, ttyd) are **host services — leave them host-native**, pods reach them via `host.containers.internal`.

### 1d — Port minimization
De-publish `mios-searxng` `:8888` to loopback (it's consumed only by host hermes); drop `mios-llm-heavy-alt`'s stray `PublishPort=...:11440`. Target: ~24 raw host binds → ~8 deliberate front doors.

## G-TASK 2 — WS-0B port collapse (build-time render) — the still-open one (DONE)
*Claim-vs-reality: prior "WS-0B port collapse DONE" is **FALSE** — 6 quadlets hardcode `PublishPort` literals; `install.env` has zero `MIOS_PORT_*`; systemd can't `${}`-expand TOML.*
Build the render: a build-pipeline step (a new `automation/NN-render-ports.sh` or a Containerfile sed pass) that reads `[ports]` from `mios.toml` and writes `MIOS_PORT_*=...` into `install.env`, with each quadlet's `PublishPort`/endpoints using `${MIOS_PORT_*}` + an `EnvironmentFile`. **Accept:** no hardcoded port literal remains in any `.container`; `grep MIOS_PORT_ install.env` is non-empty; the drift-check Claude adds (A2) catches a bare `:PORT`.

## G-TASK 3 — Docs honesty reconciliation (WS-G) (DONE)
In `usr/share/doc/mios/concepts/**`, re-tag the over-claimed items (WS-0B port collapse, "opencode council peer DONE", kernel Stage-2 "DONE", memory-tiering, governance gates) from "DONE/CLOSED" to **built-but-gated / partial / introspection-only**, citing the engineering-blueprint (the honest artifact). Fix the stale `agent.json` description still saying "SurrealDB-state chain" (post-pgvector-cutover) — find the A2A card source + update.

## G-TASK 4 — Low residual (WS-F4) (DONE)
- `usr/libexec/mios/mios-window`: add a LOCAL actuator for the named-region positions (left/right/top/bottom/corners) so `move_window`/`position_window` work on WSL when the `:11437` executor is absent (compute the region rect from `screen_layout`/monitor geometry → `mios-pc-control window-move`/`window-resize`). Currently only `center`/numeric fall back locally.
- `C:\mios-bootstrap\build-mios.ps1`: the generated `mios build` driver-staging step (~7110) hardcodes `/mnt/m` + a WARN-only fallback — add the curl-fallback the menu path (~1730) already has (compute the mount from the resolved letter; if the driver isn't `-x`, `curl -fsSL` the canonical raw URL).

## Notes
- Per operator rules: commit to `main`, no feature branches; no hardcoded English/values that belong in the SSOT; full-offline posture; Tailscale stays OFF.
- Validate quadlet edits don't break `bootc container lint` (Law 4) and respect Law 6 (unprivileged quadlets) + the documented root exceptions.
- When done with a task, mark it in this file and commit.
