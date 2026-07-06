# MiOS Master Unified Roadmap (2026-06-22)

This document is the lossless consolidation of all historical and active MiOS roadmaps, bridging the immutable bootc/OCI Fedora workstation with the local agentic AIOS plane.

## Table of Contents
- [Part 1: Next-Gen OS & Observability Research Integration](#part-1-next-gen-os--observability-research-integration)
- [Part 2: MIOS-ROADMAP-2026-06-22.md](#part-2-mios-roadmap-2026-06-22md)
- [Part 3: agentos-roadmap.md](#part-3-agentos-roadmapmd)
- [Part 4: agentic-standards-roadmap.md](#part-4-agentic-standards-roadmapmd)
- [Part 5: aios-full-control-roadmap.md](#part-5-aios-full-control-roadmapmd)
- [Part 6: aios-completion-roadmap.md](#part-6-aios-completion-roadmapmd)
- [Part 7: Architectural Gap-Fill (2026-06-24)](#part-7-architectural-gap-fill-2026-06-24)
- [Part 8: Hermes Sovereignty Migration (2026-06-24)](#part-8-hermes-sovereignty-migration-2026-06-24)
- [Part 9: XDG + CephFS Unified User Storage Fabric (2026-06-25)](#part-9-xdg--cephfs-unified-user-storage-fabric-2026-06-25)
- [Part 10: Converged-Resource Architecture — AI Pipeline Simplification (2026-06-25)](#part-10-converged-resource-architecture--ai-pipeline-simplification-2026-06-25)
- [Part 11: Windows-11-Minimal Install Completeness + NO-HARDCODE Sweep (2026-07-04)](#part-11-windows-11-minimal-install-completeness--no-hardcode-sweep-2026-07-04)
- [Part 12: MiOS Custom Windows Editions — UUP + NTLite/DISM + autounattend ISO Program (2026-07-04)](#part-12-mios-custom-windows-editions--uup--ntlitedism--autounattend-iso-program-2026-07-04)

---


# Part 1: Next-Gen OS & Observability Research Integration
*Source: 2026 Enterprise AIOS, Bootc, and Podman Architecture convergence.*

## 1. AIOS Observability & Telemetry (OTel GenAI)
- **What:** Integrate OpenTelemetry (OTel) GenAI semantic conventions to trace internal reasoning loops, tool invocations, and context drift.
- **Why:** Traditional system logs are insufficient for autonomous agents. Tracing the step-by-step reasoning and semantic tool routing provides mission-critical observability into agent "intent".

## 2. Bootc Auto-Rollbacks & Health Checks (greenboot)
- **What:** Implement `greenboot` scripts for systemd health validation.
- **Why:** If `mios-agent-pipe` or the primary inference lane fails to start after a `bootc upgrade`, the system must automatically detect the failure and roll back to the previous immutable OCI image to guarantee 100% workstation uptime.

## 3. OpenSCAP Image Compliance (oscap-im)
- **What:** Bake `oscap-im` (OpenSCAP for Image Mode) directly into the `Containerfile`.
- **Why:** Enforces declarative security policies during the OCI build step. The build process must fail if high-severity CVEs or misconfigurations are present in the bootable image.

## 4. Cryptographic Rootfs (composefs)
- **What:** Enforce `composefs` verification via `/usr/lib/ostree/prepare-root.conf`.
- **Why:** Combines overlayfs, EROFS, and fs-verity to guarantee that the read-only OS tree is cryptographically verified before userspace boots.

## 5. Podman Quadlet Auto-Generation
- **What:** Enhance the Quadlet generation script to fully parse `mios.toml` and emit `.container`, `.network`, and `.volume` units automatically at build time.
- **Why:** Eliminates manual drift between the TOML SSOT and deployed Podman sidecars, ensuring the immutable image boots exactly what is declared.

---


# Part 2: MIOS-ROADMAP-2026-06-22.md

<!-- AI-hint: The canonical MiOS roadmap (2026-06-22). Synthesizes four adversarial research workflows (OWUI location, AIOS+multi-agent+pod audit, pod consolidation, agent-template) + a live fix session into pick-up-able tasks for any IDE agent. Each task: id, priority, files, what/why, acceptance criteria, deps. Includes an honest claim-vs-reality register (trust the engineering-blueprint, not the triumphant MEMORY.md).
     AI-related: ./e2e-test-matrix-2026-06-21.md, ./install-robustness-2026-06-21.md, ../mios.toml, ../../../lib/mios/agent-pipe/server.py, ../../../../tools/generate-pod-quadlets.py, ../../../../automation/38-drift-checks.sh -->
# MiOS Roadmap — 2026-06-22

## How this was built + how to use it

Built from **four adversarial research workflows** + a live fix session, all verified
against the **running** dev VM (`podman-MiOS-DEV`), not the docs:

1. OWUI user-location delivery → MiOS AI
2. AIOS + multi-agent + container→pod **claim-vs-reality audit**
3. Pod consolidation architecture
4. Unified `[agents.*]` template + proper opencode fix + remote-node model

**Honesty note (read first).** Prior `MEMORY.md` entries over-claimed: "DONE/CLOSED/
31-of-32" was used for work that is **built + wired + unit-tested but flag-gated OFF,
empirically never-fired, or introspection-only**. The repo's own
`usr/share/doc/mios/concepts/engineering-blueprint*` is the honest artifact — **trust
it over `MEMORY.md`**. The container→pod "lie" accusation was investigated: the
`mios-webtools` pod is genuinely real (SSOT-generated, drift-gated) — **not a lie** —
but the broader "collapse everything into pods" never happened, and **WS-0B port
collapse** and **"opencode as a real council peer DONE"** were stated as done and are
not. Each task below carries a *claim-vs-reality* line where relevant.

**To pick up a task:** check its `Deps:` are met → make the change in the listed
`Files:` → meet **every** `Accept:` criterion → verify live → commit to `main`. Deep
evidence for each workstream lives in the session research outputs (cited per WS).

**Legend** — Priority **P0** blocker · **P1** high · **P2** med · **P3** polish.
Gates: 🖥️ operator-VM/bare-metal · 🔌 needs egress · ✅ done this session.

---

## ✅ Already done this session (do NOT redo)

- **OWUI login**: schema-adaptive admin INSERT (OWUI 0.9.6 dropped `user.api_key`) + **SSOT password** (`[identity].default_password`) reconciled every boot. Login proven.
- **87-verb e2e fixes** — see `usr/share/mios/docs/e2e-test-matrix-2026-06-21.md`: window verbs (executor health-gate), `cu_ground` vision shim, `mios-llm-heavy-alt` Delegate, `os_recipe` HITL granularity, `memory_update` rowcount, `sys_env` timeout, firecrawl `:6379` false-gate, `container_restart` Quadlet-aware, `system_logs` truncation, `service_restart` poll, `everything_search` envelope, `tool_choice` downgrade, `plocate`, **`knowledge_search` broker auth** (api_key export + API listing).
- **Install reproducibility**: non-admin log path, version-pinning, in-WSL clone fetch-retry.
- **Location grounding**: removed the timezone→city fabrication (3 sites); OWUI-native `{{USER_LOCATION}}` model row applied (→ **WS-E1** to persist + operator secure-context test).
- **Multi-agent**: `opencode` `health_gate=true` **band-aid** (verified: fan-out 0→4435 chars). Superseded by **WS-A1/A2/A3**.

---

## WS-A — Multi-agent / orchestrator (the agent system)
*Source: audit `wbkbuti2o`, agent-template `wuy193d96`. Files: `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`, `usr/libexec/mios/opencode-gateway/server.py`, `automation/38-drift-checks.sh`.*

### A1 — Unified `[agents.*]` template + `_defaults` inheritance + one merge path  **[P1]**
*Claim-vs-reality:* agent config is ad-hoc — `hermes` declared `health_gate`, `opencode` didn't; the loader `_load_agent_registry` (server.py:3852) defaults `health_gate=False` (:3893) while the node-loader defaults it safely to `not _is_local` (:3993). That divergence **is** the `merged_chars=0` root cause.
- **What:** Add a `[agents._defaults]` block to vendor `mios.toml` (in-band, layered — NOT a separate file). Canonical schema with a `kind` discriminator (`local-http|remote-http|cli|mobile|edge|node|a2a`) + new fields `enabled`, `transport`, `timeout_s`, `sub_lane`, `api`, `vram_mb`, `ram_mb`, `tool_capable`, `auth{scheme,header_template,principal_mode}`, `trust{min_reputation,require_signed_principal,mtls}`. In `_load_agent_registry`: `base = agents.pop("_defaults", {})`; skip `_`-prefixed names; `effective = {**base, **cfg}`; **safe `health_gate` default** = `kind in {remote-http,cli,mobile,edge,node,a2a} OR not enabled OR _is_remote_endpoint(ep)`. Extract `_coerce_agent_cfg(name, effective)` shared by BOTH `_load_agent_registry` and `_load_node_pool`.
- **Files:** `usr/share/mios/mios.toml` (`[agents._defaults]` + rewrite each `[agents.*]` as thin overrides), `usr/lib/mios/agent-pipe/server.py` (~3835-3995).
- **Accept:** absent `_defaults` → byte-identical behavior; with it, `opencode` resolves `health_gate=true`; `/v1/cluster/health` unchanged for live agents; a unit test loads a 1-field overlay agent and inherits the rest.
- **Deps:** none.

### A2 — Agent-schema validator (drift-check) — makes the bug unrepresentable  **[P1]**
- **What:** Add `check_agent_schema` to `automation/38-drift-checks.sh` (mirror `check_rbac_tiers`, python3+tomllib). For each `[agents.*]` (merge `_defaults`), FAIL on: (a) local+optional/cli agent missing `health_gate=true`; (b) `kind=cli` without `timeout_s`/`enabled`; (c) `kind=node` without `api`+`lane`; remote/edge/mobile without `health_gate=true`; (d) endpoint with a **bare `:PORT` literal** instead of `${MIOS_PORT_*}`; (e) ≠1 `default=true`; (f) unknown key (typo guard).
- **Files:** `automation/38-drift-checks.sh` (register in `main()` after `check_rbac_tiers`).
- **Accept:** `just drift-gate` fails when a test agent omits `health_gate`; passes on the cleaned config; runs in CI with no built image.
- **Deps:** A1.

### A3 — Proper opencode fix (make `:8633` return real output)  **[P1]**
*Claim-vs-reality:* "opencode as a real council peer DONE" is **FALSE** — gateway disabled/inactive, nothing on `:8633`, `opencode run` hangs (zero output). Root cause spotted: `opencode-gateway/server.py:171-173` calls `subprocess.run` with **no `stdin=` kwarg** (hangs waiting on a TTY/stdin) and the wrong output mode.
- **What:** Fix the gateway invocation: pass `stdin=subprocess.DEVNULL`, the correct headless flags (research the opencode CLI single-shot non-TUI: `opencode run -p`/`--print`/`--format`/`OPENCODE_*` env, or switch to `opencode serve` if it exposes an OpenAI server), and a fail-fast `timeout_s`. Then enable + start `mios-opencode-gateway.service`.
- **Files:** `usr/libexec/mios/opencode-gateway/server.py`, the gateway unit, `[agents.opencode]` (`enabled=true`, `fanout` once stable).
- **Accept:** `curl :8633/v1/chat/completions` returns a real completion (not a hang); `/v1/cluster/health` shows opencode `effective_up:true`; a code-routed fan-out merges real opencode output.
- **Deps:** A1. *Fallback:* if opencode truly can't run headless, document it and put a different coding agent on the lane.

### A4 — hermes-worker boot ordering (get ≥1 real council peer up)  **[P1]**
*Claim-vs-reality:* on the default VM **all 9 cluster agents `effective_up:false`** → orchestrator silently single-agent. `:8643` hermes-worker is `inactive`, `ConditionResult=no` (venv absent at boot) and never auto-restarts once the venv lands.
- **What:** Add `After=`/`Requires=` the venv-build unit, or a systemd `.path` watch on the hermes binary, so hermes-worker (re)starts once present.
- **Files:** `usr/lib/systemd/system/hermes-worker.service` (+ a `.path` unit), preset.
- **Accept:** after a fresh boot + venv build, hermes-worker is `active`; `/v1/cluster/health` shows ≥1 peer `effective_up:true`; a fan-out uses it.
- **Deps:** none.

### A5 — Council honesty: report single-agent mode  **[P2]**
- **What:** When no council peers are `effective_up`, the front door surfaces `"mode":"single-agent (no council peers up)"` in response/health metadata instead of advertising a council it silently degraded from.
- **Files:** `server.py` (the cluster-health / response-metadata path).
- **Accept:** with all peers down, `/v1/cluster/health` + a chat's metadata both say single-agent.
- **Deps:** none.

### A6 — Kernel Stage-2 hot-path migration  **[P2] 🖥️**
*Claim-vs-reality:* "kernel Stage-2a DONE" is **introspection-only** — `/v1/route` responds but `_kernel_stage2b` raises `NotImplementedError` for chat/dispatch/multi_task/agent; "live path never calls `dispatcher.run()`"; `shadow_route=False`. The LLM-as-CPU kernel does not execute.
- **What:** Migrate each mode's execution body out of `chat_completions` into dispatcher handlers behind `kernel_route`; VM-verify parity vs the shadow log before swapping.
- **Files:** `server.py` (kernel + dispatcher). **Deps:** operator VM loop.

---

## WS-B — AIOS governance (activate the inert)
*Source: audit `wbkbuti2o`. Most modules are TRUE-but-gated-OFF.*

### B1 — Flip the two SAFE gates ON by default  **[P2]**
*Claim-vs-reality:* memguard `off`, cost `enabled:false` — both observe/audit-only and zero-risk, but live system runs with neither.
- **What:** Default `[ai].memory_guard_mode="log"` (audit-only) + `[cost].enable=true` (observe-only).
- **Files:** `mios.toml`. **Accept:** `/v1/cost` shows `enabled:true`; memguard logs validations; no behavior regression. **Deps:** none. (SLO-shed + `kernel_route` need VM parity first — leave OFF.)

### B2 — Verify WS-MEM-TIER tiering loop end-to-end  **[P2] (data-safety)**
*Claim-vs-reality:* "tiering DONE" — live pg has **0 rows with `access_count>0`**, 0 hot. The outcome-ranked bump K-LRU eviction depends on has **never fired**; eviction (`evict_enable=true`) runs on all-zero counters.
- **What:** Run a live recall round-trip; re-check `access_count`. If still 0, verify the recall projection carries `id` and the `_PG_PRIMARY` page-in counter block is reached (`rid_to_pg_id`).
- **Files:** `server.py` (recall/tiering), `usr/libexec/mios/mios-pg-query`. **Accept:** after a recall, the row's `access_count` increments + a hot row appears. **Deps:** VM chat-loop.

### B3 — Self-improve ACT half  **[P3]**  ·  ### B4 — promptver consumer (hops resolve from registry)  **[P3]**  ·  ### B5 — A2A federation testable (loopback peer + smoke)  **[P3]**  ·  ### B6 — `expandvars` over `cpu_endpoint`/all `*_endpoint`  **[P3]**  ·  ### B7 — Multi-tenant RLS app-wiring (`SET LOCAL mios.owner_user`)  **[P3]**
*(See audit G8–G14 for specifics + line refs.)*

---

## WS-C — Pod consolidation + port minimization
*Source: pod-consolidation `wuj7tswip`. Mechanism EXISTS: `tools/generate-pod-quadlets.py` reads `[pods.*]` (today renders only `mios-webtools.pod`). This fills out the SSOT it already consumes. **Central constraint:** the AI brains (hermes-agent, agent-pipe, mcp, prefilter, opencode-gateway, hermes-browser, ttyd) are **host services, not containers** — podding them is a containerize-first project, out of scope; they stay host-native and pods attach via `host.containers.internal`.*

### C0 — code-server `:8080`→`:8800` remap (the unblocker — do FIRST, standalone)  **[P1]**
- **What:** `mios-code-server.container`: `Environment=BIND_ADDR=0.0.0.0:8800` **plus** an entrypoint arg override `--bind-addr 0.0.0.0:8800` (the image ENTRYPOINT wins over the env var), update the 3 `:8080` Labels + header to `:8800`. `[ports].code_server=8800` already matches.
- **Accept:** `ss -ltnp | grep 8800` binds, `:8080` free, editor reachable. **Deps:** none.

### C1 — Add the 7 `[pods.*]` blocks to `mios.toml`  **[P1]**
- **What:** Mirror `[pods.mios-webtools]`'s schema (`description/network/after/wants/wanted_by/members[]/doc`): `mios-ai-inference` (llm-light + cpu-node◇ + worker◇), `mios-ai-heavy`◇ (heavy + heavy-alt), `mios-ai-data` (pgvector), `mios-devforge` (forge + runner + code-server), `mios-netinfra-dns` (adguard), `mios-remote-desktop`◇ (guacamole stack). Keep `mios-webtools`. **Standalone:** OWUI (front door), searxng.
- **Files:** `mios.toml` `[pods.*]`. **Accept:** `generate-pod-quadlets.py --check` lists the 7 pods, no drift. **Deps:** C0.

### C2 — Set `Pod=` on members + render + validate each pod healthy  **[P1]**
- **What:** Add `Pod=<pod>.pod` to each member `.container`; run the generator; `daemon-reload`; verify every pod comes up.
- **Accept:** `podman pod ls` shows the pods Running; each member in its pod; all health checks green. **Deps:** C1.

### C3 — De-publish searxng `:8888`→loopback; drop heavy-alt stray `:11440` PublishPort  **[P2]**  ·  ### C4 — **WS-0B port collapse (still open)**: render `.container` `PublishPort` from `[ports]` SSOT at build time (generator/Containerfile sed → `MIOS_PORT_*` into install.env + EnvironmentFile)  **[P2]**  ·  ### C5 — add the pod-gen to a build render step (P6)  **[P3]**
*Port surface target: ~24 raw host binds → ~8 deliberate front doors (`53,3053,3000,49922,8800,3030,8640,8642` + host sshd/cockpit).*

---

## WS-D — Remote / edge AI nodes (remote compute)
*Source: pod `wuj7tswip` §3 + agent-template `wuy193d96` §1d. **Uses the existing `[nodes.*]`/`[agents.*]` SSOT + health-gated swarm join — no new pod, no new published port.** agent-pipe dials **outbound**; this box publishes nothing new beyond `:8640`. Tailscale stays OFF (LAN uses WSL gateway 172.x).*

### D1 — Remote/edge agent template + auto-join  **[P2]**
- **What:** Land the `kind=remote-http|edge|node` template (A1) with `auth{scheme,header_template,principal_mode}` + `trust{min_reputation,require_signed_principal}`. Vendor ships `endpoint=""` (privacy); real tailnet endpoint goes in the `/etc/mios` overlay. `_load_node_pool` auto-joins when reachable, auto-drops when gone.
- **Files:** `mios.toml` (`[agents.pi-edge]` shape + `[nodes.*]`), `server.py` (`_load_node_pool`). **Accept:** a loopback "remote" node added to `/etc` overlay shows up in `/v1/cluster/health` and is dispatched-to when up, dropped when down. **Deps:** A1.

### D2 — Pi/edge join doc + minimal-port  **[P3]** — document the one-port (`:8640`) outbound-dial join flow; optional federated pgvector via `[pgvector].listen_loopback=false` (off by default, firewall-scoped).

---

## WS-E — OWUI integration
*Source: location `wbzod13uf`.*

### E1 — Persist the OWUI location fix (firstboot wiring)  **[P1]**
*Status:* the `MiOS AI` model row + `{{USER_LOCATION}}` system prompt is applied **live** but won't survive a rebuild/reinstall unless wired.
- **What:** Wire `mios-owui-apply-system-prompt` into the OWUI firstboot/`ExecStartPost` chain so the model row (with `{{USER_LOCATION}}`/`{{CURRENT_TIMEZONE}}`/`{{CURRENT_DATE}}`) is recreated on every fresh install. Optional hardening: set `Environment=MIOS_OWUI_DB=<host webui.db>` on `mios-agent-pipe.service` + grant `mios-ai` RO read on webui.db for the deterministic DB fallback.
- **Files:** `usr/lib/systemd/system/mios-open-webui-firstboot.*` (or the hermes-firstboot chain), `usr/lib/systemd/system/mios-agent-pipe.service`.
- **Accept:** after re-running firstboot on an empty model table, the `MiOS AI` row exists with `{{USER_LOCATION}}`. **Operator precondition (document prominently):** browser geolocation requires a **secure context** — OWUI over `https://…ts.net` or `http://localhost:3030`, NOT `http://<LAN-IP>` (silently blocked). **Deps:** none.

### E2 — strip a trailing `(lat, long)` suffix in `_client_env` (cosmetic)  **[P3]**  ·  ### E3 — fix the stale `agent.json` "SurrealDB-state chain" description (post-pgvector)  **[P3]**

---

## WS-F — Install / verb residual
*Source: `e2e-test-matrix-2026-06-21.md`.*

### F1 — Re-vectorize the OWUI "MiOS Documentation" knowledge collection  **[P2]**
*Status:* the 32 files are registered but NOT vectorized in ChromaDB → `knowledge_search` auth works but returns 0 hits. **What:** re-index the collection in OWUI (or via the retrieval API) so chunks exist. **Accept:** `knowledge_search "bootc"` returns hits.

### F2 — Build the coderun-sandbox image  **[P2] 🔌** (firstboot build failed "no egress"; rebuild with egress so `run_sandboxed_code` starts).  ·  ### F3 — host-side Code Mode `/run/coderun.sock` per-session broker  **[P3]**  ·  ### F4 — generated `mios build` driver curl-fallback; `move_window` named-region local actuator; `es.exe` version upgrade  **[P3]**

---

## WS-G — Honesty / docs reconciliation  **[P2]**
- **What:** Reconcile `MEMORY.md`'s triumphant framing with the honest `engineering-blueprint`: re-tag the over-claimed items (WS-0B, opencode-peer, kernel Stage-2, tiering, governance gates) as **built-but-gated/partial**, and trim the 59 KB index (it's over its 24 KB limit). Going forward: "DONE" requires **active + live-fired**, not "built + gated-OFF".
- **Files:** `~/.claude/.../MEMORY.md`, the relevant memory topic files.

---

## WS-FED — Open agent-agnostic federation (any agent on the net + credentials joins)
*Source: federation research `w6i3l8oco`. The principle (operator): **"network reachability + a verifiable, scoped credential" is the ONLY thing required to join the council** — `hermes-worker`, a remote OpenAI box, a Claude/Gemini/vLLM proxy, opencode, a second MiOS node are all the SAME `[agents.*]` registry row with a different `endpoint`+`auth`. MiOS already has the PUBLISH side (AgentCard, OASF, Ed25519 passport, `/a2a`, `/v1` front door, the `[agents._defaults]` template); what was missing is the JOIN contract (inbound auth, per-agent credential, self-describing card, live reload, LAN discovery). The three-layer contract: Interface (OpenAI `/v1` or A2A) · Capability (AgentCard `skills`) · Credential (OpenAPI `securitySchemes` + passport). All flag-gated + degrade-open.*

### FED-G2 — per-agent OUTBOUND credential ✅ DONE this session (`81b623d`)
`[agents._defaults].auth{scheme,header_template,principal_mode}` + `trust{}`; `_load_agent_registry` env-resolves `header_template` into `_AGENT_AUTH_BY_HOSTPORT`; `_apply_outbound_auth(hdrs,ep)` attaches the shared key for a local lane OR the agent's own header for a remote endpoint. **Follow-up (P1):** apply `_apply_outbound_auth` at the other 4 dispatch sites (server.py ~1873, 4699, 5829, 26208 — currently only the council/tool-loop site is wired) for full consistency.

### FED-G1 — inbound auth gate  **[P0 / operator-greenlight: changes the front-door auth posture]**
*Today `/v1/models`, `/v1/chat/completions`, `/a2a` return 200 + run inference with NO credential (live-verified); `:8640`/`:8642` bind `0.0.0.0`.* One ASGI `@app.middleware("http")` ahead of the usage shaper (server.py:26814) gating `/v1/*`+`/a2a`: accept `API_SERVER_KEY` OR a per-agent caller-key (`/etc/mios/ai/v1/caller-keys.json`) OR a `mios_principal` scoped token → scoped identity (`max_permission`+RBAC+reputation). Flag `[security].require_auth=false` default (degrade-open). Default listen=loopback; publish `0.0.0.0` only when auth ON + firewall-scoped to 172.16/12.

### FED-G3 — live membership reload  **[P1]** — mtime-watch (cron-director pattern) on `a2a-peers.json` + `mios.toml [agents.*]/[nodes.*]`, or an auth-gated `POST /a2a/peers/reload`; re-run `_a2a_load_peers` + drop `_WORKER_TOOLS_FULL_CACHE`. Removes "restart to add an agent."
### FED-G4 — self-describing + signed AgentCard  **[P1]** — `_build_agent_card` (server.py:19082) emits `securitySchemes`+`security`+`signatures[]` (JWS over RFC-8785-canonical card, Ed25519 passport key) from a `[a2a.security]` SSOT, so a discovering peer learns how to authenticate.
### FED-G5 — LAN-native discovery  **[HIGH]** — enable `avahi` (gated); publish `_mios-ai._tcp`/`_a2a._tcp` on :8640; browse + an OpenAI `/v1/models` probe fallback; CIDR sweep fallback. Tailscale stays OFF.
### FED-G6 — authenticated inbound delegation + least-privilege  **[HIGH]** — flip `[a2a].principal_mode` off→verify(audit)→enforce once peers keyed; map verified peer → scoped identity.
### FED-G7 — route on the published AgentCard skills (not just strengths)  **[MED]** · FED-G8 caller-key store (`mios_principal`+`crl`)  **[MED]** · FED-G9 loopback-default bind + scoped publish  **[MED]** · FED-G10 generic `/v1/models`-only endpoint join (cardless Claude/Gemini/vLLM)  **[LOW]** · FED-G11 `/v1/agents` registry surface  **[LOW]**.

### A4 resolved under WS-FED
`hermes-worker` = one `kind=local-http` row with `auth{}` + `health_gate=true` (auto-drop/rejoin already present); a remote Claude/Gemini/box is the **identical row** with a different `endpoint`+`auth`. Its boot-ordering (`.path`/`After=venv-build`) is now *just* a systemd detail, not a federation decision. **Council membership is never a per-agent decision again.**

### FED MVP (the first testable increment, mostly done)
"a second OpenAI endpoint on the LAN + a credential = a live council peer": **FED-G2 done** → next **FED-G1** (the loopback test: unauth `/v1/*` → 401; a `kind=remote-http` loopback peer with its own key shows `effective_up:true` + contributes fan-out). Then FED-G3 so the peer row itself adds without a restart.

---

## WS-H — Sovereign AIOS Architecture & Advanced Orchestration (Additive Research)
*Source: AIOS architectural gap synthesis vs Rutgers AIOS. Bridges the gap between user-space abstraction and bare-metal agentic OS.*

### H1 — Native MCP Standardization & Hermetic Sandboxing  **[P1] 🖥️**
- **What:** Standardize all tool executions on the Model Context Protocol (MCP). The `usr/libexec/mios/mcp-server-runner` binary acts as a strict gatekeeper validating tool contracts. Unpack and execute incoming `.mcpb` bundles strictly within lightweight, rootless containerized sandboxes (**Lima VM** or **Kata-on-Firecracker**).
- **Files:** `usr/libexec/mios/mcp-server-runner`
- **Accept:** File operations are confined to structured schemas (`glob`, `list_directory`, `read_file`) within the sandbox, preventing Zip Slip and directory traversal escapes to the host.

### H2 — Implement Token-Time Slicing in agent-pipe  **[P1]**
- **What:** Implement a Round-Robin or priority-based token-time slicing queue within the `agent-pipe` orchestrator (Port 8640). This intercepts and queues incoming LLM generation requests to mimic traditional CPU thread scheduling at the network socket layer.
- **Files:** `usr/lib/mios/agent-pipe/server.py`
- **Accept:** Prevents VRAM thrashing when multiple agents request inference turns simultaneously without relying solely on the inference engine's continuous batching.

### H3 — Deterministic Orchestration via Conductor  **[P2]**
- **What:** Transition from brittle, token-heavy probabilistic prompt chaining to deterministic, zero-token orchestration using the Microsoft Conductor CLI. Define execution workflows in structured YAML files with Jinja2 templates.
- **Accept:** Task concurrency is managed via parallel execution groups (`fail_fast`, `continue_on_error`) and deterministic loops, eliminating LLM-based routing failures.

### H4 — Transition to Hindsight Primary Memory Tier  **[P2]**
- **What:** Replace legacy MAIA v8.0 runtime pools with the MIT-licensed **Hindsight** memory engine running inside the isolated `mios-pgvector` container.
- **Accept:** Enables multi-strategy parallel retrieval (semantic vector, BM25 keyword, graph relational, temporal) to solve retrieval latency and context bloat.

### H5 — Cryptographic State Validation Chains  **[P2]**
- **What:** Secure the multi-agent event bus by cryptographically chaining all agent state shifts and deliberations using SHA-256 hashing.
- **Accept:** Event logs written to `/var/lib/agents/` are tamper-evident, ensuring full auditability and mitigating context drift or injection mutations.

### H6 — Federated Query & Data Routing (LAKE)  **[P3]**
- **What:** Integrate the Learning-assisted Accelerated Kernel (LAKE) utilizing Spice.ai's open-source Rust engine to optimize high-throughput scheduling and dynamic data routing for inference queues.

### H7 — Harden Immutable Image with Native fapolicyd Policies  **[P1] 🖥️**
- **What:** Bake restrictive `fapolicyd` configurations (known-libs allow-list, `allow perm=any uid=0 trust=1 : all`) directly into the core `bootc` image during the OCI build cycle.
- **Accept:** Eliminates zero-day root execution loopholes before the image is distributed via self-replication.

---

## Quick-reference priority order
**P0:** FED-G1 (operator-greenlight). **P1:** A1✅→A2✅→A3✅, FED-G2✅(+4-site follow-up), FED-G3, FED-G4, A4, C0→C1→C2, E1, H1, H2, H7. **P2:** A5, B1, B2, C3, C4, D1, F1, G, FED-G6/G7/G8/G9, H3, H4, H5. **P3:** the rest (including H6).

*Research evidence (this session's task outputs): location `wbzod13uf`, audit `wbkbuti2o`, pods `wuj7tswip`, agents `wuy193d96`, federation `w6i3l8oco`, AIOS architectural synthesis.*


# Part 3: agentos-roadmap.md

<!-- AI-hint: Roadmap for evolving the MiOS agent stack toward the 2025-2026 AgentOS/AIOS reference architecture, identifying specific technical gaps (DAG decomposition, deliberative loops, event buses) and the phased engineering plan that resolves them; several phases have landed. Read to understand how the agent plane fits the whole MiOS system.
     AI-related: mios-agent-pipe, hermes-agent, mios-launcher, mios-pc-control, mios-windows, mios-daemon, mios-llm-light, mios-llm-heavy, mios-pgvector, mios-skills, mios-skills-miner, mios-passport, mios-text-edit, mios-powershell -->
# MiOS AgentOS Roadmap

## Purpose & place in the whole system

MiOS is one thing built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image — boot it, `bootc
upgrade` it like a `git pull`, roll it back like a Ctrl-Z) that is *also* a
**local, self-replicating, agentic AI operating system**. The build pipeline
assembles the image, the bootc lifecycle carries it forward, and the same image
that ships GNOME/Wayland, GPU-via-CDI, KVM/libvirt and a k3s+Ceph cluster path
*also* ships a full local agent stack behind one OpenAI-compatible endpoint.

This document is the architectural roadmap for the **agentic** half of that
system — how the MiOS agent stack evolves toward the 2025-2026 AIOS / AgentOS
reference architecture. It is written for engineers extending the agent plane.
Its job is to connect that plane to the rest of MiOS: a front-end request flows
into the **agent-pipe** orchestrator (`:8640`), which refines/decomposes it,
fans it out across a council/swarm, and dispatches typed tool/verb calls;
**MiOS-Hermes** (`:8642`) is the OpenAI-compatible gateway and tool-loop agent;
the **inference lanes** (`mios-llm-light` `:11450`, the heavy GPU lanes
`mios-llm-heavy`/`mios-llm-heavy-alt`) do generation and embeddings; and
**PostgreSQL + pgvector** (`mios-pgvector` `:5432`) is the unified agent memory.
MCP exposes the tool surface; A2A federates peer agents. Phases below are
ordered by operator-impact-per-line-of-code, not by formal completeness.

> **Migration note (2026-06-13):** The agent plane has moved off the early
> Ollama / SurrealDB / Qdrant stack. Inference + embeddings now run on
> `mios-llm-light` (`:11450`, llama.cpp behind the upstream `mios-llm-light` proxy);
> the unified datastore is PostgreSQL + pgvector. Ollama survives only as an
> *upstream API-compat reference* (the lanes speak the OpenAI/Ollama-compatible
> API). Several phases below are **landed** — those sections describe shipped
> code and are kept as the design-of-record; the still-open phases describe
> planned work.

## Current state

| AgentOS principle | MiOS implementation | Gap |
|---|---|---|
| Tripartite layer (App/SDK/Kernel) | OWUI -> mios-agent-pipe (:8640) -> hermes-agent (:8642) | No formal SDK boundary; mios-agent-pipe IS the SDK in practice |
| MCP-style tool execution | mios-launcher broker (CAPTURE_JSON), typed verbs, LiteCUA via mios-pc-control + mios-windows | Strongest piece in MiOS |
| Multi-frontend through one chain | OWUI shipped; Discord shipped; Slack/Telegram pending | Works (OWUI + Discord) |
| Shared cross-cutting state | PostgreSQL + pgvector: agent_memory / session / tool_call / event / skill / scratch / knowledge / kanban / agent_metric | Works |
| Local memory (per-agent) | hermes/.hermes/*.db, mios-daemon state, OWUI webui.db | Works |
| Primary inference + embeddings | mios-llm-light at :11450 (llama.cpp via mios-llm-light); serves everyday models + `nomic-embed-text` embeddings + the `mios-opencode` coder model | Live |
| Heavy GPU lanes | mios-llm-heavy (SGLang, :11441, served-name `mios-heavy`) / mios-llm-heavy-alt (vLLM) | Gated/off-by-default (VRAM) |
| Query decomposition into DAG | `decompose` router action runs nodes topologically | **landed (Phase A.1)** |
| Deliberative Collective Intelligence | single-pass critic loop, informal | **GAP B** |
| Document-mutation event bus | hermes-tail/*.json + nudges (polled) | **GAP C** (no inotify pub/sub) |
| Personal Knowledge Graph | `person` table in pgvector; flat OWUI memory | **GAP D** (no rich graph edges) |
| Sequential Pattern Mining | mios-skills miner over tool_call history | **landed (Phase C.2)** |
| Taint-aware memory + Semantic Firewall | `tainted` tagging + pre-dispatch firewall on WRITE-class verbs | **landed (Phase A.3 / B.3)** |
| Agent Passports / crypto identity | Ed25519 passports via mios-passport; signed envelopes on writes | **landed (Phase C.3)** |

Operator-observed failures the open/closed gaps addressed:
- "open notepad and type hello and save to documents" -- monolithic
  handling; Hermes tried random paths because no DAG split into
  open_app -> focus -> type -> save chain (Phase A.1)
- "Hermes claimed it launched but didn't" -- single-pass critic
  didn't FALSIFY the success claim (GAP B, still open)
- daemon polling 3 sideband JSONs at 5-min ticks vs reacting
  on-mutation (GAP C, still open)

## Phase A -- foundational gaps (commit 1-3)

### A.1 -- DAG query decomposition via orchestrator-subagent  *(landed)*

**Reference**: Anthropic's multi-agent research system pattern --
NOT DeepSieve verbatim (DeepSieve needs DeepSeek-V3-scale planner;
the local-stack decomposer is a small function-calling-tuned model).
~300 LoC in `mios-agent-pipe`, no new heavy deps.

**Shape**:
- New router action: `decompose`. Returns:
  ```
  {"action": "decompose",
   "nodes": [
     {"id": "n1", "tool": "open_app", "args": {"name": "notepad"}, "deps": []},
     {"id": "n2", "tool": "focus_window", "args": {"title": "Notepad"}, "deps": ["n1"]},
     {"id": "n3", "tool": "pc_type", "args": {"text": "hello"}, "deps": ["n2"]},
     {"id": "n4", "tool": "pc_key", "args": {"keys": "ctrl+s"}, "deps": ["n3"]}
   ]}
  ```
- agent-pipe runs nodes topologically; failures retry up to 2x
  (reflexion cap) before pruning + asking operator.
- Each node emits a pgvector `tool_call` row tagged with the DAG id
  + parent edges -- gives a full audit trail for multi-step intents.

**Decomposer model**: resolved through the lane router (`MIOS_AI_ENDPOINT`,
Law 5) to a function-calling-capable model served by `mios-llm-light`, not the
smallest micro-LLM (too small for reliable multi-hop per community reports).

### A.2 -- inotify-backed document-mutation event bus

Replace the 3 separate poll loops in mios-daemon (hermes-tail,
delegation-prefilter, log-watcher) with one inotify watcher on
`/var/lib/mios/*/` directories. Hooks emit pgvector `event` rows.
Agents (mios-daemon, agent-pipe critic, future Kanban dispatcher)
`SELECT FROM event WHERE source = X AND ts > <last_seen>`.

### A.3 -- Taint-aware memory tags  *(landed)*

When agent-pipe's broker dispatch returns a tool_call result whose
source is untrusted (e.g. web fetch, RAG document, external API
response), tag the result content with `tainted = true` before it
enters the chain's context. A pre-execution check in the
Semantic Firewall (Phase B.3) refuses high-privilege follow-up
verbs (service_restart, container_restart, open_url to non-allow-
listed domain) if any tainted content is in context.

## Phase B -- deliberation upgrade (commit 4-6)

### B.1 -- DCI 14-act vocabulary as structured output

Define the typed-acts schema (14 acts: frame/clarify/reframe,
propose/extend/spawn, ask/challenge, bridge/synthesize/recall,
ground/update, recommend). Each agent reply in deliberation MUST
emit JSON with an `act` field. Lets us tag the pgvector `event` row
with the act type + run analytics on which act fired before resolution.

### B.2 -- DCI-CF convergent flow critic (replaces single-pass)

4 personas on hermes-agent (Framer / Explorer /
Challenger / Integrator). Bounded loop: R_max=3 rounds, K_max=4
candidate finalists. Always emits a decision packet {choice,
rationale, minority_report, reopen_triggers}. Tensions preserved
as first-class objects in pgvector `event(kind="dissent")`.

Single-model role-playing works per the DCI paper (one capable model,
4 differentiated system prompts). Diversity helps but isn't required —
the personas can all be served by `mios-llm-light` via distinct prompts.

### B.3 -- Semantic Firewall pre-MCP-dispatch  *(landed)*

Small Python layer in agent-pipe. Before any WRITE-class verb
fires, check:
- Operator's original DAG (from A.1) authorized this verb
- No tainted content (from A.3) in agent context
- Action target is consistent with the DAG node's `args`
On violation: abort + emit pgvector `event(kind="firewall_block",
severity="high")` + surface to operator.

## Phase C -- long-horizon autonomy (commit 7+)

### C.1 -- Personal Knowledge Graph

The pgvector schema already seeds a `person` table for per-operator
grounding. The next step is rich graph edges: `pref`, `device`,
`app_install` rows + relationship columns/joins so the router/refine
pass can ground ambiguous terms ("my browser" -> preference ->
chromedev). PostgreSQL joins + JSONB carry the edges; semantic recall
rides the existing `vector(768)` HNSW columns.

### C.2 -- Sequential Pattern Mining over tool_call history  *(landed)*

Implemented as:

* `usr/share/mios/postgres/schema-init.sql` -- tables:
  `skill` (catalog row, param-templated body), `skill_invocation`
  (per-run audit), `event`/`tool_call` (the mined source), and the
  composition edges expressed as JSONB/relations. The miner
  subtracts already-codified runs so it doesn't re-mine its own
  skills.
* `usr/libexec/mios/mios-skills` -- stdlib-only CLI:
  `mine / list / show / run / promote / retire / delete /
  import / export / openai-tools / export-catalog`. The miner
  enumerates contiguous N-grams of (verb, args-shape) over
  session-bucketed tool_calls, counts support + unique-session
  witness, auto-promotes when confidence crosses the SSOT-driven
  `auto_promote_threshold`.
* `usr/lib/mios/agent-pipe/server.py` -- endpoints:
  `GET /skills/list`, `GET /skills/show`, `POST /skills/run`,
  `GET /skills/openai-tools`. `execute_skill()` routes every step
  through `dispatch_mios_verb()` so the Phase B.3 firewall +
  Phase A.3 taint chain + audit-row writes apply identically to
  direct verb dispatch.
* `usr/lib/systemd/system/mios-skills-miner.{service,timer}` --
  cadence-driven background miner; ExecStartPost also runs
  `mios-skills export-catalog` so offline agents see fresh
  catalog.json without polling agent-pipe HTTP.
* Cross-agent surfaces (every external agent reads from at least
  one of these):
    1. `GET /skills/openai-tools` on :8640 (live HTTP).
    2. `/var/lib/mios/skills/catalog.json` (static file the miner
       atomically refreshes; offline-safe).
    3. Direct read of the `skill` table in pgvector (any agent that
       can reach `:5432` via `mios-pg-query`).
* SSOT: `[skills]` in mios.toml -- `enable`, `min_length`,
  `max_length`, `min_support`, `window_hours`,
  `auto_promote_threshold`, `mine_interval_minutes`,
  `seed_catalog_dir`, `local_catalog_dir`. All routed through
  userenv.sh + the configurator HTML "Skills" section.

### C.3 -- Agent Passports (signed identity tokens)  *(landed)*

Implemented as:

* `usr/share/mios/postgres/schema-init.sql` -- an `agent_keypair`
  registry table + a `passport` JSONB field on
  tool_call / skill_invocation / event / agent_metric. Optional +
  flexible so legacy rows stay readable and v2-envelope additions
  (delegation chain headers) don't break the schema.
* `usr/libexec/mios/mios-passport` -- stdlib + python3-
  cryptography CLI: `provision / list / show / public-key /
  sign / verify / rotate / hash`. Idempotent provision generates
  Ed25519 keypairs at `/var/lib/mios/agent-passports/<agent>/`
  (private.key 0600 sysuser-owned, public.key 0644 world-
  readable). Registers public PEM in `agent_keypair` so a
  verifier without filesystem access still works.
* `usr/lib/mios/agent-pipe/server.py` -- `_passport_sign(table,
  fields)` + `_passport_verify(envelope, payload?)` helpers
  using the same canonical-JSON op_hash algorithm as the CLI.
  `_db_create` now defaults to `passport_sign=True`; every write
  through it carries an Ed25519 envelope. `_skill_invocation_
  open` builds its INSERT manually and explicitly attaches the
  passport.
  * `GET /passport/public-key?agent=` -- ship a public PEM to
    external integrators without filesystem access.
  * `POST /passport/verify` -- `{envelope, table?, fields?}` ->
    `{ok, reason, agent, kid, alg}`. Cross-agent verification
    over HTTP for clients that prefer the network surface.
* `usr/lib/systemd/system/mios-passport-provision.service` --
  one-shot firstboot keypair generator. Ordered Before=
  mios-agent-pipe / hermes-agent / mios-daemon so every signing
  service has its private key before it tries to write.
* SSOT: `[passport]` in mios.toml -- `enable`, `algo`,
  `key_dir`, `rotate_days`, `verify_on_read`, `agents` (CSV).
  All routed via userenv.sh + the configurator HTML "Passport"
  section.
* Signed bytes: `agent\nts\nnonce\nop_hash` -- deterministic +
  re-derivable from any language. `op_hash` is
  `sha256(table:canonical-json(fields-minus-passport))`,
  binding the signature to the exact data.

## Phase D -- post-Phase-C additive surface (commit 10+)

### D.1 -- Native text-editor + powershell_run verbs  *(landed)*

Closes the two FS-navigation gaps the 2026-05-18 research note
flagged.

* `usr/libexec/mios/mios-text-edit` -- stdlib Python CLI.
  Subcommands: `view / create / str_replace / insert`. Mirrors
  Anthropic's text_editor_* schema shape (view returns
  1-indexed line numbers; str_replace requires the old block
  to occur exactly once). Replaces the fragile
  `pc_type` + `pc_key ctrl+s` save chain.
* `usr/libexec/mios/mios-powershell` -- bash shim wrapping
  `pwsh.exe` / `powershell.exe` with `-NoProfile
  -NonInteractive -ExecutionPolicy Bypass`. Optional
  `--json` envelope, `--timeout N`, `--work-dir PATH`.
  Stages the script through /mnt/c/Users/Public/Documents/
  for native Windows file access (faster than the \\wsl
  UNC path).
* Five new dispatch verbs in agent-pipe `_build_dispatch_cmd`:
  `text_view`, `text_create`, `text_str_replace`,
  `text_insert`, `powershell_run`. Bodies pass through stdin
  + base64 so multiline / special-char content survives the
  broker socket round-trip.
* Router prompt advertises all five with verb-pick priority
  rules ("read X" -> text_view, "save X to Y" -> text_create,
  "run powershell: X" -> powershell_run).

### D.1a -- Hardening + Everything-Search resilience

Folded into D.1 per operator directive 2026-05-18 (harden the
Linux + Windows FS navigation + use Everything Search for
Windows paths).

* `mios-text-edit` path validation: `_validate_write_path()`
  refuses writes to /etc, /usr, /boot, /sys, /proc, /dev,
  /run, /lib, /lib64, /sbin, /bin, /mnt/c/Windows,
  /mnt/c/Program Files. `realpath` resolves symlinks first --
  no symlink escape. Operator override via
  `MIOS_TEXT_EDIT_WRITE_DENIED_PREFIXES` (CSV).
* Size caps: read 1 MiB, write 1 MiB, PowerShell script
  64 KiB, PowerShell output 256 KiB. All env-overridable.
* `text_view` resilience: on `not_found`, runs
  `mios-everything` for the basename and includes up to 5
  candidate paths in the error envelope so the planner can
  retry with the resolved path instead of giving up.
* `powershell_run` output truncation with explicit marker
  lines (`... [truncated N bytes; output cap M bytes]`) so
  the agent sees the elision instead of mis-counting.
* `_classify_verb_taint`: powershell_run output is always
  tainted (Windows-side execution = external state);
  text_view of any write-denied prefix is also tainted.
* `_HIGH_PRIVILEGE_VERBS` + `[security].
  firewall_high_privilege_verbs` extended to include the four
  WRITE-class verbs (text_create, text_str_replace,
  text_insert, powershell_run). Tainted sessions REFUSE
  dispatch.

`usr/share/mios/skills/write-text-file.json` -- seed
template demonstrating text_create -> text_view as the native
replacement for save-document's pc_type chain.

### D.2 -- ttyd browser pty bridge  *(landed)*

Operator directive 2026-05-18: "add ttyd to the stack so we can
access PowerShell from a local browser(s)". Two systemd-managed
ttyd instances expose pty-over-WebSocket bridges:

  * `mios-ttyd-bash.service`         :7681  ->  `ttyd ... /bin/bash`
  * `mios-ttyd-powershell.service`   :7682  ->  `ttyd ... mios-powershell --shell`

`mios-powershell --shell` (mode in the existing shim) execs
`pwsh.exe` (preferred) / `powershell.exe` interactively via WSL
interop, inheriting the ttyd pty. The browser tab sees a real
Windows PowerShell prompt over WebSocket.

Hardening:
  * Both bound to 127.0.0.1 by default.
  * `mios-ttyd-launch` refuses to bind beyond loopback without
    `auth_user` + `auth_pass` when `require_auth` is true.
  * Optional TLS termination via `ssl_cert` + `ssl_key`.

SSOT: `[ttyd]` in mios.toml + `[ports].ttyd_bash` (`:7681`) /
`.ttyd_powershell` (`:7682`) + the userenv.sh slot map +
configurator HTML "ttyd" section.

Package: `ttyd` in `packages-ttyd` of
`usr/share/doc/mios/reference/PACKAGES.md` (Fedora ships v1.7.7).

## Phase E -- Advanced Orchestration and Sovereignty (Research Integration)

### E.1 -- Native MCP Standardization & Hermetic Sandboxing
Standardize all tool executions on the Model Context Protocol (MCP) via the `usr/libexec/mios/mcp-server-runner` gatekeeper. All file operations must be confined to structured schemas (`glob`, `list_directory`, `read_file`) and executed strictly within lightweight, rootless containerized environments like **Lima VM** or **Kata-on-Firecracker** microVMs to prevent directory traversal escapes and capability laundering.

### E.2 -- Deterministic Orchestration (Conductor)
Transition from probabilistic, token-heavy prompt chaining to deterministic, zero-token orchestration utilizing the **Microsoft Conductor CLI**. This ensures tasks are mapped using structured YAML workflows and Jinja2 templates, deploying parallel execution groups (`fail_fast`, `continue_on_error`) for maximum reliability.

### E.3 -- Token-Time Slicing & Federated Query (LAKE)
Implement a token-time slicing queue within the `agent-pipe` orchestrator to mimic traditional CPU thread scheduling at the network socket layer, allocating VRAM dynamically. Pair this with the **Learning-assisted Accelerated Kernel (LAKE)**, built on Spice.ai's Rust engine, for optimal high-throughput federated query execution and data routing.

### E.4 -- Hindsight Primary Memory Tier
Replace legacy MAIA v8.0 runtime pools with the MIT-licensed **Hindsight** memory engine running inside the `mios-pgvector` container. Hindsight provides multi-strategy parallel retrieval (semantic vector, BM25 keyword, graph relational, and temporal) to drastically reduce context lookup latency and token bloat.

### E.5 -- Cryptographic State Validation Chains
Secure the multi-agent event bus by cryptographically chaining all agent state shifts and deliberations using **SHA-256** hashing. Event logs written to local context repositories will be tamper-evident, ensuring full auditability and mitigating context drift.

### E.6 -- Immutable Image Hardening (fapolicyd)
Bake restrictive `fapolicyd` configurations directly into the core `bootc` image during the OCI build cycle, enforcing a strict known-libs allow-list to neutralize zero-day root execution loopholes before the OS image is distributed.

## What stays put

The MCP-style execution layer (mios-launcher broker, mios-pc-
control, mios-windows, typed verbs) is already strong; the
research validates it. No changes planned. The multi-lane inference
topology — `mios-llm-light` as the primary llama.cpp lane with
multi-model auto-swap + KV-cache paging, the gated heavy GPU lanes
behind the same `MIOS_AI_ENDPOINT` — is novel vs the reference
architecture and stays.

## Cross-cutting — how this respects the system's laws

Every phase respects the six Architectural Laws and the operator rules:
- **USR-OVER-ETC / mios.toml + html SSOT** — no hardcoded values; per-phase
  knobs go into the `[skills]`/`[passport]`/`[ttyd]`/`[security]` TOML chain →
  userenv.sh → `MIOS_*` env → the configurator HTML.
- **UNIFIED-AI-REDIRECTS (Law 5)** — every agent/lane resolves the OpenAI-compat
  endpoint from `MIOS_AI_ENDPOINT`; no vendor-hardcoded URLs or ports.
- **No hardcoded English** in agent surfaces; **no hardcoded topic/app
  deny-lists** in router/refine prompts.
- **Immutable code paths / mutable state** — code under `/usr` (bootc-immutable);
  all runtime state under `/var/lib/mios/...` declared via tmpfiles (Law 2).
- **Full offline** — no cloud calls baked in; the catalog/skills/passport
  surfaces are local files + loopback HTTP + pgvector on `:5432`.

Open questions before implementing the remaining open phases:
- Phase A.2: inotify or fanotify? inotify simpler; fanotify
  catches more cases. Default inotify unless operator wants the
  fanotify generality.
- Phase B.2 personas: 4 prompts on hermes-agent (cheaper, all on
  `mios-llm-light`) or 4 isolated model instances (heavier, true
  isolation)?


# Part 4: agentic-standards-roadmap.md

<!-- AI-hint: Defines MiOS's convergence from bespoke logic onto standardized agentic protocols (MCP for tools, the OpenAI tool-call loop for execution, A2A/ACP for multi-agent coordination/delegation) so the local agent stack coordinates reliably and executes real tool calls via the `mios-mcp-server` and `agent-pipe`/Hermes orchestration. Status: Phases 1, 2, 4 shipped; 3 and 5 are cleanups.
     AI-related: mios-mcp-server, mios-mcp, mios-agent-pipe, hermes-agent, mios-opencode-gateway, mios-web-search, mios-sysview, mios-discord-send, mios-mcp.service -->
# MiOS Agentic Standards Roadmap (MCP · OpenAI tool-loop · A2A/ACP)

> **Where this fits in MiOS.** MiOS is one thing built two ways at once: an
> immutable, bootc/OCI-shaped Fedora workstation (the whole OS is a single
> container image you `bootc upgrade` like a `git pull` and `bootc rollback`
> like a Ctrl-Z) that is *also* a local, self-replicating, agentic AI operating
> system. The AI half lives behind one OpenAI-compatible endpoint: front-ends
> (Open WebUI, the Discord gateway, the `mios` CLI) hit **agent-pipe** (`:8640`),
> which refines → routes → fans out a council/swarm → dispatches tool/verb
> calls → polishes; **MiOS-Hermes** (`:8642`) is the OpenAI-compat gateway that
> runs the tool-loop; **pgvector** (`:5432`) is the unified agent memory; the
> **inference lanes** (`mios-llm-light` `:11450` primary + embeddings, the gated
> `mios-llm-heavy`/`-heavy-alt` GPU lanes) do the generation. This doc is the
> roadmap for making the COORDINATION between those parts ride open agentic
> standards instead of bespoke plumbing — so the system that ships in the image
> behaves the same on any hardware, fully local, with no cloud-AI dependency
> (Architectural Law 5).

Operator directive 2026-05-22: "NOTHING hardcoded anywhere; fix in code to
OpenAI-API standards and patterns for multi-agentic solutions using
open-source tools, locally hosted. Research, then refine to specs — ACPs,
MCP, etc." Roadmap requested ("you sequence it, I pick").

## Why
Most recurring failures trace to NON-STANDARD, hardcoded plumbing (the
exception: Hermes already runs a full standard tool-loop with its full
capability set inside the MiOS pipeline — see Phase 2):
- the executor model sometimes **narrates** "I posted to Discord" instead of
  emitting the `tool_call` it is able to → occasional reliability tuning, not
  a missing loop;
- **bespoke verb dispatch** + a (rejected) keyword detector;
- **fan-out by hardcoded strength tokens** (`event`/`what`/`happened` →
  daemon telemetry flood);
- **validation by a soft prompt rule** on a small model (misses the lie).

The fix is convergence onto the Linux-Foundation Agentic-AI standards:
**MCP** for tools, the **OpenAI tool-call loop** for execution, **A2A**
Agent Cards for coordination, **ACP** for delegated runs. All open-source,
all local, no cloud-AI dependency (Architectural Law 5). Each standard maps to
one part of the stack above: MCP is the tool surface agent-pipe/Hermes consume,
the tool-loop is what Hermes runs, A2A is how the agent-pipe fleet discovers and
delegates across peers (the `[a2a]` roster / `mios-a2a-discover`).

## What already exists (build ON this)
- `agent-pipe` (`mios-agent-pipe.service`, `:8640`) — OpenAI
  `/v1/chat/completions` endpoint (the standard surface) + the
  refine/route/council/polish orchestrator.
- `mios-mcp-server` — MCP stdio server (JSON-RPC 2.0, spec 2025-06-18);
  renders `[verbs.*]` SSOT as MCP tools; `tools/call` → agent-pipe
  `/v1/dispatch` → launcher broker. `mios-mcp.service`.
- `mios-opencode-gateway` (`mios-opencode-gateway.service`, `:8633`) — OpenAI
  `/v1` shim for opencode, the loopback ACP-style coder peer of the council.
- `usr/share/mios/ai/v1/mcp.json` — the MCP-registry overlay the agent-pipe
  CONSUMES external MCP servers from (`mcp_registry` in `mios.toml`).
- Helpers as clean tool backends: `mios-web-search` (SearXNG `:8888`),
  `mios-sysview`, `mios-discord-send`, the CDP browser tool loop.

So the work is WIRING + standardizing onto these standards, not greenfield.

## Phases (sequenced; pick a starting point)

### Phase 1 — Complete + verify the MCP tool CONTRACT  ·  effort: M  ·  risk: LOW  ·  ✅ DONE (committed)
- Audit `mios-mcp-server`: is `mios-mcp.service` running? are ALL `[verbs.*]`
  rendered as MCP tools with correct JSON input schemas?
- Fill gaps: ensure `web_search`, `browser_*`, `sysview`, `os-control` verbs
  AND `discord_send` (`[verbs.discord_send]` → `mios-discord-send` backend)
  are first-class MCP tools. Schemas come from mios.toml `[verbs.*]` (SSOT) —
  no hardcoded tool lists.
- Deliverable: one authoritative, schema-correct, locally-hosted MCP tool
  catalog. Additive — changes no live behaviour yet.

### Phase 2 — Standard OpenAI tool-call loop  ·  ✅ ALREADY REALIZED (in Hermes)
- The canonical agentic loop (offer tools → model returns `tool_calls` →
  execute → feed `role:tool` back → repeat → grounded final answer) already
  runs **inside Hermes** (`hermes-agent.service`, `:8642`), which operates full
  tool-loops with its full capability set within the complete MiOS AI
  pipeline/chains. It is NOT a thing agent-pipe still has to build.
- Topology (corrected 2026-05-22, operator): agent-pipe
  (`/v1/chat/completions`, `:8640`) is the refine → route → polish → critic
  ORCHESTRATION layer; it forwards to Hermes (`:8642`) which runs the loop,
  then folds the results back. Hermes is NOT bound to a narrow tool set — it
  carries its full built-in tool registry (terminal/shell, web, file, …) PLUS
  the full MiOS verb + skill surface (`discord_send`, os-control, browser,
  computer-use, … all reachable). Hermes config's `tools:` block only
  configures `web_search`'s provider; it is not the whole surface.
- So the historical narrate-instead-of-call symptom was never a missing-loop
  or missing-tool problem — at worst it's occasional EXECUTOR-MODEL behaviour
  (a small model describing an action instead of emitting the `tool_call` it
  is fully able to). That's optional reliability tuning, done live in the
  Hermes layer (executor model choice / `tool_choice` nudge / SOUL prose) on
  the operator's hardware — NOT an architectural gap and NOT blocking 3/5.
- SHIPPED this session (standards surface, not a fix for anything broken):
  `GET /v1/verbs/openai-tools` — the verb catalog in OpenAI `{type:function}`
  shape, the twin of `/v1/verbs` (MCP) + the A2A card skills. One SSOT
  (`_VERB_CATALOG`), three projections (MCP / OpenAI-tools / A2A). For strict
  external OpenAI / A2A / ACP clients that lack the MiOS plugin; execution via
  the existing `POST /v1/dispatch`. Hermes does not need it.

### Phase 3 — Single execution path, no hardcodes  ·  ✅ ESSENTIALLY SATISFIED
- CORRECTED FRAMING (2026-05-22): the original "delete `_build_dispatch_cmd`
  verb-arms" is WRONG. That function is NOT bespoke duplication to remove —
  it is the SINGLE shared execution backend: `/v1/dispatch` →
  `dispatch_mios_verb` → `_build_dispatch_cmd`, and MCP `tools/call`, the
  OpenAI-tools surface, A2A-routed verb calls, AND the planner DAG all execute
  THROUGH it. Deleting it breaks every standard surface. It stays.
- What Phase 3 actually wanted is already true: there is ONE execution path
  (`_build_dispatch_cmd` over the launcher broker), arms are generated from
  the `[verbs.*]` SSOT, and the rejected keyword/topic detector is gone.
  Remaining = ordinary hygiene: migrate the last few hardcoded verb arms into
  `[recipes.*]`/SSOT over time (see the no-hardcode memory). Not blocking.

### Phase 4 — A2A Agent Cards for multi-agent coordination  ·  effort: H  ·  risk: MED  ·  ✅ PUBLISH + CONSUME SHIPPED
- Replace `_pick_fanout_agents` strength-token matching with A2A Agent Cards:
  each sub-agent (Hermes, opencode, daemon, sys) publishes a card
  (capabilities/skills/endpoint); the orchestrator routes + fans out by
  card-advertised capability (semantic match), not hardcoded tokens. opencode
  keeps ACP for delegated execution. Removes the daemon-flood root cause.
- SHIPPED (publish side): agent-pipe serves the A2A AgentCard at
  `/.well-known/agent-card.json` (+ `/.well-known/agent.json` legacy +
  `/v1/agent-card`), generated from mios.toml `[agents.*]` SSOT — each agent
  becomes an A2A skill (id=name, tags=strengths, description=role+lane). Same
  data `_pick_fanout_agents` scores, now in the open standard. Additive,
  zero pipeline risk; an `x-mios` block cross-links the OpenAI `/v1` + MCP
  surfaces so a discovering peer knows how to drive MiOS.
- SHIPPED (consume side): `_pick_fanout_agents` now routes on the SAME
  `_agent_skill_tags()` SSOT the card publishes, with WORD-BOUNDARY matching
  (was substring: `search` matched inside `researching`). Card capability ==
  routing key; daemon-flood guards (fanout=false + score>0 bonus gating)
  preserved.
- SHIPPED (federation): real cross-node delegation now rides A2A — the `[a2a]`
  roster + `mios-a2a-discover` write live peers to
  `/etc/mios/ai/v1/a2a-peers.json`, and the `a2a_delegate` /
  `transfer_session_to_agent` verbs hand a sub-task (or the whole session via
  the A2A `contextId`) to a registered peer and fold its answer back. Phase 4
  is effectively complete; further refinement (semantic / embedding match over
  tags) is optional polish.

### Phase 5 — Validation → STRUCTURAL  ·  ◑ CORE ALREADY PRESENT; do NOT force the rest
- ALREADY STRUCTURAL: the confirmation engine (`_inline_satisfaction_check`)
  AND-folds the recorded `tool_call` rows' `success` fields → deterministic
  satisfied/unsatisfied when agent-pipe recorded the calls. (Those rows live in
  the `tool_call` table in PostgreSQL+pgvector, the unified agent datastore.)
- The remaining roadmap idea — "validate an action-CLAIM in the answer prose
  IFF a matching tool_call exists" — is DELIBERATELY NOT done, for two
  binding reasons: (1) it requires natural-language claim detection, which
  needs language-specific patterns → violates the no-hardcoded-language rule;
  (2) Hermes runs the tool-loop internally, so agent-pipe sees the invoked
  tool NAMES (`_tools_called`) but not always structured per-call results —
  treating "no agent-pipe row = unsatisfied" is exactly the
  "succeeds-early-then-reports-failed" false-negative the engine already fixed
  (server.py ~1979-1995). Forcing it would regress that fix.
- Net: the soft INVOKED-TOOL-CHECK polish rule stays as the language-neutral
  guard for the agent-internal path; the structural row-fold covers the
  agent-pipe-recorded path. This is the correct split, not a gap.

### Phase 6 — Hermetic Sandboxing for MCP execution  ·  effort: M  ·  risk: MED
- **What:** Standardize all tool executions on the Model Context Protocol (MCP) using the `usr/libexec/mios/mcp-server-runner` gatekeeper. All file operations must be confined to structured schemas (`glob`, `list_directory`, `read_file`) and executed strictly within lightweight, rootless containerized environments like **Lima VM** or **Kata-on-Firecracker** microVMs.
- **Why:** Prevents directory traversal escapes (e.g. Zip Slip) and capability laundering, ensuring open agentic standards don't compromise host security.

## Status / order
- Phase 1 (MCP contract) — ✅ done.
- Phase 2 (standard tool-loop) — ✅ already realized inside Hermes (full loop +
  full capabilities in the MiOS pipeline); only optional executor-reliability
  tuning remains, done live. Three standard tool projections now exist off one
  SSOT: MCP (`/v1/verbs`), OpenAI-tools (`/v1/verbs/openai-tools`), A2A skills.
- Phase 4 (A2A) — ✅ publish (agent card) + consume (tag-SSOT routing) +
  federation (peer discovery + `a2a_delegate`/`transfer_session_to_agent`)
  shipped.
- Phase 3 (retire bespoke dispatch/hardcodes) + Phase 5 (structural validation)
  remain as cleanups; neither blocks the working pipeline.

The end state these phases serve: the agentic OS half of MiOS coordinates and
executes entirely through open standards, off the one `mios.toml` SSOT, so the
same image runs the same way on any hardware — and a discovering MCP/A2A peer
can drive or be driven by a MiOS node with zero bespoke glue.


# Part 5: aios-full-control-roadmap.md

<!-- AI-hint: Strategic roadmap mapping the open-source AIOS landscape onto MiOS's current local-AI pipeline; details the implementation paths for kernel scheduling, tiered pgvector memory, KV/context engineering, multi-agent orchestration, and computer-use that carry MiOS from ~80% of the AIOS reference to full local AIOS control. -->
<!-- AI-related: /usr/share/doc/mios/concepts/aios-implementation-plan.md, /usr/share/doc/mios/concepts/upstream-gap-plan-2026-06.md, /usr/share/mios/mios.toml, /usr/share/mios/llamacpp/mios-llm-light.yaml, /usr/lib/mios/agent-pipe/server.py -->
# MiOS — Full AIOS Control Roadmap (research-grounded, 2026-06-13)

## Purpose and scope

MiOS is one system built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image you `bootc
upgrade` like a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a
**local, self-replicating, agentic AI operating system**. The same image that
ships GNOME/Wayland, GPU access via CDI, KVM/libvirt, and a k3s+Ceph one-node
cluster path also ships a complete local agent stack behind **one
OpenAI-compatible endpoint** (`MIOS_AI_ENDPOINT`, Architectural Law 5).

This document is the **AIOS half of that whole**: how MiOS's agent plane —
inference lanes → agent-pipe/Hermes orchestration → pgvector memory →
MCP/A2A → typed OS-control verbs — evolves toward a true LLM operating system
(scheduler, context manager, tiered memory, access control). It is a synthesis
of four deep research sweeps of the **open-source AIOS landscape** (June 2026),
mapped onto MiOS's current pipeline. Each pillar states the field's
battle-tested pattern, then the concrete MiOS move; sources are inline. MiOS is
already ~80% of the AIOS reference, so this is the **prioritized plan for the
remaining "full AIOS control,"** scoped to the substrate that already exists.

Audience: builders extending the MiOS agent plane. Every move below targets a
real seam in the shipped code (`mios-agent-pipe`, the `mios-llm-*` inference
lanes, the pgvector datastore, the MCP/`dispatch_mios_verb` chokepoint, the
CPU-pinned daemon-agent) — not a greenfield design.

### Where the agent plane stands today

The orchestration substrate the roadmap builds on:
**refine → route → decompose → execute → synthesize**, served by
`mios-agent-pipe.service` (`:8640`), with `MiOS-Hermes` (`hermes-agent.service`,
`:8642`) as the OpenAI-compatible gateway and tool-loop agent.

- **Inference lanes** (all behind `MIOS_AI_ENDPOINT`, Law 5):
  - **`mios-llm-light`** (`mios-llm-light.service`, `:11450`) — the **primary**
    local engine: llama.cpp behind the upstream `mios-llm-light` proxy image
    (`ghcr.io/mostlygeek/llama-swap`), multi-model auto-swap + per-conversation
    **KV-cache paging** via `--slot-save-path` and `/slots` save/restore. Serves
    the everyday chat/reasoning models, the `mios-opencode` coder model, **and
    embeddings** (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Config:
    `usr/share/mios/llamacpp/mios-llm-light.yaml`.
  - **`mios-llm-heavy`** (`mios-llm-heavy.service`, `:11441`, served-name
    `mios-heavy`) — the heavy GPU lane (SGLang, RadixAttention + HiCache
    CPU KV-offload). Gated/off-by-default on VRAM.
  - **`mios-llm-heavy-alt`** (`mios-llm-heavy-alt.service`, `:11440`,
    served-name `mios-heavy`) — alternate heavy lane (vLLM,
    PagedAttention + APC). Gated; mutually exclusive with the SGLang lane.
  - **`mios-llm-worker@`** — single-model swarm workers (templated, for the
    dGPU swarm topology).
- **Memory + RAG:** `mios-pgvector.service` (`:5432`) — **PostgreSQL +
  pgvector**, the unified agent datastore (agent_memory, event, tool_call,
  session, skill, scratch, knowledge, sys_env, kanban, …), accessed via
  `mios-pg-query` / `mios-db --pg`; embeddings come from `mios-llm-light`.
- **Tools + agents:** MCP exposes the verb/skill/recipe surface; A2A federates
  peer agents; the `dispatch_mios_verb` broker is the single tool chokepoint;
  the CPU-pinned daemon-agent tails logs and supplements context.

> Inference, embeddings, and the agent datastore are **fully local**. The
> earlier Ollama backend, SurrealDB datastore, and Qdrant vector store have been
> retired — the engines now speak the OpenAI/Ollama-*compatible* API, which is
> the only sense in which "Ollama" still appears. Naming throughout is
> `mios-<component>` (the old `CloudWS`/`cloudws-*` project name is retired).

Shipped on the way here (2026-06-11): the refine classifier now discerns
**internal / external / both**, splits "both" into a concurrent local+web
`multi_task` DAG, and **executes each facet against its own source** (local
facet → `system_status` / `mios_apps` via `_read_tool_enrich`; web facet →
`web_research`) and synthesizes — verified end-to-end (the local facet reads the
real RTX 4090).

---

## The four pillars (key findings)

### 1. Kernel + scheduling
- Rutgers **AIOS** (`agiresearch/AIOS`, kernel v0.3.0 2026-01-22) is the canonical LLM-OS:
  agent scheduler, context manager, memory/storage/tool/access managers, Cerebrum SDK.
  Reports up to **2.1× throughput** — but shipped scheduling is **only FIFO + Round-Robin**,
  isolation is **logical (privilege-group hashmap)**, and the context switch is a plain
  KV-cache snapshot (the paper's beam-search framing is NOT in the code).
- The strong *production* scheduler is **Autellix** — program-level MLFQ over vLLM,
  **4–15× throughput** by scheduling whole agent programs, not individual LLM requests.
- AIOS's own data: scheduling **hurts** trivial turns on small models — gate it to contention.

### 2. Memory + context
- **MemGPT/Letta**: tiered virtual memory (core/in-context ↔ archival/recall on disk),
  the LLM **self-pages via tool calls** (`memory_insert`/`replace`/`rethink`); productized
  on **Postgres + pgvector** (the same substrate MiOS already runs); **sleep-time agents**
  consolidate memory off the latency path; block limit is now 100k chars (not 2k).
- **Anthropic context engineering**: **compaction** (summarize+reinit near full window) +
  **context-editing** (drop stale tool results, keep last N) → +39% agentic search, 84%
  fewer tokens over 100 turns. **Sub-agent context isolation** + just-in-time retrieval.
- **Serving layer**: vLLM PagedAttention + APC; **SGLang RadixAttention + HiCache**
  (L1 GPU→L2 RAM→L3 disk, local file backend); **llama.cpp `/slots` save/restore** —
  with the **`--swa-full` guard required for Gemma/Qwen SWA models** or restored KV is wrong.
  All three map directly onto MiOS's lanes: vLLM = `mios-llm-heavy-alt`, SGLang =
  `mios-llm-heavy`, llama.cpp `/slots` = the primary `mios-llm-light`.
- Loop patterns: **ReAct** (reason+act+observe) + **Reflexion** (verbal self-reflection on
  failure into an episodic buffer, retry). Recall ranking: recency·importance·relevance.

### 3. Multi-agent orchestration
- **Magentic-One dual-ledger**: a Task Ledger (Facts/Guesses/Plan) + Progress Ledger
  (per-agent assignment + "complete?"/"progress?"), with re-plan triggered at **stall > 2**.
- **LangGraph**: state graph + **reducers** (`operator.add` accumulates concurrent writes,
  never overwrite) + **checkpoint per super-step** (durability, HITL, time-travel) + `Send()`
  dynamic map-reduce. **Supervisor vs swarm** routing (94% vs 91% accuracy, swarm ~40% faster).
- **OpenHands `AgentDelegateAction`**: parent spawns named sub-agents that run in parallel
  threads and return **one consolidated observation** (errors per sub-agent).
- **The single biggest reliability win for mixed tasks**: make an action node **depend on**
  a research node's typed output (findings → action), not run as independent siblings
  (Magentic-One WebSurfer→Coder; MS Agent-Framework explicit graphs over implicit GroupChat).
- Typed/structured handoffs (CrewAI Pydantic, MetaGPT SOP artifacts) stop the find-out→do
  boundary degrading into hallucinated free text. Loop guards (stall/handoff caps) mandatory.

### 4. Computer-use / OS control
- Field convergence: **typed-API/verb/hotkey first → a11y-tree click → vision-grounded last**
  (UltraCUA +22% OSWorld & 11% faster; Anthropic 150K→2K tokens by pushing work to code).
  This is exactly MiOS's existing posture: typed `mios_verbs.*` over MCP first, the
  `dispatch_mios_verb` chokepoint, vision only as a last resort.
- a11y-first/vision-fallback (UFO² recovers 10–25% of UIA-only failures); **Linux AT-SPI is
  materially weaker than Windows UIA** → vision fallback matters more on the flatpak side.
- Local single-GPU grounding is viable: **Holo1.5-7B** (ScreenSpot-Pro 57.94) / **UI-TARS-1.5-7B**
  (Apache-2.0, served on vLLM/SGLang — i.e. the MiOS heavy lanes). **Coordinate scaling is the
  #1 "click missed" bug** — Qwen2.5-VL emits absolute pixels, **Qwen3-VL reverted to normalized
  0-1000**; HiDPI rescale required.
- Safety = sandbox + least-privilege + **HITL on consequential actions** + injection classifier
  (Meta "Rule of Two": ≤2 of {untrusted input, sensitive access, state-change} without a gate).
- Reliability = **verify-after-action** (before/after screenshot or a11y diff) + retry +
  wait-for-stable-element + re-ground (bounded ~10 iters).

---

## Prioritized roadmap for MiOS

Mapped to MiOS's substrate (refine→route→decompose→execute→synthesize; the
`mios-llm-light` / `mios-llm-heavy` / `mios-llm-heavy-alt` lanes; pgvector +
knowledge recall; the MCP surface; typed OS-control verbs; the
`dispatch_mios_verb` chokepoint; the CPU-pinned daemon-agent). Each item closes a
named gap and serves the whole-system goal of a local, least-privileged AIOS that
upgrades and rolls back as one image.

- **P0 — Program-level scheduler with preemption (gated to contention).** Adopt
  Autellix-style MLFQ over the whole agent task/DAG so a long swarm doesn't starve quick
  council turns; demand-aware LRU eviction for victims. GATE to contention (AIOS data:
  it hurts trivial small-model turns). Closes the standing "true priority queue / preemption" gap.
- **P1 — KV slot-save/restore as agent virtual memory.** Map each conversation to a stable
  `mios-llm-light` (llama.cpp) slot file; restore-before / save-after each turn; **add
  `--swa-full` for the Gemma/Qwen lanes** (or restored KV is corrupt). The concrete local
  AIOS context manager — the lane already runs with `--slot-save-path` and `--parallel 1`.
- **P2 — Self-editing tiered memory.** Promote the per-conversation scratchpad to labeled,
  size-bounded **memory blocks** the agent edits via verbs (MemGPT); add **compaction +
  stale-tool-result clearing**; wire **memory-pressure eviction** (warn→flush, LRU-K >80%)
  to **pgvector** archival (the existing `agent_memory`/`knowledge` tables). Closes the P2.1
  eviction gap.
- **P3 — Dual-ledger + typed-output synthesis + action→research edges.** Add a per-conversation
  Fact Ledger + Progress Ledger to the DAG path; make synthesis a **reducer over typed node
  outputs** (verb-output schema for action nodes, `{claim,source}` for research) instead of a
  free-text merge (kills fabrication upstream of the polish figure-guard); for a "both" task,
  let an action facet **depend on** a research facet's output when findings must drive the action.
- **P4 — ReAct+Reflexion durable loop.** Formalize each turn as call→observe→reason until no
  tool calls, bounded by max_iter/max_retry, with a Reflexion step on tool error; **checkpoint
  per super-step** (keyed by `chat_id`, persisted to pgvector) so a crash resumes, not restarts.
  The concrete fix for the recurring narrate-instead-of-call failure.
- **P5 — Per-agent access control + HITL at the MCP chokepoint.** Implement the AIOS
  privilege-group model (agent-ID → group + audit log) at `dispatch_mios_verb`; classify verbs
  routine/privileged/destructive; **destructive → HITL confirm**. Enforces the per-child
  tool-surface goal and complements Law 6 (UNPRIVILEGED-QUADLETS); safely re-opens the
  security-blocked hermes-direct launch path.
- **P6 — Computer-use action hierarchy + reliability.** Encode verb/MCP → a11y-tree (Windows
  UIA; AT-SPI best-effort) → vision (`pc_click`) as an explicit router, not a model hope; **fix
  the qwen3-vl coordinate scaling** (pin the convention, handle HiDPI); add **verify-after-action**
  + wait-for-stable + bounded retry. Consider Holo1.5-7B / UI-TARS-1.5-7B on `mios-llm-heavy`
  (the `qwen3-vl:4b` entry in `mios-llm-light.yaml` is the staged vision-fallback seat).
- **P7 — KV hierarchy + sleep-time consolidation.** The SGLang **HiCache** path is already
  wired on `mios-llm-heavy` (CPU KV-offload); finish it so the 17K-token tool-surface prefix
  reuses and idle KV spills GPU→RAM→disk on the heavy lane. Give the **daemon-agent a Letta
  sleep-time job** (consolidate pgvector `knowledge` rows + shared memory blocks off the
  latency path). Upgrade recall to recency·importance·relevance.

- **P8 — Token-Time Slicing & Federated Query (LAKE).** Implement a token-time slicing queue within the `agent-pipe` orchestrator to mimic traditional CPU thread scheduling at the network socket layer, allocating VRAM dynamically. Pair this with the Learning-assisted Accelerated Kernel (LAKE), built on Spice.ai's Rust engine, for optimal high-throughput federated query execution.
- **P9 — Deterministic Orchestration (Conductor).** Transition from probabilistic prompt chaining to deterministic, zero-token orchestration utilizing the Microsoft Conductor CLI with structured YAML workflows and Jinja2 templates.
- **P10 — Hindsight Primary Memory Tier.** Replace legacy MAIA runtime pools with the MIT-licensed Hindsight memory engine inside `mios-pgvector` for multi-strategy parallel retrieval.
- **P11 — Cryptographic State Validation Chains.** Secure the multi-agent event bus by cryptographically chaining all agent state shifts using SHA-256 hashing.
- **P12 — Immutable Image Hardening (fapolicyd).** Bake restrictive `fapolicyd` configurations directly into the core `bootc` image during the OCI build cycle, enforcing a strict known-libs allow-list to neutralize zero-day root execution loopholes before distribution.

### What NOT to copy
- MetaGPT's rigid role assembly-line (trades concurrency for determinism) — take its
  typed-artifact-between-stages idea (P3), not the fixed role sequence.
- The paper's beam-search context-switch framing — cite/build the real KV-cache snapshot
  (MiOS already has it via the `mios-llm-light` `/slots` lane).
- Don't size MiOS expectations to vendor "superhuman OSWorld ~72%" claims (self-reported);
  independent peer-reviewed agents are ~27–35%. Architecture choices exist *because* raw
  reliability is low — that is the load-bearing lesson for local-first AIOS control.


# Part 6: aios-completion-roadmap.md

<!-- AI-hint: Maps MiOS's current architectural progress against the Rutgers AIOS reference and 2025-26 industry standards to identify the remaining technical gaps — scheduler preemption, memory self-edit, federation CONSUME, semantic firewall — for evolving the immutable bootc agent OS into a complete AIOS. -->
# MiOS → complete AIOS: research synthesis + continuation roadmap (2026-06-07)

> **Status:** continuation roadmap (historical-but-live). Captures the 2026-06-07
> gap analysis and the ranked plan that work since has been executing against.
> Facts (inference lanes, datastore, service names) are reconciled to the current
> system; the roadmap items and rationale are preserved as the planning record.

## Why this doc exists (purpose within the whole)

MiOS is one thing built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image — boot it, `bootc upgrade`
it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is *also* a **local,
self-replicating, agentic AI operating system**. The same image that ships
GNOME/Wayland, GPU via CDI, KVM/libvirt, and a k3s+Ceph cluster path also ships a
full local agent stack behind one OpenAI-compatible endpoint (`MIOS_AI_ENDPOINT`,
Architectural Law 5).

The "agentic AI OS" half is not a bolt-on chatbot; it is structured as a real
**operating-system kernel for agents**. This document measures that half against
the canonical **AIOS** reference and the 2025-26 standards convergence, names the
concrete gaps to being a *complete* AIOS, and ranks the continuation work by
leverage × safety. Its audience is whoever is extending the agent plane and needs
to know exactly which kernel managers are done, which are half-wired, and which
single moves convert MiOS from a one-operator ensemble into a true federated
agent OS.

How the piece serves the whole: the build pipeline assembles the bootc image; the
image ships the inference lanes, the agent-pipe orchestrator, pgvector memory, and
the MCP/A2A surfaces; the bootc lifecycle carries that forward and rolls it back.
This roadmap is the map of where the *agent kernel* inside that image is complete
and where it is not.

This is a synthesis of four cited research passes (AIOS reference architecture;
kernel resource management; tool + federation layer; safety/governance/reliability)
against MiOS's current state. **Verdict: MiOS already implements the canonical AIOS
six-manager kernel + LLM-syscall discipline and meets or exceeds table-stakes on
~13 of 16 components.** The gaps to being a *complete* AIOS by the 2025-26
reference are concentrated, defined, and mostly additive.

## Reference standard (what "a complete AIOS" requires)
- **Rutgers AIOS** (arXiv:2403.16971, COLM 2025): LLM-as-CPU-core; six kernel managers
  (Agent Scheduler, Context, Memory, Storage, Tool, Access) + a typed **LLM-syscall**
  interface; agents in user-space never touch resources directly.
- **Cerebrum / AIOS-Agent SDK** (arXiv:2503.11444): 4-layer agent (LLM/memory/storage/
  tool), **declarative (author,name,version) specs**, AgentHub discovery.
- **2025-26 convergence:** **MCP** (tools) + **A2A** (agent-to-agent) are the two
  load-bearing standards (both now Linux-Foundation-governed: A2A 2025-06, MCP/AAIF
  2025-12); AGNTCY/OASF is the discovery/identity layer; ACP merged into A2A.
- **Frontier:** real federation (CONSUME A2A/MCP, not just publish/serve), open
  discovery, governance-as-job-metadata, CaMeL-class semantic firewall, OTel GenAI
  tracing, and an AIOS-paper-style benchmark (task accuracy × systems throughput).

## How MiOS maps onto the AIOS kernel today (the system it grades)

The agent plane realises the six managers across a handful of unprivileged
Quadlet services, all resolving the one endpoint per Architectural Law 5:

- **LLM core (the "CPU")** — `mios-llm-light` (:11450) is the **primary** lane:
  llama.cpp behind the upstream `mios-llm-light` proxy image
  (`ghcr.io/mostlygeek/llama-swap`), multi-model auto-swap + KV-cache paging,
  serving the everyday models, the `mios-opencode` coder model, **and embeddings**
  (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Config:
  `usr/share/mios/llamacpp/mios-llm-light.yaml`. The heavy lanes `mios-llm-heavy`
  (SGLang, :11441, served-name `mios-heavy`) and `mios-llm-heavy-alt` (vLLM,
  :11440) are gated off-by-default on VRAM. The engines speak the OpenAI/
  Ollama-compatible API (a legitimate upstream API reference — Ollama itself is
  retired as a MiOS backend).
- **Scheduler / Context / Memory / Storage / Tool / Access** — realised in the
  **agent-pipe** orchestrator (`mios-agent-pipe`, :8640) and **MiOS-Hermes**
  gateway (:8642), backed by the unified **PostgreSQL + pgvector** datastore
  (`mios-pgvector`, :5432; via `mios-pg-query` / `mios-db --pg`).

## Complete-AIOS checklist — MiOS status
PRESENT (≥ reference): LLM-core abstraction (llama.cpp + the upstream mios-llm-light
proxy on `mios-llm-light`, OpenAI Tier-0/1/2 + `/v1/responses`) · Context Manager
(`_kv_paging`/`_kv_slot_action` KV snapshot/restore + `mios_kvfork` prefix-fork) ·
Storage Manager (pgvector durable + cosine recall) · Tool Manager server side
(82 verbs+recipes+skills, 3-projection catalog, `tool_search`) · Multi-agent
orchestration (swarm decompose→synthesis, priority gate) · MCP **serve** + A2A
**publish** · HITL + determinism-replay · request-cancellation · self-improvement
(LoRA distill + skill loops) · immutable bootc host.

PARTIAL / ABSENT (the work): Scheduler **preemption** · Memory **self-edit + pressure-
flush** · **Federation CONSUME** (A2A/MCP client halves dormant) · **Declarative agent
specs + discovery** · **Semantic firewall** (taint/provenance) · **microVM/fapolicyd**
sandbox (gated) · **record-and-replay** determinism · **OTel GenAI spans + AIOS-bench
eval** · **code-mode** for heavy verbs · storage **versioning/rollback**.

## Continuation roadmap (ranked by leverage × safety)

### P1 — highest leverage, safe, mostly-additive
1. **Scheduler turn-boundary preemption.** Wire the two halves that already exist
   independently: `mios_sched.PriorityGate` (priority + aging admission) + `_kv_paging`
   (KV save/restore). On a high-priority arrival while saturated, suspend the lowest-
   priority in-flight turn **at its next tool-call/DAG step boundary** → KV-save →
   admit urgent → KV-restore on resume. Add SLA classes (interactive/batch/background).
   SSOT-gated, degrade-open. *(NOT mid-decode — turn-boundary captures the interactive
   win on a single 4090.)* Basis: AIOS RR↔Context-Manager coupling; vLLM swap-recovery.
2. **Federation CONSUME — light up the client halves.** The core gap. `_mcp_tool_to_
   openai_tool` (ingest a remote server's tools) + `_a2a_send_message_to_peer`
   (delegate to a peer) are wired but dormant (vendor ships the registry empty:
   `/usr/share/mios/ai/v1/mcp.json`; runtime peers in `/etc/mios/ai/v1/mcp.json`
   and `/etc/mios/ai/v1/a2a-peers.json`).
   Self-test loop: register **MiOS's own** A2A card + MCP endpoint in the overlays →
   verify the client round-trips (A2A Message→Task→Artifact; MCP tools/list+tools/call)
   → then a 2nd MiOS node over the LAN/WSL gateway (Tailscale is OFF by policy). Turns a
   remote node into a real swarm worker; `mios-a2a-discover` already auto-populates
   `a2a-peers.json` from live AgentCards.

### P2 — high value, additive
3. **Memory self-edit + pressure-flush (MemGPT/Letta).** Expose `memory_append` /
   `memory_replace` verbs (agent-curated pinned pgvector tier) + a 70%/100%-of-`n_ctx`
   trigger that evicts oldest FIFO turns and writes a **recursive summary** into the
   scratchpad head. Complements (doesn't replace) KV-paging. Basis: arXiv:2310.08560.
4. **Semantic firewall (CaMeL-class).** Provenance/taint tag on every tool result
   carried through the scratchpad; a policy gate in `dispatch_mios_verb` that blocks a
   **side-effecting** verb driven by **tainted** (untrusted web/RAG) data without HITL
   approval (wire to the existing HITL queue, `mios_hitl`). Policies in mios.toml SSOT
   (no hardcoded deny-lists). Basis: dual-LLM/CaMeL (arXiv:2503.18813), OWASP LLM01/LLM06.
5. **Code-mode for heavy verbs/recipes.** Route multi-step verb chains + the recipe
   layer through a sandboxed code-exec lane (`mios_codemode`) so intermediate blobs
   (web corpora, file contents, DB rows) stay out of model context; only filtered
   results return. Basis: Anthropic code-execution-with-MCP (98.7% token cut),
   Cloudflare Code Mode.

### P3 — measurability + maturity
6. **OTel GenAI spans.** Emit `invoke_agent`/`execute_tool` spans with `gen_ai.*`
   attributes into a baked-in local collector (Portal as viewer); link to the replay log.
7. **AIOS-bench harness** (the "is MiOS a good AIOS" gate). Run GAIA / SWE-Bench-Lite /
   a τ-bench-style pass@k through MiOS, reporting **task accuracy × systems metrics**
   (throughput, agent waiting time, fairness under concurrency) per image build. Feed
   low pass@k cases into the LoRA/skill-improve loops (Voyager-style).
8. **Record-and-replay determinism.** Make replay serve **logged** LLM/tool I/O (not
   re-invoke); seed sampling. Tamper-evident on the immutable host.
9. **Declarative agent specs + discovery.** Give each agent an (author,name,version)
   card (reuse the A2A card schema) + expose the roster as an A2A-discoverable directory
   so P1#2's client discovers peers instead of reading a static file.

### P4 — operator-gated (image rebuild / keys)
10. **Sandboxing:** bake **fapolicyd** (known-libs→restrictive) into the bootc image;
    run tool/code exec in **Kata-on-Firecracker** microVMs behind a single-host MCP-
    gateway. (Image rebuild → operator.)
11. **Storage versioning/rollback** for self-edited core facts (`valid_from/valid_to`) +
    periodic cosine-dedup compaction.

## Net
The historic gap — the AIOS *kernel* — is built-but-gated / partial / introspection-only (see aios-engineering-blueprint.md). The
single highest-leverage move is **P1#1 (turn-boundary preemption)** because both halves
exist and only need wiring; the single most *strategic* move is **P1#2 (federation
consume)** because it converts MiOS from a one-operator ensemble into a true federated
agent OS — one immutable bootc image that, once built and booted, can discover and
delegate to its own replicas. Everything in P1–P3 is additive + fail-safe; only P4
needs the operator (because it touches the image and keys).

Sources: AIOS arXiv:2403.16971 · Cerebrum arXiv:2503.11444 · MemGPT arXiv:2310.08560 ·
vLLM/PagedAttention arXiv:2309.06180 · CaMeL arXiv:2503.18813 · Voyager arXiv:2305.16291 ·
MCP (modelcontextprotocol.io) · A2A (a2a-protocol.org) · AGNTCY (docs.agntcy.org) ·
Anthropic code-execution-with-MCP / multi-agent-research · OTel GenAI semconv.


---


# Part 7: Architectural Gap-Fill (2026-06-24)

<!-- AI-hint: Additive-only section. Six concrete gaps identified by cross-referencing the full roadmap against the OpenAI-vs-MiOS comparative research (June 2026). Each gap is genuinely absent from Parts 1-6: RouteMoA diversity gate, MOSAIC ILP aggregation bypass, pass∧k deployment gate, DGM formal proof-of-utility, rechunking delta distribution for edge OCI distribution, and smart_resize spatial formalization for UI-TARS computer-use. Files: usr/lib/mios/agent-pipe/server.py, usr/share/mios/mios.toml, usr/libexec/mios/mios-pc-control, usr/share/mios/llamacpp/mios-llm-light.yaml, usr/lib/systemd/system/. -->

*Source: OpenAI native agent loop mechanics vs MiOS comparative research (2026-06-24). Each item below is additive — it fills a named gap not present in Parts 1–6. Priority uses the same legend as Part 2: **P0** blocker · **P1** high · **P2** med · **P3** polish.*

---

## GAP-1 — RouteMoA: Pre-Synthesis Input Diversity Gate  **[P2]**

*Parts 1–6 define DCI-CF (B.1/B.2) for deadlock resolution and the MoA synthesis loop, but nothing mathematically governs the semantic diversity of inputs **before** the aggregator fires. Feeding a highly correlated ensemble wastes VRAM, burns context tokens, and degrades synthesis quality — the echo-chamber failure mode.*

- **What:** Implement a **Greedy Diversity Embedding Selection** pass (RouteMoA) inside `agent-pipe`'s council fan-out path. Before handing the `k` candidate council responses to the `aggregate-and-synthesize` prompt, score all response embeddings pairwise (cosine similarity over the existing `nomic-embed-text` 768-d vectors already produced by `mios-llm-light`). Select the maximally diverse subset via the minimax algorithm:

  1. Initial selection — pick the candidate with the **lowest mean similarity** to all others:
     `i₀ = argmin_{i∈C}( (1/N) Σ_j S_{i,j} )`
  2. Iterative expansion — for each remaining slot, pick the candidate that **minimizes its maximum similarity** to any already-selected item:
     `Φ(i) = max_{q∈Q} S_{i,q}` → `i_t = argmin_{i∈C} Φ(i)`

  Gate behind `[council].diversity_gate=true` (SSOT, default `false` — degrade-open). When enabled, any council slot whose similarity to the selected set exceeds `[council].diversity_threshold` (default `0.92`) is replaced with the next most-orthogonal candidate. Similarity matrix is computed on the already-generated 768-d embeddings; no extra model calls.

- **Files:** `usr/lib/mios/agent-pipe/server.py` (council synthesis path, after fan-out, before the aggregator prompt); `usr/share/mios/mios.toml` (`[council]` block — add `diversity_gate`, `diversity_threshold`).
- **Accept:** With two semantically identical council responses and `diversity_gate=true`, the second is replaced by the next most-orthogonal candidate; `/v1/cluster/health` includes `diversity_gate_active: true`; gate disabled → byte-identical behavior to today. No new model calls added.
- **Deps:** A1 (unified `[agents.*]` template), B.1 (DCI-CF personas).

---

## GAP-2 — MOSAIC Confidence-Aware Aggregation Bypass  **[P2]**

*The roadmap targets token-time slicing (H2/P8/E.3) and ILP makespan minimization is mentioned, but the concrete **aggregator bypass gate** — skipping the expensive final synthesis LLM call when expert responses already converge — is not a named task. This is the single highest-leverage latency win for routine council queries.*

- **What:** Add a **confidence-aware aggregation gate** to the council synthesis path in `agent-pipe`. After fan-out, before invoking the aggregator prompt:

  1. Compute pairwise cosine similarity across the `k` council responses (re-uses the vectors from GAP-1 if both are enabled; otherwise computes inline).
  2. If the fraction of pairs exceeding a consensus threshold `τ` (configurable, default `τ=0.95` — conservative) equals `k(k-1)/2` (all pairs agree), **bypass the aggregator** entirely and return the highest-confidence individual response directly.
  3. Log the bypass event as a pgvector `event(kind="aggregator_bypass", council_size=k, mean_similarity=…)` row for auditability.

  SSOT: `[council].aggregator_bypass=true` (default `false`), `[council].aggregator_bypass_threshold=0.95`. Degrade-open — disabling restores today's full synthesis path.

  Reference outcome (MOSAIC paper, arXiv:2606.03014): at `τ=1.0` (3-of-3 unanimous), 45.7% of aggregator calls are bypassed with +0.24 pp accuracy on MMLU-Pro; at `τ=0.67`, 84.6% bypassed with -0.62 pp. Start conservative (`τ=0.95`) and tune with the AIOS-bench harness (Part 6, P3#7).

- **Files:** `usr/lib/mios/agent-pipe/server.py` (council/synthesis path); `usr/share/mios/mios.toml` (`[council]` block — `aggregator_bypass`, `aggregator_bypass_threshold`).
- **Accept:** With `aggregator_bypass=true` and three identical council responses above threshold, the aggregator LLM is not called; the event row is written; `/v1/cluster/health` reports `aggregator_calls_bypassed_pct`. Gate disabled → byte-identical to current behavior.
- **Deps:** GAP-1 preferred (shares the embedding computation); A1.

---

## GAP-3 — pass∧k as a DGM Deployment Gate  **[P2]**

*Part 6 (P3#7) introduces a τ-bench-style AIOS-bench harness reporting pass@k. The roadmap never names the stricter **pass∧k** metric — where **all** k attempts must succeed — as a hard deployment gate for the self-improvement loop (B3 "self-improve ACT half"). This is the critical gap: pass@k is an optimistic capability measure; pass∧k is an operational reliability measure. They diverge catastrophically at k≥3.*

- **What:** Extend the AIOS-bench harness and the self-improvement loop (B3) with a **pass∧k gate**:

  The metric: `pass∧k = p^k` (exponential decay; a 61% single-attempt agent hits <25% at k=8). Implementation:
  1. After any proposed skill promotion (C.2 miner) or self-improvement commit (B3), run the affected trajectory **k=3 times** (configurable: `[reliability].pass_and_k_count`, default `3`).
  2. Gate: ALL k runs must succeed (`tool_call.success=true` + `event(kind="firewall_block")` count=0 + no HITL escalation). A single failure vetoes the promotion.
  3. For DGM-class self-rewrites (when B3 "ACT half" is implemented): the k requirement scales up to `[reliability].pass_and_k_dgm_count` (default `5`) before the rewrite is committed to `main`.
  4. Report `pass_and_k_rate` alongside `pass_at_k` in the AIOS-bench output table so regressions are visible across builds.

  This closes the gap between MiOS's *peak capability* (pass@k) and its *operational consistency* (pass∧k), which is the correct measure for an OS-level agent that executes autonomously.

- **Files:** `usr/libexec/mios/mios-skills` (`promote` subcommand — add the k-run gate); `usr/lib/mios/agent-pipe/server.py` (self-improve path, B3); `usr/share/mios/mios.toml` (`[reliability]` block — `pass_and_k_count`, `pass_and_k_dgm_count`).
- **Accept:** Promoting a skill that fails 1-of-3 replay runs is rejected with `pass∧k gate: FAIL (2/3 succeeded, required 3/3)`; a 3/3 clean run promotes. AIOS-bench output includes `pass∧k` column. Deps: C.2 (skills miner), B3 (self-improve), Part 6 P3#7 (bench harness).

---

## GAP-4 — Darwin Gödel Machine: Formal Proof-of-Utility Precondition for Self-Rewrites  **[P3]**

*B3 names "self-improve ACT half" as a stub. The roadmap does not articulate the DGM mathematical precondition — that a proposed source-code rewrite must **mathematically prove** it increases future utility before it is admitted — nor the bounded-sandbox evaluation infrastructure it requires. Without this gate, B3's ACT half is a regression risk.*

- **What:** When implementing B3's ACT half (the step where `mios-agent-pipe` proposes and applies code changes to itself), gate every proposed rewrite through a **utility proof sandbox**:

  1. **Sandbox execution:** run the proposed diff in a forked, isolated `mios-agent-pipe` instance (rootless Podman container, network-off, read-only host mount) against a fixed replay corpus of `n=20` canonical trajectories drawn from pgvector `tool_call` history.
  2. **Utility theorem:** the rewrite is accepted if and only if:
     - `pass∧k_new ≥ pass∧k_current` (GAP-3 metric; no reliability regression), AND
     - `mean_latency_new ≤ mean_latency_current × 1.05` (≤5% latency increase), AND
     - `peak_vram_new ≤ peak_vram_current × 1.10` (≤10% VRAM increase).
  3. If any theorem fails, the rewrite is **mathematically vetoed** — no human review needed, no commit made. The veto is logged as `event(kind="dgm_veto", reason=…)` to the Merkle-chained audit trail (H5/E.5).
  4. SSOT: `[self_improve]` block in `mios.toml` — `enable`, `sandbox_image`, `replay_corpus_size`, `latency_tolerance`, `vram_tolerance`, `pass_and_k_required`.

- **Files:** `usr/lib/mios/agent-pipe/server.py` (B3 self-improve path); `usr/share/mios/mios.toml` (`[self_improve]` block); a new `usr/libexec/mios/mios-dgm-sandbox` shim (rootless Podman fork + replay runner).
- **Accept:** A proposed rewrite that regresses pass∧k by 1 failed run is rejected with a logged veto; a neutral-or-improving rewrite is admitted. Gate is fully SSOT-driven; `enable=false` disables the ACT half entirely (safe default). Deps: GAP-3 (pass∧k gate), H5 (Merkle chain audit), B3 (self-improve stub).

---

## GAP-5 — Rechunking Delta Distribution for Edge / Offline OCI Updates  **[P2]**

*Part 1 covers `bootc upgrade` + `greenboot` rollbacks. The roadmap has no item for **block-level binary-delta compression** of the OCI image update stream itself — the mechanism that makes distributing a multi-gigabyte OS image to bandwidth-constrained edge nodes (autonomous vehicles, air-gapped servers, IoT clusters) feasible without saturating uplinks.*

- **What:** Implement a **rechunking pipeline** in the MiOS OCI build and distribution path that isolates block-level deviations between image states rather than distributing a complete new image:

  1. **Build step:** after `bootc build`, run a `mios-rechunk` post-processor that performs binary diffing (zstd-compressed block comparison) between the new OCI layer blobs and the prior published image manifest. Output: a delta bundle containing only the changed content-addressed chunks (modified tensor weights, updated prompt templates, adjusted heuristic thresholds in `mios.toml`, patched Python bytecode).
  2. **Distribution math:** target update size reduction of 80–90% vs. the full image:
     `Δ_size = ((Size_original - Size_rechunked) / Size_original) × 100% ≈ 80–90%`
     Validated by comparing `podman image diff` layer sizes before/after a representative `mios-agent-pipe` patch commit.
  3. **Receiver:** add a `mios-oci-delta-apply` service that fetches the delta bundle from the distribution endpoint, verifies its SHA-256 manifest signature (consistent with H5 cryptographic chaining), applies the chunk patches to the local OCI store, and signals `bootc` to switch the staged deployment — without pulling the full image.
  4. SSOT: `[distribution]` block in `mios.toml` — `rechunk_enable`, `delta_endpoint`, `chunk_min_size_kb`, `verify_signature`.

- **Files:** new `usr/libexec/mios/mios-rechunk` (build-time delta generator); new `usr/lib/systemd/system/mios-oci-delta-apply.service`; `usr/share/mios/mios.toml` (`[distribution]` block); `Containerfile` (add rechunk post-build step).
- **Accept:** A patch that changes only `mios-agent-pipe/server.py` produces a delta bundle ≤15% of the full image size; `mios-oci-delta-apply` applies it and `bootc status` shows the new deployment staged; signature mismatch aborts apply. Deps: Part 1 (bootc + greenboot), H5 (SHA-256 chain for signature verification).

---

## GAP-6 — smart_resize: Formal 3-Constraint Spatial Normalization for UI-TARS  **[P2] 🖥️**

*Part 5 (P6) names the Qwen3-VL coordinate scaling regression ("pin the convention, handle HiDPI") and mentions UI-TARS-1.5-7B as a candidate for `mios-llm-heavy`. The roadmap has no named task for the formal `smart_resize` algorithm that must govern every VLM coordinate round-trip — without it, "click missed" remains the #1 computer-use failure mode. This is not optional polish; it is load-bearing math for any vision grounding path.*

- **What:** Implement the **smart_resize spatial normalization algorithm** as a first-class library in `mios-pc-control`, enforced for all VLM-sourced coordinates (UI-TARS, Qwen-VL, any future vision model on `mios-llm-heavy`):

  The algorithm must satisfy three hard geometric constraints before any image is passed to the VLM:
  1. **Patch divisibility:** `H mod IMAGE_FACTOR == 0` and `W mod IMAGE_FACTOR == 0`, where `IMAGE_FACTOR=28` (aligns to the ViT patch embedding grid). Violation causes coordinate quantization error.
  2. **Pixel budget:** `MIN_PIXELS ≤ H × W ≤ MAX_PIXELS` (e.g., `100 × 28² ≤ area ≤ 16384 × 28²`). Prevents OOM during attention computation on the heavy lane's VRAM budget.
  3. **Aspect ratio bound:** `max(H/W, W/H) ≤ MAX_RATIO` (default `200`). Prevents spatial distortion that degrades bounding-box predictions.

  After resize and VLM inference, apply the deterministic inverse projection to recover physical pixel coordinates:
  ```
  X_norm = X_raw / W_tensor    Y_norm = Y_raw / H_tensor
  X_abs  = round(X_norm × W_orig)    Y_abs = round(Y_norm × H_orig)
  ```
  Where `(W_orig, H_orig)` is the **physical display resolution** captured at screenshot time (not the OS reported resolution — account for HiDPI scaling factors on Wayland compositors).

  SSOT: `[computer_use]` block in `mios.toml` — `image_factor` (default `28`), `min_pixels`, `max_pixels`, `max_ratio`, `hidpi_scale_factor` (default `1.0`; set to `2.0` for HiDPI). The existing `cu_ground` vision shim (per the e2e-test-matrix) becomes the canonical call site for this library.

- **Files:** new `usr/libexec/mios/mios-smart-resize` (stdlib Python, no new deps; takes `--width W --height H --image-factor N --min-pixels N --max-pixels N` + stdin PNG → stdout resized PNG + JSON metadata including `W_tensor`, `H_tensor`); `usr/libexec/mios/mios-pc-control` (call `mios-smart-resize` before every VLM grounding request; apply inverse projection to returned `(x,y)` before dispatching `pc_click`); `usr/share/mios/mios.toml` (`[computer_use]` block).
- **Accept:** A screenshot at 3840×2160 (HiDPI 2×) is resized to a patch-aligned tensor; the returned raw coordinate `(512, 384)` is projected back to the correct physical pixel `(1536, 1152)` on the 3840×2160 display; a `pc_click` at the physical coordinate lands within 2px of the target element. Constraint violations (non-divisible dimensions, over-budget area) raise a logged error rather than passing malformed tensors to the VLM. Deps: P6 (computer-use action hierarchy), the `mios-llm-heavy` vision lane (UI-TARS-1.5-7B or Holo1.5-7B seat).

---

## Part 7 quick-reference priority

**P2:** GAP-1 (RouteMoA diversity gate) · GAP-2 (MOSAIC aggregation bypass) · GAP-3 (pass∧k deployment gate) · GAP-5 (rechunking delta distribution) · GAP-6 (smart_resize spatial normalization 🖥️).
**P3:** GAP-4 (DGM formal proof-of-utility sandbox — depends on GAP-3 + B3 stub completion).

*Dependency chain: GAP-1 → GAP-2 (share the embedding computation). GAP-3 → GAP-4 (pass∧k gate is the theorem the DGM sandbox evaluates). GAP-6 is standalone. GAP-5 is standalone but benefits from H5 (SHA-256 Merkle chain) being live first.*

*Research evidence: OpenAI vs MiOS comparative analysis (2026-06-24) — RouteMoA arXiv:2505.24442 · MOSAIC arXiv:2606.03014 · τ-bench pass∧k arXiv · UI-TARS smart_resize arXiv + bytedance/UI-TARS README_coordinates.md · DGM self-referential proof-gated rewriting.*

---

# Part 8: Hermes Sovereignty Migration (2026-06-24)
<!-- AI-hint: Additive. Two-phase plan to replace MiOS-Hermes (NousResearch/hermes-agent) with a MiOS-native gateway that has no proprietary cloud dependency, no upstream hard constraints, and an Apache 2.0 toolchain. Tasks: T-076..T-083 in TASKS.md. -->

## Background

`hermes-agent.service` at `:8642` is the OpenAI-compatible tool-call gateway that `agent-pipe` dispatches to. It provides: the `/v1/chat/completions` loop, MCP client (stdio → `mios-mcp-server`), skill catalog refresh, SearXNG web search, and session persistence. It runs on NousResearch's `hermes-agent` framework (MIT-licensed code, but with the following operational concerns):

1. **Cloud-default configuration.** Vendor defaults route to `openrouter.ai + anthropic/claude-opus-4.6`. A fresh install 401s immediately until MiOS's `config.local.yaml` override surgery is applied (see `usr/share/mios/hermes/config.yaml` L53-59 commentary).
2. **Nous Portal dependency pull.** The "frictionless" production path is a proprietary subscription gateway bundling models, tools, and browser automation. Self-hosting requires ongoing config surgery against an upstream that is designed to steer users toward the Portal.
3. **Hard upstream constraints.** Hermes ≥0.15 refuses tool use when `context_length < 64k`. This is a vendor-imposed constraint that tightens the coupling between framework version and infrastructure configuration.
4. **Single-company governance.** Nous Research controls both the framework and the recommended cloud backend. Architectural Law 5 (no cloud-AI dependency) is currently satisfied only by MiOS's active overrides — not by the upstream's design intent.

**License finding:** The framework code is MIT-licensed and can be run without the Nous Portal. The concern is not the license text but the operational gravity toward proprietary services and the risk that future version upgrades introduce new hard constraints or cloud-default behaviours. Replacing Hermes eliminates this governance surface entirely.

---

## Candidate Selection

Research evaluated six candidates against the MiOS-critical dimensions (OpenAI `/v1` drop-in, MCP client, local inference only, Law 5 compliance, migration effort, governance). Full analysis: `hermes_replacement_research.md`.

| Candidate | License | Role fit | Decision |
|---|---|---|---|
| **Letta (MemGPT)** | Apache 2.0 | Memory backend (shares pgvector) | ✅ **Phase 1 — memory complement** |
| **smolagents (HuggingFace)** | Apache 2.0 | Tool-loop engine (~1k LOC, auditable) | ✅ **Phase 2 — gateway engine** |
| AG2 | Apache 2.0 | Multi-agent orchestration | Future — agent-pipe replacement candidate |
| LangGraph | MIT | Checkpoint/HITL workflows | Future — orchestration layer candidate |
| OpenHands | MIT | Coding specialist sub-agent | Future — specialist delegation target |
| Custom FastAPI only | MiOS-owned | Maximum sovereignty | Merged into Phase 2 design |

---

## Phase 1: Letta Memory Complement (P2, no disruption)

### Rationale
Letta's native Core/Recall/Archival tiering maps directly onto the MiOS memory roadmap items (MEM-02 T-035, MEM-03 T-036, MEM-05 T-056). It shares the `mios-pgvector` PostgreSQL instance (separate schema, same container), adding zero new infrastructure. Phase 1 deploys Letta **alongside** the running `hermes-agent.service` with no downtime and no changes to the gateway path.

### Architecture

```
agent-pipe (:8640)
    |
    +-- tool call: memory_append / memory_replace / memory_search
    |       |
    |       v
    |   LettaMemoryClient (thin httpx wrapper in server.py)
    |       |
    |       v
    |   mios-letta-server (:8283)  [Podman Quadlet, Apache 2.0]
    |       |
    |       v
    |   mios-pgvector (PostgreSQL, schema: mios_letta)
    |
    +-- everything else
            |
            v
        hermes-agent (:8642)  [unchanged]
```

### Key decisions

- **Shared PostgreSQL, separate schema**: `mios_letta` schema within the existing `mios-pgvector` pod. No second database pod. Schema created by a `schema-init.sql` fragment (additive).
- **Local LLM only (Law 5)**: `LETTA_LLM_BASE_URL=http://localhost:11450/v1` (mios-llm-light). `LETTA_EMBEDDING_MODEL=nomic-embed-text`. Zero cloud calls.
- **Degrade-open gate**: `[agents.letta].memory_backend = false` (default) → agent-pipe falls back to existing pgvector-direct path. No regression on upgrade.
- **Existing `agent_memory` table preserved**: kept as a read-only snapshot target; Letta writes authoritative state. Tables are complementary, not replaced.

### Delivers (Phase 1)
- **T-035** (MEM-02 self-editing tiered memory) — implemented via Letta `memory/blocks` API
- **T-036** (MEM-03 context compaction) — implemented via Letta native summarization loop
- **T-056** (MEM-05 sleep-time consolidation) — implemented via Letta's daemon consolidation agent

---

## Phase 2: mios-gateway-agent (P3, strategic replacement)

### Rationale
Phase 2 replaces `hermes-agent.service` at `:8642` with `mios-gateway-agent.service` — a ~800-line MiOS-native FastAPI service with `smolagents.ToolCallingAgent` (Apache 2.0, ~1k LOC auditable core) as the tool-loop engine. **Zero breaking changes**: same port, same `/v1/chat/completions` OpenAI wire protocol, same MCP tool surface. The transition is gated (`[gateway].enable = false` by default) and validated by a smoke-test suite before cutover.

### Architecture

```
agent-pipe (:8640)   OWUI (:3030)   CLI
        |                 |           |
        +--------+--------+-----------+
                 |
        mios-gateway-agent (:8642)          [Phase 2 replacement]
        FastAPI + smolagents.ToolCallingAgent (Apache 2.0)
                 |
    +------------+---------------+------------------+
    |            |               |                  |
MiOSMCPClient  WebSearchTool  SkillCatalog       Letta memory
stdio →        SearXNG        GET :8640/         (Phase 1, T-077)
mios-mcp-server :8080         skills/openai-tools
(82 verbs +                   + static fallback
 18 recipes)
    |
    v
MIOS_AI_ENDPOINT (Law 5 — localhost:11450 or :11441)
```

### Component breakdown

| Component | File | Engine | LOC est. |
|---|---|---|---|
| HTTP gateway | `gateway-agent/server.py` | FastAPI + uvicorn | ~200 |
| Tool-loop | `gateway-agent/server.py` | `smolagents.ToolCallingAgent` | ~100 |
| Tool registry | `gateway-agent/tool_registry.py` | smolagents `Tool` subclasses | ~150 |
| MCP client | `gateway-agent/mcp_client.py` | `mcp.StdioServerParameters` (MIT) | ~100 |
| Session store | `gateway-agent/session.py` | pgvector JSONB `gateway_sessions` | ~80 |
| Skill catalog | `gateway-agent/tool_registry.py` | HTTP + static JSON fallback | ~80 |
| Web search | `gateway-agent/tool_registry.py` | smolagents `WebSearchTool` | ~30 |
| **Total** | | | **~740** |

### Config migration

The Hermes `config.yaml` + `config.local.yaml` override mechanism is replaced by a single `[gateway]` block in `mios.toml`:

```toml
# SSOT for mios-gateway-agent (Part 8, Phase 2)
# Replaces usr/share/mios/hermes/config.yaml
[gateway]
port               = 8642
model              = "mios-heavy"           # from [ai].model
max_tokens         = 16384
context_length     = 65536
max_steps          = 30
tool_loop_engine   = "smolagents"           # or "native" (pass-through)
mcp_refresh_seconds       = 300
skill_refresh_seconds     = 300
skill_catalog_static_path = "/var/lib/mios/skills/catalog.json"
searxng_url        = "http://mios-searxng:8080"
enable             = false                  # operator sets true before T-083 cutover

[gateway.worker]
port = 8643
# same engine/model; heavier swarm tasks
```

### Cutover gate (T-083)

`hermes-agent.service` is **masked, not removed** until all smoke tests pass. The `[gateway].enable = false` default ensures unupgraded installs continue running Hermes with no regression. Cutover is an explicit operator decision.

### Preserved Hermes features

| Hermes feature | Phase 2 equivalent |
|---|---|
| `/v1/chat/completions` gateway | FastAPI native |
| Tool-call loop | `smolagents.ToolCallingAgent` |
| MCP client (stdio) | `mcp` SDK `StdioServerParameters` |
| Skill catalog refresh | `GET :8640/skills/openai-tools` (same endpoint) |
| SearXNG web search | `smolagents.WebSearchTool` → `:8080` |
| Browser/CDP loop | `mios-pc-control` MCP verbs (already in tool surface via T-080) |
| Session persistence | pgvector `gateway_sessions` table |
| Self-editing skills (SKILL.md) | Delegated to Letta (Phase 1, T-077) |
| Context length management | `[gateway].max_tokens` cap (same logic as Hermes L89-94) |

---

## Part 8 quick-reference priority

**P2 (no disruption):** T-076 (GWY-01 Letta server) · T-077 (GWY-02 Letta memory wiring).
**P3 (strategic):** T-078 (GWY-03 FastAPI service) · T-079 (GWY-04 smolagents engine) · T-080 (GWY-05 MCP client) · T-081 (GWY-06 skill/search/browser) · T-082 (GWY-07 config migration) · T-083 (GWY-08 service cutover).

*Critical path: T-076 → T-077 (Phase 1). T-078 → {T-079 → {T-080, T-081}, T-082} → T-083 (Phase 2). T-083 requires all of T-078..T-082 smoke-test green. Phase 1 and Phase 2 are independent — Phase 2 does NOT depend on Phase 1 (Letta memory is a complement, not a prerequisite for the gateway).*

*Research evidence: hermes_replacement_research.md (2026-06-24) — NousResearch/hermes-agent (MIT + Nous Portal concern) · letta-ai/letta (Apache 2.0, GitHub) · huggingface/smolagents (Apache 2.0, GitHub) · mcp Python SDK (MIT) · MiOS config.yaml audit (usr/share/mios/hermes/config.yaml lines 53-59, 80-94).*

---


# Part 9: XDG + CephFS Unified User Storage Fabric (2026-06-25)

<!-- AI-hint: Additive. Architectural specification and phased implementation plan for unifying XDG Base Directory Specification, standard USER folders (xdg-user-dirs), and CephFS as the distributed POSIX storage fabric beneath MiOS. Aligns with the existing k3s+Ceph one-node-cluster path already present in the image (automation/13-ceph-k3s.sh, mios-ceph.container). Tasks: T-084..T-093 in TASKS.md. Does NOT replace pgvector (agent datastore stays separate per roadmap-snapshot-decomposition-2026-06-22.md §6). -->

*Source: MiOS storage fabric research (2026-06-25). Integrates XDG Base Directory Specification (freedesktop.org), standard user-dirs provisioning, and CephFS as the distributed POSIX layer beneath the MiOS home/user-state namespace. Bridges the existing `mios-ceph` / `mios-k3s` cluster path with a structured user-space storage contract.*

## Background and Scope

MiOS already ships the k3s + Ceph one-node-cluster path (`automation/13-ceph-k3s.sh`, `mios-ceph.container`, `cephadm`). The existing roadmap explicitly designates Ceph as the storage fabric for block, object, and file workflows while keeping PostgreSQL + pgvector as the agent-plane datastore (see `roadmap-snapshot-decomposition-2026-06-22.md §6`). What the existing roadmap does **not** yet specify is:

1. How the **CephFS file layer** maps to the standard Linux user-space directory conventions (XDG Base Directory Specification + `xdg-user-dirs`).
2. How that mapping is enforced, provisioned, and secured at session time.
3. Which parts of the XDG hierarchy must be **kept off** CephFS (the cache isolation rule).
4. How CephX authentication integrates with PAM session init to deliver per-user/per-tenant subvolumes.

This section provides the authoritative design-of-record for those four gaps and defines the concrete implementation tasks (T-084..T-093).

---

## Part 9 Architecture Overview

```
+---------------------------------------------------------------------+
|                    Applications / AIOS Agents                       |
|         (agent-pipe, Hermes, MCP verbs, GNOME apps, shells)         |
+---------------------------------------------------------------------+
                                 |
                                 v
              [ XDG Environment / /etc/profile.d/xdg-cephfs.sh ]
              (Maps $XDG_CONFIG_HOME / $XDG_DATA_HOME / $XDG_STATE_HOME
               to CephFS-backed $HOME; pins $XDG_CACHE_HOME to tmpfs)
                                 |
                                 v
             +-------------------------------------+
             |     Local VFS Namespace / autofs    |
             |   /home/<username>/  (CephFS bind)  |
             +-------------------------------------+
                                 |
                                 v
+---------------------------------------------------------------------+
|                    CephFS Kernel Client (ceph.ko)                   |
|               Direct RADOS I/O via kernel client (preferred         |
|               over ceph-fuse for latency; fuse as fallback)         |
+---------------------------------------------------------------------+
                                 |
                  +--------------+--------------+
                  |                             |
                  v                             v
   +--------------------------+   +---------------------------+
   | Metadata Pool (MDS)      |   | Data Pool (RADOS OSDs)    |
   | NVMe/SSD-backed          |   | Erasure-coded HDD for     |
   | (high iops for XDG small |   | bulk user data pools;     |
   |  file create/stat ops)   |   | SSD-layout for hot paths  |
   +--------------------------+   +---------------------------+
```

**Invariant (preserves existing Law 5 / agent datastore rule):** CephFS serves the *user-space* file hierarchy (`$HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`). The agent datastore (`mios-pgvector`, `:5432`) is a separate service that is **not replaced** by this fabric.

---

## 9.1 — CephFS Namespace Strategy for MiOS Multi-User / Multi-Tenant Layouts

### 9.1.1 Path Mapping

Rather than mounting the entire CephFS root, each user session mounts only its own subvolume. MiOS uses CephFS subvolume groups to enforce quota and layout boundaries at the storage level — independent of OS-level POSIX permissions.

| CephFS path | VFS mount point | Notes |
|---|---|---|
| `cephfs:/` | (not mounted on clients) | Root — admin / cephadm only |
| `cephfs:/tenants/<tenant_id>/` | (not mounted on clients) | Tenant namespace root |
| `cephfs:/tenants/<tenant_id>/users/<uid>/` | `/home/<username>/` | Per-user subvolume — PAM-provisioned |
| `cephfs:/tenants/<tenant_id>/shared/` | `/srv/mios/shared/<tenant_id>/` | Optional: shared data between tenant users |

In the MiOS single-operator (default) deployment: `tenant_id = "mios"`, `uid = the operator UID`. The path scheme is forward-compatible with future multi-tenant or multi-user buildouts without changing the user-space contract.

### 9.1.2 Subvolume Provisioning

CephFS subvolume groups (not raw directories) provide independent quota, layout, and access-path enforcement:

```bash
# Bootstrap (run once per cluster by cephadm / bootstrap script):
ceph fs subvolumegroup create cephfs mios-users
# Per-user provisioning (run by PAM script or mios-cephfs-provision):
ceph fs subvolume create cephfs <uid>-home --group_name mios-users \
  --uid <uid> --gid <gid> --mode 0700 \
  --pool_layout <data_pool>
```

### 9.1.3 Metadata vs. Data Pool Optimization

XDG-compliant application stacks generate high volumes of small files (lock files, atomic state updates, DBUS socket files, SQLite databases, config INI files). The MDS metadata pool must be provisioned for this:

- **Metadata Pool** (`cephfs_metadata`): backed by NVMe/SSD OSDs. MDS cache size `≥ 4 GiB` on the single-node cluster. Use `mds_cache_memory_limit` in `ceph.conf`.
- **Data Pool — hot** (`cephfs_data_hot`): SSD-layout for `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME`, `$XDG_STATE_HOME`, application runtime databases (SQLite, Flatpak app state).
- **Data Pool — bulk** (`cephfs_data_bulk`): erasure-coded HDD (or replicated HDD at single-node) for `Documents/`, `Videos/`, `Music/`, `Downloads/`, `Pictures/` — the `xdg-user-dirs` standard folders.

SSOT: `[storage.cephfs]` block in `mios.toml` (see T-084).

---

## 9.2 — Unifying XDG Specifications with CephFS-Backed Home Directories

### 9.2.1 Standard Environment Mappings

All XDG paths resolve relative to `$HOME`, which is the CephFS subvolume mount. The canonical profile script is deployed as `/etc/profile.d/mios-xdg-cephfs.sh` (baked into the bootc image, immutable under `/usr`):

```bash
# /etc/profile.d/mios-xdg-cephfs.sh — baked into bootc image (immutable)
# XDG paths resolve to CephFS-backed $HOME (default freedesktop.org values)
export XDG_CONFIG_HOME="${HOME}/.config"
export XDG_DATA_HOME="${HOME}/.local/share"
export XDG_STATE_HOME="${HOME}/.local/state"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"   # Always local — kernel-managed, never CephFS

# CRITICAL: Cache MUST NOT be on CephFS. See §9.2.2.
# Default: tmpfs at /run/user/<uid>/.cache (volatile, per-session).
# Operator override: set MIOS_XDG_CACHE_LOCAL_PATH in /etc/mios/install.env
export XDG_CACHE_HOME="${MIOS_XDG_CACHE_LOCAL_PATH:-/run/user/$(id -u)/.cache}"
```

### 9.2.2 The Cache Isolation Rule (Hard Constraint)

> **NEVER map `XDG_CACHE_HOME` to a CephFS directory.**

Applications write to `$XDG_CACHE_HOME` constantly with small, non-atomic I/O operations. Mounting this on CephFS causes:
- **MDS metadata storms**: thousands of `stat()` / `create()` / `unlink()` ops per session, spiking MDS CPU and cap-recall pressure.
- **File-lock conflicts**: applications using `fcntl` advisory locks on SQLite databases in `~/.cache` (e.g., Flatpak, web browsers) can deadlock or corrupt state if the client loses network connectivity to the Ceph cluster.
- **Latency amplification**: cache misses on small random-write paths incur network round-trips; browsers and package managers degrade to unusable speeds.

**Correct implementation**: `XDG_CACHE_HOME` → `tmpfs` at `/run/user/<uid>/.cache` (managed by `systemd-logind` via `RuntimeDirectory=`). Hot application caches that must survive reboot (e.g., browser profile databases) belong in `$XDG_DATA_HOME/<app>/`, not `$XDG_CACHE_HOME`.

For read-heavy workloads accessing CephFS data, use the Linux `fscache` / `cachefilesd` kernel caching layer (mount option `fsc`) — this provides transparent local-disk read caching without the write-path MDS amplification problem.

### 9.2.3 XDG_RUNTIME_DIR Isolation for Multi-Session Identities

If an agent identity runs across multiple concurrent sessions (e.g., MiOS agent-pipe forks a sandboxed code-exec sub-process), each session must have its own `XDG_RUNTIME_DIR`:

```bash
# Per-session isolation — set by systemd-logind or mios-session-init:
export XDG_RUNTIME_DIR="/run/user/$(id -u)/session-${MIOS_SESSION_ID}"
```

This prevents SQLite lock-file collision and atomic temp-file contamination between concurrent agent sessions sharing the same UID but different execution contexts.

---

## 9.3 — Provisioning Standard USER Folders (xdg-user-dirs on CephFS)

### 9.3.1 Session Init Workflow (Three-Stage)

**Stage 1 — CephFS Namespace Validation (PAM `pam_exec.so`)**

During authentication, a PAM exec script (`/usr/libexec/mios/mios-cephfs-provision`) validates that the user's CephFS subvolume exists. If absent, it provisions the subvolume and sets strict POSIX permissions (`0700`):

```
auth  → pam_exec.so /usr/libexec/mios/mios-cephfs-provision validate
      ↓ (creates subvolume if absent, sets ownership, verifies CephX keyring)
```

**Stage 2 — Mount Execution (systemd automount + autofs)**

The host system mounts the user's subvolume using the native Ceph kernel driver (`mount -t ceph`). The mount is triggered by `systemd.automount` on first `$HOME` access:

```
/etc/systemd/system/home-<username>.mount   (template: home-@.mount)
  What=<MON_ADDR>:6789,<MON_ADDR_2>:6789:/tenants/mios/users/<uid>
  Where=/home/<username>
  Type=ceph
  Options=name=client.<uid>,secretfile=/etc/ceph/keyring.d/client.<uid>,
           noatime,fsc,_netdev
```

Operator note: `fsc` enables `fscache` (transparent read-cache on local NVMe/SSD scratch); `noatime` eliminates access-time metadata writes. Both options significantly reduce MDS pressure on login-heavy workloads.

**Stage 3 — XDG Structure Compilation (`xdg-user-dirs-update`)**

After mount, the user session triggers `xdg-user-dirs-update` via the GNOME session or a systemd user unit. This evaluates `/etc/xdg/user-dirs.defaults` and creates standard folders directly inside the CephFS-backed home:

```
$HOME/
  .config/          → XDG_CONFIG_HOME (CephFS hot pool)
  .local/share/     → XDG_DATA_HOME   (CephFS hot pool)
  .local/state/     → XDG_STATE_HOME  (CephFS hot pool)
  Desktop/          → xdg-user-dirs   (CephFS bulk pool)
  Documents/        → xdg-user-dirs   (CephFS bulk pool)
  Downloads/        → xdg-user-dirs   (CephFS bulk pool)
  Music/            → xdg-user-dirs   (CephFS bulk pool)
  Pictures/         → xdg-user-dirs   (CephFS bulk pool)
  Videos/           → xdg-user-dirs   (CephFS bulk pool)
```

The `xdg-user-dirs.defaults` file is baked into the bootc image at `/etc/xdg/user-dirs.defaults` (immutable under `/usr`); overrides go in the user's `$HOME/.config/user-dirs.dirs` (writable CephFS).

---

## 9.4 — Key Engineering Challenges and Mitigations

### 9.4.1 POSIX Locks and Concurrent Agent Sessions

CephFS provides full POSIX file locking (`fcntl` advisory locks). However, if an agent identity runs concurrent tool calls across multiple `XDG_RUNTIME_DIR` contexts sharing the same `XDG_CONFIG_HOME`, SQLite databases or lock files in `$HOME/.config` can deadlock if:
- The CephFS network connection drops mid-lock (the kernel client holds the capability and the MDS cannot reclaim it until `client_reconnect_stale_interval` expires).
- Two agent-pipe dispatch workers race on the same config file.

**Mitigation A (implemented by T-086):** Each dispatched tool context gets a unique `XDG_RUNTIME_DIR=/run/user/<uid>/session-<session_id>` via `mios-session-init`. Runtime socket files and lock temporaries are written there, not to CephFS.

**Mitigation B (implemented by T-087):** Configure `[storage.cephfs].client_reconnect_stale_interval` (default `300s` in Ceph; lower to `30s` for interactive workloads) in `mios.toml`. This bounds the worst-case lockout window on network disconnect.

**Mitigation C (architecture):** The agent datastore (pgvector, `:5432`) does NOT run on CephFS. PostgreSQL manages its own WAL and POSIX advisory lock semantics. Only the *user-space home directory* is CephFS-backed.

### 9.4.2 Metadata Amplification on Login

A typical GNOME session login with a CephFS-backed `$HOME` triggers **2,000–8,000 `stat()` / `open()` / `getxattr()` operations** within the first 5 seconds (GNOME Shell, GVfs, Tracker, Flatpak, D-Bus service activation all walk `$XDG_DATA_HOME` concurrently). On a network filesystem this creates MDS cap-recall storms.

**Mitigation (T-088):** Enable aggressive client-side read-caching via CephFS capabilities:

```bash
# In /etc/ceph/ceph.conf (or mios-ceph.conf managed by mios.toml):
[client]
client_cache_size = 16384          # inode cache entries
client_cache_after_readdir = true  # hold dir caps after readdir
client_readahead_max_bytes = 33554432  # 32 MiB readahead
fuse_disable_pagecache = false     # keep page cache (kernel client only)
```

Additionally, the MDS should be granted sufficient memory: `mds_cache_memory_limit = 4294967296` (4 GiB) for the single-node MiOS cluster. This keeps the full `$HOME` metadata tree warm in the MDS cache after first login.

### 9.4.3 Multi-Tenant / Multi-Agent Access Control (CephX Capabilities)

For MiOS deployments with multiple operator users or agent identities, CephX authentication capabilities must be scoped to the individual user's subvolume path. This prevents cross-user snooping even if local POSIX permissions are temporarily misconfigured:

```json
// Example CephX user capability restriction (mios-cephx-policy.json, managed by T-089):
{
  "client.mios-user-1001": {
    "mds": "allow r, allow rw path=/tenants/mios/users/1001",
    "osd": "allow rw pool=cephfs_data_hot tag cephfs data=cephfs, allow rw pool=cephfs_data_bulk tag cephfs data=cephfs",
    "mon": "allow r"
  }
}
```

This is enforced at the **storage fabric layer** — even if the kernel client on the host has root access, the Ceph OSD daemons will reject operations outside the capability-granted path scope.

**Integration with MiOS CephX keyring management (T-089):** Per-user CephX keyrings are provisioned by `mios-cephfs-provision` during Stage 1 (§9.3.1) and stored in `/etc/ceph/keyring.d/client.<uid>` (mode `0400`, owned by the user). The firstboot script (`mios-cephfs-bootstrap.sh`) creates the initial `client.admin` keyring for the operator.

### 9.4.4 Bootc Image Immutability and CephFS Configuration

Under the MiOS bootc model, `/usr` is immutable and `/etc` is the operator overlay. CephFS configuration follows this split:

| File | Location | Mutability |
|---|---|---|
| Profile script (XDG env vars) | `/usr/share/mios/profile.d/mios-xdg-cephfs.sh` | Immutable (baked) |
| `user-dirs.defaults` | `/usr/share/mios/xdg/user-dirs.defaults` (copied to `/etc/xdg/`) | Immutable template; per-user override in `$HOME/.config/user-dirs.dirs` |
| Ceph cluster config | `/etc/ceph/ceph.conf` (operator overlay) | Mutable — operator-managed |
| Per-user CephX keyrings | `/etc/ceph/keyring.d/client.<uid>` | Mutable — provisioned by `mios-cephfs-provision` |
| Systemd automount units | `/etc/systemd/system/home-@.mount` + `.automount` (template) | Mutable — deployed by firstboot |
| SSOT knobs | `mios.toml` `[storage.cephfs]` block | Immutable vendor defaults; operator override in `/etc/mios/install.env` |

---

## 9.5 — mios.toml SSOT: `[storage.cephfs]` Block

All CephFS behaviour is controlled via a new `[storage.cephfs]` block in `mios.toml` (additive — no existing block is modified):

```toml
# Part 9: XDG + CephFS Unified Storage Fabric
# SSOT for mios-cephfs-provision, automount templates, and ceph.conf generation.
[storage.cephfs]
enable                          = false          # Operator sets true after cluster is live
cluster_name                    = "ceph"
monitors                        = ["127.0.0.1:6789"]   # Override with actual MON IPs in /etc/mios/install.env
fs_name                         = "cephfs"
tenant_id                       = "mios"                # Subvolume group name prefix

# Pool layout
metadata_pool                   = "cephfs_metadata"
data_pool_hot                   = "cephfs_data_hot"
data_pool_bulk                  = "cephfs_data_bulk"

# MDS tuning
mds_cache_memory_limit_gib      = 4
mds_session_cap_max             = 1024

# Client-side mount options (rendered into /etc/fstab / systemd .mount units)
mount_options                   = "noatime,fsc,_netdev"
client_cache_size               = 16384
client_readahead_max_bytes      = 33554432
client_reconnect_stale_interval = 30

# XDG cache isolation (MUST be local, NEVER CephFS)
xdg_cache_home_override         = "/run/user/{uid}/.cache"    # {uid} expanded at runtime

# Provisioning
subvolume_mode                  = "0700"
keyring_dir                     = "/etc/ceph/keyring.d"
provision_script                = "/usr/libexec/mios/mios-cephfs-provision"

# Automount
automount_enable                = true
automount_idle_timeout_s        = 600    # Unmount idle home dirs after 10 min
```

---

## 9.6 — Phased Implementation Plan

### Phase 1 — Foundation (Operator-gated, P2)

**Task T-084 (STRG-01):** Add `[storage.cephfs]` SSOT block to `mios.toml` (all defaults `enable=false`). Wire SSOT into `userenv.sh` as `MIOS_CEPHFS_*` env vars. Add drift-check in `38-drift-checks.sh` that validates `[storage.cephfs].monitors` is not the placeholder when `enable=true`.

**Task T-085 (STRG-02):** Build `mios-cephfs-provision` script (`/usr/libexec/mios/mios-cephfs-provision`). Subcommands: `validate` (called by PAM), `create` (idempotent subvolume + keyring provisioning), `delete` (revoke keyring + unmount + remove subvolume). Run `validate` as `pam_exec.so optional` in `/etc/pam.d/system-auth` — optional (degrade-open: if Ceph is not reachable, login proceeds with local `$HOME`).

**Task T-086 (STRG-03):** Implement per-session `XDG_RUNTIME_DIR` isolation in `mios-session-init`. Wire `MIOS_SESSION_ID` into the dispatch env so each `mios-agent-pipe` tool dispatch context gets a unique `XDG_RUNTIME_DIR`. Add `[storage.cephfs].xdg_cache_home_override` rendering into the `/etc/profile.d/mios-xdg-cephfs.sh` template.

### Phase 2 — Automount and User-Dirs (Operator-gated, P2)

**Task T-087 (STRG-04):** Deploy systemd automount template (`home-@.mount` + `home-@.automount`) for CephFS-backed home directories. Template is baked into the bootc image under `/usr/share/mios/systemd/`; firstboot activates it by copying to `/etc/systemd/system/` and running `systemctl daemon-reload`. Mount options sourced from SSOT.

**Task T-088 (STRG-05):** Tune CephFS client-side caching. Apply `client_cache_size`, `client_readahead_max_bytes`, and `client_reconnect_stale_interval` to `/etc/ceph/ceph.conf` via the `mios-ceph-configure` firstboot helper. Enable `fscache` mount option (`fsc`) for the bulk data pool on the kernel client. Validate: login `stat()` storm drops below 500 MDS ops/s.

**Task T-089 (STRG-06):** Implement CephX per-user capability management (`mios-cephx-policy`). On provisioning, `mios-cephfs-provision create` calls `ceph auth get-or-create client.<uid>` with path-scoped `mds` + `osd` caps (§9.4.3). Store keyring in `/etc/ceph/keyring.d/client.<uid>` (mode `0400`). On deletion: `ceph auth del client.<uid>`. Add `GET /v1/storage/cephfs/users` endpoint to `agent-pipe` exposing provisioned users and their keyring status.

### Phase 3 — XDG Profile + User-Dirs Integration (P3)

**Task T-090 (STRG-07):** Bake the XDG profile script (`mios-xdg-cephfs.sh`) into the bootc image under `/usr/share/mios/profile.d/`. Firstboot symlinks it to `/etc/profile.d/`. Content: sets `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME` (CephFS); pins `XDG_RUNTIME_DIR` and `XDG_CACHE_HOME` to `/run/user/<uid>` (local tmpfs). Renders `MIOS_XDG_CACHE_LOCAL_PATH` from `[storage.cephfs].xdg_cache_home_override`.

**Task T-091 (STRG-08):** Deploy `user-dirs.defaults` template (baked into bootc; `xdg-user-dirs-update` applies it on first GNOME session). Add a systemd user unit `mios-xdg-userdir-init.service` that runs `xdg-user-dirs-update --force` after the CephFS home mount is confirmed active (via `ConditionPathIsMountPoint=/home/%u`). Ensures standard folders (`Documents/`, `Downloads/`, etc.) are created in the CephFS bulk pool on first login.

### Phase 4 — Observability, Multi-Tenant Hardening, and Drift-Gating (P3)

**Task T-092 (STRG-09):** Add CephFS health checks to `greenboot`. Script `/etc/greenboot/check/required.d/55-mios-cephfs.sh` — verifies: (a) `ceph health ok` on boot; (b) `ceph df` shows data pool not at >90% capacity; (c) `ceph fs status` shows MDS `active`; (d) user `$HOME` mount is reachable. On failure, greenboot signals but does **not** roll back (degraded-open: local `$HOME` fallback is preferred over rollback). Log event to pgvector `event(kind="storage_health", source="cephfs")`.

**Task T-093 (STRG-10):** Add `check_cephfs_ssot` to `automation/38-drift-checks.sh`. Validates: (a) `[storage.cephfs].monitors` is not placeholder when `enable=true`; (b) `xdg_cache_home_override` does NOT contain a CephFS path prefix; (c) `data_pool_hot` and `data_pool_bulk` are distinct pools; (d) `provision_script` path exists in the image. Add documentation stub `usr/share/doc/mios/guides/cephfs-xdg-storage.md`.

---

## Part 9 Quick-Reference Priority

**P2 (operator-gated, no disruption to existing stack):**
- T-084 (STRG-01 SSOT block)
- T-085 (STRG-02 provision script + PAM)
- T-086 (STRG-03 XDG_RUNTIME_DIR session isolation)
- T-087 (STRG-04 automount template)
- T-088 (STRG-05 client-side caching tuning)
- T-089 (STRG-06 CephX per-user caps)

**P3 (XDG profile + user-dirs + observability):**
- T-090 (STRG-07 XDG profile script)
- T-091 (STRG-08 user-dirs template + init unit)
- T-092 (STRG-09 greenboot health checks)
- T-093 (STRG-10 drift-check + docs)

**Critical path:** T-084 → T-085 → {T-086, T-087} → T-088 → T-089 → T-090 → T-091 → {T-092, T-093}.
T-084 (SSOT) is the unblocker for all others. T-085 must exist before T-087 (automount) because the PAM hook fires before the mount unit.

*Key constraint preserved: `XDG_CACHE_HOME` is NEVER mapped to CephFS. All research confirms this is the single highest-risk misconfiguration in network-backed home directory deployments (MDS metadata amplification + POSIX lock conflicts). The SSOT drift-check in T-093 enforces this programmatically.*

*Research evidence: freedesktop.org XDG Base Directory Specification · Ceph documentation (docs.ceph.com) — CephFS subvolumes, CephX, fscache, MDS tuning · Red Hat Enterprise Linux storage admin guide · Fedora bootc + Podman Quadlets integration patterns · systemd.automount(5) + pam_exec(8) man pages · AIOS gap analysis §3 (storage management) · roadmap-snapshot-decomposition-2026-06-22.md §6 (Ceph as storage fabric, not agent datastore).*

---


# Part 10: Converged-Resource Architecture — AI Pipeline Simplification (2026-06-25)

<!-- AI-hint: Additive. Architectural transition plan from "Container-Per-Component" to "Converged-Resource" topology across four phases: (1) asyncio.Queue process merger of agent-pipe + gateway; (2) Single-Engine Multiplexing with llama-swap LRU + vLLM multi-LoRA; (3) sqlite-vec transient memory + zstd cold eviction; (4) Hummingbird distroless containers + rechunk OCI optimization. ALL changes uphold Law 5 (MIOS_AI_ENDPOINT via MIOS_AI_ENDPOINT at http://localhost:8080/v1) and Law 6 (UNPRIVILEGED-QUADLETS). Tasks: T-094..T-113 in TASKS.md. Does NOT decommission pgvector (agent SSOT datastore) — it remains the primary warm/hot semantic store. -->

*Source: MiOS Converged-Resource Architecture research (2026-06-25). Transitions the multi-service AI pipeline from network-hop-per-component topology to a consolidated, lower-overhead runtime while strictly preserving the two immutable architectural laws that define MiOS's AI plane: Law 5 (UNIFIED-AI-REDIRECTS — every inference call resolves through `MIOS_AI_ENDPOINT`) and Law 6 (UNPRIVILEGED-QUADLETS — all AI sidecars run as unprivileged Podman Quadlet units).*

---

## Part 10 Context: The Current "Container-Per-Component" Cost Model

The existing MiOS AI pipeline architecture is a horizontal chain of distinct services:

```
External clients (OWUI, Discord, Slack)
    │
    ▼
mios-agent-pipe (:8640)          [FastAPI + router + refine/critic/polish]
    │  HTTP hop (httpx, :8642)
    ▼
mios-hermes / mios-gateway-agent (:8642)    [tool-loop executor]
    │  HTTP hop (:11441 or :11450)
    ▼
mios-llm-heavy (:11441) ──or── mios-llm-light (:11450)   [llama-server via llama-swap]
    │  (optionally)
    ▼
mios-llm-heavy-alt (:11440)      [second heavy lane — SGLang or vLLM]
```

**Observable costs of this topology:**
1. **Double event-loop overhead**: Each hop from `:8640` → `:8642` → `:11450` involves a full `httpx` TCP stack: socket connect, HTTP/1.1 headers, response body buffering, deserialization. For a streaming chat turn, this means two socket pairs per token batch.
2. **Duplicate logging**: Both `agent-pipe` and `hermes-agent` emit span events to pgvector for the same request, doubling write I/O on every turn.
3. **VRAM multi-load tax**: `mios-llm-heavy` (`:11441`) and `mios-llm-heavy-alt` (`:11440`) each own separate `llama-server` processes. On a 24 GB 4090, running two full model processes wastes ≈ 3–6 GB of VRAM in process-level overhead alone (separate KV caches, separate GGUF maps).
4. **Container boot time**: Each Quadlet cold-starts its own Python `uvicorn` event loop + httpx session pool. A full restart of the AI plane touches 5+ distinct systemd units.
5. **MCP library duplication**: `agent-pipe` and `hermes-agent` each link their own `mcp` SDK client; tool schemas are fetched and cached independently.

The Converged-Resource Architecture addresses all five cost centres across four coordinated phases.

---

## 10.1 — Phase 1: Orchestration and Runtime Convergence (Process Merger)

### 10.1.1 The Gap

The `:8640` → `:8642` HTTP hop is a network-level abstraction for what is logically an in-process function call: "pick an action type, build a tool-call request, execute the tool loop, return the result." The gap is the absence of an `asyncio.Queue` seam that would let the orchestration logic call the tool-loop executor without leaving the Python process.

### 10.1.2 Research Findings

- **smolagents `ToolCallingAgent`** (Hugging Face, Apache 2.0) provides a structured tool-call loop that can be embedded inside `server.py` as a module-level singleton with no external server. It executes tools as direct Python function calls — the tool's `__call__` body replaces the HTTP POST to `:8642`.
- **`asyncio.Queue` producer-consumer** is the canonical pattern for eliminating in-process HTTP hops in FastAPI. A request handler puts a `(payload, future)` tuple onto a shared queue; a background `asyncio.Task` consumer picks it up, executes the tool loop synchronously (or via `asyncio.to_thread`), and resolves the future. The handler awaits the future.
- **The existing `mios_dispatcher.py` and `mios_kernel.py` modules** already implement the Kernel-facade routing + dispatch model for the router → dispatcher path. The Phase 1 work extends these modules with a `GatewayQueue` seam rather than a new HTTP service.
- **Degrade-open**: The `MIOS_GATEWAY_MODE` SSOT key controls which path is active. `queue` = in-process (new), `http` = the current `:8642` path (always-available fallback). Zero regression on existing deployments.

### 10.1.3 Architecture: Converged Gateway Loop

```
External clients (OWUI, Discord, Slack)
    │
    ▼
mios-agent-pipe (:8640) [SINGLE FastAPI process — enlarged]
    │
    ├─── Request router (mios_router.py)
    │         │  (action=agent / tool_call)
    │         ▼
    │    asyncio.Queue("gateway_queue")    ← NEW seam (replaces HTTP :8642 hop)
    │         │
    │         ▼
    │    GatewayWorker Task (smolagents ToolCallingAgent in-process)
    │         │  Direct Python call to mios_capreg tool functions
    │         ▼
    │    Tool execution (mios_sandbox bwrap, MCP verbs, shell)
    │
    └─── Response streaming back to client
    │
    ▼
MIOS_AI_ENDPOINT (http://localhost:8080/v1)   ← Law 5 unchanged
```

**hermes-agent.service** is retained as a deprecated-open compatibility shim: `MIOS_GATEWAY_MODE=http` in `/etc/mios/install.env` re-enables the HTTP route to `:8642`, ensuring zero-disruption rollback if the queue worker encounters an unexpected condition.

### 10.1.4 Key Implementation Contracts

1. **`GatewayQueue` module** (`usr/lib/mios/agent-pipe/mios_gateway_queue.py`, new): Contains `GatewayQueue` dataclass (holds the `asyncio.Queue`), `GatewayRequest` (payload + `asyncio.Future`), `GatewayWorker` (consumes queue, runs `smolagents.ToolCallingAgent`, resolves future). Pure module — no FastAPI globals.
2. **`server.py` wiring** (extend existing FastAPI `lifespan`): At startup, construct the `smolagents.ToolCallingAgent` with the `mios_capreg` tool registry; start the `GatewayWorker` as `asyncio.create_task(worker.run())`. At shutdown, cancel the task and drain the queue.
3. **`mios_dispatcher.py` extension**: Add `dispatch_via_queue(payload, queue)` alongside the existing `dispatch_via_http(payload, backend)`. `server.py` selects based on `MIOS_GATEWAY_MODE`.
4. **Logging deduplication**: The `GatewayWorker` emits a SINGLE `event(kind="tool_loop", ...)` span per request. The old per-service double-write is replaced by a single `mios_trace.span` call in the worker.
5. **SSOT**: `[converge.gateway]` block in `mios.toml` — `mode = "queue"` (default), `queue_maxsize = 64`, `worker_concurrency = 4`, `fallback_http = "http://localhost:8642/v1"`.

### 10.1.5 VRAM and Latency Impact

| Metric | Before (HTTP hop) | After (asyncio.Queue) |
|---|---|---|
| Overhead per streaming turn | 2 socket pairs + 2× header parse | 0 sockets; 1 `asyncio.Queue.put` |
| pgvector writes per turn | 2 (agent-pipe + hermes) | 1 (gateway worker) |
| Cold-start time change | 0 (hermes still loaded) | −0.4 s (no wait for `:8642` probe) |
| Rollback risk | — | Zero (MIOS_GATEWAY_MODE=http) |

---

## 10.2 — Phase 2: Inference Lane Consolidation (Single-Engine Multiplexing)

### 10.2.1 The Gap

Running `mios-llm-heavy` (`:11441`) and `mios-llm-heavy-alt` (`:11440`) as two separate llama-server or SGLang/vLLM processes means:
- **Separate VRAM allocations**: Each process independently maps the model weights. Two 14 B-class GGUFs = ≈ 16–20 GB of weight VRAM before any KV cache.
- **No shared prefix cache**: Requests to `:11441` and `:11440` cannot reuse each other's computed KV prefixes, even when processing identical system prompts.
- **No per-request adapter specialization**: Loading a fine-tuned LoRA for code vs. a general reasoning base model requires running two separate model processes.

### 10.2.2 Research Findings

**llama-swap LRU Multi-Model (current lane, extend):**
- `llama-swap` already provides a single-endpoint multi-model proxy (used in `mios-llm-light.yaml`). The `resident` group prevents swap storms on the hot chat+embed path.
- **LRU eviction** (`--models-max` flag on `llama-server ≥ b3800`): A single `llama-server` process can manage multiple GGUFs in VRAM with automatic LRU eviction when the VRAM limit is reached. This collapses the two `mios-llm-heavy` processes into one `llama-swap` proxy entry set per the existing `mios-llm-light.yaml` pattern.
- **Shared KV prefix cache** (`--cache-reuse N`): As of llama.cpp `b3800+`, slots that share a common prefix (e.g., the same system prompt) can reuse that prefix's cached KV tensors. Enable with `--cache-reuse 256` (minimum prefix match length in tokens). Reduces TTFT for system-prompt-heavy agent turns by 30–60%.
- **Prompt caching flags**: `--np 4` (parallel slots), `--system-prompt-file` (static system prompt pre-filled into every slot's KV prefix before the first request), `--slot-save-path` (already enabled in the current yaml).

**vLLM Multi-LoRA (heavy lane, upgrade path):**
- For the heavy lane (`mios-llm-heavy`), **vLLM `--enable-lora`** provides true per-request LoRA adapter injection without reloading the base model. Adapters are managed with LRU via `--max-cpu-loras`.
- **Dynamic loading at runtime**: `VLLM_ALLOW_RUNTIME_LORA_UPDATING=true` + `POST /v1/load_lora_adapter` allows adding new adapters without process restart.
- **LoRA resolver plugin** (`VLLM_PLUGINS=lora_filesystem_resolver`): The engine auto-discovers adapters from `/var/lib/mios/lora-adapters/` when a named model tag is requested. No explicit preload required.
- **Shared prefix caching**: vLLM's native block-based KV cache (PagedAttention) automatically deduplicates common prefixes across requests and adapters — a property the current per-process SGLang/vLLM pair lacks.

### 10.2.3 Architecture: Single-Engine Multiplexing

```
mios-llm-light (:11450)              [llama-swap proxy — ONE port]
│  resident group: {granite4.1:8b, lfm2:700m, nomic-embed-text}
│  LRU eviction: --models-max 3 (VRAM-budget-aware)
│  Shared prefix: --cache-reuse 256 on each chat model
│  LoRA: N/A (llama.cpp LoRA at startup only; see Note)
│
└─── REPLACES: mios-llm-light (:11450) + mios-llm-heavy-alt (:11440)
     when [ai].heavy_engine = "light"

mios-llm-heavy (:11441)              [vLLM engine — ONE port, multi-LoRA]
│  Base model: a single 14B+ GGUF / safetensors
│  --enable-lora + VLLM_ALLOW_RUNTIME_LORA_UPDATING=true
│  Adapters loaded from /var/lib/mios/lora-adapters/:
│     coding/   → qwen2.5-coder LoRA delta
│     reasoning/ → general instruct LoRA delta
│     vision/   → (future) visual grounding LoRA delta
│  Shared base-model VRAM: ~12 GB (one load, multiple adapters)
│
└─── REPLACES: mios-llm-heavy (:11441) + mios-llm-heavy-alt (:11440)
     [two separate containers → one vLLM container]
```

**Note on llama.cpp LoRA**: llama.cpp supports `--lora <path>` at startup only (not per-request dynamic). For the light lane, LoRA specialization is deferred to vLLM. The llama-swap `resident` group handles the multi-model case for the light lane via LRU GGUF swapping, not LoRA.

### 10.2.4 Updated mios-llm-light.yaml Additions

The additions to `mios-llm-light.yaml` to enable Single-Engine Multiplexing for the light lane (extending the existing file — no existing entries changed):

```yaml
# ── Phase 2: Single-Engine Multiplexing additions (Part 10, 2026-06-25) ──────
# Shared prefix caching: --cache-reuse 256 added to existing chat model cmds.
# Add to granite4.1:8b and lfm2:700m cmd lines (operator edit; see T-096).
# Example for granite4.1:8b:
#   --cache-reuse 256          # share KV prefix of len >= 256 tokens across slots
#   --np 4                     # 4 parallel slots (was 1; shared prefix supports this)
# The `resident` group (already in file) keeps all three models co-resident.
# No structural changes to existing model entries.

# ── vLLM heavy lane registration (replaces mios-llm-heavy-alt :11440) ────────
# The vLLM process is managed by mios-llm-heavy.container (Quadlet).
# llama-swap does NOT manage vLLM; the heavy lane resolver (mios_lanes.py)
# routes to it via MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY = http://localhost:11441/v1.
# mios-llm-heavy-alt (:11440) is DEPRECATED when [ai].heavy_engine = "vllm".
# See T-097 and T-098 for migration steps and the updated mios-llm-heavy.container.
```

### 10.2.5 VRAM Budget After Consolidation

| Before | VRAM | After | VRAM |
|---|---|---|---|
| `mios-llm-light` llama-swap (3 models co-resident) | ~6.7 GB | `mios-llm-light` (unchanged, + cache-reuse) | ~6.7 GB |
| `mios-llm-heavy` (SGLang, separate process) | ~12 GB | `mios-llm-heavy` (vLLM, multi-LoRA, shared base) | ~12 GB |
| `mios-llm-heavy-alt` (:11440, second process) | ~12 GB | ~~`mios-llm-heavy-alt`~~ (retired) | **0 GB** |
| **Total** | **~30.7 GB** ❌ over 24 GB | **Total** | **~18.7 GB** ✅ |

---

## 10.3 — Phase 3: Memory Tiering and Database Compaction

### 10.3.1 The Gap

The current `mios-pgvector` PostgreSQL instance (`:5432`) serves as both:
1. The **semantic memory store** (HNSW vector index, embedding-recall, hot workspace) — a correct and permanent function.
2. A **transient scratchpad** for ephemeral per-turn events, tool-call logs, and short-lived agent state that has no long-term value — a resource-intensive misuse.

Running PostgreSQL as a single-plane store for both hot semantic memory and throwaway scratchpad data means WAL write amplification on every transient event and a growing table that `mios_evict.py` must periodically sweep. On an edge device with limited NVMe, this is the primary source of database I/O contention.

### 10.3.2 Research Findings

**sqlite-vec (MIT/Apache-2.0, amontalenti/sqlite-vec):**
- Zero-infrastructure embedded vector search. Runs inside the Python process as a SQLite extension loaded via `sqlite_vec.load(conn)`.
- SIMD-accelerated (AVX/NEON): fast nearest-neighbor on up to ~1M vectors without a network round-trip.
- Supports `vec0` virtual tables with `float[N]` embedding columns; SQL query interface identical to pgvector's `<->` operator (cosine / L2 distance).
- **Ideal use case**: per-session scratchpad storage that is created at session start and destroyed (or compacted to cold storage) at session end. No pgvector schema changes required.
- **Hybrid retrieval**: SQLite FTS5 (already installed with SQLite) + sqlite-vec = keyword + semantic search within a single file, no external services.

**zstd-compressed JSONL cold storage:**
- Standard archival pattern (2026): export PostgreSQL rows as JSONL → compress with `zstd --level 10` → write to `/var/lib/mios/history/YYYY-MM-DD/<session_id>.jsonl.zst`.
- Decompression is cheap (zstd decode ≈ 1–3 GB/s on a 4090 host CPU): cold events can be queried on demand via `zstd -d` piped to `jq`.
- **PostgreSQL FDW query**: `CREATE SERVER cold_archive FOREIGN DATA WRAPPER file_fdw; CREATE FOREIGN TABLE event_archive (...)` allows SQL queries over cold `.jsonl.zst` files if the operator installs `pg_zstd_fdw` (optional; read-only access).

### 10.3.3 Architecture: Two-Tier Memory Model

```
TIER 0 — Process-local scratchpad (sqlite-vec)
│  Scope: single agent session, ephemeral
│  Storage: /run/user/<uid>/mios-session-<id>.sqlite (tmpfs)
│  Vector index: vec0 table, 768-dim (matches EmbeddingGemma-300m QAT)
│  Lifecycle: created at GatewayWorker task start; destroyed at session end
│  Contents: per-turn tool outputs, intermediate reasoning traces,
│             short-term episodic scratchpad (NOT persisted across sessions)
│
TIER 1 — Warm semantic workspace (mios-pgvector, :5432)
│  Scope: cross-session, long-lived semantic memory
│  Storage: /var/lib/mios/postgres/  (existing)
│  Vector index: pgvector HNSW 768-dim (existing schema)
│  Contents: knowledge base, satisfied outcomes, pinned memories,
│             embedding recall, cross-session goals
│  Eviction: existing mios_evict.py sweep (unchanged)
│
TIER 2 — Cold archive (zstd JSONL on /var/lib/mios/history/)
│  Scope: historical events, TTL-expired knowledge rows
│  Storage: /var/lib/mios/history/YYYY/MM-DD/<session_id>.jsonl.zst
│  Contents: evicted rows from Tier 1 (mios_evict.py cold-offload path)
│  Query: mios-cold-query CLI (zstd -d | jq) or file_fdw (optional)
│  Retention: configurable; default 90 days before deletion
```

### 10.3.4 Eviction Script Design (`mios_cold_evict.py`)

The new `mios_cold_evict.py` module extends `mios_evict.py` with a cold-export path:

```python
# mios_cold_evict.py — Phase 3 cold-offload extension (new module)
#
# Eviction flow:
#  1. Run mios_evict.plan_sweep() to identify TTL-expired / cap-overflow rows.
#  2. SELECT those rows as JSONL from PostgreSQL (SELECT row_to_json(t)).
#  3. Write to /var/lib/mios/history/<YYYY>/<MM-DD>/<session_id>.jsonl.tmp
#  4. Compress: subprocess(['zstd', '--level', '10', '-o', '<dst>.zst', '<tmp>'])
#  5. DELETE from PostgreSQL (existing mios_evict.delete_ids_sql).
#  6. Remove .tmp file.
#  7. Log event(kind="cold_evict", rows=N, dest=<path>) to Tier 1.
#
# Gate: [converge.memory].cold_evict_enable = true in mios.toml.
# Cold path is NEVER triggered for hot/pinned/satisfied rows.
# mios_evict.py is NOT modified; mios_cold_evict.py IMPORTS it.
```

### 10.3.5 sqlite-vec Integration in GatewayWorker

```python
# GatewayWorker session-scoped sqlite-vec scratchpad:
import sqlite3, sqlite_vec, tempfile, pathlib

_SCRATCHPAD_DIR = pathlib.Path(os.environ.get(
    "MIOS_SCRATCHPAD_DIR", f"/run/user/{os.getuid()}"))

async def _create_scratchpad(session_id: str):
    db_path = _SCRATCHPAD_DIR / f"mios-session-{session_id}.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS vec_scratch USING vec0(
        content TEXT,
        embedding float[768]
    )""")
    conn.commit()
    return conn, db_path

async def _destroy_scratchpad(conn, db_path: pathlib.Path):
    conn.close()
    db_path.unlink(missing_ok=True)
```

**Law 5 invariant**: the sqlite-vec scratchpad is a per-session write buffer only. All embedding calls still flow through `MIOS_AI_ENDPOINT/v1/embeddings` (the `nomic-embed-text` model on `:11450`) — sqlite-vec stores the resulting vectors, it does not generate them. The scratchpad is the write target, not the inference source.

---

## 10.4 — Phase 4: Tool Federation and Distroless Image Optimization

### 10.4.1 The Gap

**MCP client duplication**: `agent-pipe` and `hermes-agent` each import the `mcp` Python SDK and maintain independent MCP server connections. When Phase 1 merges these into a single process, the MCP client pool should also be unified — a single persistent MCP connection per server, shared across all tool invocations in the merged process.

**Container OS overhead**: The `mios-agent-pipe.container` Quadlet uses a Fedora-derived base that includes `dnf`, `bash`, `coreutils`, `systemd-udev`, and other OS utilities that are never used at runtime. These add ≈ 200–400 MB of unneeded layer data to the OCI image, inflating pull time and the attack surface.

### 10.4.2 Research Findings

**Unified MCP client pool:**
- Post-Phase 1 (single-process), a `MCPClientPool` dict (`{server_name: MCPClient}`) is initialized in the FastAPI `lifespan` and passed to the `GatewayWorker`. Connections are established once at startup; tool schemas are fetched once and cached.
- The MCP November 2025 spec's **Tasks primitive** (asynchronous, long-running workflows) aligns naturally with the `asyncio.Queue` design: a long MCP task enqueues to the gateway queue and the result is fetched later.
- **Unified A2A/MCP runtime**: `mios_interop.py` (WS-11, already present) implements the 3-projection A2A skill shape. Phase 4 wires `MCPClientPool` into `mios_interop.py` so A2A peer discovery and MCP tool calls share the same authenticated session. No new A2A client code needed.

**Distroless Hummingbird containers (`gcr.io/distroless/python3-debian13`):**
- Multi-stage `Containerfile` build: Stage 1 (builder) uses the full `python:3.13-slim` to `pip install` requirements into `/opt/venv`. Stage 2 (runtime) copies only `/opt/venv` and the app source into `gcr.io/distroless/python3-debian13` — no `dnf`, no `bash`, no package cache.
- **No shell**: distroless images have no `/bin/sh`. Observability (OpenTelemetry traces + pgvector `event` table) must cover all debugging surfaces. No `podman exec -it` interactive debugging in production.
- **Chainguard as Fedora-native alternative**: For Fedora-derived Quadlets, `cgr.dev/chainguard/python:latest-dev` (Wolfi-based, minimal, regular CVE updates) is the Fedora-adjacent distroless option for operators who need RPM-derived ABI guarantees.
- **rechunk for bootc image optimization**: The bootc base image is rechunked after each build via `rpm-ostree experimental compose build-chunked-oci --bootc`. This restructures OCI layers by RPM component groups, reducing the delta-pull size for updates. The AI sidecar layers (llama.cpp binary, Python venv) are assigned custom xattrs (`user.component=ai-sidecar`) to force them into their own dedicated OCI chunks.

### 10.4.3 Hummingbird Container Architecture

```
mios-agent-pipe.container (Hummingbird variant — Phase 4)
│
├─ Stage 1 (builder): python:3.13-slim
│   ├─ pip install fastapi uvicorn httpx smolagents sqlite-vec mcp ...
│   ├─ Output: /opt/venv (all Python deps)
│   └─ DOES NOT ship in final image
│
└─ Stage 2 (runtime): gcr.io/distroless/python3-debian13
    ├─ COPY --from=builder /opt/venv /opt/venv
    ├─ COPY usr/lib/mios/agent-pipe/ /app/
    ├─ ENV PATH="/opt/venv/bin:$PATH"
    ├─ USER 65534:65534   (nonroot UID — Law 6 UNPRIVILEGED-QUADLETS)
    ├─ EXPOSE 8640
    └─ CMD ["/opt/venv/bin/uvicorn", "server:app",
             "--host", "0.0.0.0", "--port", "8640",
             "--workers", "1", "--loop", "uvloop"]
```

**Law 6 contract**: The distroless runtime stage **must** set `USER 65534:65534` (the standard `nobody:nogroup` nonroot UID in distroless images). This is a hard requirement — building with `USER root` (even in the final stage) violates Law 6 and must cause a CI drift-check failure.

**Law 5 contract**: The `MIOS_AI_ENDPOINT` env var is propagated into the distroless container via the Quadlet's `Environment=` directive. The profile script (`mios-xdg-cephfs.sh`) is NOT executed inside a distroless container (no shell). The endpoint is hardwired via the Quadlet file, not sourced from a profile.

### 10.4.4 rechunk OCI Layer Strategy

For the MiOS bootc image, rechunking is applied post-build to minimize update bandwidth:

```bash
# In the CI/CD pipeline (after podman build):
podman unshare rpm-ostree experimental compose build-chunked-oci \
  --bootc \
  --format-version=1 \
  --from=$(podman inspect mios-bootc:latest --format '{{.Digest}}') \
  --output containers-storage:mios-bootc:rechunked

# Custom chunk assignment xattrs (applied to AI sidecar directories):
setfattr -n user.component -v ai-sidecar /usr/lib/mios/agent-pipe/
setfattr -n user.component -v ai-sidecar /usr/share/mios/llamacpp/
setfattr -n user.component -v llm-models /var/lib/mios/models/
```

This ensures:
- AI sidecar changes (Python code edits) only pull the `ai-sidecar` chunk, not the full OS layer.
- Model GGUF updates only pull the `llm-models` chunk.
- OS security updates only pull the base OS chunks.

---

## 10.5 — mios.toml SSOT: `[converge]` Block

All Converged-Resource behaviours are controlled via a new `[converge]` top-level section in `mios.toml` (additive — no existing blocks modified):

```toml
# Part 10: Converged-Resource Architecture (2026-06-25)
# All sub-keys default to the safe/backward-compatible no-op value.
# Operator enables phase-by-phase; all phases are independently gated.

[converge.gateway]
# Phase 1: Gateway Queue (process merger)
mode            = "http"          # "queue" = in-process; "http" = legacy :8642 (default)
queue_maxsize   = 64              # max pending requests in the asyncio.Queue
worker_concurrency = 4            # parallel GatewayWorker coroutines
fallback_http   = "http://localhost:8642/v1"   # used when mode="http" or worker fails

[converge.inference]
# Phase 2: Single-Engine Multiplexing
heavy_engine_mode = "dual"        # "dual" = current (two processes); "single" = vLLM multi-LoRA
vllm_lora_adapters_dir = "/var/lib/mios/lora-adapters/"
vllm_allow_runtime_lora = false   # set true + VLLM_ALLOW_RUNTIME_LORA_UPDATING=true
llama_cache_reuse_tokens = 0      # 0 = disabled; 256 = enable shared prefix caching
llama_parallel_slots     = 1      # increase to 4 with cache-reuse enabled
retire_heavy_alt         = false  # true = stop mios-llm-heavy-alt.container

[converge.memory]
# Phase 3: Memory Tiering
sqlite_vec_enable      = false    # true = per-session sqlite-vec scratchpad
scratchpad_dir         = "/run/user/{uid}"    # {uid} expanded at runtime
cold_evict_enable      = false    # true = export evicted pg rows to zstd JSONL
cold_storage_dir       = "/var/lib/mios/history/"
cold_retention_days    = 90       # delete cold archives older than this
cold_zstd_level        = 10       # zstd compression level (1-19; 10 = good balance)

[converge.image]
# Phase 4: Hummingbird Distroless
distroless_enable      = false    # true = agent-pipe built from distroless base
distroless_base        = "gcr.io/distroless/python3-debian13"
rechunk_enable         = false    # true = apply rechunk in CI post-build step
rechunk_format_version = 1
mcp_pool_enable        = false    # true = unified MCPClientPool in GatewayWorker
```

---

## 10.6 — Phased Implementation Plan

### Phase 1 — Gateway Queue (P2, operator-gated, zero regression)

**T-094 (CONV-01):** Add `[converge.gateway]` block to `mios.toml` (all defaults `mode="http"`). Wire into `userenv.sh` as `MIOS_CONV_GATEWAY_*`. Add `check_converge_gateway` stub to `38-drift-checks.sh`.

**T-095 (CONV-02):** Build `mios_gateway_queue.py` module: `GatewayQueue`, `GatewayRequest`, `GatewayWorker`. Integrate `smolagents.ToolCallingAgent` as the tool-loop engine. Wire into `server.py` `lifespan` (gated: `MIOS_CONV_GATEWAY_MODE=queue`). Add `dispatch_via_queue` to `mios_dispatcher.py`. Single-log deduplication (one `mios_trace.span` per request instead of two). Keep `dispatch_via_http` intact as fallback.

**T-096 (CONV-03):** Add `mios_gateway_queue.py` test suite (`test_mios_gateway_queue.py`). Cover: queue put/get, future resolution, fallback-to-http on worker exception, concurrency = 4, cancellation on shutdown. All tests pass without a running llama-server.

### Phase 2 — Single-Engine Multiplexing (P2, operator-gated)

**T-097 (CONV-04):** Add `--cache-reuse 256` and `--np 4` to `granite4.1:8b` and `lfm2:700m` cmd lines in `mios-llm-light.yaml`. Gate via `[converge.inference].llama_cache_reuse_tokens`. Validate: `ceph tell mds` (if applicable) and llama-server debug-slot logs show cache-hit rate > 60% on system-prompt-heavy turns.

**T-098 (CONV-05):** Build `mios-llm-heavy.container` Quadlet upgrade for vLLM multi-LoRA: `--enable-lora`, `--lora-modules coding=... reasoning=...`, `VLLM_ALLOW_RUNTIME_LORA_UPDATING=true`. Create `/var/lib/mios/lora-adapters/` directory structure. Add `[converge.inference].vllm_lora_adapters_dir` to SSOT. Gate: `heavy_engine_mode = "single"`.

**T-099 (CONV-06):** Add `POST /v1/inference/lora/load` and `GET /v1/inference/lora/list` endpoints to `agent-pipe server.py` — thin proxies to the vLLM `/v1/load_lora_adapter` endpoint. Respect Law 5: endpoint is sourced from `MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY`. Add drift-check: `retire_heavy_alt=true` MUST NOT be set while `mios-llm-heavy-alt.container` is still `enabled` in systemd.

**T-100 (CONV-07):** Document the `mios-llm-heavy-alt` retirement path. Add `[ai].heavy_engine = "vllm"` migration guide to `usr/share/doc/mios/guides/inference-consolidation.md`. Deprecation header added to `mios-llm-heavy-alt.container` (operator must explicitly set `retire_heavy_alt = true`).

### Phase 3 — Memory Tiering (P2, operator-gated)

**T-101 (CONV-08):** Add `[converge.memory]` block to `mios.toml`. Wire `MIOS_CONV_MEMORY_*` vars. Add `sqlite-vec` PyPI dependency to `requirements.txt` (agent-pipe). Add `mios_scratchpad.py` module: `create_scratchpad(session_id)`, `destroy_scratchpad(conn, path)`, `vec_insert(conn, content, embedding)`, `vec_search(conn, query_embedding, k)`. Pure module (no FastAPI globals).

**T-102 (CONV-09):** Build `mios_cold_evict.py` module: extends `mios_evict.py` with `export_to_cold(pg, rows, dest_dir, zstd_level)`. Writes JSONL, compresses with `subprocess(['zstd', ...])`, calls `mios_evict.delete_ids_sql` to remove from PostgreSQL, logs `event(kind="cold_evict")`. Gate: `[converge.memory].cold_evict_enable`. Adds `test_mios_cold_evict.py`.

**T-103 (CONV-10):** Wire `mios_scratchpad.py` into `GatewayWorker`: create scratchpad at task start, use it for per-turn tool-output caching (vec_insert after each tool call), destroy at task end. Gate: `[converge.memory].sqlite_vec_enable`. Validate: no pgvector writes for per-turn tool outputs (only the end-of-session synthesis is persisted to Tier 1).

**T-104 (CONV-11):** Add cold-archive retention sweep to the existing eviction background task in `server.py`. Sweep: find `.jsonl.zst` files in `cold_storage_dir` older than `cold_retention_days`, delete them. Log `event(kind="cold_retention_sweep", deleted=N)`. Add drift-check: `cold_storage_dir` must NOT be inside a CephFS mount path (cold archives are node-local, not distributed).

### Phase 4 — Hummingbird Distroless + rechunk (P3)

**T-105 (CONV-12):** Build `Containerfile.hummingbird` (new file alongside the existing `Containerfile`). Two-stage build: Stage 1 = `python:3.13-slim` builder; Stage 2 = `gcr.io/distroless/python3-debian13` runtime. `USER 65534:65534`. `CMD uvicorn`. Gate: `[converge.image].distroless_enable`. Add drift-check: final image layer must NOT contain `/usr/bin/dnf`, `/bin/bash`, or `/usr/bin/python3` outside `/opt/venv/`.

**T-106 (CONV-13):** Build `MCPClientPool` in `mios_gateway_queue.py` (extends T-095). Initialized in FastAPI `lifespan`, shared with `GatewayWorker`. Pool entry per MCP server name from `[tools.mcp_servers]` in `mios.toml`. Wire into `mios_interop.py` for A2A/MCP unified session. Gate: `[converge.image].mcp_pool_enable`. Add `test_mios_mcp_pool.py`.

**T-107 (CONV-14):** Add rechunk CI step to the MiOS build pipeline (`automation/build/rechunk.sh`). Runs `rpm-ostree experimental compose build-chunked-oci --bootc`. Applies `setfattr` xattrs to `ai-sidecar` and `llm-models` directories. Gate: `[converge.image].rechunk_enable`. Integrates with existing `just build` flow (appended, not replacing).

**T-108 (CONV-15):** Add drift-check suite for Phase 4: `check_hummingbird` in `38-drift-checks.sh`. Validates: (a) `USER 65534` in `Containerfile.hummingbird` final stage; (b) no `/bin/bash` in distroless layer manifest; (c) `MIOS_AI_ENDPOINT` is set in the Quadlet `Environment=` line when `distroless_enable=true` (profile.d is NOT available); (d) `rechunk_enable=true` requires `rpm-ostree` present in the build environment. Add `usr/share/doc/mios/guides/hummingbird-distroless.md`.

---

## Part 10 Quick-Reference Priority

**P2 (operator-gated, no disruption to existing stack):**
- T-094 (CONV-01 [converge] SSOT block)
- T-095 (CONV-02 GatewayQueue + GatewayWorker + smolagents wiring)
- T-096 (CONV-03 GatewayQueue test suite)
- T-097 (CONV-04 llama-swap cache-reuse + parallel slots)
- T-098 (CONV-05 vLLM multi-LoRA heavy lane upgrade)
- T-099 (CONV-06 LoRA load/list API endpoints)
- T-100 (CONV-07 heavy-alt retirement docs)
- T-101 (CONV-08 sqlite-vec scratchpad module)
- T-102 (CONV-09 cold eviction module + zstd export)
- T-103 (CONV-10 scratchpad wired into GatewayWorker)
- T-104 (CONV-11 cold-archive retention sweep)

**P3 (image optimization, longer horizon):**
- T-105 (CONV-12 Hummingbird distroless Containerfile)
- T-106 (CONV-13 unified MCPClientPool)
- T-107 (CONV-14 rechunk CI step)
- T-108 (CONV-15 Phase 4 drift-checks + docs)

**Critical path:** T-094 → T-095 → T-096 (Phase 1 complete) → {T-097, T-098 → T-099 → T-100} (Phase 2) → {T-101 → T-103, T-102 → T-104} (Phase 3) → {T-105, T-106, T-107 → T-108} (Phase 4).
T-094 (SSOT) is the unblocker for all phases. T-095 (GatewayQueue) must be complete before T-103 (scratchpad wiring). T-105 (distroless) depends on T-095 (merged process) and T-106 (MCPClientPool).

**Law 5 invariant (enforced throughout):** `MIOS_AI_ENDPOINT` remains the sole inference resolution point. The `asyncio.Queue` merger (Phase 1) does not change the inference backend — all completions still route through `MIOS_AI_ENDPOINT`. The sqlite-vec scratchpad (Phase 3) stores vectors but never generates them — embeddings are always fetched via `MIOS_AI_ENDPOINT/v1/embeddings`. The distroless container (Phase 4) receives `MIOS_AI_ENDPOINT` via the Quadlet `Environment=` directive, not via `profile.d`.

**Law 6 invariant (enforced throughout):** All new containers (`Containerfile.hummingbird`, upgraded `mios-llm-heavy.container`) run as `USER 65534:65534` (nonroot). The `[converge]` drift-check suite validates the USER line in every modified Containerfile. No privileged containers are introduced.

*Research evidence: smolagents ToolCallingAgent (HuggingFace, Apache 2.0, GitHub) · asyncio.Queue producer-consumer pattern (CPython docs) · llama.cpp `--cache-reuse` flag (llama.cpp GitHub, PR discussion b3800+) · vLLM multi-LoRA docs (vllm.ai — `--enable-lora`, `VLLM_ALLOW_RUNTIME_LORA_UPDATING`, `/v1/load_lora_adapter`) · sqlite-vec (amontalenti, MIT/Apache-2.0, PyPI `sqlite-vec`) · zstd + JSONL archival pattern (PostgreSQL community, crunchydata.com) · distroless containers (gcr.io/distroless/python3-debian13, Google distroless GitHub) · Chainguard wolfi-based Python images (cgr.dev) · rechunk / rpm-ostree `build-chunked-oci` (bootc-dev.github.io, redhat.com) · MCP November 2025 spec Tasks primitive (Anthropic / LF AAIF) · MiOS server.py (mios_dispatcher.py, mios_lanes.py, mios_kernel.py, mios_capreg.py, mios_evict.py audit 2026-06-25).*

---

# Part 11: Windows-11-Minimal Install Completeness + NO-HARDCODE Sweep (2026-07-04)

Grounded in a 4-agent read-only audit (2026-07-04) with live `file:line` evidence across
`C:\MiOS` (image + agent-pipe) and `C:\mios-bootstrap` (Windows installer). Two goals:
**(1)** the canonical `irm|iex` one-liner must take ANY fresh minimal Windows 11 machine to a
working MiOS with zero manual prerequisites; **(2)** enforce NO-HARDCODE -- every port/IP/host/
keyword-gate resolves from `mios.toml`/`mios.html` SSOT with a default. Task IDs T-120..T-130.

## WS-NOHC -- NO-HARDCODE / SSOT completeness

- **NOHC-01 (T-120) `[ports]` renumber drift [P1, systemic]** -- the keystone. `C:\MiOS` `[ports]`
  was renumbered into the 8xxx range (llm_light=8450, searxng=8899, open_webui=8033, pgvector=8432,
  cockpit=8090, forge_http=8300, sglang=8442, vllm=8441) -- confirmed live (`install.env`:
  `MIOS_PORT_LLM_LIGHT=8450`, lanes listen on 8450/8458) -- but code, docs, and
  `C:\mios-bootstrap\mios.toml` still use the OLD values (11450/8888/3030/5432/9090/3000/11441/40).
  Live symptom: `mios-doctor:62` probes a dead `:11450`. Reconcile to one authoritative table +
  a cross-repo `[ports]` drift-check.
- **NOHC-02 (T-121) port literals in code [P1]** -- 22 evidenced literal-port sites in libexec +
  agent-pipe + bootstrap (`mios-launch`, `mios-doctor`, `mios-coderun-broker`, `grounding.py`
  system-prompt text, `portal.py` served JS, wrong-default env fallbacks ...). Resolve each from
  `${MIOS_PORT_*}`; a good in-repo pattern already exists (`build-mios.ps1:5567-5575`).
- **NOHC-03 (T-122) unowned service ports [P1]** -- six named services (prefilter 8641, arbiter
  8650, oscontrol 11437, model_router 11442, daemon_agent 8644, mcp 8765) have NO `[ports]` key at
  all -- port lives only as a code literal. Add SSOT keys + `userenv.sh` bridge + configurator field.
- **NOHC-04 (T-123) baked operator identity [P1]** -- `MIOS_PUBLIC_HOST` defaults to a specific
  operator's Tailscale name `"mios.taildd86d0.ts.net"` in `portal.py:97` (portability + privacy).
  Purge it; source from `[portal].public_host`. Wire the endpoint env vars that restate ports
  (hermes/worker/heavy/vllm/a2a) to their SSOT keys; fix the orphaned `micro_*` bridge gap.
- **NOHC-05 (T-124) English keyword-gates [P1]** -- the router/classifier are clean and
  model-driven; 4 residual decision-gating English matchers remain: `chat.py:1301` temporal
  word-list (the surviving twin of an already-fixed `web_research.py:661` bug -- lift the fix),
  `routing.py:233` connective alternation (-> `[routing].compound_connectives`), `a2a_client.py:190`
  modality-by-substring, `mios_gateway_queue.py:114` param-type-by-name.
- **NOHC-06 (T-125) enforcement gap [P2]** -- `mios-hardcode-lint` checks only date-literals + BOM;
  the port drift-check scans only `.container` files. Port/IP hardcodes in `.py/.sh/.ps1` are
  UNENFORCED (that is how the 22 sites accumulated). Add a `check_code_ports_ips` gate with an
  SSOT allowlist.
- **NOHC-07 (T-126) SSOT hygiene [P3]** -- podman-subnet IP defaults (`globals.sh:214`) -> `[network]`
  keys; prune dead `userenv.sh` bridge rows (ollama/hermes_workspace); close configurator drift
  (`stack_id`, `hermes_worker/dashboard`, `[network.quadlet]`, `[a2a]` keys missing from `mios.html`).
  Note: `mios.toml` itself has NO missing defaults -- every empty value is intentional degrade-open;
  the gap is code bypassing/restating SSOT, not SSOT being incomplete.

## WS-WIN -- Windows-11-minimal install completeness

Already handled well (verified): WSL2 feature+kernel+v2, VMP/Hyper-V enable, BIOS-virt detection,
winget bootstrap, single up-front UAC elevation, ExecutionPolicy Bypass, adaptive disk shrink/clamp
(256->64 GB floor), WSL reboot-gate (idempotent re-run), the PS 5.1 `chcp 65001`/UTF-8/computed-glyph
path, and the historical BOM parse bug is FIXED.

- **WIN-01 (T-127) entry-path prereq fallbacks [P1]** -- on a winget-less minimal Win11 the one-liner
  dies: `Get-MiOS.ps1:6497 Require-Cmd git` hard-exits and git is winget-only; the PortableGit direct
  download exists only in `build-mios.ps1`, which runs AFTER the clone that needs git. Same for podman
  (`5141-5146 exit 1`). Add direct-download fallbacks BEFORE the fatal gates.
- **WIN-02 (T-128) early virt probe [P2]** -- move the virt-disabled check from `build-mios.ps1:8583`
  into `Get-MiOS.ps1` Pass-2 so a virt-off box fails BEFORE disk-shrink + reboot.
- **WIN-03 (T-129) podman-CLI-only + login autostart "service" [P2]** -- (proposed, captured as a task,
  reverted pending approval) default to Podman-for-Windows CLI (Desktop opt-in), and register a hidden
  AtLogon `MiOS-Autostart` task that `podman machine start`s the distro so systemd auto-starts every
  quadlet before the desktop -- the service-equivalent for a per-user WSL/podman context.
- **WIN-04 (T-130) residual hardening [P3]** -- Windows-side GPU host-driver check (no driver ->
  silent CPU fallback), `LongPathsEnabled`, explicit TLS 1.2, offline/proxy docs, and reconcile the two
  divergent "canonical" entry points (`Get-MiOS.ps1` vs `bootstrap.ps1`).
- **WIN-05 (T-131) zero-touch offline multi-user install via autounattend.xml [P2, strategic]** --
  SSOT-generate `autounattend.xml` (cschneegans MIT lib, pwsh 7.4, or a template personalized at
  FirstLogon) from an `[accounts]` list, so a fresh OFFLINE Win11 boots MiOS media -> all local
  accounts created (no MS-account), long-paths on, `M:\` carved + bloat stripped at the Setup layer,
  and a FirstLogon script fires `irm Get-MiOS.ps1 | iex` -> full multi-user MiOS with ZERO manual
  steps incl. OOBE. Subsumes the git/podman prereq gaps for the media path (moot inside first-logon)
  and dovetails with the multi-tenant direction. Passwords are first-boot-temporary (rotate on logon).

**Critical path:** T-120 (reconcile `[ports]`) is the unblocker for T-121/T-122/T-125. T-127 is the
unblocker for "install on ANY minimal Win11". NOHC and WIN streams are otherwise independent and
parallelizable. Each ships flag-gated + degrade-open; comments stay timeless; behaviour verified live.

*Research evidence: 4-agent read-only audit 2026-07-04 -- (a) hardcoded ports/IPs sweep of `usr/libexec/mios` + `usr/lib/mios/agent-pipe` + `C:\mios-bootstrap`, cross-checked vs `mios.toml [ports]` and live `install.env`; (b) English keyword-gate sweep of agent-pipe (~79K LOC) confirming the router/`classify.py`/`mios_routing` are model-driven+SSOT with only 4 residual gates; (c) `Get-MiOS.ps1`/`build-mios.ps1`/`preflight.ps1` fresh-Win11 flow trace; (d) `mios.toml` (10,424 lines) x `configurator/mios.html` (4,455 lines) x `tools/lib/userenv.sh` SSOT-coverage cross-reference. Enforcement precedent: `usr/libexec/mios/mios-hardcode-lint`, `check_container_ports`/`check_no_hardcode` in `automation/38-drift-checks.sh`. Fix-order law: model-driven > SSOT > unicode-aware > delete-dead.*

---


# Part 12: MiOS Custom Windows Editions — UUP + NTLite/DISM + autounattend ISO Program (2026-07-04)
*Source: operator direction to ship fresh MiOS-derived Windows install ISOs (incl. MiOS-XBOX) with FEATURE PARITY to the `irm|iex` installer. Extends Part 11 / WIN-05 (T-131) from "seed" to a delivered pipeline. Reference targets: operator-provided Xbox-Minimal NTLite presets + a Schneegans ExtractScript autounattend + `driver-extract.ps1`.*

The MiOS-XBOX.iso and the `irm|iex` installer are the SAME installer: both run `Get-MiOS.ps1` (the ISO nests it in FirstLogon; existing Windows runs it directly), and both apply ONE shared install-time provisioning core so they reach identical state — parity by construction. Delivered under `C:\mios-bootstrap\src\autounattend\` (commits `a034894..997ee2f`).

## WS-WISO — Custom Windows ISO pipeline (UUP Dump → customize → autounattend → ISO)
- **WISO-01 (T-132) shared provisioning core [P2] [DONE]** — `MiOS-Provision.lib.ps1`: single source of install-time provisioning (SSOT reader, hostname-gen, credentialed accounts, global branding/theme, strip-and-rebuild Linux-like layout, prefs) emitting plain `reg`/`mkdir` strings. Dot-sourced by all three generators so ISO + irm|iex never drift.
- **WISO-02 (T-133) NTLite preset sanitizer [P2] [DONE]** — `ConvertTo-MiOSPreset.ps1`: namespace-aware transform of an operator NTLite preset → MiOS-conformant (`MiOS-Xbox.xml`): MiOS naming/GUID/ISO label, SSOT hostname + accounts + AutoLogon, shared provisioning as `FirstLogonCommands` + nested `irm Get-MiOS.ps1 | iex`, **Posture B** (re-preserve WSL2/VMP/Hyper-V), 0 legacy identity refs, 280/282 debloat entries + all drivers preserved.
- **WISO-03 (T-134) Schneegans autounattend generator [P2] [DONE]** — `New-MiOSAutounattend.ps1`: SSOT → autounattend.xml; disk carve **C: = `[autounattend].c_partition_gb` (96 GB) + M:=remainder (MIOS-DEV)**; **pre-OOBE strip-and-rebuild** in the specialize pass (Schneegans DefaultUser default-hive context); TPM/SecureBoot/RAM bypass; oscdimg ISO inject; winutil `tools\` drop.
- **WISO-04 (T-135) existing-Windows parity path [P2] [DONE]** — `Invoke-MiOSProvision.ps1`: creates SSOT accounts + LIVE-applies the same global branding/layout/prefs the ISO bakes + long-paths, then chains the nested bootstrap. "During install" and "post install" converge.
- **WISO-05 (T-136) OEM driver export [P3] [DONE]** — `Export-MiOSDrivers.ps1` (`Export-WindowsDriver -Online` → SSOT dest) feeds NTLite Drivers / DISM `Add-WindowsDriver`.
- **WISO-06 (T-137) UUP-Dump source-ISO automation (`mios-uup-fetch`) [P2]** — wrap `rgl/uup-dump-get-windows-iso` (or `uup-dump/converter` + aria2 + `ConvertConfig.ini` from SSOT) to fetch a pinned, checksummed **25H2 x64** source ISO (26H1 is ARM64-only, see WEDITION-03).
- **WISO-07 (T-138) DISM-native debloat + oscdimg assembly + CI [P2]** — **[OPERATOR DECISION]** DISM-native (appx/capability/feature removal + LabConfig; free/reproducible) as the canonical path vs an NTLite-licensed CLI accelerator; then oscdimg dual BIOS/UEFI build → `MiOS-Win11.iso` / `MiOS-XBOX.iso`; GitHub-Actions: fetch → customize → assemble → VM smoke-boot.
- **WISO-08 (T-139) stage branding assets into the image [P2]** — place `mios-wallpaper.jpg`, `mios-logo.bmp`, Bibata `.cur/.ani`, Geist fonts at the referenced `C:\Windows\Web\MiOS\` / `%SystemRoot%\Cursors\Bibata-Modern-Classic\` paths so branding applies at first paint.

## WS-XBOX — MiOS-XBOX gaming edition (Xbox Mode out of the box)
- **XBOX-01 (T-140) Xbox Full Screen Experience out of the box [P2]** — enable Xbox Mode via `vivetool /enable /id:58989070,59765208` (2026 IDs; needs 24H2 26100.7019+ + Xbox app signed in, FSE = home launcher) + auto-launch. The operator reference's `unattend-01.ps1` used the WRONG (Copilot/taskbar) IDs — fix to the FSE IDs. Win+F11 launches it.
- **XBOX-02 (T-141) gaming loadout + Xbox tuning [P3]** — Xbox services Manual, Teredo/IPv6, Game Mode, Delivery Optimization, FSE regs; winget gaming apps (Steam/Vesktop/Zen) — adopt the reference `unattend-02/03.ps1`, sanitized (branding → MiOS OEM, never a personal/machine-specific name).
- **XBOX-03 (T-142) posture decision [P2]** — MiOS-XBOX gaming = Posture A (WSL purged, no local brain, remote/cloud MiOS) OR Posture B (keep WSL2 → local brain). Reference is Posture A; MiOS default = Posture B (keep the brain). Windows-side MiOS layer runs either way.

## WS-WBRAND — OS-wide MiOS branding/theme parity (Windows + Linux)
- **WBRAND-01 (T-143) global Windows branding [P2] [DONE]** — from SSOT (`[branding]`/`[colors].accent`/`[theme]`) to Default hive + HKLM + first HKCU: accent (#1A407F → AABBGGRR), dark theme + transparency, wallpaper + lockscreen (PersonalizationCSP), OEM info, **Dynamic Lighting RGB** (accent-tracking), **Geist** UI font (Segoe UI substitute), **Bibata** cursor scheme.
- **WBRAND-02 (T-144) Linux desktop palette parity via matugen [P2]** — generate GTK/Qt/Flatpak/base16 palettes from the SAME SSOT accent + wallpaper (matugen); Flatpak theming (`org.gtk.Gtk3theme` + `flatpak override`); Geist + Bibata system-wide on Linux; OpenRGB profile from the accent (Linux Dynamic-Lighting analog). Lives in mios.git / the deployed image, bridged to `mios.toml` SSOT.
- **WBRAND-03 (T-145) stage + re-assert [P3]** — Windows Dynamic Lighting reverts on some CU/feature updates → `mios update` re-asserts `Software\Microsoft\Lighting` + branding.
- **WBRAND-04 (T-162) SSOT living-wallpaper shader (self-authored, permissive) [P3]** — a GPU-accelerated animated **mesh-gradient** whose colors come from the SAME SSOT `[colors].accent`/`[colors].bg` that drive the static wallpaper + DWM accent + Linux palette. Prefer a ~40-line self-authored WGSL/GLSL fragment shader (no third-party license) or Apache-2.0 BabylonJS; **NEVER `firecmsco/neat` (MIT + Commons Clause forbids shipping-for-value in a distributed OS)**. Degrade-open ladder: animated shader → today's baked static gradient JPG → solid accent. Gated `[branding].living_wallpaper` (off by default; iGPU shader wallpaper burns power/thermals). Research: `research/mesh-gradient-living-wallpaper-2026-07-06.md`.
- **WBRAND-05 (T-163) Linux living wallpaper (GNOME layer / optional Quickshell) [P3]** — render the WBRAND-04 shader natively (Qt6 RHI→Vulkan/OpenGL on the Mesa iGPU — MiOS already ships `[packages.gpu-mesa]`), NOT WebGPU-in-browser. GNOME/Wayland has no native shader-wallpaper API → a tiny Wayland-background helper or MPV loop (`mpvpaper`); an optional Hyprland/Quickshell desktop profile can use a native `ShaderEffect` (refs: MIT `magetsu002/qs-wallpaper-picker`, `bjarneo/quickshell` `backgrounds`). Universal fallback = pre-rendered video loop.
- **WBRAND-06 (T-164) Windows animated background + SSOT keys [P3]** — MiOS-XBOX/MiOS-Win animated desktop background (borderless WebView2/D3D canvas at background z-order, OR a pre-rendered loop) from the same shader/palette; add `[branding].living_wallpaper` + `living_wallpaper_mode` (`shader|video|static`) to mios.toml + configurator. WebGPU-in-browser is the right host ONLY on Windows (WebView2/D3D12); Linux renders native (see WBRAND-05).

## WS-WEDITION — MiOS-derived Windows editions matrix
- **WEDITION-01 (T-146) editions SSOT [P2]** — an `[editions]` matrix (name / channel / arch / posture / debloat-profile / accent) so ONE pipeline emits MiOS (full, Posture B) + MiOS-XBOX (gaming) from SSOT.
- **WEDITION-02 (T-147) SSOT keys + configurator [P1]** — add `[autounattend]` (computer_name, c_partition_gb=96, bootstrap_url, iso_out/label, `[[accounts]]`), `[autounattend.layout]` (strip_defaults, strip_folders, linux_tree, lowercase_userfolders, strip_thispc), `[branding]` (oem_*, wallpaper, lockscreen, ui_font, cursor*, font_substitute) to mios.toml + expose in `configurator/mios.html`. Generators degrade-open to MiOS defaults until added.
- **WEDITION-03 (T-148) ARM64 / 26H1 handheld edition [P3]** — 26H1 is a Snapdragon-X2 ARM64 platform update (~Apr 2026), NOT x64. A `MiOS-XBOX-ARM` handheld edition (native Xbox FSE home) = separate ARM64 UUP source + ARM64 drivers/packages; the x64 gaming build stays on 25H2.
- **WEDITION-04 (T-149) fold reverting generated-file changes into the generator source [P2]** — `Get-MiOS.ps1`/`build-mios.ps1`/`mios.toml` regenerate ~every 12 min from upstream, wiping direct edits; fold podman-CLI-only + multi-user `MiOS-Autostart` + `[autounattend]`/`[branding]` SSOT keys into that generator source so they persist.

**Critical path:** T-132..T-136 DONE. T-147 (SSOT keys + configurator) unblocks operator tuning; T-137 (`mios-uup-fetch`) + T-138 (DISM/oscdimg + CI) unblock a reproducible end-to-end ISO build; T-142 (posture) + T-140 (Xbox Mode IDs) gate MiOS-XBOX behaviour. All degrade-open; provisioning is one shared core so ISO and irm|iex never diverge.

*Research evidence (2026-07-04): Schneegans generator (partitions "Size of system partition" + custom-diskpart data partition; folder provisions = Start/Desktop visibility + DefaultUser default-hive context, no native known-folder redirect; OneDrive under bloatware); UUP Dump 26H1 = ARM64-only Snapdragon platform update, x64 gaming → 25H2; Xbox Full Screen Experience ViVeTool IDs `58989070,59765208` (KB5083631, 24H2 26100.7019+); matugen cross-platform Material You (GTK/Qt/base16); Windows Dynamic Lighting `HKCU\Software\Microsoft\Lighting`. NTLite CLI is paid-only → DISM-native canonical. Delivered: `src/autounattend/` {MiOS-Provision.lib.ps1, ConvertTo-MiOSPreset.ps1, New-MiOSAutounattend.ps1, Invoke-MiOSProvision.ps1, Export-MiOSDrivers.ps1, autounattend.xml, MiOS-Xbox.xml}.*

## WS-ACCT — DB-driven GLOBAL account control plane (Linux + Windows; live, bidirectional)
*Source: operator directive — "all users are defined in mios.toml / mios.html / MiOS App and controlled and managed natively in the database; the DBs control BOTH Windows and Linux user + admin accounts; edits reflect the global environments LIVE and are managed via DB management surfaces that drive the OS account variables directly." Extends install-time `[[accounts]]` seeding (WISO-01/T-132, WEDITION-02/T-147) from one-shot provisioning to a LIVE control plane. Ships in the MiOS-XBOX custom Windows edition — its gaming-edition user/admin accounts are DB-managed identically to Linux.*

The pgvector `account` table is the RUNTIME SSOT for OS accounts. Setup/install seeds it from the mios.toml SSOT; thereafter the DB is authoritative and both OSes reflect DB edits live. A hard rule falls out of the current dashboard bug: the LOGIN account (`account.name`) is distinct from the operator DISPLAY name (`[user].name`) — the display name must NEVER land in a login/credential slot, and no consumer may resolve the login user from `MIOS_USER` / `[user].name`.

- **ACCT-01 (T-150) account SSOT schema + install-time seeding [P2]** — extend pgvector `account` (name == owner_user, kind `user|admin|service`, display, password_hash, uid/gid, groups + sudo/admin, os_targets `linux|windows|both`, enabled, meta) as the account SSOT; mios-bootstrap (Linux) + `Get-MiOS.ps1`/`MiOS-Provision.lib.ps1` (Windows) + configurator seed rows from mios.toml `[[accounts]]`/`[identity]`. Vendor default account = `user`/`user` until personalized via a DB surface. Purge the `MIOS_USER`=display-name leak from every consumer.
- **ACCT-02 (T-151) Linux: DB-native accounts via NSS + PAM [P2]** — `libnss-pgsql2` (NSS `passwd`/`shadow`/`group` served from pgvector) + `pam_pgsql` (PAM auth against the DB) so the DB IS the Linux account store, resolved live; a DB edit reflects with no re-provision. `nsswitch.conf` orders `files pgsql` so root/service accounts and a DB outage both degrade-open. Flag-gated (`[accounts].db_backed`).
- **ACCT-03 (T-152) Windows: DB→SAM live account-sync service [P2] [MiOS-XBOX]** — Windows has no NSS, so a MiOS account-sync service (PowerShell `LocalAccounts`/SAM provisioning + optional custom Credential Provider) watches the account SSOT and applies create/modify/disable/password to local SAM accounts live; auto-create-at-first-login from the DB. This is the MiOS-XBOX custom-Windows account path — gaming-edition accounts editable from the same surfaces as Linux.
- **ACCT-04 (T-153) DB management surfaces + consumer cutover [P2]** — mios.html/configurator + MiOS App expose account CRUD (add/edit/disable user & admin, set password, groups/sudo, per-OS targeting) writing the account SSOT; both OSes reflect live via ACCT-02/03. Cut consumers (both dashboards, cockpit PAM, forge) over to read the account SSOT, never `MIOS_USER`/`[user].name`.

*Research (2026-07-04): Linux — `libnss-pgsql2` NSS module replaces /etc/passwd,/shadow,/group with a PostgreSQL backend; `pam_pgsql` authenticates against it (NSS makes the user EXIST, PAM authorizes) — the canonical "DB is the account SSOT, live" mechanism. Windows — no NSS equivalent; local accounts live in the SAM (LSA-validated), so DB→OS is a sync service (PowerShell LocalAccounts / SAM APIs + custom Credential Providers, which can auto-create local accounts at first logon from an external store). Refs: libnss-pgsql, pam-pgsql, Microsoft Credential Providers + SAM/LSA docs.*

# Part 13: Advanced Multi-Agent Orchestration Strategies (2026-07-05)
*Source: operator-provided multi-vendor research digest (SSOT rationale → developer SSOT formats → multi-agent coordination) requested folded into roadmap/tasks/research. Full reality-check + MiOS mapping: `research/multi-agent-orchestration-strategies-2026-07-05.md`.*

MiOS already implements ~70% of this landscape (agent-pipe router+refine+council/swarm+critic, Hermes tool-loop, `delegation-prefilter`, A2A + `agent-passport.json` (Ed25519), MCP consume, pgvector shared memory, light/heavy lanes + `[ai.host_thresholds]`). These items are **enhancements/gap-fills to the existing plane**, not greenfield. **Provenance caveat:** the DCI / LDP / OpenClaw / IntrospecLOO protocols trace to single-author, post-cutoff arXiv preprints (`2603.xxxxx`) that are UNVERIFIABLE — same signature as the LAKE/ProbeLogits fabrications. The *concepts* are sound and mapped here; the *named papers* are evaluate-first, not authority. **Every item obeys Law 7:** flag-gated in `[agents.orchestration]`, **model-driven triggers (never keyword/English/ASCII gates)**, degrade-open, no magic weights.

## WS-MAO — Multi-Agent Orchestration strategy adoption (on the existing agent plane)
- **MAO-01 (T-154) typed handoffs + parallel guardrails + tracing spans [P2]** — model agent-pipe handoffs as typed transfer functions returning `{target_agent, Result(context-update)}`; run **input/output guardrails in parallel** (cheap model, can short-circuit); emit a **trace span per hop** (feeds the native-streaming mandate). Server-side `context_variables` dict hidden from the tool schema (no prompt pollution). *Verified pattern: OpenAI Agents SDK / Swarm.*
- **MAO-02 (T-155) structured deliberation for consequential tasks (DCI concept), MODEL-gated [P2]** — upgrade the council hop from free-form debate to archetype roles (Framer/Explorer/Challenger/Integrator via **differentiated system prompts** — bias, not hardcoded capability), a **typed interaction grammar** (propose/challenge/evidence/reframe/synthesize/concede…), **tension tracking** (disagreements preserved, never averaged away), and a bounded loop terminating in a **Decision Packet** (action + residual objections + minority report + reopen-conditions). **~62× tokens and HARMS routine tasks** → trigger is a **model-driven consequentiality classifier**, gated, default **off**. *Concept sound; source unverifiable — do not cite the paper.*
- **MAO-03 (T-156) document-mutation + LISTEN/NOTIFY coordination lane on pgvector [P3]** — decoupled, auditable async coordination: agents coordinate by mutating shared rows/docs; a pgvector `LISTEN/NOTIFY` (or logical-decode) event bus wakes decoupled worker/daemon agents on mutation. Permanent audit trail (every trigger = a row), reactive priority without polling, absolute decoupling. Reuses the datastore + MiOS-Daemon supervisor pattern. *OpenClaw concept, built on existing infra.*
- **MAO-04 (T-157) manifest-guided progressive-disclosure retrieval [P3]** — for large/longitudinal doc trees where one cosine distance collapses time+scope+type: organize as a tree with per-node natural-language `manifest`; retrieve via **LLM-select** traversal (reason over descriptions, prune subtrees) to a depth bound; manifest maintenance O(depth)/mutation. An *additional* retrieval strategy selectable per query-class, NOT a pgvector-recall replacement. *OpenClaw concept.*
- **MAO-05 (T-158) identity-aware delegation — extend agent-passport/A2A (LDP concept) [P2]** — add `reasoning_profile`/`context_window`/`cost_hint`/capability fields for **metadata-aware routing** (cheap-fast model → simple subtasks; heavy → hard reasoning), **attested-vs-claimed quality** to defeat the **Provenance Paradox** (routing on self-reported score selects the WORST delegates), **governed sessions** (persistent context, no per-call history re-send), **trust domains** (capability scopes / data-handling). Extends existing MiOS identity, not a new stack. *Concept sound; source unverifiable.*
- **MAO-06 (T-159) progressive payload / token-efficiency modes [P3]** — negotiate richest mutually-supported delegation payload: text (auditable fallback) → **semantic-frame (typed JSON, ~37% token cut claimed)** → embedding hints → semantic graph. Feeds the native-typed-args + streaming mandates; text fallback always kept for auditability. *LDP concept.*
- **MAO-07 (T-160) cheap contribution evaluation → reputation (IntrospecLOO concept) [P3]** — score each council/swarm agent's marginal contribution WITHOUT re-running the debate: post-session, prompt the remaining agents to re-decide ignoring agent *j*; delta ≈ leave-one-out at O(N) not O(T·N²). Feeds the `reputation` table (down-weight adversarial/negative agents, surface high-value ones). *Concept sound; source unverifiable.*
- **MAO-08 (T-161) selectable topology + debate protocol from SSOT [P2]** — make topology (pipeline/hierarchical/swarm/mesh) and debate protocol (within-round / cross-round / rank-adaptive) selectable per task-class from `[agents.orchestration]` + orchestrator judgement. Documented trade-off: within-round maximizes interaction but converges slowly; rank-adaptive cross-round converges fastest. No hardcoded choice. *Verified taxonomy.*

**Critical path:** MAO-01 (typed handoffs/guardrails/tracing) + MAO-08 (topology/protocol selection) harden the existing fan-out and are the base. MAO-05 (identity-aware delegation) extends the shipped agent-passport and defeats the provenance paradox — highest-value P2. MAO-02 (structured deliberation) is the biggest quality lever for consequential tasks but is token-expensive → strictly model-gated, default off. MAO-03/04/06/07 are P3 efficiency/robustness enhancers. Everything reuses agent-pipe + pgvector + A2A; every trigger is model-driven, gated, degrade-open (Law 7).

*Research (2026-07-05): full landscape + provenance reality-check in `research/multi-agent-orchestration-strategies-2026-07-05.md`. Verified-real: OpenAI Agents SDK + Swarm (handoffs / agents-as-tools / guardrails / tracing / context_variables), Anthropic MCP, LangGraph/CrewAI/Google-ADK, multi-agent-debate + creator-verifier + self-consistency, swarm/mesh/hierarchical/pipeline taxonomy. Unverifiable post-cutoff (concepts adopted, papers NOT cited as authority): DCI (arXiv 2603.11781), LDP (arXiv 2603.18043), OpenClaw-Hospital (arXiv 2603.11721), IntrospecLOO. MiOS already ships ~70% of this via the agent plane; Part 13 fills the deltas.*
