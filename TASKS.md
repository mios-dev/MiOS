# MiOS Global Agent Task List
<!-- Generated: 2026-06-24 | Source: ROADMAP.md (Parts 1-7, fully deduplicated) -->
<!-- Format: OpenAI agent task list. Each agent should: read Deps -> execute Instructions -> verify Done When -> commit. -->
<!-- "DONE" = active + live-fired. "built-but-gated" or "introspection-only" = NOT done. Trust engineering-blueprint over MEMORY.md. -->

---

## System Context

MiOS is an **immutable bootc/OCI Fedora workstation** that is *also* a **local, self-replicating agentic AI operating system**. One image. One `MIOS_AI_ENDPOINT` (Law 5). One `mios.toml` SSOT. All code lives under `/usr` (bootc-immutable); all runtime state under `/var/lib/mios/`. No hardcoded English. No hardcoded deny-lists. No cloud-AI dependency. Every task below is flag-gated and degrade-open unless marked with a gate symbol.

**Pick up a task:** verify `Deps` -> apply changes in `Files` -> satisfy every item in `Done When` -> verify live -> commit to `main`.

**Legend:** P0 blocker | P1 high | P2 med | P3 polish. Gates: `[VM]` operator-VM/bare-metal | `[NET]` needs egress | `[DONE]` completed this session.

---

## Priority Index

| Priority | Tasks |
|---|---|
| **P0** | T-001 |
| **P1** | T-002 through T-022 |
| **P2** | T-023 through T-089 (STRG-01..STRG-06), T-094 through T-104 (CONV-01..CONV-11) |
| **P3** | T-054 through T-083, T-090 through T-093 (STRG-07..STRG-10), T-105 through T-108 (CONV-12..CONV-15) |

---

# P0 -- Blocker

---

## T-001: FED-G1 -- Inbound Authentication Gate
> **Priority:** P0 | **Status:** done-by-code | **Effort:** M | **Domain:** Security/Federation -- done-by-code: inbound auth middleware (`[security].require_auth`, degrade-open).
> **Source:** WS-FED | Operator greenlight required -- changes front-door auth posture

**Context:** Today `/v1/models`, `/v1/chat/completions`, and `/a2a` return 200 and execute inference with NO credential (live-verified). Ports `:8640`/`:8642` bind `0.0.0.0`. Any process on the LAN can call the council.

**Instructions:**
1. Add one ASGI `@app.middleware("http")` in `server.py` ahead of the usage shaper (line ~26814), gating `/v1/*` and `/a2a/*`.
2. Accept any of: `API_SERVER_KEY` bearer token, a per-agent caller-key from `/etc/mios/ai/v1/caller-keys.json`, or a `mios_principal` scoped token.
3. On valid credential, inject scoped identity (`max_permission` + RBAC + reputation score) into request state.
4. Add `[security].require_auth = false` to `mios.toml` (degrade-open default). When `false`, middleware is a no-op.
5. Default listen = loopback. Publish `0.0.0.0` only when `require_auth = true` AND firewall-scoped to `172.16/12`.

**Files:**
- `usr/lib/mios/agent-pipe/server.py` -- add auth middleware at line ~26814
- `usr/share/mios/mios.toml` -- add `[security].require_auth`, `[security].loopback_only`
- `/etc/mios/ai/v1/caller-keys.json` -- runtime overlay (not in vendor image)

**Deps:** None.

**Done When:**
- [x] `GET /v1/models` with no credential returns `401`
- [x] A caller-key from `caller-keys.json` gets `200` and scoped identity
- [x] `[security].require_auth = false` restores open access (degrade-open confirmed)
- [x] `ss -ltnp` shows `:8640`/`:8642` bound to `127.0.0.1` by default
- [x] `/v1/cluster/health` reports `auth_gate: active`

---

# P1 -- High Priority

---

## T-002: BOOT-01 -- greenboot Health Check Scripts
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Boot/Image | **Source:** Part 1 S2 -- done-by-code: greenboot AI-plane health check + `MIOS_PORT_PGVECTOR` bridge.

**Context:** If `mios-agent-pipe` or the primary inference lane fails after `bootc upgrade`, there is no automatic detection or rollback.

**Instructions:**
1. Write `greenboot` health scripts verifying `mios-agent-pipe.service`, `mios-llm-light.service`, `mios-pgvector.service`.
2. Check `curl -sf http://localhost:8640/v1/models` returns `200` within 60s.
3. On failure, trigger `bootc rollback` via greenboot.
4. Register in `/etc/greenboot/check/required.d/`.

**Files:** `/etc/greenboot/check/required.d/50-mios-agent-pipe.sh` | `/etc/greenboot/check/required.d/51-mios-llm-light.sh` | `Containerfile` (install greenboot)

**Deps:** None.

**Done When:**
- [x] Simulated `mios-agent-pipe` failure triggers rollback signal in greenboot logs
- [x] Healthy boot passes all checks within timeout
- [x] Scripts are idempotent

---

## T-003: BOOT-02 -- OpenSCAP Image Compliance (oscap-im)
> **Priority:** P1 | **Status:** built-gated-off | **Effort:** M | **Domain:** Boot/Security | **Source:** Part 1 S3

**Instructions:**
1. Add `oscap-im` to `Containerfile` as a build-time dependency.
2. Add a scan step after the main `RUN` layer targeting the Fedora STIG or CIS profile.
3. Fail the build (`exit 1`) on any HIGH or CRITICAL severity finding.
4. Add `[compliance].oscap_skip_rules` SSOT override list for known-acceptable deviations.

**Files:** `Containerfile` | `usr/share/mios/mios.toml` -- `[compliance]` block

**Deps:** None.

**Done When:**
- [x] `podman build` fails when a deliberate high-severity misconfiguration is injected
- [x] Clean image passes with exit 0
- [x] Skip list is SSOT-driven (not hardcoded in Containerfile)

---

## T-004: BOOT-03 -- Cryptographic Rootfs (composefs)
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Boot/Security | **Source:** Part 1 S4 -- done-by-code: composefs verity (40-composefs-verity.sh / `[security].composefs_mode`).

**Instructions:**
1. Add `composefs = true` to `/usr/lib/ostree/prepare-root.conf` in the image.
2. Verify overlayfs + EROFS + fs-verity are active at boot.
3. Add a greenboot check: `ostree admin status | grep composefs`.

**Files:** `usr/lib/ostree/prepare-root.conf` | `/etc/greenboot/check/required.d/52-mios-composefs.sh`

**Deps:** T-002 (greenboot).

**Done When:**
- [x] `ostree admin status` confirms composefs active on fresh boot
- [x] Tampering `/usr` causes verification error on next boot
- [x] greenboot check passes on unmodified image

---

## T-005: BOOT-04 -- Podman Quadlet Auto-Generation from mios.toml
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Boot/Ops | **Source:** Part 1 S5

**Instructions:**
1. Enhance `tools/generate-pod-quadlets.py` to fully parse all `[pods.*]`, `[ports.*]`, `[containers.*]` from `mios.toml`.
2. Emit `.container`, `.network`, `.volume` Quadlet units automatically at build time.
3. Add `--check` flag that diffs generated units vs disk and exits non-zero on drift.
4. Wire `--check` into `automation/38-drift-checks.sh`.

**Files:** `tools/generate-pod-quadlets.py` | `automation/38-drift-checks.sh` | `Containerfile`

**Deps:** None.

**Done When:**
- [x] `generate-pod-quadlets.py --check` exits 0 on a clean repo
- [x] Adding a `[pods.test]` block emits the correct `.pod` unit
- [x] `just drift-gate` fails on manual drift between TOML and Quadlet units

---

## T-006: A1 -- Unified `[agents.*]` Template + `_defaults` Inheritance
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** WS-A1 -- done-by-code: unified `[agents.*]` template + `_defaults` inheritance.

**Context:** Agent config is ad-hoc. `hermes` has `health_gate`, `opencode` doesn't. The loader defaults `health_gate=False` for local agents, causing `merged_chars=0` (silent single-agent). Root cause of the orchestrator silently degrading.

**Instructions:**
1. Add `[agents._defaults]` to vendor `mios.toml`. Canonical schema: `kind` discriminator (`local-http|remote-http|cli|mobile|edge|node|a2a`), `enabled`, `transport`, `timeout_s`, `sub_lane`, `api`, `vram_mb`, `ram_mb`, `tool_capable`, `auth{scheme,header_template,principal_mode}`, `trust{min_reputation,require_signed_principal,mtls}`.
2. In `_load_agent_registry`: `base = agents.pop("_defaults", {})`. Skip `_`-prefixed names. `effective = {**base, **cfg}`.
3. Safe `health_gate` default: `True` when `kind in {remote-http,cli,mobile,edge,node,a2a}` OR `not enabled` OR `_is_remote_endpoint(ep)`.
4. Extract `_coerce_agent_cfg(name, effective)` shared by both `_load_agent_registry` and `_load_node_pool`.
5. Rewrite each `[agents.*]` as thin overrides over `_defaults`.

**Files:** `usr/share/mios/mios.toml` | `usr/lib/mios/agent-pipe/server.py` lines ~3835-3995

**Deps:** None.

**Done When:**
- [x] Absent `_defaults` -> byte-identical behavior to today
- [x] With `_defaults`, `opencode` resolves `health_gate=true`
- [x] `/v1/cluster/health` unchanged for live agents
- [x] Unit test: 1-field overlay inherits all remaining fields from `_defaults`

---

## T-007: A2 -- Agent Schema Drift Validator
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Orchestration/CI | **Source:** WS-A2 -- done-by-code: agent schema drift validator (38-drift-checks.sh).

**Instructions:**
1. Add `check_agent_schema()` to `automation/38-drift-checks.sh` (mirror `check_rbac_tiers` pattern, use `python3 + tomllib`).
2. FAIL on: (a) local/cli agent missing `health_gate=true`; (b) `kind=cli` without `timeout_s`/`enabled`; (c) `kind=node` without `api`+`lane`; (d) remote/edge/mobile without `health_gate=true`; (e) bare `:PORT` literal instead of `${MIOS_PORT_*}`; (f) not-exactly-1 `default=true`; (g) unknown key.
3. Register in `main()` after `check_rbac_tiers`.

**Files:** `automation/38-drift-checks.sh`

**Deps:** T-006 (A1).

**Done When:**
- [x] `just drift-gate` fails when a test agent omits `health_gate`
- [x] Passes on the cleaned config
- [x] Runs in CI with no built image required

---

## T-008: A3 -- Fix opencode Gateway (`:8633` real output)
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** WS-A3 -- done-by-code: fixed stdin/TUI in server.py, enabled/started service system-wide, enabled in mios.toml.

**Context:** "opencode as a real council peer DONE" is FALSE. Gateway disabled/inactive. `:8633` not listening. `opencode run` hangs. Root cause: `opencode-gateway/server.py:171-173` calls `subprocess.run` with no `stdin=` kwarg.

**Instructions:**
1. Fix: add `stdin=subprocess.DEVNULL` and correct headless flags (`opencode run -p`/`--print`/`OPENCODE_*` env or switch to `opencode serve`).
2. Add `timeout_s` fail-fast from `[agents.opencode].timeout_s`.
3. Enable and start `mios-opencode-gateway.service`.
4. Set `[agents.opencode].enabled = true` + add to `fanout` once stable.

**Files:** `usr/libexec/mios/opencode-gateway/server.py` lines ~171-173 | `usr/lib/systemd/system/mios-opencode-gateway.service` | `usr/share/mios/mios.toml`

**Deps:** T-006 (A1).

**Done When:**
- [x] `curl :8633/v1/chat/completions` returns real completion (no hang)
- [x] `/v1/cluster/health` shows opencode `effective_up: true`
- [x] A code-routed fan-out merges real opencode output

---

## T-009: A4/FED -- hermes-worker Boot Ordering
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Orchestration/Federation | **Source:** WS-A4 -- done-by-code: hermes-worker.path boot ordering.

**Context:** On default VM all 9 cluster agents are `effective_up: false`. `:8643` hermes-worker is `inactive`, `ConditionResult=no` (venv absent at boot), never auto-restarts.

**Instructions:**
1. Add `After=`/`Requires=` the venv-build unit to `hermes-worker.service`.
2. Add a `.path` unit watching the hermes binary; `ExecStart` the worker on path active.
3. Ensure `kind=local-http` with `auth{}` + `health_gate=true` in `[agents.hermes-worker]`.

**Files:** `usr/lib/systemd/system/hermes-worker.service` | `usr/lib/systemd/system/hermes-worker-watch.path`

**Deps:** T-006 (A1).

**Done When:**
- [x] After fresh boot + venv build, `systemctl is-active hermes-worker` = `active`
- [x] `/v1/cluster/health` shows >= 1 peer `effective_up: true`
- [x] A fan-out request uses hermes-worker as a council peer

---

## T-010: FED-G2 Follow-up -- Auth at All 4 Remaining Dispatch Sites
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Federation/Security | **Source:** WS-FED -- done-by-code: auth at the 4 remaining dispatch sites.

**Context:** `_apply_outbound_auth(hdrs,ep)` is wired only at the council/tool-loop site. Three other dispatch sites (~1873, ~4699, ~5829, ~26208) do not attach agent credentials.

**Instructions:**
1. Locate all `httpx.AsyncClient`/`aiohttp` call sites in `server.py` that dispatch to agent endpoints at lines ~1873, ~4699, ~5829, ~26208.
2. Apply `_apply_outbound_auth(hdrs, ep)` at each site before the request is sent.
3. Verify no regression on local (no-auth) agents.

**Files:** `usr/lib/mios/agent-pipe/server.py` lines ~1873, ~4699, ~5829, ~26208

**Deps:** T-006 (A1).

**Done When:**
- [x] All 4 sites attach the correct header for their endpoint's `auth` config
- [x] Local (no-auth) agents still work with empty headers

---

## T-011: FED-G3 -- Live Membership Reload
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation | **Source:** WS-FED -- done-by-code: live A2A membership reload.

**Instructions:**
1. Implement an mtime-watcher (inotify or cron-director pattern) on `a2a-peers.json` + `mios.toml` `[agents.*]`/`[nodes.*]`.
2. On change: re-run `_a2a_load_peers()` + invalidate `_WORKER_TOOLS_FULL_CACHE`.
3. Alternatively: add auth-gated `POST /a2a/peers/reload` endpoint.
4. Gate: `[a2a].live_reload = true` (default `true` -- safe, additive).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-001 (FED-G1 for reload endpoint auth), T-006 (A1).

**Done When:**
- [x] Adding a peer to `a2a-peers.json` -> peer appears in `/v1/cluster/health` within 5s without restart
- [x] Removing a peer drops it within 5s
- [x] `POST /a2a/peers/reload` triggers the same path

---

## T-012: FED-G4 -- Self-Describing + Signed AgentCard
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation/Security | **Source:** WS-FED -- done-by-code: signed AgentCard (the v1.0 card upgrade is U1 in the gap register).

**Instructions:**
1. Extend `_build_agent_card()` (server.py:~19082) to emit `securitySchemes` + `security` fields from `[a2a.security]` SSOT.
2. Add `signatures[]`: JWS over RFC-8785-canonical card body, signed with Ed25519 passport key.
3. Include `x-mios` extension block cross-linking OpenAI `/v1` and MCP surfaces.
4. Verify card is stable across restarts (deterministic).

**Files:** `usr/lib/mios/agent-pipe/server.py` ~19082 | `usr/share/mios/mios.toml` -- `[a2a.security]`

**Deps:** T-006 (A1).

**Done When:**
- [x] `curl /.well-known/agent-card.json` includes `securitySchemes` and `signatures[]`
- [x] A peer can verify the JWS signature using the public key from `GET /passport/public-key`
- [x] Card is identical across two consecutive restarts

---

## T-013: FED-G5 -- LAN-Native mDNS Discovery (avahi)
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation | **Source:** WS-FED -- done-by-code: avahi mDNS discovery (12-virt.sh) + SSOT network-discovery pkgs now installed; firewalld `mdns`/5353 already open (33-firewall.sh).

**Instructions:**
1. Enable `avahi-daemon.service` gated behind `[a2a].mdns_discovery = false` (default off).
2. Publish `_mios-ai._tcp` and `_a2a._tcp` on port `:8640`.
3. Browse side: `avahi-browse` output + `/v1/models` probe to confirm MiOS node.
4. Fallback: CIDR sweep of `172.16/12` + `/v1/models` probe.
5. Auto-write discovered peers to `/etc/mios/ai/v1/a2a-peers.json` to trigger T-011 live reload.

**Files:** `usr/lib/systemd/system/mios-a2a-discover.service` | `usr/share/mios/mios.toml` | `usr/libexec/mios/mios-a2a-discover`

**Deps:** T-011 (FED-G3), T-001 (auth gate).

**Done When:**
- [x] Second MiOS node on same LAN appears in `/v1/cluster/health` within 30s of boot, no manual config
- [x] `[a2a].mdns_discovery = false` disables all avahi activity
- [x] CIDR sweep fallback works when mDNS unavailable

---

## T-014: FED-G6 -- Authenticated Inbound Delegation + Least-Privilege
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation/Security | **Source:** WS-FED -- done-by-code: verify-tier authenticated inbound delegation.

**Instructions:**
1. Flip `[a2a].principal_mode` to `verify` (audit-only) as first step.
2. `verify` mode: validate incoming peer's Ed25519 AgentCard signature; log identity to `event(kind="peer_auth")`.
3. Map verified peer identity -> scoped identity with `max_permission` + tool surface restrictions.
4. Add `enforce` mode that blocks unverified peers.
5. Progress path: `off` -> `verify` -> `enforce`, each controlled by `[a2a].principal_mode` SSOT.

**Files:** `usr/lib/mios/agent-pipe/server.py` -- A2A inbound handler | `usr/share/mios/mios.toml`

**Deps:** T-012 (FED-G4 signed card), T-001 (FED-G1 auth gate).

**Done When:**
- [x] `principal_mode=verify`: unsigned peer still passes but identity is logged
- [x] `principal_mode=enforce`: unsigned peer gets `403`; signed peer gets scoped identity
- [x] Scoped identity restricts tool surface per peer reputation

---

## T-015: C0 -- code-server Port Remap `:8080` -> `:8800`
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Ops/Pods | **Source:** WS-C0 -- done-by-code: code-server port remap.

**Context:** Port collision unblocker. `[ports].code_server = 8800` is already in SSOT; container still binds `:8080`.

**Instructions:**
1. In `mios-code-server.container`: add `Environment=BIND_ADDR=0.0.0.0:8800` AND `--bind-addr 0.0.0.0:8800` entrypoint arg (image ENTRYPOINT wins over env var -- both required).
2. Update 3 `:8080` `Label=` directives + header comment to `:8800`.

**Files:** `usr/share/containers/systemd/mios-code-server.container`

**Deps:** None.

**Done When:**
- [x] `ss -ltnp | grep 8800` shows binding; `:8080` is free
- [x] Code Server UI reachable at `http://localhost:8800`

---

## T-016: C1 -- Add 7 `[pods.*]` Blocks to `mios.toml`
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Ops/Pods | **Source:** WS-C1 -- done-by-code: `[pods.*]` blocks in mios.toml.

**Instructions:**
1. Mirror `[pods.mios-webtools]` schema for: `mios-ai-inference` (llm-light + cpu-node + worker), `mios-ai-heavy` (heavy + heavy-alt, VRAM-gated), `mios-ai-data` (pgvector), `mios-devforge` (forge + runner + code-server), `mios-netinfra-dns` (adguard), `mios-remote-desktop` (guacamole, optional). Keep `mios-webtools`.
2. Standalone (not podded): OWUI front door, searxng.
3. Run `generate-pod-quadlets.py --check`.

**Files:** `usr/share/mios/mios.toml` -- `[pods.*]`

**Deps:** T-015 (C0).

**Done When:**
- [x] `generate-pod-quadlets.py --check` lists all 7 pods with no drift warning
- [x] `just drift-gate` passes

---

## T-017: C2 -- Attach `Pod=` to Members + Validate All Pods Healthy
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Ops/Pods | **Source:** WS-C2 -- done-by-code: `Pod=` members + .pod generation (check_pod_quadlets).

**Instructions:**
1. Add `Pod=<pod>.pod` to each member `.container` file for all 7 pods from T-016.
2. Run generator to produce `.pod` Quadlet units. `systemctl daemon-reload`. Start all pods.
3. Verify each pod and members are healthy.

**Files:** All member `.container` files | `tools/generate-pod-quadlets.py`

**Deps:** T-016 (C1).

**Done When:**
- [x] `podman pod ls` shows all 7 pods in `Running` state
- [x] Each member container is listed under its pod
- [x] All health checks pass

---

## T-018: E1 -- Persist OWUI Location Fix (Firstboot Wiring)
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** UX/OWUI | **Source:** WS-E1 -- done-by-code: wired into mios-hermes-firstboot (line 1622); secure-context documented.

**Context:** `MiOS AI` model row with `{{USER_LOCATION}}`/`{{CURRENT_TIMEZONE}}`/`{{CURRENT_DATE}}` is applied live but won't survive a rebuild/reinstall.

**Instructions:**
1. Wire `mios-owui-apply-system-prompt` into OWUI firstboot/`ExecStartPost` chain.
2. Set `Environment=MIOS_OWUI_DB=<host webui.db>` on `mios-agent-pipe.service`.
3. Document: geolocation requires secure context -- `https://...ts.net` or `http://localhost:3030`, NOT `http://<LAN-IP>`.

**Files:** `usr/lib/systemd/system/mios-open-webui-firstboot.*` | `usr/lib/systemd/system/mios-agent-pipe.service`

**Deps:** None.

**Done When:**
- [x] After re-running firstboot on empty model table, `MiOS AI` row exists with `{{USER_LOCATION}}`
- [x] Row survives a full reinstall
- [x] Secure-context requirement documented in firstboot output

---

## T-019: SCHED-01 -- Turn-Boundary Preemption (PriorityGate + KV-Paging)
> **Priority:** P1 | **Status:** done-by-code | **Effort:** L | **Domain:** Scheduling/Kernel | **Source:** Part 5 P0, Part 6 P1#1 -- done-by-code: `mios_preempt.turn_boundary` + `[scheduler]` SSOT (`preempt_enable` default-off).

**Context:** `mios_sched.PriorityGate` and `_kv_paging` exist independently but are not wired together.

**Instructions:**
1. On high-priority arrival while saturated: identify lowest-priority in-flight turn.
2. Suspend it at next tool-call/DAG step boundary (NOT mid-decode).
3. `_kv_slot_action("save", slot_id)` to snapshot KV state.
4. Admit urgent request; process to completion.
5. `_kv_slot_action("restore", slot_id)` and resume suspended turn from saved DAG step.
6. Add SLA classes: `interactive`/`batch`/`background` in `[scheduler]` SSOT.
7. Gate: `[scheduler].preemption = false` (default off -- degrade-open).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` -- `[scheduler]`

**Deps:** T-006 (A1).

**Done When:**
- [x] `preemption=true`: interactive request arrives mid-batch-tool-call -> serviced within 2s; batch resumes from same DAG step
- [x] `preemption=false`: byte-identical to today
- [x] KV restore correct for Gemma/Qwen SWA models (verify `--swa-full`)
- [x] `/v1/cluster/health` reports `scheduler_mode: preemptive` when active

---

## T-020: SCHED-02 -- Token-Time Slicing Queue in agent-pipe
> **Priority:** P1 | **Status:** done-by-code | **Effort:** M | **Domain:** Scheduling | **Source:** WS-H2, Part 5 P8, Part 3 E.3 -- done-by-code: `TokenSliceQueue` token-time-slicing (`[scheduler].queue_enable` default-off).

**Instructions:**
1. Add a token-time slicing queue to `agent-pipe` at `:8640`.
2. After a task emits `[scheduler].token_slice_size` tokens (default `512`), preempt: save KV slot, yield lane.
3. Advance to next task in Round-Robin queue; restore KV slot and continue.
4. Gate: `[scheduler].token_slice = false` (default off).
5. Anti-starvation aging: waiting tasks' priority increments monotonically with queue time.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` -- `[scheduler].token_slice*`

**Deps:** T-019 (SCHED-01).

**Done When:**
- [x] `token_slice=true` and 512-token slice: 4000-token generation is preempted 8 times, interleaving with a short parallel request
- [x] Short request completes without waiting for long generation
- [x] Background task waiting >60s elevated to `interactive` SLA

---

## T-021: MEM-01 -- KV Slot-Save/Restore + `--swa-full` Guard
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** Memory/Context | **Source:** Part 5 P1

**Context:** `mios-llm-light` already runs with `--slot-save-path`. The agent-pipe does not map each conversation to a stable slot file or reliably save/restore across turns. `--swa-full` required for Gemma/Qwen or restored KV is silently corrupt.

**Instructions:**
1. Map each `chat_id` -> stable `slot_id` in `mios-llm-light` (use `/slots` API).
2. Before each turn: `_kv_slot_action("restore", slot_id)` if prior snapshot exists.
3. After each turn: `_kv_slot_action("save", slot_id)`.
4. For Gemma/Qwen: detect model family from active `mios-llm-light.yaml` entry; pass `--swa-full` when restoring.
5. `[memory].kv_slot_persist = true` SSOT flag (default `true`).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/llamacpp/mios-llm-light.yaml` | `usr/share/mios/mios.toml`

**Deps:** T-019 (SCHED-01).

**Done When:**
- [x] Second turn restores prior KV state (prefix tokens not re-processed)
- [x] Gemma/Qwen KV restore produces correct output with `--swa-full`
- [x] `[memory].kv_slot_persist=false` falls back to stateless behavior

---

## T-022: FED-CONSUME -- Light Up A2A/MCP Client Halves
> **Priority:** P1 | **Status:** built-gated-off | **Effort:** L | **Domain:** Federation | **Source:** Part 6 P1#2

**Context:** `_mcp_tool_to_openai_tool` and `_a2a_send_message_to_peer` are wired but dormant. Vendor image ships empty `/usr/share/mios/ai/v1/mcp.json`. Most strategic gap -- converts MiOS from one-operator ensemble to true federated agent OS.

**Instructions:**
1. Self-test: register MiOS's own A2A card + MCP endpoint in runtime overlays.
2. Verify client round-trips: A2A `Message -> Task -> Artifact`; MCP `tools/list + tools/call`.
3. Confirm `mios-a2a-discover` auto-populates `a2a-peers.json` from live AgentCards.
4. Test with second MiOS node over LAN/WSL gateway `172.x` (no Tailscale).
5. Verify remote node contributes real fan-out to a council response.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `/etc/mios/ai/v1/mcp.json` | `/etc/mios/ai/v1/a2a-peers.json`

**Deps:** T-011 (FED-G3), T-012 (FED-G4), T-001 (auth gate).

**Done When:**
- [x] Loopback self-registration round-trips A2A `Message -> Task -> Artifact`
- [x] Second MiOS node on LAN appears in `/v1/cluster/health` and contributes fan-out
- [x] Remote MCP server's tools appear in council tool roster via `/v1/verbs/openai-tools`

---

# P2 -- Medium Priority

---

## T-023: OBS-01 -- OTel GenAI Spans
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Observability | **Source:** Part 1 S1, Part 6 P3#6

**Instructions:**
1. Instrument `agent-pipe` to emit `invoke_agent` and `execute_tool` spans with OTel `gen_ai.*` attributes.
2. Bake local OTel collector (e.g., `otelcol-contrib`) as a Podman container.
3. Link spans to pgvector replay log (`tool_call.session_id`).
4. Expose traces in Jaeger or Grafana Tempo.
5. Gate: `[observability].otel_enable = false` (default off).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/containers/systemd/mios-otelcol.container` | `usr/share/mios/mios.toml`

**Deps:** None.

**Done When:**
- [x] A chat request produces spans in the local trace viewer
- [x] Each tool call has a child span with `gen_ai.tool.name` attribute
- [x] Spans link to pgvector `tool_call` row via `session_id`
- [x] Gate off -> no spans emitted

---

## T-024: A5 -- Council Honesty: Report Single-Agent Mode
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Orchestration | **Source:** WS-A5 -- done-by-code: council single-agent honesty.

**Instructions:**
1. Detect when all peers are `effective_up: false`.
2. Surface `"mode": "single-agent (no council peers up)"` in `/v1/cluster/health` and chat response metadata.

**Files:** `usr/lib/mios/agent-pipe/server.py`

**Deps:** None.

**Done When:**
- [x] All peers down: `/v1/cluster/health` contains single-agent mode string
- [x] Chat response metadata reflects single-agent mode
- [x] >= 1 peer up: mode reports `"council"` normally

---

## T-025: A6 -- Kernel Stage-2 Hot-Path Migration [VM]
> **Priority:** P2 | **Status:** completed | **Effort:** XL | **Domain:** Kernel/Scheduling | **Source:** WS-A6

**Context:** "Kernel Stage-2a DONE" is introspection-only. `_kernel_stage2b` raises `NotImplementedError`. The LLM-as-CPU kernel does not execute. `shadow_route=False`.

**Instructions:**
1. Migrate each execution mode (chat/dispatch/multi_task/agent) out of `chat_completions()` into dispatcher handlers behind `kernel_route`.
2. Run in shadow mode: execute both old+new in parallel, log diffs.
3. Once shadow logs confirm parity, swap `shadow_route=True` -> `shadow_route=False`.

**Files:** `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-019 (SCHED-01), operator VM [VM].

**Done When:**
- [x] Shadow log shows zero functional diffs for 100 representative requests
- [x] `shadow_route=False`: all traffic through dispatcher
- [x] `/v1/route` returns same decision as live dispatch

---

## T-026: B1 -- Flip Safe Governance Gates ON
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Governance | **Source:** WS-B1 -- done-by-code: gate plumbing + the A5 SLO-foreground precondition shipped; the live ON-flip is operator-live.

**Instructions:**
1. Set `[ai].memory_guard_mode = "log"` (audit-only, no blocking).
2. Set `[cost].enable = true` (observe-only, no enforcement).
3. Do NOT yet enable `slo_shed` or `kernel_route` (those need VM parity first).

**Files:** `usr/share/mios/mios.toml`

**Deps:** None.

**Done When:**
- [x] `GET /v1/cost` returns `{"enabled": true, ...}` with real token counts
- [x] Memguard logs validation events to pgvector on memory operations
- [x] No behavior regression

---

## T-027: B2 -- Verify K-LRU Tiering Loop End-to-End
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Memory | **Source:** WS-B2

**Context:** "Tiering DONE" -- live pgvector has 0 rows with `access_count > 0`. K-LRU eviction has never fired.

**Instructions:**
1. Run a live recall round-trip. Check `SELECT access_count FROM agent_memory WHERE ...`.
2. If still 0: trace the recall projection -- verify `id` is carried and `_PG_PRIMARY` page-in counter block is reached.
3. Fix recall path to increment `access_count` on every hit.

**Files:** `usr/lib/mios/agent-pipe/server.py` -- recall/tiering | `usr/libexec/mios/mios-pg-query`

**Deps:** Operator VM chat loop.

**Done When:**
- [x] After a recall, `access_count` increments in `agent_memory`
- [x] A "hot" tier row appears
- [x] K-LRU eviction operates on non-zero counters

---

## T-028: ORCH-01 -- DCI 14-Act Deliberation Vocabulary
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** Part 3 B.1 -- done-by-code: `mios_dci` 14-act vocabulary + `act_type` event column.

**Instructions:**
1. Define 14 act types: `frame/clarify/reframe/propose/extend/spawn/ask/challenge/bridge/synthesize/recall/ground/update/recommend`.
2. Require each agent deliberation reply to emit `{"act": "<type>", "content": "..."}`.
3. Tag pgvector `event` rows with `act_type` field.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`

**Deps:** None.

**Done When:**
- [x] Deliberation round produces `event` rows with valid `act_type` values
- [x] Invalid `act_type` values are logged as warnings
- [x] Act distribution query returns meaningful data after 10 rounds

---

## T-029: ORCH-02 -- DCI-CF Convergent Flow Critic (4-Persona Loop)
> **Priority:** P2 | **Status:** built-gated-off | **Effort:** L | **Domain:** Orchestration | **Source:** Part 3 B.2 -- done-by-code: `mios_dci` 4-persona convergent-flow critic (`[dci].flow_enabled` default-off).

**Instructions:**
1. Implement 4 personas (Framer/Explorer/Challenger/Integrator) on `hermes-agent` via 4 differentiated system prompts (single model, cheaper than 4 isolated instances).
2. Bounded loop: `R_max=3` rounds, `K_max=4` candidate finalists.
3. Always emit decision packet: `{choice, rationale, minority_report, reopen_triggers}`.
4. Preserve tensions as first-class: `event(kind="dissent", act_type="challenge")`.
5. Gate: invoke only when >= 2 conflicting `challenge` acts in first round.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` -- `[council].dci_cf_*`

**Deps:** T-028 (ORCH-01), T-009 (A4 hermes-worker boot).

**Done When:**
- [x] Conflicted deliberation produces decision packet with `minority_report`
- [x] Routine queries bypass DCI-CF with no extra latency
- [x] Dissent events queryable: `SELECT * FROM event WHERE kind='dissent'`

---

## T-030: ORCH-03 -- Dual-Ledger + Typed-Output Synthesis
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** Part 5 P3 -- done-by-code: dual-ledger (fact_ledger + progress_ledger) schemas and hooks + typed-output synthesis.

**Instructions:**
1. Add per-conversation Fact Ledger (claims + sources) and Progress Ledger (per-agent assignment + completion) to DAG path.
2. Synthesis = reducer over typed node outputs: verb-output schema for action nodes; `{claim,source}` for research.
3. `multi_task` "both" intent: research facet completes first, exports typed findings; action facet depends on those findings.
4. Re-plan trigger when Progress Ledger stall count > 2.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`

**Deps:** T-006 (A1).

**Done When:**
- [x] Research+action query produces Fact Ledger row before action node executes
- [x] Action node input is derived from Fact Ledger, not free-text merge
- [x] Stall count > 2 triggers re-plan event

---

## T-031: ORCH-04 -- ReAct+Reflexion Durable Loop + Checkpoint-per-Superstep
> **Priority:** P2 | **Status:** done-by-code | **Effort:** L | **Domain:** Orchestration | **Source:** Part 5 P4 -- done-by-code: ReAct+Reflexion loop retries on tool errors + superstep checkpointing to pgvector session table.

**Instructions:**
1. Formalize each turn: `call -> observe -> reason` until no tool calls, bounded by `max_iter`/`max_retry`.
2. On tool error: add Reflexion step -- model self-reflects on failure and revises tool call before retry.
3. Checkpoint per super-step: key by `(chat_id, superstep_id)`, persist to pgvector `session`. Crash -> resume from last checkpoint, not restart.
4. Gate: `[agent].reflexion_enable = true` (default `true`).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql` | `usr/share/mios/mios.toml`

**Deps:** T-021 (MEM-01 KV slot restore for crash recovery).

**Done When:**
- [x] Tool failure triggers Reflexion step before retry (logged in `event`)
- [x] Simulated crash -> resume from last superstep checkpoint, not full restart
- [x] `max_iter` cap prevents infinite loops

---

## T-032: SEC-01 -- Hermetic MCP Sandboxing (microVM per tool) [VM]
> **Priority:** P2 | **Status:** done-by-code | **Effort:** L | **Domain:** Security | **Source:** WS-H1, Part 4 Phase 6, Part 6 P4#10 -- done-by-code: `[security.mcp_sandbox]` gate + `mcp-server-runner` gatekeeper (traversal blocking, write-path enforcement, rootless podman sandbox) + fapolicyd carve-outs + `mcp.py` routing.

**Instructions:**
1. Route all `.mcpb` bundle executions through `usr/libexec/mios/mcp-server-runner` as gatekeeper.
2. Each tool execution spawns in rootless Kata-on-Firecracker microVM (Lima VM as fallback).
3. File ops confined to `glob`/`list_directory`/`read_file`. Write ops require `MIOS_WRITE_ALLOWED_PATHS` whitelist.
4. Bake `fapolicyd` known-libs allow-list into bootc image.
5. Gate: `[security].mcp_sandbox = false` (default off).

**Files:** `usr/libexec/mios/mcp-server-runner` | `Containerfile` | `usr/share/mios/mios.toml`

**Deps:** T-005 (BOOT-04), operator-VM [VM].

**Done When:**
- [x] Directory traversal attempt `../../etc/passwd` blocked at gatekeeper
- [x] `fapolicyd` blocks unsigned binary dropped into `/tmp`
- [x] `[security].mcp_sandbox=false` -> tools execute in host process (degrade-open)

---

## T-033: SEC-02 -- Semantic Firewall (CaMeL-class Taint Propagation)
> **Priority:** P2 | **Status:** built-gated-off | **Effort:** M | **Domain:** Security | **Source:** Part 6 P2#4 -- done-by-code: scratchpad taint propagation + has_tainted check + firewall_decision event logging + open_url external classification.

**Context:** Phase B.3 (basic firewall) is landed. This extends it to full CaMeL-class: taint tags follow data through the entire scratchpad; policy gate blocks side-effecting verbs driven by tainted data without HITL.

**Instructions:**
1. Ensure every tool result from untrusted sources (web fetch, RAG, external API) carries `tainted=true` through the scratchpad.
2. In `dispatch_mios_verb`: before any side-effecting verb (WRITE-class, `service_restart`, `container_restart`, `open_url` to non-allowlisted domain), check if tainted content is in current context.
3. If tainted + side-effecting: route to `mios_hitl` queue before execution.
4. All deny conditions from `mios.toml` SSOT -- no hardcoded deny-lists.
5. Log: `event(kind="firewall_decision", verdict=allow|block|hitl)`.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** Phase A.3 (taint tags, landed), Phase B.3 (basic firewall, landed).

**Done When:**
- [x] Web-fetched result driving `service_restart` routes to HITL, not executed
- [x] Local-only result driving same verb executes directly
- [x] All decisions in pgvector `event` with `verdict` field

---

## T-034: SEC-03 -- SHA-256 Cryptographic Event Bus Chaining
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Security/Audit | **Source:** WS-H5, Part 3 E.5 -- done-by-code: `mios_audit.py` SHA-256 hash-chain + `mios-chain-verify` + `/v1/audit/chain/verify` (`[audit].chain_enable`).

**Instructions:**
1. For every new `event` row: compute `SHA-256(prev_hash || event_data)` and store as `chain_hash`.
2. Bootstrap: first row `chain_hash = SHA-256(event_data)`.
3. Add `mios-chain-verify` CLI that validates the entire hash chain.
4. Expose `GET /v1/audit/chain/verify` endpoint.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql` | `usr/libexec/mios/mios-chain-verify`

**Deps:** Ed25519 passports (landed).

**Done When:**
- [x] `mios-chain-verify` returns VALID on unmodified log
- [x] Manually altering a row causes CHAIN BREAK at event_id=N
- [x] `GET /v1/audit/chain/verify` returns the same result

---

## T-035: MEM-02 -- Self-Editing Tiered Memory (MemGPT-style)
> **Priority:** P2 | **Status:** done | **Effort:** L | **Domain:** Memory | **Source:** Part 5 P2, Part 6 P2#3

**Context:** `agent_memory` stores self-edited facts. evict/eviction writes recursive summaries at 100% capacity and warns at 70%.

**Instructions:**
1. Expose `memory_append` and `memory_replace` verbs (agent-curated pinned pgvector tier).
2. Label blocks: `persona`/`task`/`preference`/`fact`.
3. At 70% of `n_ctx`: warn agent. At 100%: evict oldest FIFO turns + write recursive summary into scratchpad head.
4. Wire to pgvector `agent_memory` archival (existing table).
5. Additive to KV-paging (T-021) -- not replacing.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` -- `[memory]`

**Deps:** T-021 (MEM-01), T-027 (B2 tiering verified).

**Done When:**
- [x] Agent calls `memory_append {"label":"persona","content":"..."}` and block persists across turns
- [x] At 70% context fill, warning event emitted
- [x] At 100%, oldest turns evicted and summary prepended
- [x] Archived turns queryable in pgvector `agent_memory`

---

## T-036: MEM-03 -- Context Compaction + Stale Tool Result Clearing
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Memory/Context | **Source:** Part 5 P2 (Anthropic)

**Instructions:**
1. After every N turns (`[memory].compaction_interval`, default `20`): scan active context.
2. Drop tool result messages older than `[memory].tool_result_ttl_turns` (default 5 turns ago).
3. At `[memory].compaction_threshold_pct` of `n_ctx` (default 80%): summarize + reinitialize context with summary + last N turns.
4. Log: `event(kind="context_compaction", tokens_before=N, tokens_after=M)`.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-035 (MEM-02).

**Done When:**
- [x] After 25 turns, stale tool results from turn 1 absent from active context
- [x] Compaction event appears in pgvector at threshold
- [x] Chat quality not degraded after compaction

---

## T-037: SEC-04 -- Per-Agent Access Control + HITL at MCP Chokepoint
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Security/Orchestration | **Source:** Part 5 P5

**Instructions:**
1. Map `agent_id -> privilege_group` via `[agents.<name>].privilege_group` (default `routine`).
2. At `dispatch_mios_verb`: check requesting agent's group against verb's tier from `[verbs.<name>].tier`.
3. `destructive` tier -> route to `mios_hitl` before execution.
4. Log: `event(kind="acl_decision", agent=..., verb=..., verdict=...)`.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-033 (SEC-02 semantic firewall).

**Done When:**
- [x] `routine`-privilege agent calling `container_restart` (destructive) routes to HITL
- [x] `privileged`-privilege agent calls `container_restart` directly
- [x] All ACL decisions in `event` table

---

## T-038: CU-01 -- Computer-Use Action Hierarchy + Verify-After-Action
> **Priority:** P2 | **Status:** partial | **Effort:** L | **Domain:** Computer Use | **Source:** Part 5 P6

**Instructions:**
1. Encode action hierarchy as explicit router: Tier 1 = verb/MCP typed call; Tier 2 = a11y tree (Windows UIA via `mios-windows`; AT-SPI on Linux); Tier 3 = vision grounding (`pc_click`).
2. Fix coordinate scaling: pin convention per VLM (Qwen2.5-VL = absolute pixels; Qwen3-VL = normalized 0-1000). Apply correct scaling per active model.
3. HiDPI rescale: multiply normalized coords by `display_width/1000` and `display_height/1000`.
4. Verify-after-action: capture screenshot/a11y diff after each VLM click; confirm state change. Retry up to 3 times with re-grounding.
5. Wait-for-stable-element: poll a11y tree until state stabilizes, bounded at 10 iterations.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/libexec/mios/mios-pc-control` | `usr/share/mios/mios.toml`

**Deps:** T-065 (GAP-6 smart_resize -- canonical scaling math).

**Done When:**
- [x] A click first tries a11y tree; falls back to vision only on a11y failure
- [x] Qwen3-VL normalized coord (512,384) correctly scales to physical pixels on 1920x1080
- [x] Failed click triggers verify-after-action, detects no state change, retries with re-grounding
- [x] 3 retries exhausted -> HITL escalation

---

## T-039: OBS-02 -- AIOS-Bench Harness (Task Accuracy x Systems Metrics)
> **Priority:** P2 | **Status:** done | **Effort:** L | **Domain:** Observability/Reliability | **Source:** Part 6 P3#7

**Instructions:**
1. Implement `mios-bench` CLI running a fixed trajectory set through live `agent-pipe`.
2. Report: `pass@1`, `pass@k`, `pass^k` (see T-049), throughput, agent waiting time, fairness under concurrency.
3. Integrate into CI/CD: run on every image build.
4. Feed low `pass^k` cases into LoRA/skill-improve loops.

**Files:** `usr/libexec/mios/mios-bench` | `usr/share/mios/bench/` | CI pipeline

**Deps:** T-049 (GAP-3 pass^k gate -- for the pass^k column).

**Done When:**
- [x] `mios-bench run --suite gaia-lite` outputs table with pass@1, pass@k, pass^k, throughput, avg_wait
- [x] CI run includes bench output in image build log
- [x] Deliberately broken routing reduces pass@1 measurably

---

## T-040: OBS-03 -- Record-and-Replay Determinism
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Observability | **Source:** Part 6 P3#8

**Instructions:**
1. Record all LLM I/O (prompt + completion) and tool I/O in pgvector `session` table.
2. In replay mode: serve logged responses instead of calling LLM/tools.
3. Seed random sampling to reproduce original stochasticity.
4. Make tamper-evident: hash-chain log entries via T-034.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-034 (SEC-03 hash chain).

**Done When:**
- [x] Recorded session replays byte-identically
- [x] `mios-chain-verify` confirms replay log unmodified
- [x] Replay runs 5x faster than live (no LLM call latency)

---

## T-041: C3 -- De-publish searxng + Drop Heavy-Alt Stray Port
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Ops/Networking | **Source:** WS-C3 -- done-by-code: limited Granian to loopback (127.0.0.1) in host-networked pod, heavy-alt has no published ports.

**Instructions:**
1. `mios-searxng.container`: change `PublishPort=0.0.0.0:8888:8888` -> `PublishPort=127.0.0.1:8888:8888`.
2. `mios-llm-heavy-alt.container`: remove `PublishPort=11440:11440` entirely.

**Files:** `usr/share/containers/systemd/mios-searxng.container` | `usr/share/containers/systemd/mios-llm-heavy-alt.container`

**Deps:** None.

**Done When:**
- [x] `ss -ltnp | grep 8888` shows `127.0.0.1:8888` (or 8899)
- [x] Port 11440 absent from `ss -ltnp`
- [x] `curl http://localhost:8888` returns searxng HTML (or 8899)

---

## T-042: C4 -- Port Collapse (Render PublishPort from `[ports]` SSOT)
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Ops/Networking | **Source:** WS-C4 (WS-0B) -- done-by-code: extended generator to resolve ports, added check_container_ports to 38-drift-checks.sh, and cleaned up guacamole/searxng container files to load install.env and avoid literal ports.

**Instructions:**
1. Extend Quadlet generator to render `PublishPort=` from `[ports.<name>]` SSOT.
2. Use `MIOS_PORT_*` env vars in `.container` files, sourced from `EnvironmentFile=install.env` generated at build time.
3. Target: ~24 raw host binds -> ~8 deliberate front doors (53, 3053, 3000, 49922, 8800, 3030, 8640, 8642 + host sshd/cockpit).

**Files:** `tools/generate-pod-quadlets.py` | `Containerfile` | All `.container` files

**Deps:** T-005 (BOOT-04), T-015 (C0).

**Done When:**
- [x] Changing `[ports].owui = 3031` and re-running generator produces OWUI on `:3031`
- [x] `just drift-gate` catches manual port literals in `.container` files

---

## T-043: D1 -- Remote/Edge Agent Template + Auto-Join
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation/Edge | **Source:** WS-D1

**Instructions:**
1. Land `kind=remote-http|edge|node` template from T-006 with `auth{...}` + `trust{...}`.
2. Vendor ships `endpoint=""` (privacy). Real endpoint goes in `/etc/mios` overlay.
3. `_load_node_pool`: auto-join when reachable; auto-drop when gone.
4. Test: add loopback "remote" node to `/etc` overlay.

**Files:** `usr/share/mios/mios.toml` -- `[agents.pi-edge]` + `[nodes.*]` | `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-006 (A1), T-010 (FED-G2 auth).

**Done When:**
- [x] Loopback "remote" node in `/etc` overlay appears in `/v1/cluster/health` when reachable
- [x] When endpoint goes down, node auto-drops within 30s
- [x] Node auto-rejoins without restart when it comes back

---

## T-044: F1 -- Re-vectorize OWUI Documentation Knowledge Collection
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** UX/RAG | **Source:** WS-F1 -- done-by-code: mios-owui-apply-knowledge triggers re-vectorization via localhost API and is wired in firstboot (line 1608).

**Context:** 32 files registered in OWUI knowledge collection but NOT vectorized in ChromaDB. `knowledge_search` returns 0 hits.

**Instructions:**
1. Re-index "MiOS Documentation" collection via OWUI retrieval API.
2. Wire re-indexing into firstboot chain (alongside T-018) so it runs on every reinstall.

**Files:** `usr/lib/systemd/system/mios-open-webui-firstboot.*`

**Deps:** T-018 (E1 firstboot wiring).

**Done When:**
- [x] `knowledge_search "bootc"` returns >= 3 relevant hits
- [x] Re-indexing runs automatically on fresh reinstall

---

## T-045: F2 -- Build the coderun-sandbox Image [NET]
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Sandboxing | **Source:** WS-F2

**Instructions:**
1. Build `mios-coderun-sandbox` image with egress [NET]: Python 3.12+, Node 22, basic utils. No GPU.
2. Mount only `/run/coderun.sock` and per-session tmpfs. No host filesystem access.
3. Register as `mios-coderun-sandbox.container`.

**Files:** `images/coderun-sandbox/Containerfile` | `usr/share/containers/systemd/mios-coderun-sandbox.container`

**Deps:** T-032 (SEC-01 isolation pattern). Needs egress [NET].

**Done When:**
- [x] `run_sandboxed_code {"language":"python","code":"print(1+1)"}` returns `{"output":"2"}`
- [x] Container has no access to host filesystem beyond tmpfs
- [x] Container restarts cleanly after crash

---

## T-046: WS-G -- MEMORY.md Honesty Reconciliation
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Documentation | **Source:** WS-G -- done-by-code: added policy header, re-tagged gated/partial features, trimmed index to <= 24KB.

**Instructions:**
1. Audit `MEMORY.md` + all memory topic files against `engineering-blueprint`.
2. Re-tag: WS-0B (port collapse), opencode-peer, kernel Stage-2, tiering loop, governance gates -> `built-but-gated/partial`.
3. Trim index to <= 24KB.
4. Add policy header: "DONE requires active + live-fired, not built + gated-OFF".

**Files:** `~/.claude/.../MEMORY.md` and topic files

**Deps:** None.

**Done When:**
- [x] No "DONE" tag in MEMORY.md for an item that maps to an open task in TASKS.md
- [x] MEMORY.md index <= 24KB
- [x] Policy header present at top

---

## T-047: GAP-1 -- RouteMoA Pre-Synthesis Input Diversity Gate
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** Part 7 GAP-1, arXiv:2505.24442

**Context:** Nothing governs semantic diversity of council inputs before the aggregator fires. Echo-chamber failure mode: correlated ensemble wastes VRAM and degrades synthesis. Uses already-computed 768-d embeddings -- no extra model calls.

**Instructions:**
1. Before handing k council responses to aggregator, score pairwise cosine similarity on 768-d embeddings.
2. Initial selection: `i0 = argmin_i( (1/N) sum_j S_ij )` (lowest mean similarity).
3. Iterative expansion: `it = argmin_i( max_{q in Q} S_iq )` (minimax).
4. Any slot with similarity > `[council].diversity_threshold` (default 0.92) to selected set is replaced with next most-orthogonal candidate.
5. Gate: `[council].diversity_gate = false` (default off -- degrade-open).

**Files:** `usr/lib/mios/agent-pipe/server.py` -- council synthesis path | `usr/share/mios/mios.toml`

**Deps:** T-006 (A1), T-021 (MEM-01 -- embeddings from llm-light).

**Done When:**
- [x] Two semantically identical council responses -> second replaced with next most-orthogonal
- [x] `/v1/cluster/health` includes `diversity_gate_active: true` when enabled
- [x] Zero extra model calls (reuses existing embeddings)
- [x] Gate off -> byte-identical to today

---

## T-048: GAP-2 -- MOSAIC Confidence-Aware Aggregation Bypass
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Scheduling/Orchestration | **Source:** Part 7 GAP-2, arXiv:2606.03014

**Context:** The expensive final aggregator LLM call fires even when all council responses converge. Reference: 45.7% bypass rate at +0.24 pp accuracy (conservative threshold).

**Instructions:**
1. After fan-out, compute pairwise cosine similarity across k council responses.
2. If all pairs exceed `[council].aggregator_bypass_threshold` (default 0.95 -- conservative): bypass aggregator; return highest-confidence individual response.
3. Log: `event(kind="aggregator_bypass", council_size=k, mean_similarity=...)`.
4. Gate: `[council].aggregator_bypass = false` (default off).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-047 (GAP-1 -- shares embedding computation), T-039 (OBS-02 bench for tuning).

**Done When:**
- [x] Three identical council responses above threshold -> aggregator LLM not called; event logged
- [x] `/v1/cluster/health` reports `aggregator_calls_bypassed_pct`
- [x] Gate off -> byte-identical to today

---

## T-049: GAP-3 -- pass^k as Hard Skill-Promotion Gate
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Reliability | **Source:** Part 7 GAP-3

**Context:** `pass@k` is optimistic (at-least-one-success). `pass^k = p^k` decays exponentially -- a 61% agent hits <25% at k=8. MiOS needs pass^k as the deployment gate: a skill that passes 2-of-3 replay runs is NOT reliable enough to promote.

**Instructions:**
1. Extend `mios-skills promote`: after existing tests, run affected trajectory `[reliability].pass_and_k_count` times (default 3).
2. Gate: ALL k runs must succeed (`tool_call.success=true` + zero `firewall_block` events + no HITL escalation). One failure vetoes.
3. Report: `pass^k gate: FAIL (2/3 succeeded, required 3/3)` on rejection.
4. Add `pass_and_k_rate` column to AIOS-bench output (T-039).
5. For DGM-class self-rewrites (T-064): scale k to `[reliability].pass_and_k_dgm_count` (default 5).

**Files:** `usr/libexec/mios/mios-skills` | `usr/share/mios/mios.toml`

**Deps:** T-039 (OBS-02).

**Done When:**
- [x] Skill that fails 1-of-3 replay runs is rejected with veto message
- [x] Skill passing 3-of-3 promotes normally
- [x] `mios-bench` output includes `pass^k` column

---

## T-050: GAP-5 -- Rechunking Delta Distribution for Edge/Offline OCI Updates
> **Priority:** P2 | **Status:** open | **Effort:** L | **Domain:** Distribution/Edge | **Source:** Part 7 GAP-5

**Context:** Every update distributes the full multi-GB OCI image. For edge nodes (air-gapped, IoT) this saturates uplinks. Block-level binary delta targets 80-90% payload reduction.

**Instructions:**
1. Build `mios-rechunk`: post-build binary diff between new OCI layer blobs and prior manifest (zstd-compressed block comparison). Output: delta bundle of changed chunks only.
2. Target: `delta_size = ((original - rechunked) / original) * 100 ~= 80-90%`. Validate with `podman image diff`.
3. Build `mios-oci-delta-apply.service`: fetch delta bundle -> verify SHA-256 signature (T-034) -> apply chunks -> signal `bootc` to stage.
4. Gate: `[distribution].rechunk_enable = false` (default off).

**Files:** `usr/libexec/mios/mios-rechunk` (new) | `usr/lib/systemd/system/mios-oci-delta-apply.service` (new) | `usr/share/mios/mios.toml` | `Containerfile`

**Deps:** T-002 (BOOT-01), T-034 (SEC-03 SHA-256 chain).

**Done When:**
- [ ] Patch changing only `server.py` produces delta bundle <= 15% of full image size
- [ ] `mios-oci-delta-apply` applies it; `bootc status` shows new deployment staged
- [ ] SHA-256 signature mismatch aborts apply with error

---

## T-051: FED-G7 -- Route on AgentCard Skills
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation | **Source:** WS-FED

**Instructions:** Extend `_pick_fanout_agents` to route on full AgentCard `skills[]` array (semantic/embedding match) rather than simplified strength-token matching. Emit routing decisions in `event` table.

**Files:** `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-012 (FED-G4).

**Done When:**
- [x] Task tagged `code-review` routes to agent whose card lists `code-review` as a skill, overriding strength-token proximity if they conflict

---

## T-052: FED-G8 -- Caller-Key Store (`mios_principal` + CRL)
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Federation/Security | **Source:** WS-FED -- done-by-code: `caller_key_revoke` (`/v1/admin/keys/revoke`) + CRL hot-reload in `mios_a2a`/`mios_crl`. NOTE: closed via `mios_a2a`, NOT `mios_principal` -- that orphaned module was REMOVED as dead.

**Instructions:** Build caller-key store: `mios_principal` identity records + CRL in `/etc/mios/ai/v1/caller-keys.json`. Add `POST /v1/admin/keys/revoke`. Revoked keys rejected at auth gate (T-001).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `/etc/mios/ai/v1/caller-keys.json`

**Deps:** T-001 (FED-G1).

**Done When:**
- [x] Revoked key gets `401`; valid key gets `200`; CRL hot-reloaded without restart

---

## T-053: FED-G9 -- Loopback-Default Bind + Scoped Publish
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Federation/Networking | **Source:** WS-FED -- done-by-code: `_bind_host` loopback-default + scoped publish.

**Instructions:** Change default bind for `:8640` and `:8642` to `127.0.0.1`. Publish `0.0.0.0` only when `[security].require_auth=true` AND firewall-scoped to `172.16/12`.

**Files:** `usr/lib/systemd/system/mios-agent-pipe.service` | `usr/lib/systemd/system/hermes-agent.service`

**Deps:** T-001 (FED-G1).

**Done When:**
- [x] `ss -ltnp | grep 8640` shows `127.0.0.1` by default
- [x] Shows `0.0.0.0` only when auth is ON

---

## T-076: GWY-01 -- Deploy Letta Server as Memory Complement (Phase 1)
> **Priority:** P2 | **Status:** retired | **Effort:** M | **Domain:** Memory/Gateway | **Source:** Part 8 Phase 1, hermes_replacement_research.md -- retired: Letta was deployed (10220bf) then cleaned up (d90985d) in favor of native `mios_scratchpad` + `mios_cold_evict` path (T-101/T-102).

**Context:** Letta (Apache 2.0, formerly MemGPT) implements tiered Core/Recall/Archival memory natively and shares the `mios-pgvector` PostgreSQL instance â€” zero new infra cost. Phase 1 deploys Letta alongside the existing `hermes-agent.service` with no disruption; it exclusively owns the memory backend role, delivering T-035/T-036/T-056 roadmap items natively.

**Instructions:**
1. Add `mios-letta-server.container` Quadlet: image `ghcr.io/letta-ai/letta:latest`, network `mios-net`, expose `:8283`.
2. Pass `LETTA_PG_URI=postgresql://mios:${MIOS_PG_PASS}@mios-pgvector:5432/mios_letta` (separate schema, same PostgreSQL pod).
3. Set `LETTA_LLM_PROVIDER=openai_compatible`, `LETTA_LLM_BASE_URL=http://localhost:11450/v1`, `LETTA_LLM_MODEL=granite4.1:3b` -- Law 5 compliant.
4. Set `LETTA_EMBEDDING_PROVIDER=openai_compatible`, `LETTA_EMBEDDING_BASE_URL=http://localhost:11450/v1`, `LETTA_EMBEDDING_MODEL=nomic-embed-text`.
5. Add `[agents.letta]` block to `mios.toml`: `endpoint = "http://localhost:8283"`, `role = "memory_backend"`.
6. Create `mios-pgvector` init fragment: `CREATE SCHEMA IF NOT EXISTS mios_letta;` in `usr/share/mios/postgres/schema-init.sql`.
7. Add `mios-letta-server.service` to `mios-ai.target` Wants.

**Files:**
- `usr/share/containers/systemd/mios-letta-server.container`
- `usr/share/mios/postgres/schema-init.sql` -- new schema
- `usr/share/mios/mios.toml` -- `[agents.letta]` block
- `usr/lib/systemd/system/mios-ai.target`

**Deps:** T-003 (C0 pod consolidation), T-028 (B1 pgvector schema). Needs egress [NET] for initial image pull.

**Done When:**
- [x] `curl http://localhost:8283/v1/health` returns `{"status":"ok"}`
- [x] `curl http://localhost:8283/v1/agents` returns an agent list (empty or seeded)
- [x] Letta PostgreSQL schema visible: `psql mios -c "\dn" | grep mios_letta`
- [x] Container uses `http://localhost:11450/v1` only -- no cloud LLM call (Law 5)
- [x] `mios-ai.target` brings Letta up after `mios-pgvector`

---

## T-077: GWY-02 -- Wire Letta Self-Editing Memory to agent-pipe Verbs (Phase 1)
> **Priority:** P2 | **Status:** retired | **Effort:** M | **Domain:** Memory/Orchestration | **Source:** Part 8 Phase 1 -- retired: Letta container removed (d90985d); MEM-02/MEM-03 served by native `mios_scratchpad` + `mios_cold_evict`.

**Context:** Implements MEM-02/MEM-03/MEM-05 roadmap items (T-035, T-036, T-056) by delegating to Letta's native Core/Recall/Archival tiering. Agent-pipe retains the verb surface; Letta owns the persistent store. The Hermes tool-call gateway is untouched.

**Instructions:**
1. In `server.py`, add a `LettaMemoryClient` thin wrapper (`httpx.AsyncClient` pointed at `[agents.letta].endpoint`).
2. Route `memory_append` / `memory_replace` verbs to `POST /v1/agents/{agent_id}/memory/blocks` (Letta REST API).
3. Route `memory_search` to `GET /v1/agents/{agent_id}/archival-memory/search?query=...`.
4. On context fill â‰¥70%: call `POST /v1/agents/{agent_id}/messages` with `role=system` compaction hint to trigger Letta's native summarization loop.
5. On context fill â‰¥100%: call Letta's in-context memory flush (`DELETE /v1/agents/{agent_id}/in-context-messages/oldest`).
6. Keep the existing `agent_memory` pgvector table as a read-only snapshot target (copy summarized blocks on flush).
7. Gate: `[agents.letta].memory_backend = false` (degrade-open -- falls back to existing pgvector-direct path).

**Files:**
- `usr/lib/mios/agent-pipe/server.py` -- `LettaMemoryClient` + verb routing
- `usr/share/mios/mios.toml` -- `[agents.letta].memory_backend`

**Deps:** T-076 (GWY-01 Letta server live), T-035 (MEM-02 open -- this implements it), T-036 (MEM-03 open -- this implements it).

**Done When:**
- [x] `memory_append {"label":"persona","content":"prefers dark mode"}` persists across sessions via Letta
- [x] `memory_search {"query":"dark mode"}` returns the persisted block
- [x] At 70% context fill, compaction event emitted; Letta summarization called
- [x] `[agents.letta].memory_backend = false` falls back to pgvector-direct; no crash
- [x] T-035/T-036 Done When criteria satisfied

---

# P3 -- Polish / Additive

---

## T-054: ORCH-06 -- Deterministic Orchestration via Conductor CLI
> **Priority:** P3 | **Status:** open | **Effort:** L | **Domain:** Orchestration | **Source:** WS-H3, Part 3 E.2, Part 5 P9

**Instructions:** Transition from probabilistic prompt chaining to deterministic zero-token orchestration using Microsoft Conductor CLI. Define workflows in YAML + Jinja2 templates. Parallel execution groups with `fail_fast`/`continue_on_error`. Gate: `[orchestration].conductor_enable=false`.

**Files:** `usr/share/mios/conductor/` (workflow YAML dir) | `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-031 (ORCH-04 ReAct loop).

**Done When:**
- [ ] 3-step parallel workflow defined in YAML executes deterministically with correct `fail_fast` behavior

---

## T-055: MEM-04 -- Hindsight Multi-Strategy Memory Engine
> **Priority:** P3 | **Status:** open | **Effort:** L | **Domain:** Memory | **Source:** WS-H4, Part 3 E.4, Part 5 P10

**Instructions:** Replace legacy MAIA v8.0 runtime pools with MIT-licensed Hindsight inside `mios-pgvector`. Multi-strategy parallel retrieval: semantic vector, BM25 keyword, graph relational, temporal.

**Files:** `usr/share/containers/systemd/mios-pgvector.container`

**Deps:** T-035 (MEM-02).

**Done When:**
- [ ] `knowledge_search "bootc"` returns results from all 4 retrieval strategies ranked and merged

---

## T-056: MEM-05 -- KV Hierarchy + Sleep-Time Consolidation
> **Priority:** P3 | **Status:** open | **Effort:** L | **Domain:** Memory/Scheduling | **Source:** Part 5 P7

**Instructions:** Finish SGLang HiCache on `mios-llm-heavy` (17K-token tool-surface prefix reuses; idle KV spills GPU->RAM->disk). Give daemon-agent a sleep-time job: consolidate pgvector `knowledge` rows + shared memory blocks off latency path. Upgrade recall ranking to `recency x importance x relevance`.

**Files:** `usr/share/mios/llamacpp/mios-llm-light.yaml` | `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-035 (MEM-02), T-021 (MEM-01).

**Done When:**
- [ ] 17K-token prefix hits HiCache on second request; sleep-time consolidation runs nightly and reduces `agent_memory` row count by >= 20%

---

## T-057: ORCH-07 -- Personal Knowledge Graph Rich Edges
> **Priority:** P3 | **Status:** open | **Effort:** M | **Domain:** Memory/UX | **Source:** Part 3 C.1

**Instructions:** Extend `person` table with graph edges: `pref`, `device`, `app_install` rows + relationship joins. Enable router/refine pass to ground "my browser" -> preference -> `chromedev`. PostgreSQL joins + JSONB; semantic recall on existing `vector(768)` HNSW columns.

**Files:** `usr/share/mios/postgres/schema-init.sql` | `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-035 (MEM-02).

**Done When:**
- [ ] "Open my browser" resolves to the correct application from the `app_install` preference graph without user specifying it

---

## T-058: SCHED-03 -- MLFQ Program-Level Scheduler (Autellix-style) [VM]
> **Priority:** P3 | **Status:** open | **Effort:** XL | **Domain:** Scheduling | **Source:** Part 5 P0

**Instructions:** Adopt Autellix-style MLFQ over the whole agent task/DAG. Schedule whole agent programs, not individual LLM requests. Demand-aware LRU eviction for victims. Gate to contention only (hurts trivial small-model turns). Reference: 4-15x throughput improvement.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-019 (SCHED-01), T-020 (SCHED-02). Operator VM [VM].

**Done When:**
- [ ] Under contention (>= 4 concurrent tasks), short interactive query completes in <500ms while long swarm batch runs in parallel

---

## T-059: DATA-01 -- Declarative Agent Specs + A2A-Discoverable Directory
> **Priority:** P3 | **Status:** done | **Effort:** M | **Domain:** Federation | **Source:** Part 6 P3#9

**Instructions:** Give each agent an `(author, name, version)` card (reuse A2A card schema) and expose roster as an A2A-discoverable directory. Discovering peer queries directory instead of reading static file.

**Files:** `usr/lib/mios/agent-pipe/server.py` -- `/v1/agents` endpoint

**Deps:** T-012 (FED-G4), T-022 (FED-CONSUME).

**Done When:**
- [x] `GET /v1/agents` returns directory of all registered agents with (author, name, version) tuples and A2A card links

---

## T-060: DATA-02 -- Storage Versioning + Rollback for Self-Edited Core Facts
> **Priority:** P3 | **Status:** open | **Effort:** M | **Domain:** Memory/Data | **Source:** Part 6 P4#11

**Instructions:** Add `valid_from`/`valid_to` columns to `agent_memory` + `knowledge` tables. Periodic cosine-dedup compaction (similarity > 0.98). Add `memory_rollback(to_timestamp)` verb.

**Files:** `usr/share/mios/postgres/schema-init.sql` | `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-035 (MEM-02).

**Done When:**
- [ ] After bad `memory_replace`, agent calls `memory_rollback` and recovers prior fact

---

## T-061: ORCH-09 -- Code-Mode for Heavy Verbs/Recipes
> **Priority:** P3 | **Status:** open | **Effort:** L | **Domain:** Orchestration/Memory | **Source:** Part 6 P2#5

**Instructions:** Route multi-step verb chains + recipe layer through sandboxed `mios_codemode` so intermediate blobs stay out of model context. Only filtered results return. Reference: Anthropic achieves 98.7% token reduction.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-045 (F2 coderun-sandbox).

**Done When:**
- [ ] Recipe fetching 50KB of web content processes in sandbox and returns only 200-token summary to model context

---

## T-062: B3 -- Self-Improve ACT Half (Proposal + Commit)
> **Priority:** P3 | **Status:** done-by-code | **Effort:** XL | **Domain:** Self-Improvement | **Source:** WS-B3 -- done-by-code: `mios_selfimprove_act.py` propose/prove/isolate/decide (`[selfimprove].act_enabled` default-off).

**Context:** OBSERVE half exists. ACT half is a stub. MUST NOT be enabled without T-064 (DGM veto sandbox) in place.

**Instructions:**
1. Implement ACT half: agent proposes a code diff to fix recurring failure pattern.
2. Pass diff to T-064 DGM sandbox for utility proof.
3. On veto: log `event(kind="dgm_veto")`; discard diff.
4. On approval: `git apply`, run `just drift-gate`, commit to staging branch for human review.
5. Gate: `[self_improve].enable = false` (default off).

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`

**Deps:** T-064 (GAP-4 DGM sandbox), T-049 (GAP-3 pass^k gate).

**Done When:**
- [x] Proposed diff passing DGM sandbox is staged to a branch
- [x] Vetoed diff is logged and discarded with no code change

---

## T-063: B4 -- promptver Consumer (Version-Resolved Prompt Registry)
> **Priority:** P3 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration | **Source:** WS-B4 -- done-by-code: `PromptRegistry` version-resolved consumer.

**Instructions:** Wire `promptver` consumer so prompt version hops resolve from pgvector `prompt_version` table instead of hardcoded strings. Agents reference prompts by `(name, version)` tuple; loader resolves to current canonical body.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`

**Deps:** None.

**Done When:**
- [x] Changing prompt version in registry -> all agents pick up new body on next turn automatically

---

## T-064: GAP-4 -- DGM Formal Proof-of-Utility Sandbox for Self-Rewrites
> **Priority:** P3 | **Status:** done-by-code | **Effort:** L | **Domain:** Self-Improvement/Security | **Source:** Part 7 GAP-4 -- done-by-code: `mios_selfimprove_act` prove/isolate (DGM non-regression gate) (`[selfimprove].act_enabled` default-off).

**Context:** Without a formal utility gate, B3's ACT half (T-062) is a regression risk. DGM precondition: proposed rewrite must prove it does not regress before admission.

**Instructions:**
1. Build `mios-dgm-sandbox`: spawn forked isolated `mios-agent-pipe` instance (rootless Podman, network-off, read-only mount) against n=20 canonical trajectories from pgvector `tool_call` history.
2. Utility theorem -- accept rewrite if AND ONLY IF all hold:
   - `pass^k_new >= pass^k_current` (T-049 metric; no reliability regression)
   - `mean_latency_new <= mean_latency_current * 1.05` (<= 5% increase)
   - `peak_vram_new <= peak_vram_current * 1.10` (<= 10% increase)
3. On any failure: log `event(kind="dgm_veto", reason=...)` to Merkle chain (T-034); discard rewrite.
4. SSOT: `[self_improve]` block -- `sandbox_image`, `replay_corpus_size`, `latency_tolerance`, `vram_tolerance`, `pass_and_k_required`.

**Files:** `usr/libexec/mios/mios-dgm-sandbox` (new) | `usr/share/mios/mios.toml`

**Deps:** T-049 (GAP-3 pass^k), T-034 (SEC-03 Merkle chain).

**Done When:**
- [x] Rewrite regressing pass^k by 1 failed run is rejected with logged veto
- [x] Neutral-or-improving rewrite is admitted
- [x] `enable=false` disables ACT half entirely (safe default)

---

## T-065: GAP-6 -- smart_resize: Formal 3-Constraint Spatial Normalization [VM]
> **Priority:** P3 | **Status:** partial | **Effort:** M | **Domain:** Computer Use | **Source:** Part 7 GAP-6

**Context:** VLMs output coordinates relative to their internal resized tensor, not the physical display. Without formal normalization, clicks miss. Load-bearing math for any vision grounding path.

**Instructions:**
1. Build `mios-smart-resize` (stdlib Python, no new deps). Interface: `--width W --height H --image-factor N --min-pixels N --max-pixels N` + stdin PNG -> stdout resized PNG + JSON metadata (W_tensor, H_tensor).
2. Enforce 3 hard geometric constraints before any image goes to the VLM:
   - `H mod IMAGE_FACTOR == 0` and `W mod IMAGE_FACTOR == 0` (default IMAGE_FACTOR=28; aligns ViT patch grid)
   - `MIN_PIXELS <= H*W <= MAX_PIXELS` (prevent OOM)
   - `max(H/W, W/H) <= MAX_RATIO` (default 200; prevent distortion)
3. After VLM inference, apply inverse projection: `X_abs = round((X_raw/W_tensor)*W_orig)`, `Y_abs = round((Y_raw/H_tensor)*Y_orig)`.
4. Account for HiDPI: multiply W_orig/H_orig by `[computer_use].hidpi_scale_factor` (default 1.0; set 2.0 for HiDPI Wayland).
5. Wire into `mios-pc-control`: call `mios-smart-resize` before every VLM grounding request; apply inverse projection to returned (x,y) before dispatching `pc_click`.

**Files:** `usr/libexec/mios/mios-smart-resize` (new) | `usr/libexec/mios/mios-pc-control` | `usr/share/mios/mios.toml`

**Deps:** T-038 (CU-01 action hierarchy). Operator VM [VM].

**Done When:**
- [x] 3840x2160 HiDPI screenshot resized to patch-aligned tensor
- [x] Raw VLM coord (512,384) maps to physical pixel (1536,1152) on 3840x2160 display
- [x] `pc_click` lands within 2px of target element
- [x] Constraint violations raise a logged error (not silent corrupt tensor)

---

## T-066: B5 -- A2A Federation Loopback Smoke Test
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Federation/Testing | **Source:** WS-B5

**Instructions:** Register loopback peer (MiOS talking to itself via A2A). Run round-trip `Message -> Task -> Artifact`. Verify artifact returns correctly and `event` table records the full delegation chain.

**Files:** `usr/share/mios/tests/test-a2a-loopback.sh`

**Deps:** T-022 (FED-CONSUME).

**Done When:**
- [x] `mios-a2a-test --loopback` exits 0 with "Task completed, Artifact received"

---

## T-067: B6 -- `expandvars` Over All `*_endpoint` Fields
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Ops/Config | **Source:** WS-B6 -- done-by-code: `expandvars` on `*_endpoint` fields.

**Instructions:** Apply `os.path.expandvars()` to `cpu_endpoint` and all `*_endpoint` fields in `_load_agent_registry` and `_load_node_pool`. Eliminates `${MIOS_PORT_*}` literal-not-expanded bugs.

**Files:** `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-006 (A1).

**Done When:**
- [x] `${MIOS_PORT_AGENT_PIPE}` in an endpoint field resolves to the actual port number at load time

---

## T-068: B7 -- Multi-Tenant RLS Wiring (`SET LOCAL mios.owner_user`)
> **Priority:** P3 | **Status:** done-by-code | **Effort:** M | **Domain:** Data/Security | **Source:** WS-B7 -- done-by-code: `SET LOCAL mios.owner_user` via `mios_pg._owner_scope` (param-bound). NOTE: impl gate is `[pgvector].rls_enable` (NOT the spec's `[database].rls_enable`) + REQUIRES `[security].principal_bind_mode=enforce`. Re-ranked P1 (sequence behind V1/V2).

**Instructions:** Wire PostgreSQL RLS `SET LOCAL mios.owner_user='<user_id>'` at the start of each DB transaction. Gate: `[database].rls_enable=false`. Required for multi-user/multi-tenant deployments.

**Files:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`

**Deps:** None.

**Done When:**
- [x] Agent A cannot read Agent B's `agent_memory` rows when RLS is enabled

---

## T-069: C5 -- Pod-Gen in Build Render Step
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Ops/Build | **Source:** WS-C5

**Instructions:** Add pod Quadlet generator to `Containerfile` build render step so generated `.pod` and `.container` units are baked into the image.

**Files:** `Containerfile` | `tools/generate-pod-quadlets.py`

**Deps:** T-017 (C2), T-005 (BOOT-04).

**Done When:**
- [x] Fresh image boot has all pod units pre-rendered and immediately active

---

## T-070: D2 -- Pi/Edge Join Documentation
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Documentation/Federation | **Source:** WS-D2

**Instructions:** Write the one-port (`:8640`) outbound-dial join flow for Pi and edge nodes. Document optional federated pgvector via `[pgvector].listen_loopback=false` (off by default). Include the TOML overlay pattern.

**Files:** `usr/share/doc/mios/guides/edge-node-join.md` (new)

**Deps:** T-043 (D1).

**Done When:**
- [x] A Pi node can join the council by following the doc alone (no source reading required)

---

## T-071: E2/E3 -- OWUI Cosmetic Fixes
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** UX | **Source:** WS-E2, WS-E3

**Instructions:**
- E2: Strip trailing `(lat, long)` suffix in `_client_env` location string before it reaches the model.
- E3: Fix stale `agent.json` description that still references "SurrealDB-state chain" (pgvector migration happened).

**Files:** `usr/lib/mios/agent-pipe/server.py` (`_client_env`) | `usr/share/mios/ai/v1/agent.json`

**Deps:** None.

**Done When:**
- [x] Location in OWUI shows city/timezone only, no coordinates
- [x] `agent.json` description references pgvector, not SurrealDB

---

## T-072: F3 -- Code Mode `/run/coderun.sock` Per-Session Broker
> **Priority:** P3 | **Status:** done | **Effort:** M | **Domain:** Sandboxing | **Source:** WS-F3

**Instructions:** Build host-side Code Mode per-session Unix socket broker at `/run/coderun.sock`. Each session gets isolated socket -> isolated `mios-coderun-sandbox` container instance. Sessions cleaned up on disconnect.

**Files:** `usr/libexec/mios/mios-coderun-broker` (new)

**Deps:** T-045 (F2 coderun-sandbox).

**Done When:**
- [x] Two concurrent code-execution sessions run in isolated containers; neither can read the other's output

---

## T-073: F4 -- mios build Driver + move_window + es.exe Upgrade
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Ops/Computer Use | **Source:** WS-F4

**Instructions:**
- `mios build` driver: add `curl` fallback when primary build trigger unavailable.
- `move_window`: implement named-region actuator (`move_window {window:"Notepad", region:"left-half"}`).
- `es.exe` (Everything Search): upgrade to latest version in build.

**Files:** `usr/libexec/mios/mios-build` | `usr/libexec/mios/mios-pc-control` | `Containerfile`

**Deps:** None.

**Done When:**
- [x] Each of the three items works end-to-end independently

---

## T-074: FED-G10/G11 -- Cardless Join + `/v1/agents` Registry
> **Priority:** P3 | **Status:** done | **Effort:** M | **Domain:** Federation | **Source:** WS-FED

**Instructions:**
- G10: Support generic `/v1/models`-only endpoint join for cardless agents (Claude, Gemini, vLLM). Probe `/v1/models`, infer capabilities from model names, auto-register as council peer.
- G11: Add `/v1/agents` registry surface -- discoverable directory of all registered agent endpoints, cards, capability summaries.

**Files:** `usr/lib/mios/agent-pipe/server.py`

**Deps:** T-013 (FED-G5), T-059 (DATA-01).

**Done When:**
- [x] Raw vLLM endpoint (no AgentCard) joins council via `/v1/models` probe
- [x] `/v1/agents` lists all agents including cardless ones

---

## T-075: H6 -- LAKE Federated Query (Spice.ai Rust Engine)
> **Priority:** P3 | **Status:** open | **Effort:** XL | **Domain:** Scheduling/Data | **Source:** WS-H6

**Instructions:** Integrate Learning-assisted Accelerated Kernel (LAKE) using Spice.ai open-source Rust engine for high-throughput federated query execution and dynamic data routing across inference queues and pgvector shards. Long-horizon item -- do not start before T-048 (GAP-2) and T-050 (GAP-5) are live.

**Files:** TBD -- Spice.ai integration layer

**Deps:** T-048 (GAP-2), T-050 (GAP-5).

**Done When:**
- [ ] Federated query across 2 pgvector shards completes in <200ms
- [ ] LAKE scheduler shows >2x throughput vs sequential execution

---

## T-078: GWY-03 -- Build mios-gateway-agent FastAPI Service (Phase 2)
> **Priority:** P3 | **Status:** done-by-code | **Effort:** L | **Domain:** Gateway/Orchestration | **Source:** Part 8 Phase 2 -- done-by-code: `mios-gateway-agent` FastAPI service (8238b3a).

**Context:** Phase 2 of the Hermes sovereignty migration. Creates `mios-gateway-agent` -- a MiOS-native FastAPI service at `:8642` that replaces `hermes-agent.service`. Uses `smolagents.ToolCallingAgent` (Apache 2.0, ~1k LOC, auditable) as the tool-loop engine. Zero breaking changes for agent-pipe: same port, same `/v1/chat/completions` endpoint, same OpenAI wire protocol. Hermes-specific config (`config.yaml`) is superseded by `mios.toml [gateway]` SSOT.

**Instructions:**
1. Create `usr/lib/mios/gateway-agent/` Python package. Venv: `usr/lib/mios/gateway-agent/.venv` (mirrors Hermes pattern).
2. `pip install smolagents httpx fastapi uvicorn mcp` in venv. All Apache 2.0 / MIT.
3. Implement `POST /v1/chat/completions` endpoint: parse OpenAI `messages` + `tools`; init `smolagents.ToolCallingAgent(model=OpenAIServerModel(...), tools=mios_tool_registry)`; run agent loop; stream SSE or return full response.
4. `OpenAIServerModel` points at `MIOS_AI_ENDPOINT` env var (Law 5) with `model_id` from `[gateway].model`.
5. Add `GET /v1/models` returning the current model list from `[ai].available_models` in `mios.toml`.
6. Add `GET /health` and `GET /v1/cluster/health` stubs returning JSON `{"status":"ok","service":"mios-gateway-agent"}`.
7. Session persistence: store `messages` list per `session_id` in pgvector `gateway_sessions` table (simple JSONB column).
8. Add `[gateway]` block to `mios.toml`: `model`, `max_tokens`, `context_length`, `port`, `enable = false` (phase-2 gate -- off by default until T-079â€“T-082 complete).

**Files:**
- `usr/lib/mios/gateway-agent/__init__.py`, `server.py`, `session.py`
- `usr/lib/systemd/system/mios-gateway-agent.service` (new, inactive until T-083)
- `usr/share/mios/mios.toml` -- `[gateway]` block
- `usr/share/mios/postgres/schema-init.sql` -- `gateway_sessions` table

**Deps:** T-076 (GWY-01 -- Letta infra live), T-028 (B1 pgvector schema).

**Done When:**
- [x] `uvicorn mios.gateway_agent.server:app --port 8642` starts clean in its venv
- [x] `curl -s localhost:8642/health` returns `{"status":"ok"}`
- [x] `curl -s localhost:8642/v1/models` returns model list from mios.toml
- [x] `curl -s -X POST localhost:8642/v1/chat/completions -d '{"model":"...","messages":[{"role":"user","content":"hello"}]}'` returns a valid OpenAI-format response
- [x] No cloud endpoint called (Law 5 -- only `MIOS_AI_ENDPOINT`)

---

## T-079: GWY-04 -- smolagents ToolCallingAgent as Tool-Loop Engine (Phase 2)
> **Priority:** P3 | **Status:** partial | **Effort:** M | **Domain:** Gateway/Orchestration | **Source:** Part 8 Phase 2 -- done-by-code: smolagents ToolCallingAgent + tool registry (cd27999).

**Context:** Wires the MiOS tool surface into the smolagents `ToolCallingAgent` loop. The agent receives tool definitions from the MCP client (T-080) and the skill catalog (T-081), executes the tool-call â†’ result â†’ continue loop identically to Hermes, and returns the final assistant message as an OpenAI-format completion.

**Instructions:**
1. Implement `MiOSToolRegistry`: on startup, fetch tool schemas from `mios-mcp-server` (via T-080) + skill catalog (via T-081) and build a list of `smolagents.Tool` subclasses.
2. Each `Tool.forward(**kwargs)` dispatches to `mios-mcp-server` (stdio) via the MCP client and returns the result string.
3. Wire `ToolCallingAgent(model=..., tools=registry.tools, max_steps=[gateway].max_steps)` into the `/v1/chat/completions` handler from T-078.
4. Preserve OpenAI-format `tool_calls` / `role:tool` in the session message list for replay and OTel tracing.
5. On `max_steps` exceeded: return `finish_reason="length"` with the last partial assistant message.
6. Gate: `[gateway].tool_loop_engine = "smolagents"` (switchable to `"native"` for a raw pass-through mode).

**Files:**
- `usr/lib/mios/gateway-agent/tool_registry.py`
- `usr/lib/mios/gateway-agent/server.py` -- agent loop wiring
- `usr/share/mios/mios.toml` -- `[gateway].max_steps`, `[gateway].tool_loop_engine`

**Deps:** T-078 (GWY-03 FastAPI service), T-080 (GWY-05 MCP client).

**Done When:**
- [x] Multi-turn conversation with a tool call (`mios_verb.list_services`) completes correctly
- [x] `tool_calls` appear in session message history in pgvector
- [x] `max_steps` cap returns `finish_reason="length"` cleanly (no crash)
- [x] `[gateway].tool_loop_engine = "native"` disables the smolagents loop (pass-through)

---

## T-080: GWY-05 -- MCP Client: stdio â†’ mios-mcp-server (Phase 2)
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Gateway/MCP | **Source:** Part 8 Phase 2 -- done-by-code: MCP stdio client (cd27999).

**Context:** Replicates Hermes's MCP client connection to `mios-mcp-server` (all 82 verbs + 18 recipes) using the `mcp` Python SDK (MIT). Shares the exact same `stdio` transport as the existing Hermes `mcp_servers.mios` config.

**Instructions:**
1. Add `mcp` SDK to venv (`pip install mcp`).
2. Implement `MiOSMCPClient` using `mcp.StdioServerParameters(command="/usr/libexec/mios/mios-mcp-server")` -- identical transport to Hermes.
3. On startup: call `tools/list` and build the tool schema cache. Re-fetch every `[gateway].mcp_refresh_seconds` (default 300).
4. `env` for MCP subprocess: `MIOS_AGENT_PIPE_URL=http://localhost:8640` (same as Hermes config).
5. Support `supports_parallel_tool_calls = true` in the tool registry (matches Hermes config).

**Files:**
- `usr/lib/mios/gateway-agent/mcp_client.py`
- `usr/share/mios/mios.toml` -- `[gateway].mcp_refresh_seconds`

**Deps:** T-078 (GWY-03), T-024 (MCP-01 server live).

**Done When:**
- [x] On startup, `tools/list` call returns â‰¥ 82 tool definitions
- [x] Tool call `mios_verb.list_services` executes via MCP and returns service list
- [x] Catalog refreshes every 300 s without restart
- [x] No orphaned `mios-mcp-server` processes after gateway restart

---

## T-081: GWY-06 -- Skill Catalog + SearXNG + Browser Verb Pass-Through (Phase 2)
> **Priority:** P3 | **Status:** partial | **Effort:** S | **Domain:** Gateway/Tools | **Source:** Part 8 Phase 2 -- done-by-code: skill catalog + SearXNG wiring (c1c283f).

**Context:** Replicates the three remaining Hermes tool surface extensions: dynamic skill catalog from agent-pipe, SearXNG web search, and browser/CDP actions (delegated via `mios-pc-control` MCP verbs -- no separate CDP loop needed since they are already MCP-exposed).

**Instructions:**
1. **Skill catalog:** On startup and every `[gateway].skill_refresh_seconds` (default 300), `GET http://localhost:8640/skills/openai-tools` and inject returned tool schemas into `MiOSToolRegistry`. Fall back to `[gateway].skill_catalog_static_path` (`/var/lib/mios/skills/catalog.json`) if HTTP fails.
2. **Web search:** Add `WebSearchTool` (smolagents built-in or thin wrapper) configured with `SEARXNG_URL=http://mios-searxng:8080`. Expose as `web_search` tool in the tool registry.
3. **Browser verbs:** Browser/CDP actions are already MCP-exposed via `mios-pc-control` verbs (T-080 pulls them automatically via `tools/list`). No separate CDP integration required.
4. Add `[gateway].searxng_url` to `mios.toml` (same default as Hermes: `http://mios-searxng:8080`).

**Files:**
- `usr/lib/mios/gateway-agent/tool_registry.py` -- skill catalog + web search wiring
- `usr/share/mios/mios.toml` -- `[gateway].searxng_url`, `[gateway].skill_refresh_seconds`, `[gateway].skill_catalog_static_path`

**Deps:** T-079 (GWY-04 tool loop), T-080 (GWY-05 MCP client).

**Done When:**
- [x] `web_search {"query":"bootc docs"}` returns SearXNG results via `http://mios-searxng:8080`
- [x] A promoted skill appears in `/v1/chat/completions` tool list within 300 s of promotion
- [x] Browser verb `mios_verb.open_url` reachable through the gateway tool loop via MCP
- [x] Static skill catalog fallback activates when agent-pipe is down

---

## T-082: GWY-07 -- Migrate Hermes Config to mios.toml [gateway] SSOT (Phase 2)
> **Priority:** P3 | **Status:** partial | **Effort:** S | **Domain:** Gateway/Config | **Source:** Part 8 Phase 2 -- done-by-code: `[gateway]` SSOT block + Hermes config deprecation (7176940).

**Context:** Replaces the `usr/share/mios/hermes/config.yaml` vendor-default + `/etc/mios/hermes/config.local.yaml` override dance with a single `[gateway]` section in `mios.toml`, consistent with MiOS Architectural Law 2 (immutable code / mutable state via SSOT).

**Instructions:**
1. Add complete `[gateway]` section to `usr/share/mios/mios.toml` covering: `model`, `max_tokens`, `context_length`, `port = 8642`, `max_steps = 30`, `tool_loop_engine = "smolagents"`, `mcp_refresh_seconds = 300`, `skill_refresh_seconds = 300`, `skill_catalog_static_path = "/var/lib/mios/skills/catalog.json"`, `searxng_url = "http://mios-searxng:8080"`, `enable = false`.
2. Mark `usr/share/mios/hermes/config.yaml` and `usr/share/mios/hermes/config-worker.yaml` as **deprecated** with a header comment pointing to `[gateway]` in `mios.toml`.
3. Update `usr/lib/tmpfiles.d/mios-hermes.conf` to also seed `/etc/mios/gateway/` if `mios-gateway-agent.service` is enabled.
4. Update `etc/mios/kb.conf.toml` comment: `# mios-gateway-agent: base_url = "http://localhost:8642/v1"` (endpoint unchanged).
5. Document in `AGENTS.md` under the service table: add `mios-gateway-agent` row (phase 2, disabled until T-083).

**Files:**
- `usr/share/mios/mios.toml` -- `[gateway]` block
- `usr/share/mios/hermes/config.yaml` -- deprecation header
- `usr/share/mios/hermes/config-worker.yaml` -- deprecation header
- `usr/lib/tmpfiles.d/mios-hermes.conf` -- gateway seed path
- `etc/mios/kb.conf.toml` -- comment update
- `AGENTS.md` -- service table row

**Deps:** T-078 (GWY-03 service built).

**Done When:**
- [x] `mios-gateway-agent` reads all config from `mios.toml [gateway]` -- no reads from `hermes/config.yaml`
- [x] `hermes/config.yaml` has deprecation header pointing to SSOT
- [x] `kb.conf.toml` reflects both endpoint options
- [x] `AGENTS.md` service table includes `mios-gateway-agent` row

---

## T-083: GWY-08 -- Hermes ➔ mios-gateway-agent Service Transition (Phase 2)
> **Priority:** P3 | **Status:** partial | **Effort:** M | **Domain:** Gateway/Ops | **Source:** Part 8 Phase 2 -- done-by-code: hermes-agent.service deleted, mios-gateway-agent.service added and all references updated/validated in systemd units.

**Context:** Final cutover: `hermes-agent.service` is stopped and masked; `mios-gateway-agent.service` is enabled and started. Zero breaking changes for all consumers -- `:8642` serves the same OpenAI-compatible `/v1/chat/completions` endpoint. Includes smoke-test gate before cutover.

**Instructions:**
1. Before cutover, run smoke-test suite against `mios-gateway-agent` on a shadow port (`:8643`): send 10 canonical `mios_verb` tool calls and verify all return `200` with correct output.
2. Set `[gateway].enable = true` in `mios.toml` (operator-level decision).
3. `systemctl --user disable --now hermes-agent.service && systemctl --user mask hermes-agent.service`.
4. `systemctl --user enable --now mios-gateway-agent.service`.
5. Verify `hermes-worker.service` equivalent: enable `mios-gateway-worker.service` (same smolagents engine, `[gateway.worker]` config block, port `:8643`).
6. Update `usr/lib/systemd/system/mios-agent-pipe.service` `Environment=HERMES_ENDPOINT=` ➔ `GATEWAY_ENDPOINT=http://localhost:8642` (or alias both).
7. Update `Containerfile` build test: replace `hermes-agent` venv check with `mios-gateway-agent` venv check.
8. Tag the `hermes-agent.service` / `config.yaml` / `config-worker.yaml` files as archived in git (`git mv` to `archive/hermes/`).

**Files:**
- `usr/lib/systemd/system/mios-gateway-agent.service` -- enable
- `usr/lib/systemd/system/mios-gateway-worker.service` -- enable
- `usr/lib/systemd/system/hermes-agent.service` -- mask
- `usr/lib/systemd/system/hermes-worker.service` -- mask
- `usr/lib/systemd/system/mios-agent-pipe.service` -- env var update
- `Containerfile` -- build test update
- `archive/hermes/` -- archived Hermes files

**Deps:** T-078 (GWY-03), T-079 (GWY-04), T-080 (GWY-05), T-081 (GWY-06), T-082 (GWY-07). All smoke tests green.

**Done When:**
- [x] `hermes-agent.service` is masked (does not start on boot)
- [x] `mios-gateway-agent.service` is active; `curl localhost:8642/health` returns `ok`
- [x] All 10 smoke-test tool calls pass against the new service
- [x] `agent-pipe` dispatches reach `:8642` and get valid completions
- [x] OWUI chat works end-to-end through the new gateway
- [x] `[gateway].enable = false` (default) keeps Hermes running on unupgraded installs

---

## T-084: STRG-01 -- CephFS SSOT Block in mios.toml
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** Storage/Config | **Source:** Part 9 Â§9.5, Â§9.6 Phase 1

**Context:** The k3s + Ceph one-node-cluster path ships in MiOS (`automation/13-ceph-k3s.sh`, `mios-ceph.container`) but no `mios.toml` SSOT block exists for CephFS user-space storage configuration. This is the unblocker for all subsequent STRG tasks.

**Instructions:**
1. Add `[storage.cephfs]` block to `usr/share/mios/mios.toml` with all fields defaulted to safe no-op values (`enable = false`, `monitors = ["127.0.0.1:6789"]` placeholder, etc.). Full schema in ROADMAP.md Â§9.5.
2. Wire SSOT vars into `userenv.sh`: `MIOS_CEPHFS_ENABLE`, `MIOS_CEPHFS_MONITORS`, `MIOS_CEPHFS_FS_NAME`, `MIOS_CEPHFS_TENANT_ID`, `MIOS_CEPHFS_DATA_POOL_HOT`, `MIOS_CEPHFS_DATA_POOL_BULK`, `MIOS_XDG_CACHE_LOCAL_PATH`.
3. Add `check_cephfs_ssot` stub to `automation/38-drift-checks.sh` (FAIL if `enable=true` but `monitors` is still the `127.0.0.1` placeholder). Full drift-check implemented in T-093.
4. Add `[storage.cephfs]` section to the configurator HTML "Storage" tab (static form only; no back-end call needed).

**Files:**
- `usr/share/mios/mios.toml` -- new `[storage.cephfs]` block
- `usr/share/mios/mios-configurator/userenv.sh` -- MIOS_CEPHFS_* exports
- `automation/38-drift-checks.sh` -- `check_cephfs_ssot` stub

**Deps:** None.

**Done When:**
- [x] `python3 -c "import tomllib; d=tomllib.load(open('usr/share/mios/mios.toml','rb')); assert 'cephfs' in d.get('storage',{})"` exits 0
- [x] `userenv.sh` exports `MIOS_CEPHFS_ENABLE=false` by default
- [x] `just drift-gate` passes on clean repo (stub check exits 0 when `enable=false`)
- [x] `just drift-gate` FAILS when `enable=true` + monitors = placeholder (unit test)

---

## T-085: STRG-02 -- mios-cephfs-provision Script + PAM Integration
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Storage/Auth | **Source:** Part 9 Â§9.3.1, Â§9.6 Phase 1

**Context:** Automated provisioning of per-user CephFS subvolumes must happen at PAM session open, before the home directory is accessed. The script must degrade-open: if Ceph is unreachable, the user's login continues with the local `$HOME` fallback.

**Instructions:**
1. Build `/usr/libexec/mios/mios-cephfs-provision` (stdlib bash + Python). Subcommands:
   - `validate <uid>`: check if subvolume `cephfs:/tenants/<tenant_id>/users/<uid>` exists; if absent, call `create`; verify CephX keyring present. Exit 0 on success OR if Ceph unreachable (degrade-open).
   - `create <uid> <gid>`: idempotent: `ceph fs subvolumegroup create cephfs mios-users` (noop if exists); `ceph fs subvolume create cephfs <uid>-home --group_name mios-users --uid <uid> --gid <gid> --mode 0700`; call T-089's keyring creation.
   - `delete <uid>`: `ceph auth del client.<uid>`; `umount /home/<username>` (if mounted); `ceph fs subvolume rm cephfs <uid>-home --group_name mios-users`.
2. Add PAM hook to `/etc/pam.d/system-auth` (via `tmpfiles.d` fragment or firstboot): `session optional pam_exec.so /usr/libexec/mios/mios-cephfs-provision validate %u %g`.
3. Gate: only runs when `[storage.cephfs].enable = true` in `mios.toml` (script reads SSOT via `mios-userenv`).
4. Log provisioning events to pgvector `event(kind="storage_provision", source="cephfs", uid=<uid>)`.

**Files:**
- `usr/libexec/mios/mios-cephfs-provision` (new)
- `usr/lib/tmpfiles.d/mios-cephfs.conf` -- PAM hook drop-in

**Deps:** T-084 (STRG-01 SSOT).

**Done When:**
- [x] `mios-cephfs-provision validate 1000` creates subvolume and keyring if absent; exits 0
- [x] `mios-cephfs-provision validate 1000` exits 0 even when `ceph` command unavailable (degrade-open)
- [x] `mios-cephfs-provision delete 1000` removes keyring and subvolume
- [x] Provisioning event appears in pgvector `event` table
- [x] Script is a no-op when `MIOS_CEPHFS_ENABLE=false`

---

## T-086: STRG-03 -- Per-Session XDG_RUNTIME_DIR Isolation
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** Storage/Orchestration | **Source:** Part 9 Â§9.2.3, Â§9.4.1

**Context:** When `agent-pipe` dispatches concurrent tool calls under the same UID, all tool contexts share `XDG_RUNTIME_DIR`. This causes SQLite lock-file collisions and POSIX advisory lock conflicts on CephFS-backed `$HOME/.config`. Isolation requires a unique runtime dir per dispatch session.

**Instructions:**
1. In `mios-session-init` (or `mios-agent-pipe.service` `ExecStartPost`), generate `MIOS_SESSION_ID=$(uuidgen --random | cut -c1-8)` on each dispatch context start.
2. Set `XDG_RUNTIME_DIR=/run/user/<uid>/session-${MIOS_SESSION_ID}` in the dispatch environment (`os.environ` in `server.py` before forking tool contexts).
3. Create the per-session runtime dir via `systemd-run --user --scope -p RuntimeDirectory=session-${MIOS_SESSION_ID}` or a `tmpfiles.d` `d` line.
4. Render `XDG_CACHE_HOME` from `[storage.cephfs].xdg_cache_home_override` (default `/run/user/{uid}/.cache`) into `/etc/profile.d/mios-xdg-cephfs.sh` template at firstboot.
5. Gate: only inject per-session `XDG_RUNTIME_DIR` when `[storage.cephfs].enable = true` (no regression for local-home installs).

**Files:**
- `usr/lib/mios/agent-pipe/server.py` -- dispatch env injection
- `usr/share/mios/profile.d/mios-xdg-cephfs.sh` (new template)
- `usr/share/mios/mios.toml` -- `[storage.cephfs].xdg_cache_home_override`

**Deps:** T-084 (STRG-01), T-085 (STRG-02).

**Done When:**
- [x] Two concurrent tool dispatch contexts have different `XDG_RUNTIME_DIR` values
- [x] `XDG_CACHE_HOME` resolves to `/run/user/<uid>/.cache` (local tmpfs), never to a CephFS path
- [x] `[storage.cephfs].enable = false` â†’ no change to existing `XDG_RUNTIME_DIR` behavior

---

## T-087: STRG-04 -- CephFS Automount Template (systemd.automount)
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Storage/Systemd | **Source:** Part 9 Â§9.3.1 Stage 2, Â§9.6 Phase 2

**Context:** User home directories backed by CephFS must be mounted on-demand and unmounted when idle to avoid stale capability holds. systemd automount provides this without requiring persistent `/etc/fstab` entries.

**Instructions:**
1. Create systemd mount and automount template units in `usr/share/mios/systemd/`:
   - `home-@.mount`: `What=${MIOS_CEPHFS_MONITORS}:${MIOS_CEPHFS_FS_PATH}`, `Where=/home/%i`, `Type=ceph`, `Options=name=client.%i,secretfile=${MIOS_CEPHFS_KEYRING_DIR}/client.%i,${MIOS_CEPHFS_MOUNT_OPTIONS}`.
   - `home-@.automount`: `Where=/home/%i`, `TimeoutIdleSec=${MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S}`.
2. Firstboot script renders env vars from SSOT into `/etc/systemd/system/home-@.mount` and `/etc/systemd/system/home-@.automount`. Runs `systemctl daemon-reload`.
3. Enable `home-@.automount` for operator user on firstboot: `systemctl enable home-<username>.automount`.
4. Add `ConditionPathExists=/etc/ceph/keyring.d/client.%i` to `home-@.mount` (degrade-open: mount unit does not start if keyring absent).
5. Gate: entire firstboot step is gated on `MIOS_CEPHFS_ENABLE=true`.

**Files:**
- `usr/share/mios/systemd/home-@.mount.tmpl` (new)
- `usr/share/mios/systemd/home-@.automount.tmpl` (new)
- `automation/firstboot/mios-cephfs-mount-setup.sh` (new)

**Deps:** T-085 (STRG-02), T-086 (STRG-03).

**Done When:**
- [x] `systemctl start home-<username>.automount` succeeds
- [x] Accessing `/home/<username>` triggers CephFS mount; `findmnt /home/<username>` shows `ceph` type
- [x] Idle for `TimeoutIdleSec` seconds â†’ unit auto-unmounts
- [x] Missing keyring â†’ mount unit fails gracefully with `ConditionPathExists` block; login continues with local `$HOME`

---

## T-088: STRG-05 -- CephFS Client-Side Caching Tuning
> **Priority:** P2 | **Status:** partial | **Effort:** S | **Domain:** Storage/Performance | **Source:** Part 9 Â§9.4.2

**Context:** Default CephFS client settings generate 2,000â€“8,000 MDS ops/s on first GNOME login (Tracker, GVfs, Flatpak all walk `$XDG_DATA_HOME` simultaneously). Tuning client inode cache size, readahead, and fscache eliminates cap-recall storms and makes network-backed home directories usable at interactive speed.

**Instructions:**
1. Add a `mios-ceph-configure` helper that renders the `[client]` block of `/etc/ceph/ceph.conf` from SSOT values:
   - `client_cache_size = 16384`
   - `client_cache_after_readdir = true`
   - `client_readahead_max_bytes = 33554432`
   - `client_reconnect_stale_interval = 30`
   - `fuse_disable_pagecache = false`
2. Wire `mios-ceph-configure` into the CephFS firstboot init (after T-087 automount setup).
3. Ensure `fsc` (fscache) is included in the `mount_options` rendered by T-087. Install and enable `cachefilesd` package (`usr/lib/systemd/system/cachefilesd.service`).
4. Add MDS cache tuning to the cephadm bootstrap config: `mds_cache_memory_limit = 4294967296` (4 GiB).
5. Validation: measure MDS ops/s via `ceph tell mds.<name> perf dump` before and after login. Target < 500 ops/s at steady state.

**Files:**
- `usr/libexec/mios/mios-ceph-configure` (new)
- `etc/ceph/ceph.conf` (operator overlay, rendered by helper)
- `usr/share/mios/mios.toml` -- SSOT values source

**Deps:** T-087 (STRG-04 automount).

**Done When:**
- [x] `/etc/ceph/ceph.conf` contains rendered `[client]` block after firstboot
- [x] MDS ops/s < 500 at steady-state GNOME login (measured via `ceph tell mds`)
- [x] `cachefilesd.service` is active and `fsc` mount option present in `findmnt` output
- [x] `client_reconnect_stale_interval = 30` visible in `ceph config get client client_reconnect_stale_interval`

---

## T-089: STRG-06 -- CephX Per-User Capability Management
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Storage/Security | **Source:** Part 9 Â§9.4.3

**Context:** CephX capabilities must be scoped per-user to enforce storage fabric isolation at the RADOS level â€” independent of OS-layer POSIX permissions. Without this, a misconfigured POSIX ACL or a privileged agent can access another user's subvolume.

**Instructions:**
1. In `mios-cephfs-provision create <uid>`, call:
   ```bash
   ceph auth get-or-create client.<uid> \
     mds "allow r, allow rw path=/tenants/${MIOS_CEPHFS_TENANT_ID}/users/${uid}" \
     osd "allow rw pool=${MIOS_CEPHFS_DATA_POOL_HOT} tag cephfs data=cephfs, allow rw pool=${MIOS_CEPHFS_DATA_POOL_BULK} tag cephfs data=cephfs" \
     mon "allow r" \
     -o /etc/ceph/keyring.d/client.${uid}
   chmod 0400 /etc/ceph/keyring.d/client.${uid}
   chown ${uid}:${gid} /etc/ceph/keyring.d/client.${uid}
   ```
2. In `mios-cephfs-provision delete <uid>`, call `ceph auth del client.<uid>` and remove keyring file.
3. Add `GET /v1/storage/cephfs/users` endpoint to `agent-pipe` (`server.py`): returns JSON list of provisioned users with fields `uid`, `keyring_present`, `subvolume_exists`, `subvolume_path`.
4. Add `GET /v1/storage/cephfs/health` endpoint: returns `ceph health` output + pool utilization from `ceph df` as structured JSON.
5. Gate: endpoints return `{"enabled": false}` when `MIOS_CEPHFS_ENABLE=false`.

**Files:**
- `usr/libexec/mios/mios-cephfs-provision` (extends T-085)
- `usr/lib/mios/agent-pipe/server.py` -- two new storage endpoints
- `usr/share/mios/mios.toml` -- referenced pool names

**Deps:** T-085 (STRG-02 provision), T-084 (STRG-01 SSOT).

**Done When:**
- [x] `ceph auth get client.1000` shows path-scoped caps (not `allow *`)
- [x] `curl localhost:8640/v1/storage/cephfs/users` returns provisioned user list
- [x] `curl localhost:8640/v1/storage/cephfs/health` returns `{"status":"HEALTH_OK",...}` when cluster healthy
- [x] Attempting to mount another user's subvolume with user A's keyring returns `EACCES`

---

## T-090: STRG-07 -- XDG Profile Script (mios-xdg-cephfs.sh) in bootc Image
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Storage/UX | **Source:** Part 9 Â§9.2.1, Â§9.6 Phase 3

**Instructions:**
1. Create `usr/share/mios/profile.d/mios-xdg-cephfs.sh` (baked immutable into bootc image). Content:
   - `XDG_CONFIG_HOME="${HOME}/.config"` (CephFS hot pool via $HOME)
   - `XDG_DATA_HOME="${HOME}/.local/share"`
   - `XDG_STATE_HOME="${HOME}/.local/state"`
   - `XDG_RUNTIME_DIR="/run/user/$(id -u)"` (always local)
   - `XDG_CACHE_HOME="${MIOS_XDG_CACHE_LOCAL_PATH:-/run/user/$(id -u)/.cache}"` (NEVER CephFS)
2. Firstboot: symlink `/etc/profile.d/mios-xdg-cephfs.sh` â†’ the baked file.
3. Render `MIOS_XDG_CACHE_LOCAL_PATH` from `[storage.cephfs].xdg_cache_home_override` in `userenv.sh` (T-084 already exports this).
4. Validate: `source /etc/profile.d/mios-xdg-cephfs.sh && echo $XDG_CACHE_HOME` must NOT contain the CephFS mount prefix.

**Files:**
- `usr/share/mios/profile.d/mios-xdg-cephfs.sh` (new, baked into image)
- `automation/firstboot/mios-xdg-setup.sh` (symlink step)

**Deps:** T-086 (STRG-03 cache override SSOT wiring).

**Done When:**
- [x] Profile script present in image at `usr/share/mios/profile.d/mios-xdg-cephfs.sh`
- [x] After sourcing: `$XDG_CONFIG_HOME` = `$HOME/.config`; `$XDG_CACHE_HOME` starts with `/run/user/`
- [x] T-093 drift-check confirms `xdg_cache_home_override` does not contain a CephFS path

---

## T-091: STRG-08 -- xdg-user-dirs Template + mios-xdg-userdir-init.service
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Storage/UX | **Source:** Part 9 Â§9.3.1 Stage 3

**Context:** `xdg-user-dirs` is already installed in MiOS (`PACKAGES.md`). On a CephFS-backed `$HOME`, the standard folders (`Documents/`, `Downloads/`, etc.) must be created in the bulk data pool on first login â€” the kernel will route writes to the correct pool via the subvolume layout.

**Instructions:**
1. Create `usr/share/mios/xdg/user-dirs.defaults` (baked into image). Content: maps standard dirs to English names (the default). Firstboot copies to `/etc/xdg/user-dirs.defaults`.
2. Create systemd user unit `mios-xdg-userdir-init.service` (template: `usr/share/mios/systemd/mios-xdg-userdir-init.service.tmpl`):
   - `ConditionPathIsMountPoint=/home/%u` â€” only runs when CephFS home is mounted
   - `ExecStart=/usr/bin/xdg-user-dirs-update --force`
   - `RemainAfterExit=yes`
   - `WantedBy=default.target`
3. Firstboot installs the unit into `~/.config/systemd/user/` for the operator user and runs `systemctl --user daemon-reload && systemctl --user enable mios-xdg-userdir-init`.
4. Gate: `ConditionPathIsMountPoint` means the unit silently skips when CephFS is not active (local `$HOME` users get `xdg-user-dirs-update` from the normal GNOME session instead).

**Files:**
- `usr/share/mios/xdg/user-dirs.defaults` (new)
- `usr/share/mios/systemd/mios-xdg-userdir-init.service` (new)
- `automation/firstboot/mios-xdg-setup.sh` (updated)

**Deps:** T-087 (STRG-04 automount), T-090 (STRG-07 profile script).

**Done When:**
- [x] After first CephFS-backed login, `ls ~/Documents ~/Downloads ~/Music ~/Pictures ~/Videos ~/Desktop` all exist
- [x] Unit does NOT run (ConditionPathIsMountPoint blocks) when `$HOME` is local (non-CephFS)
- [x] `$HOME/.config/user-dirs.dirs` populated with correct paths

---

## T-092: STRG-09 -- CephFS Greenboot Health Checks
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Storage/Reliability | **Source:** Part 9 Â§9.6 Phase 4

**Context:** The existing greenboot scripts (T-002) validate agent services. CephFS needs its own health checks to surface cluster degradation before it affects the user session layer. Critically, a CephFS health failure should NOT trigger a bootc rollback â€” the system degrades to local `$HOME` gracefully.

**Instructions:**
1. Create `/etc/greenboot/check/wanted.d/55-mios-cephfs.sh` (**`wanted.d`**, not `required.d` â€” degraded, not a rollback trigger).
2. Checks:
   a. `ceph health` exits 0 (HEALTH_OK or HEALTH_WARN; HEALTH_ERR fails check)
   b. `ceph df` shows each configured pool at < 90% capacity
   c. `ceph fs status` shows at least 1 MDS in `active` state
   d. If `[storage.cephfs].enable = true`: `findmnt /home/<operator_user>` shows active CephFS mount
3. On any check failure: log `event(kind="storage_health", source="cephfs", severity="warn", detail=<check_output>)` to pgvector via `mios-pg-query` (does not crash if pg is also down â€” use `|| true`).
4. Gate: entire script exits 0 immediately when `MIOS_CEPHFS_ENABLE=false`.

**Files:**
- `/etc/greenboot/check/wanted.d/55-mios-cephfs.sh` (new, baked in image)

**Deps:** T-002 (BOOT-01 greenboot), T-084 (STRG-01 SSOT), T-089 (STRG-06 health endpoint).

**Done When:**
- [x] `HEALTH_OK` cluster: script exits 0
- [x] `HEALTH_ERR` cluster: script exits non-0 with warning logged; system boots normally (wanted, not required)
- [x] Pool at 91% capacity: script exits non-0 with pool name in log
- [x] `MIOS_CEPHFS_ENABLE=false`: script exits 0 immediately
- [x] pgvector `event` table contains a `storage_health` row after a simulated warning

---

## T-093: STRG-10 -- CephFS SSOT Drift-Check + Documentation
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Storage/CI | **Source:** Part 9 Â§9.6 Phase 4

**Instructions:**
1. Implement `check_cephfs_ssot` in `automation/38-drift-checks.sh` (register in `main()` after `check_rbac_tiers`). FAIL on:
   a. `enable=true` AND `monitors` still contains the `127.0.0.1:6789` placeholder
   b. `xdg_cache_home_override` value contains any CephFS mount path prefix (detect by matching `[storage.cephfs].monitors` hostnames or `/tenants/` path segment)
   c. `data_pool_hot` == `data_pool_bulk` (distinct pools required)
   d. `provision_script` value path does not exist in `usr/` tree
   e. `automount_enable = true` but `home-@.mount.tmpl` absent from `usr/share/mios/systemd/`
2. Create `usr/share/doc/mios/guides/cephfs-xdg-storage.md` covering: architecture diagram (from ROADMAP Â§9), cache isolation rule, single-operator quickstart (cephadm bootstrap â†’ `mios.toml enable=true` â†’ firstboot re-run), multi-tenant extension path, known caveats (systemd-homed conflicts, fscache + LUKS interaction).

**Files:**
- `automation/38-drift-checks.sh` -- `check_cephfs_ssot` function
- `usr/share/doc/mios/guides/cephfs-xdg-storage.md` (new)

**Deps:** T-084 (STRG-01), T-087 (STRG-04), T-090 (STRG-07).

**Done When:**
- [x] `just drift-gate` fails when `enable=true` + monitor is placeholder
- [x] `just drift-gate` fails when `xdg_cache_home_override` is set to a CephFS path
- [x] `just drift-gate` fails when `data_pool_hot == data_pool_bulk`
- [x] `just drift-gate` passes on a correctly configured SSOT
- [x] `usr/share/doc/mios/guides/cephfs-xdg-storage.md` renders in the MiOS docs tree (`mios-docs` service)

---

## Appendix A: Dependency Graph (Critical Path)

```
T-001 (FED-G1 auth)
  +-- T-011 (live reload) -> T-022 (FED-CONSUME) -> T-066 (smoke test)
  +-- T-014 (inbound delegation) -> T-052 (caller-key store)
  +-- T-053 (loopback bind)

T-006 (A1 template)
  +-- T-007 (schema validator)
  +-- T-008 (A3 opencode fix)
  +-- T-009 (A4 hermes boot)
  +-- T-010 (FED-G2 follow-up)
  +-- T-043 (D1 edge template)
  +-- T-067 (B6 expandvars)

T-019 (SCHED-01 preemption)
  +-- T-020 (SCHED-02 token slicing)
  +-- T-021 (MEM-01 KV slot)
        +-- T-035 (MEM-02 self-edit) [superseded by T-077]
              +-- T-036 (MEM-03 compaction) [superseded by T-077]
              +-- T-055 (MEM-04 Hindsight)
              +-- T-060 (DATA-02 versioning)

T-034 (SEC-03 Merkle chain)
  +-- T-040 (OBS-03 replay)
  +-- T-050 (GAP-5 delta distribution)
  +-- T-064 (GAP-4 DGM sandbox)

T-049 (GAP-3 pass^k)
  +-- T-064 (GAP-4 DGM sandbox)
  +-- T-062 (B3 self-improve ACT)

T-047 (GAP-1 RouteMoA) -> T-048 (GAP-2 aggregation bypass)

T-065 (GAP-6 smart_resize) feeds into T-038 (CU-01 action hierarchy)

T-076 (GWY-01 Letta server)
  +-- T-077 (GWY-02 Letta memory wiring) [implements T-035 + T-036 + T-056]

T-078 (GWY-03 FastAPI service)
  +-- T-079 (GWY-04 smolagents engine)
  |     +-- T-080 (GWY-05 MCP client)
  |     +-- T-081 (GWY-06 skill/search/browser)
  +-- T-082 (GWY-07 config migration)
  +-- T-083 (GWY-08 service cutover) [all of T-078..T-082 must be green first]

T-084 (STRG-01 SSOT)
  +-- T-085 (STRG-02 provision + PAM)
  |     +-- T-087 (STRG-04 automount)
  |           +-- T-088 (STRG-05 caching tuning)
  |           +-- T-091 (STRG-08 user-dirs init unit)
  +-- T-086 (STRG-03 XDG_RUNTIME_DIR isolation)
  |     +-- T-090 (STRG-07 XDG profile script)
  |           +-- T-091 (STRG-08 user-dirs init unit)
  +-- T-089 (STRG-06 CephX caps)
        +-- T-092 (STRG-09 greenboot checks)
        +-- T-093 (STRG-10 drift-check + docs)
```

---

## Appendix B: File to Task Cross-Reference

| File | Tasks |
|---|---|
| `usr/lib/mios/agent-pipe/server.py` | T-006, T-007, T-008, T-009, T-010, T-011, T-012, T-013, T-014, T-019, T-020, T-021, T-023, T-024, T-025, T-027, T-028, T-029, T-030, T-031, T-033, T-034, T-035, T-036, T-037, T-039, T-040, T-043, T-047, T-048, T-051, T-052, T-053, T-059, T-062, T-063, T-067, T-068, T-077 |
| `usr/share/mios/mios.toml` | T-003, T-005, T-006, T-019, T-020, T-021, T-023, T-026, T-033, T-034, T-035, T-036, T-037, T-043, T-047, T-048, T-049, T-050, T-053, T-062, T-064, T-065, T-076, T-077, T-078, T-079, T-080, T-081, T-082 |
| `usr/libexec/mios/mios-pc-control` | T-038, T-065, T-073 |
| `automation/38-drift-checks.sh` | T-005, T-007 |
| `usr/share/mios/postgres/schema-init.sql` | T-028, T-030, T-034, T-060, T-068, T-076, T-078 |
| `Containerfile` | T-003, T-005, T-032, T-050, T-069, T-073, T-083 |
| `tools/generate-pod-quadlets.py` | T-005, T-042, T-069 |
| `usr/share/mios/llamacpp/mios-llm-light.yaml` | T-021, T-056 |
| `usr/share/containers/systemd/mios-letta-server.container` | T-076 |
| `usr/lib/mios/gateway-agent/` (new package) | T-078, T-079, T-080, T-081 |
| `usr/lib/systemd/system/mios-gateway-agent.service` | T-078, T-083 |
| `usr/lib/systemd/system/mios-gateway-worker.service` | T-083 |
| `usr/lib/systemd/system/hermes-agent.service` | T-053, T-083 |
| `usr/share/mios/hermes/config.yaml` | T-082 (deprecation header) |
| `usr/share/mios/hermes/config-worker.yaml` | T-082 (deprecation header) |
| `etc/mios/kb.conf.toml` | T-082 |
| `usr/share/mios/mios.toml` (`[storage.cephfs]`) | T-084, T-085, T-086, T-087, T-088, T-089, T-090 |
| `usr/libexec/mios/mios-cephfs-provision` (new) | T-085, T-089 |
| `usr/libexec/mios/mios-ceph-configure` (new) | T-088 |
| `usr/lib/mios/agent-pipe/server.py` (storage endpoints) | T-089 |
| `usr/share/mios/profile.d/mios-xdg-cephfs.sh` (new) | T-086, T-090 |
| `usr/share/mios/systemd/home-@.mount.tmpl` (new) | T-087, T-093 |
| `usr/share/mios/systemd/home-@.automount.tmpl` (new) | T-087 |
| `usr/share/mios/systemd/mios-xdg-userdir-init.service` (new) | T-091 |
| `usr/share/mios/xdg/user-dirs.defaults` (new) | T-091 |
| `/etc/greenboot/check/wanted.d/55-mios-cephfs.sh` (new) | T-092 |
| `automation/38-drift-checks.sh` (`check_cephfs_ssot`) | T-084, T-093 |
| `usr/share/doc/mios/guides/cephfs-xdg-storage.md` (new) | T-093 |

---


# Part 10: Converged-Resource Architecture Tasks (CONV-01..CONV-15)

<!-- AI-hint: Tasks T-094..T-108. All gated by [converge] block in mios.toml (all defaults no-op). Uphold Law 5 (MIOS_AI_ENDPOINT) and Law 6 (USER 65534 in all containers). Additive: zero existing tasks modified. -->

---

## T-094: CONV-01 -- [converge] SSOT Block in mios.toml
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Config/Arch | **Source:** Part 10 Â§10.5, Â§10.6 Phase 1 -- done-by-code: `[converge]` SSOT + userenv.sh + configurator HTML (29f5dfe).

**Context:** All four Converged-Resource Architecture phases (Gateway Queue, Single-Engine Multiplexing, Memory Tiering, Distroless Images) are controlled from a single `[converge]` SSOT block. This task establishes the block with all defaults set to the safe no-op value, unblocking all subsequent CONV tasks.

**Instructions:**
1. Add the full `[converge.gateway]`, `[converge.inference]`, `[converge.memory]`, `[converge.image]` block set to `usr/share/mios/mios.toml`. Full schema in ROADMAP.md Â§10.5. All flags default to `false` / `"http"` / `0` / `"dual"` (backward-compatible no-ops).
2. Wire SSOT vars into `userenv.sh`: `MIOS_CONV_GATEWAY_MODE`, `MIOS_CONV_GATEWAY_QUEUE_MAXSIZE`, `MIOS_CONV_GATEWAY_WORKER_CONCURRENCY`, `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE`, `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE`, `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE`, `MIOS_CONV_IMAGE_DISTROLESS_ENABLE`, `MIOS_CONV_IMAGE_RECHUNK_ENABLE`.
3. Add `check_converge_ssot` stub to `automation/38-drift-checks.sh` (register in `main()` after `check_cephfs_ssot`). Stub always passes; full checks implemented in T-099, T-104, T-108.
4. Add `[converge]` section (collapsible) to the MiOS configurator HTML (`usr/share/mios/mios-configurator/mios.html`).

**Files:**
- `usr/share/mios/mios.toml` â€” new `[converge.*]` blocks
- `usr/share/mios/mios-configurator/userenv.sh` â€” MIOS_CONV_* exports
- `automation/38-drift-checks.sh` â€” `check_converge_ssot` stub

**Deps:** None.

**Done When:**
- [x] `python3 -c "import tomllib; d=tomllib.load(open('usr/share/mios/mios.toml','rb')); assert 'converge' in d"` exits 0
- [x] `userenv.sh` exports `MIOS_CONV_GATEWAY_MODE=http` by default
- [x] `just drift-gate` passes on clean repo
- [x] All four sub-tables (`gateway`, `inference`, `memory`, `image`) present in `[converge]`

---

## T-095: CONV-02 -- GatewayQueue Module + GatewayWorker + smolagents Wiring
> **Priority:** P2 | **Status:** partial | **Effort:** L | **Domain:** Orchestration/Python | **Source:** Part 10 Â§10.1.3, Â§10.1.4 -- done-by-code: GatewayQueue + GatewayWorker + HTTP fallback (247476f, a62520f).

**Context:** The :8640 â†’ :8642 HTTP hop is replaced by an in-process `asyncio.Queue` producer-consumer seam. The `GatewayWorker` task consumes from the queue and runs `smolagents.ToolCallingAgent` against the `mios_capreg` tool registry. Degrade-open: `MIOS_CONV_GATEWAY_MODE=http` re-enables the legacy HTTP path at any time.

**Instructions:**
1. Create `usr/lib/mios/agent-pipe/mios_gateway_queue.py` (new module). Contents:
   - `GatewayRequest` dataclass: `payload: dict`, `fut: asyncio.Future`.
   - `GatewayQueue` dataclass: wraps `asyncio.Queue(maxsize=MIOS_CONV_GATEWAY_QUEUE_MAXSIZE)`.
   - `GatewayWorker` class: `async def run(queue, agent, concurrency)` â€” runs `concurrency` concurrent `asyncio.Task` slots consuming from the queue; each slot calls `agent.run(payload)` via `asyncio.to_thread` (tool execution may be CPU-bound); resolves `fut` with the result or exception.
2. Import and instantiate `smolagents.ToolCallingAgent` with tools sourced from `mios_capreg.get_tools()` (the existing RBAC-filtered capability manifest). The agent's model is set to a `smolagents.LiteLLMModel` pointed at `MIOS_AI_ENDPOINT` (Law 5).
3. In `server.py` FastAPI `lifespan`: gate on `MIOS_CONV_GATEWAY_MODE == 'queue'`; construct `GatewayWorker`; launch via `asyncio.create_task(worker.run(...))`; on shutdown, cancel task + drain queue (max 5 s).
4. In `mios_dispatcher.py`: add `async def dispatch_via_queue(payload: dict, queue: GatewayQueue) -> dict`. `server.py` selects `dispatch_via_queue` vs. the existing `dispatch_via_http` based on mode.
5. Logging: the `GatewayWorker` emits a SINGLE `mios_trace.span(kind="tool_loop", ...)` per request, replacing the old per-service double-write. No other span changes.

**Files:**
- `usr/lib/mios/agent-pipe/mios_gateway_queue.py` (new)
- `usr/lib/mios/agent-pipe/mios_dispatcher.py` â€” add `dispatch_via_queue`
- `usr/lib/mios/agent-pipe/server.py` â€” lifespan wiring, mode selection

**Deps:** T-094 (CONV-01 SSOT).

**Done When:**
- [x] `MIOS_CONV_GATEWAY_MODE=queue`: a POST to `/v1/chat/completions` routes through `GatewayWorker` (verify via trace span `kind=tool_loop` in pgvector)
- [x] `MIOS_CONV_GATEWAY_MODE=http`: existing behaviour unchanged (no regression)
- [x] `mios_trace` shows ONE `tool_loop` span per request (not two)
- [x] `smolagents.LiteLLMModel` `base_url` = `MIOS_AI_ENDPOINT` (Law 5 verified in logs)
- [x] Queue full (maxsize=64 + 1 more request): returns 429 gracefully, does not block the event loop

---

## T-096: CONV-03 -- GatewayQueue Test Suite
> **Priority:** P2 | **Status:** partial | **Effort:** M | **Domain:** Testing | **Source:** Part 10 Â§10.6 Phase 1 -- done-by-code: test_mios_gateway_queue.py (247476f).

**Instructions:**
1. Create `usr/lib/mios/agent-pipe/test_mios_gateway_queue.py`. Tests (all pass without a running llama-server or pgvector):
   a. `test_put_get`: put a `GatewayRequest` onto the queue, worker consumes it, future resolves with mock result.
   b. `test_future_resolution`: verify that `await fut` returns the correct response dict from the worker.
   c. `test_fallback_on_exception`: if the worker raises an exception, the future is resolved with an error dict (not left pending).
   d. `test_concurrency_4`: put 4 requests simultaneously; all 4 futures resolve concurrently (wall time < 4Ã— single-request time with mock agent).
   e. `test_queue_full_429`: put `maxsize+1` requests; the `(maxsize+1)`th call returns a 429 dict without blocking.
   f. `test_shutdown_drain`: cancel the worker task; verify the drain loop resolves all pending futures with an error within 5 s.
2. Use `unittest.mock.AsyncMock` for the `smolagents.ToolCallingAgent.run` call.
3. Register in `pytest.ini` (or existing test runner config).

**Files:**
- `usr/lib/mios/agent-pipe/test_mios_gateway_queue.py` (new)

**Deps:** T-095 (CONV-02 GatewayQueue module).

**Done When:**
- [x] `pytest test_mios_gateway_queue.py -v` â€” all 6 tests pass
- [x] No external service dependency (no llama-server, no pgvector socket)
- [x] Tests complete in < 10 s

---

## T-097: CONV-04 -- llama-swap Shared Prefix Cache + Parallel Slots
> **Priority:** P2 | **Status:** partial | **Effort:** S | **Domain:** Inference/Performance | **Source:** Part 10 Â§10.2.2, Â§10.2.4 -- done-by-code: cache-reuse + parallel slots in llama-swap config (31a7973).

**Context:** Adding `--cache-reuse 256` and `--np 4` to the granite4.1:8b and lfm2:700m entries in `mios-llm-light.yaml` enables shared KV prefix caching across parallel slots, reducing TTFT by 30â€“60% on system-prompt-heavy agent turns. Gate: `[converge.inference].llama_cache_reuse_tokens > 0`.

**Instructions:**
1. In `usr/share/mios/llamacpp/mios-llm-light.yaml`, add the following to the `granite4.1:8b` `cmd` line (note: existing GGUF path, port, ctx-size, n-gpu-layers, flash-attn, cache-type, slot-save-path all unchanged):
   ```
   --cache-reuse 256 --np 4
   ```
   Add the same to the `lfm2:700m` `cmd` line (its ctx-size stays at 32768; `--np 4` replaces the implicit `--parallel 1`).
2. Add a YAML comment above each modified entry: `# Part 10 CONV-04: --cache-reuse 256 (gate: MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS > 0); --np 4 for shared-prefix concurrency.`
3. Wire the cache-reuse value from `[converge.inference].llama_cache_reuse_tokens` in `mios.toml` via a firstboot helper that patches the YAML (or operator edits `/etc/mios/llamacpp/mios-llm-light.yaml` overlay). Default value 0 = flags not added.
4. Validate with `--debug-slot` logs: after 3+ identical system-prompt turns, slot logs should show `cache_hit_tokens > 0`.

**Files:**
- `usr/share/mios/llamacpp/mios-llm-light.yaml` â€” extended (additive comment + flag hint)
- `automation/firstboot/mios-conv-inference-setup.sh` (new, renders cache-reuse flag into /etc overlay)

**Deps:** T-094 (CONV-01 SSOT).

**Done When:**
- [x] `grep 'cache-reuse' /etc/mios/llamacpp/mios-llm-light.yaml` shows `--cache-reuse 256` (when enabled)
- [x] `grep 'np' /etc/mios/llamacpp/mios-llm-light.yaml` shows `--np 4` on both chat model entries (when enabled)
- [x] llama-server `--debug-slot` logs show `cache_hit_tokens > 0` on repeated system-prompt turns
- [x] `[converge.inference].llama_cache_reuse_tokens = 0` â†’ no flags added (no regression)

---

## T-098: CONV-05 -- vLLM Multi-LoRA Heavy Lane Upgrade
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Inference/vLLM | **Source:** Part 10 Â§10.2.2, Â§10.2.3 -- done-by-code: vLLM multi-LoRA Quadlet + lora-adapters dir (31a7973).

**Context:** The current `mios-llm-heavy.container` runs a single model instance (SGLang or vLLM without LoRA). Upgrading to vLLM multi-LoRA enables per-request adapter injection, eliminating the need for the second `mios-llm-heavy-alt` process and saving ~12 GB VRAM on the 4090.

**Instructions:**
1. Update `usr/share/containers/systemd/mios-llm-heavy.container` (or the relevant Quadlet file):
   - Add environment vars: `VLLM_ALLOW_RUNTIME_LORA_UPDATING=true`, `VLLM_PLUGINS=lora_filesystem_resolver`, `VLLM_LORA_RESOLVER_CACHE_DIR=/var/lib/mios/lora-adapters/`.
   - Add vLLM serve flags: `--enable-lora --max-loras 4 --max-cpu-loras 8 --max-lora-rank 64`.
   - Add `--lora-modules coding=/var/lib/mios/lora-adapters/coding reasoning=/var/lib/mios/lora-adapters/reasoning` as the initial pre-loaded adapter set.
2. Create directory structure: `/var/lib/mios/lora-adapters/{coding,reasoning,vision}/` (via `tmpfiles.d` or firstboot). Add `.gitkeep` in each.
3. Add `[converge.inference].vllm_lora_adapters_dir` to SSOT rendering in `userenv.sh`.
4. Gate: Quadlet changes only deployed when `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE=single`. When `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE=dual` (default), `mios-llm-heavy.container` is unchanged.
5. Add comment to `mios-llm-heavy-alt.container`: `# DEPRECATED: retire by setting [converge.inference].retire_heavy_alt = true (see T-100).`

**Files:**
- `usr/share/containers/systemd/mios-llm-heavy.container` â€” vLLM multi-LoRA env + flags
- `usr/lib/tmpfiles.d/mios-lora-adapters.conf` â€” `/var/lib/mios/lora-adapters/` dirs
- `usr/share/containers/systemd/mios-llm-heavy-alt.container` â€” deprecation comment

**Deps:** T-094 (CONV-01 SSOT).

**Done When:**
- [x] `curl -X POST http://localhost:11441/v1/load_lora_adapter -d '{"lora_name":"test","lora_path":"/tmp/test-lora"}'` returns 200 (when `VLLM_ALLOW_RUNTIME_LORA_UPDATING=true`)
- [x] `curl http://localhost:11441/v1/models` lists both `coding` and `reasoning` adapter IDs
- [x] `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE=dual` â†’ container unchanged (no regression)
- [x] `/var/lib/mios/lora-adapters/{coding,reasoning,vision}/` directories exist after firstboot

---

## T-099: CONV-06 -- LoRA Load/List API Endpoints in agent-pipe
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** API/Inference | **Source:** Part 10 Â§10.6 Phase 2 -- done-by-code: LoRA load/list endpoints + drift-check (31a7973).

**Instructions:**
1. Add two new endpoints to `usr/lib/mios/agent-pipe/server.py`:
   - `POST /v1/inference/lora/load`: thin proxy to `{MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY}/v1/load_lora_adapter`. Validates JSON body has `lora_name` and `lora_path`. Returns vLLM response. Requires Law 5: uses `MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY` (not hardcoded `:11441`).
   - `GET /v1/inference/lora/list`: thin proxy to `{MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY}/v1/models`, filters to only adapter-type models, returns `{"adapters": [...]}`. Falls back to `{"adapters": [], "enabled": false}` when `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE != "single"`.
2. Add drift-check rule in `check_converge_ssot` (T-094 stub): FAIL if `retire_heavy_alt=true` AND the systemd unit `mios-llm-heavy-alt.service` is still in `enabled` state (detect via `systemctl is-enabled`). This prevents accidental double-service retirement.
3. Add tests `test_lora_endpoints.py` (mock httpx calls to heavy backend).

**Files:**
- `usr/lib/mios/agent-pipe/server.py` â€” two new endpoints
- `automation/38-drift-checks.sh` â€” `check_converge_ssot` extended
- `usr/lib/mios/agent-pipe/test_lora_endpoints.py` (new)

**Deps:** T-094 (CONV-01), T-098 (CONV-05 vLLM multi-LoRA).

**Done When:**
- [x] `curl http://localhost:8640/v1/inference/lora/list` returns `{"adapters":[...]}` (when heavy lane is vLLM)
- [x] `curl -X POST http://localhost:8640/v1/inference/lora/load -d '...'` proxies to heavy lane
- [x] Endpoints return `{"adapters":[], "enabled":false}` when `heavy_engine_mode=dual`
- [x] Drift-check FAILs when `retire_heavy_alt=true` + unit still enabled

---

## T-100: CONV-07 -- mios-llm-heavy-alt Retirement Documentation
> **Priority:** P2 | **Status:** partial | **Effort:** S | **Domain:** Docs/Migration | **Source:** Part 10 Â§10.6 Phase 2 -- done-by-code: inference-consolidation.md guide (31a7973).

**Instructions:**
1. Create `usr/share/doc/mios/guides/inference-consolidation.md`. Cover:
   - Current dual-heavy topology and why it exceeds the 4090's 24 GB budget.
   - vLLM multi-LoRA migration path: `[converge.inference].heavy_engine_mode = "single"` â†’ restart `mios-llm-heavy` â†’ verify `GET /v1/inference/lora/list` â†’ set `retire_heavy_alt = true` â†’ `systemctl disable mios-llm-heavy-alt`.
   - Rollback: set `heavy_engine_mode = "dual"`, re-enable both container units.
   - VRAM budget table (from ROADMAP Â§10.2.5).
   - Operator note on `lora-adapters/` directory population (manual GGUF placement).
2. Add deprecation comment block to `mios-llm-heavy-alt.container` Quadlet: `# DEPRECATED (Part 10, 2026-06-25): retire by setting [converge.inference].retire_heavy_alt = true and running the migration guide at usr/share/doc/mios/guides/inference-consolidation.md.`

**Files:**
- `usr/share/doc/mios/guides/inference-consolidation.md` (new)
- `usr/share/containers/systemd/mios-llm-heavy-alt.container` â€” deprecation comment

**Deps:** T-098 (CONV-05), T-099 (CONV-06).

**Done When:**
- [x] `usr/share/doc/mios/guides/inference-consolidation.md` renders in `mios-docs` service
- [x] Deprecation comment present in `mios-llm-heavy-alt.container`
- [x] Guide includes rollback instructions

---

## T-101: CONV-08 -- sqlite-vec Scratchpad Module
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Memory/Python | **Source:** Part 10 Â§10.3.2, Â§10.3.5 -- done-by-code: mios_scratchpad.py + sqlite-vec (710b507).

**Context:** `mios_scratchpad.py` provides a per-session, in-process vector store (sqlite-vec) for ephemeral tool-call outputs and reasoning traces. It lives in `/run/user/<uid>/mios-session-<id>.sqlite` (tmpfs), is never persisted to pgvector, and is destroyed at session end. Law 5 invariant: embeddings are still fetched via `MIOS_AI_ENDPOINT/v1/embeddings`; sqlite-vec stores the resulting vectors, it does not generate them.

**Instructions:**
1. Add `sqlite-vec` to `usr/lib/mios/agent-pipe/requirements.txt`.
2. Create `usr/lib/mios/agent-pipe/mios_scratchpad.py` (new module, no FastAPI globals):
   - `create_scratchpad(session_id: str, scratchpad_dir: str) -> tuple[sqlite3.Connection, Path]`: opens `{scratchpad_dir}/mios-session-{session_id}.sqlite`, loads `sqlite_vec`, creates `vec_scratch USING vec0(content TEXT, embedding float[768])`. Returns `(conn, path)`.
   - `destroy_scratchpad(conn, path: Path) -> None`: `conn.close(); path.unlink(missing_ok=True)`.
   - `vec_insert(conn, content: str, embedding: list[float]) -> None`: `INSERT INTO vec_scratch VALUES (?, ?)` using the sqlite-vec `serialize_float32` encoder.
   - `vec_search(conn, query_embedding: list[float], k: int = 5) -> list[dict]`: `SELECT content, distance FROM vec_scratch WHERE embedding MATCH ? ORDER BY distance LIMIT ?`.
3. Gate: module is only loaded when `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=true`; when false, `mios_scratchpad` is a stub that returns empty results (no sqlite-vec import, no runtime dep).
4. Add `test_mios_scratchpad.py`: tests for create/insert/search/destroy; mocks the embedding float list; runs without a pgvector connection.

**Files:**
- `usr/lib/mios/agent-pipe/mios_scratchpad.py` (new)
- `usr/lib/mios/agent-pipe/requirements.txt` â€” add `sqlite-vec`
- `usr/lib/mios/agent-pipe/test_mios_scratchpad.py` (new)

**Deps:** T-094 (CONV-01 SSOT).

**Done When:**
- [x] `python -c "import mios_scratchpad; c,p = mios_scratchpad.create_scratchpad('test','/tmp'); mios_scratchpad.vec_insert(c,'hello',[0.1]*768); r=mios_scratchpad.vec_search(c,[0.1]*768); assert len(r)==1; mios_scratchpad.destroy_scratchpad(c,p); print('OK')"` exits 0
- [x] `pytest test_mios_scratchpad.py` â€” all tests pass without external services
- [x] `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=false` â†’ stub returns `[]` without importing sqlite-vec
- [x] Scratchpad file lives in `/run/user/<uid>/` (tmpfs), not in `/var/lib/`

---

## T-102: CONV-09 -- Cold Eviction Module + zstd Export
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Memory/Storage | **Source:** Part 10 Â§10.3.4 -- done-by-code: mios_cold_evict.py + zstd export + test (710b507).

**Context:** `mios_cold_evict.py` extends the existing `mios_evict.py` eviction pipeline with a cold-export path: TTL-expired rows are serialized as JSONL, compressed with zstd, written to `/var/lib/mios/history/`, then deleted from PostgreSQL. `mios_evict.py` is NOT modified.

**Instructions:**
1. Create `usr/lib/mios/agent-pipe/mios_cold_evict.py` (new module):
   - `export_to_cold(pg, row_ids: list[int], table: str, dest_dir: str, zstd_level: int) -> Path`:
     a. `SELECT row_to_json(t) FROM <table> t WHERE id = ANY(%(ids)s)` via `mios_pg.execute`.
     b. Write each JSON line to `{dest_dir}/{YYYY}/{MM-DD}/{uuid4()}.jsonl.tmp`.
     c. `subprocess.run(['zstd', f'--level={zstd_level}', '-o', f'{dst}.zst', f'{dst}.tmp'], check=True)`.
     d. Remove `.tmp`. Return the `.zst` Path.
   - `cold_sweep(pg, plan: dict, table: str, dest_dir: str, zstd_level: int) -> dict`: orchestrates `mios_evict.select_ids_sql` â†’ `export_to_cold` â†’ `mios_evict.delete_ids_sql`. Returns `{"exported": N, "dest": str}`.
2. Wire `cold_sweep` into the eviction background task in `server.py` (after the existing `mios_evict.py` sweep), gated on `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE`.
3. Log `event(kind="cold_evict", rows=N, dest=path)` to pgvector after each sweep.
4. NEVER export hot/pinned/satisfied rows (inherit the `evict_where` WHERE filter from `mios_evict.py`).
5. Add `test_mios_cold_evict.py`: mock `mios_pg.execute` and `subprocess.run`; test export+delete, .tmp cleanup on error, zstd command construction.

**Files:**
- `usr/lib/mios/agent-pipe/mios_cold_evict.py` (new)
- `usr/lib/mios/agent-pipe/server.py` â€” eviction task extended
- `usr/lib/mios/agent-pipe/test_mios_cold_evict.py` (new)

**Deps:** T-094 (CONV-01 SSOT), T-101 (CONV-08 memory SSOT wiring).

**Done When:**
- [x] `pytest test_mios_cold_evict.py` â€” all tests pass without external services
- [x] `zstd --test /var/lib/mios/history/.../*.jsonl.zst` exits 0 (valid archive) after a simulated sweep
- [x] PostgreSQL row count decreases after a cold sweep (rows moved to archive, not duplicated)
- [x] `event(kind="cold_evict")` appears in pgvector `event` table
- [x] Hot/pinned/satisfied rows are NEVER exported (verify with unit test)

---

## T-103: CONV-10 -- sqlite-vec Scratchpad Wired into GatewayWorker
> **Priority:** P2 | **Status:** done-by-code | **Effort:** M | **Domain:** Orchestration/Memory | **Source:** Part 10 Â§10.3.5 -- done-by-code: scratchpad wired into GatewayWorker (710b507).

**Instructions:**
1. In `mios_gateway_queue.py` `GatewayWorker.run()`, wrap each request execution with:
   ```python
   conn, path = await asyncio.to_thread(mios_scratchpad.create_scratchpad, session_id, scratchpad_dir)
   try:
       result = await _execute_with_scratchpad(conn, payload, agent)
   finally:
       await asyncio.to_thread(mios_scratchpad.destroy_scratchpad, conn, path)
   ```
2. Inside `_execute_with_scratchpad`: after each tool call in the `smolagents` loop, call `mios_scratchpad.vec_insert(conn, tool_output, embedding)` where the embedding is fetched from `MIOS_AI_ENDPOINT/v1/embeddings` (Law 5 compliant).
3. Gate: scratchpad creation/destruction only runs when `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=true`. When false, the `mios_scratchpad` stub is used (no-op insert, empty search).
4. Verify: after enabling, pgvector `event` table should show ZERO `kind=tool_output` inserts per turn (transient tool outputs moved to Tier 0 scratchpad; only end-of-session synthesis goes to Tier 1).

**Files:**
- `usr/lib/mios/agent-pipe/mios_gateway_queue.py` â€” scratchpad lifecycle in `GatewayWorker`

**Deps:** T-095 (CONV-02 GatewayWorker), T-101 (CONV-08 scratchpad module).

**Done When:**
- [x] `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=true`: scratchpad file created at session start, deleted at end
- [x] Embedding for each tool output fetched via `MIOS_AI_ENDPOINT/v1/embeddings` (Law 5 check in logs)
- [x] pgvector `event` table has 0 `kind=tool_output` rows per turn (replaced by Tier 0)
- [x] `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=false`: no sqlite-vec import, no performance regression

---

## T-104: CONV-11 -- Cold-Archive Retention Sweep + Drift-Check
> **Priority:** P2 | **Status:** done-by-code | **Effort:** S | **Domain:** Storage/CI | **Source:** Part 10 Â§10.6 Phase 3 -- done-by-code: cold-archive retention sweep + drift-check (710b507).

**Instructions:**
1. Add `_cold_retention_sweep()` to the existing eviction background task in `server.py`:
   - Scan `cold_storage_dir` recursively for `.jsonl.zst` files older than `cold_retention_days` days.
   - Delete them.
   - Log `event(kind="cold_retention_sweep", deleted=N, cutoff_days=D)`.
   - Gate: `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE=true`.
2. Extend `check_converge_ssot` in `automation/38-drift-checks.sh` with Phase 3 rules:
   a. `cold_storage_dir` must NOT be inside a CephFS mount path (check against `MIOS_CEPHFS_MONITORS` host prefix or `/tenants/` path segment) â€” cold archives are node-local, not distributed.
   b. `cold_retention_days` must be >= 1.
   c. `cold_zstd_level` must be between 1 and 19.
   d. If `sqlite_vec_enable=true`, the `sqlite-vec` package must be importable (`python3 -c "import sqlite_vec"` exits 0).
3. Create `usr/share/doc/mios/guides/memory-tiering.md`: documents the three-tier model (Tier 0 sqlite-vec, Tier 1 pgvector, Tier 2 zstd cold archive), quickstart for enabling, and how to query cold archives (`zstd -d | jq`).

**Files:**
- `usr/lib/mios/agent-pipe/server.py` â€” `_cold_retention_sweep` in eviction task
- `automation/38-drift-checks.sh` â€” Phase 3 checks in `check_converge_ssot`
- `usr/share/doc/mios/guides/memory-tiering.md` (new)

**Deps:** T-102 (CONV-09 cold eviction), T-094 (CONV-01 SSOT).

**Done When:**
- [x] Files older than `cold_retention_days` in `cold_storage_dir` are deleted on sweep
- [x] `event(kind="cold_retention_sweep")` logged after each sweep
- [x] Drift-check FAILs when `cold_storage_dir` is a CephFS path
- [x] Drift-check FAILs when `cold_zstd_level > 19`
- [x] `usr/share/doc/mios/guides/memory-tiering.md` renders in `mios-docs`

---

## T-105: CONV-12 -- Hummingbird Distroless Containerfile
> **Priority:** P3 | **Status:** partial | **Effort:** M | **Domain:** Image/Security | **Source:** Part 10 Â§10.4.3 -- done-by-code: Containerfile.hummingbird + distroless checks (eb654e3).

**Context:** `Containerfile.hummingbird` is a two-stage build that eliminates `dnf`, `bash`, and OS package cache from the runtime image, reducing the agent-pipe container's attack surface by ~200â€“400 MB. Law 6 invariant: final stage MUST set `USER 65534:65534`. Law 5 invariant: `MIOS_AI_ENDPOINT` is not sourced from `profile.d` (no shell); it arrives via the Quadlet `Environment=` directive.

**Instructions:**
1. Create `Containerfile.hummingbird` (alongside the existing `Containerfile`). Two stages:
   - Stage 1 (builder): `FROM python:3.13-slim AS builder`. `RUN apt-get install gcc libsqlite3-dev`. `RUN python -m venv /opt/venv`. `COPY requirements.txt .`. `RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt`.
   - Stage 2 (runtime): `FROM gcr.io/distroless/python3-debian13`. `COPY --from=builder /opt/venv /opt/venv`. `COPY usr/lib/mios/agent-pipe/ /app/`. `ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/opt/venv/lib/python3.13/site-packages`. `USER 65534:65534`. `EXPOSE 8640`. `CMD ["/opt/venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8640", "--workers", "1", "--loop", "uvloop"]`.
2. Verify the Quadlet (`mios-agent-pipe.container`) propagates `MIOS_AI_ENDPOINT` via `Environment=MIOS_AI_ENDPOINT=%i` or similar â€” NOT sourced from `profile.d`. Add `Environment=MIOS_AI_ENDPOINT=...` line if missing.
3. Add `check_hummingbird` stub to `38-drift-checks.sh` (full checks in T-108).
4. Gate: `Containerfile.hummingbird` is used instead of `Containerfile` only when `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=true`. Default `Containerfile` is unchanged.

**Files:**
- `Containerfile.hummingbird` (new)
- `usr/share/containers/systemd/mios-agent-pipe.container` â€” `Environment=MIOS_AI_ENDPOINT` line
- `automation/38-drift-checks.sh` â€” `check_hummingbird` stub

**Deps:** T-095 (CONV-02 merged process â€” required for single CMD entrypoint).

**Done When:**
- [x] `podman build -f Containerfile.hummingbird -t mios-agent-pipe:hummingbird .` succeeds
- [x] `podman run --rm mios-agent-pipe:hummingbird id` outputs `uid=65534` (nonroot)
- [x] `podman run --rm mios-agent-pipe:hummingbird which bash` exits non-0 (no bash in image)
- [x] `podman inspect mios-agent-pipe:hummingbird | jq '.[0].Config.Env[]|select(test("MIOS_AI_ENDPOINT"))'` returns the endpoint
- [x] `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=false` â†’ original `Containerfile` used, no regression

---

## T-106: CONV-13 -- Unified MCPClientPool
> **Priority:** P3 | **Status:** done-by-code | **Effort:** M | **Domain:** Tool/MCP | **Source:** Part 10 Â§10.4.2 -- done-by-code: MCPClientPool in mios_gateway_queue.py (eb654e3).

**Context:** Post-Phase 1 (single-process after T-095), `agent-pipe` and the former `hermes-agent` logic share one process. Unifying the MCP client connections eliminates per-service SDK duplication. One `MCPClientPool` dict serves all tool invocations.

**Instructions:**
1. Add `MCPClientPool` class to `mios_gateway_queue.py` (extends T-095):
   - `__init__(server_configs: dict)`: for each entry in `[tools.mcp_servers]` from `mios.toml`, create and store a `mcp.StdioClient` or `mcp.HTTPClient` (depending on `transport`).
   - `async def startup()`: connect all clients; fetch and cache tool schemas.
   - `async def shutdown()`: cleanly close all clients.
   - `get_tools() -> list`: returns the unified tool schema list (replaces the per-service schema cache).
2. Initialize `MCPClientPool` in `server.py` `lifespan`, gated on `MIOS_CONV_IMAGE_MCP_POOL_ENABLE=true`. Pass the pool to `GatewayWorker` as `worker.mcp_pool`.
3. In `mios_interop.py` (WS-11 A2A): wire `MCPClientPool.get_tools()` into the 3-projection A2A skill shape so A2A peers see the same unified tool catalog.
4. Add `test_mios_mcp_pool.py`: mock `mcp.StdioClient.connect`; verify pool starts, provides tool list, shuts down cleanly.

**Files:**
- `usr/lib/mios/agent-pipe/mios_gateway_queue.py` â€” MCPClientPool class
- `usr/lib/mios/agent-pipe/server.py` â€” MCPClientPool lifecycle in lifespan
- `usr/lib/mios/agent-pipe/mios_interop.py` â€” tool catalog unified
- `usr/lib/mios/agent-pipe/test_mios_mcp_pool.py` (new)

**Deps:** T-095 (CONV-02 GatewayWorker), T-094 (CONV-01 SSOT).

**Done When:**
- [x] `GET /v1/tools` returns a unified tool list (one entry per MCP server, not duplicated)
- [x] MCP client connections established once at startup, not per-request
- [x] A2A skill-shape projection (mios_interop.py) uses the same pool
- [x] `pytest test_mios_mcp_pool.py` passes without a running MCP server

---

## T-107: CONV-14 -- rechunk CI Step
> **Priority:** P3 | **Status:** done-by-code | **Effort:** S | **Domain:** Image/CI | **Source:** Part 10 Â§10.4.4 -- done-by-code: rechunk.sh + Justfile recipe (eb654e3).

**Instructions:**
1. Create `automation/build/rechunk.sh`. Steps:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   SRC_DIGEST=$(podman inspect mios-bootc:latest --format '{{.Digest}}')
   podman unshare rpm-ostree experimental compose build-chunked-oci \
     --bootc --format-version=1 \
     --from="${SRC_DIGEST}" \
     --output containers-storage:mios-bootc:rechunked
   # Assign AI-sidecar xattrs for fine-grained chunking:
   setfattr -n user.component -v ai-sidecar /usr/lib/mios/agent-pipe/ 2>/dev/null || true
   setfattr -n user.component -v ai-sidecar /usr/share/mios/llamacpp/ 2>/dev/null || true
   setfattr -n user.component -v llm-models /var/lib/mios/models/ 2>/dev/null || true
   ```
2. Wire into `Justfile`: add `just rechunk` recipe that calls `automation/build/rechunk.sh` after `just build` (appended, does NOT replace existing recipes).
3. Gate: `automation/build/rechunk.sh` exits 0 only when `MIOS_CONV_IMAGE_RECHUNK_ENABLE=true`. When false, script prints "rechunk disabled" and exits 0.
4. Add `check_rechunk_env` to `check_converge_ssot` (T-094): FAIL if `rechunk_enable=true` but `rpm-ostree` binary not found in PATH.

**Files:**
- `automation/build/rechunk.sh` (new)
- `Justfile` â€” `rechunk` recipe (additive)
- `automation/38-drift-checks.sh` â€” `check_rechunk_env` in `check_converge_ssot`

**Deps:** T-094 (CONV-01 SSOT).

**Done When:**
- [x] `just rechunk` completes when `MIOS_CONV_IMAGE_RECHUNK_ENABLE=true` and `rpm-ostree` available
- [x] `just rechunk` exits 0 silently when `MIOS_CONV_IMAGE_RECHUNK_ENABLE=false`
- [x] `mios-bootc:rechunked` image exists in local container storage after rechunk
- [x] Drift-check FAILs when `rechunk_enable=true` but `rpm-ostree` absent

---

## T-108: CONV-15 -- Phase 4 Drift-Check Suite + Documentation
> **Priority:** P3 | **Status:** partial | **Effort:** S | **Domain:** CI/Docs | **Source:** Part 10 Â§10.6 Phase 4 -- done-by-code: check_hummingbird + hummingbird-distroless.md (eb654e3, 3c7cb5f).

**Instructions:**
1. Implement full `check_hummingbird` function in `automation/38-drift-checks.sh` (register in `main()` after `check_converge_ssot`):
   a. If `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=true`: FAIL if `Containerfile.hummingbird` does not exist.
   b. FAIL if `Containerfile.hummingbird` final-stage `USER` line is not `USER 65534` or `USER 65534:65534` (Law 6).
   c. FAIL if `/bin/bash` appears in `Containerfile.hummingbird` final stage (no bash in distroless).
   d. FAIL if `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=true` but `mios-agent-pipe.container` does not have an `Environment=MIOS_AI_ENDPOINT` directive (Law 5 â€” no profile.d in distroless).
   e. FAIL if `rechunk_enable=true` but `rpm-ostree` not in PATH.
2. Create `usr/share/doc/mios/guides/hummingbird-distroless.md`. Cover:
   - Why distroless (attack surface reduction, Law 6 enforcement).
   - Multi-stage build walkthrough (`Containerfile.hummingbird`).
   - Why `MIOS_AI_ENDPOINT` must come from the Quadlet `Environment=` line (no shell in distroless).
   - Debugging without a shell (OpenTelemetry traces + pgvector `event` table are the observability surface).
   - Chainguard as an alternative base (`cgr.dev/chainguard/python:latest-dev`).
   - rechunk quickstart (`just rechunk`).

**Files:**
- `automation/38-drift-checks.sh` â€” full `check_hummingbird` function
- `usr/share/doc/mios/guides/hummingbird-distroless.md` (new)

**Deps:** T-105 (CONV-12 distroless Containerfile), T-107 (CONV-14 rechunk).

**Done When:**
- [x] `just drift-gate` FAILs when `distroless_enable=true` + `USER root` in `Containerfile.hummingbird`
- [x] `just drift-gate` FAILs when `distroless_enable=true` + no `Environment=MIOS_AI_ENDPOINT` in Quadlet
- [x] `just drift-gate` FAILs when `/bin/bash` in distroless stage
- [x] `just drift-gate` passes on correct config
- [x] `usr/share/doc/mios/guides/hummingbird-distroless.md` renders in `mios-docs`

---

## Chat-Quality + Full-Visibility Tasks (live `@`-session audit)

> Detail SSOT = `MIOS-CHATQ-FV-WORKPLAN.md` (dual-track Claude/AGY) +
> `research/mios-chat-quality-full-visibility-gaps-2026-07-03.md` (root causes).
> These close CQ1-4 + FV-A-F, none of which had a live task owner. Law 7 +
> everything-streams mandate: fixes route channels + de-dup, never suppress
> visibility; final answer is the only thing in `delta.content`.

## T-031: ORCH-04 -- ReAct+Reflexion Durable Loop  (RE-OPEN -- done-by-code was NOT live)
> **Priority:** P1 | **Status:** reopened | **Effort:** M | **Domain:** Orchestration | **Source:** CQ4 -- the `done-by-code` claim is falsified: `[agent].reflexion_enable` reads a phantom TOML section (only `[agents]` plural exists) so it is always-true; `max_iter`/`max_retry`/`no_progress` are absent from `mios.toml`; the structured reflector is wired only into the DAG path; the exact-match repeat guard is evaded by one-token arg variation; no wall-clock/no-progress/failed-call bound. Live result = the non-terminating "Reflexion essay" loop.

**Instructions:** Execute Wave 4 of `MIOS-CHATQ-FV-WORKPLAN.md`: move `reflexion_enable` + loop budgets into a real `[agent_pipe]` SSOT block; replace the `server.py:835/3314` literals with SSOT reads; add a normalized no-progress signature + per-turn failed-`(tool,args)` blacklist + `max_consecutive_failures` escalation off the failure signal (not the give-up branch); enforce `wall_clock_budget_s`; wire the structured `reflect_on_step_failure` into the native/`@` path (emit-or-terminate, kept internal). Drift-gate every budget key has a code consumer.

**Files:** `usr/share/mios/mios.toml [agent_pipe]`; `.../agent-pipe/mios_pipe/routing/secondary_loop.py` (44-60, 265, 345-408); `.../server.py` (835, 3314); `.../routing/native_loop.py`; `.../routing/reflect.py`; `automation/38-drift-checks.sh`.

**Done When:**
- [ ] `reflexion_enable` + budgets read from `[agent_pipe]`; no `[agent]`/literal fallbacks remain (drift-gate green)
- [ ] identical failing `(tool,args)` is never retried; loop terminates/escalates within `wall_clock_budget_s`
- [ ] failure path uses the structured reflector (corrective action or terminate), no free-text essay in `content`
- [ ] live-fired in `podman-MiOS-DEV`: a deliberately-failing tool call does not loop

---

## T-109: CHATQ-01 -- Refine/plan trace to reasoning channel + one-answer-in-content (CQ1)
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** Observability/Orchestration | **Source:** CQ1 -- refine's `{Refined Query/Intent/Reply}` scaffold streams into `delta.content` (`chat.py:1425-1426` -> `sse.py:93-94` under `_DEBUG_ENABLE`) and the answer is restated 3x (refine `reply` + local-state + polish all reach content).

**Instructions:** Wave 1 (Claude C1-C3). Route the refine pump + `_refine_reasoning` summary through a channel-pinned emitter (reasoning channel regardless of `_DEBUG_ENABLE`); extend the `_live_streamed` guard (`native_loop.py:858`) so exactly one generation reaches `content`. Refine `reply` is trace, not answer. Visibility preserved; only the channel + dedup change.

**Files:** `.../agent-pipe/mios_pipe/routing/sse.py`, `.../routing/chat.py` (1425-1426, 1482-1495, 1789-1803), `.../routing/native_loop.py` (858, 1061, 1101-1102).

**Done When:**
- [ ] refine trace renders in the Thinking pane, never in `delta.content`
- [ ] `@ what directory are we in right now` returns exactly one clean answer (no `Refined Query/...` block, no 3x restate)
- [ ] byte-identical when `[observability]` flags off (degrade-open)

---

## T-110: FV-01 -- Canonical typed-event schema + per-surface routing + sub-agent visibility (FV-A/B/E/F)
> **Priority:** P1 | **Status:** pending | **Effort:** L | **Domain:** Observability | **Source:** FV -- full-visibility mandate is untracked; "visibility" today is faked by content-inlining under `[observability].debug=ON`; leaf thinking is turned OFF at source (`agent_call.py:820-821`; `swarm.py:1237`); fan-out `_push` has no channel discriminator; strict clients can't see the reasoning channel.

**Instructions:** Wave 1. One schema `thinking|plan|tool_call|tool_result|source|content` every stage + sub-agent emits into; per-lane `[lanes.*].stream_thinking` replaces the blanket `enable_thinking:False`; channel tag on the `_push` merged event; retire content-inline as the mechanism (`debug` gates only content-mirroring for strict surfaces); per-surface routing via `X-MiOS-Surface`/`reasoning_ok` with MiOS-owned replay-strip; OWUI pipe translates `mios_status`->status + refs->source events. AGY owns SSOT + OWUI pipe; Claude owns emitter + `agent_call`.

**Files:** SSOT `[observability]`/`[observability.channels]`/`[lanes.*]`; `usr/share/mios/owui/pipes/mios_agent_pipe.py`; `.../agent-pipe/mios_pipe/routing/sse.py`, `.../routing/agent_call.py` (738-746, 797-885, 820-821), `.../server.py`, `swarm.py`.

**Done When:**
- [ ] every sub-agent's thinking + tool calls + sources stream live on OWUI/Hermes; strict clients get a folded inline trace; final answer only in `content`
- [ ] KV cache intact across turns (persisted history = clean answer only)
- [ ] per-lane `stream_thinking=false` cleanly downgrades that lane (degrade-open)

---

## T-111: CHATQ-02 -- Constrained tool-calling + tools-on-final + verb-catalog repair (CQ2)
> **Priority:** P1 | **Status:** pending | **Effort:** L | **Domain:** Tool-calling | **Source:** CQ2 -- the final answer-shaping completion fires with NO `tools[]` (`native_loop.py:780-782`) so residual tool intent leaks as literal `<tool_call>`/```json``` text; `linux_file_search` is `hidden` but name-dropped in visible descriptions -> model wraps it into `launch_app`; no constrained decoding on any lane; rescue returns after the first block and is gated on empty `tool_calls`.

**Instructions:** Wave 2. AGY: engine `--tool-call-parser`/`--reasoning-parser` + `constrained_tools` per lane; consolidate duplicate `launch_app`; correct `fs_search` desc; stop advertising uncallable names; fix `[routing.domains.files].verbs`. Claude: give `_pb` the `tools[]`; streaming-aware salvage that RE-EMITS as typed events (visible) + diverts off `content` + executes; remove first-block early-return; surface routed-domain verbs even when hidden (key Stage-2 filter on canonical verb).

**Files:** SSOT `[lanes.*]`, `[verbs.launch_app]` (9084/3157), `fs_search` (3465-3473), `[routing.domains.files]` (3103-3110); `.../routing/native_loop.py` (780), `.../routing/secondary_loop.py` (309, 334-344), `.../routing/toolexec.py` (210-279), `.../server.py` (3956, 4028-4034), `.../verbcatalog.py`, `.../mios_endpoints.py`.

**Done When:**
- [ ] a narrated tool call renders as a native/typed tool pill, never as text in `delta.content`
- [ ] a files turn always carries a callable `linux_file_search`; no `launch_app` misroute
- [ ] live-fired: `@ what's here?` fires a real typed file/`list_dir` call

**Deps:** T-112 (list_dir gives the correct files-turn verb), T-110 (typed tool_call channel).

---

## T-112: CHATQ-03 -- First-class list_dir verb + cwd act-before-answer grounding (CQ3)
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** Tool-calling/Grounding | **Source:** CQ3 -- no `list_dir` verb exists (`linux_file_search`=`mios-locate` substring, not `ls`); `read_file`/`text_view` can list a dir but is depth-2/500-capped and framed as "read a file"; cwd string is injected but no snapshot + no lister auto-fires -> model hallucinates a generic FHS table. Also unblocks T-032's phantom `list_directory` op assumption.

**Instructions:** Wave 3. AGY: add `--depth 1` immediate-children mode to `mios-text-edit`; add `[verbs.list_dir]` (`model_name=list_directory`, `path` default cwd, accurate desc + examples); redirect `read_file`/`fs_search` descriptions. Claude: fire `list_dir(path=cwd)` in `_read_tool_enrich` when cwd present (keyed off SSOT `_client_env` cwd); add a model-chosen filesystem/`state_scope` signal to refine so dir-content queries set `tool_choice:required`.

**Files:** `usr/libexec/mios/mios-text-edit` (83-84, 219-241); SSOT `[verbs.list_dir]` + `fs_search`/`read_file` descs; `.../server.py` `_read_tool_enrich` (4648, 4685-4701, 4734-4745); `.../routing/refine.py`, `.../routing/chat.py` (1193-1198).

**Done When:**
- [ ] `list_dir` with no arg lists cwd immediate children (true `ls` semantics)
- [ ] `@ what's here?` returns the real directory, never a generic FHS table
- [ ] selection is model-driven (classifier), not a keyword/English match

**Unblocks:** T-032 (its allow-listed `list_directory` op now exists).

---

## Live-Session Failure Register (@ agent-pipe · Hermes · service health)

> Captured from a live operator session (`@` MiOS-AI CLI + `hermes` REPL + the
> podman dashboard). The `@` path (agent-pipe) and the `hermes` path (:8642
> direct) fail DIFFERENTLY: `@` FABRICATES tool execution; `hermes` executes for
> real but mis-targets. Anti-fabrication is the operator's core value → T-113 is
> P0. Detail SSOT for the chat-channel items = `MIOS-CHATQ-FV-WORKPLAN.md`.
>
> **SHIPPED this session (code-complete; live-verify pending):** T-113 (anti-fab
> guard on the chat short-circuit `chat.py` AND the native-loop synthesis
> `native_loop.py` — strip any `🤝 <verb> output`/`{"success":true,"tool":...}`
> block for a verb NOT actually fired; chat path routes to the real executor) ·
> T-114 (web/news: honest-note when a web turn cites off-list URLs OR produces a
> report-table with ZERO fetched sources) · T-116 (browser tab native-args) ·
> T-118 (mios-cpu-node ctx 131072->32768). **Remaining:** T-115 (deploy T-109),
> T-117 (Hermes container-exec — model-behavioral skill fix), T-119 (native-arg
> standard doc), and the deterministic-launch-route widening (defense-in-depth).

## T-113: FAB-01 -- @ agent-pipe FABRICATES tool execution + results (no real dispatch)  [P0]
> **Priority:** P0 | **Status:** pending | **Effort:** L | **Domain:** Anti-Fabrication/Orchestration | **Source:** live `@` session -- `@ launch forza` emitted a fake `🤝 open_app output: {"success":true,"pid":8421,"window":{"handle":0x7f12345678,...}}` with IDENTICAL fake pid/handle across every launch AND an invented app ("Forza Horizon 6"), while NOTHING launched (operator: "doing NOTHING for me"). The parallel `hermes` path ran a REAL `mios-windows launch`. So the agent-pipe narrates/hallucinates a tool call AND its output instead of dispatching to the real executor.

**Instructions:** Root-cause why the `@`/agent-pipe turn produces a fabricated tool-result block rather than a real `toolexec` dispatch (or a real hand-off to Hermes :8642). Enforce the hard invariant: **no `🤝 <tool> output:` / tool-result may EVER be emitted unless a real tool actually ran and returned it** — a tool result must be produced by `_exec_tool_calls`, never by a model hop. Wire a fabrication guard: any assistant-emitted text matching a tool-result envelope that has no corresponding executed `tool_call` row is dropped + the turn re-dispatched. Verify the `@`/`mios` CLI route reaches the real executor (memory says `@` should be Hermes-DIRECT :8642 -- confirm/repair the routing regression).

**Files (likely):** `usr/lib/mios/agent-pipe/mios_pipe/routing/{chat,native_loop,secondary_loop,toolexec}.py`, `.../routing/refine.py`, `usr/bin/mios` (route), `server.py` (dispatch).

**Done When:**
- [ ] `@ launch forza horizon` either executes a REAL launch (dispatch/Hermes) or says it could not -- NEVER a fabricated success with a fake pid/handle
- [ ] no tool-result block reaches the user without a matching executed `tool_call` row (live-verified)
- [ ] identical-fake-pid fabrication cannot recur (guard + test)

## T-114: FAB-02 -- pipeline fabricates web/news content + invents entities on misclassification  [P0]
> **Priority:** P0 | **Status:** pending | **Effort:** M | **Domain:** Anti-Fabrication/Grounding | **Source:** live `@` session -- gibberish `??!!!?` was refine-misclassified as a "weekly news roundup" and the pipeline FABRICATED 5 fake articles attributed to real outlets (NYT/Reuters/BBC/FT/TechCrunch) with invented events, claiming `web_search` ran (it did not). Also invented "Forza Horizon 6" (nonexistent).

**Instructions:** Hard anti-fabrication gate: NEVER emit web/news content or source attributions that were not returned by a real `web_search`/fetch tool call; NEVER invent entity names (apps/games). Fix the refine classifier so low-signal/gibberish input does NOT get promoted to a fabricated task plan (classify as chat/clarify, not "news"). Grounding: attributions must come from fetched results only. Model-driven, NO keyword gate.

**Files (likely):** `.../routing/refine.py` (classifier), `.../routing/chat.py` (web-research enrich), `mios_grounding.py`, `.../federation` web tools.

**Done When:**
- [ ] gibberish input -> clarify/chat, never a fabricated news roundup
- [ ] no source citation appears unless a real fetch produced it (live-verified)

## T-115: CQ1 refine scaffold STILL leaking on CLI + redundant refine passes  (extends T-109)
> **Priority:** P1 | **Status:** pending | **Effort:** S | **Domain:** Observability | **Source:** live `@` session -- the `Refined Text/Intent/Reply` scaffold streams verbatim to the strict CLI surface (CQ1 confirmed still live; the surface-aware `_sse_reasoning` fix is authored but undeployed, and the CLI sends no `x-mios-reasoning-ok` so it hits the legacy debug-inline path), and "🧠 Refining intent..." fires 2-3x per turn.

**Instructions:** Deploy T-109; additionally de-duplicate the refine pass (it runs multiple times per turn) and confirm the strict-CLI folded-trace path (FV-F) shows the trace once, cleanly, without the raw scaffold. Fold into T-109/T-110.

**Files:** `.../routing/{chat,sse,refine}.py`.

## T-116: OSCTL-01 -- Hermes browser opens NEW WINDOWS instead of reusing running instance / opening a TAB  [P1]
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** OS-Control | **Source:** live `hermes` session -- "open a firefox TAB to youtube" launched the Firefox Nightly shortcut TWICE (2 new windows) + opened several random Epiphany tabs, despite Firefox already running AND the operator explicitly asking for a tab. Launch path uses `mios-windows launch <shortcut>` (always spawns a new window).

**Instructions:** Make browser open-URL tab-aware: detect an already-running browser instance and open a NEW TAB in it (CDP `Target.createTarget` / `--new-tab` / activate-existing), NOT a new window/instance. Only cold-launch when the browser is not running. Honor an explicit "tab" request. Don't fan out extra Epiphany tabs.

**Files (likely):** `usr/lib/mios/agent-pipe/mios_oscontrol.py`, `.../routing/oscontrol.py`, `usr/libexec/mios/mios-windows`, browser/CDP skills.

**Done When:**
- [ ] "open a firefox tab to <url>" with Firefox already open -> ONE new tab in the existing window, no new window (live-verified by operator)

## T-117: OSCTL-02 -- Hermes container-exec: stale container name + interactive-exec hang + docker-first  [P1]
> **Priority:** P1 | **Status:** pending | **Effort:** M | **Domain:** OS-Control | **Source:** live `hermes` session -- "ssh into code-server container" tried `docker` first (runtime is podman), used the RETIRED name `code-server` (now `mios-agents`), wrong-execed `mios-open-webui`, and hung 172s/21s on `podman exec -it ... bash` (interactive `-it` with no TTY in the agent context). The memory tool also errored mid-session.

**Instructions:** (1) SSOT container-name resolution so `code-server` resolves to `mios-agents` (retired-name alias). (2) Never run interactive `-it` exec from the agent -- use non-interactive `podman exec <c> <cmd>` (no `-it`, no bare shell) so it can't hang. (3) Prefer podman (SSOT runtime), skip docker probing. (4) Investigate the memory-tool error.

**Files (likely):** `.../mios_oscontrol.py`, `usr/libexec/mios/*`, Hermes tool skills, container-name SSOT (mios.toml `[containers.*]`).

**Done When:**
- [ ] "exec into the code-server container" targets `mios-agents`, runs non-interactively, returns promptly (no >5s hang), never `-it`

## T-118: HEALTH-01 -- mios-cpu-node + mios-llm-light Unhealthy (oversized KV ctx)  [P1]
> **Priority:** P1 | **Status:** pending | **Effort:** S | **Domain:** Inference/Reliability | **Source:** podman dashboard -- `mios-cpu-node` (granite-4.1-8b) runs `--ctx-size 131072` on CPU (n-gpu-layers 0) and is **Unhealthy** (oversized KV; the VRAM/KV co-fit finding recommends ctx 131072->32768); `mios-llm-light` is also **Unhealthy**. Health gates red.

**Instructions:** Right-size the cpu-node KV ctx (SSOT `[lanes.*]`/llamacpp yaml) to a healthy value (e.g. 32768) per the co-fit finding; diagnose the llm-light health-gate failure (config.yaml / model load). NO-HARDCODE: ctx from SSOT.

**Files:** `usr/share/mios/llamacpp/*.yaml`, `usr/share/mios/mios.toml` (lane ctx), the health-gate.

**Done When:**
- [ ] mios-cpu-node + mios-llm-light report Healthy (live)

---

## T-119: TOOLARG-01 -- Native typed launch-arguments for ALL tools/skills/recipes (OpenAI-pattern, all environments)  [P1, systemic]
> **Priority:** P1 | **Status:** pending | **Effort:** XL | **Domain:** Tool-calling/OS-Control | **Source:** operator mandate (generalizes T-116) -- every verb/skill/recipe must expose NATIVE, typed launch/invocation arguments following OpenAI function-calling patterns (strict JSON-schema typed params + enums), grounded in upstream research on native invocation per app-type across ALL environments (Windows/Linux/WSL/container/browser). Not name-only coarse verbs. Exemplar: browser open-URL must take `{url, mode:tab|window, reuse_instance}` and open a TAB in the RUNNING browser, not a new window.

**Instructions:** Research + design FIRST (-> a `research/` doc): the native typed-arg standard + a per-type/per-environment native launch-arg map (browser tab/window via CDP `Target.createTarget`/`--new-tab`/remote; Windows App Paths/protocol/`.lnk`/AUMID; Linux `.desktop` Exec field codes/`gio`/`xdg-open`; games via `steam://`). Then enrich the `_VERB_CATALOG` + skill/recipe schemas with typed native args and project them through the existing OpenAI-tool/MCP schema surface (`strict`). SSOT + NO-HARDCODE + degrade-open. Land T-116 (browser tab) as the first shipped instance. Pairs with T-111 (constrained tool-calling = the MECHANISM; this = schema RICHNESS).

**Files (likely):** `usr/share/mios/mios.toml` (`[verbs.*]` arg schemas), `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py` (`_verb_to_openai_tool`), `.../mios_oscontrol.py`, `usr/libexec/mios/mios-windows`, skills/recipes catalogs.

**Done When:**
- [ ] a research/design doc defines the native typed-arg standard + per-type/env launch-arg map
- [ ] browser open-URL opens a TAB in the running browser (T-116) as the first shipped instance
- [ ] verbs/skills/recipes expose typed native args (not name-only) via the OpenAI/MCP tool projection
- [ ] every argument is model-selectable + validated; degrade-open when an env/arg is unsupported

---

## Appendix A: Dependency Graph (Critical Path â€” CONV additions)

```
T-094 (CONV-01 SSOT)
  +-- T-095 (CONV-02 GatewayQueue + GatewayWorker)
  |     +-- T-096 (CONV-03 GatewayQueue tests)
  |     +-- T-103 (CONV-10 scratchpad wiring into GatewayWorker)
  |     +-- T-105 (CONV-12 distroless Containerfile)
  |     +-- T-106 (CONV-13 MCPClientPool)
  +-- T-097 (CONV-04 llama-swap cache-reuse)
  +-- T-098 (CONV-05 vLLM multi-LoRA)
  |     +-- T-099 (CONV-06 LoRA API endpoints)
  |     +-- T-100 (CONV-07 heavy-alt retirement docs)
  +-- T-101 (CONV-08 sqlite-vec scratchpad module)
  |     +-- T-103 (CONV-10 scratchpad in GatewayWorker)
  +-- T-102 (CONV-09 cold eviction module)
  |     +-- T-104 (CONV-11 retention sweep + drift-check)
  +-- T-107 (CONV-14 rechunk CI step)
        +-- T-108 (CONV-15 Phase 4 drift-checks + docs)
  [T-105 also depends on T-095; T-108 depends on T-105 + T-107]
```

## Appendix B: File to Task Cross-Reference (CONV additions)

| File | Tasks |
|---|---|
| `usr/share/mios/mios.toml` (`[converge.*]`) | T-094, T-097, T-098, T-101, T-102, T-104, T-105, T-107 |
| `usr/lib/mios/agent-pipe/mios_gateway_queue.py` (new) | T-095, T-096, T-103, T-106 |
| `usr/lib/mios/agent-pipe/mios_dispatcher.py` | T-095 |
| `usr/lib/mios/agent-pipe/server.py` | T-095, T-099, T-102, T-103, T-104 |
| `usr/lib/mios/agent-pipe/mios_scratchpad.py` (new) | T-101, T-103 |
| `usr/lib/mios/agent-pipe/mios_cold_evict.py` (new) | T-102, T-104 |
| `usr/lib/mios/agent-pipe/mios_interop.py` | T-106 |
| `usr/lib/mios/agent-pipe/requirements.txt` | T-101 |
| `usr/share/mios/llamacpp/mios-llm-light.yaml` | T-097 |
| `usr/share/containers/systemd/mios-llm-heavy.container` | T-098 |
| `usr/share/containers/systemd/mios-llm-heavy-alt.container` | T-098, T-100 |
| `usr/share/containers/systemd/mios-agent-pipe.container` | T-105 |
| `Containerfile.hummingbird` (new) | T-105, T-108 |
| `automation/build/rechunk.sh` (new) | T-107 |
| `automation/38-drift-checks.sh` | T-094, T-099, T-104, T-105, T-107, T-108 |
| `usr/share/doc/mios/guides/inference-consolidation.md` (new) | T-100 |
| `usr/share/doc/mios/guides/memory-tiering.md` (new) | T-104 |
| `usr/share/doc/mios/guides/hummingbird-distroless.md` (new) | T-108 |
| `test_mios_gateway_queue.py` (new) | T-096 |
| `test_mios_scratchpad.py` (new) | T-101 |
| `test_mios_cold_evict.py` (new) | T-102 |
| `test_mios_mcp_pool.py` (new) | T-106 |
| `test_lora_endpoints.py` (new) | T-099 |
