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

## Quick-reference priority order
**P0:** FED-G1 (operator-greenlight). **P1:** A1✅→A2✅→A3✅, FED-G2✅(+4-site follow-up), FED-G3, FED-G4, A4, C0→C1→C2, E1. **P2:** A5, B1, B2, C3, C4, D1, F1, G, FED-G6/G7/G8/G9. **P3:** the rest.

*Research evidence (this session's task outputs): location `wbzod13uf`, audit `wbkbuti2o`, pods `wuj7tswip`, agents `wuy193d96`, federation `w6i3l8oco`.*
