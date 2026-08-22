<!-- AI-hint: MiOS -- Master Tasks (SINGULAR monolith)
     AI-related: /etc/profile.d/mios-xdg-cephfs.sh, /etc/mios/ai/v1/caller-keys.json, /etc/mios/ai/v1/a2a-peers.json, /usr/share/mios/ai/v1/mcp.json, /etc/mios/ai/v1/mcp.json, /usr/libexec/mios/mios-mcp-server, /etc/mios/hermes/config.local.yaml, /etc/mios/gateway/, /usr/libexec/mios/mios-cephfs-provision, /etc/mios/llamacpp/mios-llm-light.yaml -->
# MiOS -- Master Tasks (SINGULAR monolith)

> The one canonical task list. **255 tasks** (189 closed, 66 open/in-progress). Absorbs the former `*-PLAN-*.md` + `concepts/*` backlogs. Each task carries **Who / What / Where / When / How** + Done-When.

| ID | Pri | Status | Domain | Title |
|---|---|---|---|---|
| T-001 | P0 | done-by-code | ? | FED-G1 -- Inbound Authentication Gate |
| T-002 | P1 | done-by-code | Boot/Image | BOOT-01 -- greenboot Health Check Scripts |
| T-003 | P1 | built-gated-off | Boot/Security | BOOT-02 -- OpenSCAP Image Compliance (oscap-im) |
| T-004 | P1 | done-by-code | Boot/Security | BOOT-03 -- Cryptographic Rootfs (composefs) |
| T-005 | P1 | done-by-code | Boot/Ops | BOOT-04 -- Podman Quadlet Auto-Generation from mios.toml |
| T-006 | P1 | done-by-code | Orchestration | A1 -- Unified `[agents.*]` Template + `_defaults` Inheritance |
| T-007 | P1 | done-by-code | Orchestration/CI | A2 -- Agent Schema Drift Validator |
| T-008 | P1 | done-by-code | Orchestration | A3 -- Fix opencode Gateway (`:8633` real output) |
| T-009 | P1 | done-by-code | Orchestration/Federation | A4/FED -- hermes-worker Boot Ordering |
| T-010 | P1 | done-by-code | Federation/Security | FED-G2 Follow-up -- Auth at All 4 Remaining Dispatch Sites |
| T-011 | P1 | done-by-code | Federation | FED-G3 -- Live Membership Reload |
| T-012 | P1 | done-by-code | Federation/Security | FED-G4 -- Self-Describing + Signed AgentCard |
| T-013 | P1 | done-by-code | Federation | FED-G5 -- LAN-Native mDNS Discovery (avahi) |
| T-014 | P1 | done-by-code | Federation/Security | FED-G6 -- Authenticated Inbound Delegation + Least-Privilege |
| T-015 | P1 | done-by-code | Ops/Pods | C0 -- code-server Port Remap `:8080` -> `:8800` |
| T-016 | P1 | done-by-code | Ops/Pods | C1 -- Add 7 `[pods.*]` Blocks to `mios.toml` |
| T-017 | P1 | done-by-code | Ops/Pods | C2 -- Attach `Pod=` to Members + Validate All Pods Healthy |
| T-018 | P1 | done-by-code | UX/OWUI | E1 -- Persist OWUI Location Fix (Firstboot Wiring) |
| T-019 | P1 | done-by-code | Scheduling/Kernel | SCHED-01 -- Turn-Boundary Preemption (PriorityGate + KV-Paging) |
| T-020 | P1 | done-by-code | Scheduling | SCHED-02 -- Token-Time Slicing Queue in agent-pipe |
| T-021 | P1 | done | Memory/Context | MEM-01 -- KV Slot-Save/Restore + `--swa-full` Guard |
| T-022 | P1 | built-gated-off | Federation | FED-CONSUME -- Light Up A2A/MCP Client Halves |
| T-023 | P2 | done-by-code | Observability | OBS-01 -- OTel GenAI Spans |
| T-024 | P2 | done-by-code | Orchestration | A5 -- Council Honesty: Report Single-Agent Mode |
| T-025 | P2 | completed | Kernel/Scheduling | A6 -- Kernel Stage-2 Hot-Path Migration [VM] |
| T-026 | P2 | done-by-code | Governance | B1 -- Flip Safe Governance Gates ON |
| T-027 | P2 | done-by-code | Memory | B2 -- Verify K-LRU Tiering Loop End-to-End |
| T-028 | P2 | done-by-code | Orchestration | ORCH-01 -- DCI 14-Act Deliberation Vocabulary |
| T-029 | P2 | built-gated-off | Orchestration | ORCH-02 -- DCI-CF Convergent Flow Critic (4-Persona Loop) |
| T-030 | P2 | done-by-code | Orchestration | ORCH-03 -- Dual-Ledger + Typed-Output Synthesis |
| T-031 | P2 | done-by-code | Orchestration | ORCH-04 -- ReAct+Reflexion Durable Loop + Checkpoint-per-Superst |
| T-032 | P2 | done-by-code | Security | SEC-01 -- Hermetic MCP Sandboxing (microVM per tool) [VM] |
| T-033 | P2 | built-gated-off | Security | SEC-02 -- Semantic Firewall (CaMeL-class Taint Propagation) |
| T-034 | P2 | done-by-code | Security/Audit | SEC-03 -- SHA-256 Cryptographic Event Bus Chaining |
| T-035 | P2 | done | Memory | MEM-02 -- Self-Editing Tiered Memory (MemGPT-style) |
| T-036 | P2 | done | Memory/Context | MEM-03 -- Context Compaction + Stale Tool Result Clearing |
| T-037 | P2 | done | Security/Orchestration | SEC-04 -- Per-Agent Access Control + HITL at MCP Chokepoint |
| T-038 | P2 | partial | Computer Use | CU-01 -- Computer-Use Action Hierarchy + Verify-After-Action |
| T-039 | P2 | done | Observability/Reliability | OBS-02 -- AIOS-Bench Harness (Task Accuracy x Systems Metrics) |
| T-040 | P2 | done | Observability | OBS-03 -- Record-and-Replay Determinism |
| T-041 | P2 | done-by-code | Ops/Networking | C3 -- De-publish searxng + Drop Heavy-Alt Stray Port |
| T-042 | P2 | done-by-code | Ops/Networking | C4 -- Port Collapse (Render PublishPort from `[ports]` SSOT) |
| T-043 | P2 | done-by-code | Federation/Edge | D1 -- Remote/Edge Agent Template + Auto-Join |
| T-044 | P2 | done-by-code | UX/RAG | F1 -- Re-vectorize OWUI Documentation Knowledge Collection |
| T-045 | P2 | done | Sandboxing | F2 -- Build the coderun-sandbox Image [NET] |
| T-046 | P2 | done-by-code | Documentation | WS-G -- MEMORY.md Honesty Reconciliation |
| T-047 | P2 | done-by-code | Orchestration | GAP-1 -- RouteMoA Pre-Synthesis Input Diversity Gate |
| T-048 | P2 | done-by-code | Scheduling/Orchestration | GAP-2 -- MOSAIC Confidence-Aware Aggregation Bypass |
| T-049 | P2 | done-by-code | Reliability | GAP-3 -- pass^k as Hard Skill-Promotion Gate |
| T-050 | P2 | done-by-code | Distribution/Edge | GAP-5 -- Rechunking Delta Distribution for Edge/Offline OCI Upda |
| T-051 | P2 | done-by-code | Federation | FED-G7 -- Route on AgentCard Skills |
| T-052 | P2 | done-by-code | Federation/Security | FED-G8 -- Caller-Key Store (`mios_principal` + CRL) |
| T-053 | P2 | done-by-code | Federation/Networking | FED-G9 -- Loopback-Default Bind + Scoped Publish |
| T-076 | P2 | retired | Memory/Gateway | GWY-01 -- Deploy Letta Server as Memory Complement (Phase 1) |
| T-077 | P2 | retired | Memory/Orchestration | GWY-02 -- Wire Letta Self-Editing Memory to agent-pipe Verbs (Ph |
| T-054 | P3 | done-by-code | Orchestration | ORCH-06 -- Deterministic Orchestration via Conductor CLI |
| T-055 | P3 | done-by-code | Memory | MEM-04 -- Hindsight Multi-Strategy Memory Engine |
| T-056 | P3 | done-by-code | Memory/Scheduling | MEM-05 -- KV Hierarchy + Sleep-Time Consolidation |
| T-057 | P3 | done-by-code | Memory/UX | ORCH-07 -- Personal Knowledge Graph Rich Edges |
| T-058 | P3 | done-by-code | Scheduling | SCHED-03 -- MLFQ Program-Level Scheduler (Autellix-style) [VM] |
| T-059 | P3 | done | Federation | DATA-01 -- Declarative Agent Specs + A2A-Discoverable Directory |
| T-060 | P3 | done-by-code | Memory/Data | DATA-02 -- Storage Versioning + Rollback for Self-Edited Core Fa |
| T-061 | P3 | done-by-code | Orchestration/Memory | ORCH-09 -- Code-Mode for Heavy Verbs/Recipes |
| T-062 | P3 | done-by-code | Self-Improvement | B3 -- Self-Improve ACT Half (Proposal + Commit) |
| T-063 | P3 | done-by-code | Orchestration | B4 -- promptver Consumer (Version-Resolved Prompt Registry) |
| T-064 | P3 | done-by-code | Self-Improvement/Security | GAP-4 -- DGM Formal Proof-of-Utility Sandbox for Self-Rewrites |
| T-065 | P3 | partial | Computer Use | GAP-6 -- smart_resize: Formal 3-Constraint Spatial Normalization |
| T-066 | P3 | done-by-code | Federation/Testing | B5 -- A2A Federation Loopback Smoke Test |
| T-067 | P3 | done-by-code | Ops/Config | B6 -- `expandvars` Over All `*_endpoint` Fields |
| T-068 | P3 | done-by-code | Data/Security | B7 -- Multi-Tenant RLS Wiring (`SET LOCAL mios.owner_user`) |
| T-069 | P3 | done-by-code | Ops/Build | C5 -- Pod-Gen in Build Render Step |
| T-070 | P3 | done | Documentation/Federation | D2 -- Pi/Edge Join Documentation |
| T-071 | P3 | done | UX | E2/E3 -- OWUI Cosmetic Fixes |
| T-072 | P3 | done | Sandboxing | F3 -- Code Mode `/run/coderun.sock` Per-Session Broker |
| T-073 | P3 | done-by-code | Ops/Computer Use | F4 -- mios build Driver + move_window + es.exe Upgrade |
| T-074 | P3 | done | Federation | FED-G10/G11 -- Cardless Join + `/v1/agents` Registry |
| T-075 | P3 | open | Scheduling/Data | H6 -- LAKE Federated Query (Spice.ai Rust Engine) |
| T-078 | P3 | done-by-code | Gateway/Orchestration | GWY-03 -- Build mios-gateway-agent FastAPI Service (Phase 2) |
| T-079 | P3 | done-by-code | Gateway/Orchestration | GWY-04 -- smolagents ToolCallingAgent as Tool-Loop Engine (Phase |
| T-080 | P3 | done-by-code | Gateway/MCP | GWY-05 -- MCP Client: stdio â†’ mios-mcp-server (Phase 2) |
| T-081 | P3 | done-by-code | Gateway/Tools | GWY-06 -- Skill Catalog + SearXNG + Browser Verb Pass-Through (P |
| T-082 | P3 | done-by-code | Gateway/Config | GWY-07 -- Migrate Hermes Config to mios.toml [gateway] SSOT (Pha |
| T-083 | P3 | partial | Gateway/Ops | GWY-08 -- Hermes ➔ mios-gateway-agent Service Transition (Phase  |
| T-084 | P2 | done | Storage/Config | STRG-01 -- CephFS SSOT Block in mios.toml |
| T-085 | P2 | done | Storage/Auth | STRG-02 -- mios-cephfs-provision Script + PAM Integration |
| T-086 | P2 | done | Storage/Orchestration | STRG-03 -- Per-Session XDG_RUNTIME_DIR Isolation |
| T-087 | P2 | done | Storage/Systemd | STRG-04 -- CephFS Automount Template (systemd.automount) |
| T-088 | P2 | partial | Storage/Performance | STRG-05 -- CephFS Client-Side Caching Tuning |
| T-089 | P2 | done | Storage/Security | STRG-06 -- CephX Per-User Capability Management |
| T-090 | P3 | done | Storage/UX | STRG-07 -- XDG Profile Script (mios-xdg-cephfs.sh) in bootc Imag |
| T-091 | P3 | done | Storage/UX | STRG-08 -- xdg-user-dirs Template + mios-xdg-userdir-init.servic |
| T-092 | P3 | done | Storage/Reliability | STRG-09 -- CephFS Greenboot Health Checks |
| T-093 | P3 | done | Storage/CI | STRG-10 -- CephFS SSOT Drift-Check + Documentation |
| T-094 | P2 | done-by-code | Config/Arch | CONV-01 -- [converge] SSOT Block in mios.toml |
| T-095 | P2 | done-by-code | Orchestration/Python | CONV-02 -- GatewayQueue Module + GatewayWorker + smolagents Wiri |
| T-096 | P2 | done-by-code | Testing | CONV-03 -- GatewayQueue Test Suite |
| T-097 | P2 | done-by-code | Inference/Performance | CONV-04 -- llama-swap Shared Prefix Cache + Parallel Slots |
| T-098 | P2 | done-by-code | Inference/vLLM | CONV-05 -- vLLM Multi-LoRA Heavy Lane Upgrade |
| T-099 | P2 | done-by-code | API/Inference | CONV-06 -- LoRA Load/List API Endpoints in agent-pipe |
| T-100 | P2 | done | Docs/Migration | CONV-07 -- mios-llm-heavy-alt Retirement Documentation |
| T-101 | P2 | done-by-code | Memory/Python | CONV-08 -- sqlite-vec Scratchpad Module |
| T-102 | P2 | done-by-code | Memory/Storage | CONV-09 -- Cold Eviction Module + zstd Export |
| T-103 | P2 | done-by-code | Orchestration/Memory | CONV-10 -- sqlite-vec Scratchpad Wired into GatewayWorker |
| T-104 | P2 | done-by-code | Storage/CI | CONV-11 -- Cold-Archive Retention Sweep + Drift-Check |
| T-105 | P3 | done    | Image/Security | CONV-12 -- Hummingbird Distroless Containerfile |
| T-106 | P3 | done-by-code | Tool/MCP | CONV-13 -- Unified MCPClientPool |
| T-107 | P3 | done-by-code | Image/CI | CONV-14 -- rechunk CI Step |
| T-108 | P3 | done    | CI/Docs | CONV-15 -- Phase 4 Drift-Check Suite + Documentation |
| T-031 | P1 | done     | Orchestration | ORCH-04 -- ReAct+Reflexion Durable Loop                         |
| T-109 | P1 | done | Observability/Orchestration | CHATQ-01 -- Refine/plan trace to reasoning channel + one-answer- |
| T-110 | P1 | done | Observability | FV-01 -- Canonical typed-event schema + per-surface routing + su |
| T-111 | P1 | done | Tool-calling | CHATQ-02 -- Constrained tool-calling + tools-on-final + verb-cat |
| T-112 | P1 | done | Tool-calling/Grounding | CHATQ-03 -- First-class list_dir verb + cwd act-before-answer gr |
| T-113 | P0 | done-by-code | Anti-Fabrication/Orchestration | FAB-01 -- @ agent-pipe FABRICATES tool execution + results (no r |
| T-114 | P0 | done-by-code | Anti-Fabrication/Grounding | FAB-02 -- pipeline fabricates web/news content + invents entitie |
| T-115 | P1 | done | Observability | CQ1 refine scaffold STILL leaking on CLI + redundant refine pass |
| T-116 | P1 | done | OS-Control | OSCTL-01 -- Hermes browser opens NEW WINDOWS instead of reusing  |
| T-117 | P1 | done | OS-Control | OSCTL-02 -- Hermes container-exec: stale container name + intera |
| T-118 | P1 | done-by-code | Inference/Reliability | HEALTH-01 -- mios-cpu-node + mios-llm-light Unhealthy (baked hea |
| T-119 | P1 | done | Tool-calling/OS-Control | TOOLARG-01 -- Native typed launch-arguments for ALL tools/skills |
| T-120 | P1 | done | SSOT/Ports | NOHC-01 -- Reconcile the `[ports]` SSOT renumber drift (8xxx) ac |
| T-121 | P1 | done | NO-HARDCODE/Ports | NOHC-02 -- De-hardcode port literals in libexec + agent-pipe cod |
| T-122 | P1 | done | SSOT/Ports | NOHC-03 -- Register the 6 unowned first-party service ports in ` |
| T-123 | P1 | done | NO-HARDCODE/Privacy | NOHC-04 -- Purge baked operator identity + wire endpoint env var |
| T-124 | P1 | done | NO-HARDCODE/Routing | NOHC-05 -- De-hardcode English keyword-gates in agent-pipe  [P1] |
| T-125 | P2 | done | CI/Enforcement | NOHC-06 -- Extend NO-HARDCODE enforcement to ports/IPs in code ( |
| T-126 | P3 | done | SSOT/Config | NOHC-07 -- SSOT hygiene: subnet IPs, dead bridge rows, configura |
| T-127 | P1 | done | Install/Windows | WIN-01 -- `Get-MiOS.ps1` entry-path prereq fallbacks (git + podm |
| T-128 | P2 | done | Install/Windows | WIN-02 -- Move the virtualization probe earlier (before disk-shr |
| T-129 | P2 | done | Install/Windows | WIN-03 -- Podman CLI-only default + optional Desktop, and a logi |
| T-130 | P3 | done | Install/Windows | WIN-04 -- Residual minimal-Win11 hardening (GPU driver / long-pa |
| T-131 | P2 | done | Install/Windows | WIN-05 -- Zero-touch offline multi-user Win11 provisioning via S |
| T-132 | P2 | done | Windows/Install | WISO-01 -- Shared install-time provisioning core (`MiOS-Provisio |
| T-133 | P2 | done | Windows/Install | WISO-02 -- NTLite preset sanitizer (`ConvertTo-MiOSPreset.ps1` - |
| T-134 | P2 | done | Windows/Install | WISO-03 -- Schneegans autounattend generator + 96 GB C: carve  ( |
| T-135 | P2 | done | Windows/Install | WISO-04 -- Existing-Windows parity path (`Invoke-MiOSProvision.p |
| T-136 | P3 | done | Windows/Install | WISO-05 -- OEM driver export for slipstream (`Export-MiOSDrivers |
| T-137 | P2 | done | Windows/Install | WISO-06 -- UUP-Dump source-ISO automation (`mios-uup-fetch`)  [P |
| T-138 | P2 | done | Windows/Install | WISO-07 -- DISM-native debloat + oscdimg assembly + CI  [P2] |
| T-139 | P2 | done | Windows/Install | WISO-08 -- Stage MiOS branding assets into the image  [P2] |
| T-140 | P2 | done | Windows/Gaming | XBOX-01 -- Xbox Full Screen Experience out of the box  [P2] |
| T-141 | P3 | done | Windows/Gaming | XBOX-02 -- Gaming loadout + Xbox tuning  [P3] |
| T-142 | P2 | done | Windows/Gaming | XBOX-03 -- MiOS-XBOX posture decision (A pure-gaming vs B keep-t |
| T-143 | P2 | done | Windows/Branding | WBRAND-01 -- Global Windows branding/theme from SSOT  [P2] |
| T-144 | P2 | pending | Linux/Branding | WBRAND-02 -- Linux desktop palette parity via matugen  [P2] |
| T-145 | P3 | done | Windows/Branding | WBRAND-03 -- Re-assert branding on Windows update drift  [P3] |
| T-146 | P2 | done | Windows/Install | WEDITION-01 -- Editions SSOT matrix  [P2] |
| T-147 | P1 | done | Windows/SSOT | WEDITION-02 -- SSOT keys + configurator for the ISO/branding sur |
| T-148 | P3 | done | Windows/Install | WEDITION-03 -- ARM64 / 26H1 handheld edition (`MiOS-XBOX-ARM`)   |
| T-149 | P2 | done | Windows/Install | WEDITION-04 -- Fold reverting generated-file changes into the ge |
| T-150 | P2 | completed | Data/Accounts | ACCT-01 -- Account SSOT schema + install-time seeding (pgvector  |
| T-151 | P2 | completed | Linux/Accounts | ACCT-02 -- Linux DB-native accounts via NSS + PAM (libnss-pgsql2 |
| T-152 | P2 | completed | Windows/Accounts | ACCT-03 -- Windows DB->SAM live account-sync service (MiOS-XBOX) |
| T-153 | P2 | completed | UI/Accounts | ACCT-04 -- DB account management surfaces + consumer cutover  [P |
| T-154 | P2 | pending | Agents/Orchestration | MAO-01 -- Typed handoffs + parallel guardrails + tracing spans   |
| T-155 | P2 | pending | Agents/Council | MAO-02 -- Structured deliberation for consequential tasks (DCI c |
| T-156 | P3 | pending | Agents/Coordination | MAO-03 -- Document-mutation + LISTEN/NOTIFY coordination lane on |
| T-157 | P3 | pending | Agents/Memory | MAO-04 -- Manifest-guided progressive-disclosure retrieval  [P3] |
| T-158 | P2 | pending | Agents/A2A | MAO-05 -- Identity-aware delegation: extend agent-passport/A2A ( |
| T-159 | P3 | pending | Agents/A2A | MAO-06 -- Progressive payload / token-efficiency modes  [P3] |
| T-160 | P3 | pending | Agents/Reputation | MAO-07 -- Cheap contribution evaluation → reputation (IntrospecL |
| T-161 | P2 | pending | Agents/Orchestration | MAO-08 -- Selectable topology + debate protocol from SSOT  [P2] |
| T-162 | P3 | done | Branding | WBRAND-04 -- SSOT living-wallpaper shader (self-authored, permis |
| T-163 | P3 | done | Linux/Branding | WBRAND-05 -- Linux living wallpaper (GNOME layer / optional Quic |
| T-164 | P3 | done | Windows/Branding | WBRAND-06 -- Windows animated background + SSOT living-wallpaper |
| T-165 | P2 | planned | SSOT/Cross-cutting | NAME-01 -- Global naming minification → one unified names/keys r |
| T-166 | P1 | planned | Install/Deploy/SSOT | DEPLOY-01 -- Install/first-boot reorder → eliminate "missing dep |
| T-167 | P2 | done | Tool-execution/Sandbox | SHELL-01 -- Persistent PTY / stateful shell substrate  [P2] |
| T-168 | P2 | planned | Security/Kernel | KENF-01 -- Tetragon eBPF/LSM kernel enforcement plane  [P2] [VM] |
| T-169 | P2 | planned | Security/Sandbox | ISOL-01 -- Per-action isolation tier ladder (promote-not-refuse) |
| T-170 | P1 | done-by-code | Computer-Use/Perception | GVLM-01 -- Activate grounding VLM + cu_act/cu_verify verbs  [P1] |
| T-171 | P2 | done | Orchestration/Judging | CONS-01 -- Weighted multi-judge consensus pipeline  [P2] |
| T-172 | P2 | done | Observability/Safety | CONS-02 -- JSD drift monitor  [P2] |
| T-173 | P0 | done | Autonomy/Safety | GUARD-01 -- Daemon runaway controls, FULLY implemented. `escalation_cooldown_s`/`escalation_max_attempts` were declared-and-dead (zero consumers); `_escalation_allowed()` now suppresses repeat escalation of the same concern inside the cooldown, parks it permanently at the attempt cap, keeps concerns independent, bounds its table and degrades open at cooldown<=0 -- applied at the refusal AND launch-verifier escalation sites. The host-pressure governor covered only 5 of 11 loops; the 6 that bypassed it (launch-verifier, fs-watcher, task-collector, index, satisfaction, rolling-report) now consult it, with fs-watcher still DRAINING inotify under pressure so the fd cannot overflow. `check_daemon_governor` (gate 160) makes it non-regressable: every autonomous loop must consult the gate, every [daemon] knob must have a real consumer (a mention in a comment or a test file does not count), and agent-pipe budget fallbacks must match the SSOT. 9-case + 7-case sibling tests, negative test. |
| T-174 | P0 | done | Autonomy/Scheduling | GUARD-02 -- Aggregate token/turn budget + background preemption. Verified ENFORCED end to end: `chat.py` admits autonomous work against `autonomous_max_inflight` with a pruned in-flight set and debits a rolling `window_s` bucket; `agent_call.py` trims history when `conversation_token_ceil`/`autonomous_token_ceil` are exceeded and caps dispatch depth. FIXED: chat.py's fallback defaults had drifted MORE PERMISSIVE than the SSOT (autonomous_token_ceil 1,000,000 vs 400,000; autonomous_max_inflight 2 vs 1), so a failed TOML read silently ran 2.5x the token ceiling and double the concurrency. Now equal, and `check_daemon_governor` fails any future drift. |
| T-175 | P1 | planned | Data/Durability | DURA-01 -- pgvector durability + exposure hardening. EXPOSURE AUDITED: the cluster binds `listen_addresses=127.0.0.1` on the `pgvector` port inside `mios-ai.pod` as uid 826 (not network-exposed), but its credential is `Environment=POSTGRES_PASSWORD=mios` in a WORLD-READABLE Quadlet -- and Law 11's enforcer never saw it, because it scans only `*.env`/`*secrets*` files for three hardcoded secret NAMES. A sweep found 7 such literals across units, including `WEBUI_SECRET_KEY=mios-stable-secret-change-me`. LANDED: `check_credential_literals` (gate 162) + `[security.credential_literals].grandfathered`, a SHRINK-ONLY registry -- the 7 are recorded, a NEW one fails the gate, and removing one without updating the list also fails. It distinguishes credentials from token COUNTS, boolean flags and `${VAR}` indirection (8-case sibling test + negative test). REMAINING for done: rotate the 7 into `/etc/mios/secrets.env` (0600) via `EnvironmentFile=`, which needs firstboot generation plus unit ordering AND a migration guard -- POSTGRES_PASSWORD only applies at initdb, so rotating it on an existing cluster locks the agent plane out of its own datastore. Needs a host to validate; not shippable blind. Durability (WAL/backup cadence) also still open. |
| T-176 | P1 | done | Security/Privacy | DURA-02 -- Secret/PII redaction on persist + federate. FEDERATE was already wired (a2a.py redacts every outbound task payload). PERSIST covered only 4 of the schema's 50 tables via a hardcoded tuple in `memory/pg.py`, leaving free-text sinks -- `scratch`, `session`, `gateway_sessions`, `fact_ledger`, `log_digest`, `kanban`, `tasks`, `mios_rag`, `skill_invocation`, `progress_ledger`, `pending_action`, `directory_entry`, `config_event`, `peer_reputation` -- writing raw. New `[security.redact]` SSOT classifies ALL 50 tables (18 redacted / 32 exempt, with structured key/config tables exempt because redaction would corrupt them, e.g. `agent_keypair.public_key_pem`). pg.py now reads the SSOT and FAILS CLOSED: a redaction error refuses the write instead of silently persisting raw text (CLAUDE.md: never persist secrets). `check_redact_coverage` (gate 161) fails any table classified in neither/both lists, any classified table absent from the schema, any free-text table dropped from the redact side, and any return to a hardcoded tuple. 8-case sibling test + negative test. |
| T-177 | P3 | planned | Memory/Filesystem | LSFS-01 -- Semantic-FS verbs + task-state protocol  [P3] |
| T-178 | P1 | in-progress | AI-plane/Inference/Deploy | HEAVY-01 -- provision the heavy dGPU model so the stated lanes d |
| T-200 | P2 | in-progress | Provisioning/AI-lanes | FBM-01 -- First-boot large-model provisioner (`mios-models-first |
| T-201 | P2 | done | SSOT/CLI | FBM-02 -- `[ai.firstboot_models]` SSOT + `mios models {list,sync |
| T-202 | P3 | done-by-code | Provisioning/Containers | FBM-03 -- Heavy-lane bound-images first-boot pull (`mios-bound-i |
| T-203 | P3 | planned | UI/Provisioning | FBM-04 -- Portal model-provisioning status tile + air-gapped pre |
| T-204 | P3 | done | Build/Offline | OFFL-01 -- Vendor external repo definitions (terra.repo)  [P3] |
| T-205 | P3 | done | Build/Offline | OFFL-02 -- Vendor desktop assets (Geist + Nerd fonts, Bibata cur |
| T-206 | P3 | done | Build/Offline | OFFL-03 -- Vendor k3s binary + k3s-selinux  [P3] |
| T-207 | P3 | done | Build/Offline | OFFL-04 -- Vendor hermes-agent source + pip wheels (`--no-index` |
| T-208 | P2 | done | Build/Offline/AI-lanes | OFFL-05 -- Vendor GGUF blobs + pre-pull llama-swap proxy image   |
| T-209 | P3 | done | Build/Offline | OFFL-06 -- Local rpm mirror image for fully-offline dnf  [P3] |
| T-210 | P2 | planned | Verification/Compute | IGPU-00 -- Wave-0 hardware verify probes (iGPU-WSL, heavy-lane 4 |
| T-211 | P2 | planned | Compute/AI-lanes | IGPU-01 -- In-VM iGPU compute lane; retire native `mios-igpu-ser |
| T-212 | P2 | planned | Compute/AI-lanes | IGPU-02 -- llama.cpp RPC fabric across lanes + coopmat2 verify   |
| T-213 | P3 | planned | RemoteDesktop/GPU | RDSK-01 -- Selkies (WebRTC + NVENC) GPU remote-desktop lane  [P3 |
| T-214 | P2 | in-progress | Packaging/WSL | WSL-01 -- Dual-personality `rootfs-export → wsl --import` pipeli |
| T-215 | P2 | planned | Lifecycle/Offline | WSL-02 -- bootc offline atomic upgrades (skopeo→oci→bootc switch |
| T-216 | P3 | in-progress | WSL/Supply-chain | WSL-03 -- `.wslconfig` / image hygiene + WSL self-verify cosign  |
| T-217 | P2 | planned | Standards/MCP | STD26-01 -- MCP `2026-07-28` wire adoption  [P2] |
| T-218 | P2 | in-progress | Standards/A2A | STD26-02 -- A2A v1.0.0 + signed AgentCard (JWS/JCS) + task-state |
| T-219 | P2 | planned | Standards/Federation | STD26-03 -- AGNTCY OASF Agent Directory + DID Agent Identity  [P |
| T-220 | P3 | planned | Durability/Memory | STD26-04 -- Durable event-sourcing over swarm/DAG + Memory-Block |
| T-221 | P3 | planned | Standards/HITL | STD26-05 -- Standards-based HITL (MCP elicitation SEP-2322 + A2A |
| T-222 | P2 | in-progress | Routing/Catalog | OAI-01 -- Unified multi-kind capability catalog (recipes + skill |
| T-223 | P3 | done-by-code | OpenAI-conformance | OAI-02 -- Tier-1 `usage` detail fields + strict function schemas |
| T-224 | P2 | done | OS-control/ACI | OAI-03 -- Persistent PTY/tmux stateful shell + PowerShell object |
| T-225 | P2 | done | Orchestration/Determinism | OAI-04 -- Run-template REPLAY-REUSE (intent-keyed zero-token DAG |
| T-226 | P3 | done | Scheduling | KACT-01 -- Wire batch-coalescing chokepoint (`mios_batch`)  [P3] |
| T-227 | P2 | in-progress | Routing/Cost | KACT-02 -- Remote SmartRouting + quality-gate + daily budget (`m |
| T-228 | P3 | done | Cost/Identity | KACT-03 -- Per-user quota keying + persistence on verified princ |
| T-229 | P3 | in-progress | Federation/Discovery | KACT-04 -- Gossip/DHT federated discovery transport (`mios_gossi |
| T-230 | P2 | done | Security/Sandbox | KACT-05 -- Per-verb risk-tier bwrap/seccomp ENFORCEMENT exec (`m |
| T-231 | P2 | planned/unverified | Lifecycle/Health | KACT-06 -- `Notify=healthy` + `HealthCmd` + rollback across AI q |
| T-232 | P3 | planned | UI/QML | UISHELL-01 -- Native QML Services/Swarm views (replace web-Porta |
| T-233 | P3 | planned | UI/QML | UISHELL-02 -- Login-prompt QML popup (`PortalData.login()`)  [P3 |
| T-234 | P3 | done | UI/Config | UISHELL-03 -- Reconcile `mios-webshell` AI-sidebar endpoint (`:3 |
| T-235 | P3 | planned | UI/Architecture | UISHELL-04 -- Cockpit native-vs-web decision  [P3] |
| T-236 | P2 | planned | SSOT/Identity | NAME2-01 -- Agent-plane user SSOT reconciliation (820/822 → 850) |
| T-237 | P3 | blocked | Naming | NAME2-02 -- Rename `mios-daemon-agent` agent-id → `daemon-agent` |
| T-238 | P3 | in-progress | Naming/Hygiene | NAME2-03 -- Mutable-state casing pass + `ContainerName=` audit   |
| T-239 | P3 | in-progress | Security/Boot | UKI-01 -- verity-rooted UKI build + fapolicyd enforce-promotion  |
| T-240 | P2 | in-progress | Data/Migration | A3F-01 -- Central-path legacy-datastore→pg primary flip + un-mirrored w |
| T-241 | P2 | done | OS-control/Windows | OSCTL2-01 -- hwnd-threaded target-window resolution for `pc_type |
| T-242 | P1 | done-by-code | AI-plane/SSOT/DB | VECTOR-00 -- V0 Foundation: unified DB + provenance + DB->TOML m |
| T-243 | P1 | completed | AI-plane/SSOT/DB | VECTOR-01 -- V1 Config read-path: DB becomes the runtime read (T |
| T-244 | P2 | completed | AI-plane/Vectorization | VECTOR-02 -- V2 AI-plane vectors: embed skill/verb/tool_call/eve |
| T-245 | P2 | planned | Build/Install/Xbox/DB | VECTOR-03 -- V3 Build catalog: package/build/xbox/debloat tables |
| T-246 | P2 | in-progress | Accounts/Identity/DB | VECTOR-04 -- V4 Accounts/users: DB-owned ids + prefs + bidirecti |
| T-247 | P3 | planned | SSOT/DB/Configurator | VECTOR-05 -- V5 Invert authority: DB=SSOT, TOML=generated export |
| T-248 | P1 | completed | Build/Bake | BAKE-01 -- `[build.bake]` core allow-list + bake-plan projection ( |
| T-249 | P1 | done | Build/Activation | BLADE-01 -- Universal-core + blade-type activation gate (`Conditi |
| T-250 | P1 | done | Build/Consolidation | MIOSSYS-01 -- mios-sys + mios-cuda shared-base consolidation (~18 |
| T-251 | P2 | done | SBOM/Provenance | SBOM-01 -- build-time provenance beyond images (model/pkg hashes) |
| T-252 | P2 | done | Release/CI | RELTOP-01 -- credential-driven registry selection (GHCR else Forg |
| T-253 | P2 | done-by-code | AI-plane/Deps | DEPRED-01 -- Hermes->agent-pipe collapse + sidecar consolidation |
| T-254 | P1 | planned | Deploy/Windows | MDRIVE-01 -- Hyper-V Gen 2 .vhdx off M: + sovereign Ceph OSD on M |
| T-255 | P1 | done | Docs/Meta | DOCS -- ADR system (done) + generated roadmap index + lean thematic roadmap + Diátaxis |
| T-256 | P1 | planned | Deploy/Cat | CAT-01 -- Flatten + single-owner: mios-bootstrap owns cat/, delete C:\MiOS dup |
| T-257 | P1 | planned | Deploy/Cat | CAT-02 -- Verb dispatch (stage/install/build/update/provision/manual) + tri-launcher parity |
| T-258 | P1 | planned | Deploy/Cat/SSOT | CAT-03 -- `[cat]` SSOT block + fix dangling drivepath/medicatver/cache_path reads |
| T-259 | P1 | planned | Deploy/Cat | CAT-04 -- Fold the web one-liners (irm\|iex ⇄ curl) into `cat install` |
| T-260 | P1 | planned | Deploy/Cat/Repo | CATREPO-01 -- Small MiOS-Repo shadow-config partition (always) + kickstart path fix |
| T-261 | P1 | planned | Deploy/Cat/Repo | CATREPO-02 -- Separate MiOS-Data bulk store (512GB+): OCI tar + artifacts |
| T-262 | P1 | planned | Deploy/Cat/Models | CATREPO-03 -- Model embedding + `cat provision` (Law 12 offline, zero-network heavy lane) |
| T-263 | P2 | planned | Deploy/Cat/Mirrors | CATREPO-04 -- Offline dnf/flatpak/pip mirrors on MiOS-Data + `cat update` self-refresh |
| T-264 | P2 | planned | Deploy/Cat/Flatten | CATFLAT-01 -- Dead-weight purge + leave-nothing-behind (drop bundled binaries) |
| T-265 | P2 | planned | Deploy/Cat/Docs | CATFLAT-02 -- ADR root breadcrumb (ADR.md + cat\ADR-0008.md) + spec cross-ref |
| T-266 | P3 | done-by-code | Deploy/Cat/SSOT | CATFLAT-03 -- mios.toml seed-copy consolidation (63/68 KB seeds vs 597 KB SSOT) |
| T-287 | P2 | done-by-code | Bootstrap/RAG | LOGBOOT-01 -- harden+complete `tools/log-to-bootstrap.sh`: purged-ollama `:11434` RAG snippet -> MiOS `/v1` lane (`:8642`, OpenAI-compatible); `--retry` on the example; `jq --rawfile` graph injection; SSOT endpoint. Producer follow-on = AGY-103 |
| T-267 | P1 | done-by-code | Config/Portal | CONFIG-01 -- Fold mios.html into the MiOS Portal at :8640/ (one web + API door) |
| T-268 | P1 | done-by-code | Build/SSOT/Version | DEBT-01 -- Collapse version/SSOT to one value (TD-2: 3x mios.toml + 0.2.4 root + 37x headers) |
| T-269 | P1 | done-by-code | Build/Security | DEBT-02 -- shellcheck CI gate + kill the 9 eval-on-agent-args verbs (TD-1) |
| T-270 | P1 | done-by-code | Dotfiles/SSOT | DOTFILES-01 -- [dotfiles.registry.*] + mios-dotfiles-render + apply verb + both-sides gate (ADR-0010) |
| T-271 | P1 | done-by-code | Build/Templates | TEMPLATE-01 -- Compiled file-pattern system + mios new + conformance check + Law-14 (ADR-0011) |
| T-272 | P1 | done-by-code | Build/Lang | LANG-01 -- Stand up Rust workspace + port first fragile bash tool (drift-runner/verb dispatcher) |
| T-273 | P2 | in-progress | AI-Plane/Refactor | DEBT-03 -- Split mios_dispatch.py + finish server.py decomposition (TD-5) |
| T-274 | P1 | done | Deploy/MiOS-Cat | CATREPO-FIX -- MiOS-Cat stages `repos/` onto the DATA partition instead of the REPO partition (WS-CATREPO, rel T-260). Repos (config/source clone) belong on the small always-present MiOS-Repo (E:); MiOS-Data is caches/models/user-DBs/deps ONLY. Fix the staging path in `cat/MiOS-Cat.bat` + `.ps1` so repos land on MiOS-Repo. **Done-when:** a fresh `cat stage` places `repos/` on MiOS-Repo, nothing repo-class on MiOS-Data, kickstart path aligned. |
| T-275 | P1 | done | UX/Branding, Lang | WALL-RUST -- Consolidate the WebView2 wallpaper host + the WSLg gui-watch daemon into ONE silent native **Rust** service (WS-LANG / Law 14): `wry` WorkerW host + `windows-service`, fold gui-watch, drop both `Run` keys (MiOSWallpaper + MiOS-GuiWatch), window never surfaces + no console flash. Compile via the now-provisioned Rust (Install-MiosRust). **Done-when:** login shows the wallpaper with zero visible windows/terminals; one auto-start service; Run keys gone. |
| T-276 | P1 | done | UX/Branding | WALL-BAKE -- Bake the reworked living-wallpaper (calm 16-colour ocean: pure blend, role-weighted proc, tamed highlights, zen pace, colour-spill-from-void intro, black bg, live theme sync) into MiOS-Xbox provisioning: regen `Get-MiOSLivingWallpaperHtmlB64` from the canonical `usr/share/mios/branding/living-wallpaper.html` + emit the `a0..a15` (mode-less) URL in `MiOS-Provision.lib.ps1`. **Done-when:** a freshly-flashed MiOS-Xbox desktop matches the live wallpaper exactly. |
| T-277 | P2 | done | Deploy/MiOS-Cat | XBOX-VIRTIO-VERIFY -- Confirm the virtio-win w11 guest drivers actually baked INSIDE `MiOS-Xbox.iso` (mount + inspect the injected driver subtree in the install media), not merely that the ISO is valid. **Done-when:** the w11 virtio (vioscsi/netkvm/viostor/ivshmem) tree is present in the baked image. |
| T-278 | P2 | done | UX/Branding | TASKBAR-ALIGN -- Taskbar reverted to LEFT-aligned; MiOS must pin the intended alignment. Set `HKCU\...\Explorer\Advanced\TaskbarAl` in the per-user branding (`Get-MiOSPerUserBrandingReg`) + Default hive so it survives updates/reprovision and is SSOT-driven (`branding.taskbar_align`). **Done-when:** taskbar shows the MiOS-intended alignment on every profile + after reprovision. |
| T-279 | P1 | done | Deploy/MiOS-Cat | CAT-XBOX-DEPLOY -- Harden the full MiOS-Cat -> MiOS-Xbox deploy path beyond the ISO build: audit every failure surfaced during flashing (repo/data partition placement T-274, autounattend/kickstart wiring, WinPE/DISM staging, Ventoy menu, boot). **Done-when:** a clean `MiOS-Cat` flash deploys a bootable MiOS-Xbox with repos on MiOS-Repo, drivers baked, and no manual fixups. |
| T-280 | P1 | done | Deploy/Reliability | SYSTEMPROFILE-DESKTOP -- Modal error on MiOS-Xbox: `C:\WINDOWS\system32\config\systemprofile\desktop is not accessible. Access is denied.` A process running as SYSTEM/systemprofile touches a non-existent Desktop folder. Fix: pre-create `%WINDIR%\System32\config\systemprofile\Desktop` (+ SysWOW64 mirror) in provisioning, AND/OR run the offending step (SetupComplete/task/service) as the interactive user not SYSTEM. **Done-when:** no such modal on boot/login. |
| T-281 | P1 | done | Deploy/Drivers | NET-DRIVERS-BAKE -- WiFi + LAN drivers NOT baked for most systems -> no network after MiOS-Xbox install on much hardware. Bake a broad NIC/WLAN driver pack into the image (offline `DISM /Add-Driver /Recurse` of a curated driver set) so common wired+wireless adapters work out-of-box. **Done-when:** mainstream Intel/Realtek/MediaTek WiFi+LAN come up on a fresh install with no network. |
| T-282 | P1 | done | Deploy/MiOS-PE | PE-DRIVER-INSTALLER -- MiOS-PE must ship a PORTABLE offline driver installer (e.g. Snappy Driver Installer Origin) among its portable apps, so missing WiFi/LAN drivers can be injected during staging/install without connectivity. (User: should already be present.) **Done-when:** MiOS-PE portable-apps menu includes a working offline driver installer. |
| T-283 | P0 | done | Deploy/MiOS-Xbox | XBOX-PROVISION-NOTAPPLIED -- Operator audit of the FLASHED MiOS-Xbox: the operator-supplied XMLs/autounattend branding is NOT applied. Desktop icons visible (XML said none); Start layout is default (no app pins, only Personal/Network/Settings/Explorer shortcuts); Start centered but SEARCH NOT VISIBLE; no taskbar pins; NO wallpaper at all; built-in static wallpaper NOT disabled. Root-cause why the preset/branding (ConvertTo-MiOSPreset + MiOS-Provision.lib.ps1 branding + the operator XMLs) doesn't reach the image. **Done-when:** a flashed MiOS-Xbox matches the operator XMLs (no icons, pinned Start layout, search visible, taskbar pins, living wallpaper, no static wallpaper). |
| T-284 | P0 | done | Deploy/MiOS-Xbox | XBOX-ACCOUNT-FLOW -- WRONG account+setup order: MiOS setup runs AFTER a visible desktop, logged into an auto-created `User` (User/user) account -- NOT the intended `MiOS-Sudo` (built-in Administrator). Accounts are not set up properly at all. Must: create the SSOT accounts (MiOS-Sudo=Administrator) in the autounattend, run MiOS provisioning during OOBE/SetupComplete (SYSTEM) BEFORE first interactive desktop, and NOT fall back to a default User/user. **Done-when:** first boot provisions on the built-in Administrator (MiOS-Sudo) before any desktop; no stray User/user account. |
| T-285 | P1 | done | Deploy/MiOS-Xbox | XBOX-MODE-NOTBAKED -- "Xbox Mode" (the gaming/Xbox edition feature set) is NOT baked into the MiOS-Xbox image. Ensure the Xbox-mode preset/features actually apply during the build. **Done-when:** a flashed MiOS-Xbox has Xbox Mode present. |
| T-286 | P1 | done | Process/Honesty | VERIFY-FLASHED-IMAGE -- Claims about MiOS-Xbox must be verified INSIDE the flashed image (mount install.wim / inspect the deployed system), never inferred from the live dev box or a valid-ISO check. Add a post-build image-audit step that asserts branding/accounts/wallpaper/Xbox-mode are actually present. **Done-when:** the build emits a verifiable provisioning-applied report from within the image. |
| T-294 | P1 | done | Docs/DocGen | DOCGEN-01 -- gate the corpus ledger and repair the landing predicate: `Policy.landing_min_word_ratio` wired from `[docs]` so `mios-manual landed()` stops raising, `check_manual_ledger` + negative test, ledger regenerated as the LAST step of `tools/sync-generated.sh`, both manual surfaces added to the Law-8 projection registry, `test_mios_comments.py` wired into the gate. **Done-when:** `ledger --check` green, landing ratio correct at the 0.90 boundary, ratchet held at ceiling without raising it. |
| T-303 | P2 | done | Docs/DocGen | DOCGEN-10 -- root `llms.txt` ownership resolved: mios.git now ships its OWN machine-readable index (Containerfile/automation/SSOT/quadlets/doc surfaces; installer entry points to mios-bootstrap's llms.txt), with `MIOS-GEN` markers for the what-MiOS-is boilerplate, all 16 laws and the 12 root exceptions (added to `[docs].render_extra`). The bootstrap mirror question dissolves: each repo indexes itself, divergence is now intentional (Law 15 justified). **Done-when (met):** mios.git's llms.txt describes mios.git; markers render idempotently. |
| T-302 | P2 | done | Docs/DocGen | DOCGEN-09 -- finish the manual rebuild: manual.md split into 51 authored chapter files under `usr/share/doc/mios/manual/ch*.md` (line-lossless, anchors preserved), manual.md reduced to intro + ToC + a derived chapter index; `llms-full.txt` de-rotted onto laws/root-exceptions/pipeline markers via the new `[docs].render_extra` scope; `usr/share/doc/mios/README.md` entry point landed earlier. `llms.txt` markers deferred to the T-303 ownership decision (Law 15). **Done-when (met):** `render --check` is idempotent-green and a hidden chapter file turns `check_manual_generated` red (third negative-test phase). |
| T-301 | P2 | done | Docs/DocGen | DOCGEN-08 -- the three remaining deriver families (`index:<glob>`, `related:<path>`, `api:<path>`), plus the second negative-test phase for `check_manual_generated` proving prose OUTSIDE a marker stays green -- without it the gate could be satisfied by a generator that owns a whole file, the exact failure the marker protocol exists to prevent. **Done-when:** all nine families render from the SSOT and the marker gate asserts both directions. |
| T-295 | P2 | done | Docs/DocGen | DOCGEN-02 -- durable ratchet floor (`coverage --write-floor` + low-water mark) so a lowered ceiling cannot be silently raised back; monotone gate currently compares only against HEAD and exits 0 when the previous TOML will not parse. **Done-when:** lowering then raising a ceiling in one commit fails the gate. |
| T-296 | P1 | done | Docs/DocGen | DOCGEN-03 -- `mios-manual harvest`, the missing link: move a MIGRATE comment block into an authored doc passage, stamp the `mios-src:<sha12>` anchor, fill the ledger's landed_* columns. **Done-when:** a harvested block flips `landed()` false->true and the narrative count falls by one. |
| T-297 | P1 | done | Docs/DocGen | DOCGEN-04 -- `check_comment_landing` + `mios-manual prune`: delete a source comment only once its knowledge is provably landed. **Done-when:** prune refuses when the predicate is false; round-trip covered by a test. |
| T-298 | P2 | done | Docs/DocGen | DOCGEN-05 -- widened render scope to every tracked `.md` and added four deriver families (pipeline, verbs, root-exceptions, boilerplate), taking the set from 2 to 6; unknown deriver ARGs now fail loudly via `DeriverError` instead of silently rendering everything. **Done-when:** each family renders from the SSOT and is drift-gated. Remaining families (index/related/api) and the marker-scope negative-test phase split out as T-301. |
| T-299 | P2 | done | Docs/DocGen | DOCGEN-06 -- de-rot the shipped manual: its law section is now a MIOS-GEN marker interior derived from `[laws]` (it claimed seven laws against a registry of sixteen, and two Law-6 root exceptions against twelve), 154 retired `:8642` endpoint literals replaced with the NAME `MIOS_AI_ENDPOINT`, 50 `file:///C:/MiOS/...` links rewritten repo-relative, and the `just manual` target retired because its generator owned the whole file and dropped the H1/ToC/markers. **Done-when:** no retired port literal, Windows path or hand-written law list remains in manual.md, and render is idempotent over it. Full authored-chapter rebuild + llms.txt marker treatment split out as T-302. |
| T-300 | P2 | done | Docs/DocGen | DOCGEN-07 -- cross-repo participation: run the doc CLIs against `mios-bootstrap.git` by root (69 of its 98 taggable files already carry AI-hints, but it ships no docgen tooling) without duplicating any tool across repos (Law 15). **Done-when:** one command documents either repo. |
| T-288 | P1 | done | Security/Upstream | UPSTREAM-01 -- float the last hand-pinned image refs: pgvector `0.8.3-pg17` -> the `pg17` family tag (resolves newest every build), and k3s -> `v1.36.3-k3s1` since it publishes no usable channel tag and its version-shaped tag feeds the k8s-repo-minor derivation. **Done-when:** no hand-pinned pgvector version remains in `[image.sidecars]`, `[build.bake].core`, the Quadlet, plan.d or any generated twin, and its `check_version_ssot` literal exemption is withdrawn. |
| T-289 | P1 | done | Security/Upstream | UPSTREAM-02 -- derive the `mios-resolve-latest` ref list from `[image.sidecars]` instead of a hand-mirrored array (four refs had silently drifted: `pg16`, `valkey:8.0`, `ceph:v18`, `open-webui:latest`). **Done-when:** deleting a ref from the SSOT changes the resolver's set with no script edit; a parity drift-check covers the surface. |
| T-290 | P2 | done | Security/Upstream | UPSTREAM-03 -- Renovate customManager for the exact-pinned `[image.sidecars]` entries so the SSOT's "Bump via Renovate" comment becomes true. **Done-when:** a stale exact pin (pgvector, k3s) produces a Renovate PR; float `:latest`/`:main` refs stay unmanaged. |
| T-291 | P2 | done | Security/Upstream | UPSTREAM-04 -- warn-tier greenboot probe asserting the booted kernel honors the `lockdown=integrity` karg the image declares. **Done-when:** probe passes on a lockdown-enabled boot, warns on mismatch, stays silent where the lockdown LSM is absent (WSL2). |
| T-292 | P2 | done | Security/Upstream | UPSTREAM-05 -- PG-major migration for the mios-pgvector data dir, so the `pgNN` tag can advance; ref moved to `pg18`. `mios-pgvector-major-upgrade.service` dumps the old cluster with an image of the OLD major into `[pgvector].restore_sql` (bind-mounted into `docker-entrypoint-initdb.d`), stashes rather than deletes the old data dir, and is non-destructive on every failure path. **Done-when:** a populated older cluster comes up on the newer major via the replayed dump, the old data dir survives as a stash, and a failed/absent dump leaves everything untouched rather than initialising an empty cluster. |
| T-293 | P2 | done | Security/Upstream | UPSTREAM-06 -- re-render the stale doc port/lane tables from the `[ports]` SSOT. Three retired schemes circulated (84xx lanes, 11450/11441, 3030/8888); the contract docs (README/CLAUDE/GEMINI/AGENTS/SECURITY/ai-instructions/api.md/llms*.txt) now reference `[ports]` KEYS, api.md carries derived `ports:<category>` marker tables, and the swapped heavy-lane engine claims (heavy=vLLM `vllm`, alt=SGLang `sglang` per the quadlets) are corrected in README/GEMINI/AGENTS. **Done-when (met):** `check_doc_port_scheme` greps `[docs].retired_ports` out of every `[docs].port_clean` file (negative-tested); wider payload surfaces split to T-304. |
| T-304 | P2 | done | Docs/DocGen | DOCGEN-11 -- retire the old port schemes from the runtime AI-payload surfaces, batch 1 (12 files, 85 edits): `ai/INDEX.md` (31), `docs/agents/AI-ARCHITECTURE.md` (21), `docs/ai-pipeline-map.md` (15), `ai/audit-prompt.md`, `etc/mios/ai/system-prompt.md`, `etc/mios/system-prompts/mios-reviewer.md`, two hermes SKILL.md, `cookbooks/ingest-kb.md`, `tools/README.md`, root `system-prompt.md`, `security/README.md`. Every edit drafted then adversarially verified (0 rejections). The sweep also corrected INDEX.md's swapped heavy-lane engines and its `ConditionPathExists` paths, which matched neither Quadlet. **Done-when (met):** all 12 in `[docs].port_clean`, gate green. Batch 2 = T-305. |
| T-305 | P2 | done | Docs/DocGen | DOCGEN-12 -- batch 2 of the payload de-rot: 24 files, 127 verified edits (17 full-mode + 7 AI-hint headers whose rot projected into the generated indexes). Covers `ai/system.md`, `ai/hermes-soul-full.md`, both remaining `etc/mios/system-prompts/*`, `mios-environment` + `opencode-delegation` SKILL.md, `open-webui/system-prompts/mios-agent.md`, both remaining cookbooks, `docs/day-0/FIRST-BOOT.md`, `docs/agents/PC-CONTROL-LOCAL.md`, `docs/terminal/INVOCATIONS.md`, `installation/UNIFY.md`, `tools/windows/README-WINDOWS.md`, the manual ToC blurbs and chapters ch04/ch10, and the seven hint-only docs. Runnable `curl` examples now resolve the port from the environment instead of hardcoding it. The verifier pass also proved its own worth by rejecting 87 proposals that were already applied. **Done-when (met):** 39 files in `[docs].port_clean`; `check_doc_port_scheme` green; hint-only files deliberately excluded because their bodies are historical. |
| T-306 | P2 | done | Docs/DocGen | DOCGEN-13 -- de-rot the documentation long tail: 74 files, 310 verified edits across ADRs, concepts, guides, upstream notes, reference docs and distilled manual pages (388 sites in, 38 out). `[docs].port_clean` grows 39 -> 107 files. The verifiers rejected 10 proposals, among them a rewrite that would have made an engine claim wrong, a mis-mapped key (8642 read as `llm_light`), a runnable `export` that would have stopped running, and two edits inside `mios-src` anchored passages. Historical archives (knowledge/, archive/, audits/, roadmap/history/, upstream-gaps) stay verbatim by design. **Done-when (met):** gate green over 107 files. |
| T-307 | P2 | done | Docs/DocGen | DOCGEN-14 -- de-rot the AI-hint headers the generated indexes read from: 35 source files (headers only, bodies untouched) plus four systemd units fixed at their source under `usr/lib/systemd/system` with golden-master snapshots refreshed (`cargo test --test golden_master` green). After re-render `tool-index.md` and `README.md` carry ZERO retired ports -- they healed from the corrected hints, which is the generative pipeline working as designed. Two enumerated port lists (`mios-firewall-ports`, `service-health.sh`) now name `[ports]` categories instead of literal lists that drift; the latter's hint was also truncated mid-word and is repaired. **Done-when (met):** generated indexes clean, gate green. |
| T-308 | P1 | done | Roadmap/Gates | ROADMAP-01 -- TASKS.md summary table and task sections agreed |
| T-309 | P3 | planned | Security/Sandbox | SBX-01 -- Reconcile the reference bwrap argv with the wrapper |
| T-310 | P2 | done | Security/Transport | SEC-TLS-01 -- Five outbound clients disable TLS verification |
| T-311 | P3 | planned | Naming/Hygiene | NAME2-04 -- Rename the globals that are truly mutated at runtime |
| T-312 | P1 | done | Topology/SSOT | BLADE-01 -- Total [urls]: one canonical address per service |
| T-313 | P2 | done | Topology/SSOT | BLADE-02 -- [blades] becomes the machine registry; nodes gain a blade |
| T-314 | P2 | done | Lifecycle/Health | BLADE-03 -- Give greenboot's role-awareness an SSOT it actually reads |
| T-315 | P2 | done | Topology/SSOT | BLADE-04 -- Finish WS-BLADE: karg producer, role-apply demotion, [profile] fold |
| T-316 | P1 | done | Naming/Addressing | ADDR-01 -- 17 executable retired-port fallbacks; Hermes binds an unassigned port |
| T-317 | P1 | done | Build/SSOT | UNITGEN-01 -- [units] is an SSOT that projects to nothing; the golden master guards a copy against a copy |
| T-318 | P1 | done | Naming/Addressing | ADDR-02 -- Seven sidecar ports were allocated but never bound; the collision check guards numbers nothing uses |
| T-319 | P1 | done | Topology/SSOT | BLADE-05 -- The activation axis gates 3 of 23 services, so a seat still starts the whole service plane |
| T-320 | P1 | done | Naming/Addressing | ADDR-03 -- The front door bound a retired port: 54 stale literals beside MIOS_PORT_* names |
| T-321 | P1 | done | Build/SSOT | ADDR-04 -- A generator rewrote the fixtures that prove it works; four addresses could never be offloaded |
| T-322 | P1 | done | Docs/SSOT | MINI-01 -- The seat-vs-blade comparison is generated from the SSOT, so it cannot go stale |
| T-323 | P1 | done | Topology/SSOT | MINI-02 -- A seat could not tell an unreachable blade from a broken model |
| T-324 | P1 | planned | Naming/Addressing | ADDR-05 -- Retired ports live on in shipped units and Quadlets; the sweep only scans docs |
| T-325 | P0 | done | Security/Federation | SEC-01 -- An unclosed table header made the seat's tenancy boundary unswitchable |
| T-326 | P1 | done | Build/SSOT | BUILD-01 -- sync-generated.sh needs two passes and says nothing; a gate passed over a stale tree |
| T-327 | P0 | planned | Security/Federation | SEC-02 -- A seat's auth posture must follow the role, not an operator remembering a flag |

---

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

## T-001 -- FED-G1: authenticate every inbound `/v1` and `/a2a` request at the one front door  (WS-FED | P0 | M)
**Goal:** E-24 Autonomy guardrails -- the single OpenAI `/v1` front door (`MIOS_AI_ENDPOINT`) stops being an anonymous, LAN-reachable inference oracle.
**What+How:** Add ONE ASGI `@app.middleware("http")` in `server.py`, ordered ahead of the usage shaper (~line 26814), matching `/v1/*` and `/a2a/*`. Accept any of three credentials: an `API_SERVER_KEY` bearer token, a per-agent caller-key loaded from `/etc/mios/ai/v1/caller-keys.json`, or a `mios_principal` scoped token. On a valid credential inject the scoped identity (`max_permission` + RBAC tier + reputation score) into request state so downstream handlers authorize off it. Add SSOT keys `[security].require_auth` (default `false`, making the middleware a literal no-op -- degrade-open) and `[security].loopback_only`; default the listener to loopback and only publish `0.0.0.0` when `require_auth = true` AND the bind is firewall-scoped to `172.16/12`.
**Where:** `usr/lib/mios/agent-pipe/server.py` (~26814) | `usr/share/mios/mios.toml` (`[security].require_auth`, `[security].loopback_only`) | `/etc/mios/ai/v1/caller-keys.json` (runtime overlay, not in the vendor image)
**Done When:** `GET /v1/models` with no credential returns `401`; a `caller-keys.json` key returns `200` with a scoped identity attached; setting `[security].require_auth = false` restores open access unchanged; `ss -ltnp` shows `:8640`/`:8642` on `127.0.0.1` by default; `/v1/cluster/health` reports `auth_gate: active`.
**Why:** Live-verified today: `/v1/models`, `/v1/chat/completions` and `/a2a` all return `200` and execute real inference with NO credential, on ports bound to `0.0.0.0` -- any process on the LAN can drive the council, spend the GPU, and reach every registered tool.
**Dep:** none
**Status:** done-by-code | **Domain:** Security/Federation | **Who:** WS-FED | Operator greenlight required -- changes front-door auth posture

## T-002 -- BOOT-01: greenboot health checks that roll back a bad AI-plane upgrade  (WS-RUNTIME | P1 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- greenboot health COVERAGE gated so every critical service has a check and a rollback path.
**What+How:** Author greenboot required-check scripts that assert `mios-agent-pipe.service`, `mios-llm-light.service` and `mios-pgvector.service` are active, and that `curl -sf http://localhost:8640/v1/models` returns `200` inside a 60s budget. Failure exits non-zero so greenboot triggers `bootc rollback`. Register the scripts in `/etc/greenboot/check/required.d/` and install the `greenboot` package from the `Containerfile`. Scripts must be idempotent (safe on every boot, no state written). Port literals come from the SSOT port keys, not inline `8640`.
**Where:** `/etc/greenboot/check/required.d/50-mios-agent-pipe.sh` | `/etc/greenboot/check/required.d/51-mios-llm-light.sh` | `Containerfile`
**Done When:** A deliberately broken `mios-agent-pipe` produces a rollback signal in the greenboot journal; a healthy boot passes all checks inside the timeout; re-running the scripts twice yields identical results.
**Why:** After a `bootc upgrade` that breaks the agent-pipe or the primary inference lane there is no automatic detection and no automatic rollback -- the machine boots "green" into an OS whose entire reason for existing (NS-2) is dead, and an operator has to notice by hand.
**Dep:** none
**Status:** done-by-code | **Domain:** Boot/Image | **Who:** Part 1 S2

## T-003 -- BOOT-02: fail the image build on HIGH/CRITICAL OpenSCAP findings (`oscap-im`)  (WS-SEC | P1 | M)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- compliance becomes a build-time fitness function instead of an after-the-fact audit.
**What+How:** Add `oscap-im` as a build-time dependency in the `Containerfile` and run a scan step after the main `RUN` layer against the Fedora STIG or CIS profile. Any HIGH or CRITICAL finding `exit 1`s the build. Known-acceptable deviations are declared in SSOT as `[compliance].oscap_skip_rules` and read by the scan step -- the skip list must never be a literal list inside the `Containerfile` (Law 7 NO-HARDCODE).
**Where:** `Containerfile` | `usr/share/mios/mios.toml` (`[compliance]` block)
**Done When:** `podman build` fails when a deliberate high-severity misconfiguration is injected; a clean tree builds with exit 0; adding a rule id to `[compliance].oscap_skip_rules` (and nowhere else) suppresses that finding.
**Why:** Published images ship with no mechanical compliance floor -- a hardening regression rides straight into `ghcr.io/mios-dev/mios` and onto every host that pulls the ref, discoverable only by scanning the fleet afterwards.
**Dep:** none
**Status:** built-gated-off | **Domain:** Boot/Security | **Who:** Part 1 S3

## T-004 -- BOOT-03: cryptographically verified rootfs via composefs + fs-verity  (WS-SEC2 | P1 | S)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- the read-only `/usr` of NS-1's single image is provably the image, not something edited underneath it.
**What+How:** Set `composefs = true` in the image's `/usr/lib/ostree/prepare-root.conf` so the deployment mounts through composefs. Verify at boot that overlayfs + EROFS + fs-verity are all active. Add a greenboot required check (`ostree admin status | grep composefs`) so a deployment that silently falls back to a non-verified mount is caught and rolled back rather than run. SSOT-drive the mode via `[security].composefs_mode`.
**Where:** `usr/lib/ostree/prepare-root.conf` | `/etc/greenboot/check/required.d/52-mios-composefs.sh`
**Done When:** `ostree admin status` confirms composefs active on a fresh boot; tampering with a file under `/usr` raises a verification error on the next boot instead of booting the tampered tree; the greenboot check passes on an unmodified image.
**Why:** Without composefs/fs-verity the immutability of `/usr` is a convention, not an enforced property -- offline modification of the deployed root is undetectable, which breaks the "a host that pulls the ref reproduces the fleet exactly" guarantee.
**Dep:** T-002 (greenboot)
**Status:** done-by-code | **Domain:** Boot/Security | **Who:** Part 1 S4

## T-005 -- BOOT-04: generate every Podman Quadlet from `mios.toml` and drift-gate the result  (WS-SYSTEMD | P1 | M)
**Goal:** E-18 Generate the systemd units from SSOT -- no container unit is hand-maintained and none can silently diverge from the SSOT that declares it.
**What+How:** Extend `tools/generate-pod-quadlets.py` to fully parse `[pods.*]`, `[ports.*]` and `[containers.*]` from `mios.toml` and emit `.container`, `.network` and `.volume` Quadlet units at build time. Add a `--check` mode that renders to memory, diffs against the units on disk, and exits non-zero on any difference. Wire that `--check` invocation into `automation/98-drift-checks.sh` as a registered check so the gate owns it.
**Where:** `tools/generate-pod-quadlets.py` | `automation/98-drift-checks.sh` | `Containerfile`
**Done When:** `generate-pod-quadlets.py --check` exits 0 on a clean repo; adding a `[pods.test]` block emits the correct `.pod` unit; hand-editing a generated unit turns `just drift-gate` RED.
**Why:** Quadlets edited by hand drift from `[pods.*]`/`[containers.*]` with nothing to catch it -- this is the exact recurring class where a broad `git add` strips or reverts generated unit content and the divergence is only discovered when a pod fails to start on a real host.
**Dep:** none
**Status:** done-by-code | **Domain:** Boot/Ops | **Who:** Part 1 S5

## T-006 -- A1: one `[agents.*]` schema with `_defaults` inheritance, ending silent single-agent degradation  (WS-A1 | P1 | M)
**Goal:** E-09 One value, one name -- per-agent config collapses to thin overrides over a single declared default block instead of N ad-hoc copies.
**What+How:** Add `[agents._defaults]` to vendor `mios.toml` carrying the canonical schema: a `kind` discriminator (`local-http|remote-http|cli|mobile|edge|node|a2a`), `enabled`, `transport`, `timeout_s`, `sub_lane`, `api`, `vram_mb`, `ram_mb`, `tool_capable`, `auth{scheme,header_template,principal_mode}`, `trust{min_reputation,require_signed_principal,mtls}`. In `_load_agent_registry` do `base = agents.pop("_defaults", {})`, skip any `_`-prefixed name, and merge `effective = {**base, **cfg}`. Make the `health_gate` default SAFE: `True` when `kind in {remote-http,cli,mobile,edge,node,a2a}`, or when `not enabled`, or when `_is_remote_endpoint(ep)`. Extract `_coerce_agent_cfg(name, effective)` and share it between `_load_agent_registry` and `_load_node_pool`. Rewrite each `[agents.*]` block as a thin override.
**Where:** `usr/share/mios/mios.toml` | `usr/lib/mios/agent-pipe/server.py` (~3835-3995)
**Done When:** With `_defaults` absent, behavior is byte-identical to today; with `_defaults` present, `opencode` resolves `health_gate=true`; `/v1/cluster/health` is unchanged for live agents; a unit test proves a 1-field overlay inherits every remaining field.
**Why:** Agent config is ad-hoc -- `hermes` carries `health_gate`, `opencode` does not, and the loader defaults local agents to `health_gate=False`, producing `merged_chars=0`. That is the root cause of the orchestrator quietly running as a single agent while still reporting a council.
**Dep:** none
**Status:** done-by-code | **Domain:** Orchestration | **Who:** WS-A1

## T-007 -- A2: `check_agent_schema()` drift-gate so a malformed agent block cannot merge  (WS-A2 | P1 | S)
**Goal:** E-07 The drift-gate as the enforcement plane -- the T-006 schema becomes a machine-checked invariant, not a convention.
**What+How:** Add `check_agent_schema()` to `automation/98-drift-checks.sh`, mirroring the existing `check_rbac_tiers` pattern (inline `python3` + `tomllib`). It FAILS on: (a) a local/cli agent missing `health_gate=true`; (b) `kind=cli` without `timeout_s`/`enabled`; (c) `kind=node` without both `api` and `lane`; (d) remote/edge/mobile without `health_gate=true`; (e) a bare `:PORT` literal where `${MIOS_PORT_*}` belongs; (f) not-exactly-one `default=true`; (g) any unknown key. Register it in `main()` immediately after `check_rbac_tiers`.
**Where:** `automation/98-drift-checks.sh`
**Done When:** `just drift-gate` fails when a test agent omits `health_gate`; it passes on the cleaned config; the check runs in CI with no built image required (pure repo-tree parse).
**Why:** Nothing stops the T-006 regression class from reappearing -- one merged agent block missing `health_gate` silently returns the orchestrator to single-agent mode, and a hardcoded `:PORT` in an agent block reintroduces the NO-HARDCODE violations that E-12/E-13 exist to remove.
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Orchestration/CI | **Who:** WS-A2

## T-008 -- A3: make the opencode gateway a real council peer on `:8633` instead of a hang  (WS-A3 | P1 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a gateway MiOS already ships either works and is SSOT-enabled, or its claim is withdrawn.
**What+How:** Fix the root cause at `opencode-gateway/server.py:171-173`: the `subprocess.run` call passes no `stdin=`, so `opencode run` drops into its TUI and blocks forever. Pass `stdin=subprocess.DEVNULL` and use genuinely headless invocation (`opencode run -p`/`--print`, the `OPENCODE_*` env, or switch to `opencode serve`). Add a fail-fast timeout read from `[agents.opencode].timeout_s`. Enable and start `mios-opencode-gateway.service`, then set `[agents.opencode].enabled = true` and add it to `fanout` once it is stable under load.
**Where:** `usr/libexec/mios/opencode-gateway/server.py` (~171-173) | `usr/lib/systemd/system/mios-opencode-gateway.service` | `usr/share/mios/mios.toml`
**Done When:** `curl :8633/v1/chat/completions` returns a real completion with no hang; `/v1/cluster/health` shows opencode `effective_up: true`; a code-routed fan-out merges real opencode output into the council response.
**Why:** "opencode as a real council peer DONE" is FALSE today -- the gateway is disabled and inactive, `:8633` is not listening, and any call that did reach it would hang indefinitely on the TUI. The code lane of the council has no second opinion.
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Orchestration | **Who:** WS-A3

## T-009 -- A4/FED: make `hermes-worker` come up after its venv exists instead of dying at boot  (WS-A4 | P1 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a shipped lane that never reaches `active` is an unwired capability.
**What+How:** Add `After=`/`Requires=` on the venv-build unit to `hermes-worker.service` so ordering is explicit rather than racing. Add a `.path` unit watching the hermes binary that `ExecStart`s the worker when the path becomes available, covering the case where the venv is built after boot. Ensure `[agents.hermes-worker]` declares `kind=local-http` with an `auth{}` block and `health_gate=true` per the T-006 schema.
**Where:** `usr/lib/systemd/system/hermes-worker.service` | `usr/lib/systemd/system/hermes-worker-watch.path`
**Done When:** After a fresh boot plus venv build, `systemctl is-active hermes-worker` reports `active`; `/v1/cluster/health` shows at least one peer `effective_up: true`; a fan-out request measurably uses hermes-worker as a council peer.
**Why:** On a default VM all 9 cluster agents report `effective_up: false` -- `:8643` hermes-worker sits `inactive` with `ConditionResult=no` because the venv is absent at boot, and nothing ever retries. The council has zero peers on a clean install.
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Orchestration/Federation | **Who:** WS-A4

## T-010 -- FED-G2 follow-up: attach outbound agent credentials at all 4 remaining dispatch sites  (WS-FED | P1 | S)
**Goal:** E-24 Autonomy guardrails -- outbound federation is credentialed everywhere, not just on the one path someone remembered.
**What+How:** Locate every `httpx.AsyncClient`/`aiohttp` call site in `server.py` that dispatches to an agent endpoint -- the known ones are at ~1873, ~4699, ~5829 and ~26208 -- and call `_apply_outbound_auth(hdrs, ep)` at each site before the request is issued, exactly as the council/tool-loop site already does. Confirm the helper is a no-op for endpoints whose `auth` config is empty so local agents are untouched.
**Where:** `usr/lib/mios/agent-pipe/server.py` (~1873, ~4699, ~5829, ~26208)
**Done When:** All 4 sites attach the header their endpoint's `auth` config specifies; local no-auth agents still succeed with empty headers; no dispatch path remains that reaches a remote peer uncredentialed.
**Why:** `_apply_outbound_auth(hdrs,ep)` is wired only at the council/tool-loop site -- the other dispatch paths reach authenticated peers with no credential, so once T-001/T-014 turn auth on at the receiving end those paths start failing (or, worse, keep working only because peers are still open).
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Federation/Security | **Who:** WS-FED

## T-011 -- FED-G3: live A2A membership reload without restarting the agent-pipe  (WS-FED | P1 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- federation membership becomes a live-reloaded projection of its config files.
**What+How:** Implement an mtime watcher (inotify, or the existing cron-director pattern) over `a2a-peers.json` plus the `[agents.*]`/`[nodes.*]` sections of `mios.toml`. On change, re-run `_a2a_load_peers()` and invalidate `_WORKER_TOOLS_FULL_CACHE` so the tool roster is rebuilt. Additionally expose an auth-gated `POST /a2a/peers/reload` that drives the same code path. Gate the watcher on `[a2a].live_reload` (default `true` -- additive and safe).
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` (`[a2a].live_reload`)
**Done When:** Adding a peer to `a2a-peers.json` makes it appear in `/v1/cluster/health` within 5s with no restart; removing one drops it within 5s; `POST /a2a/peers/reload` produces the same result.
**Why:** Every membership change today requires restarting `mios-agent-pipe`, which drops in-flight turns and warm KV state -- and it makes automatic discovery (T-013) useless, since a discovered peer written to disk would never be noticed.
**Dep:** T-001 (FED-G1, for reload-endpoint auth), T-006 (A1)
**Status:** done-by-code | **Domain:** Federation | **Who:** WS-FED

## T-012 -- FED-G4: self-describing, Ed25519-signed AgentCard  (WS-FED | P1 | M)
**Goal:** E-15 supply-chain hardening as gated policy -- a peer's identity claim is cryptographically verifiable rather than asserted.
**What+How:** Extend `_build_agent_card()` (`server.py:~19082`) to emit `securitySchemes` and `security` fields projected from `[a2a.security]` in SSOT (never hand-written into the card). Add a `signatures[]` array holding a JWS over the RFC-8785 canonical (JCS) form of the card body, signed with the Ed25519 passport key. Include an `x-mios` extension block cross-linking the OpenAI `/v1` and MCP surfaces so one fetch describes all three contracts. Ensure the canonicalization is deterministic so the card is byte-stable across restarts.
**Where:** `usr/lib/mios/agent-pipe/server.py` (~19082) | `usr/share/mios/mios.toml` (`[a2a.security]`)
**Done When:** `curl /.well-known/agent-card.json` returns a card containing `securitySchemes` and `signatures[]`; a peer verifies the JWS using the key from `GET /passport/public-key`; two consecutive restarts produce identical card bytes.
**Why:** Without a signed card, peer identity is whatever the peer says it is -- T-014's verify/enforce delegation has nothing to check against, and a hostile LAN node can present itself as a trusted MiOS peer.
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Federation/Security | **Who:** WS-FED

## T-013 -- FED-G5: LAN-native mDNS peer discovery (avahi) with a CIDR-sweep fallback  (WS-FED | P1 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- avahi and the discovery packages MiOS already installs actually produce peers.
**What+How:** Enable `avahi-daemon.service` behind `[a2a].mdns_discovery` (default `false`). Publish `_mios-ai._tcp` and `_a2a._tcp` on the agent-pipe port `:8640`. On the browse side, `mios-a2a-discover` parses `avahi-browse` output and confirms each candidate with a `/v1/models` probe before trusting it; when mDNS is unavailable it falls back to a CIDR sweep of `172.16/12` with the same probe. Discovered peers are written to `/etc/mios/ai/v1/a2a-peers.json`, which triggers the T-011 live reload rather than a restart. firewalld already opens `mdns`/5353 (`33-firewall.sh`) -- do not re-add a rule.
**Where:** `usr/lib/systemd/system/mios-a2a-discover.service` | `usr/libexec/mios/mios-a2a-discover` | `usr/share/mios/mios.toml`
**Done When:** A second MiOS node on the same LAN appears in `/v1/cluster/health` within 30s of boot with zero manual config; `[a2a].mdns_discovery = false` results in no avahi activity at all; the CIDR sweep path produces the same peer set when mDNS is blocked.
**Why:** Federation is manual-only: every peer must be hand-written into `a2a-peers.json`, so two MiOS boxes on one LAN stay isolated and the "federated agent OS" property is operator labor rather than a property of the image.
**Dep:** T-011 (FED-G3), T-001 (auth gate)
**Status:** done-by-code | **Domain:** Federation | **Who:** WS-FED

## T-014 -- FED-G6: authenticated inbound delegation with least-privilege scoping  (WS-FED | P1 | M)
**Goal:** E-24 Autonomy guardrails -- an inbound peer gets exactly the tool surface its verified identity earns, and nothing more.
**What+How:** Stage the rollout through the `[a2a].principal_mode` SSOT key: `off` -> `verify` -> `enforce`. In `verify` (audit-only), validate the incoming peer's Ed25519 AgentCard signature and log the resolved identity as `event(kind="peer_auth")` without blocking anyone. Map a verified peer identity to a scoped identity carrying `max_permission` plus explicit tool-surface restrictions driven by reputation. In `enforce`, unverified peers are rejected outright. Implement in the A2A inbound handler so it composes with the T-001 middleware rather than duplicating it.
**Where:** `usr/lib/mios/agent-pipe/server.py` (A2A inbound handler) | `usr/share/mios/mios.toml` (`[a2a].principal_mode`)
**Done When:** With `principal_mode=verify` an unsigned peer still passes but its identity is logged; with `enforce` an unsigned peer gets `403` while a signed peer gets a scoped identity; the scoped identity demonstrably narrows the tool surface for a low-reputation peer.
**Why:** Any peer that reaches `/a2a` today gets the full tool surface of the host -- filesystem, shell and verb tools included -- with no identity check and no ceiling, so one compromised LAN node owns the whole council.
**Dep:** T-012 (FED-G4 signed card), T-001 (FED-G1 auth gate)
**Status:** done-by-code | **Domain:** Federation/Security | **Who:** WS-FED

## T-015 -- C0: make code-server actually bind the SSOT port `:8800` instead of `:8080`  (WS-C0 | P1 | S)
**Goal:** E-13 Ports are allocated from SSOT, not hand-assigned -- the container obeys the key that already exists.
**What+How:** `[ports].code_server = 8800` is already in SSOT but the container still binds `:8080`. In `mios-code-server.container` set BOTH `Environment=BIND_ADDR=0.0.0.0:8800` AND the `--bind-addr 0.0.0.0:8800` entrypoint argument -- the image `ENTRYPOINT` overrides the env var, so either alone is insufficient. Update the three `Label=` directives and the header comment that still say `:8080`.
**Where:** `usr/share/containers/systemd/mios-code-server.container`
**Done When:** `ss -ltnp | grep 8800` shows the binding and `:8080` is free; the Code Server UI answers at `http://localhost:8800`; no `:8080` literal remains in the unit.
**Why:** `:8080` is a contested port on this host and the collision blocks other services from starting; it is also a live NO-HARDCODE violation of a key that already exists in SSOT, which is exactly the class the hardcode lint is supposed to catch.
**Dep:** none
**Status:** done-by-code | **Domain:** Ops/Pods | **Who:** WS-C0

## T-016 -- C1: declare the 7 remaining `[pods.*]` groupings in `mios.toml`  (WS-C1 | P1 | M)
**Goal:** E-18 Generate the systemd units from SSOT -- pod topology is declared once in SSOT and rendered, never hand-assembled.
**What+How:** Mirror the proven `[pods.mios-webtools]` schema for: `mios-ai-inference` (llm-light + cpu-node + worker), `mios-ai-heavy` (heavy + heavy-alt, VRAM-gated), `mios-ai-data` (pgvector), `mios-devforge` (forge + runner + code-server), `mios-netinfra-dns` (adguard), `mios-remote-desktop` (guacamole, optional), keeping `mios-webtools` as-is. Deliberately leave the OWUI front door and searxng standalone (not podded). Validate by running `generate-pod-quadlets.py --check`.
**Where:** `usr/share/mios/mios.toml` (`[pods.*]`)
**Done When:** `generate-pod-quadlets.py --check` lists all 7 pods with no drift warning; `just drift-gate` passes.
**Why:** Without pod declarations the sidecar containers share no network namespace or lifecycle, so ordering, restart and teardown are per-container accidents -- and T-017's `Pod=` attachment has nothing to attach to.
**Dep:** T-015 (C0)
**Status:** done-by-code | **Domain:** Ops/Pods | **Who:** WS-C1

## T-017 -- C2: attach `Pod=` to every member container and prove all 7 pods run healthy  (WS-C2 | P1 | M)
**Goal:** E-18 Generate the systemd units from SSOT -- the declared topology from T-016 is realized on the running host.
**What+How:** Add `Pod=<pod>.pod` to each member `.container` file for all 7 pods declared in T-016. Run `tools/generate-pod-quadlets.py` to produce the `.pod` Quadlet units, `systemctl daemon-reload`, then start each pod and verify both the pod and each member reach healthy. The existing `check_pod_quadlets` drift-check covers the generated-vs-disk half.
**Where:** every member `.container` file under `usr/share/containers/systemd/` | `tools/generate-pod-quadlets.py`
**Done When:** `podman pod ls` shows all 7 pods `Running`; every member container is listed under its pod; all container health checks pass.
**Why:** Declared-but-unattached pods are inert -- containers keep their own isolated netns, so intra-pod service names do not resolve and the grouping exists only in SSOT while the running system contradicts it.
**Dep:** T-016 (C1)
**Status:** done-by-code | **Domain:** Ops/Pods | **Who:** WS-C2

## T-018 -- E1: persist the OWUI location/model row through firstboot so it survives a rebuild  (WS-E1 | P1 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a live-applied setting becomes part of the image's reproducible first boot.
**What+How:** Wire `mios-owui-apply-system-prompt` into the OWUI firstboot / `ExecStartPost` chain so the `MiOS AI` model row carrying `{{USER_LOCATION}}`, `{{CURRENT_TIMEZONE}}` and `{{CURRENT_DATE}}` is (re)applied on every fresh start. Set `Environment=MIOS_OWUI_DB=<host webui.db>` on `mios-agent-pipe.service` so the applier finds the right database. Document in the firstboot output that browser geolocation needs a secure context -- `https://...ts.net` or `http://localhost:3030`, NOT `http://<LAN-IP>`.
**Where:** `usr/lib/systemd/system/mios-open-webui-firstboot.*` | `usr/lib/systemd/system/mios-agent-pipe.service`
**Done When:** Re-running firstboot against an empty model table recreates the `MiOS AI` row with `{{USER_LOCATION}}`; the row survives a full reinstall; the secure-context requirement appears in firstboot output.
**Why:** The fix is applied live only -- any rebuild or reinstall silently loses it, so the flagship OWUI entry point reverts to a location-blind default and the operator re-does it by hand every image cycle (a direct NS-1 reproducibility violation).
**Dep:** none
**Status:** done-by-code | **Domain:** UX/OWUI | **Who:** WS-E1

## T-019 -- SCHED-01: turn-boundary preemption wiring `PriorityGate` to KV paging  (WS-GUARD | P1 | L)
**Goal:** E-24 Autonomy guardrails -- foreground work preempts background work by lane priority instead of queueing behind it.
**What+How:** On a high-priority arrival while the lane is saturated, identify the lowest-priority in-flight turn and suspend it at the next tool-call or DAG-step boundary -- never mid-decode. Snapshot its state with `_kv_slot_action("save", slot_id)`, admit and complete the urgent request, then `_kv_slot_action("restore", slot_id)` and resume the suspended turn from the saved DAG step. Add SLA classes `interactive`/`batch`/`background` to the `[scheduler]` SSOT block. Gate the whole path on `[scheduler].preemption` (default `false`, degrade-open).
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` (`[scheduler]`)
**Done When:** With `preemption=true`, an interactive request arriving mid-batch-tool-call is serviced within 2s and the batch resumes from the same DAG step; with `preemption=false` behavior is byte-identical to today; KV restore is correct for Gemma/Qwen SWA models (verified with `--swa-full`); `/v1/cluster/health` reports `scheduler_mode: preemptive` when active.
**Why:** `mios_sched.PriorityGate` and `_kv_paging` both exist but were never connected -- so a long background generation blocks the interactive lane end-to-end, and the operator's own prompt waits behind an autonomous loop's batch job.
**Dep:** T-006 (A1)
**Status:** done-by-code | **Domain:** Scheduling/Kernel | **Who:** Part 5 P0, Part 6 P1#1

## T-020 -- SCHED-02: token-time slicing queue with anti-starvation aging in agent-pipe  (WS-H2 | P1 | M)
**Goal:** E-24 Autonomy guardrails -- concurrent requests share the lane fairly instead of running to completion head-of-line.
**What+How:** Add a token-time slicing queue to `agent-pipe` on `:8640`. Once a task emits `[scheduler].token_slice_size` tokens (default `512`), preempt it: save the KV slot, yield the lane, advance to the next task in a round-robin queue, restore that task's KV slot and continue. Add monotonic aging so a task's effective priority rises with queue wait time. Gate on `[scheduler].token_slice` (default `false`).
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` (`[scheduler].token_slice*`)
**Done When:** With `token_slice=true` and a 512-token slice, a 4000-token generation is preempted 8 times and interleaves with a short parallel request; the short request completes without waiting for the long generation; a background task waiting >60s is elevated to the `interactive` SLA.
**Why:** A single long generation monopolizes the lane for its full duration, so every concurrent caller -- including the interactive one -- sees latency equal to the longest in-flight job, and low-priority work can wait indefinitely with no aging to rescue it.
**Dep:** T-019 (SCHED-01)
**Status:** done-by-code | **Domain:** Scheduling | **Who:** WS-H2, Part 5 P8, Part 3 E.3

## T-021 -- MEM-01: stable per-conversation KV slots with a `--swa-full` correctness guard  (WS-DURA | P1 | M)
**Goal:** E-24 Autonomy guardrails -- conversation state is durable and correct across turns rather than silently recomputed or silently corrupt.
**What+How:** Map each `chat_id` to a stable `slot_id` in `mios-llm-light` using its `/slots` API. Before each turn call `_kv_slot_action("restore", slot_id)` when a prior snapshot exists; after each turn call `_kv_slot_action("save", slot_id)`. Detect the model family from the active `mios-llm-light.yaml` entry and, for Gemma/Qwen sliding-window models, pass `--swa-full` on restore -- without it the restored KV is silently wrong rather than erroring. Add `[memory].kv_slot_persist` (default `true`) as the SSOT switch back to stateless behavior.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/llamacpp/mios-llm-light.yaml` | `usr/share/mios/mios.toml` (`[memory]`)
**Done When:** A second turn restores prior KV state with prefix tokens not re-processed (measurable in prefill time); Gemma/Qwen restores produce correct output with `--swa-full`; `[memory].kv_slot_persist=false` cleanly falls back to stateless.
**Why:** `mios-llm-light` already runs with `--slot-save-path` but nothing maps a conversation to a slot file, so every turn re-processes the full prefix -- wasted GPU on every message -- and the T-019/T-020 preemption paths have no correct save/restore primitive to suspend against.
**Dep:** T-019 (SCHED-01)
**Status:** done | **Domain:** Memory/Context | **Who:** Part 5 P1

## T-022 -- FED-CONSUME: light up the dormant A2A and MCP client halves  (WS-FED | P1 | L)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- the client side of federation stops being dead code and MiOS becomes a real peer, not just a server.
**What+How:** Self-test first: register MiOS's own A2A card and MCP endpoint into the runtime overlays so the client halves exercise themselves over loopback. Verify the full client round-trips -- A2A `Message -> Task -> Artifact`, and MCP `tools/list` + `tools/call` via `_mcp_tool_to_openai_tool` / `_a2a_send_message_to_peer`. Confirm `mios-a2a-discover` auto-populates `a2a-peers.json` from live AgentCards. Then test against a second MiOS node over the LAN/WSL `172.x` gateway (deliberately without Tailscale) and confirm the remote node contributes real content to a council fan-out.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `/etc/mios/ai/v1/mcp.json` | `/etc/mios/ai/v1/a2a-peers.json`
**Done When:** Loopback self-registration round-trips A2A `Message -> Task -> Artifact`; a second MiOS node on the LAN appears in `/v1/cluster/health` and contributes fan-out; a remote MCP server's tools appear in the council tool roster via `/v1/verbs/openai-tools`.
**Why:** `_mcp_tool_to_openai_tool` and `_a2a_send_message_to_peer` are wired but never invoked, and the vendor image ships an empty `/usr/share/mios/ai/v1/mcp.json` -- so MiOS can be consumed by others but consumes nothing. This is the single largest strategic gap between "one-operator ensemble" and the NS-2 federated agent OS.
**Dep:** T-011 (FED-G3), T-012 (FED-G4), T-001 (auth gate)
**Status:** built-gated-off | **Domain:** Federation | **Who:** Part 6 P1#2

## T-023 -- OBS-01: OpenTelemetry GenAI spans linked to the pgvector replay log  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- agent execution is observable and joins back to the unified datastore that already records it.
**What+How:** Instrument `agent-pipe` to emit `invoke_agent` and `execute_tool` spans carrying OTel `gen_ai.*` semantic attributes. Bake a local collector (`otelcol-contrib`) as a Podman container via a Quadlet unit -- baked into the image, not fetched (Law 12). Carry `tool_call.session_id` on the spans so each trace joins to its pgvector replay row, and surface traces in Jaeger or Grafana Tempo. Gate everything on `[observability].otel_enable` (default `false`).
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/containers/systemd/mios-otelcol.container` | `usr/share/mios/mios.toml` (`[observability]`)
**Done When:** A chat request produces spans in the local trace viewer; each tool call has a child span with `gen_ai.tool.name`; a span links to its pgvector `tool_call` row via `session_id`; with the gate off, no spans are emitted and the collector does not run.
**Why:** A multi-agent fan-out with nested tool calls is currently debuggable only by reading logs -- there is no per-turn causal trace, so latency and failure attribution across the council is guesswork.
**Dep:** none
**Status:** done-by-code | **Domain:** Observability | **Who:** Part 1 S1, Part 6 P3#6

## T-024 -- A5: council honesty -- report single-agent mode instead of implying a council  (WS-A5 | P2 | S)
**Goal:** E-24 Autonomy guardrails -- degraded operation is reported, never disguised.
**What+How:** Detect the condition where every peer is `effective_up: false` and surface `"mode": "single-agent (no council peers up)"` both in `/v1/cluster/health` and in chat response metadata, so the degradation is visible to a human and machine-detectable by a monitor.
**Where:** `usr/lib/mios/agent-pipe/server.py`
**Done When:** With all peers down, `/v1/cluster/health` contains the single-agent mode string; chat response metadata reflects it; with at least one peer up, mode reports `"council"` normally.
**Why:** With all peers down the pipe still answers as though a council deliberated, so a silent full degradation (the exact outcome of the T-006/T-008/T-009 bugs) looks identical to healthy operation and goes unnoticed.
**Dep:** none
**Status:** done-by-code | **Domain:** Orchestration | **Who:** WS-A5

## T-025 -- A6: migrate the kernel hot path out of `chat_completions()` into dispatcher handlers [VM]  (WS-A6 | P2 [VM] | XL)
**Goal:** E-02 Technical-debt retirement -- the agent-pipe god-module is decomposed so the LLM-as-CPU kernel actually executes the routing it claims to.
**What+How:** Move each execution mode (`chat`, `dispatch`, `multi_task`, `agent`) out of the monolithic `chat_completions()` into discrete dispatcher handlers behind `kernel_route`, and implement `_kernel_stage2b` rather than leaving it raising `NotImplementedError`. Run in shadow mode first -- execute old and new paths in parallel and log every functional diff -- and only flip `shadow_route=True` -> `shadow_route=False` once the shadow log is clean over a representative corpus. Requires an operator VM to exercise real routing.
**Where:** `usr/lib/mios/agent-pipe/server.py`
**Done When:** The shadow log shows zero functional diffs across 100 representative requests; with `shadow_route=False` all traffic flows through the dispatcher; `/v1/route` returns the same decision the live dispatch takes.
**Why:** "Kernel Stage-2a DONE" is introspection-only -- `_kernel_stage2b` raises `NotImplementedError` and `shadow_route=False`, so the kernel does not execute and all routing still runs inside the `chat_completions()` monolith, the single largest block of the ~9k-line `server.py` debt item.
**Dep:** T-019 (SCHED-01), operator VM [VM]
**Status:** completed | **Domain:** Kernel/Scheduling | **Who:** WS-A6

## T-026 -- B1: Flip the safe governance gates to observe-only ON in SSOT  (WS-GUARD | P2 | S)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- the cost and memory rails run live in audit mode before they are ever allowed to enforce.
**What+How:** In the vendor SSOT set `[ai].memory_guard_mode = "log"` (memguard validates and records, blocks nothing) and `[cost].enable = true` (token accounting observed, nothing shed). Deliberately leave `slo_shed` and `kernel_route` OFF -- those change routing behaviour and need VM parity first. The gate plumbing and the A5 SLO-foreground precondition already shipped; this task is the SSOT flip and nothing else.
**Where:** `usr/share/mios/mios.toml`
**Done When:** `GET /v1/cost` returns `{"enabled": true, ...}` carrying real token counts, memguard writes validation events to pgvector on every memory operation, and no existing behaviour regresses.
**Why:** With the gates off there is no measured baseline of token spend or memguard hit-rate, so any future enforcement threshold is a guess and the first hard-stop will fire in the wrong place.
**Dep:** none
**Status:** done-by-code | **Domain:** Governance

---

## T-027 -- B2: Prove the K-LRU tiering loop actually fires end-to-end  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- pgvector is a measured recall tier, not a write-only store that grows forever.
**What+How:** Run a live recall round-trip and check `SELECT access_count FROM agent_memory WHERE ...`. If it is still 0, trace the recall projection in `server.py`: verify the row `id` is carried through the projection and that the `_PG_PRIMARY` page-in counter block is actually reached. Fix the recall path so `access_count` increments on every hit, giving K-LRU eviction a real signal. Use `mios-pg-query` for the inspection queries.
**Where:** `usr/lib/mios/agent-pipe/server.py` (recall/tiering), `usr/libexec/mios/mios-pg-query`
**Done When:** After a recall, `access_count` increments in `agent_memory`, a row appears in the "hot" tier, and K-LRU eviction operates on non-zero counters.
**Why:** Live pgvector has 0 rows with `access_count > 0` -- eviction has never once fired, so "tiering DONE" is an unproven claim and the memory tier is effectively unbounded.
**Dep:** Operator VM chat loop.
**Status:** done-by-code | **Domain:** Memory

---

## T-028 -- ORCH-01: Type every deliberation turn with the DCI 14-act vocabulary  (WS-DB | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- deliberation becomes queryable structured rows in the agent datastore instead of free text.
**What+How:** Define the 14 act types `frame/clarify/reframe/propose/extend/spawn/ask/challenge/bridge/synthesize/recall/ground/update/recommend` in `mios_dci`; require every agent deliberation reply to emit `{"act": "<type>", "content": "..."}`; add an `act_type` column to the `event` table in `schema-init.sql` and tag each persisted deliberation row with it.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql`
**Done When:** A deliberation round produces `event` rows carrying valid `act_type` values, invalid values are logged as warnings rather than persisted silently, and an act-distribution query returns meaningful data after 10 rounds.
**Why:** Untyped deliberation transcripts cannot be analysed or gated -- downstream conflict detection (ORCH-02's ">= 2 conflicting `challenge` acts") has nothing to key on.
**Dep:** None.
**Status:** done-by-code | **Domain:** Orchestration

---

## T-029 -- ORCH-02: DCI-CF convergent-flow critic as a bounded, conflict-triggered 4-persona loop  (WS-GUARD | P2 | L)
**Goal:** E-24 Autonomy guardrails -- a critic loop that is bounded by construction and cannot fan out on every query.
**What+How:** Implement four personas (Framer/Explorer/Challenger/Integrator) on `hermes-agent` as four differentiated system prompts over a single model -- cheaper than four isolated instances. Bound the loop at `R_max=3` rounds and `K_max=4` candidate finalists. Always emit a decision packet `{choice, rationale, minority_report, reopen_triggers}`. Persist tension as first-class `event(kind="dissent", act_type="challenge")`. Invoke only when the first round contains >= 2 conflicting `challenge` acts; configured under `[council].dci_cf_*` with `[dci].flow_enabled` default-off.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[council].dci_cf_*`)
**Done When:** A conflicted deliberation produces a decision packet containing `minority_report`, routine queries bypass DCI-CF with no added latency, and `SELECT * FROM event WHERE kind='dissent'` returns rows.
**Why:** An unconditional critic multiplies VRAM and latency on every single query, and without a persisted minority report the reason a rejected option was rejected is lost the moment the turn ends.
**Dep:** T-028 (ORCH-01), T-009 (A4 hermes-worker boot).
**Status:** built-gated-off | **Domain:** Orchestration

---

## T-030 -- ORCH-03: Dual-ledger DAG state plus typed-output synthesis  (WS-DB | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- multi-agent state lives in typed tables, not in a free-text merge.
**What+How:** Add a per-conversation Fact Ledger (claims + sources) and Progress Ledger (per-agent assignment + completion) to the DAG path, schema in `schema-init.sql`. Make synthesis a reducer over typed node outputs: the verb-output schema for action nodes, `{claim,source}` for research nodes. For a `multi_task` "both" intent, order it so the research facet completes and exports typed findings first and the action facet depends on those findings. Trigger a re-plan when the Progress Ledger stall count exceeds 2.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql`
**Done When:** A research+action query writes a Fact Ledger row before the action node executes, the action node's input is derived from that ledger rather than a free-text merge, and stall count > 2 emits a re-plan event.
**Why:** Free-text merging of multi-agent output silently drops or fabricates claims, and with no progress ledger a stalled facet hangs the whole DAG with nothing observing it.
**Dep:** T-006 (A1).
**Status:** done-by-code | **Domain:** Orchestration

---

## T-031 -- ORCH-04: ReAct+Reflexion loop with per-superstep checkpointing  (WS-DURA | P2 | L)
**Goal:** E-24 Autonomy guardrails -- bounded, durable agent loops that resume after a crash instead of re-running the whole plan.
**What+How:** Formalise each turn as `call -> observe -> reason` repeating until no tool calls remain, bounded by `max_iter`/`max_retry`. On a tool error, insert a Reflexion step where the model self-critiques the failure and revises the call before retrying. Checkpoint per super-step keyed by `(chat_id, superstep_id)` into the pgvector `session` table so a crash resumes from the last checkpoint rather than restarting. Gated by `[agent].reflexion_enable` (default `true`).
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql`, `usr/share/mios/mios.toml`
**Done When:** A tool failure logs a Reflexion step in `event` before the retry, a simulated crash resumes from the last superstep checkpoint instead of a full restart, and the `max_iter` cap demonstrably stops an infinite loop.
**Why:** Without checkpoints a mid-DAG crash re-spends every token and minute already used, and a blind retry repeats the identical failing tool call until the cap is hit.
**Dep:** T-021 (MEM-01 KV slot restore for crash recovery).
**Status:** done-by-code | **Domain:** Orchestration

---

## T-032 -- SEC-01: Hermetic MCP sandboxing, one gatekeeper per tool execution [VM]  (WS-SEC | P2 | L)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- untrusted third-party tool code runs only under image-baked, enforced trust policy.
**What+How:** Route every `.mcpb` bundle execution through `usr/libexec/mios/mcp-server-runner` as the single gatekeeper (path-traversal blocking, write-path enforcement, rootless podman sandbox), with `mcp.py` doing the routing. Each tool execution spawns in a rootless Kata-on-Firecracker microVM, Lima VM as fallback. Confine file ops to `glob`/`list_directory`/`read_file`; writes require the `MIOS_WRITE_ALLOWED_PATHS` whitelist. Bake the `fapolicyd` known-libs allow-list plus MiOS carve-outs into the bootc image from the `Containerfile`. Gate `[security].mcp_sandbox = false` (default off, degrade-open).
**Where:** `usr/libexec/mios/mcp-server-runner`, `Containerfile`, `usr/share/mios/mios.toml`
**Done When:** A `../../etc/passwd` traversal attempt is blocked at the gatekeeper, `fapolicyd` blocks an unsigned binary dropped into `/tmp`, and with `mcp_sandbox=false` tools still execute in the host process (degrade-open).
**Why:** An MCP bundle is arbitrary third-party code holding agent privileges; with no chokepoint, one hostile or sloppy tool reads and writes everything the agent can reach.
**Dep:** T-005 (BOOT-04), operator-VM [VM].
**Status:** done-by-code | **Domain:** Security

---

## T-033 -- SEC-02: Semantic firewall -- CaMeL-class taint propagation through the scratchpad  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- untrusted content can never drive a side-effecting verb without a human in the loop.
**What+How:** Extend the landed Phase B.3 firewall: tag every tool result from an untrusted source (web fetch, RAG, external API) `tainted=true` and propagate the tag through the whole scratchpad. In `dispatch_mios_verb`, run the `has_tainted` check before any side-effecting verb -- WRITE-class, `service_restart`, `container_restart`, or `open_url` to a non-allowlisted domain. Tainted + side-effecting routes to the `mios_hitl` queue instead of executing. Every deny condition is read from `mios.toml` SSOT; no hardcoded deny-list (Law 7). Log `event(kind="firewall_decision", verdict=allow|block|hitl)`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** A web-fetched result driving `service_restart` lands in HITL rather than executing, a local-only result driving the same verb executes directly, and every decision is a pgvector `event` row carrying a `verdict` field.
**Why:** Prompt injection inside a fetched page currently reaches side-effecting verbs directly -- the basic firewall inspects the call site but has no notion of where the driving data came from.
**Dep:** Phase A.3 (taint tags, landed), Phase B.3 (basic firewall, landed).
**Status:** built-gated-off | **Domain:** Security

---

## T-034 -- SEC-03: SHA-256 hash-chain the event bus so the audit log is tamper-evident  (WS-SEC | P2 | M)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- provenance of what the autonomous plane did is cryptographically verifiable.
**What+How:** For every new `event` row compute `SHA-256(prev_hash || event_data)` and store it as `chain_hash` (bootstrap: first row is `SHA-256(event_data)`), implemented in `mios_audit.py` with the column added in `schema-init.sql`. Ship a `mios-chain-verify` CLI that walks and validates the whole chain, and expose the same verification at `GET /v1/audit/chain/verify`. Gated by `[audit].chain_enable`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql`, `usr/libexec/mios/mios-chain-verify`
**Done When:** `mios-chain-verify` returns VALID on an unmodified log, reports CHAIN BREAK at `event_id=N` after a row is manually altered, and the HTTP endpoint returns the identical result.
**Why:** The event table is the only record of autonomous action; unchained, a compromised agent (or a careless operator) can edit its own audit trail and nothing will ever detect it.
**Dep:** Ed25519 passports (landed).
**Status:** done-by-code | **Domain:** Security/Audit

---

## T-035 -- MEM-02: Self-editing tiered memory (MemGPT-style) over pgvector  (WS-VECTOR | P2 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- the agent curates a durable memory tier instead of forgetting the operator every session.
**What+How:** Expose `memory_append` and `memory_replace` verbs writing an agent-curated pinned tier into the existing pgvector `agent_memory` table, with blocks labelled `persona`/`task`/`preference`/`fact`. At 70% of `n_ctx` warn the agent; at 100% evict oldest FIFO turns and write a recursive summary into the scratchpad head. Thresholds live under `[memory]` in SSOT. Additive to the T-021 KV paging path, not a replacement for it.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[memory]`)
**Done When:** `memory_append {"label":"persona","content":"..."}` persists across turns, a warning event fires at 70% context fill, at 100% the oldest turns are evicted with a summary prepended, and archived turns are queryable in `agent_memory`.
**Why:** Without a self-edited tier the agent re-learns operator preferences from scratch each session, and a full context window truncates silently -- taking the earliest instructions with it.
**Dep:** T-021 (MEM-01), T-027 (B2 tiering verified).
**Status:** done | **Domain:** Memory

---

## T-036 -- MEM-03: Context compaction and stale tool-result clearing  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the per-session token budget stays bounded with a graceful summarize instead of a silent truncation.
**What+How:** Every `[memory].compaction_interval` turns (default 20), scan the active context and drop tool-result messages older than `[memory].tool_result_ttl_turns` (default 5 turns ago). At `[memory].compaction_threshold_pct` of `n_ctx` (default 80%), summarize and reinitialize the context as summary + last N turns. Log `event(kind="context_compaction", tokens_before=N, tokens_after=M)`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** After 25 turns the turn-1 tool results are absent from the active context, a compaction event appears in pgvector at the threshold, and chat quality is not degraded after compaction.
**Why:** Stale tool blobs dominate the window and drive cost and latency up on every subsequent turn; without compaction a long session simply hits `n_ctx` and hard-truncates.
**Dep:** T-035 (MEM-02).
**Status:** done | **Domain:** Memory/Context

---

## T-037 -- SEC-04: Per-agent access control with HITL at the verb-dispatch chokepoint  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- privilege is per-agent, so a low-trust lane cannot invoke destructive verbs.
**What+How:** Map `agent_id -> privilege_group` from `[agents.<name>].privilege_group` (default `routine`). At `dispatch_mios_verb`, compare the calling agent's group against the verb's tier from `[verbs.<name>].tier`; a `destructive`-tier verb routes to the `mios_hitl` queue before execution. Log `event(kind="acl_decision", agent=..., verb=..., verdict=...)`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** A `routine`-privilege agent calling `container_restart` routes to HITL, a `privileged`-privilege agent calls it directly, and every ACL decision lands in the `event` table.
**Why:** Every agent shares one privilege level today, so a research or edge-federated agent can invoke exactly the same destructive verbs as the operator's own trusted lane.
**Dep:** T-033 (SEC-02 semantic firewall).
**Status:** done | **Domain:** Security/Orchestration

---

## T-038 -- CU-01: Computer-use action hierarchy, pinned coordinate scaling, verify-after-action  (WS-GUARD | P2 | L)
**Goal:** E-24 Autonomy guardrails -- GUI automation is bounded and self-verifying, escalating to a human instead of acting blind.
**What+How:** Encode the action hierarchy as an explicit router -- Tier 1 typed verb/MCP call, Tier 2 accessibility tree (Windows UIA via `mios-windows`, AT-SPI on Linux), Tier 3 vision grounding (`pc_click`). Fix coordinate scaling by pinning the convention per VLM (Qwen2.5-VL = absolute pixels, Qwen3-VL = normalized 0-1000) and applying the right one for the active model; HiDPI rescale multiplies normalized coords by `display_width/1000` and `display_height/1000`. Add verify-after-action: capture a screenshot/a11y diff after each VLM click, confirm the state changed, retry up to 3 times with re-grounding. Add wait-for-stable-element polling of the a11y tree, bounded at 10 iterations.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/libexec/mios/mios-pc-control`, `usr/share/mios/mios.toml`
**Done When:** A click tries the a11y tree first and only falls back to vision on a11y failure, a Qwen3-VL normalized `(512,384)` maps correctly to physical pixels on 1920x1080, a failed click is caught by verify-after-action and retried with re-grounding, and 3 exhausted retries escalate to HITL.
**Why:** Mis-scaled coordinates make the model click the wrong pixel, and with no verification step the agent continues reasoning about a UI state it never actually reached -- the surface is only `partial` today.
**Dep:** T-065 (GAP-6 smart_resize -- canonical scaling math).
**Status:** partial | **Domain:** Computer Use

---

## T-039 -- OBS-02: AIOS-Bench harness -- task accuracy crossed with systems metrics, in CI  (WS-TESTGOV | P2 | L)
**Goal:** E-05 Test and CI governance -- the agent plane gets the measured quality gate the shell plane already has.
**What+How:** Implement a `mios-bench` CLI that runs a fixed trajectory suite from `usr/share/mios/bench/` through the live `agent-pipe`. Report `pass@1`, `pass@k`, `pass^k` (column supplied by T-049), throughput, agent waiting time, and fairness under concurrency. Wire it into the CI pipeline so it runs on every image build, and feed low-`pass^k` cases into the LoRA/skill-improve loops.
**Where:** `usr/libexec/mios/mios-bench`, `usr/share/mios/bench/`, CI pipeline
**Done When:** `mios-bench run --suite gaia-lite` prints a table with pass@1, pass@k, pass^k, throughput and avg_wait; the CI image-build log contains that output; and deliberately breaking routing reduces pass@1 measurably.
**Why:** With no accuracy-plus-systems measurement on each build, an orchestration change that quietly halves task success rate ships to the fleet undetected.
**Dep:** T-049 (GAP-3 pass^k gate -- for the pass^k column).
**Status:** done | **Domain:** Observability/Reliability

---

## T-040 -- OBS-03: Record-and-replay determinism for the agent plane  (WS-TESTGOV | P2 | M)
**Goal:** E-05 Test and CI governance -- non-deterministic agent failures become reproducible test cases.
**What+How:** Record all LLM I/O (prompt + completion) and all tool I/O into the pgvector `session` table. Add a replay mode that serves the logged responses instead of calling the LLM or the tools, seeding random sampling so the original stochasticity reproduces. Make the log tamper-evident by hash-chaining its entries through T-034. Toggles in `mios.toml`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** A recorded session replays byte-identically, `mios-chain-verify` confirms the replay log is unmodified, and replay runs about 5x faster than live because no LLM call is made.
**Why:** Agent bugs are stochastic and currently unreproducible -- every debugging attempt re-rolls the dice, burns GPU time, and may never hit the same failure again.
**Dep:** T-034 (SEC-03 hash chain).
**Status:** done | **Domain:** Observability

---

## T-041 -- C3: De-publish searxng to loopback and drop the heavy-alt stray port  (WS-ZEROHC | P2 | S)
**Goal:** E-12 ZERO-HARDCODES -- literal, unintended bind addresses stop leaking services onto the LAN.
**What+How:** In `mios-searxng.container` change `PublishPort=0.0.0.0:8888:8888` to `PublishPort=127.0.0.1:8888:8888`. In `mios-llm-heavy-alt.container` remove `PublishPort=11440:11440` entirely -- heavy-alt is reached inside the pod and needs no host bind. Landed form: Granian limited to `127.0.0.1` inside the host-networked pod, heavy-alt publishing nothing.
**Where:** `usr/share/containers/systemd/mios-searxng.container`, `usr/share/containers/systemd/mios-llm-heavy-alt.container`
**Done When:** `ss -ltnp | grep 8888` shows `127.0.0.1:8888` (or 8899), port 11440 is absent from `ss -ltnp`, and `curl http://localhost:8888` still returns searxng HTML.
**Why:** Two internal services are currently reachable from the whole LAN with no reason to be -- a stray host bind is free lateral movement for anything already on the network.
**Dep:** None.
**Status:** done-by-code | **Domain:** Ops/Networking

---

## T-042 -- C4: Port collapse -- render every `PublishPort=` from the `[ports]` SSOT  (WS-PORTFLOAT | P2 | M)
**Goal:** E-13 Ports are allocated from SSOT, not hand-assigned -- one declared port value reaches every Quadlet by projection.
**What+How:** Extend `tools/generate-pod-quadlets.py` to resolve and render `PublishPort=` from `[ports.<name>]` in SSOT rather than literals; have `.container` files reference `MIOS_PORT_*` env vars sourced from `EnvironmentFile=install.env` generated at build time by the `Containerfile`. Collapse roughly 24 raw host binds down to ~8 deliberate front doors (53, 3053, 3000, 49922, 8800, 3030, 8640, 8642, plus host sshd/cockpit). Add `check_container_ports` to `98-drift-checks.sh`, and strip literal ports out of the guacamole and searxng container files by loading `install.env`.
**Where:** `tools/generate-pod-quadlets.py`, `Containerfile`, all `.container` files
**Done When:** Setting `[ports].owui = 3031` and re-running the generator publishes OWUI on `:3031`, and `just drift-gate` fails on a hand-written port literal in any `.container` file.
**Why:** Hand-numbered `PublishPort` lines drift away from SSOT, collide with each other, and silently expose front doors the operator never chose to open.
**Dep:** T-005 (BOOT-04), T-015 (C0).
**Status:** done-by-code | **Domain:** Ops/Networking

---

## T-043 -- D1: Remote/edge agent template with auto-join and auto-drop  (WS-DB | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- every federated peer is an interchangeable OpenAI endpoint whose membership is SSOT-declared and self-maintaining.
**What+How:** Land the `kind=remote-http|edge|node` template from T-006 carrying `auth{...}` and `trust{...}` blocks. The vendor SSOT ships `endpoint=""` for privacy; the real endpoint is supplied by the `/etc/mios` host overlay layer. Make `_load_node_pool` in `server.py` auto-join a node when it is reachable and auto-drop it when it disappears. Test by declaring a loopback "remote" node in the `/etc` overlay.
**Where:** `usr/share/mios/mios.toml` (`[agents.pi-edge]`, `[nodes.*]`), `usr/lib/mios/agent-pipe/server.py`
**Done When:** The loopback overlay node appears in `/v1/cluster/health` while reachable, auto-drops within 30s once the endpoint dies, and auto-rejoins without restarting agent-pipe when it returns.
**Why:** Without auto-join/auto-drop every edge box is a hand-edited static entry, and a dead node keeps receiving dispatched work until a human notices the failures.
**Dep:** T-006 (A1), T-010 (FED-G2 auth).
**Status:** done-by-code | **Domain:** Federation/Edge

---

## T-044 -- F1: Re-vectorize the OWUI documentation knowledge collection on every install  (WS-VECTOR | P2 | S)
**Goal:** E-23 DB-driven configuration and vector recall -- shipped documentation is actually retrievable, not merely registered.
**What+How:** Re-index the "MiOS Documentation" collection through the OWUI retrieval API (`mios-owui-apply-knowledge` calls it over localhost), and wire that re-index into the firstboot chain alongside T-018 so it runs on every reinstall rather than needing a manual trigger.
**Where:** `usr/lib/systemd/system/mios-open-webui-firstboot.*`
**Done When:** `knowledge_search "bootc"` returns >= 3 relevant hits, and re-indexing runs automatically on a fresh reinstall with no operator step.
**Why:** 32 files are registered in the OWUI knowledge collection but were never vectorized into ChromaDB, so `knowledge_search` returns 0 hits and the OS's own documentation is invisible to the agent that needs it.
**Dep:** T-018 (E1 firstboot wiring).
**Status:** done-by-code | **Domain:** UX/RAG

---

## T-045 -- F2: Build the coderun-sandbox image for agent-authored code [NET]  (WS-CODEMODE | P2 | M)
**Goal:** E-24 Autonomy guardrails -- agent-generated code executes in a disposable jail, never inside the agent-pipe process.
**What+How:** Add `images/coderun-sandbox/Containerfile` building `mios-coderun-sandbox` (Python 3.12+, Node 22, basic utils, no GPU) -- build needs egress [NET]. Mount only `/run/coderun.sock` and a per-session tmpfs, with no host filesystem access. Register it as `usr/share/containers/systemd/mios-coderun-sandbox.container`, reusing the SEC-01 isolation pattern.
**Where:** `images/coderun-sandbox/Containerfile`, `usr/share/containers/systemd/mios-coderun-sandbox.container`
**Done When:** `run_sandboxed_code {"language":"python","code":"print(1+1)"}` returns `{"output":"2"}`, the container can reach no host path beyond its tmpfs, and it restarts cleanly after a crash.
**Why:** Otherwise model-authored code runs with the agent-pipe's own filesystem and network reach, so one bad generated snippet is a full-host incident.
**Dep:** T-032 (SEC-01 isolation pattern). Needs egress [NET].
**Status:** done | **Domain:** Sandboxing

---

## T-046 -- WS-G: MEMORY.md honesty reconciliation against the blueprint  (WS-DOCS | P2 | S)
**Goal:** E-06 Test and documentation harness -- the doc set an arriving agent trusts states the real status, not an aspirational one.
**What+How:** Audit `MEMORY.md` and every memory topic file against the `engineering-blueprint`. Re-tag WS-0B (port collapse), opencode-peer, kernel Stage-2, the tiering loop and the governance gates from DONE to `built-but-gated/partial`. Trim the index to <= 24KB. Add the policy header: "DONE requires active + live-fired, not built + gated-OFF".
**Where:** `~/.claude/.../MEMORY.md` and its topic files
**Done When:** No entry in MEMORY.md carries a DONE tag for anything that maps to an open task in TASKS.md, the index is <= 24KB, and the policy header is the first block in the file.
**Why:** An agent that believes a stale DONE skips work that was never finished; the oversized index also burns context budget on every single session load.
**Dep:** None.
**Status:** done-by-code | **Domain:** Documentation

---

## T-047 -- GAP-1: RouteMoA pre-synthesis input-diversity gate for council fan-out  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the council stops burning VRAM to hear one opinion restated k times.
**What+How:** Before handing k council responses to the aggregator, score pairwise cosine similarity over the already-computed 768-d embeddings (no extra model calls). Pick the initial member by lowest mean similarity, `i0 = argmin_i((1/N) sum_j S_ij)`, then expand minimax, `it = argmin_i(max_{q in Q} S_iq)`. Replace any slot whose similarity to the selected set exceeds `[council].diversity_threshold` (default 0.92) with the next most-orthogonal candidate. Gate `[council].diversity_gate = false` (default off, degrade-open).
**Where:** `usr/lib/mios/agent-pipe/server.py` (council synthesis path), `usr/share/mios/mios.toml`
**Done When:** Two semantically identical council responses cause the second to be swapped for the next most-orthogonal candidate, `/v1/cluster/health` reports `diversity_gate_active: true` when enabled, no extra model calls are issued, and with the gate off output is byte-identical to today.
**Why:** Nothing governs semantic diversity before the aggregator fires, so a correlated ensemble spends k lanes of VRAM producing near-duplicate input and degrades the synthesis it feeds.
**Dep:** T-006 (A1), T-021 (MEM-01 -- embeddings from llm-light).
**Status:** done-by-code | **Domain:** Orchestration

---

## T-048 -- GAP-2: MOSAIC confidence-aware aggregator bypass on converged councils  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the most expensive call in a council turn is skipped when there is nothing to reconcile.
**What+How:** After fan-out, compute pairwise cosine similarity across the k council responses. If every pair exceeds `[council].aggregator_bypass_threshold` (default 0.95, deliberately conservative), bypass the aggregator LLM and return the highest-confidence individual response. Log `event(kind="aggregator_bypass", council_size=k, mean_similarity=...)`. Gate `[council].aggregator_bypass = false` (default off).
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** Three identical council responses above threshold produce no aggregator LLM call plus one logged bypass event, `/v1/cluster/health` reports `aggregator_calls_bypassed_pct`, and with the gate off output is byte-identical to today.
**Why:** The final aggregator call fires on every council turn even when all members already agree -- reference work measures ~45.7% of those calls as bypassable at +0.24pp accuracy, so today's behaviour is pure wasted VRAM and latency.
**Dep:** T-047 (GAP-1 -- shares embedding computation), T-039 (OBS-02 bench for tuning).
**Status:** done-by-code | **Domain:** Scheduling/Orchestration

---

## T-049 -- GAP-3: Make pass^k the hard gate on skill promotion  (WS-TESTGOV | P2 | M)
**Goal:** E-05 Test and CI governance -- nothing enters the autonomous loop until it is reliable across repeats, not merely lucky once.
**What+How:** Extend `mios-skills promote` so that after the existing tests it replays the affected trajectory `[reliability].pass_and_k_count` times (default 3) and requires ALL k runs to succeed -- `tool_call.success=true`, zero `firewall_block` events, no HITL escalation. A single failure vetoes, reporting `pass^k gate: FAIL (2/3 succeeded, required 3/3)`. Add a `pass_and_k_rate` column to the AIOS-bench output (T-039). For DGM-class self-rewrites (T-064) scale k to `[reliability].pass_and_k_dgm_count` (default 5).
**Where:** `usr/libexec/mios/mios-skills`, `usr/share/mios/mios.toml`
**Done When:** A skill failing 1-of-3 replay runs is rejected with the veto message, a 3-of-3 skill promotes normally, and `mios-bench` output includes the `pass^k` column.
**Why:** Promotion currently accepts `pass@k` optimism: a 61%-reliable skill looks acceptable at k=1 but is under 25% reliable at k=8, and it gets promoted into the self-driving loop regardless.
**Dep:** T-039 (OBS-02).
**Status:** done-by-code | **Domain:** Reliability

---

## T-050 -- GAP-5: Rechunking delta distribution for edge and offline OCI updates  (WS-BOOTC | P2 | L)
**Goal:** E-20 The bootc-native install legs -- an air-gapped or thin-uplink machine can take a signed update without pulling the whole image.
**What+How:** Build `mios-rechunk`: a post-build binary diff between the new OCI layer blobs and the prior manifest (zstd-compressed block comparison) emitting a delta bundle of changed chunks only, targeting `delta_size = ((original - rechunked)/original)*100 ~= 80-90%` and validated against `podman image diff`. Build `mios-oci-delta-apply.service` to fetch the bundle, verify its SHA-256 signature via the T-034 chain, apply the chunks, and signal `bootc` to stage. Both baked in by the `Containerfile`. Gate `[distribution].rechunk_enable = false` (default off).
**Where:** `usr/libexec/mios/mios-rechunk` (new), `usr/lib/systemd/system/mios-oci-delta-apply.service` (new), `usr/share/mios/mios.toml`, `Containerfile`
**Done When:** A patch changing only `server.py` produces a delta bundle <= 15% of full image size, `mios-oci-delta-apply` applies it and `bootc status` shows the new deployment staged, and a SHA-256 signature mismatch aborts the apply with an error.
**Why:** Every update currently ships the full multi-GB OCI image, saturating edge and IoT uplinks and making routine `bootc upgrade` impractical anywhere off a fat link.
**Dep:** T-002 (BOOT-01), T-034 (SEC-03 SHA-256 chain).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: the rechunk delta path ships as `automation/build/rechunk.sh`. | **Domain:** Distribution/Edge

## T-051 -- FED-G7: Route A2A fan-out on the full AgentCard `skills[]` array  (WS-FED | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- peer selection is decided by embedded skill semantics recorded in Postgres rather than ad-hoc string proximity, so every federated peer stays an interchangeable, correctly-chosen OpenAI endpoint (NS-2).
**What+How:** Replace the simplified strength-token matching inside `_pick_fanout_agents` in the agent-pipe `server.py` with a semantic/embedding match over the peer AgentCard's complete `skills[]` array. An explicitly declared skill must override token proximity when the two disagree. Write every routing decision as a row in the `event` table so a dispatch can be replayed and explained after the fact.
**Where:** `usr/lib/mios/agent-pipe/server.py`
**Done When:** A task tagged `code-review` fans out to the peer whose AgentCard lists `code-review` in `skills[]` even when another peer scores higher on strength tokens, and the chosen route appears as an `event` row.
**Why:** Token-proximity routing silently sends work to peers that cannot do it -- the failure is a bad answer, not an error, and with no `event` row there is nothing to debug afterwards.
**Dep:** T-012 (FED-G4).
**Status:** done-by-code | **Domain:** Federation

## T-052 -- FED-G8: Caller-key store with hot-reloading revocation list  (WS-FED | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the agent plane's one front door can revoke a compromised caller instantly, so federation cannot become an unbounded, unauthenticated ingress into the host.
**What+How:** Back the auth gate (T-001) with an identity/CRL store at `/etc/mios/ai/v1/caller-keys.json` and add `POST /v1/admin/keys/revoke`. Revoked keys are rejected at the auth gate and the CRL is re-read live -- no service restart. Landed via `caller_key_revoke` in `mios_a2a`/`mios_crl`; the originally-specified `mios_principal` module was orphaned and REMOVED as dead code, so do not reintroduce it.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `/etc/mios/ai/v1/caller-keys.json`
**Done When:** A revoked key gets `401` and a valid key gets `200`, with the revocation taking effect after a CRL edit alone (no `systemctl restart`).
**Why:** Without live revocation, a leaked federation key stays valid until someone reboots the AI plane -- the blast radius of one leaked credential is every peer call it can make.
**Dep:** T-001 (FED-G1).
**Status:** done-by-code | **Domain:** Federation/Security

## T-053 -- FED-G9: Loopback-default bind with auth-gated scoped publish  (WS-FED | P2 | S)
**Goal:** E-12 ZERO-HARDCODES -- bind addresses come from the `[network]` loopback/bind_all SSOT keys and default closed, so the AI front door is never exposed by an unreviewed literal in a unit file (NS-4).
**What+How:** Change the default listen address for `:8640` (agent-pipe) and `:8642` (Hermes) to `127.0.0.1` via `_bind_host`, and publish on `0.0.0.0` only when `[security].require_auth=true` AND the firewall scopes the listener to `172.16/12`. The bind host is a resolved SSOT value in the unit files, not a written-in constant.
**Where:** `usr/lib/systemd/system/mios-agent-pipe.service` | `usr/lib/systemd/system/hermes-agent.service`
**Done When:** `ss -ltnp | grep 8640` shows `127.0.0.1` on a default install, and shows `0.0.0.0` only after auth is turned on.
**Why:** A default all-interfaces bind puts an unauthenticated local-inference endpoint on every network the machine touches the moment the service starts.
**Dep:** T-001 (FED-G1).
**Status:** done-by-code | **Domain:** Federation/Networking

## T-076 -- GWY-01: Letta memory-backend sidecar, Phase 1 deploy (RETIRED)  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- tiered Core/Recall/Archival memory over the existing `mios-pgvector` instance, now satisfied natively instead of by a sidecar.
**What+How:** As specified: a `mios-letta-server.container` Quadlet (`ghcr.io/letta-ai/letta:latest`, `mios-net`, `:8283`) pointed at a `mios_letta` schema inside the shared PostgreSQL pod, with `LETTA_LLM_*` / `LETTA_EMBEDDING_*` forced to the local `/v1` endpoint (Law 5), an `[agents.letta]` block in `mios.toml`, a `CREATE SCHEMA IF NOT EXISTS mios_letta;` fragment in `schema-init.sql`, and the unit added to `mios-ai.target` Wants. RETIRED: deployed at 10220bf, removed at d90985d in favour of the native `mios_scratchpad` + `mios_cold_evict` path (T-101/T-102). Treat as history -- do not redeploy.
**Where:** `usr/share/containers/systemd/mios-letta-server.container` | `usr/share/mios/postgres/schema-init.sql` | `usr/share/mios/mios.toml` | `usr/lib/systemd/system/mios-ai.target`
**Done When:** No Letta artefact remains in the tree -- `usr/share/containers/systemd/mios-letta-server.container` does not exist, `[agents.letta]` is absent from `mios.toml`, and the memory verbs resolve through `mios_scratchpad`/`mios_cold_evict`.
**Why:** Leaving the retired sidecar half-referenced re-adds an image to the fleet that E-17 is trying to shrink, and leaves two competing memory backends for one verb surface.
**Dep:** T-003 (C0 pod consolidation), T-028 (B1 pgvector schema). Needs egress [NET] for initial image pull.
**Status:** retired | **Domain:** Memory/Gateway

## T-077 -- GWY-02: Wire self-editing memory verbs to the Letta backend (RETIRED)  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the `memory_*` verb surface delegates tiering and compaction to one owner of the persistent store; served natively rather than by Letta.
**What+How:** As specified: a `LettaMemoryClient` (`httpx.AsyncClient` at `[agents.letta].endpoint`) in `server.py` routing `memory_append`/`memory_replace` to Letta memory blocks and `memory_search` to archival search, firing compaction at 70% context fill and an oldest-message flush at 100%, keeping `agent_memory` as a read-only snapshot target, all behind `[agents.letta].memory_backend = false` (degrade-open to the pgvector-direct path). RETIRED with the container at d90985d; MEM-02/MEM-03 (T-035/T-036) are served by `mios_scratchpad` + `mios_cold_evict`.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`
**Done When:** `server.py` contains no `LettaMemoryClient` and no `[agents.letta]` reads, and `memory_append`/`memory_search` round-trip through the native path with the T-035/T-036 criteria still met.
**Why:** A dead client class in the ~9k-line `server.py` god-module (TD register, E-02) is dead weight that the next reader has to prove is unreachable.
**Dep:** T-076 (GWY-01 Letta server live), T-035 (MEM-02), T-036 (MEM-03).
**Status:** retired | **Domain:** Memory/Orchestration

## T-054 -- ORCH-06: Deterministic zero-token orchestration via Conductor CLI  (WS-H3 | P3 | L)
**Goal:** E-24 Autonomy guardrails -- multi-step work runs as a declared, bounded workflow instead of a probabilistic prompt chain that can fan out indefinitely.
**What+How:** Add a workflow directory `usr/share/mios/conductor/` holding YAML + Jinja2 workflow definitions, and a Conductor CLI execution path in `server.py` that runs them with real parallel execution groups honouring `fail_fast` and `continue_on_error` semantics. Ship gated off with `[orchestration].conductor_enable=false` so the existing prompt-chaining path stays the default until parity is proven.
**Where:** `usr/share/mios/conductor/` | `usr/lib/mios/agent-pipe/server.py`
**Done When:** A 3-step parallel workflow declared in YAML executes deterministically -- same step order, same outputs across runs -- and a failing step honours `fail_fast` by halting the group rather than continuing.
**Why:** Prompt-chained orchestration spends tokens re-deciding a fixed sequence every turn and gives no reproducible execution trace when a multi-step job goes wrong.
**Dep:** T-031 (ORCH-04 ReAct loop).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: `usr/share/mios/conductor/test-workflow.yaml` + `mios_pipe/routing/conductor.py`, reached from `server.py` behind the `[orchestration].conductor_enable` gate. | **Domain:** Orchestration

## T-055 -- MEM-04: Hindsight multi-strategy retrieval replaces the MAIA v8.0 pools  (WS-H4 | P3 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- one Postgres+pgvector datastore answers recall through several complementary strategies instead of a bespoke legacy pool.
**What+How:** Retire the legacy MAIA v8.0 runtime pools and run MIT-licensed Hindsight inside the `mios-pgvector` container, exposing parallel retrieval across all four strategies -- semantic vector, BM25 keyword, graph relational and temporal -- with results ranked and merged into one answer set for `knowledge_search`.
**Where:** `usr/share/containers/systemd/mios-pgvector.container`
**Done When:** `knowledge_search "bootc"` returns a single merged, ranked result set with contributions traceable to all four retrieval strategies.
**Why:** Pure vector similarity misses exact-token and time-ordered facts, so recall quietly drops answers the datastore actually holds.
**Dep:** T-035 (MEM-02).
**Status:** done-by-code | **Domain:** Memory

## T-056 -- MEM-05: KV cache hierarchy plus sleep-time memory consolidation  (WS-VECTOR | P3 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- expensive context is reused rather than recomputed, and memory upkeep happens off the interactive latency path.
**What+How:** Finish SGLang HiCache on `mios-llm-heavy` so the ~17K-token tool-surface prefix is reused across requests and idle KV spills GPU -> RAM -> disk. Give the daemon-agent a scheduled sleep-time job that consolidates pgvector `knowledge` rows and shared memory blocks while idle, and upgrade recall ranking from plain relevance to `recency x importance x relevance`.
**Where:** `usr/share/mios/llamacpp/mios-llm-light.yaml` | `usr/lib/mios/agent-pipe/server.py`
**Done When:** The 17K-token prefix hits HiCache on the second request (measurable prefill drop) and the nightly consolidation job reduces `agent_memory` row count by at least 20% without losing a recallable fact.
**Why:** Re-prefilling a 17K-token tool surface on every turn burns GPU time on identical input, while an ever-growing `agent_memory` makes every subsequent recall slower.
**Dep:** T-035 (MEM-02), T-021 (MEM-01).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: `--cache-reuse 256` in `usr/share/mios/llamacpp/mios-llm-light.yaml` plus the `_consolidate_memory_sweep_once` sweep in `mios_pipe/kernel/daemons.py`. | **Domain:** Memory/Scheduling

## T-057 -- ORCH-07: Rich relationship edges on the personal knowledge graph  (WS-VECTOR | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the datastore stores relationships, not just rows, so the agent can resolve possessive references against the operator's own machine.
**What+How:** Extend the `person` table in `schema-init.sql` with graph edges -- `pref`, `device` and `app_install` rows plus their relationship joins -- using PostgreSQL joins and JSONB, and reuse the existing `vector(768)` HNSW columns for semantic recall. Teach the router/refine pass in `server.py` to walk those edges so "my browser" grounds through the preference edge to the concrete `chromedev` install.
**Where:** `usr/share/mios/postgres/schema-init.sql` | `usr/lib/mios/agent-pipe/server.py`
**Done When:** "Open my browser" launches the application named by the `app_install` preference edge with no application named in the prompt.
**Why:** Without edges the agent either asks the operator to name their own defaults every time or guesses, which makes possessive phrasing unusable.
**Dep:** T-035 (MEM-02).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: `kg_lookup` resolves alias -> resolves_to -> app_install in `mios_pipe/memory/knowledge.py`, covered by `test_mios_knowledge.py`. | **Domain:** Memory/UX

## T-058 -- SCHED-03: Autellix-style MLFQ scheduling over whole agent programs [VM]  (WS-GUARD | P3 | XL)
**Goal:** E-24 Autonomy guardrails -- background swarm work is preempted by foreground turns on lane priority, so a batch job cannot make the interactive assistant feel dead.
**What+How:** Schedule at the level of the whole agent task/DAG rather than the individual LLM request: an Autellix-style multi-level feedback queue in `server.py` with demand-aware LRU eviction for victim selection, its thresholds declared in `mios.toml`. Engage the MLFQ only under contention -- it costs more than it saves on trivial small-model turns -- so the gate itself is part of the deliverable. Reference implementations report 4-15x throughput.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`
**Done When:** With four or more concurrent tasks running, a short interactive query returns in under 500ms while a long swarm batch continues in parallel.
**Why:** Per-request FIFO lets one long DAG monopolise the lane, so the operator's own prompt waits behind a background job on their own hardware.
**Dep:** T-019 (SCHED-01), T-020 (SCHED-02). Operator VM [VM].
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: the MLFQ ordering (LRU eviction + contention-gated priority decay) in `mios_pipe/scheduler/preempt.py`, covered by `test_mios_preempt.py`. | **Domain:** Scheduling

## T-059 -- DATA-01: Declarative agent cards and an A2A-discoverable directory  (WS-VECTOR | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the agent roster is a queryable `directory_entry` surface, not a static file each peer must read.
**What+How:** Give every agent an `(author, name, version)` card reusing the A2A card schema, and serve the whole roster from the `/v1/agents` endpoint in `server.py` as an A2A-discoverable directory with card links. A discovering peer queries that endpoint instead of parsing a shipped file.
**Where:** `usr/lib/mios/agent-pipe/server.py` -- `/v1/agents` endpoint
**Done When:** `GET /v1/agents` returns every registered agent as an `(author, name, version)` tuple with a resolvable A2A card link.
**Why:** File-scraped rosters go stale the moment an agent is added or renamed, and a remote peer has no way to read a file it cannot reach.
**Dep:** T-012 (FED-G4), T-022 (FED-CONSUME).
**Status:** done | **Domain:** Federation

## T-060 -- DATA-02: Bitemporal versioning and rollback for self-edited core facts  (WS-DB | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- a self-editing agent's writes are reversible, so memory is an auditable store rather than a destructive overwrite.
**What+How:** Add `valid_from`/`valid_to` columns to the `agent_memory` and `knowledge` tables in `schema-init.sql` so a replace supersedes rather than deletes, run a periodic cosine-dedup compaction over near-identical rows (similarity > 0.98) to stop history from unbounded growth, and expose a `memory_rollback(to_timestamp)` verb in `server.py`.
**Where:** `usr/share/mios/postgres/schema-init.sql` | `usr/lib/mios/agent-pipe/server.py`
**Done When:** After a wrong `memory_replace`, calling `memory_rollback` with a prior timestamp restores the previous fact and a subsequent `memory_search` returns it.
**Why:** Today one bad self-edit permanently destroys the fact it overwrote, with no recovery path short of a database restore.
**Dep:** T-035 (MEM-02).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: `valid_from`/`valid_to` columns on `knowledge` and `agent_memory` in `usr/share/mios/postgres/schema-init.sql`. | **Domain:** Memory/Data

## T-061 -- ORCH-09: Code-mode execution for heavy verb chains and recipes  (WS-CODEMODE | P3 | L)
**Goal:** E-24 Autonomy guardrails -- bulk intermediate data never enters model context, so a large fetch cannot blow a session's token budget.
**What+How:** Route multi-step verb chains and the recipe layer through the sandboxed `mios_codemode` path so intermediate blobs are produced, filtered and discarded inside the sandbox, with only the filtered result returned to the model. Declare the routing threshold in `mios.toml`. Reference: Anthropic reports ~98.7% token reduction on this pattern.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`
**Done When:** A recipe fetching 50KB of web content executes in the sandbox and returns roughly a 200-token summary into model context, with the raw payload absent from the transcript.
**Why:** Piping raw tool output through the model burns context on data the model never needed to see, and pushes long chains into truncation.
**Dep:** T-045 (F2 coderun-sandbox).
**Status:** done-by-code -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: the `[code_mode]` SSOT section and the `code_mode` verb. | **Domain:** Orchestration/Memory

## T-062 -- B3: Self-improvement ACT half -- propose, prove, stage  (WS-B3 | P3 | XL)
**Goal:** E-24 Autonomy guardrails -- self-modification is bounded by construction: nothing reaches main without a proof and a human, and the whole path is default-off.
**What+How:** The OBSERVE half exists; implement the ACT half in `mios_selfimprove_act.py` (propose / prove / isolate / decide) so the agent proposes a code diff against a recurring failure pattern, submits it to the T-064 DGM sandbox for a utility proof, logs `event(kind="dgm_veto")` and discards on veto, and on approval runs `git apply` plus `just drift-gate` and commits to a staging branch for human review. Ships gated behind `[selfimprove].act_enabled` (default off; the spec named `[self_improve].enable`). MUST NOT be enabled before T-064 is in place.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml`
**Done When:** A diff that passes the DGM sandbox lands on a staging branch with the drift-gate green, and a vetoed diff leaves the working tree byte-identical with a logged veto event.
**Why:** An unproven self-rewrite path is the one class of bug that edits its own guardrails; without the propose/prove/stage split, the only options are no self-improvement or an unreviewed one.
**Dep:** T-064 (GAP-4 DGM sandbox), T-049 (GAP-3 pass^k gate).
**Status:** done-by-code | **Domain:** Self-Improvement

## T-063 -- B4: promptver consumer -- version-resolved prompt registry  (WS-B4 | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- prompt bodies are DB-resolved facts referenced by name and version, not literals compiled into the agent plane.
**What+How:** Wire the `promptver` consumer (`PromptRegistry`) so prompt version hops resolve from the pgvector `prompt_version` table instead of hardcoded strings in `server.py`. Agents reference a prompt by an `(name, version)` tuple and the loader returns the current canonical body for that tuple.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`
**Done When:** Updating the canonical body for a version in `prompt_version` changes agent behaviour on the next turn with no code edit, restart or redeploy.
**Why:** Inline prompt strings mean every wording change is a code change, an image rebuild and a redeploy -- and duplicated copies drift apart between agents.
**Dep:** None.
**Status:** done-by-code | **Domain:** Orchestration

## T-064 -- GAP-4: DGM formal proof-of-utility sandbox for self-rewrites  (WS-GUARD | P3 | L)
**Goal:** E-24 Autonomy guardrails -- a self-rewrite is admitted only against a machine-checked non-regression theorem, so the agent plane cannot degrade itself or starve the host.
**What+How:** Build `usr/libexec/mios/mios-dgm-sandbox`: fork an isolated `mios-agent-pipe` instance (rootless Podman, network off, read-only mounts) and replay n=20 canonical trajectories drawn from the pgvector `tool_call` history. Admit the rewrite if and only if all three hold -- `pass^k_new >= pass^k_current` (the T-049 metric), `mean_latency_new <= mean_latency_current * 1.05`, and `peak_vram_new <= peak_vram_current * 1.10`. Any failure logs `event(kind="dgm_veto", reason=...)` to the T-034 Merkle chain and discards. Every threshold lives in the `[self_improve]` SSOT block (`sandbox_image`, `replay_corpus_size`, `latency_tolerance`, `vram_tolerance`, `pass_and_k_required`).
**Where:** `usr/libexec/mios/mios-dgm-sandbox` (new) | `usr/share/mios/mios.toml`
**Done When:** A rewrite that regresses pass^k by a single failed run is rejected with a chained veto record, a neutral-or-improving rewrite is admitted, and `enable=false` disables the ACT half entirely.
**Why:** Without the utility gate, T-062's ACT half is an unbounded regression risk -- a rewrite could halve reliability or double VRAM and still be committed.
**Dep:** T-049 (GAP-3 pass^k), T-034 (SEC-03 Merkle chain).
**Status:** done-by-code | **Domain:** Self-Improvement/Security

## T-065 -- GAP-6: smart_resize -- three-constraint spatial normalization for VLM grounding [VM]  (WS-GUARD | P3 | M)
**Goal:** E-24 Autonomy guardrails -- an agent driving the desktop clicks where it intends to, because coordinate space is formally normalized instead of assumed.
**What+How:** Build `usr/libexec/mios/mios-smart-resize` (stdlib Python, no new deps) taking `--width --height --image-factor --min-pixels --max-pixels` plus a PNG on stdin and emitting a resized PNG plus JSON metadata (`W_tensor`, `H_tensor`). Enforce three hard constraints before any image reaches the VLM: `H mod IMAGE_FACTOR == 0` and `W mod IMAGE_FACTOR == 0` (default 28, ViT patch-grid alignment), `MIN_PIXELS <= H*W <= MAX_PIXELS` (OOM guard), and `max(H/W, W/H) <= MAX_RATIO` (default 200, distortion guard). After inference apply the inverse projection `X_abs = round((X_raw/W_tensor)*W_orig)` (same for Y), scaling by `[computer_use].hidpi_scale_factor`. Call it from `mios-pc-control` before every grounding request and un-project the returned (x,y) before dispatching `pc_click`.
**Where:** `usr/libexec/mios/mios-smart-resize` (new) | `usr/libexec/mios/mios-pc-control` | `usr/share/mios/mios.toml`
**Done When:** A 3840x2160 HiDPI screenshot resizes to a patch-aligned tensor, raw VLM coord (512,384) maps to physical pixel (1536,1152), `pc_click` lands within 2px of the target element, and a constraint violation raises a logged error instead of silently shipping a corrupt tensor.
**Why:** VLMs return coordinates in their own resized tensor space; unprojected, every click on a HiDPI display misses its target, which makes the whole vision grounding path unusable.
**Dep:** T-038 (CU-01 action hierarchy). Operator VM [VM].
**Status:** partial | **Domain:** Computer Use

## T-066 -- B5: A2A federation loopback round-trip smoke test  (WS-B5 | P3 | S)
**Goal:** E-06 Test and documentation harness -- the federation path has an executable proof it works, so a regression fails a test rather than a demo.
**What+How:** Add `usr/share/mios/tests/test-a2a-loopback.sh` registering MiOS as its own A2A peer and driving one full `Message -> Task -> Artifact` round trip, asserting the artifact returns intact and that the `event` table records the complete delegation chain.
**Where:** `usr/share/mios/tests/test-a2a-loopback.sh`
**Done When:** `mios-a2a-test --loopback` exits 0 printing "Task completed, Artifact received".
**Why:** Federation is only ever exercised by hand today, so a broken hop is found by an operator mid-task instead of by CI.
**Dep:** T-022 (FED-CONSUME).
**Status:** done-by-code | **Domain:** Federation/Testing

## T-067 -- B6: `expandvars` across every `*_endpoint` field  (WS-B6 | P3 | S)
**Goal:** E-13 Ports are allocated from SSOT -- an endpoint declared with a `${MIOS_PORT_*}` reference resolves to the derived port at load time instead of being dialled as a literal.
**What+How:** Apply `os.path.expandvars()` to `cpu_endpoint` and every other `*_endpoint` field read by `_load_agent_registry` and `_load_node_pool` in `server.py`, so SSOT-derived port variables expand once at registry load.
**Where:** `usr/lib/mios/agent-pipe/server.py`
**Done When:** An endpoint configured as `http://host:${MIOS_PORT_AGENT_PIPE}/v1` shows the numeric port in the loaded registry and dials successfully.
**Why:** An unexpanded `${MIOS_PORT_*}` becomes a connection attempt to a nonsense host:port, which surfaces as an opaque dial failure rather than a config error -- and it punishes exactly the operators who followed the no-hardcode rule.
**Dep:** T-006 (A1).
**Status:** done-by-code | **Domain:** Ops/Config

## T-068 -- B7: Multi-tenant row-level security via `SET LOCAL mios.owner_user`  (WS-B7 | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the shared datastore enforces per-owner isolation in the database, not in application if-statements.
**What+How:** Issue a param-bound `SET LOCAL mios.owner_user='<user_id>'` at the start of each DB transaction through `mios_pg._owner_scope`, with matching RLS policies in `schema-init.sql`. Note the implementation gate is `[pgvector].rls_enable` (NOT the spec's `[database].rls_enable`) and it REQUIRES `[security].principal_bind_mode=enforce`; re-ranked P1 in sequence behind V1/V2.
**Where:** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/postgres/schema-init.sql`
**Done When:** With RLS enabled, a query run as Agent A returns zero of Agent B's `agent_memory` rows even on a `SELECT *` with no owner predicate.
**Why:** Without database-enforced scoping, any missed WHERE clause in a ~9k-line server module leaks one user's memory into another's context -- and multi-user deployment cannot be offered at all.
**Dep:** None.
**Status:** done-by-code | **Domain:** Data/Security

## T-069 -- C5: Bake pod Quadlet generation into the build render step  (WS-C5 | P3 | S)
**Goal:** E-18 Generate the 168 systemd units from SSOT -- generated units are a build output present in the image, never a hand-maintained file committed by an operator.
**What+How:** Call `tools/generate-pod-quadlets.py` from the `Containerfile` render step so every `.pod` and `.container` unit is rendered during the bake and shipped inside the image, rather than generated post-boot or committed by hand.
**Where:** `Containerfile` | `tools/generate-pod-quadlets.py`
**Done When:** A freshly booted image has all pod units already present and active with no first-boot generation step, and the pod-quadlets drift-check is green on a clean checkout.
**Why:** Hand-committed Quadlets are exactly the surface that keeps losing its build-resolved digests and turning the pod-quadlets gate red; generating at bake removes the class.
**Dep:** T-017 (C2), T-005 (BOOT-04).
**Status:** done-by-code | **Domain:** Ops/Build

## T-070 -- D2: Pi/edge node join guide  (WS-D2 | P3 | S)
**Goal:** E-06 Test and documentation harness -- an arriving operator or agent can join an edge node cold, from the doc set alone.
**What+How:** Write `usr/share/doc/mios/guides/edge-node-join.md` documenting the one-port (`:8640`) outbound-dial join flow for Pi and edge nodes, the TOML overlay pattern used to configure a joining node, and the optional federated pgvector path via `[pgvector].listen_loopback=false` (off by default, with its exposure caveat stated).
**Where:** `usr/share/doc/mios/guides/edge-node-join.md` (new)
**Done When:** A Pi node joins the council following only the guide -- no source reading, no undocumented flag.
**Why:** Undocumented, the join flow lives in one person's head and every new node costs a source-reading session.
**Dep:** T-043 (D1).
**Status:** done | **Domain:** Documentation/Federation

## T-071 -- E2/E3: OWUI surface corrections -- location string and stale agent card  (WS-E2/E3 | P3 | S)
**Goal:** E-06 Test and documentation harness -- shipped descriptive surfaces stay truthful after a migration, so what the UI states matches what the system does.
**What+How:** Two independent fixes. E2: strip the trailing `(lat, long)` suffix from the location string built in `_client_env` before it is handed to the model. E3: rewrite the `agent.json` description that still advertises the "legacy-datastore-state chain" from before the pgvector migration.
**Where:** `usr/lib/mios/agent-pipe/server.py` (`_client_env`) | `usr/share/mios/ai/v1/agent.json`
**Done When:** OWUI shows city and timezone with no coordinates, and `agent.json`'s description names pgvector with no reference to the legacy datastore.
**Why:** Raw coordinates leak precise location into every model turn, and a stale card teaches every reader (human and agent) an architecture that no longer exists.
**Dep:** None.
**Status:** done | **Domain:** UX

## T-072 -- F3: Per-session code-mode broker on `/run/coderun.sock`  (WS-F3 | P3 | M)
**Goal:** E-24 Autonomy guardrails -- concurrent code execution is isolated per session, so one agent's sandbox cannot observe or corrupt another's.
**What+How:** Build the host-side broker `usr/libexec/mios/mios-coderun-broker` listening on `/run/coderun.sock`: each session is handed its own socket bound to its own `mios-coderun-sandbox` container instance, and both socket and container are torn down on disconnect so nothing survives the session.
**Where:** `usr/libexec/mios/mios-coderun-broker` (new)
**Done When:** Two concurrent code-execution sessions run in separate containers and neither can read the other's output or leftover files, with both containers gone after disconnect.
**Why:** A single shared sandbox lets one session's untrusted generated code read another session's data, and leaked containers accumulate on the host.
**Dep:** T-045 (F2 coderun-sandbox).
**Status:** done | **Domain:** Sandboxing

## T-073 -- F4: build-driver fallback, `move_window` actuator, `es.exe` refresh  (WS-F4 | P3 | S)
**Goal:** E-01 Compiled native tier -- the libexec tool fleet and build driver behave correctly and float their inputs, ahead of being ported to compiled binaries.
**What+How:** Three independent items. (1) `mios-build`: add a `curl` fallback path when the primary build trigger is unavailable, so a build can still be kicked off. (2) `mios-pc-control`: implement `move_window` as a named-region actuator, e.g. `move_window {window:"Notepad", region:"left-half"}`. (3) `Containerfile`: bring the baked `es.exe` (Everything Search) up to the current release rather than the pinned older one.
**Where:** `usr/libexec/mios/mios-build` | `usr/libexec/mios/mios-pc-control` | `Containerfile`
**Done When:** Each of the three works end-to-end on its own -- a build triggers with the primary path down, `move_window` snaps a named window to a named region, and the image ships the current `es.exe`.
**Why:** A single-path build trigger blocks every build when it is down, `move_window` without named regions forces the agent to compute pixel geometry it cannot see, and a stale `es.exe` is a hand-pinned input contradicting float-latest.
**Dep:** None.
**Status:** done-by-code | **Domain:** Ops/Computer Use

## T-074 -- FED-G10/G11: cardless `/v1/models` join + a `/v1/agents` peer directory  (WS-FED | P3 | M)
**Goal:** E-11 Unified config surface: one door at :8640/ -- NS-2's rule that every agent, lane and federated peer is an interchangeable OpenAI endpoint reachable through the single `/v1/*` front door.
**What+How:** In `agent-pipe/server.py` add a cardless join path: probe a candidate endpoint's `GET /v1/models`, infer its capabilities from the returned model ids (no AgentCard required), and register it as a council peer -- so Claude, Gemini and raw vLLM endpoints join on the OpenAI surface alone. Then add a `GET /v1/agents` registry handler that returns the discoverable directory of every registered agent endpoint with its card (or the inferred capability summary) and a cardless flag.
**Where:** `usr/lib/mios/agent-pipe/server.py`
**Done When:** a raw vLLM endpoint that serves no AgentCard joins the council purely off the `/v1/models` probe, and `curl -s localhost:8640/v1/agents` lists it alongside the carded peers.
**Why:** without it only AgentCard-speaking peers can federate -- every plain OpenAI endpoint must be hand-wired -- and there is no queryable answer to "who is in this council right now".
**Dep:** T-013 (FED-G5), T-059 (DATA-01).
**Status:** done | **Domain:** Federation

## T-075 -- H6: LAKE federated query over pgvector shards via the Spice.ai Rust engine  (WS-H6 | P3 | XL)
**Goal:** E-23 DB-driven configuration and vector recall -- NS-2's pgvector-backed memory answering across shards fast enough to sit in an agent turn.
**What+How:** Integrate the Learning-assisted Accelerated Kernel (LAKE) built on the Spice.ai open-source Rust engine as a federated query/routing layer over the inference queues and the pgvector shards, so a single recall query fans out across shards and dynamically routes rather than executing sequentially. Explicitly long-horizon: do not start before T-048 (GAP-2) and T-050 (GAP-5) are live, since both define the routing surface LAKE would sit on.
**Where:** TBD -- a new Spice.ai integration layer; no file paths chosen in the source entry.
**Done When:** a federated query spanning 2 pgvector shards returns in under 200 ms, and the LAKE scheduler measures greater than 2x throughput against the same workload run sequentially.
**Why:** cross-shard recall today is sequential, so memory lookup latency grows linearly with shard count and caps how much history an agent turn can afford to consult.
**Dep:** T-048 (GAP-2), T-050 (GAP-5).
**Status:** open | **Domain:** Scheduling/Data

## T-078 -- GWY-03: build the `mios-gateway-agent` FastAPI service that replaces `hermes-agent`  (WS-GWY | P3 | L)
**Goal:** E-24 Autonomy guardrails / the sovereign agent plane -- NS-2's MiOS-native, auditable tool-loop service behind the one OpenAI `/v1` contract, with no vendor config file in the loop.
**What+How:** Create the `usr/lib/mios/gateway-agent/` Python package with its own venv (mirroring the Hermes pattern) holding smolagents, httpx, fastapi, uvicorn and mcp -- all Apache-2.0/MIT. Implement `POST /v1/chat/completions`: parse the OpenAI `messages` + `tools` body, construct `smolagents.ToolCallingAgent(model=OpenAIServerModel(...), tools=mios_tool_registry)` whose `OpenAIServerModel` base URL is `MIOS_AI_ENDPOINT` (Law 5, never a cloud host), run the loop and either stream SSE or return the full response. Add `GET /v1/models` sourced from `[ai].available_models`, plus `GET /health` and `GET /v1/cluster/health` JSON stubs. Persist per-`session_id` message lists in a new pgvector `gateway_sessions` JSONB table, and add the `[gateway]` block (`model`, `max_tokens`, `context_length`, `port`, `enable = false`) so phase 2 stays off until T-079..T-082 land.
**Where:** `usr/lib/mios/gateway-agent/__init__.py`, `usr/lib/mios/gateway-agent/server.py`, `usr/lib/mios/gateway-agent/session.py`, `usr/lib/systemd/system/mios-gateway-agent.service`, `usr/share/mios/mios.toml`, `usr/share/mios/postgres/schema-init.sql`
**Done When:** `uvicorn mios.gateway_agent.server:app --port 8642` starts clean in its venv; `curl -s localhost:8642/health` returns `{"status":"ok"}`; `/v1/models` returns the mios.toml model list; a `POST /v1/chat/completions` returns a valid OpenAI-shaped response; and no cloud endpoint appears in the logs.
**Why:** the tool loop is otherwise owned by upstream Hermes on port :8642 with its own `config.yaml` -- an unauditable, non-SSOT dependency sitting on the OS's primary AI contract.
**Dep:** T-076 (GWY-01 Letta infra live), T-028 (B1 pgvector schema).
**Status:** done-by-code | **Domain:** Gateway/Orchestration

## T-079 -- GWY-04: wire smolagents `ToolCallingAgent` as the gateway's tool-loop engine  (WS-GWY | P3 | M)
**Goal:** E-24 Autonomy guardrails / the sovereign agent plane -- NS-2's local tool loop bounded by an explicit step cap and switchable back to pass-through.
**What+How:** Implement `MiOSToolRegistry` in `gateway-agent/tool_registry.py`: on startup pull tool schemas from `mios-mcp-server` (via T-080) and the skill catalog (via T-081) and build `smolagents.Tool` subclasses whose `forward(**kwargs)` dispatches over the MCP stdio client and returns the result string. Wire `ToolCallingAgent(model=..., tools=registry.tools, max_steps=[gateway].max_steps)` into the `/v1/chat/completions` handler from T-078, keeping OpenAI-format `tool_calls` / `role:tool` entries in the session message list so runs replay and OTel-trace correctly. On exceeding `max_steps`, return `finish_reason="length"` with the last partial assistant message instead of raising. Gate the whole engine behind `[gateway].tool_loop_engine`, with `"native"` selecting a raw pass-through.
**Where:** `usr/lib/mios/gateway-agent/tool_registry.py`, `usr/lib/mios/gateway-agent/server.py`, `usr/share/mios/mios.toml` (`[gateway].max_steps`, `[gateway].tool_loop_engine`)
**Done When:** a multi-turn conversation invoking `mios_verb.list_services` completes correctly, the `tool_calls` show up in the pgvector session history, the `max_steps` cap returns `finish_reason="length"` without crashing, and setting `tool_loop_engine = "native"` bypasses smolagents entirely.
**Why:** without the loop engine the new gateway is an empty shell -- it can proxy completions but cannot execute a single MiOS verb, so Hermes cannot be retired.
**Dep:** T-078 (GWY-03 FastAPI service), T-080 (GWY-05 MCP client).
**Status:** done-by-code | **Domain:** Gateway/Orchestration

## T-080 -- GWY-05: MCP stdio client from the gateway to `mios-mcp-server`  (WS-GWY | P3 | S)
**Goal:** E-24 Autonomy guardrails / the sovereign agent plane -- NS-2's MCP tool surface reaching the new gateway over the same transport Hermes used, with no capability lost in the swap.
**What+How:** Add the MIT-licensed `mcp` SDK to the gateway venv and implement `MiOSMCPClient` on `mcp.StdioServerParameters(command="/usr/libexec/mios/mios-mcp-server")` -- byte-identical transport to the existing Hermes `mcp_servers.mios` config, giving the gateway all 82 verbs plus 18 recipes. On startup call `tools/list` to build the schema cache and re-fetch it every `[gateway].mcp_refresh_seconds` (default 300). Pass `MIOS_AGENT_PIPE_URL=http://localhost:8640` into the MCP subprocess env, and declare `supports_parallel_tool_calls = true` in the registry to match Hermes behaviour.
**Where:** `usr/lib/mios/gateway-agent/mcp_client.py`, `usr/share/mios/mios.toml` (`[gateway].mcp_refresh_seconds`)
**Done When:** the startup `tools/list` returns at least 82 tool definitions, `mios_verb.list_services` executes through MCP and returns the service list, the catalog refreshes on the 300 s cycle with no restart, and no orphaned `mios-mcp-server` processes remain after a gateway restart.
**Why:** the gateway would otherwise have zero tools, and a leaked stdio child per restart accumulates orphan `mios-mcp-server` processes on the host.
**Dep:** T-078 (GWY-03), T-024 (MCP-01 server live).
**Status:** done-by-code | **Domain:** Gateway/MCP

## T-081 -- GWY-06: skill catalog, SearXNG web search and browser-verb pass-through in the tool registry  (WS-GWY | P3 | S)
**Goal:** E-24 Autonomy guardrails / the sovereign agent plane -- NS-2's fully local tool surface, including search, with a static fallback so the plane degrades open.
**What+How:** Extend `MiOSToolRegistry` with the three Hermes surface extensions still missing. Skill catalog: at startup and every `[gateway].skill_refresh_seconds` (default 300) `GET http://localhost:8640/skills/openai-tools` and inject the returned schemas, falling back to `[gateway].skill_catalog_static_path` (`/var/lib/mios/skills/catalog.json`) when the HTTP call fails. Web search: register a `web_search` tool (smolagents built-in or a thin wrapper) pointed at `[gateway].searxng_url` (`http://mios-searxng:8080`). Browser/CDP actions need no new integration -- `mios-pc-control` already exposes them as MCP verbs that T-080's `tools/list` pulls in automatically.
**Where:** `usr/lib/mios/gateway-agent/tool_registry.py`, `usr/share/mios/mios.toml` (`[gateway].searxng_url`, `[gateway].skill_refresh_seconds`, `[gateway].skill_catalog_static_path`)
**Done When:** `web_search {"query":"bootc docs"}` returns SearXNG results, a newly promoted skill appears in the `/v1/chat/completions` tool list within 300 s, `mios_verb.open_url` is callable through the gateway loop, and the static catalog fallback engages when agent-pipe is down.
**Why:** without these the gateway loses search and dynamic skills relative to Hermes, so the cutover would be a functional regression rather than a swap.
**Dep:** T-079 (GWY-04 tool loop), T-080 (GWY-05 MCP client).
**Status:** done-by-code | **Domain:** Gateway/Tools

## T-082 -- GWY-07: collapse the Hermes YAML config pair into the `mios.toml [gateway]` SSOT  (WS-GWY | P3 | S)
**Goal:** E-11 Unified config surface: one door at :8640/ -- NS-3's rule that a value which could live in mios.toml but doesn't is a bug, and no config path may bypass the SSOT.
**What+How:** Replace the `usr/share/mios/hermes/config.yaml` vendor-default plus `/etc/mios/hermes/config.local.yaml` override dance with one `[gateway]` section in `usr/share/mios/mios.toml` carrying `model`, `max_tokens`, `context_length`, `port = 8642`, `max_steps = 30`, `tool_loop_engine = "smolagents"`, `mcp_refresh_seconds = 300`, `skill_refresh_seconds = 300`, `skill_catalog_static_path`, `searxng_url` and `enable = false`. Mark both `hermes/config.yaml` and `hermes/config-worker.yaml` deprecated with a header comment pointing at `[gateway]`; teach `usr/lib/tmpfiles.d/mios-hermes.conf` to also seed `/etc/mios/gateway/` when `mios-gateway-agent.service` is enabled; update the `etc/mios/kb.conf.toml` comment to record `base_url = "http://localhost:8642/v1"`; and add the `mios-gateway-agent` row to the `AGENTS.md` service table.
**Where:** `usr/share/mios/mios.toml`, `usr/share/mios/hermes/config.yaml`, `usr/share/mios/hermes/config-worker.yaml`, `usr/lib/tmpfiles.d/mios-hermes.conf`, `etc/mios/kb.conf.toml`, `AGENTS.md`
**Done When:** `mios-gateway-agent` reads every setting from `mios.toml [gateway]` with zero reads of `hermes/config.yaml`, both YAML files carry the deprecation header, `kb.conf.toml` reflects both endpoint options, and the `AGENTS.md` service table lists the new service.
**Why:** two live config surfaces for one service means the configurator/Portal cannot show or change the gateway's real settings, and every value in the YAML pair is a second definition of a fact that belongs in SSOT.
**Dep:** T-078 (GWY-03 service built).
**Status:** done-by-code | **Domain:** Gateway/Config

## T-083 -- GWY-08: cut over from `hermes-agent` to `mios-gateway-agent` and archive the Hermes units  (WS-GWY | P3 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- the rule that a capability is either SSOT-wired and gated or explicitly removed with a recorded decision; here Hermes is removed on the record.
**What+How:** Smoke-test first: run the new service on shadow port `:8643` and send 10 canonical `mios_verb` tool calls, requiring 200 + correct output on all 10. Then flip `[gateway].enable = true`, `systemctl --user disable --now hermes-agent.service && systemctl --user mask hermes-agent.service`, enable and start `mios-gateway-agent.service`, and bring up the worker equivalent `mios-gateway-worker.service` (same smolagents engine, `[gateway.worker]` block, `:8643`). Repoint `mios-agent-pipe.service` from `Environment=HERMES_ENDPOINT=` to `GATEWAY_ENDPOINT=http://localhost:8642` (or alias both), swap the `Containerfile` build test from the `hermes-agent` venv check to the gateway venv check, and `git mv` `hermes-agent.service` / `config.yaml` / `config-worker.yaml` into `archive/hermes/`.
**Where:** `usr/lib/systemd/system/mios-gateway-agent.service`, `usr/lib/systemd/system/mios-gateway-worker.service`, `usr/lib/systemd/system/hermes-agent.service`, `usr/lib/systemd/system/hermes-worker.service`, `usr/lib/systemd/system/mios-agent-pipe.service`, `Containerfile`, `archive/hermes/`
**Done When:** `hermes-agent.service` is masked and does not start at boot, `curl localhost:8642/health` returns ok from the new unit, all 10 smoke-test tool calls pass, agent-pipe dispatches reach `:8642` and get valid completions, OWUI chat works end to end, and `[gateway].enable = false` still leaves Hermes running on unupgraded installs.
**Why:** until the cutover happens, all of T-078..T-082 is dead code and the image still ships two competing services claiming port :8642.
**Dep:** T-078 (GWY-03), T-079 (GWY-04), T-080 (GWY-05), T-081 (GWY-06), T-082 (GWY-07). All smoke tests green.
**Status:** partial | **Domain:** Gateway/Ops

## T-084 -- STRG-01: `[storage.cephfs]` SSOT block, userenv exports and drift-check stub  (WS-STRG | P2 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- Ceph already ships in the image (`automation/13-ceph-k3s.sh`, `mios-ceph.container`) but has no SSOT face; this gives it one.
**What+How:** Add a `[storage.cephfs]` block to `usr/share/mios/mios.toml` with every field defaulted to a safe no-op (`enable = false`, `monitors = ["127.0.0.1:6789"]` placeholder, pools, tenant id, cache override), per the ROADMAP 9.5 schema. Export the derived keys from `usr/share/mios/mios-configurator/userenv.sh`: `MIOS_CEPHFS_ENABLE`, `MIOS_CEPHFS_MONITORS`, `MIOS_CEPHFS_FS_NAME`, `MIOS_CEPHFS_TENANT_ID`, `MIOS_CEPHFS_DATA_POOL_HOT`, `MIOS_CEPHFS_DATA_POOL_BULK`, `MIOS_XDG_CACHE_LOCAL_PATH`. Register a `check_cephfs_ssot` stub in `automation/98-drift-checks.sh` that fails when `enable=true` while `monitors` is still the `127.0.0.1` placeholder (T-093 fills in the rest), and add a static `[storage.cephfs]` form to the configurator's Storage tab.
**Where:** `usr/share/mios/mios.toml`, `usr/share/mios/mios-configurator/userenv.sh`, `automation/98-drift-checks.sh`
**Done When:** `python3 -c "import tomllib; d=tomllib.load(open('usr/share/mios/mios.toml','rb')); assert 'cephfs' in d.get('storage',{})"` exits 0, `userenv.sh` exports `MIOS_CEPHFS_ENABLE=false`, `just drift-gate` passes clean, and the same gate FAILS when `enable=true` with the placeholder monitor.
**Why:** every downstream STRG task needs a key to read; without the block each would hardcode monitors, pools and paths, which is exactly the Law 7 class the tree is trying to eliminate.
**Dep:** none
**Status:** done | **Domain:** Storage/Config

## T-085 -- STRG-02: `mios-cephfs-provision` subvolume lifecycle + degrade-open PAM hook  (WS-STRG | P2 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- per-user network home provisioning that never blocks a login when the fabric is down.
**What+How:** Build `/usr/libexec/mios/mios-cephfs-provision` with three subcommands. `validate <uid>`: check whether `cephfs:/tenants/<tenant_id>/users/<uid>` exists, call `create` if absent, verify the CephX keyring is present, and exit 0 both on success and when Ceph is unreachable (degrade-open). `create <uid> <gid>`: idempotently `ceph fs subvolumegroup create cephfs mios-users`, then `ceph fs subvolume create cephfs <uid>-home --group_name mios-users --uid --gid --mode 0700`, then invoke T-089's keyring creation. `delete <uid>`: `ceph auth del client.<uid>`, unmount `/home/<username>` if mounted, `ceph fs subvolume rm`. Install the PAM hook `session optional pam_exec.so /usr/libexec/mios/mios-cephfs-provision validate %u %g` into `/etc/pam.d/system-auth` via a tmpfiles.d fragment or firstboot, so provisioning runs before the home directory is touched. Read the SSOT gate through `mios-userenv` and log each provisioning to pgvector as `event(kind="storage_provision", source="cephfs", uid=<uid>)`.
**Where:** `usr/libexec/mios/mios-cephfs-provision`, `usr/lib/tmpfiles.d/mios-cephfs.conf`
**Done When:** `mios-cephfs-provision validate 1000` creates the subvolume and keyring when absent and exits 0; the same call still exits 0 with the `ceph` binary unavailable; `delete 1000` removes both keyring and subvolume; a `storage_provision` row lands in the pgvector `event` table; and the script is a strict no-op with `MIOS_CEPHFS_ENABLE=false`.
**Why:** without this, CephFS homes must be provisioned by hand per user, and a naive PAM hook that fails closed would lock every operator out of the machine the moment the cluster degrades.
**Dep:** T-084 (STRG-01 SSOT).
**Status:** done | **Domain:** Storage/Auth

## T-086 -- STRG-03: per-dispatch `XDG_RUNTIME_DIR` isolation for concurrent tool contexts  (WS-STRG | P2 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- concurrent agent dispatch that stays correct on a network-backed `$HOME`.
**What+How:** In `mios-session-init` (or `mios-agent-pipe.service` `ExecStartPost`) mint `MIOS_SESSION_ID=$(uuidgen --random | cut -c1-8)` per dispatch context, and set `XDG_RUNTIME_DIR=/run/user/<uid>/session-${MIOS_SESSION_ID}` in the dispatch environment (`os.environ` in `server.py` before tool contexts fork). Create the directory with `systemd-run --user --scope -p RuntimeDirectory=session-${MIOS_SESSION_ID}` or a tmpfiles.d `d` line. Render `XDG_CACHE_HOME` from `[storage.cephfs].xdg_cache_home_override` (default `/run/user/{uid}/.cache`) into `/etc/profile.d/mios-xdg-cephfs.sh` at firstboot. Gate the whole injection on `[storage.cephfs].enable = true` so local-home installs see no behaviour change.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/profile.d/mios-xdg-cephfs.sh`, `usr/share/mios/mios.toml` (`[storage.cephfs].xdg_cache_home_override`)
**Done When:** two concurrent dispatch contexts report different `XDG_RUNTIME_DIR` values, `XDG_CACHE_HOME` always resolves under `/run/user/<uid>/.cache` and never to a CephFS path, and with `enable = false` the existing `XDG_RUNTIME_DIR` behaviour is byte-identical.
**Why:** today parallel tool calls under one UID share a runtime dir, so SQLite lock files and POSIX advisory locks collide on CephFS-backed `$HOME/.config` -- a corruption and hang class, not just a slowdown.
**Dep:** T-084 (STRG-01), T-085 (STRG-02).
**Status:** done | **Domain:** Storage/Orchestration

## T-087 -- STRG-04: SSOT-rendered `home-@.mount` / `home-@.automount` template pair  (WS-STRG | P2 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- on-demand network homes with no hand-maintained `/etc/fstab` entry anywhere in the image.
**What+How:** Add two unit templates under `usr/share/mios/systemd/`: `home-@.mount` with `What=${MIOS_CEPHFS_MONITORS}:${MIOS_CEPHFS_FS_PATH}`, `Where=/home/%i`, `Type=ceph` and `Options=name=client.%i,secretfile=${MIOS_CEPHFS_KEYRING_DIR}/client.%i,${MIOS_CEPHFS_MOUNT_OPTIONS}`; and `home-@.automount` with `Where=/home/%i` and `TimeoutIdleSec=${MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S}`. A new firstboot script substitutes those SSOT vars into `/etc/systemd/system/home-@.{mount,automount}`, runs `systemctl daemon-reload`, and enables `home-<username>.automount` for the operator user. Add `ConditionPathExists=/etc/ceph/keyring.d/client.%i` to the mount unit so a missing keyring skips the mount instead of failing the boot, and gate the entire firstboot step on `MIOS_CEPHFS_ENABLE=true`.
**Where:** `usr/share/mios/systemd/home-@.mount.tmpl`, `usr/share/mios/systemd/home-@.automount.tmpl`, `automation/firstboot/mios-cephfs-mount-setup.sh`
**Done When:** `systemctl start home-<username>.automount` succeeds, first access to `/home/<username>` triggers the mount and `findmnt /home/<username>` reports type `ceph`, the unit auto-unmounts after `TimeoutIdleSec`, and a missing keyring leaves login working on the local `$HOME`.
**Why:** persistent fstab mounts hold MDS capabilities forever and turn one unreachable monitor into a failed boot; without the templates there is no idle-unmount path at all.
**Dep:** T-085 (STRG-02), T-086 (STRG-03).
**Status:** done | **Domain:** Storage/Systemd

## T-088 -- STRG-05: CephFS client cache/readahead/fscache tuning rendered from SSOT  (WS-STRG | P2 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a network-backed home that is usable at interactive desktop speed, not just technically mounted.
**What+How:** Add a `mios-ceph-configure` helper that renders the `[client]` block of `/etc/ceph/ceph.conf` from SSOT values: `client_cache_size = 16384`, `client_cache_after_readdir = true`, `client_readahead_max_bytes = 33554432`, `client_reconnect_stale_interval = 30`, `fuse_disable_pagecache = false`. Call it from the CephFS firstboot init after T-087's automount setup. Ensure `fsc` is present in the mount options T-087 renders, and install/enable `cachefilesd`. Add `mds_cache_memory_limit = 4294967296` (4 GiB) to the cephadm bootstrap config. Measure with `ceph tell mds.<name> perf dump` before and after a GNOME login.
**Where:** `usr/libexec/mios/mios-ceph-configure`, `etc/ceph/ceph.conf` (operator overlay, rendered), `usr/share/mios/mios.toml`, `usr/lib/systemd/system/cachefilesd.service`
**Done When:** `/etc/ceph/ceph.conf` shows the rendered `[client]` block after firstboot, steady-state GNOME login measures under 500 MDS ops/s, `cachefilesd.service` is active with `fsc` visible in `findmnt` output, and `ceph config get client client_reconnect_stale_interval` returns 30.
**Why:** stock client settings drive 2,000-8,000 MDS ops/s on first GNOME login as Tracker, GVfs and Flatpak walk `$XDG_DATA_HOME` at once -- cap-recall storms that make the desktop feel broken.
**Dep:** T-087 (STRG-04 automount).
**Status:** partial | **Domain:** Storage/Performance

## T-089 -- STRG-06: per-user CephX capability scoping + storage status endpoints  (WS-STRG | P2 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- storage isolation enforced at the RADOS layer, and its state visible through the `/v1` front door.
**What+How:** Extend `mios-cephfs-provision create <uid>` to mint a path-scoped key: `ceph auth get-or-create client.<uid>` with `mds "allow r, allow rw path=/tenants/${MIOS_CEPHFS_TENANT_ID}/users/${uid}"`, `osd "allow rw pool=${MIOS_CEPHFS_DATA_POOL_HOT} tag cephfs data=cephfs, allow rw pool=${MIOS_CEPHFS_DATA_POOL_BULK} tag cephfs data=cephfs"` and `mon "allow r"`, written to `/etc/ceph/keyring.d/client.<uid>` at mode 0400 owned by that uid/gid; and extend `delete <uid>` to `ceph auth del` plus remove the keyring file. In `agent-pipe/server.py` add `GET /v1/storage/cephfs/users` (JSON list of `uid`, `keyring_present`, `subvolume_exists`, `subvolume_path`) and `GET /v1/storage/cephfs/health` (structured `ceph health` plus `ceph df` pool utilisation), both returning `{"enabled": false}` when `MIOS_CEPHFS_ENABLE=false`.
**Where:** `usr/libexec/mios/mios-cephfs-provision`, `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml`
**Done When:** `ceph auth get client.1000` shows path-scoped caps rather than `allow *`, `curl localhost:8640/v1/storage/cephfs/users` returns the provisioned list, `/v1/storage/cephfs/health` returns `{"status":"HEALTH_OK",...}` on a healthy cluster, and mounting another user's subvolume with user A's keyring is refused with `EACCES`.
**Why:** with a shared or wildcard CephX key, one misconfigured POSIX ACL or one privileged agent reads every other user's home -- POSIX permissions are the only barrier and they are the wrong layer.
**Dep:** T-085 (STRG-02 provision), T-084 (STRG-01 SSOT).
**Status:** done | **Domain:** Storage/Security

## T-090 -- STRG-07: bake the `mios-xdg-cephfs.sh` profile script that keeps cache off the network  (WS-STRG | P3 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- the immutable image itself guarantees the cache/home split rather than relying on operator shell config.
**What+How:** Create `usr/share/mios/profile.d/mios-xdg-cephfs.sh`, baked immutable into the bootc image, exporting `XDG_CONFIG_HOME="${HOME}/.config"`, `XDG_DATA_HOME="${HOME}/.local/share"`, `XDG_STATE_HOME="${HOME}/.local/state"` (all CephFS-hot via `$HOME`), `XDG_RUNTIME_DIR="/run/user/$(id -u)"` and `XDG_CACHE_HOME="${MIOS_XDG_CACHE_LOCAL_PATH:-/run/user/$(id -u)/.cache}"` -- cache NEVER on CephFS. Firstboot symlinks `/etc/profile.d/mios-xdg-cephfs.sh` at the baked file; `MIOS_XDG_CACHE_LOCAL_PATH` comes from `[storage.cephfs].xdg_cache_home_override` already exported by T-084.
**Where:** `usr/share/mios/profile.d/mios-xdg-cephfs.sh`, `automation/firstboot/mios-xdg-setup.sh`
**Done When:** the script is present in the image at the baked path; after sourcing it `$XDG_CONFIG_HOME` equals `$HOME/.config` and `$XDG_CACHE_HOME` starts with `/run/user/`; and T-093's drift-check confirms `xdg_cache_home_override` holds no CephFS path.
**Why:** if the cache lands on CephFS, every browser and toolchain write becomes MDS traffic -- the exact load pattern T-088 exists to suppress, reintroduced through the back door.
**Dep:** T-086 (STRG-03 cache override SSOT wiring).
**Status:** done | **Domain:** Storage/UX

## T-091 -- STRG-08: `xdg-user-dirs` defaults + `mios-xdg-userdir-init.service` mount-conditional unit  (WS-STRG | P3 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a CephFS-backed first login lands in a fully formed home, with the local-home path untouched.
**What+How:** Bake `usr/share/mios/xdg/user-dirs.defaults` (standard English folder names) and have firstboot copy it to `/etc/xdg/user-dirs.defaults`. Add the systemd user unit `mios-xdg-userdir-init.service` with `ConditionPathIsMountPoint=/home/%u`, `ExecStart=/usr/bin/xdg-user-dirs-update --force`, `RemainAfterExit=yes`, `WantedBy=default.target`. Firstboot installs it into the operator's `~/.config/systemd/user/`, then runs `systemctl --user daemon-reload && systemctl --user enable mios-xdg-userdir-init`. The `ConditionPathIsMountPoint` is the gate: on a local `$HOME` the unit silently skips and the normal GNOME session handles user dirs.
**Where:** `usr/share/mios/xdg/user-dirs.defaults`, `usr/share/mios/systemd/mios-xdg-userdir-init.service`, `automation/firstboot/mios-xdg-setup.sh`
**Done When:** after a first CephFS-backed login `~/Documents ~/Downloads ~/Music ~/Pictures ~/Videos ~/Desktop` all exist, `$HOME/.config/user-dirs.dirs` is populated with the right paths, and the unit provably does not run on a local (non-CephFS) `$HOME`.
**Why:** on a network home the standard folders are never created in the bulk pool, so writes land in the hot pool and desktop apps hit missing-directory errors on first launch.
**Dep:** T-087 (STRG-04 automount), T-090 (STRG-07 profile script).
**Status:** done | **Domain:** Storage/UX

## T-092 -- STRG-09: CephFS greenboot health checks in `wanted.d` (degrade, never roll back)  (WS-STRG | P3 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- greenboot health COVERAGE extended so every critical service has a check, without turning a storage warning into a bootc rollback.
**What+How:** Add `/etc/greenboot/check/wanted.d/55-mios-cephfs.sh` -- deliberately `wanted.d`, not `required.d`. It checks that `ceph health` is OK or WARN (HEALTH_ERR fails), that every configured pool in `ceph df` is under 90% capacity, that `ceph fs status` shows at least one MDS `active`, and, when `[storage.cephfs].enable = true`, that `findmnt /home/<operator_user>` shows a live CephFS mount. Any failure logs `event(kind="storage_health", source="cephfs", severity="warn", detail=<check_output>)` through `mios-pg-query` with `|| true` so a simultaneously-down Postgres cannot crash the check. The script exits 0 immediately when `MIOS_CEPHFS_ENABLE=false`.
**Where:** `/etc/greenboot/check/wanted.d/55-mios-cephfs.sh` (baked in image)
**Done When:** a HEALTH_OK cluster exits 0; a HEALTH_ERR cluster exits non-zero with the warning logged while the system still boots; a pool at 91% exits non-zero naming that pool; `MIOS_CEPHFS_ENABLE=false` exits 0 immediately; and a simulated warning leaves a `storage_health` row in the pgvector `event` table.
**Why:** storage degradation is currently invisible until a user session breaks -- and putting the check in `required.d` would be worse, rolling the whole OS back over a cluster that MiOS is designed to degrade away from.
**Dep:** T-002 (BOOT-01 greenboot), T-084 (STRG-01 SSOT), T-089 (STRG-06 health endpoint).
**Status:** done | **Domain:** Storage/Reliability

## T-093 -- STRG-10: implement `check_cephfs_ssot` in full plus the CephFS/XDG operator guide  (WS-STRG | P3 | S)
**Goal:** E-07 The drift-gate as the enforcement plane -- the CephFS SSOT stops being convention and becomes a check that fails the build.
**What+How:** Replace the T-084 stub with a real `check_cephfs_ssot` in `automation/98-drift-checks.sh`, registered in `main()` after `check_rbac_tiers`, failing on: (a) `enable=true` with `monitors` still holding the `127.0.0.1:6789` placeholder; (b) `xdg_cache_home_override` containing a CephFS path prefix (matched via `[storage.cephfs].monitors` hostnames or a `/tenants/` segment); (c) `data_pool_hot == data_pool_bulk`; (d) a `provision_script` path that does not exist in the `usr/` tree; (e) `automount_enable = true` while `home-@.mount.tmpl` is absent from `usr/share/mios/systemd/`. Then write `usr/share/doc/mios/guides/cephfs-xdg-storage.md` covering the ROADMAP 9 architecture diagram, the cache-isolation rule, the single-operator quickstart (cephadm bootstrap, `enable=true`, firstboot re-run), the multi-tenant extension path, and known caveats (systemd-homed conflicts, fscache + LUKS interaction).
**Where:** `automation/98-drift-checks.sh`, `usr/share/doc/mios/guides/cephfs-xdg-storage.md`
**Done When:** `just drift-gate` fails on the placeholder monitor, on a CephFS `xdg_cache_home_override`, and on `data_pool_hot == data_pool_bulk`; passes on a correctly configured SSOT; and the guide renders in the `mios-docs` service.
**Why:** every invariant T-084..T-092 relies on is currently enforced only by whoever remembers it -- one edit re-points the cache at CephFS or collapses the two pools and nothing complains until the desktop crawls.
**Dep:** T-084 (STRG-01), T-087 (STRG-04), T-090 (STRG-07).
**Status:** done | **Domain:** Storage/CI

## T-094 -- CONV-01: `[converge.*]` SSOT block, `MIOS_CONV_*` exports and drift-check stub  (WS-CONV | P2 | S)
**Goal:** E-11 Unified config surface: one door at :8640/ -- all four Converged-Resource phases steer from one operator-visible SSOT block instead of four scattered switches.
**What+How:** Add the full `[converge.gateway]`, `[converge.inference]`, `[converge.memory]` and `[converge.image]` sub-tables to `usr/share/mios/mios.toml` per the ROADMAP 10.5 schema, every flag defaulting to a backward-compatible no-op (`false` / `"http"` / `0` / `"dual"`). Export the derived keys from `userenv.sh`: `MIOS_CONV_GATEWAY_MODE`, `MIOS_CONV_GATEWAY_QUEUE_MAXSIZE`, `MIOS_CONV_GATEWAY_WORKER_CONCURRENCY`, `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE`, `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE`, `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE`, `MIOS_CONV_IMAGE_DISTROLESS_ENABLE`, `MIOS_CONV_IMAGE_RECHUNK_ENABLE`. Register a passing `check_converge_ssot` stub in `98-drift-checks.sh` after `check_cephfs_ssot` (real rules land in T-099/T-104/T-108), and add a collapsible `[converge]` section to `mios.html`.
**Where:** `usr/share/mios/mios.toml`, `usr/share/mios/mios-configurator/userenv.sh`, `automation/98-drift-checks.sh`, `usr/share/mios/mios-configurator/mios.html`
**Done When:** `python3 -c "import tomllib; d=tomllib.load(open('usr/share/mios/mios.toml','rb')); assert 'converge' in d"` exits 0, `userenv.sh` exports `MIOS_CONV_GATEWAY_MODE=http`, all four sub-tables are present, and `just drift-gate` passes on a clean repo.
**Why:** without the block each CONV task would invent its own enable flag, and the operator would have no single place to turn the converged path on or roll it back.
**Dep:** none
**Status:** done-by-code | **Domain:** Config/Arch

## T-095 -- CONV-02: replace the :8640 -> :8642 HTTP hop with an in-process `GatewayQueue`/`GatewayWorker`  (WS-CONV | P2 | L)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- bounded, backpressured dispatch with a hard queue cap instead of an unbounded HTTP fan-out.
**What+How:** Add `usr/lib/mios/agent-pipe/mios_gateway_queue.py` holding a `GatewayRequest` dataclass (`payload: dict`, `fut: asyncio.Future`), a `GatewayQueue` wrapping `asyncio.Queue(maxsize=MIOS_CONV_GATEWAY_QUEUE_MAXSIZE)`, and a `GatewayWorker.run(queue, agent, concurrency)` that runs `concurrency` consumer `asyncio.Task` slots, each calling `agent.run(payload)` through `asyncio.to_thread` (tool work may be CPU-bound) and resolving the future with the result or the exception. Build the agent as `smolagents.ToolCallingAgent` over `mios_capreg.get_tools()` (the existing RBAC-filtered manifest) with a `smolagents.LiteLLMModel` pointed at `MIOS_AI_ENDPOINT` per Law 5. Wire it in the `server.py` FastAPI `lifespan` behind `MIOS_CONV_GATEWAY_MODE == 'queue'`, cancelling the task and draining the queue within 5 s on shutdown. Add `dispatch_via_queue(payload, queue)` to `mios_dispatcher.py` and select between it and the existing `dispatch_via_http` by mode. The worker emits ONE `mios_trace.span(kind="tool_loop", ...)` per request, replacing the per-service double-write.
**Where:** `usr/lib/mios/agent-pipe/mios_gateway_queue.py`, `usr/lib/mios/agent-pipe/mios_dispatcher.py`, `usr/lib/mios/agent-pipe/server.py`
**Done When:** with `MIOS_CONV_GATEWAY_MODE=queue` a `POST /v1/chat/completions` is provably routed through `GatewayWorker` (one `kind=tool_loop` span in pgvector, not two); with `http` the legacy behaviour is unchanged; `LiteLLMModel.base_url` equals `MIOS_AI_ENDPOINT` in the logs; and request 65 against a 64-slot queue returns 429 without blocking the event loop.
**Why:** the localhost HTTP hop costs a serialization round trip on every turn, double-writes traces, and -- having no queue -- lets a retry storm open unbounded concurrent tool loops on the operator's own host.
**Dep:** T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Orchestration/Python

## T-096 -- CONV-03: dependency-free pytest suite for the GatewayQueue seam  (WS-CONV | P2 | M)
**Goal:** E-06 Test and documentation harness -- the queue's failure modes are proven by tests that run anywhere, not asserted in a commit message.
**What+How:** Add `usr/lib/mios/agent-pipe/test_mios_gateway_queue.py` with six tests, all passing with no llama-server and no pgvector: `test_put_get` (worker consumes a `GatewayRequest`, future resolves with the mock result); `test_future_resolution` (awaiting the future yields the correct response dict); `test_fallback_on_exception` (a worker exception resolves the future with an error dict rather than leaving it pending forever); `test_concurrency_4` (4 simultaneous requests resolve concurrently, wall time well under 4x a single request); `test_queue_full_429` (request `maxsize+1` returns a 429 dict without blocking); `test_shutdown_drain` (cancelling the worker resolves all pending futures with an error inside 5 s). Mock `smolagents.ToolCallingAgent.run` with `unittest.mock.AsyncMock` and register the file in `pytest.ini` or the existing runner config.
**Where:** `usr/lib/mios/agent-pipe/test_mios_gateway_queue.py`
**Done When:** `pytest test_mios_gateway_queue.py -v` reports 6 passed, with no external service socket touched, in under 10 seconds.
**Why:** the pending-future and drain paths are exactly the bugs that hang a request forever in production and are invisible to smoke tests that only exercise the happy path.
**Dep:** T-095 (CONV-02 GatewayQueue module).
**Status:** done-by-code | **Domain:** Testing

## T-097 -- CONV-04: shared prefix-cache reuse and parallel slots on the light llama lane  (WS-CONV | P2 | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- llama-swap already ships; this turns on its KV prefix reuse from SSOT rather than by hand-editing YAML.
**What+How:** Add `--cache-reuse 256 --np 4` to the `granite4.1:8b` and `lfm2:700m` `cmd` lines in `usr/share/mios/llamacpp/mios-llm-light.yaml` (GGUF path, port, ctx-size, n-gpu-layers, flash-attn, cache-type and slot-save-path all unchanged; `--np 4` replaces the implicit `--parallel 1` on lfm2), each preceded by the comment `# Part 10 CONV-04: --cache-reuse 256 (gate: MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS > 0); --np 4 for shared-prefix concurrency.` Drive the value from `[converge.inference].llama_cache_reuse_tokens` through a new firstboot helper that renders the flags into the `/etc/mios/llamacpp/mios-llm-light.yaml` overlay, with default 0 meaning the flags are simply not added.
**Where:** `usr/share/mios/llamacpp/mios-llm-light.yaml`, `automation/firstboot/mios-conv-inference-setup.sh`
**Done When:** with the gate enabled, `grep 'cache-reuse' /etc/mios/llamacpp/mios-llm-light.yaml` shows `--cache-reuse 256` and `--np 4` on both chat entries; llama-server `--debug-slot` logs report `cache_hit_tokens > 0` after repeated system-prompt turns; and with `llama_cache_reuse_tokens = 0` the overlay is unchanged.
**Why:** every agent turn re-processes the same long system prompt from scratch, paying 30-60% more time-to-first-token than needed on the lane that serves interactive chat.
**Dep:** T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Inference/Performance

## T-098 -- CONV-05: vLLM multi-LoRA heavy lane so one engine replaces two  (WS-CONV | P2 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- the heavy inference lane fits a single 24 GB GPU by serving adapters per request instead of running two whole model processes.
**What+How:** Update `usr/share/containers/systemd/mios-llm-heavy.container` with `VLLM_ALLOW_RUNTIME_LORA_UPDATING=true`, `VLLM_PLUGINS=lora_filesystem_resolver`, `VLLM_LORA_RESOLVER_CACHE_DIR=/var/lib/mios/lora-adapters/`, the serve flags `--enable-lora --max-loras 4 --max-cpu-loras 8 --max-lora-rank 64`, and `--lora-modules coding=/var/lib/mios/lora-adapters/coding reasoning=/var/lib/mios/lora-adapters/reasoning` as the pre-loaded set. Create `/var/lib/mios/lora-adapters/{coding,reasoning,vision}/` via tmpfiles.d or firstboot with a `.gitkeep` in each, and render `[converge.inference].vllm_lora_adapters_dir` into `userenv.sh`. Gate the Quadlet changes on `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE=single`; in the default `dual` mode the container is untouched. Mark `mios-llm-heavy-alt.container` deprecated pointing at `[converge.inference].retire_heavy_alt` (T-100).
**Where:** `usr/share/containers/systemd/mios-llm-heavy.container`, `usr/lib/tmpfiles.d/mios-lora-adapters.conf`, `usr/share/containers/systemd/mios-llm-heavy-alt.container`
**Done When:** `POST http://localhost:11441/v1/load_lora_adapter` returns 200 with runtime updating on, `GET :11441/v1/models` lists both the `coding` and `reasoning` adapter ids, `heavy_engine_mode=dual` leaves the container byte-identical, and the three adapter directories exist after firstboot.
**Why:** running `mios-llm-heavy` and `mios-llm-heavy-alt` as two model processes overruns the 4090's 24 GB budget -- roughly 12 GB is spent duplicating base weights that multi-LoRA would share.
**Dep:** T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Inference/vLLM

## T-099 -- CONV-06: LoRA load/list endpoints on agent-pipe + retire-safety drift rule  (WS-CONV | P2 | S)
**Goal:** E-11 Unified config surface: one door at :8640/ -- adapter control lives on the same `/v1/*` front door as everything else, addressed through SSOT keys rather than a literal port.
**What+How:** Add two endpoints to `usr/lib/mios/agent-pipe/server.py`. `POST /v1/inference/lora/load`: validate that the body carries `lora_name` and `lora_path`, then thin-proxy to `{MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY}/v1/load_lora_adapter` -- resolved from SSOT, never a hardcoded `:11441` (Law 5/Law 7). `GET /v1/inference/lora/list`: proxy `{MIOS_AGENT_PIPE_TOOL_BACKEND_HEAVY}/v1/models`, filter to adapter-type models and return `{"adapters": [...]}`, degrading to `{"adapters": [], "enabled": false}` whenever `MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE != "single"`. Extend the T-094 `check_converge_ssot` stub with a real rule: FAIL when `retire_heavy_alt=true` while `systemctl is-enabled mios-llm-heavy-alt.service` still reports enabled. Cover both endpoints in `test_lora_endpoints.py` with mocked httpx calls.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `automation/98-drift-checks.sh`, `usr/lib/mios/agent-pipe/test_lora_endpoints.py`
**Done When:** `curl localhost:8640/v1/inference/lora/list` returns `{"adapters":[...]}` on a vLLM heavy lane, the load endpoint proxies through to the heavy backend, both return the disabled shape under `heavy_engine_mode=dual`, and the drift-check FAILS on `retire_heavy_alt=true` with the alt unit still enabled.
**Why:** adapters would otherwise only be loadable by curling the engine port directly, and nothing would catch the half-retired state where SSOT says the alt lane is gone but systemd still starts it.
**Dep:** T-094 (CONV-01), T-098 (CONV-05 vLLM multi-LoRA).
**Status:** done-by-code | **Domain:** API/Inference

## T-100 -- CONV-07: inference-consolidation migration guide + heavy-alt deprecation notice  (WS-CONV | P2 | S)
**Goal:** E-06 Test and documentation harness: doc integrity -- the retirement of a live service ships with a written, reversible procedure an operator can follow cold.
**What+How:** Write `usr/share/doc/mios/guides/inference-consolidation.md` covering the current dual-heavy topology and why it exceeds the 4090's 24 GB budget; the migration path (`[converge.inference].heavy_engine_mode = "single"`, restart `mios-llm-heavy`, verify `GET /v1/inference/lora/list`, set `retire_heavy_alt = true`, `systemctl disable mios-llm-heavy-alt`); the rollback (`heavy_engine_mode = "dual"`, re-enable both container units); the VRAM budget table from ROADMAP 10.2.5; and the operator note on populating `lora-adapters/` by manual GGUF placement. Add the deprecation block to the alt Quadlet: `# DEPRECATED (Part 10, 2026-06-25): retire by setting [converge.inference].retire_heavy_alt = true and running the migration guide at usr/share/doc/mios/guides/inference-consolidation.md.`
**Where:** `usr/share/doc/mios/guides/inference-consolidation.md`, `usr/share/containers/systemd/mios-llm-heavy-alt.container`
**Done When:** the guide renders in the `mios-docs` service, the deprecation comment is present in `mios-llm-heavy-alt.container`, and the guide contains explicit rollback instructions.
**Why:** an operator who flips `heavy_engine_mode` with no documented verify-and-rollback path can take the heavy lane down with no way back, and the alt Quadlet gives no hint it is on its way out.
**Dep:** T-098 (CONV-05), T-099 (CONV-06).
**Status:** done | **Domain:** Docs/Migration

## T-101: CONV-08 -- Tier-0 sqlite-vec session scratchpad module  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- gives the agent an ephemeral Tier-0 vector store so pgvector holds durable recall only, never every transient tool output.
**What+How:** Add a new dependency-light module `mios_scratchpad.py` (no FastAPI globals) exposing `create_scratchpad(session_id, scratchpad_dir) -> (sqlite3.Connection, Path)` which opens `{scratchpad_dir}/mios-session-{session_id}.sqlite` on tmpfs, loads `sqlite_vec`, and creates `vec_scratch USING vec0(content TEXT, embedding float[768])`; plus `vec_insert(conn, content, embedding)` using sqlite-vec's `serialize_float32`, `vec_search(conn, query_embedding, k=5)` doing `WHERE embedding MATCH ? ORDER BY distance LIMIT ?`, and `destroy_scratchpad(conn, path)` (close + unlink). Register `sqlite-vec` in `requirements.txt`. Gate the real implementation on `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=true`; when false the module is a stub returning empty results with no `sqlite_vec` import, so the runtime dep stays optional. Law 5 invariant holds: embeddings are still fetched from `MIOS_AI_ENDPOINT/v1/embeddings` -- sqlite-vec only stores the vectors it is handed. Cover create/insert/search/destroy in `test_mios_scratchpad.py` with a mocked float list and no pgvector connection.
**Where:** `usr/lib/mios/agent-pipe/mios_scratchpad.py` (new), `usr/lib/mios/agent-pipe/requirements.txt`, `usr/lib/mios/agent-pipe/test_mios_scratchpad.py` (new)
**Done When:** `python -c "import mios_scratchpad; c,p = mios_scratchpad.create_scratchpad('test','/tmp'); mios_scratchpad.vec_insert(c,'hello',[0.1]*768); assert len(mios_scratchpad.vec_search(c,[0.1]*768))==1; mios_scratchpad.destroy_scratchpad(c,p)"` exits 0; `pytest test_mios_scratchpad.py` passes with no external services; with the enable flag false the stub returns `[]` and `sqlite_vec` is never imported; the session file lands under `/run/user/<uid>/`, not `/var/lib/`.
**Why:** Without a Tier-0 store every tool output and reasoning trace is written straight to pgvector, so the durable memory table fills with per-turn garbage that has to be evicted later and pollutes recall quality.
**Dep:** T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Memory/Python

---

## T-102: CONV-09 -- Cold-eviction module with zstd JSONL export  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- completes the three-tier memory model so TTL-expired rows leave PostgreSQL as durable archives instead of being destroyed or hoarded.
**What+How:** Add `mios_cold_evict.py` alongside (never modifying) the existing `mios_evict.py`. `export_to_cold(pg, row_ids, table, dest_dir, zstd_level) -> Path` selects `row_to_json(t)` for the id set via `mios_pg.execute`, writes one JSON object per line to `{dest_dir}/{YYYY}/{MM-DD}/{uuid4()}.jsonl.tmp`, shells `zstd --level=<n> -o <dst>.zst <dst>.tmp` under `check=True`, removes the `.tmp`, and returns the `.zst` path. `cold_sweep(pg, plan, table, dest_dir, zstd_level) -> {"exported": N, "dest": str}` chains `mios_evict.select_ids_sql` -> `export_to_cold` -> `mios_evict.delete_ids_sql`, inheriting the `evict_where` filter so hot/pinned/satisfied rows can never be exported. Call `cold_sweep` from the existing eviction background task in `server.py` after the current sweep, gated on `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE`, and log `event(kind="cold_evict", rows=N, dest=path)` to pgvector. `test_mios_cold_evict.py` mocks `mios_pg.execute` and `subprocess.run` to assert export+delete ordering, `.tmp` cleanup on error, and the exact zstd argv.
**Where:** `usr/lib/mios/agent-pipe/mios_cold_evict.py` (new), `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/test_mios_cold_evict.py` (new)
**Done When:** `pytest test_mios_cold_evict.py` passes with no external services; `zstd --test /var/lib/mios/history/.../*.jsonl.zst` exits 0 after a simulated sweep; the PostgreSQL row count drops after the sweep (moved, not duplicated); `event(kind="cold_evict")` appears in the pgvector `event` table; a unit test proves hot/pinned/satisfied rows are never exported.
**Why:** Today eviction is a pure delete -- expired history is unrecoverable, so operators either lose it or disable eviction and let the pgvector tables grow without bound.
**Dep:** T-094 (CONV-01 SSOT), T-101 (CONV-08 memory SSOT wiring).
**Status:** done-by-code | **Domain:** Memory/Storage

---

## T-103: CONV-10 -- Wire the sqlite-vec scratchpad into GatewayWorker  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- makes Tier 0 actually intercept per-turn tool output so only end-of-session synthesis reaches Tier 1 pgvector.
**What+How:** In `mios_gateway_queue.py`, wrap each request execution in `GatewayWorker.run()` with a scratchpad lifecycle: `conn, path = await asyncio.to_thread(mios_scratchpad.create_scratchpad, session_id, scratchpad_dir)` and a `finally:` that calls `destroy_scratchpad` through `asyncio.to_thread`, so the sqlite handle never blocks the event loop and the tmpfs file is always reaped. Inside `_execute_with_scratchpad`, after every tool call in the smolagents loop, fetch the embedding from `MIOS_AI_ENDPOINT/v1/embeddings` (Law 5) and `vec_insert` the tool output into the session store instead of persisting it. The whole lifecycle is gated on `MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=true`; when false the T-101 stub makes insert a no-op and search return empty.
**Where:** `usr/lib/mios/agent-pipe/mios_gateway_queue.py`
**Done When:** With the flag on, the session sqlite file is created at session start and gone at session end; logs show each tool-output embedding fetched via `MIOS_AI_ENDPOINT/v1/embeddings`; the pgvector `event` table records zero `kind=tool_output` rows per turn; with the flag off there is no `sqlite_vec` import and no measurable latency change.
**Why:** The T-101 module is dead code until a caller owns its lifecycle -- transient tool outputs keep landing in pgvector one row per call, which is exactly the write amplification the tiering was built to stop.
**Dep:** T-095 (CONV-02 GatewayWorker), T-101 (CONV-08 scratchpad module).
**Status:** done-by-code | **Domain:** Orchestration/Memory

---

## T-104: CONV-11 -- Cold-archive retention sweep plus converge drift-check  (WS-VECTOR | P2 | S)
**Goal:** E-23 DB-driven configuration and vector recall -- bounds the Tier-2 archive and puts its configuration under the drift gate so a misconfigured tier cannot silently corrupt storage.
**What+How:** Add `_cold_retention_sweep()` to the existing eviction background task in `server.py`: walk `cold_storage_dir` recursively for `.jsonl.zst` files older than `cold_retention_days`, delete them, and log `event(kind="cold_retention_sweep", deleted=N, cutoff_days=D)`, all gated on `MIOS_CONV_MEMORY_COLD_EVICT_ENABLE=true`. Extend `check_converge_ssot` in `automation/98-drift-checks.sh` with the Phase 3 rules: `cold_storage_dir` must not sit inside a CephFS mount (test against the `MIOS_CEPHFS_MONITORS` host prefix or a `/tenants/` path segment -- cold archives are node-local by design), `cold_retention_days >= 1`, `1 <= cold_zstd_level <= 19`, and if `sqlite_vec_enable=true` then `python3 -c "import sqlite_vec"` must exit 0. Write `usr/share/doc/mios/guides/memory-tiering.md` documenting the three tiers (Tier 0 sqlite-vec, Tier 1 pgvector, Tier 2 zstd cold archive), how to enable them, and how to query an archive with `zstd -d | jq`.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `automation/98-drift-checks.sh`, `usr/share/doc/mios/guides/memory-tiering.md` (new)
**Done When:** Files older than `cold_retention_days` disappear on the next sweep and `event(kind="cold_retention_sweep")` is logged; the drift-check FAILs when `cold_storage_dir` is a CephFS path and when `cold_zstd_level > 19`; the memory-tiering guide renders in `mios-docs`.
**Why:** Without a retention sweep and its guardrails the cold archive grows forever, and nothing stops an operator pointing it at distributed CephFS storage -- turning node-local archival writes into cluster traffic.
**Dep:** T-102 (CONV-09 cold eviction), T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Storage/CI

---

## T-105: CONV-12 -- Hummingbird distroless Containerfile for agent-pipe  (WS-SEC | P3 | M)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- removes the package manager and shell from the agent-pipe runtime so the container's trust surface is only the app and its venv.
**What+How:** Add `Containerfile.hummingbird` beside the existing `Containerfile` as a two-stage build. Builder: `FROM python:3.13-slim AS builder`, install `gcc`/`libsqlite3-dev`, `python -m venv /opt/venv`, `pip install --no-cache-dir -r requirements.txt`. Runtime: `FROM gcr.io/distroless/python3-debian13`, copy `/opt/venv` and `usr/lib/mios/agent-pipe/` to `/app/`, set `PATH`/`PYTHONPATH` to the venv, `USER 65534:65534` (Law 6 nonroot), `EXPOSE 8640`, and `CMD` running uvicorn on `server:app` with `--workers 1 --loop uvloop`. Because a distroless image has no shell, `profile.d` cannot supply `MIOS_AI_ENDPOINT` -- verify the Quadlet `mios-agent-pipe.container` carries an explicit `Environment=MIOS_AI_ENDPOINT=...` line and add it if absent (Law 5). Land a `check_hummingbird` stub in `98-drift-checks.sh` (full rules in T-108). Selection is gated: the distroless Containerfile is used only when `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=true`, and the default `Containerfile` path is untouched.
**Where:** `Containerfile.hummingbird` (new), `usr/share/containers/systemd/mios-agent-pipe.container`, `automation/98-drift-checks.sh`
**Done When:** `podman build -f Containerfile.hummingbird -t mios-agent-pipe:hummingbird .` succeeds; `podman run --rm ... id` reports `uid=65534`; `... which bash` exits non-zero; `podman inspect ... | jq '.[0].Config.Env[]|select(test("MIOS_AI_ENDPOINT"))'` returns the endpoint; with the flag false the original Containerfile builds unchanged.
**Why:** The current runtime image ships `dnf`, `bash` and the OS package cache -- roughly 200-400 MB of CVE-bearing surface that the agent-pipe process never uses but an attacker with code execution would.
**Dep:** T-095 (CONV-02 merged process -- required for the single CMD entrypoint).
**Status:** done | **Domain:** Image/Security

---

## T-106: CONV-13 -- Unified MCPClientPool for all tool invocations  (WS-DEBT-PIPE | P3 | M)
**Goal:** E-02 Technical-debt retirement -- collapses per-service MCP SDK duplication in the merged agent-pipe process into one pooled, typed tool catalog.
**What+How:** Add an `MCPClientPool` class to `mios_gateway_queue.py`: `__init__(server_configs)` builds one `mcp.StdioClient` or `mcp.HTTPClient` per entry in `[tools.mcp_servers]` from `mios.toml` according to its `transport`; `async startup()` connects every client and caches its tool schemas; `async shutdown()` closes them cleanly; `get_tools()` returns the single unified schema list that replaces the per-service caches. Instantiate the pool in the `server.py` `lifespan` handler gated on `MIOS_CONV_IMAGE_MCP_POOL_ENABLE=true` and hand it to the worker as `worker.mcp_pool`. In `mios_interop.py` (WS-11 A2A), feed `MCPClientPool.get_tools()` into the 3-projection A2A skill shape so federated peers see the same catalog the local agent sees. `test_mios_mcp_pool.py` mocks `mcp.StdioClient.connect` to assert startup, catalog contents and clean shutdown.
**Where:** `usr/lib/mios/agent-pipe/mios_gateway_queue.py`, `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/mios_interop.py`, `usr/lib/mios/agent-pipe/test_mios_mcp_pool.py` (new)
**Done When:** `GET /v1/tools` returns one entry per MCP server with no duplicates; MCP connections are established once at startup rather than per request; the A2A skill projection in `mios_interop.py` reads from the same pool; `pytest test_mios_mcp_pool.py` passes with no MCP server running.
**Why:** Now that the services share one process, each still opens its own MCP clients per request -- duplicated schemas mean a tool can appear twice in `/v1/tools`, and A2A peers can be shown a catalog that disagrees with the local one.
**Dep:** T-095 (CONV-02 GatewayWorker), T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Tool/MCP

---

## T-107: CONV-14 -- rechunk build step with component xattrs  (WS-BAKE | P3 | S)
**Goal:** E-16 The bake plane -- makes the published image's OCI layers chunk along component boundaries so an upgrade ships deltas instead of whole layers.
**What+How:** Create `automation/build/rechunk.sh` that reads the source digest with `podman inspect mios-bootc:latest --format '{{.Digest}}'`, runs `podman unshare rpm-ostree experimental compose build-chunked-oci --bootc --format-version=1 --from="$SRC_DIGEST" --output containers-storage:mios-bootc:rechunked`, and tags component xattrs (`setfattr -n user.component`) for `ai-sidecar` on `/usr/lib/mios/agent-pipe/` and `/usr/share/mios/llamacpp/` and `llm-models` on `/var/lib/mios/models/` so the chunker separates the volatile AI payload from the OS. Add an additive `just rechunk` recipe to the `Justfile` that invokes it after `just build` without replacing any existing recipe. Gate on `MIOS_CONV_IMAGE_RECHUNK_ENABLE`: when false the script prints "rechunk disabled" and exits 0. Add `check_rechunk_env` to `check_converge_ssot` that FAILs when `rechunk_enable=true` but `rpm-ostree` is not on PATH.
**Where:** `automation/build/rechunk.sh` (new), `Justfile`, `automation/98-drift-checks.sh`
**Done When:** `just rechunk` completes when the flag is true and `rpm-ostree` is present, and exits 0 silently when the flag is false; `mios-bootc:rechunked` exists in local container storage afterwards; the drift-check FAILs when the flag is on but `rpm-ostree` is absent.
**Why:** Without rechunking, every image build reshuffles layer content, so a `bootc upgrade` that changes only the agent-pipe payload still pulls multi-GB layers containing unchanged model and OS content.
**Dep:** T-094 (CONV-01 SSOT).
**Status:** done-by-code | **Domain:** Image/CI

---

## T-108: CONV-15 -- Full check_hummingbird drift-check plus distroless guide  (WS-DRIFT | P3 | S)
**Goal:** E-07 The drift-gate as the enforcement plane -- turns the distroless and rechunk invariants from convention into machine-checked policy registered in the gate.
**What+How:** Replace the T-105 stub with a full `check_hummingbird` in `automation/98-drift-checks.sh`, registered in `main()` immediately after `check_converge_ssot`. It FAILs when: `MIOS_CONV_IMAGE_DISTROLESS_ENABLE=true` and `Containerfile.hummingbird` is missing; the final-stage `USER` line is not `USER 65534` or `USER 65534:65534` (Law 6); `/bin/bash` appears anywhere in the final stage; distroless is enabled but `mios-agent-pipe.container` lacks an `Environment=MIOS_AI_ENDPOINT` directive (Law 5 -- there is no `profile.d` to fall back on); or `rechunk_enable=true` with `rpm-ostree` off PATH. Write `usr/share/doc/mios/guides/hummingbird-distroless.md` covering why distroless (attack-surface reduction, Law 6), the multi-stage build walkthrough, why the endpoint must arrive through the Quadlet `Environment=` line, how to debug without a shell (OpenTelemetry traces plus the pgvector `event` table are the observability surface), Chainguard (`cgr.dev/chainguard/python:latest-dev`) as an alternative base, and a `just rechunk` quickstart.
**Where:** `automation/98-drift-checks.sh`, `usr/share/doc/mios/guides/hummingbird-distroless.md` (new)
**Done When:** `just drift-gate` FAILs on each of: `USER root` in the distroless stage, a missing `Environment=MIOS_AI_ENDPOINT` in the Quadlet, and `/bin/bash` present in the final stage; it passes on a correct config; the hummingbird guide renders in `mios-docs`.
**Why:** A distroless image with no enforcing check regresses the first time someone adds a debug shell or drops the `USER` line, and the Law 5 endpoint wiring fails silently at runtime because there is no shell to source it from.
**Dep:** T-105 (CONV-12 distroless Containerfile), T-107 (CONV-14 rechunk).
**Status:** done | **Domain:** CI/Docs

---

## T-031: ORCH-04 -- Bound the ReAct+Reflexion loop with real SSOT budgets  (WS-DURA | P1 | M)
**Goal:** E-24 Autonomy guardrails -- makes the self-driving reasoning loop terminate by construction instead of spinning out a non-terminating "Reflexion essay".
**What+How:** Execute Wave 4 of `MIOS-CHATQ-FV-WORKPLAN.md`. The `done-by-code` claim is false: `[agent].reflexion_enable` reads a phantom TOML section (only `[agents]` plural exists) so the flag is always-true, and `max_iter`/`max_retry`/`no_progress` do not exist in `mios.toml` at all. Create a real `[agent_pipe]` SSOT block holding `reflexion_enable` plus every loop budget, and replace the literals at `server.py:835` and `server.py:3314` with SSOT reads. In `secondary_loop.py` add a normalized no-progress signature (so one-token argument variation no longer evades the exact-match repeat guard), a per-turn blacklist of failed `(tool,args)` pairs, and `max_consecutive_failures` escalation triggered off the failure signal rather than the give-up branch; enforce `wall_clock_budget_s` as a hard bound. Wire the structured `reflect_on_step_failure` from `reflect.py` into the native/`@` path -- currently it is only reachable on the DAG path -- as emit-or-terminate, kept internal. Add a drift-check asserting every budget key declared in `[agent_pipe]` has a code consumer.
**Where:** `usr/share/mios/mios.toml [agent_pipe]`, `usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py` (44-60, 265, 345-408), `.../routing/native_loop.py`, `.../routing/reflect.py`, `.../server.py` (835, 3314), `automation/98-drift-checks.sh`
**Done When:** `reflexion_enable` and all budgets resolve from `[agent_pipe]` with no `[agent]` or literal fallbacks left and the drift-gate green; an identical failing `(tool,args)` is never retried and the loop terminates or escalates inside `wall_clock_budget_s`; the failure path emits a structured corrective action or terminates, never free-text in `content`; live-fired in `podman-MiOS-DEV`, a deliberately failing tool call does not loop.
**Why:** Today a failing tool call produces an unbounded retry loop that burns GPU and tokens until the operator kills the session, and the reflection output leaks into the user-visible answer as an essay.
**Dep:** none
**Status:** done | **Domain:** Orchestration

---

## T-109: CHATQ-01 -- Route refine/plan trace to the reasoning channel, one answer in content  (WS-DEBT-PIPE | P1 | M)
**Goal:** E-02 Technical-debt retirement -- puts the agent-pipe streaming path behind typed, channel-pinned events so the wire contract is explicit instead of debug-flag-dependent.
**What+How:** Wave 1 (Claude C1-C3). Today refine's `{Refined Query/Intent/Reply}` scaffold streams straight into `delta.content` via `chat.py:1425-1426` -> `sse.py:93-94` under `_DEBUG_ENABLE`, and the answer is restated three times because the refine `reply`, the local-state pass and the polish pass all reach content. Route the refine pump and the `_refine_reasoning` summary through a channel-pinned emitter in `sse.py` that always targets the reasoning channel regardless of `_DEBUG_ENABLE`, and extend the `_live_streamed` guard at `native_loop.py:858` so exactly one generation is allowed to reach `content`. Refine's `reply` is reclassified as trace, not answer. Visibility is preserved end to end -- only the channel and the de-duplication change.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py`, `.../routing/chat.py` (1425-1426, 1482-1495, 1789-1803), `.../routing/native_loop.py` (858, 1061, 1101-1102)
**Done When:** The refine trace renders in the Thinking pane and never in `delta.content`; `@ what directory are we in right now` returns exactly one clean answer with no `Refined Query/...` block and no triple restatement; output is byte-identical to today when the `[observability]` flags are off (degrade-open).
**Why:** Every chat turn currently shows the user the internal refine scaffold and repeats the answer three times, which makes the product look broken and pollutes the persisted history that feeds the next turn's KV cache.
**Dep:** none
**Status:** done | **Domain:** Observability/Orchestration

---

## T-110: FV-01 -- Canonical typed-event schema, per-surface routing, sub-agent visibility  (WS-DEBT-PIPE | P1 | L)
**Goal:** E-02 Technical-debt retirement -- replaces content-inlining with one typed wire schema every stage and sub-agent emits into, so full visibility is a contract rather than a debug hack.
**What+How:** Wave 1. Define one event schema -- `thinking | plan | tool_call | tool_result | source | content` -- that every stage and every sub-agent emits into. Replace the blanket `enable_thinking:False` at `agent_call.py:820-821` and `swarm.py:1237` (which turns leaf thinking off at the source) with a per-lane `[lanes.*].stream_thinking` switch. Add a channel discriminator to the fan-out `_push` merged event, which today carries none. Retire content-inlining as the visibility mechanism: `[observability].debug` should gate only content-mirroring for strict surfaces. Add per-surface routing keyed on the `X-MiOS-Surface` / `reasoning_ok` request signals, with a MiOS-owned replay-strip so persisted history stays clean. Translate `mios_status` to status events and refs to source events in the OWUI pipe. Split of work: AGY owns the SSOT blocks and the OWUI pipe; Claude owns the emitter and `agent_call`.
**Where:** `usr/share/mios/mios.toml` `[observability]`, `[observability.channels]`, `[lanes.*]`; `usr/share/mios/owui/pipes/mios_agent_pipe.py`; `usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py`, `.../routing/agent_call.py` (738-746, 797-885, 820-821), `.../server.py`, `.../swarm.py`
**Done When:** Every sub-agent's thinking, tool calls and sources stream live on OWUI and Hermes while strict clients receive a folded inline trace and the final answer appears only in `content`; the KV cache survives across turns because persisted history is the clean answer only; setting `stream_thinking=false` on one lane downgrades just that lane (degrade-open).
**Why:** The full-visibility mandate is currently faked by inlining traces into content under a debug flag, leaf agents' reasoning is discarded at source, and strict clients cannot see the reasoning channel at all -- so operators cannot tell what a multi-agent turn actually did.
**Dep:** none
**Status:** done | **Domain:** Observability | **Who:** AGY owns SSOT + OWUI pipe; Claude owns emitter + `agent_call`

---

## T-111: CHATQ-02 -- Constrained tool-calling, tools on the final pass, verb-catalog repair  (WS-CODEMODE | P1 | L)
**Goal:** E-24 Autonomy guardrails -- makes tool invocation a structurally guaranteed typed call instead of text the model narrates and the user has to read.
**What+How:** Wave 2. The answer-shaping completion fires with no `tools[]` (`native_loop.py:780-782`), so residual tool intent leaks as literal `<tool_call>` / ```json``` text; `linux_file_search` is marked `hidden` yet name-dropped in visible descriptions, so the model wraps it into `launch_app`; no lane uses constrained decoding; and the rescue path returns after the first block and is gated on empty `tool_calls`. AGY side: set engine `--tool-call-parser` / `--reasoning-parser` and `constrained_tools` per lane in `[lanes.*]`, consolidate the duplicate `launch_app` verb definitions (9084/3157), correct the `fs_search` description (3465-3473), stop advertising uncallable names, and fix `[routing.domains.files].verbs` (3103-3110). Claude side: pass `tools[]` to `_pb`, replace the text salvage with a streaming-aware one that re-emits as typed events (still visible), diverts them off `content` and actually executes them, remove the first-block early return in `secondary_loop.py`, and surface routed-domain verbs even when hidden by keying the Stage-2 filter on the canonical verb name.
**Where:** `usr/share/mios/mios.toml` `[lanes.*]`, `[verbs.launch_app]` (9084/3157), `fs_search` (3465-3473), `[routing.domains.files]` (3103-3110); `.../routing/native_loop.py` (780), `.../routing/secondary_loop.py` (309, 334-344), `.../routing/toolexec.py` (210-279), `.../server.py` (3956, 4028-4034), `.../verbcatalog.py`, `.../mios_endpoints.py`
**Done When:** A narrated tool call renders as a native typed tool pill and never as text in `delta.content`; any files turn always carries a callable `linux_file_search` with no `launch_app` misroute; live-fired, `@ what's here?` fires a real typed file/`list_dir` call.
**Why:** Users currently see raw `<tool_call>` JSON in the answer, and file questions get routed to an app launcher, so the tool plane looks and behaves like a hallucination even when the model's intent was correct.
**Dep:** T-112 (list_dir gives the correct files-turn verb), T-110 (typed tool_call channel).
**Status:** done | **Domain:** Tool-calling | **Who:** AGY (SSOT/engine flags) + Claude (pipe code)

---

## T-112: CHATQ-03 -- First-class list_dir verb and cwd act-before-answer grounding  (WS-CODEMODE | P1 | M)
**Goal:** E-24 Autonomy guardrails -- gives the agent a real directory-listing primitive so "what's here?" is answered from the filesystem rather than from priors.
**What+How:** Wave 3. No `list_dir` verb exists today: `linux_file_search` is a `mios-locate` substring search, not `ls`, and `read_file`/`text_view` can list a directory but is depth-2/500-entry capped and framed as "read a file" -- so with only a cwd string injected and no lister auto-firing, the model hallucinates a generic FHS table. AGY side: add a `--depth 1` immediate-children mode to `usr/libexec/mios/mios-text-edit` (83-84, 219-241), add `[verbs.list_dir]` with `model_name=list_directory`, a `path` argument defaulting to cwd, and an accurate description plus examples, and redirect the `read_file`/`fs_search` descriptions accordingly. Claude side: fire `list_dir(path=cwd)` from `_read_tool_enrich` in `server.py` whenever a cwd is present (keyed off the SSOT `_client_env` cwd), and add a model-chosen filesystem/`state_scope` signal to refine so directory-content queries set `tool_choice:required`. Selection must stay classifier-driven, never an English keyword match.
**Where:** `usr/libexec/mios/mios-text-edit` (83-84, 219-241); `usr/share/mios/mios.toml` `[verbs.list_dir]` plus `fs_search`/`read_file` descriptions; `.../server.py` `_read_tool_enrich` (4648, 4685-4701, 4734-4745); `.../routing/refine.py`, `.../routing/chat.py` (1193-1198)
**Done When:** `list_dir` with no argument lists the cwd's immediate children with true `ls` semantics; `@ what's here?` returns the real directory contents, never a generic FHS table; the decision to call it is made by the classifier, not a keyword match.
**Why:** The most basic filesystem question an operator asks returns invented output today, which destroys trust in every other grounded answer -- and T-032 is blocked because it assumes a `list_directory` op that does not exist.
**Dep:** none (**Unblocks:** T-032 -- its allow-listed `list_directory` op now exists)
**Status:** done | **Domain:** Tool-calling/Grounding

---

## T-113: FAB-01 -- Stop the @ agent-pipe fabricating tool execution and results  (WS-GUARD | P0 | L)
**Goal:** E-24 Autonomy guardrails -- enforces the hard invariant that a tool result can only be produced by a tool that actually ran.
**What+How:** In a live session `@ launch fakegame` emitted a fake `🤝 open_app output: {"success":true,"pid":8421,"window":{"handle":0x7f12345678,...}}` -- the same fake pid and handle on every launch, for an invented app -- while nothing launched, whereas the parallel `hermes` path ran a real `mios-windows launch`. Root-cause why the `@`/agent-pipe turn produces a fabricated tool-result block instead of a real `toolexec` dispatch or a real hand-off to Hermes `:8642`, and confirm or repair the `usr/bin/mios` route (the `@` path is supposed to reach Hermes-direct). Enforce the invariant in code: no `🤝 <tool> output:` envelope may be emitted unless `_exec_tool_calls` produced it. Ship a fabrication guard -- `_contains_tool_result_block` in `chat.py` short-circuits any chat reply that narrates a tool-result / success-JSON block and routes it to the real executor, and `native_loop.py` strips the same shape for any verb not present in `_fired` -- with unit coverage in `test_mios_antifab.py`, and re-dispatch the turn rather than passing the text through.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/{chat,native_loop,secondary_loop,toolexec}.py`, `.../routing/refine.py`, `usr/bin/mios` (route), `usr/lib/mios/agent-pipe/server.py` (dispatch), `usr/lib/mios/agent-pipe/test_mios_antifab.py`
**Done When:** `@ launch fake game` either performs a real launch or states it could not, never a fabricated success with a fake pid/handle (needs live `@`-session verify); no tool-result block reaches the user without a matching executed `tool_call` row (needs live `@`-session verify); the identical-fake-pid fabrication cannot recur -- guard plus test, already landed.
**Why:** The agent currently tells the operator it did something it did not do, with plausible fabricated evidence; anti-fabrication is the operator's core value, so every other capability is worthless while this holds.
**Dep:** none
**Status:** done-by-code (fix reproduction-tested; live @-verify pending) | **Domain:** Anti-Fabrication/Orchestration

---

## T-114: FAB-02 -- Stop fabricated web/news content and invented entities on misclassification  (WS-GUARD | P0 | M)
**Goal:** E-24 Autonomy guardrails -- makes every citation and entity name traceable to a real fetch, so grounding failures surface as honest notes instead of confident fiction.
**What+How:** In a live session the gibberish input `??!!!?` was refine-misclassified as a "weekly news roundup" and the pipeline fabricated five articles attributed to real outlets (NYT/Reuters/BBC/FT/TechCrunch) with invented events, claiming `web_search` had run when it had not; it also invented a nonexistent app ("FakeGame 6"). Add a hard anti-fabrication gate: never emit web/news content or source attributions that a real `web_search`/fetch call did not return, and never invent entity names. Fix the refine classifier in `refine.py` so low-signal or gibberish input is classified as chat/clarify rather than promoted into a fabricated task plan. Attribution must be drawn only from fetched results in the web-research enrich path and `mios_grounding.py`. The shipped guard is structural, not keyword-based: `native_loop.py` rewrites the answer to an honest note when a web/news turn cites an off-list URL, or when it produces a markdown report table having fetched zero sources. Model-driven throughout -- no keyword gate.
**Where:** `.../routing/refine.py` (classifier), `.../routing/chat.py` (web-research enrich), `usr/lib/mios/agent-pipe/mios_grounding.py`, `.../routing/native_loop.py`, `.../federation` web tools
**Done When:** Gibberish input yields a clarify/chat turn, never a fabricated news roundup (needs live `@`-session verify; classifier reclassification is out of scope for the shipped guard); no source citation appears unless a real fetch produced it -- landed as the structural off-list-URL / zero-sources-with-report-table guard, SSOT-wired, with live confirmation still pending.
**Why:** The pipeline currently attributes invented events to real news organizations, which is both a trust-destroying failure and a reputational and legal hazard the moment such output is shared.
**Dep:** none
**Status:** done-by-code (fix reproduction-tested; live @-verify pending) | **Domain:** Anti-Fabrication/Grounding

---

## T-115: CQ1 -- Deploy T-109 and de-duplicate the refine pass on the strict CLI surface  (WS-DEBT-PIPE | P1 | S)
**Goal:** E-02 Technical-debt retirement -- finishes the channel-routing fix on the surface that has no reasoning channel, so the strict CLI gets one clean folded trace.
**What+How:** Extends T-109. On the live CLI the `Refined Text/Intent/Reply` scaffold still streams verbatim, because the surface-aware `_sse_reasoning` fix is authored but undeployed and the CLI sends no `x-mios-reasoning-ok` header, so it falls through to the legacy debug-inline path; separately `"🧠 Refining intent..."` fires two to three times per turn. Deploy the T-109 change, de-duplicate the refine pass so it runs once per turn, and confirm the strict-CLI folded-trace path (FV-F) shows the trace exactly once with no raw scaffold. Fold the work into the T-109/T-110 branch rather than shipping a parallel fix.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/{chat,sse,refine}.py`
**Done When:** A CLI turn shows no `Refined Text/Intent/Reply` scaffold in the answer, the folded trace appears once, and `🧠 Refining intent...` fires exactly once per turn.
**Why:** T-109's fix is invisible to the operator's primary surface until it is deployed and the strict-client path is wired, and the duplicated refine pass costs two to three extra model calls on every single turn.
**Dep:** T-109 (extends it)
**Status:** done | **Domain:** Observability

---

## T-116: OSCTL-01 -- Browser open-URL reuses the running instance and opens a tab  (WS-CODEMODE | P1 | M)
**Goal:** E-24 Autonomy guardrails -- makes an OS-control verb honor the operator's stated intent instead of taking the one coarse action it knows.
**What+How:** In a live `hermes` session, "open a firefox TAB to youtube" launched the Firefox Nightly shortcut twice (two new windows) and opened several stray Epiphany tabs, even though Firefox was already running and a tab was explicitly requested -- because the launch path uses `mios-windows launch <shortcut>`, which always spawns a new window. Make browser open-URL tab-aware: detect an already-running browser instance and open a new tab in it (CDP `Target.createTarget`, `--new-tab`, or activate-existing), cold-launching only when the browser is not running, honoring an explicit "tab" request, and never fanning out extra Epiphany tabs.
**Where:** `usr/lib/mios/agent-pipe/mios_oscontrol.py`, `.../routing/oscontrol.py`, `usr/libexec/mios/mios-windows`, the browser/CDP skills
**Done When:** "open a firefox tab to `<url>`" with Firefox already open produces exactly one new tab in the existing window and no new window (live-verified by the operator).
**Why:** Every browser request currently multiplies the operator's open windows and opens unrelated browsers, so routine OS-control asks leave the desktop worse than before.
**Dep:** none
**Status:** done | **Domain:** OS-Control

---

## T-117: OSCTL-02 -- Container exec: SSOT name resolution, non-interactive, podman-first  (WS-CODEMODE | P1 | M)
**Goal:** E-24 Autonomy guardrails -- keeps an agent-issued container exec bounded and correctly targeted so it cannot hang the turn.
**What+How:** In a live `hermes` session, "ssh into code-server container" tried `docker` first (the runtime is podman), used the retired name `code-server` (now `mios-agents`), wrongly exec'd into `mios-open-webui`, and hung for 172s and 21s on `podman exec -it ... bash` because the agent context has no TTY; the memory tool also errored mid-session. Four fixes: (1) resolve container names through SSOT `[containers.*]` with a retired-name alias so `code-server` maps to `mios-agents`; (2) never issue interactive `-it` exec from the agent -- always `podman exec <container> <cmd>` with an explicit command and no bare shell, so it cannot block on a TTY; (3) prefer podman as the SSOT runtime and skip docker probing entirely; (4) investigate the mid-session memory-tool error.
**Where:** `usr/lib/mios/agent-pipe/mios_oscontrol.py`, `usr/libexec/mios/*`, the Hermes tool skills, container-name SSOT in `usr/share/mios/mios.toml` `[containers.*]`
**Done When:** "exec into the code-server container" targets `mios-agents`, runs non-interactively, returns in under five seconds, and never passes `-it`.
**Why:** An agent exec today can hang for minutes against a TTY that will never appear, and lands in the wrong container when it does return -- a stalled turn the operator has to kill.
**Dep:** none
**Status:** done | **Domain:** OS-Control

---

## T-118: HEALTH-01 -- Override the baked llama-swap healthcheck with an SSOT HealthCmd  (WS-SYSTEMD | P1 | S)
**Goal:** E-18 Generate the systemd units from SSOT -- makes the container health contract a rendered property of `[containers.*]` rather than whatever the upstream image happened to bake in.
**What+How:** Both llama-swap:cuda lanes report Unhealthy on the podman dashboard, but live probing corrects the original "oversized KV" premise: the lanes are up -- `curl :${MIOS_PORT_CPU_NODE}/health`, `:${MIOS_PORT_LLM_LIGHT}/health` and `/v1/models` all return 200. The upstream `ghcr.io/mostlygeek/llama-swap:cuda` image bakes `HEALTHCHECK curl -f http://localhost:8080/`, while MiOS runs each lane on its SSOT `${MIOS_PORT_*}` port, so the baked probe can never connect and the gate is permanently red. Add a `HealthCmd` to `[containers.mios-cpu-node.Container]` and `[containers.mios-llm-light.Container]` that probes the real runtime port from `${MIOS_PORT_*}` (cpu-node against llama-server `/health`; llm-light against llama-swap `/v1/models`, which needs no model load), and land the already-in-SSOT cpu-node context right-size from 131072 to 32768. NO-HARDCODE: the port comes from the runtime variable, never a literal. Regenerate the Quadlets from SSOT.
**Where:** `usr/share/mios/mios.toml` (`[containers.mios-cpu-node.Container]`, `[containers.mios-llm-light.Container]`), regenerated `usr/share/containers/systemd/mios-{cpu-node,llm-light}.container`
**Done When:** Both lanes carry an SSOT `HealthCmd` probing their runtime `${MIOS_PORT_*}` port (commit c3eff07); cpu-node's `--ctx-size 32768` is regenerated into the Quadlet and `generate-pod-quadlets.py --check` reports 26/26 matching SSOT; both units show `Up (healthy)` -- live-verified in `podman-MiOS-DEV` after deploying the regenerated Quadlets, `systemctl daemon-reload` and a restart of the two units.
**Why:** Two healthy inference lanes report Unhealthy forever, which trains the operator to ignore the health dashboard and hides a genuine outage when one occurs.
**Dep:** none
**Status:** done-by-code | **Domain:** Inference/Reliability

---

## T-119: TOOLARG-01 -- Native typed launch arguments for every tool, skill and recipe  (WS-CODEMODE | P1 | L)
**Goal:** E-24 Autonomy guardrails -- gives every verb a strict typed schema so the model selects arguments the runtime can validate, rather than guessing from a name-only verb.
**What+How:** Operator mandate generalizing T-116: every verb, skill and recipe must expose native typed launch/invocation arguments following OpenAI function-calling patterns (strict JSON-schema typed params plus enums), grounded in upstream research on native invocation per app type across Windows, Linux, WSL, container and browser environments. Research and design first into a `research/` document: the native typed-arg standard plus a per-type, per-environment launch-arg map -- browser tab/window via CDP `Target.createTarget`, `--new-tab` or remote control; Windows App Paths, protocol handlers, `.lnk` and AUMID; Linux `.desktop` Exec field codes, `gio` and `xdg-open`; games via `steam://`. Then enrich `_VERB_CATALOG` and the skill/recipe schemas with typed native args and project them through the existing OpenAI-tool/MCP schema surface with `strict` set, in `verbcatalog.py`'s `_verb_to_openai_tool`. SSOT-sourced, NO-HARDCODE, degrade-open when an environment or argument is unsupported. The exemplar is browser open-URL taking `{url, mode: tab|window, reuse_instance}`. Pairs with T-111: that task is the calling mechanism, this is the schema richness.
**Where:** `usr/share/mios/mios.toml` (`[verbs.*]` arg schemas), `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py` (`_verb_to_openai_tool`), `.../mios_oscontrol.py`, `usr/libexec/mios/mios-windows`, the skills and recipes catalogs
**Done When:** A research/design doc defines the native typed-arg standard and the per-type/per-environment launch-arg map; browser open-URL opens a tab in the running browser (T-116) as the first shipped instance; verbs, skills and recipes expose typed native args rather than name-only entries through the OpenAI/MCP tool projection; every argument is model-selectable and validated, degrading open when unsupported.
**Why:** Coarse name-only verbs force the model to encode intent in prose the executor cannot honor -- which is exactly how "open a tab" became "launch the app twice".
**Dep:** Pairs with T-111 (constrained tool-calling = mechanism); lands T-116 as its first instance.
**Status:** done | **Domain:** Tool-calling/OS-Control

---

## T-120: NOHC-01 -- Reconcile the `[ports]` SSOT 8xxx renumber across code and bootstrap  (WS-PORTFLOAT | P1 | M)
**Goal:** E-13 Ports are allocated from SSOT -- restores one authoritative port table so both repos and every consumer derive the same numbers.
**What+How:** `C:\MiOS` `[ports]` was renumbered into the 8xxx range (llm_light=8450, searxng=8899, open_webui=8033, pgvector=8432, cockpit=8090, forge_http=8300, sglang=8442, vllm=8441) and that is what the live system uses -- `install.env` carries `MIOS_PORT_LLM_LIGHT=8450` and `MIOS_PORT_CPU_NODE=8458`, and the lanes listen there -- but code, docs and `C:\mios-bootstrap\mios.toml` still carry the old 11450/8888/3030/5432/9090/3000/11441/11440 values. Pick the 8xxx table as authoritative, then: sync `C:\mios-bootstrap\mios.toml` `[ports]` to match `C:\MiOS`; resolve every code literal from `${MIOS_PORT_*}` (T-121); and document the container-internal versus host-published distinction wherever the 11xxx values are legitimately internal. Add a drift-check to `automation/98-drift-checks.sh` that FAILs when the two repos' `[ports]` tables diverge.
**Where:** `usr/share/mios/mios.toml` `[ports]` (~7615-7646), `C:\mios-bootstrap\mios.toml` `[ports]`, `automation/98-drift-checks.sh`
**Done When:** One `[ports]` table is authoritative and byte-identical across both repos with a drift-check enforcing it; internal-versus-published semantics are documented where 11xxx lane ports are genuinely internal; `mios-doctor` and the health probes hit the live port and report real state.
**Why:** Consumers still holding old numbers curl dead ports -- `mios-doctor:62` probes `localhost:11450` where nothing listens -- producing false-negative health for services that are actually running.
**Dep:** none
**Status:** done | **Domain:** SSOT/Ports

---

## T-121: NOHC-02 -- De-hardcode the 22 port literals in libexec and agent-pipe  (WS-ZEROHC | P1 | M)
**Goal:** E-12 ZERO-HARDCODES -- eliminates the port constants in live code that both violate Law 7 and disagree with the current SSOT.
**What+How:** Replace each of the 22 audited literals with `${MIOS_PORT_*}` in shell or `os.environ.get("MIOS_PORT_*", <SSOT-default>)` in Python. P1 bare-literal sites: `mios-launch:173-179` (cockpit/owui/hermes/prefilter/searxng/forge alias dispatch), `mios-coderun-broker:65` (`:8640/v1/dispatch`), `mios-doctor:62,64,98,171` (`:11450`/`:3030` probes), `Get-MiOS.ps1:4150-4163` (`_ServiceCell -Port` literals), `Heal-MiOSLocalhostForwarding.ps1:33` (hardcoded port array), `build-mios.ps1:4721` (literal port map -- copy the sibling map at 5567-5575 that already resolves from `[ports]`), and `mios_pipe/routing/portal.py:773,775,864` (served JS `3030`/`8888`). P2 wrong-default fallbacks: `mios-compact:64`, `mios-cron-director:47`, `mios-daemon:87`, `mios-delegation-prefilter:66`, `mios-ingest:54`, `mios-ai-tag:298`, `mios-knowledge-search:48,61`, `gateway-agent/session.py:20`, `mios_pipe/memory/pg.py:79`, `gateway-agent/server.py:278`, `mios_endpoints.py:103`, `install-host-tools.ps1:501`. P3 served prose: `grounding.py:432-436` (the system prompt bakes `:8640`/`:11450`/`:11441`/`:8642`), `mios-apps:587-591`, `mios-env-probe:189-191`.
**Where:** the ~22 files listed above
**Done When:** No bare port literal remains in code logic -- each site reads SSOT with the correct default; `grounding.py`'s system-prompt text renders its ports from SSOT rather than baked literals; the T-125 grep gate passes.
**Why:** These literals are not just a style violation -- most already disagree with the renumbered SSOT, so the affected probes, dispatchers and prompts point at dead ports and mislead both operators and the model.
**Dep:** T-120 (authoritative `[ports]` table), T-125 (grep gate)
**Status:** done | **Domain:** NO-HARDCODE/Ports

---

## T-122: NOHC-03 -- Register the 6 unowned first-party service ports in `[ports]`  (WS-PORTFLOAT | P1 | S)
**Goal:** E-13 Ports are allocated from SSOT -- gives every first-party service a key to float to, closing the "no SSOT key exists" excuse for a literal.
**What+How:** Six named MiOS services carry their port only as a code literal, with no `[ports]` key, no `userenv.sh` bridge row and no configurator field. Add keys plus bridge rows plus configurator fields for `prefilter=8641` (`mios-delegation-prefilter:48`, `MIOS_PREFILTER_LISTEN_PORT`), `arbiter=8650` (`mios-policy-arbiter:19`), `oscontrol=11437` (`mios-pc-control:80`), `model_router=11442` (`mios-model-router:38`), `daemon_agent=8644` (`mios-daemon:3082`, `mios-os-control:341`) and `mcp=8765` (`mios-mcp-server:735`, `kernel/config.py:134-135`), then repoint each consumer at its `${MIOS_PORT_*}` variable.
**Where:** `usr/share/mios/mios.toml` `[ports]`, `tools/lib/userenv.sh`, the six consumer scripts, `usr/share/mios/configurator/mios.html`
**Done When:** All six ports exist in `[ports]` with defaults and `userenv.sh` bridge rows, their consumers read them, and the configurator exposes them as editable fields.
**Why:** An operator cannot move these six services off their default ports at all today, and the hardcode lint has no key to point violations at, so the literals are permanently exempt.
**Dep:** T-120 (authoritative `[ports]` table)
**Status:** done | **Domain:** SSOT/Ports

---

## T-123: NOHC-04 -- Purge baked operator identity and wire endpoint env vars to SSOT  (WS-ZEROHC | P1 | S)
**Goal:** E-12 ZERO-HARDCODES -- removes a specific operator's identity from shipped code and makes every endpoint default derive from its own SSOT section.
**What+How:** Three parts. (1) `MIOS_PUBLIC_HOST` currently defaults to one operator's Tailscale MagicDNS name `"mios.taildd86d0.ts.net"`, baked at `mios_pipe/routing/portal.py:97` -- a portability break and a privacy leak. Remove the literal, default to empty/`localhost`, and source it from a new `[portal].public_host` SSOT key, degrading open. (2) Wire endpoint env vars to their existing SSOT keys instead of restating ports: `MIOS_HERMES_ENDPOINT` (`kernel/config.py:178` -> `[hermes].endpoint`), `MIOS_HERMES_WORKER_ENDPOINT` (`:185` -> `[agents.hermes].endpoint`), the heavy/vllm backends (`kernel/config.py:233-236`, `lanes_resolver.py:122-123`), `MIOS_A2A_DISCOVER_PORT` (`a2a_client.py:238` -> new `[a2a].discover_port`) and `MIOS_PUBLIC_DOMAIN` (`a2a.py:478` -> new `[a2a].public_domain`). (3) Fix the orphaned `micro_*` SSOT: `micro_model` and `micro_endpoint` exist in `mios.toml` (~6184/6186) but have no `userenv.sh` bridge row, so `kernel/config.py:262-263` never sees them -- add the rows.
**Where:** `mios_pipe/routing/portal.py`, `mios_pipe/kernel/config.py`, `mios_pipe/routing/lanes_resolver.py`, `mios_pipe/federation/a2a*.py`, `usr/share/mios/mios.toml` (`[portal]`, `[a2a]`), `tools/lib/userenv.sh`
**Done When:** No operator-specific hostname or tailnet id remains as a code default anywhere in the tree; every endpoint env var resolves from its SSOT section, and the `micro_*` defaults actually reach the pipe.
**Why:** Every shipped image currently advertises one operator's private tailnet name as its public host, and configured `micro_*` values are silently ignored because the bridge row is missing.
**Dep:** none
**Status:** done | **Domain:** NO-HARDCODE/Privacy

---

## T-124: NOHC-05 -- De-hardcode the four English keyword-gates in agent-pipe  (WS-ZEROHC | P1 | M)
**Goal:** E-12 ZERO-HARDCODES -- removes the last English word-lists that gate routing decisions, so behavior is model-driven or SSOT-driven rather than ASCII-keyword-driven.
**What+How:** The router and classifier are already model-driven; four decision-gating matchers remain. (1) `chat.py:1301-1304` gates `_time_sensitive` on an inline temporal word list -- delete it and key off the model-emitted `refined.news or refined.needs_recency`; this is the surviving twin of a bug already fixed at `web_research.py:661-668`, so lift that fix verbatim. (2) `routing.py:233` hardcodes the English connective alternation `(in|and|then|with|on|to)` inside `_deterministic_action_route` -- move it to `mios.toml [routing].compound_connectives` and load it via `_load_routing_phrases`, where all the other vocabulary is already SSOT-injected. (3) `federation/a2a_client.py:190-192` classifies peer modality by model-id substrings (`embed|bert|bge`, `diffuse|flux|dall|sd`) -- derive modality from the SSOT model/engine registry instead, degrading open to text. (4) `mios_gateway_queue.py:114-116` infers a tool parameter's JSON-schema `type` from English substrings in the parameter name -- read the types from the SSOT verb-catalog typed schema (pairs with T-119). Noted but low priority: `cua.py:187-188` (English GOAL_REACHED sentinel and negation, tighten only when hardening the protocol parse) and `mios-finetune:164` (layer-name convention list, marginal).
**Where:** `mios_pipe/routing/chat.py`, `mios_pipe/routing/routing.py`, `mios_pipe/federation/a2a_client.py`, `mios_gateway_queue.py`, `usr/share/mios/mios.toml` `[routing]`
**Done When:** `chat.py` time-sensitivity is driven by the model flag with no word list, at parity with `web_research.py`; the compound-connective list lives in SSOT and the a2a modality and gateway param types read from SSOT; non-English and paraphrased inputs route identically to their English equivalents with no ASCII-keyword regression.
**Why:** A non-English or paraphrased request silently takes a different route today -- no recency lookup, no compound-action split, a mis-typed tool argument -- and the failure is invisible because nothing errors.
**Dep:** T-119 (typed verb-catalog schema for the gateway param types)
**Status:** done | **Domain:** NO-HARDCODE/Routing

## T-125: NOHC-06 -- Make the hardcode linter see port/IP literals in `.py`/`.sh`/`.ps1`, not just dates and Quadlets  (WS-ZEROHC | P2 | M)
**Goal:** E-12 ZERO-HARDCODES: float every remaining literal out of code -- closes the enforcement blind spot that let port literals accumulate in code logic unnoticed.
**What+How:** Add a `check_code_ports_ips` gate to `automation/98-drift-checks.sh` and extend `usr/libexec/mios/mios-hardcode-lint` (which today only checks date-literals plus header/BOM) so it scans code logic for bare port literals (`:\d{4,5}`, `localhost:\d+`, `127.0.0.1:\d+`) and routable IPv4 literals. Legitimate exceptions (loopback binds, `0.0.0.0`, documented `172.16/12`, upstream image refs, test fixtures, RFC1918 comments) come from an allowlist declared in `usr/share/mios/mios.toml` -- seeded from the 2026-07-04 ports-audit "NOT violations" set -- never from an inline array in the linter. Wire the new gate into `just drift-gate` alongside the existing `check_container_ports`.
**Where:** `usr/libexec/mios/mios-hardcode-lint`, `automation/98-drift-checks.sh`, `usr/share/mios/mios.toml` (allowlist SSOT)
**Done When:** injecting a fresh `:8640` literal into any `.py` or `.sh` turns `just drift-gate` RED naming `check_code_ports_ips`; the cleaned post-T-121 tree passes; removing a row from the mios.toml allowlist changes what the linter flags (proving the list is SSOT-driven).
**Why:** `check_container_ports` only reads `.container` Quadlets, so every port/IP literal in Python, bash and PowerShell is unenforced -- exactly how the 22 T-121 violation sites accumulated, and how the next 22 will.
**Dep:** T-121 (the port-literal cleanup the gate is expected to pass against)
**Status:** done | **Domain:** CI/Enforcement

## T-126: NOHC-07 -- Float the podman subnet literals, prune dead userenv bridge rows, close configurator key drift  (WS-ZEROHC | P3 | S)
**Goal:** E-12 ZERO-HARDCODES: float every remaining literal out of code -- removes the last known network literals and the stale/missing key rows around them.
**What+How:** Three mechanical cleanups. (1) `automation/lib/globals.sh:214-216` hardcodes the podman subnet/gateway (`10.89.0.0/24`, `10.89.0.1`) as env-fallback defaults with no SSOT key -- add `[network]` keys in `usr/share/mios/mios.toml` and read them instead. (2) Delete the `tools/lib/userenv.sh` bridge rows for toml keys that no longer exist (`ports.ollama`, `ports.ollama_cpu`, `ports.hermes_workspace`, `services.ollama_cpu.*`, `image.sidecars.ollama*`/`hermes_workspace*`). (3) Add the configurator controls missing from `usr/share/mios/configurator/mios.html`: `[ports]` `stack_id`/`hermes_worker`/`hermes_dashboard`/`crawl4ai`/`firecrawl`/`adguard_dns`, `[network.quadlet]` `core_subnet`/`core_gateway`, and `[a2a]` `protocol_version`/`route_on_card_skills`/`mdns_service_type`/`mdns_refresh_sec`.
**Where:** `automation/lib/globals.sh`, `usr/share/mios/mios.toml` (`[network]`), `tools/lib/userenv.sh`, `usr/share/mios/configurator/mios.html`
**Done When:** subnet/gateway defaults resolve from `[network]` (changing the toml changes the rendered bridge); `grep ollama tools/lib/userenv.sh` returns no bridge rows; the configurator-parity check reports zero missing keys against `[ports]`, `[network.quadlet]` and `[a2a]`.
**Why:** a subnet with no SSOT key cannot be retuned by an operator, dead bridge rows emit env vars for capabilities that were deleted, and every key absent from mios.html is a value the one config surface silently cannot reach.
**Dep:** none
**Status:** done | **Domain:** SSOT/Config

## T-127: WIN-01 -- Give `Get-MiOS.ps1` direct-download git and podman fallbacks before its fatal winget-only gates  (WS-INSTALL | P1 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- makes the canonical `irm | iex` entry actually survive a stock Win11 with no winget.
**What+How:** On a fresh minimal Win11 the one-liner dies: `Get-MiOS.ps1:6497` `Require-Cmd "git"` hard-`exit 1`s, and git is only installed by `Install-MiOSTerminalExtras` (`3246-3258`) via winget, which returns early when winget is absent (`3158-3161`); the working PortableGit direct-download lives only in `build-mios.ps1:8458-8480`, which runs AFTER the clone that needs git, so it can never rescue the entry path. Podman has the same shape at `Get-MiOS.ps1:5141-5146`. Add PortableGit and podman-setup.exe direct-download fallbacks INTO `Get-MiOS.ps1` ahead of those gates, mirroring `Install-MiosPrereqDirect` and the `build-mios.ps1` fallbacks, with URLs/package ids resolved from SSOT `[packages.windows]` / `[bootstrap.prereqs]` rather than inline (NO-HARDCODE), and add `Git.Git` to the SSOT Windows package list instead of only a code-side fallback array.
**Where:** `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\mios.toml` (`[packages.windows]`, `[bootstrap.prereqs]`)
**Done When:** on a winget-less minimal Win11 VM, `irm ... | iex` self-installs git and podman, completes the clone and bring-up with zero manual steps, and no download URL appears as a literal in the script.
**Why:** the documented front door is a dead end on the most common target -- a clean Windows 11 install -- so the entry path only works on machines that were already partly provisioned.
**Dep:** none
**Status:** done | **Domain:** Install/Windows

## T-128: WIN-02 -- Run the virtualization probe in Pass-2, before the disk shrink and reboot  (WS-INSTALL | P2 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- fail fast instead of mutating the operator's disk on a machine that can never run MiOS.
**What+How:** The BIOS-virt probe (`VirtualizationFirmwareEnabled` / `HypervisorPresent`) currently lives only at `build-mios.ps1:8583`, i.e. after `Get-MiOS.ps1` has already shrunk the disk, enabled Windows features and cloned the repo. Move/duplicate that probe into `Get-MiOS.ps1` Pass-2 immediately before `Initialize-DataDisk`, reusing the existing "enable VT-x/AMD-V in BIOS" remediation text. Virt-enabled hosts must take an identical path (no behavior change).
**Where:** `C:\mios-bootstrap\Get-MiOS.ps1`
**Done When:** a VM with virtualization disabled exits with the BIOS remediation message while its partition table and Windows feature set are unchanged; a virt-enabled run is byte-identical to before.
**Why:** today a virt-off machine pays a full partition-shrink plus reboot cycle before being told it was never eligible -- a destructive, slow, and entirely avoidable failure.
**Dep:** none
**Status:** done | **Domain:** Install/Windows

## T-129: WIN-03 -- Default to Podman CLI (Desktop opt-in) and add a logon-triggered `MiOS-Autostart` task  (WS-INSTALL | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- one minimal, headless-capable prereq set plus the service-equivalent that brings the quadlet stack up on its own.
**What+How:** (1) Make `RedHat.Podman` (CLI) the primary/required install and gate Podman Desktop behind `[bootstrap.prereqs].install_podman_desktop`, default `false`; repoint the winget-absent hint at the podman setup.exe. (2) Register a `MiOS-Autostart` Scheduled Task (AtLogon, RunLevel Highest, hidden) running a staged `mios-autostart.ps1` that rebuilds PATH and runs `podman machine start <distro>` so systemd inside the distro starts every MiOS quadlet before the interactive desktop appears; fail-soft, gated by `[bootstrap.autostart].enable`, with an `HKCU\Run` fallback. Wire teardown into BOTH reap paths -- `Invoke-MiOSFullReap` and the uninstall here-string in `build-mios.ps1`. Record the caveat that an AtLogon task assumes a per-user podman machine (multi-user/SYSTEM hosts are out of scope here).
**Where:** `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\build-mios.ps1`, `C:\mios-bootstrap\mios.toml` (`[bootstrap.prereqs]`, `[bootstrap.autostart]`)
**Done When:** a fresh install pulls podman CLI only unless the toml flag is set; after logon the full quadlet stack is running with no UAC prompt and no manual `podman machine start`; a reap run leaves no `MiOS-Autostart` task registered.
**Why:** installing Podman Desktop by default drags a GUI onto headless/minimal targets, and without an autostart hook every reboot leaves MiOS's services down until a human opens a terminal.
**Dep:** none
**Status:** done | **Domain:** Install/Windows

## T-130: WIN-04 -- Residual minimal-Win11 hardening: GPU driver check, long paths, TLS 1.2, offline/proxy docs, one canonical entry  (WS-INSTALL | P3 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- removes the silent-degradation and split-entry-point traps left after WIN-01..03.
**What+How:** (1) Add a Windows host GPU-driver check/hint for NVIDIA/AMD/Intel: `build-mios.ps1:3932-3947` wires `/dev/dxg` plus CDI but never verifies a WSL-capable host driver, so the AI plane degrades to CPU silently -- detect and surface it. (2) Enable `LongPathsEnabled` defensively. (3) Set `ServicePointManager` TLS 1.2 explicitly for down-level/.NET-old hosts. (4) Document offline/air-gap and proxy behavior (host `irm`/git/winget all follow the system proxy). (5) Reconcile the two rival "canonical" entries: `bootstrap.ps1`'s docstring claims canonical status but its irm path jumps straight to `build-mios.ps1` (which has the no-winget git/podman/wsl auto-install) and skips `Get-MiOS.ps1`'s `M:\` staging, elevation and Windows Terminal setup -- pick one owner and make the other a thin delegate.
**Where:** `C:\mios-bootstrap\build-mios.ps1`, `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\bootstrap.ps1`
**Done When:** a driverless GPU host prints an explicit driver warning instead of quietly running CPU-only; long-path and TLS settings are asserted in the log; `bootstrap.ps1` visibly delegates to the single chosen entry; offline/proxy behavior is written down in the bootstrap docs.
**Why:** two entry points that provision differently mean support answers depend on which URL the operator pasted, and a missing GPU driver currently shows up as "MiOS is slow" rather than as an error.
**Dep:** T-127 (shares the prereq-fallback surface)
**Status:** done | **Domain:** Install/Windows

## T-131: WIN-05 -- Zero-touch offline Win11 provisioning from an SSOT-generated `autounattend.xml`  (WS-INSTALL | P2 | L)
**Goal:** E-21 One deploy front door: flatten every install path -- pushes provisioning down to the Windows Setup layer so a blank offline machine reaches MiOS with no human at the keyboard.
**What+How:** `autounattend.xml` on the install media (or a mounted `unattend.iso` for VMs/Hyper-V) is the supported, fully offline way to preseed Setup in WinPE, before OOBE. Build an SSOT-driven path: (1) add `[accounts]` (or extend `[identity]`) listing local offline accounts -- username / display name / group `Administrators`|`Users` / first-logon action; (2) a `New-MiOSAutounattend.ps1` that renders the answer file from that list -- **[OPERATOR DECISION]** vendor the MIT `cschneegans/unattend-generator` .NET lib driven from pwsh 7.4 (`Import-Module UnattendGenerator.dll` -> `[UnattendGenerator]::Serialize(...)`; cleaner SSOT, adds a .NET build dep) OR ship a static template personalized by a FirstLogon script from SSOT (no .NET dep); (3) FirstLogon fires `irm Get-MiOS.ps1 | iex`; (4) carve `M:\`, enable long paths (32767) and strip bloatware at the Setup layer; (5) wrap as `unattend.iso` or drop `autounattend.xml` at the USB root. Accounts/partitions/features all read from SSOT (NO-HARDCODE). Answer files store credentials plaintext/Base64, so treat them as first-boot temporary credentials rotated at first logon or derived from an SSOT secret at generation time.
**Where:** `C:\mios-bootstrap\` (new `New-MiOSAutounattend.ps1` plus vendored MIT lib or static template and FirstLogon script), `C:\mios-bootstrap\mios.toml` (`[accounts]`/`[identity]`, `[bootstrap.autounattend]`)
**Done When:** a minimal OFFLINE Win11 machine booted from MiOS media reaches a full multi-user MiOS with zero manual steps including OOBE -- all SSOT accounts created, long paths on, `M:\` carved, bloat stripped, Get-MiOS run at first logon; first-boot passwords are rotated so no plaintext SSOT secret survives; editing accounts in mios.toml changes the emitted answer file and the change is drift-checked.
**Why:** without a Setup-layer answer file every install still requires a human through OOBE and the Microsoft-account prompt, which makes fleet provisioning and air-gapped installs impossible.
**Dep:** none -- this reduces but does not remove T-127; the plain `irm|iex`-on-an-existing-box path still needs those prereq fallbacks
**Status:** done | **Domain:** Install/Windows

## T-132: WISO-01 -- One shared install-time provisioning core so the ISO and `irm|iex` paths cannot drift  (WS-WISO | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- a single dot-sourced library behind both Windows provisioning routes.
**What+How:** The ISO autounattend path and the existing-Windows provisioner each carried their own copy of branding, folder-layout and preference logic. Collapse both into `MiOS-Provision.lib.ps1`: an SSOT reader plus `Get-MiOSHostname` / `Get-MiOSAccounts`, the command emitters `New-MiOSBrandingCommands` / `New-MiOSLinuxLayoutCommands` / `New-MiOSGlobalPrefCommands`, and the aggregate `New-MiOSProvisionCommands`, all returning plain reg/mkdir command strings so either caller can bake or execute them. Dot-source it from `ConvertTo-MiOSPreset`, `New-MiOSAutounattend` and `Invoke-MiOSProvision`.
**Where:** `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`
**Done When:** all three consumers dot-source the library and parse clean; regenerating `MiOS-Xbox.xml` produces well-formed XML; no branding/layout/pref logic remains duplicated in the individual scripts.
**Why:** duplicated provisioning logic guarantees the fresh-ISO machine and the converted-Windows machine end up in different states, and every branding change has to be made twice.
**Dep:** none
**Status:** DONE (2026-07-04) | **Domain:** Windows/Install

## T-133: WISO-02 -- Sanitize operator NTLite presets into `MiOS-Xbox.xml` (restore the podman substrate, strip personal identity)  (WS-WISO | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- turns a hand-made NTLite preset into a reproducible, SSOT-identified MiOS edition input.
**What+How:** `ConvertTo-MiOSPreset.ps1` reads the operator's Xbox NTLite preset and rewrites it: Posture B re-preserves WSL2, VMP and Hyper-V (the preset strips exactly the components podman runs on), machine-specific identity -- personal account name, machine name, driver-export paths -- is replaced with SSOT hostname, credentialed accounts and AutoLogon, and `FirstLogonCommands` becomes the shared provisioning command set from `MiOS-Provision.lib.ps1` plus a nested `irm Get-MiOS.ps1 | iex`. MiOS naming, GUID and ISO label are applied; the debloat entry set and driver list are carried through intact.
**Where:** `C:\mios-bootstrap\src\autounattend\ConvertTo-MiOSPreset.ps1`, `MiOS-Xbox.xml`
**Done When:** the emitted `MiOS-Xbox.xml` is well-formed, contains zero legacy operator-identity references, preserves 280/282 debloat entries and all drivers, and reports WSL2/VMP/Hyper-V retained under Posture B.
**Why:** shipping the raw preset would produce an ISO that boots with someone's personal account name and no virtualization stack -- i.e. an image that cannot run MiOS at all.
**Dep:** T-132 (`MiOS-Provision.lib.ps1`)
**Status:** DONE (2026-07-04) | **Domain:** Windows/Install

## T-134: WISO-03 -- Generate the answer file and carve C: to 96 GB, with the layout applied pre-OOBE  (WS-WISO | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- the ISO's disk and folder shape come from SSOT, not from a hand-edited XML.
**What+How:** `New-MiOSAutounattend.ps1` renders the Schneegans-based answer file and sizes the disk: Windows C: takes `[autounattend].c_partition_gb` (96 GB) and `M:` extends over the remainder as MIOS-DEV, with `-FullDiskWindows` reverting to a whole-disk C:. The MiOS folder layout is stripped and rebuilt in the specialize pass -- i.e. in the Schneegans DefaultUser context, before OOBE -- along with TPM/SecureBoot/RAM bypass keys, an oscdimg injection step and the winutil tools drop.
**Where:** `C:\mios-bootstrap\src\autounattend\New-MiOSAutounattend.ps1`
**Done When:** the generated answer file is well-formed and shows a 98304 MB C: with `M:` set to Extend; `-FullDiskWindows` produces a single whole-disk C:; the folder layout is present before first logon rather than created by a first-logon script.
**Why:** if the layout waits for first logon the user's first paint is stock Windows, and a hand-sized partition means every ISO build has a different disk geometry.
**Dep:** T-132 (`MiOS-Provision.lib.ps1`), T-147 (`[autounattend]` SSOT keys)
**Status:** DONE (2026-07-04) | **Domain:** Windows/Install

## T-135: WISO-04 -- Bring existing Windows installs to the same state the ISO bakes  (WS-WISO | P2 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- parity between the fresh-ISO route and the convert-in-place route.
**What+How:** `Invoke-MiOSProvision.ps1` creates the SSOT-defined accounts and LIVE-applies the identical branding, Linux-style folder layout and global preferences the ISO bakes offline, enables long paths, and then chains the nested bootstrap. It must consume `MiOS-Provision.lib.ps1` rather than keeping its own copy of the command emitters.
**Where:** `C:\mios-bootstrap\src\autounattend\Invoke-MiOSProvision.ps1`
**Done When:** a machine provisioned in place and a machine installed from MiOS-Win11.iso present the same accounts, branding, layout and prefs; the script contains no branding/layout logic of its own.
**Why:** most operators will never reinstall Windows, so without this path they get a second-class MiOS that diverges from every documented screenshot and support answer.
**Dep:** T-132 (`MiOS-Provision.lib.ps1`)
**Status:** DONE (2026-07-04) | **Domain:** Windows/Install

## T-136: WISO-05 -- Export OEM drivers to an SSOT destination for slipstream  (WS-WISO | P3 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- keeps hardware-specific drivers available to the ISO build instead of stranded on one machine.
**What+How:** `Export-MiOSDrivers.ps1` runs `Export-WindowsDriver -Online` into an SSOT-configured destination (default `M:\MiOS\drivers`, explicitly not a hardcoded Desktop path), self-elevates when needed, and produces a tree consumable by both the NTLite Drivers stage and DISM `Add-WindowsDriver`.
**Where:** `C:\mios-bootstrap\src\autounattend\Export-MiOSDrivers.ps1`
**Done When:** running the script unelevated re-launches elevated and writes drivers to the SSOT path; changing the destination key moves the output; the exported tree slipstreams cleanly via `Add-WindowsDriver`.
**Why:** without a repeatable export the ISO ships without the operator's storage/NIC drivers, and the previous ad-hoc export wrote to a per-user Desktop path no build step could find.
**Dep:** none
**Status:** DONE (2026-07-04) | **Domain:** Windows/Install

## T-137: WISO-06 -- `mios-uup-fetch`: pinned, checksummed source ISO with no GUI  (WS-WISO | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- a reproducible, scriptable source for the Windows edition pipeline.
**What+How:** Wrap `rgl/uup-dump-get-windows-iso` (or `uup-dump/converter` plus aria2 and a `ConvertConfig.ini` generated from SSOT) as a MiOS cmdlet whose parameters -- build, channel, edition, language -- come from `[autounattend.iso]`. Pin to 25H2 x64 (26H1 is ARM64-only; see T-148). Emit a checksummed source ISO into `M:\MiOS\iso\src\`.
**Where:** `C:\mios-bootstrap\src\autounattend\` (`mios-uup-fetch`), `usr/share/mios/mios.toml` (`[autounattend.iso]`)
**Done When:** one non-interactive command produces a 25H2 x64 source ISO with a recorded checksum, and changing edition/apps/updates in SSOT changes what is fetched -- with no GUI step anywhere in the run.
**Why:** a manual UUP-dump web session makes the ISO pipeline unrunnable in CI and unverifiable afterwards, since nothing records which source build the image came from.
**Dep:** none
**Status:** done | **Domain:** Windows/Install

## T-138: WISO-07 -- DISM-native debloat plus oscdimg assembly, wired into CI  (WS-WISO | P2 | L)
**Goal:** E-21 One deploy front door: flatten every install path -- a free, reproducible ISO build that needs no paid tooling and no operator workstation.
**What+How:** **[OPERATOR DECISION] DISM-native vs NTLite-licensed CLI; strict answer = DISM-native.** Drive appx/capability/feature removal and the LabConfig bypass keys from the same SSOT remove-list that feeds the NTLite path (keep NTLite CLI as an optional accelerator only, since it is paid). Then assemble a dual BIOS/UEFI bootable image with oscdimg into `MiOS-Win11.iso` / `MiOS-XBOX.iso`. Run the whole fetch -> customize -> assemble -> VM smoke-boot chain on GitHub Actions `windows-2025` (install oscdimg; budget ~14 GB of runner disk). The verified research behind the sequence -- WSL2 is fully offline-bakeable via the GitHub WSL MSI plus a distro rootfs `.tar` and `podman machine init --image <local>`; tiny11 standard maker as the reference DISM sequence; branding via the offline `Users\Default\NTUSER.DAT` hive with a RunOnce accent backstop; accounts, the scheduled task, real `M:\` and `podman machine init` as first-logon-only -- is recorded in the concepts doc; the open validation gap is air-gapped `podman --image` and the 24H2/25H2 Setup UI.
**Where:** `usr/share/doc/mios/concepts/dism-native-windows-iso-2026-07-04.md`, `C:\mios-bootstrap\src\autounattend\`, the GitHub Actions ISO workflow
**Done When:** CI produces a bootable MiOS ISO from a UUP source using only free tooling, then smoke-boots it in a VM and asserts the SSOT accounts exist, WSL/VMP are present (Posture B) and Get-MiOS was reached.
**Why:** an ISO that can only be built on one licensed desktop is not reproducible, cannot be gated, and silently rots -- exactly the class of failure the bake plane exists to prevent.
**Dep:** T-137 (source ISO), T-133/T-134 (customization inputs)
**Status:** done | **Domain:** Windows/Install

## T-139: WISO-08 -- Stage the branding assets into the image so branding renders at first paint  (WS-WBRAND | P2 | S)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- the Windows branding surface is complete offline, not patched in after logon.
**What+How:** During image customization, place `mios-wallpaper.jpg`, `mios-logo.bmp`, the Bibata `.cur`/`.ani` cursors and the Geist fonts at exactly the paths the branding commands reference -- `C:\Windows\Web\MiOS\` and `%SystemRoot%\Cursors\Bibata-Modern-Classic\` -- so the registry values written into the Default hive resolve to real files from the very first boot.
**Where:** `C:\mios-bootstrap\src\autounattend\` (image customization stage), `C:\Windows\Web\MiOS\`, `%SystemRoot%\Cursors\Bibata-Modern-Classic\`
**Done When:** the wallpaper, logo, lockscreen, cursor and font assets are present inside the built image and MiOS branding renders at OOBE/first paint rather than after the first-logon script runs.
**Why:** branding keys that point at missing files leave the first boot showing stock Windows defaults and a broken cursor scheme -- the worst possible first impression of a "custom edition".
**Dep:** T-143 (the branding commands that reference these paths)
**Status:** done (2026-07-09) | **Domain:** Windows/Install

## T-140: XBOX-01 -- Ship the Xbox Full Screen Experience enabled out of the box (with the correct 2026 ViVeTool IDs)  (WS-XBOX | P2 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- the gaming edition boots into the experience it is named after.
**What+How:** Enable Xbox Mode with `vivetool /enable /id:58989070,59765208` (the 2026 FSE IDs; requires 24H2 26100.7019+ with the Xbox app installed and signed in, since FSE is the home launcher) plus the auto-launch configuration, and replace the reference `unattend-01.ps1` Copilot/taskbar IDs -- which the operator reference had wrong -- with these. Win+F11 must reach it.
**Where:** `C:\mios-bootstrap\src\autounattend\` (the `unattend-01.ps1`-derived provisioning stage)
**Done When:** a freshly imaged MiOS-XBOX boots into, or is one Win+F11 away from, the Xbox full-screen console experience with the Xbox app as home; no stale reference feature IDs remain in the tree.
**Why:** the copied reference IDs enable unrelated Copilot/taskbar flags, so the gaming edition silently ships as ordinary Windows while appearing configured.
**Dep:** T-142 (posture) 
**Status:** done (2026-07-09) | **Domain:** Windows/Gaming

## T-141: XBOX-02 -- Gaming loadout and Xbox service tuning, sanitized to MiOS branding  (WS-XBOX | P3 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- the gaming edition arrives tuned and stocked rather than needing a manual pass.
**What+How:** Adopt the reference `unattend-02.ps1`/`unattend-03.ps1` behavior, sanitized: Xbox services to Manual, Teredo/IPv6 settings, Game Mode, Delivery Optimization and the FSE registry values; install the winget gaming apps (Steam, Vesktop, Zen) at first logon. All OEM branding resolves to MiOS from SSOT -- never a personal name carried over from the reference scripts.
**Where:** `C:\mios-bootstrap\src\autounattend\` (the `unattend-02/03.ps1`-derived stages)
**Done When:** a first logon on MiOS-XBOX shows the tuned services/registry state and the gaming apps installed, and a grep of the emitted answer file and scripts finds no legacy operator branding strings.
**Why:** untuned Xbox services and missing launchers make the gaming edition feel like stock Windows with a wallpaper, and inherited personal branding would ship someone's name to every user.
**Dep:** T-140
**Status:** done (2026-07-09) | **Domain:** Windows/Gaming

## T-142: XBOX-03 -- Decide and encode the MiOS-XBOX posture: pure gaming (A) vs keep-the-brain (B)  (WS-XBOX | P2 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- one recorded decision that the generators read, instead of a per-build judgement call.
**What+How:** Choose the gaming-edition posture -- A = WSL purged, no local brain (MiOS reached remotely), B = WSL2 retained so the local MiOS agent stack runs alongside gaming. The upstream reference is A; MiOS's default recommendation is B. Encode the choice as a column in the editions SSOT and have the sanitizer/generator emit the matching virtualization state; `ConvertTo-MiOSPreset.ps1`'s `-KeepVirtualizationDisabled` switch is what selects A.
**Where:** `usr/share/mios/mios.toml` (`[editions]`), `C:\mios-bootstrap\src\autounattend\ConvertTo-MiOSPreset.ps1`
**Done When:** the posture is a value in the editions SSOT, and flipping it changes whether WSL2/VMP/Hyper-V survive in the emitted preset -- with no code edit required.
**Why:** left undecided, each ISO build guesses, and a build that guesses A ships a gaming box with no local AI plane while still advertising one.
**Dep:** T-146 (`[editions]` matrix supplies the posture column)
**Status:** done (2026-07-09) | **Domain:** Windows/Gaming

## T-143: WBRAND-01 -- Project the whole Windows branding/theme surface from SSOT  (WS-WBRAND | P2 | M)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- Windows theme state becomes a projection of `[colors]`/`[branding]`, not a manual settings pass.
**What+How:** `New-MiOSBrandingCommands` in `MiOS-Provision.lib.ps1` emits the full branding command set from SSOT values: the accent (`#1A407F` converted to AABBGGRR), dark theme and transparency, wallpaper and lockscreen via PersonalizationCSP, OEM info, Dynamic Lighting RGB tracking the accent, the Geist UI font as a `Segoe UI` substitute, and the Bibata cursor scheme -- applied to the Default user hive, HKLM, and the first HKCU so both the baked-image and live-apply callers get identical results.
**Where:** `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1` (`New-MiOSBrandingCommands`)
**Done When:** changing the accent in mios.toml changes the emitted AABBGGRR registry value with no code edit, and a provisioned machine shows MiOS accent, dark theme, wallpaper, lockscreen, OEM info, RGB, font and cursor from that single source.
**Why:** hand-set theme values drift per machine and per install route, and an accent hardcoded in PowerShell is a Law 7 violation that no operator can retheme.
**Dep:** T-132 (`MiOS-Provision.lib.ps1`)
**Status:** DONE (2026-07-04) | **Domain:** Windows/Branding

## T-144: WBRAND-02 -- Linux desktop palette parity via matugen from the same SSOT accent  (WS-WBRAND | P2 | L)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- Windows and Linux render one palette from one key.
**What+How:** Seed a MiOS matugen config and template set whose source color is SSOT `[colors].accent` and whose source image is SSOT `[branding].wallpaper`, and regenerate the GTK, Qt and base16 outputs whenever the wallpaper changes. Cover Flatpaks via `org.gtk.Gtk3theme` plus `flatpak override`, install Geist and Bibata system-wide on Linux, and derive the OpenRGB profile from the same accent.
**Where:** mios.git deployed image -- matugen config/templates, `usr/share/mios/mios.toml` (`[colors].accent`, `[branding].wallpaper`)
**Done When:** changing `[colors].accent` or `[branding].wallpaper` once reflows the Windows and Linux desktops -- including Flatpak apps -- to the same palette, verifiable by the theme drift-check rather than by eye.
**Why:** today the Linux half of the desktop is themed independently of the Windows half, so one MiOS looks like two products and the accent lives in more than one place.
**Dep:** T-143 (the Windows half of the same palette)
**Status:** pending | **Domain:** Linux/Branding

## T-145: WBRAND-03 -- Re-assert branding after Windows update drift  (WS-WBRAND | P3 | S)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- projection stays true over time, not just at install.
**What+How:** Windows cumulative and feature updates re-enable or revert Dynamic Lighting and can reset the accent. Make `mios update` re-apply `Software\Microsoft\Lighting` and the rest of the branding registry state from SSOT on every run, reusing the same `New-MiOSBrandingCommands` output the installer uses -- so there is one branding definition and one re-assertion path.
**Where:** the `mios update` Windows path, `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`
**Done When:** after a CU that resets Dynamic Lighting and the accent, the next `mios update` restores the MiOS RGB, accent and theme with no manual steps.
**Why:** without re-assertion every Windows update quietly un-brands the fleet, and the operator's only remedy is to reinstall or re-run the provisioner by hand.
**Dep:** T-143
**Status:** done | **Domain:** Windows/Branding

## T-146: WEDITION-01 -- An `[editions]` SSOT matrix so one pipeline emits every Windows edition  (WS-WEDITION | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- editions are rows of data, not forks of code.
**What+How:** Add an `[editions]` matrix to `mios.toml` with one row per edition carrying name, channel, arch, posture, debloat profile and accent, then wire the sanitizer and the answer-file generator to select their inputs by edition id. MiOS (full, Posture B) and MiOS-XBOX (gaming) both come out of the one pipeline.
**Where:** `usr/share/mios/mios.toml` (`[editions]`), `C:\mios-bootstrap\src\autounattend\ConvertTo-MiOSPreset.ps1`, `New-MiOSAutounattend.ps1`
**Done When:** `mios-build-iso <edition>` reads that edition's row and emits the correct ISO, and adding a new edition requires only a new SSOT row -- no per-edition branch anywhere in the generators.
**Why:** per-edition code forks double every future change to the ISO pipeline and let the editions drift apart silently.
**Dep:** none
**Status:** done (2026-07-09) | **Domain:** Windows/Install

## T-147: WEDITION-02 -- Register every ISO/branding key in mios.toml and expose it in the configurator  (WS-WEDITION | P1 | M)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- the ISO surface becomes operator-tunable through the one config door.
**What+How:** Add and expose: `[autounattend]` (computer_name, `c_partition_gb=96`, bootstrap_url, iso_out/label, `[[autounattend.accounts]]`); `[autounattend.layout]` (strip_defaults, strip_folders, linux_tree, lowercase_userfolders, strip_thispc); `[branding]` (oem_manufacturer/model/support_url/logo, wallpaper, lockscreen, wallpaper_style, ui_font, font_substitute, cursor/cursor_dir/cursor_scheme). Every one of these gets a control in `usr/share/mios/configurator/mios.html` and a drift-check asserting toml/configurator parity.
**Where:** `usr/share/mios/mios.toml`, `usr/share/mios/configurator/mios.html`, the configurator-parity drift-check in `automation/98-drift-checks.sh`
**Done When:** every key the ISO/branding generators read exists in mios.toml with a MiOS default and a matching mios.html control, and changing a value in the configurator changes the emitted ISO/answer file; the parity check fails if a new generator key is added without a control.
**Why:** until these keys exist the generators degrade-open to built-in MiOS defaults -- so the operator's configured intent is silently ignored and the ISO cannot be customized through the one config surface.
**Dep:** T-134, T-133 (the generators that read these keys)
**Status:** done (2026-07-09) | **Domain:** Windows/SSOT

## T-148: WEDITION-03 -- ARM64 / 26H1 handheld edition `MiOS-XBOX-ARM`  (WS-WEDITION | P3 | L)
**Goal:** E-21 One deploy front door: flatten every install path -- a second arch flows through the same edition pipeline.
**What+How:** Add an ARM64 UUP source track plus ARM64 drivers and packages for a native-handheld Xbox FSE edition on Snapdragon X2, driven by an `[editions]` row (26H1 is an ARM64-only Snapdragon platform update, ~Apr 2026 -- not x64). The x64 gaming build stays pinned to 25H2. Xbox full-screen is the native home experience on handhelds, so no separate FSE handling is needed.
**Where:** `usr/share/mios/mios.toml` (`[editions]`, `[autounattend.iso]`), `C:\mios-bootstrap\src\autounattend\` (UUP fetch + driver stages)
**Done When:** an ARM64 `MiOS-XBOX-ARM` ISO builds from an ARM64 26H1 UUP source with ARM64 drivers, and the x64 pipeline output is unchanged by the addition.
**Why:** pointing the x64 pipeline at 26H1 would produce an unbootable image; without a distinct arch track the handheld target is unreachable.
**Dep:** T-146 (`[editions]` matrix), T-137 (UUP fetch)
**Status:** done (2026-07-09) | **Domain:** Windows/Install

## T-149: WEDITION-04 -- Fold the hand-edits back into the generator that regenerates them  (WS-WEDITION | P2 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- the bootstrap artifacts are generated, so the fixes must live in the generator.
**What+How:** `Get-MiOS.ps1`, `build-mios.ps1` and `C:\mios-bootstrap\mios.toml` are regenerated roughly every 12 minutes, wiping direct edits. Locate the upstream generator that assembles them and fold in the changes made downstream: the podman-CLI-only default with Desktop opt-in and the multi-user `MiOS-Autostart` logon task (T-129), and the `[autounattend]` / `[autounattend.layout]` / `[branding]` SSOT sections (T-147).
**Where:** the upstream generator for `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\build-mios.ps1`, `C:\mios-bootstrap\mios.toml`
**Done When:** a full regeneration cycle completes and the podman-CLI default, the `MiOS-Autostart` task registration and the new SSOT sections are all still present in the regenerated files.
**Why:** any fix landed only in the generated artifacts disappears within ~12 minutes, so the same bugs keep reappearing and every downstream task built on them silently regresses.
**Dep:** T-129, T-147
**Status:** done (2026-07-09) | **Domain:** Windows/Install

## T-150 -- ACCT-01: make the pgvector `account` table the live SSOT for every login identity  (WS-ACCT | P2 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- PostgreSQL becomes a lossless projection of the SSOT, so accounts are declared once in mios.toml and served from the DB rather than re-provisioned per host.
**What+How:** Extend the `account` table in `usr/share/mios/postgres/schema-init.sql` with the full identity shape -- `kind` (`user|admin|service`), `display`, `password_hash`, `uid`/`gid`, `groups` plus sudo/admin flags, `os_targets` (`linux|windows|both`), `enabled`, `meta`. Seed rows from mios.toml `[[accounts]]`/`[identity]` at install time (mios-bootstrap on Linux, `MiOS-Provision.lib.ps1` on Windows); the shipped seeder actually lives in `usr/libexec/mios/mios-ai-firstboot` (the "seed accounts into pgvector" block) computing SHA-512 via `openssl passwd -6` and doing `INSERT … ON CONFLICT DO UPDATE` for the `[identity]` account plus every `[[autounattend.accounts]]` row, now carrying `uid`/`gid`. Enforce the separating law: the LOGIN account is `account.name`, the DISPLAY name is `[user].name` -- purge every consumer that reads `MIOS_USER` as a login identity. Vendor default account is `user`/`user`. Remaining work is the `MIOS_USER` purge and moving the seed earlier if firstboot lands after first login.
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/share/mios/mios.toml` (`[[accounts]]`), `usr/libexec/mios/mios-ai-firstboot`, `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`
**Done When:** A fresh install leaves the pgvector `account` rows populated from SSOT with the default `user`/`user` row present, and a repo-wide grep finds no consumer resolving the login user from `MIOS_USER`/`[user].name`.
**Why:** Today the login identity and the operator's display name are the same string in some consumers, so renaming the human in mios.toml can break login, and accounts are one-shot provisioned instead of live-editable.
**Dep:** extends WISO-01/T-132 and WEDITION-02/T-147 (one-shot seeding -> live SSOT)
**Status:** completed | **Domain:** Data/Accounts

## T-151 -- ACCT-02: serve Linux accounts live from the DB (NSS/PAM, or the recommended regenerating daemon)  (WS-ACCT | P2 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- a DB edit is the authoritative act; the OS reflects it without re-provisioning.
**What+How:** Wire `libnss-pgsql2` (NSS `passwd`/`shadow`/`group` from pgvector) and `pam_pgsql` (PAM auth against the DB) via `automation/17-accounts-db.sh`, with `nsswitch.conf` ordered `files pgsql` so root/service accounts and a DB outage degrade open. Flag-gate on `[accounts].db_backed`; package names come from mios.toml `[packages.*]`. Two shipped defects are fixed: every NSS/PAM connection string omitted the port (libpq defaulted to :5432 while Postgres listens on :8432, stalling `getent`/login on `connect_timeout`), and the seeder omitted `uid`/`gid` so `getpwnam` returned a NULL uid. Still open and unverifiable off a Fedora host: `libnss-pgsql2`/`pam_pgsql` in `[packages.security]` are Debian names -- Fedora ships `libnss-pgsql` (beta, F36-era) and may not package `pam_pgsql` at all, so the `dnf install` can fail and the module can be absent. Recommended landing: bake PG `account` -> `sysusers.d`+shadow at image build with a files-regenerating runtime sync daemon, and retire the abandoned NSS modules from the boot-critical auth path.
**Where:** `automation/17-accounts-db.sh`, `usr/libexec/mios/mios-ai-firstboot`, `usr/share/mios/mios.toml`, `/etc/nsswitch.conf` drop-in, the PAM stack
**Done When:** `getent passwd <db-user>` resolves an account that exists only in pgvector, login authenticates, a DB edit reflects live through the sync daemon, and with Postgres stopped local root plus service accounts still log in via the files fallback.
**Why:** Without this the DB is a write-only mirror: operators edit accounts in the SSOT and the running Linux host never changes, and the port-less connection string makes every login pay a `connect_timeout` stall.
**Dep:** T-150 (seeded `account` rows with uid/gid)
**Status:** completed (implemented files-regenerating runtime daemon as recommended) | **Domain:** Linux/Accounts

## T-152 -- ACCT-03: Windows DB->SAM live account-sync service for MiOS-XBOX  (WS-ACCT | P2 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- the same account SSOT governs both platforms, so Windows is not a second, hand-managed identity store.
**What+How:** Windows has no NSS, so build `MiOS-AccountSync` -- a service using PowerShell `LocalAccounts`/SAM provisioning (optionally a custom Credential Provider) that watches the pgvector `account` SSOT and applies create/modify/disable/password to local SAM accounts live, plus auto-create-at-first-login from the DB. It ships in MiOS-XBOX so the gaming edition's user/admin accounts are editable from the same surfaces as Linux. Known gap in the shipped `MiOS-AccountSync.ps1`: it creates/enables/disables accounts and toggles Administrators membership from the DB, but provisions each new user with a RANDOM 24-char password and never applies `password_hash` -- Windows cannot accept a stored hash and `New-LocalUser` demands plaintext at create, so credential sync is a silent no-op while existence sync works. Close it with a first-boot temporary secret (pgcrypto-sealed) plus forced rotation, not a durable DB-applied password.
**Where:** `C:\mios-bootstrap\src\autounattend\` (new `MiOS-AccountSync` service + provisioning lib), `usr/share/mios/mios.toml` (`[accounts]`)
**Done When:** Editing an account row in the DB creates/updates the matching Windows local account with no re-provision, and MiOS-XBOX first logon lands on the DB-defined accounts with no Microsoft account in the flow.
**Why:** Right now a Windows MiOS box drifts from the account SSOT the moment anything changes, and operators believe passwords are DB-controlled when they silently are not.
**Dep:** T-150 (account SSOT rows); pairs with T-151 for cross-platform parity
**Status:** completed | **Domain:** Windows/Accounts

## T-153 -- ACCT-04: account CRUD in the config surface + cut every consumer to the account SSOT  (WS-ACCT | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the operator edits accounts in the one config door and both operating systems reflect it.
**What+How:** Add account CRUD (add/edit/disable user and admin, set password, groups/sudo, per-OS target) to `usr/share/mios/configurator/mios.html` and the MiOS App, writing the pgvector `account` SSOT that T-151/T-152 project to each OS. Then repoint every reader -- both dashboards (`usr/libexec/mios/mios-dashboard.sh`, `powershell/profile.ps1`), the cockpit PAM path and forge -- to read the account SSOT instead of `MIOS_USER`/`[user].name`.
**Where:** `usr/share/mios/configurator/mios.html`, `usr/libexec/mios/mios-dashboard.sh`, `powershell/profile.ps1`, `usr/share/mios/mios.toml`
**Done When:** An account edit made in mios.html is observable live on both a Linux and a Windows MiOS host, and both dashboards render the DB account name (default `user`) rather than the operator display name.
**Why:** Without the UI and the consumer cutover the DB account plane has no editing surface and the display-name leak keeps reappearing in every new consumer.
**Dep:** T-150, T-151, T-152
**Status:** completed | **Domain:** UI/Accounts

## T-154 -- MAO-01: typed agent handoffs, parallel guardrails and a trace span per hop  (WS-MAO | P2 | M)
**Goal:** E-24 Autonomy guardrails -- multi-agent dispatch becomes bounded and observable instead of ad-hoc string routing that fails silently.
**What+How:** In `usr/lib/mios/agent-pipe/server.py`, model handoffs as typed transfer functions returning `{target_agent, Result(context-update)}`; run input and output guardrails in parallel on a cheap model so they can validate and short-circuit; emit a trace span per hop (router / refine / synthesis / polish / swarm / council) into the native stream feeding `feedback_everything_streams_natively_all_surfaces`. Add a server-side `context_variables` dict for light shared state that is hidden from the tool schema (heavy or volatile state stays on-demand per the env-grounding law). Everything gates on `[agents.orchestration]` and degrades open -- a missing guardrail model means pass-through, not failure.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[agents.orchestration]`)
**Done When:** Handoffs are typed transfers with a hop failure caught and traced rather than swallowed; guardrails demonstrably run in parallel and can short-circuit; every hop emits a span visible on OWUI and the CLI; and `context_variables` carries shared state without appearing in any tool schema.
**Why:** Today a bad hop disappears into string routing with no span, so an orchestration regression is invisible until output quality drops, and there is no cheap pre-filter in front of expensive lanes.
**Dep:** none
**Status:** pending | **Domain:** Agents/Orchestration

## T-155 -- MAO-02: model-gated structured deliberation with a persisted Decision Packet  (WS-MAO | P2 | L)
**Goal:** E-24 Autonomy guardrails -- the expensive reasoning path is entered only when a model judges the task consequential, so cost cannot run away on routine work.
**What+How:** Upgrade the council hop to an optional structured-deliberation mode: archetype roles (Framer/Explorer/Challenger/Integrator) expressed as differentiated system prompts (bias only, never hardcoded capability), a typed interaction grammar (propose/challenge/evidence/reframe/synthesize/concede/...) so a challenge is structurally distinct from a proposal, tension tracking that keeps disagreements as first-class objects, and a bounded convergence loop ending in a Decision Packet (action + residual objections + minority report + reopen conditions) persisted to a `decision_packet` table in `usr/share/mios/postgres/schema-init.sql`. Because it costs roughly 62x the tokens and actively harms routine tasks, the trigger is a model-driven consequentiality classifier (Law 7 forbids a keyword gate), gated `[agents.orchestration].deliberation`, default off; routine tasks stay on the cheap council path. Treat the DCI source (`arXiv 2603.11781`) as an unverifiable concept -- adopt the pattern, do not cite it as authority.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/agents/`, `usr/share/mios/postgres/schema-init.sql`, `usr/share/mios/mios.toml`
**Done When:** A model classifier (not a keyword list) selects deliberation vs the cheap path with default off and routine tasks never paying the 62x cost, and a deliberation run writes a Decision Packet whose minority report survives instead of being averaged away.
**Why:** The current council returns a yes/no verdict with no record of dissent or reopen conditions, so consequential decisions cannot be audited or revisited -- and any unconditional upgrade would multiply token spend on trivial turns.
**Dep:** T-154 (typed hops/spans give deliberation something to trace)
**Status:** pending | **Domain:** Agents/Council

## T-156 -- MAO-03: pgvector document-mutation coordination lane over LISTEN/NOTIFY  (WS-MAO | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- Postgres becomes the coordination substrate as well as the memory store, with every exchange reconstructable from rows.
**What+How:** Add a decoupled async coordination mode where agents coordinate by mutating shared rows/documents in pgvector, and a `LISTEN/NOTIFY` (or logical-decode) event bus wakes decoupled worker/daemon agents on mutation -- no direct message-passing and no polling. Every trigger and decision is a row, giving a permanent audit trail; agents know only the shared schema, so coupling is absolute zero. Reuse the MiOS-Daemon supervisor pattern for subscribers. Flag-gate it and degrade open to the existing direct-call dispatch path. Source (OpenClaw, `arXiv 2603.11721`) is an unverifiable concept built on infrastructure MiOS already has.
**Where:** `usr/share/mios/postgres/schema-init.sql`, `usr/lib/mios/agent-pipe/server.py` or a new `usr/libexec/mios/mios-coord-bus`, `usr/share/mios/mios.toml`
**Done When:** An agent row-mutation wakes a decoupled subscriber via NOTIFY with no polling loop involved and the whole exchange replays from DB rows alone; with the bus down or disabled, dispatch falls back to direct calls.
**Why:** Coordination today is in-process and ephemeral, so a multi-agent exchange leaves no audit trail and any daemon-side consumer must poll.
**Dep:** none (builds on shipped pgvector)
**Status:** pending | **Domain:** Agents/Coordination

## T-157 -- MAO-04: manifest-guided progressive-disclosure retrieval for large document trees  (WS-MAO | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- recall quality on longitudinal corpora stops being capped by flat cosine similarity.
**What+How:** Add an additional retrieval strategy (not a replacement for pgvector recall) that walks a tree of nodes, each carrying a natural-language `manifest` describing its children, and uses LLM-select to reason over those descriptions and prune subtrees down to a depth bound. Manifest maintenance is O(depth) per mutation via a local update on write. Expose it as a retrieval-strategy hook in `server.py`, selectable per query-class from `[agents.orchestration]`, with vector recall remaining the default. Store node/manifest rows in `schema-init.sql`.
**Where:** `usr/lib/mios/agent-pipe/server.py` (retrieval strategy hook), `usr/share/mios/postgres/schema-init.sql`, `usr/share/mios/mios.toml`
**Done When:** A longitudinal-tree query retrieves via manifest LLM-select traversal with subtrees pruned, measurably beating flat vector recall on that query class, and a document mutation updates only local manifests with no sibling re-embed.
**Why:** Cosine-only recall over a deep document tree returns locally-similar fragments and misses structurally-relevant branches, and today there is no alternative strategy to select.
**Dep:** none
**Status:** pending | **Domain:** Agents/Memory

## T-158 -- MAO-05: identity-aware delegation -- extend agent-passport/A2A with attested routing metadata  (WS-MAO | P2 | M)
**Goal:** E-24 Autonomy guardrails -- delegation picks lanes on measured quality and cost, so the agent plane cannot be gamed into routing work to the worst or most expensive delegate.
**What+How:** Extend the shipped MiOS agent identity (A2A card plus `agent-passport.json` with Ed25519 and `max_permission`) with `reasoning_profile`, `context_window`, `cost_hint` and capability fields for metadata-aware routing (cheap-fast model for simple subtasks, heavy lane for hard reasoning). Defeat the Provenance Paradox -- routing on self-reported score systematically selects the worst delegates -- by attesting quality from measured outcomes rather than claims. Add governed sessions holding persistent context so history is not re-sent every call, and trust domains carrying capability scopes and data-handling rules. This extends existing identity; do NOT adopt the LDP wire protocol (`arXiv 2603.18043`, unverifiable) blind.
**Where:** agent-passport + A2A card generators under `usr/share/mios/agents/` and `usr/lib/mios/agent-pipe/`, `usr/lib/mios/agent-pipe/server.py` (router), `usr/share/mios/mios.toml`
**Done When:** Delegation demonstrably routes on attested, measured quality so a self-inflating delegate is not preferred, and a subtask's model tier is chosen from the delegate's `reasoning_profile`/`cost_hint` while sessions stop re-transmitting full history per call.
**Why:** The router has no cost or capability signal, so every subtask can land on the heavy lane, and any peer that claims a high score wins the work regardless of results.
**Dep:** none (extends shipped agent-passport/A2A)
**Status:** pending | **Domain:** Agents/A2A

## T-159 -- MAO-06: negotiated progressive delegation payloads (token-efficiency modes)  (WS-MAO | P3 | M)
**Goal:** E-24 Autonomy guardrails -- delegation traffic costs the fewest tokens the peers can jointly support, without losing the auditable path.
**What+How:** Negotiate the richest mutually-supported payload mode along a chain -- text (auditable fallback) -> semantic-frame (typed JSON, ~37% token reduction claimed) -> embedding hints -> semantic graph -- with automatic fall-back down the chain when a peer does not support a mode. Text mode is always retained for auditability. Gate it and measure the real token delta before defaulting to anything above text. Feeds `feedback_native_typed_launch_args_all_tools`. Source (LDP) is an unverifiable concept.
**Where:** `usr/lib/mios/agent-pipe/server.py` / the A2A transport, `usr/share/mios/mios.toml`
**Done When:** Two MiOS agents negotiate semantic-frame mode, fall back to text against a peer that lacks it, log the measured token reduction, and show no quality regression versus text on a delegation benchmark.
**Why:** Every delegation currently ships full text payloads, so federated work pays maximum tokens even between two peers that could exchange typed frames.
**Dep:** T-158 (capability fields on the passport/A2A card carry the supported modes)
**Status:** pending | **Domain:** Agents/A2A

## T-160 -- MAO-07: O(N) introspective leave-one-out contribution scoring feeding reputation  (WS-MAO | P3 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the `reputation` table gets real measured input, so fan-out weighting is data-driven rather than uniform.
**What+How:** Score each council/swarm agent's marginal contribution without re-running the debate: after a session, prompt the remaining agents to re-decide while ignoring agent *j*'s inputs; the outcome delta approximates leave-one-out at O(N) instead of O(T*N^2). Write scores into the pgvector `reputation` table (`schema-init.sql`), down-weighting consistently negative or adversarial agents and surfacing high-value ones in later fan-outs. Gate it and degrade open -- no scoring model means equal weights. IntrospecLOO is an unverifiable concept feeding the existing reputation workstream.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql` (`reputation`), `usr/share/mios/mios.toml`
**Done When:** After a council session every agent carries an O(N) LOO contribution score in which a positively-necessary agent outscores a redundant one, those scores weight the next fan-out, and with no scoring model available weights fall back to equal.
**Why:** Every council member is weighted identically today, so an agent that consistently degrades the answer keeps getting the same share of the fan-out and the same GPU time.
**Dep:** none (feeds existing reputation workstream)
**Status:** pending | **Domain:** Agents/Reputation

## T-161 -- MAO-08: fan-out topology and debate protocol selected from SSOT, never hardcoded  (WS-MAO | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the orchestration shape is an operator-tunable, model-selected decision instead of one fixed path baked into server.py.
**What+How:** Make the fan-out topology (pipeline / hierarchical / swarm / mesh) and the debate protocol (within-round / cross-round / rank-adaptive cross-round) selectable per task-class from `[agents.orchestration]` combined with the orchestrator's own judgement -- Law 7 forbids a keyword gate, so the selection is model-driven. Document the trade-off in the SSOT comments and the reference doc: within-round maximizes peer-reference and interaction but converges slowly, while rank-adaptive cross-round converges fastest. No single hardcoded choice remains.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[agents.orchestration]`)
**Done When:** Topology and debate protocol are chosen per task-class from SSOT plus orchestrator judgement rather than a fixed code path, switching protocol visibly changes convergence/interaction behaviour as documented, and the default degrades open to today's fan-out.
**Why:** One hardcoded fan-out shape is applied to every task class, so tasks that would converge in one rank-adaptive round pay full within-round debate cost and vice versa.
**Dep:** T-154 (typed hops give the topology something to route over)
**Status:** pending | **Domain:** Agents/Orchestration

## T-162 -- WBRAND-04: self-authored SSOT-driven living-wallpaper mesh-gradient shader  (WS-WBRAND | P3 | M)
**Goal:** E-22 Dotfiles projection -- another visual surface derives its colors from `[colors]` in mios.toml rather than carrying its own palette.
**What+How:** Author a small (~40-line) WGSL/GLSL mesh-gradient fragment shader at `usr/share/mios/branding/living-wallpaper.wgsl` whose colors read `[colors].accent`/`[colors].bg` -- the same values behind the static wallpaper, the DWM accent and matugen. Use no third-party code, or Apache-2.0 BabylonJS if a full engine is ever wanted. LAW: never vendor `firecmsco/neat` (MIT + Commons Clause) or any non-OSI dependency into a shipped OS, and verify every LICENSE at vendor time. Ship the degrade-open ladder: animated shader -> static SSOT gradient (today's baked JPG) -> solid accent, gated `[branding].living_wallpaper`, off by default.
**Where:** `usr/share/mios/branding/living-wallpaper.wgsl` (new), `usr/share/mios/mios.toml` (`[branding]`)
**Done When:** The shader renders a mesh gradient composed solely from SSOT colors with no hardcoded palette and stays disabled by default, auto-degrading to the static gradient on a no-Vulkan or old-iGPU host, with no Commons-Clause or non-OSI dependency vendored.
**Why:** A wallpaper with its own palette is a second color source that silently diverges from `[colors]`, and vendoring a Commons-Clause dependency would make the shipped image non-redistributable.
**Dep:** none
**Status:** done (2026-07-09) | **Domain:** Branding

## T-163 -- WBRAND-05: render the living wallpaper natively on Linux (GNOME/Wayland, optional Quickshell)  (WS-WBRAND | P3 | M)
**Goal:** E-22 Dotfiles projection -- the Linux desktop surface consumes the same SSOT-derived shader without a browser dependency.
**What+How:** Render the T-162 shader natively via Qt6 RHI over Vulkan/OpenGL on the Mesa iGPU (MiOS already ships `[packages.gpu-mesa]`), not WebGPU-in-browser. Because GNOME/Wayland exposes no shader-wallpaper API, implement a minimal Wayland-background helper or an `mpvpaper` video loop in `usr/libexec/mios/mios-living-wallpaper`; an optional Hyprland/Quickshell desktop profile may use a native `ShaderEffect` (references: MIT `magetsu002/qs-wallpaper-picker`, `bjarneo/quickshell`). The universal fallback is a pre-rendered loop. Gated and off by default.
**Where:** `usr/libexec/mios/mios-living-wallpaper` (new), `usr/share/mios/mios.toml`
**Done When:** The SSOT mesh gradient animates on a MiOS GNOME/Wayland desktop driven by the iGPU, falls back to static or video where unsupported, and the Linux path pulls in no browser or WebGPU flag.
**Why:** Without a native path the only way to animate the desktop on Linux would be a browser window at background z-order -- a permanent Chromium process on the desktop plane.
**Dep:** T-162
**Status:** done (2026-07-09) | **Domain:** Linux/Branding

## T-164 -- WBRAND-06: Windows animated background + `[branding].living_wallpaper*` SSOT keys  (WS-WBRAND | P3 | M)
**Goal:** E-22 Dotfiles projection -- the Windows half of the branding surface is projected from the same SSOT keys as Linux, both platforms, one registry.
**What+How:** Add a MiOS-XBOX/MiOS-Win animated desktop background driven by the T-162 shader/palette -- a borderless WebView2/D3D canvas at background z-order, or the more compatible pre-rendered loop. WebGPU-in-browser (WebView2/D3D12) is acceptable ONLY on Windows. Add `[branding].living_wallpaper` and `living_wallpaper_mode` (`shader|video|static`) to mios.toml and expose them in `mios.html`, then wire the Windows branding path (`MiOS-Provision.lib.ps1` / `Set-MiOSIdentityOffline`) to read them alongside the current static gradient.
**Where:** `usr/share/mios/mios.toml` (`[branding]`), `usr/share/mios/configurator/mios.html`, `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`
**Done When:** `living_wallpaper_mode=static` reproduces today's baked gradient with no regression while `shader`/`video` add the animated layer from SSOT colors, and the mode is settable in the configurator and read through the layered SSOT resolver.
**Why:** Windows branding is currently a hardcoded static gradient with no SSOT key, so the two platforms' desktop appearance can only be kept in sync by hand.
**Dep:** T-162
**Status:** done (2026-07-09) | **Domain:** Windows/Branding

## T-165 -- NAME-01: collapse ~1,290 authored names onto one generated names/keys registry  (WS-NAME | P2 | L)
**Goal:** E-10 One canonical name: the unified names/keys registry -- no env var renames a native key and no capability carries a second name (Law 9).
**What+How:** Collapse every authored name in MiOS -- TOML keys, `MIOS_*` env vars, verbs, `globals.sh`/`.ps1` constants, configurator `data-key`s and emitters, about 1,290 today -- onto ONE registry that is the naming SSOT (`usr/share/mios/names.toml`, or `mios.toml [names]`). Delete the translation layer outright: the 418-entry key->env table in `tools/lib/userenv.sh` / `usr/lib/mios/userenv.sh` and the `globals` mirror give way to generic sourcing, so every surface takes the same canonical identifier directly from the generated registry. Fold similar capabilities into one parametric entry, keeping exactly one minimal combined name per capability. Zero functional loss -- rename and collapse only, behind a compat-shim phase. Add the drift-gate to `automation/98-drift-checks.sh`. Full workflow, convention and phased migration are in `usr/share/doc/mios/reference/naming-unification.md`. Effort is XL.
**Where:** `usr/share/mios/names.toml` (new) or `mios.toml [names]`, `tools/lib/userenv.sh`, `usr/lib/mios/userenv.sh`, `automation/lib/globals.sh`/`.ps1`, `usr/lib/mios/mios_toml.py`, `automation/98-drift-checks.sh`, `usr/share/doc/mios/reference/naming-unification.md`
**Done When:** One registry is the naming SSOT with every surface generated from or sourcing it and no authored per-name mapping left anywhere; similar capabilities are folded to one parametric entry with legacy names and the userenv table deleted at zero functional regression; and a drift-gate regenerates and diffs the registry, failing on any new translation or duplicate, with all `test_mios_*` and `just drift-gate` green.
**Why:** A hand-maintained 418-entry translation table means every new fact must be named twice, and the emitted-vs-consumed mismatch class (`MIOS_AI_VLLM_*` vs `MIOS_VLLM_*`) keeps producing keys that are referenced but never emitted.
**Dep:** none
**Status:** planned -- BLOCKED ON A DECISION THIS TASK OWNS, now made concrete. Two findings from attempting it: (1) `tools/generate-names-registry.py:23-31` carries `SHORT_ALIAS_PREFIX`/`SHORT_ALIAS_IRREGULAR`, a SECOND authored per-name mapping hand-mirroring `mios_toml.get_aliases()` -- so the Done-When "no authored per-name mapping left anywhere" fails in two places, not one. (2) Deriving the generator from `get_aliases()` (the one authority) changes **182 of 571 rows**, because the registry and the running system disagree about which name is canonical: the registry records the deterministic transform (`ports.ssh` -> `MIOS_PORTS_SSH`, 5 consumers) while the system overwhelmingly uses the short alias (`MIOS_PORT_SSH`, 18 consumers); same for `identity.username` -> `MIOS_IDENTITY_USERNAME` (5) vs `MIOS_USER` (88). BOTH are emitted by globals.sh, so neither is wrong -- which is exactly the ambiguity Law 9 exists to remove. This is safe to change (nothing reads `names.generated.txt` at runtime; only check 30 regenerates-and-diffs it, and `mios_var_closure` excludes it), but picking a winner for 182 values is this task's decision to make, not a cleanup to slip in. DECIDE FIRST: is the canonical name the deterministic transform or the short alias? Then the generator derives from `get_aliases` and its private table is deleted. Also unchanged: `TARGET_SECTIONS` is 22 hardcoded sections, so the registry is a partial slice; `usr/share/mios/names.toml` does not exist; `naming-unification.md` still reads "Status: planned". **Domain:** SSOT/Cross-cutting

## T-166 -- DEPLOY-01: reorder install/first-boot into a producer->consumer DAG so "missing dependency" is impossible  (WS-DEPLOY | P1 | L)
**Goal:** E-21 One deploy front door -- a clean install reaches a fully working system instead of a half-provisioned one whose failures depend on timing.
**What+How:** (1) Model the producer->consumer DAG across `automation/NN-*.sh` and the `*-firstboot` units, encoding edges as systemd `After=`/`Requires=`/`ConditionPathExists=`. (2) Replace fixed timeouts with readiness gates that poll the real health/socket/row/file signal plus `Restart=on-failure`. (3) Make every producer atomic, retried, idempotent and completeness-self-checking -- the `38-hermes-agent.sh` venv fix (install `-r requirements.txt` in one retried transaction) is the reference pattern to apply to the webtools/sandbox image builds, the GGUF/vLLM fetch and the forge bootstrap. (4) Topologically reorder the overlay/automation sequence. (5) Add a drift-gate to `automation/98-drift-checks.sh` that fails the build on any consumer-before-producer edge (a missing `After=`/`Condition*=`). Full plan in `usr/share/doc/mios/reference/install-ordering.md`.
**Where:** `automation/38-hermes-agent.sh` (done), `usr/libexec/mios/mios-ai-firstboot`, `usr/libexec/mios/mios-webtools-firstboot.sh`, `usr/libexec/mios/forge-firstboot.sh`, the `*-firstboot`/`38-*` units and their `.service` `After=`/`Condition*=`, `automation/build.sh`, `automation/98-drift-checks.sh`, `usr/share/doc/mios/reference/install-ordering.md`
**Done When:** Every consumer step gates on its producer's real readiness with no fixed-timeout aborts and every producer is atomic, retried, idempotent and completeness-checked; a clean `podman-MiOS-DEV` reinstall brings up AI plane, forge and webtools with zero "missing dependency" failures; and the new drift-gate fails the build on any consumer-before-producer edge with `just drift-gate` and `test_mios_*` green.
**Why:** A clean reinstall today produces prerequisite-not-ready and artifact-not-built states that vary run to run, so install success depends on machine speed rather than on declared ordering.
**Dep:** none (surfaced by the clean-reinstall debug)
**Status:** planned | **Domain:** Install/Deploy/SSOT

## T-167 -- SHELL-01: persistent PTY substrate so shell state survives across agent turns  (WS-CODEMODE | P2 | M)
**Goal:** E-24 Autonomy guardrails -- tool execution gains a bounded, reapable long-lived session instead of a fresh isolated process per call.
**What+How:** (1) Add `usr/lib/mios/agent-pipe/mios_pty.py` as a pure module beside `mios_aci`: session-id keying, tmux-argv construction, and a marker-sentinel plus per-command nonce protocol capturing completion, exit code and cwd, hardened against output spoofing; ship `test_mios_pty.py`. (2) Add `usr/libexec/mios/mios-shell-session`, a tmux-backed bash with one session per chat, confined in the existing bwrap jail at `--level baseline` reusing UID 828 with no new container. (3) Bound output through the existing `mios_aci` normalizer (head+tail+marker elision). (4) Add `mios-shell-session-gc.{service,timer}` as an idle reaper plus tmpfiles for `/var/lib/mios/shell-sessions`. (5) Register `[verbs.shell_session]` (model_name `run_in_shell`) and a `[shell_session]` config block in mios.toml, which auto-projects to MCP/OpenAI/A2A with no new dispatch code. Repo grep confirms no `mios_pty`/`mios-shell-session`/`run_in_shell` exists today.
**Where:** `usr/lib/mios/agent-pipe/mios_pty.py` (new) + test, `usr/libexec/mios/mios-shell-session` (new), `usr/lib/systemd/system/mios-shell-session-gc.{service,timer}` (new), `usr/lib/tmpfiles.d/`, `usr/share/mios/mios.toml`
**Done When:** `exec --session t1 'cd /tmp && export FOO=bar'` followed by `exec --session t1 'echo $PWD $FOO'` returns `/tmp bar`; a 5MB log comes back ACI-elided rather than raw-truncated; idle sessions are reaped by the GC timer and `run_in_shell` appears on `/v1/tools`; `test_mios_pty.py` passes on nonce/marker parsing and exit-code capture.
**Why:** Every shell or code call discards `cwd`, `env` and history, so an agent must re-establish its working state on every single turn and cannot run any multi-step workflow that depends on shell state.
**Dep:** none hard; independent of the other Part-17 items
**Status:** done -- VERIFIED against a live tmux, not just unit-tested. `exec --session t1 'cd /tmp && export FOO=bar'` then `exec --session t1 'echo $PWD $FOO'` returns exactly `/tmp bar`; a 5000-line command comes back ACI-elided with BOTH head and tail plus the omission marker; sessions are isolated (a second session has its own cwd and no FOO); exit codes are carried (0, 1); and a command that KILLS the shell returns in 0.3s instead of hanging to the timeout. Shipped: `mios_pipe/routing/pty.py` (pure protocol, 40 assertions in `test_mios_pty.py`), `usr/libexec/mios/mios-shell-session` (exec/gc/list/kill), `[shell_session]` SSOT + `[verbs.shell_session]` (model_name `run_in_shell`, now on the generated tool surface), tmpfiles for the state dir (Law 2), and `mios-shell-session-gc.{service,timer}` preset-enabled. THREE defects only running it revealed, all fixed at the source and documented in manual ch56: (1) the marker matched its own PTY ECHO, so the first command reported a null exit code parsed out of the literal `$?` -- fixed by printing the marker in two pieces; (2) a shell-killing command spun the poll loop to the full timeout -- fixed by checking session liveness on capture failure; (3) long output lost its HEAD because tmux keeps 2000 scrollback lines and `history-limit` applies only to panes created after it is set, with `set-option -g` failing outright before the first session -- fixed by passing a generated tmux.conf with `-f`. Ships OFF by default: a long-lived shell is state the agent accumulates. **Domain:** Tool-execution/Sandbox | **Who:** agent-pipe backend engineer (Python + bwrap/tmux)

## T-168 -- KENF-01: Tetragon eBPF/LSM kernel enforcement plane behind the intent arbiter  (WS-SEC | P2 | L) [VM]
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- side-effects are verified in-kernel, not merely reasoned about in userspace.
**What+How:** (1) Add `usr/share/containers/systemd/mios-enforcer.container` running Cilium Tetragon standalone (file-based TracingPolicies, no K8s) as user `mios-enforcer` -- a DOCUMENTED Law-6 privileged exception (CAP_BPF/CAP_SYS_ADMIN) added to the `automation/99-postcheck.sh` allowlist beside mios-ceph/k3s with a header rationale. (2) Add `mios-enforcer-render` compiling `mios.toml [security.policy]` into Tetragon TracingPolicy YAML plus a firstboot oneshot, with seed `policies.d/*.yaml.tmpl` (exfil-block on tcp_connect, exec-guard on execve/LSM) cgroup-scoped to the AI and codemode units only. (3) Add `mios-enforcer-shipper` writing `enforcer_kill`/`enforcer_deny` rows into the `event`/`tool_call` tables. (4) Add `[security.enforcer]` and `[security.policy]` SSOT sections, configurator cards and the `mios-enforcer` sysuser. (5) Gate the unit `ConditionVirtualization` OFF on WSL2 (no BPF/LSM surface); enforcement is bare-metal only and ships in observe mode first.
**Where:** `usr/share/containers/systemd/mios-enforcer.container` (new), `usr/libexec/mios/mios-enforcer-render` and `-shipper` (new), `automation/99-postcheck.sh` (allowlist), `usr/lib/sysusers.d/`, `usr/share/mios/mios.toml`
**Done When:** In observe mode a tainted process's disallowed `execve` or outbound connect produces a Tetragon Post event and a shipper row; flipping to enforce SIGKILLs the offending process; the unit is Condition-skipped and inert on the WSL2 dev VM; `bootc container lint` and the Law-6 postcheck pass with the documented exception; and editing `[security.policy]` re-renders the TracingPolicy YAML with no hardcoded policy.
**Why:** The shipped `mios-policy-arbiter` can only reason about intent -- a compromised AI process can still `execve` and connect outbound with nothing in the kernel to observe or stop it.
**Dep:** after the arbiter (already shipped); shares the dangerous-verb/taint set with T-033 (SEC-02)
**Status:** planned | **Domain:** Security/Kernel | **Who:** security engineer (eBPF/Tetragon + bootc quadlets)

## T-169 -- ISOL-01: per-action isolation tier ladder that promotes instead of refusing  (WS-CODEMODE | P2 | L)
**Goal:** E-24 Autonomy guardrails -- a tainted high-risk action runs in a stronger sandbox rather than being blocked, so safety does not cost capability.
**What+How:** (1) Add an `[isolation]` table to mios.toml carrying the ladder definition, taint->tier map, `taint_min_tier`, `default_code_tier` and `health_gate`, reusing the existing high-privilege verb set rather than re-listing it. (2) Add `usr/lib/mios/agent-pipe/mios_isolation.py` as pure tier-selection/promotion logic plus tests. (3) In dispatch, replace the binary REFUSE-on-taint branch with `resolve_effective_tier()` that runs the action in the promoted tier and emits a `firewall_promote {from_tier,to_tier}` event, degrading CLOSED to `firewall_block` when the floor tier is unavailable. (4) Register `runsc` (gVisor, tier 3) and `krun` (libkrun via crun, tier 4) as OCI runtimes with USER-scope Quadlet templates reusing the hardened sandbox verbatim, `krun` gated `ConditionPathExists=/dev/kvm`. (5) Add a `mios-coderun-tier` launcher and a gated `automation/NN-isolation-tiers.sh` build hook. Distinct from T-032 (hermetic microVM per tool): this is the tier-selection engine.
**Where:** `usr/lib/mios/agent-pipe/mios_isolation.py` (new) + test, `usr/lib/mios/agent-pipe/server.py` (dispatch taint branch), `usr/share/containers/containers.conf.d/*-isolation-runtimes.conf` (new), `usr/libexec/mios/mios-coderun-tier` (new), `usr/share/mios/mios.toml`
**Done When:** Tainting a session with an external `open_url` and then dispatching a high-privilege verb records a `firewall_promote` event with the verb having run in the promoted tier; `[isolation].enable=false` leaves behavior byte-identical to today; the tier-4 microVM Quadlet is inert on WSL2 with no `/dev/kvm`; and `test_mios_isolation.py` passes on tier selection and degrade-closed.
**Why:** Tiers 1-2 exist but gVisor and microVM do not, and the taint plane only refuses -- so any tainted session simply loses access to its high-value verbs instead of running them more safely.
**Dep:** shares the sandbox substrate with T-032/T-045; the promote decision reads the same dangerous-verb set as T-033/T-168
**Status:** planned | **Domain:** Security/Sandbox | **Who:** security engineer (OCI runtimes + agent-pipe dispatch)

## T-170 -- GVLM-01: activate the staged grounding VLM and add the `cu_act`/`cu_verify` verbs  (WS-RUNTIME-WIRE | P1 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a perception->action->verify chain that already ships stops being inert.
**What+How:** (1) Bake/reference the vision GGUF already named in `usr/share/mios/llamacpp/mios-llm-light.yaml` (Holo1.5-7B Q4_K_M plus mmproj-Q8_0, mapped from `qwen3-vl:4b`) into the bound `mios-llm-light` seed and set `[ai].vision_grounding_model="qwen3-vl:4b"` with a `vision_grounding_enable` gate; the operator performs the actual weight fetch (the classifier blocks assistant HF fetch) and mradermacher filenames are verified at bake time. (2) Add `usr/libexec/mios/mios-cu-verify`, a visual Definition-of-Done tool -- the screen analogue of `mios-verify-launch` -- that returns `{ok:false}` honestly when the lane is down and never fabricates. (3) Add a `cu_act` subcommand to `mios-computer-use` (ground -> click -> verify) and register `[verbs.cu_verify]` and `[verbs.cu_act]` for three-projection. (4) Set `[computer_use].verify_after_act`, keeping AT-SPI grounding as the deterministic fast path with the VLM used only on canvas/Electron misses.
**Where:** `usr/share/mios/mios.toml` (`[ai]`/`[computer_use]` keys + verbs), `usr/share/mios/llamacpp/mios-llm-light.yaml` (already staged), `usr/libexec/mios/mios-cu-verify` (new), `usr/libexec/mios/mios-computer-use`
**Done When:** `curl <light-lane>/v1/chat/completions model=qwen3-vl:4b` with a base64 screenshot returns coordinate JSON; `mios-pc-vision <png> "the OK button"` returns `{x,y,confidence>0.5}`; `mios-cu-verify "<criterion>"` returns `{ok:false}` when the lane is down; `cu_act`/`cu_verify` appear on `/v1/tools` and the whole path is inert with `vision_grounding_enable=false`.
**Why:** `mios-pc-vision`, `cu_ground` and `mios-verify-launch` all ship but `[ai].vision_grounding_model` is empty, so the grounding lane never activates and the image carries a computer-use capability that cannot be invoked.
**Dep:** independent; rides existing `cu_*` and verify tooling -- the operator bake step gates final live verification
**Status:** done-by-code | **Domain:** Computer-Use/Perception | **Who:** computer-use engineer (llama.cpp vision + verbs)

## T-171 -- CONS-01: weighted multi-judge consensus over 2-3 lanes  (WS-DURA | P2 | M)
**Goal:** E-24 Autonomy guardrails -- judging quality becomes a scored, reliability-weighted quorum rather than one lane's yes/no.
**What+How:** (1) Add `usr/lib/mios/agent-pipe/mios_consensus.py` as a pure module implementing weighted_vote plus Reciprocal-Rank-Fusion over 2-3 judge lanes, with weights optionally sourced from the `reliability_run` output of T-049 and degrade-open to a single judge on the fast CPU path; ship `test_mios_consensus.py`. (2) Wire it into the judge/synthesis path in `server.py` behind a `[consensus]` gate. (3) Add the `[consensus]` SSOT section plus a configurator card.
**Where:** `usr/lib/mios/agent-pipe/mios_consensus.py` (new) + test, `usr/lib/mios/agent-pipe/server.py` (judge/synthesis), `usr/share/mios/mios.toml`
**Done When:** A multi-judge Definition-of-Done is reached by quorum with conflicting judges resolved by weighted vote, `[consensus].enable=false` keeps the fast CPU path single-judge, and `test_mios_consensus.py` passes the weighted_vote and RRF math.
**Why:** The DCI critic returns a single yes/no verdict, so one unreliable judge lane can gate or pass the whole pipeline with no second opinion and no reliability weighting.
**Dep:** builds on T-049 (reliability scorer) for weights; degrade-open so it functions without it
**Status:** done -- landed: `mios_pipe/routing/consensus.py` (weighted_vote + RRF + resolve_weights, 37 assertions in `test_mios_consensus.py`), wired into `_judge_answer_satisfied` via `_judge_panel_verdict` behind `[consensus].enable` (default false), 7 wiring cases in `test_mios_reflect.py`, `[consensus]` SSOT + configurator card, rationale in manual ch52. Abstention is not a rejection; sub-quorum falls back to the single lane. | **Domain:** Orchestration/Judging | **Who:** orchestration engineer (agent-pipe judge path)

## T-172 -- CONS-02: Jensen-Shannon drift monitor as the Goodhart early-warning alarm  (WS-DURA | P2 | M)
**Goal:** E-24 Autonomy guardrails -- self-improvement and consensus cannot quietly optimize into reward-hacking without an alarm.
**What+How:** (1) Add `usr/lib/mios/agent-pipe/mios_drift.py` computing pure JSD over intent/score/verdict histograms against a frozen baseline, plus `test_mios_drift.py`. (2) Add a `drift_snapshot` table in `usr/share/mios/postgres/schema-init.sql` storing the baseline and periodic samples. (3) Add `GET /v1/drift` to `server.py` and emit a `drift_alert` event when JSD exceeds the threshold. (4) Add a `[drift]` SSOT section carrying threshold, window and `enable=false`.
**Where:** `usr/lib/mios/agent-pipe/mios_drift.py` (new) + test, `usr/share/mios/postgres/schema-init.sql`, `usr/lib/mios/agent-pipe/server.py` (`/v1/drift`), `usr/share/mios/mios.toml`
**Done When:** Crossing the JSD threshold emits a `drift_alert` event, `GET /v1/drift` returns the current divergence against baseline, and `drift_snapshot` records a baseline row on first run.
**Why:** There is no distribution-drift alarm at all, so as T-062/T-064 self-improvement and T-171 consensus come online a Goodhart shift in verdict distribution would be invisible until behavior visibly degrades.
**Dep:** pairs with T-171/T-049; can land independently as an observe-only alarm
**Status:** done -- landed: `mios_pipe/observability/drift_monitor.py` (bounded log2 JSD + per-axis `compare` + thin-window guard, 33 assertions in `test_mios_drift_monitor.py`), `drift_snapshot` table, `GET /v1/drift` emitting `drift_alert`, `[drift_monitor]` SSOT + configurator card, manual ch53. NOTE: the SSOT table is `[drift_monitor]`, NOT `[drift]` -- `[drift]` already registers agent-pipe module-wiring exceptions. Axes are `verdict` + `intent`, extracted from recorded satisfaction events, so no separate sampler is needed. | **Domain:** Observability/Safety | **Who:** orchestration engineer (metrics + pgvector)

## T-173 -- GUARD-01: daemon runaway controls -- host-pressure gate, classification dedup, cron cap  (WS-GUARD | P0 | M)
**Goal:** E-24 Autonomy guardrails -- the agent plane cannot starve its own host; this is the direct fix for the live GPU-runaway incident.
**What+How:** (1) Add `_host_pressure_gate()` to `usr/libexec/mios/mios-daemon`, caching loadavg and `nvidia-smi` at roughly 5s TTL and guarding the classify, refusal, cron and suggestions loops so a tick is skipped under pressure. (2) Add per-`(source,kind,summary-hash)` dedup plus cooldown so repeated identical high-severity classifications are suppressed. (3) Add a cron concurrency cap tracking Popen so cron actions cannot stack. (4) Feed a quiescence/auto-halt signal into cadence backoff. (5) Add a `[daemon]` SSOT section plus configurator cards for thresholds, TTL and cap, with no hardcoded literals.
**Where:** `usr/libexec/mios/mios-daemon`, `usr/share/mios/mios.toml` (`[daemon]`), the configurator
**Done When:** Repeated identical high-severity classifications are suppressed by dedup+cooldown, loops skip a tick when the pressure gate fires, concurrent cron actions cannot stack under the cap, and `test_mios_daemon.py` covers both the gate and the dedup.
**Why:** Five subsystems guard the shared 4090 with independent local heuristics that do not compose, so the daemon->swarm runaway had no cumulative tripwire and no host-pressure circuit breaker -- it already happened once on live hardware.
**Dep:** first-wave safety; composes with T-174 (budget) and the existing admission controller into one pressure signal
**Status:** done -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: `_host_pressure_gate()` in `usr/libexec/mios/mios-daemon` guarding the loops, the `[daemon]` SSOT section, `_dedup_suppressed` + the escalation cooldown, the `cron_concurrency_cap` defer, and `test_mios_daemon.py`. | **Domain:** Autonomy/Safety | **Who:** agent-pipe/daemon engineer

## T-174 -- GUARD-02: aggregate token/turn budget with foreground preemption of background work  (WS-GUARD | P0 | M)
**Goal:** E-24 Autonomy guardrails -- background autonomy is budgeted and preemptible, so a self-driving loop cannot monopolize the GPU.
**What+How:** (1) Add a cumulative token/turn ceiling in `usr/lib/mios/agent-pipe/server.py`, debited both per-conversation and per-autonomous-source, hard-halting on exhaustion with a graceful stop. (2) Give `mios_autonomous` its own low budget and the lowest dispatch priority so a foreground turn preempts background work for the next GPU slot. (3) Add a `max_dispatch_depth` recursion bound that refuses deeper dispatch. (4) Route every threshold through `[budget]`/`[dispatch]` in mios.toml plus the configurator.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[budget]`/`[dispatch]`)
**Done When:** A background loop self-limits and hard-halts at its budget, a foreground turn demonstrably preempts background work for the next GPU slot, and recursion beyond `max_dispatch_depth` is refused.
**Why:** No cumulative token or turn ceiling exists and autonomous work is not first-class isolated at the queue, so a background loop can consume unbounded GPU while an interactive turn waits behind it.
**Dep:** pairs with T-173; both must compose into the single host-pressure signal the admission controller and swarm-width logic read
**Status:** done -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: the `[budget]` SSOT section, `MAX_DISPATCH_DEPTH` wired through `server.py`, and the preemption state machine in `mios_pipe/scheduler/preempt.py` covered by `test_mios_preempt.py`. | **Domain:** Autonomy/Scheduling | **Who:** agent-pipe scheduler engineer

## T-175 -- DURA-01 nightly `pg_dump` backup timer + loopback-only pgvector bind  (WS-DURA | P1 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- the pgvector datastore that holds the whole agent brain survives a disk loss and is not reachable off-host by default.
**What+How:** Add `mios-pgvector-backup.service` + `mios-pgvector-backup.timer` running a nightly `pg_dump` into `/var/lib/mios/backups`, declaring that directory through `usr/lib/tmpfiles.d/` rather than `mkdir` (the NO-MKDIR-IN-VAR postcheck forbids it). Change the pgvector quadlet to bind `127.0.0.1` by default and refuse any off-loopback bind until a non-default password is set. Add a `[pgvector]` SSOT section carrying bind address, credential policy and backup retention, and expose it in the configurator so none of the three is a literal in the unit.
**Where:** `usr/lib/systemd/system/mios-pgvector-backup.{service,timer}` (new) | `usr/lib/tmpfiles.d/` | pgvector quadlet | `usr/share/mios/mios.toml` (`[pgvector]`)
**Done When:** the timer fires and leaves a restorable dump under `/var/lib/mios/backups`; `ss -ltnp` shows pgvector on `127.0.0.1` only with stock config and an off-loopback bind is refused without a non-default password; `bootc container lint` and the NO-MKDIR-IN-VAR postcheck stay green.
**Why:** knowledge, memory, passports and audit all live in pgvector with no backup at all, and it historically bound `0.0.0.0` on default credentials -- so one disk failure erases the brain and one flat network exposes it, while the immutable OS half is fully rollback-protected (inverse asymmetry).
**Dep:** Independent; complements T-060 (DATA-02 storage versioning) and any schema-rollback work.
**Status:** planned | **Domain:** Data/Durability | **Who:** platform/ops engineer (systemd timers + quadlets)

---

## T-176 -- DURA-02 SSOT-driven secret/PII redaction before persist, scratchpad and A2A echo  (WS-DURA | P1 | M)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- redaction on every persist and every federate, so an autonomous loop cannot leak credentials it happened to read.
**What+How:** Add one redaction filter in `server.py` and call it on all three egress paths: the pgvector write, the scratchpad broadcast, and the A2A echo -- reusing/extending the existing persistence sanitization that already strips vendor names and paths, so there is a single scrubber rather than three. Carry the secret patterns (API keys, tokens) and common PII patterns in `mios.toml [security]` instead of hardcoded English deny-list literals (Law 7), with the filter default-on for persist and its degrade-open behaviour documented.
**Where:** `usr/lib/mios/agent-pipe/server.py` (persist / scratchpad / A2A echo paths) | `usr/share/mios/mios.toml` (`[security]`)
**Done When:** a turn containing a synthetic key and a synthetic PII string reaches pgvector, the scratchpad and an A2A echo scrubbed; the pattern set is read from SSOT (grep finds no inline deny-list); `test_*` cases cover redact-on-persist and redact-on-federate and fail if the filter is bypassed.
**Why:** secrets and PII are written verbatim into pgvector, broadcast on the scratchpad and echoed over A2A today -- once federation leaves loopback, every leaked token is permanently in a peer's memory store.
**Dep:** Should precede any non-loopback A2A federation; composes with the passport gate (T-001/T-014).
**Status:** done -- the summary table already carried this verdict; the detail line had never been updated. Re-verified against the tree: the `[security.redact]` SSOT pattern set consumed on the persist path (`mios_pipe/memory/pg.py`) and the federate path (`mios_pipe/federation/a2a.py`), covered by `test_mios_redact.py`. | **Domain:** Security/Privacy | **Who:** agent-pipe backend engineer

---

## T-177 -- LSFS-01 semantic-filesystem verbs + durable cross-turn task-state protocol  (WS-LSFS | P3 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- the FS and pgvector become one recallable memory surface the agent can address by meaning, not path.
**What+How:** Add `[verbs.lsfs_*]` cmd-template verbs (`mount`/`create`/`write`/`search`/`rollback`/`share`) in mios.toml backed by the filesystem plus pgvector and nomic-embed -- pure cmd-template so they auto-project through the existing verb surface and add no runtime dependency. Add a `tasks` table to `schema-init.sql` (or an equivalent `tasks/backlog|in-progress|done.md` directory protocol) that the agent reads and writes to carry execution state across turns, and wire the read into prompt assembly as a tool-sourced block only -- never a `pre_llm_call` auto-prepend, which would violate the no-injection rule. Add an `[lsfs]` SSOT section plus configurator entry.
**Where:** `usr/share/mios/mios.toml` (`[verbs.lsfs_*]`, `[lsfs]`) | `usr/share/mios/postgres/schema-init.sql` (`tasks`) | `usr/lib/mios/agent-pipe/server.py` (task-state read into assembly)
**Done When:** `lsfs_write` followed by `lsfs_search` round-trips a semantic query over the stored content; `lsfs_rollback` restores a prior version of an entry; task state survives an agent-pipe restart and is observable only through a tool call, with no auto-injected block in the assembled prompt.
**Why:** docs-index, pgvector and scratch exist but there is no semantic-FS verb surface over them and no durable backlog/in-progress/done state, so a long-running agent re-derives its own plan every turn and loses it on restart.
**Dep:** Independent, last (P3); reuses the existing memory/knowledge substrate.
**Status:** planned | **Domain:** Memory/Filesystem | **Who:** agent-pipe engineer (verbs + pgvector)

---

## T-178 -- HEAVY-01 auto-provision the heavy-lane weights so the STATED vLLM+SGLang lanes actually come up  (WS-DEPLOY | P1 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- the heavy inference lanes MiOS already declares in SSOT deploy themselves on a detected dGPU with no manual step.
**What+How:** Do not re-decide any lane default -- the fix is to DEPLOY what `[lanes.*]`, `[ai.vllm]`, `[ai.sglang]`, `[ai.host_thresholds]` and `lane_priority` already state. (1) Fix `mios-ai-firstboot`'s weights fetch to be atomic, retried and checksum-verified (the WS-DEPLOY producer pattern) so `mios-llm-heavy.container`'s `ConditionPathExists=/usr/share/mios/vllm/model/config.json` is satisfied on a fresh install, choosing the model by the stated tier resolution for the detected 24 GB card. (2) Extend the tier resolver in `build-mios.ps1`, the install pipeline and `mios-hermes-firstboot` only where they fail to apply the stated default, keeping the mios.html knobs. (3) Confirm `MIOS_AGENT_PIPE_BACKEND` / `[nodes.local-*]` / the hermes route match the stated lanes. (4) Honour the stated `gpu_util` / `mem_fraction=0.45` so heavy, light and the Windows host co-tenant without OOM.
**Where:** `usr/libexec/mios/mios-ai-firstboot` | `usr/share/mios/mios.toml` (`[lanes.*]`, `[ai.vllm]`, `[ai.sglang]`, `[ai.host_thresholds]`, `lane_priority`) | `usr/share/containers/systemd/mios-llm-heavy.container` | `build-mios.ps1` | `usr/libexec/mios/mios-hermes-firstboot`
**Done When:** a fresh install on a detected dGPU brings the heavy lane up per the stated SSOT defaults with the model auto-fetched (no manual step, Condition gate satisfied); a plain-English query is answered on the GPU with agents/nodes/hermes routed by `lane_priority` and light-lane + Windows co-tenancy staying OOM-free; both the vLLM and SGLang lanes come up -- neither silently dropped.
**Why:** the SSOT advertises heavy lanes that never start, because the weights are missing and the Condition gate holds the unit down forever -- so the documented dGPU capability is dead on every fresh install and every query falls back to the light lane.
**Dep:** After the agent venv fix (31a52fb1, done), since the weights fetch runs through it; aligns with WS-DEPLOY's readiness-gated producer pattern.
**Status:** in-progress | **Domain:** AI-plane/Inference/Deploy | **Who:** inference/deploy agent

---

## T-200 -- FBM-01 `mios-models-firstboot.service`: resumable, checksummed first-boot GGUF provisioner  (WS-FBM | P2 | M)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- large model weights arrive on first boot, once, without blocking boot or bloating the image.
**What+How:** Add a first-boot oneshot unit plus its `usr/libexec/mios/mios-models-firstboot` fetcher that reads the model set from SSOT (the `[ai.firstboot_models]` table from T-201) and downloads GGUFs into `/var/lib/mios/llamacpp/models` with resume, sha256 verify and a progress file, then writes a sentinel so it never re-runs. Order it `After=network-online.target` with `ConditionPathExists=!<sentinel>`, register it in `usr/lib/systemd/system-preset/`, and make it degrade-open -- a failed pull must never fail the boot. Reuse the existing llama-swap model directory and `mios-llm-light` lane layout rather than inventing a second one.
**Where:** `usr/lib/systemd/system/mios-models-firstboot.service` (new) | `usr/libexec/mios/mios-models-firstboot` (new) | `usr/lib/systemd/system-preset/`
**Done When:** a fresh boot with an empty model dir pulls the SSOT set, verifies each sha, writes the sentinel, and is inert on the next boot; a network-down first boot still reaches a login with the lane serving whatever is present; killing the fetch mid-pull and rebooting resumes rather than restarting the download.
**Why:** without it the heavy/light lanes can only ever serve models baked into the image, so every non-baked model is a manual `wget` per host and a half-downloaded file leaves the lane permanently broken.
**Dep:** Must land before the lanes can serve non-baked models; depends on T-201 for its input table.
**Status:** in-progress -- four of the five remaining items are closed. (1) REAL sha256: the fetcher streams the part file through hashlib and DELETES it on mismatch (it printed "Verifying sha256" and renamed without hashing -- see T-201). (2) `SENTINEL.touch()` is now GATED on every declared model actually being on disk; it fired unconditionally before, so one failed download retired the provisioner permanently -- the unit's ConditionPathExists gate had already been satisfied. It still exits 0 either way (Law 12), so `mios-models-firstboot.timer` retries. (4) `/var/lib/mios/llamacpp/models` is declared in `usr/lib/tmpfiles.d/mios-llamacpp.conf` instead of being mkdir'd by the fetcher (Law 2). (5) New gate `check_firstboot_provisioners` ties the triple together -- fetcher exists and IS the unit's ExecStart, the unit gates on a sentinel path the fetcher actually writes, a preset line enables it, and every /var dir it writes is tmpfiles-declared; 8 directions in the sibling test, plus a negative test that repoints the gate at a sentinel nothing writes. REMAINING: (3) only -- populate a real `[[ai.firstboot_models]]` entry, or accept the "ships dormant" scope. Declaring URLs and digests I cannot verify offline would be fabrication, so the SSOT documents the dormancy instead. **Domain:** Provisioning/AI-lanes | **Who:** systemd/build agent

---

## T-201 -- FBM-02 `[ai.firstboot_models]` SSOT table + `mios models {list,sync,add,rm}`  (WS-FBM | P2 | M)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- which models a host provisions is an operator-editable SSOT fact, not a constant in a fetch script.
**What+How:** Add an `[ai.firstboot_models]` table to mios.toml with one entry per model (name, GGUF/HF source URL, sha256, target lane) and flow it through the existing projections -- `usr/libexec/mios/userenv.sh`, `install.env` and the configurator HTML -- so the same set is visible in every surface. Add a `mios models` subcommand in `usr/bin/mios` with `list`, `sync`, `add` and `rm` verbs that read the table and drive the T-200 fetcher on demand, with `add`/`rm` writing the runtime user-layer overlay rather than editing the vendor file.
**Where:** `usr/share/mios/mios.toml` (`[ai.firstboot_models]`) | `usr/bin/mios` | `usr/libexec/mios/userenv.sh` | configurator HTML
**Done When:** `mios models list` prints exactly the SSOT set; `mios models sync` pulls the missing entries and verifies each checksum; `mios models add`/`rm` change the overlay and a following `sync` reflects it; the drift-check confirming the table round-trips through `userenv.sh` and `install.env` passes.
**Why:** the model list would otherwise be hardcoded in the first-boot fetcher, so changing which model a fleet runs means editing and rebuilding a script instead of editing one config surface.
**Dep:** Feeds T-200; do first or together.
**Status:** done -- the machinery is real; the vendor list stays empty ON PURPOSE (declaring model URLs + digests I cannot verify offline would be fabrication, and the SSOT documents the dormancy). SECURITY: the fetcher printed `Verifying sha256 for {name}...` and then renamed the part file WITHOUT HASHING ANYTHING -- a corrupted or substituted GGUF installed and reported as verified. It now streams the part file through sha256 chunked, and on mismatch DELETES it and skips the model so a resume cannot poison the next run. `mios models list` reads the LAYERED [ai].firstboot_models through mios_toml.load_merged (it globbed the filesystem and never opened the TOML -- its tomllib import was dead), joins it against disk, and shows declared-but-missing and undeclared-on-disk separately. `add`/`rm` were a print statement and a file-delete; they now edit the USER overlay per the cascade and never the vendor file, refuse a duplicate name, and warn when no digest is given. Entry schema documented in the SSOT. 21 assertions in `usr/libexec/mios/test_mios_models.py`, including an end-to-end fetch through a curl stub proving a matching payload installs and a substituted one is rejected with nothing left on disk. | **Domain:** SSOT/CLI | **Who:** config/CLI agent

---

## T-202 -- FBM-03 `mios-bound-images-firstboot`: pull the heavy-lane container images at boot, not at bake  (WS-FBM | P3 | M)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- the published image stays inside a standard runner's budget while heavy lanes still start on demand.
**What+How:** Add a first-boot oneshot service plus a libexec puller that fetches the heavy-lane (SGLang/vLLM) container images at boot, keyed off the same sentinel pattern T-200 establishes, driven by a bound-images list in mios.toml. Optionally split-bake -- keep the small base images baked so the a-la-carte cascade still resolves offline, and pull only the large layers.
**Where:** `usr/lib/systemd/system/mios-bound-images-firstboot.service` (new) + libexec puller (new) | `usr/share/mios/mios.toml` (bound-images list)
**Done When:** a first boot pulls the heavy-lane images exactly once and the heavy lanes start against them when enabled; the built image no longer contains the large heavy-lane layers and the measured image size drops.
**Why:** the vLLM+SGLang whales are the reason the bake has to be tiered to fit a standard runner at all -- while they are baked in, every publish is capacity-gated.
**Dep:** After the T-200 sentinel/first-boot pattern is established.
**Status:** done-by-code (audited) -- `[build.bake].firstboot_tokens` (mios.toml:10484) projects through `tools/generate-bake-plan.py` into `usr/lib/mios/bake/plan.d/firstboot.list` (4 refs), and BOTH de-bake branches honour it: the shell path in `automation/01-system-files-overlay.sh:113-131` and the Rust `miosd overlay-bind-images` path (`src/mios-rs/miosd/src/main.rs:724-800`, which re-parses firstboot_tokens). Cleanup left: the dormant `mios-bound-images-firstboot` unit is a second mechanism on an undeclared key -- retire it or point it at firstboot.list. | **Domain:** Provisioning/Containers | **Who:** systemd/build agent

---

## T-203 -- FBM-04 Portal model-provisioning tile + `mios models cache <dir>` air-gapped pre-seed  (WS-FBM | P3 | S)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- provisioning state is visible at the same door the operator configures from, and works with no egress.
**What+How:** Add a "model provisioning" tile to the Quickshell/Portal surface that reads the T-200 sentinel and progress file and renders progress / complete / failed. Add a `mios models cache <dir>` verb to `usr/bin/mios` that copies models from a USB or local mirror into the model dir and marks them satisfied, so an air-gapped install can be pre-seeded before first boot and T-200 skips the download entirely.
**Where:** `usr/share/mios/quickshell/` (tile) | `usr/bin/mios` (`models cache`)
**Done When:** the tile tracks live provisioning state through a real pull (progress, then complete, then failed on an induced error); after `mios models cache <dir>` a first boot finds the models present, writes the sentinel and performs no network fetch.
**Why:** provisioning is otherwise a silent multi-gigabyte background download with no operator-visible state, and an air-gapped install has no way to supply the weights at all.
**Dep:** After T-200 and T-201.
**Status:** planned | **Domain:** UI/Provisioning | **Who:** portal/UI agent

---

## T-204 -- OFFL-01 vendor `terra.repo` instead of curling it at build  (WS-OFFL | P3 | S)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- a build input is a tracked in-tree file, not a network round-trip (Law 12 BAKE-NOT-FETCH).
**What+How:** `automation/05-enable-external-repos.sh` fetches `terra.repo` over the network. Vendor the file as `usr/share/mios/repos/terra.repo` and change the step to copy the in-tree copy, keeping the network fetch only behind an explicit `--online` flag.
**Where:** `automation/05-enable-external-repos.sh` | `usr/share/mios/repos/terra.repo` (new)
**Done When:** a build with egress blocked passes the repo-enable step with no outbound request.
**Why:** an upstream URL change or a five-minute outage breaks the build for every operator, and the repo definition that gates package resolution is untracked and unreviewable.
**Dep:** Independent; part of the offline-build sweep.
**Status:** done | **Domain:** Build/Offline | **Who:** build agent

---

## T-205 -- OFFL-02 vendor desktop assets: Geist + Nerd fonts, Bibata cursor, flathub mirror  (WS-OFFL | P3 | M)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- the desktop layer bakes from in-tree bytes rather than four live remotes.
**What+How:** `automation/09-fonts.sh` and `automation/10-gnome.sh` fetch Geist and Nerd-Fonts, the Bibata cursor, and add the flathub remote at build time. Vendor `usr/share/mios/vendored/fonts/{geist,nerd}.tar.xz` and `usr/share/mios/vendored/cursors/bibata-*.tar.xz` and install from those, and stand up a local flathub mirror or bake the needed flatpaks as OCI archives -- `automation/40-flatpak-bake.sh` already does OCI bake for flatpaks, so extend that path rather than adding a second one.
**Where:** `automation/09-fonts.sh` | `automation/10-gnome.sh` | `usr/share/mios/vendored/fonts/` (new) | `usr/share/mios/vendored/cursors/` (new)
**Done When:** an offline build installs the fonts and cursor from the in-tree tarballs and the flatpak install resolves from the local mirror / OCI archives, with no remote added.
**Why:** four separate desktop remotes each turn a font-CDN hiccup into a failed OS build, and the exact font/cursor bytes shipped to users are not pinned in the tree.
**Dep:** Independent.
**Status:** done | **Domain:** Build/Offline | **Who:** build agent

---

## T-206 -- OFFL-03 vendor the k3s binary + k3s-selinux policy  (WS-OFFL | P3 | S)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- the cluster layer installs from tracked artifacts instead of a fetch and a git clone.
**What+How:** `automation/13-ceph-k3s.sh` downloads the k3s binary and `automation/19-k3s-selinux.sh` clones k3s-selinux. Vendor `usr/share/mios/vendored/k3s/k3s-<tag>` plus a k3s-selinux source tarball and change both steps to install from in-tree.
**Where:** `automation/13-ceph-k3s.sh` | `automation/19-k3s-selinux.sh` | `usr/share/mios/vendored/k3s/` (new)
**Done When:** an offline build installs k3s and its SELinux policy with no clone and no download.
**Why:** cloning a default branch at build means the SELinux policy shipped in the image is whatever upstream had that minute -- unreviewed, unpinned and unbuildable offline.
**Dep:** Independent.
**Status:** done | **Domain:** Build/Offline | **Who:** build agent

---

## T-207 -- OFFL-04 vendor the hermes-agent source snapshot + a `--no-index` wheelhouse  (WS-OFFL | P3 | M)
**Goal:** E-02 Technical-debt retirement: the TD-1..TD-8 register -- retires a network-at-build baker from the "clone the default branch and WARN forever" class.
**What+How:** `automation/38-hermes-agent.sh` fetches the hermes-agent git tree and its pip dependencies during the build. Vendor a source snapshot in-tree plus a wheelhouse under `usr/share/mios/vendored/wheels/`, and switch the venv step to `pip install --no-index --find-links <wheelhouse>` so dependency resolution is fully local and reproducible.
**Where:** `automation/38-hermes-agent.sh` | `usr/share/mios/vendored/wheels/` (new) | vendored hermes source (new)
**Done When:** the hermes venv builds with PyPI unreachable and no git remote configured.
**Why:** the agent runtime is assembled from an unpinned branch plus whatever PyPI serves at build time, so two builds of the same commit can ship different agent code -- the exact drift class the debt register exists to close.
**Dep:** Independent.
**Status:** done | **Domain:** Build/Offline | **Who:** build agent

---

## T-208 -- OFFL-05 vendor the baseline GGUF blobs + pre-pull the llama-swap proxy image  (WS-OFFL | P2 | M)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- an offline build still yields a bootable image that can answer a prompt.
**What+How:** `automation/38-llamacpp-prep.sh` fetches GGUF blobs and the llama-swap proxy image at build. Bundle only the small/default GGUFs under `usr/share/mios/vendored/models/` and pre-pull the proxy image into the build cache; coordinate with WS-FBM so the large models stay on the T-200 first-boot path and only the baseline lands in the bake.
**Where:** `automation/38-llamacpp-prep.sh` | `usr/share/mios/vendored/models/` (new)
**Done When:** an offline build produces a bootable image containing the baseline model and the proxy image, with zero build-time model fetch.
**Why:** without a baseline model in the bake, an air-gapped install boots into an AI OS whose front door has nothing to serve; with all models in the bake, the image is too large to publish.
**Dep:** Coordinate with T-200/T-201, which own the large-model path.
**Status:** done | **Domain:** Build/Offline/AI-lanes | **Who:** build agent

---

## T-209 -- OFFL-06 local rpm mirror image so `dnf` never leaves the host at build  (WS-OFFL | P3 | L)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- the last and largest build-time egress path is closed.
**What+How:** Package installs still reach Fedora mirrors during the build. Ship a local rpm mirror image (or a vendored repo snapshot) and point the `automation/` dnf-config step at it, with a new reproducible mirror-snapshot build target so the mirror contents themselves are regenerable rather than a hand-curated blob. This is the largest remaining offline gap -- scope the snapshot step before implementing.
**Where:** `automation/` dnf-config step | new mirror-build target
**Done When:** a build with all egress blocked completes the package-install phase entirely from the local mirror.
**Why:** every other offline fix is moot while `dnf` needs the internet -- the Scenario-2 USB build cannot run in an air-gapped facility at all.
**Dep:** Last and heaviest item of the WS-OFFL sweep.
**Status:** done | **Domain:** Build/Offline | **Who:** build agent

---

## T-210 -- IGPU-00 Wave-0 go/no-go probes: iGPU-in-WSL, 4 GB heavy lane, WSL rebaseline  (WS-IGPU | P2 [VM] | S)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- multi-vendor GPU compute is committed to only after the hardware says it works.
**What+How:** Run three gating probes on real hardware and record each result: (1) an iGPU-in-WSL matmul via AMD ROCDXG or Intel Level-Zero; (2) the heavy lane inside ~4 GB using `--gpu-memory-utilization 0.2` plus KV-cache CPU offload; (3) a WSL rebaseline confirming `wsl --version` >= 2.7.5 and kernel >= 6.18. Write the findings up as the explicit go/no-go for T-211 and T-212 rather than leaving them in a chat log.
**Where:** operator-loop probes | findings captured in `usr/share/doc/mios/concepts/`
**Done When:** all three probe results and a written go/no-go decision exist in `usr/share/doc/mios/concepts/`.
**Why:** T-211 and T-212 are both L-effort lane rewrites that are wasted work if the iGPU passthrough or the 4 GB heavy lane simply does not function on this hardware.
**Dep:** Blocks T-211 and T-212.
**Status:** planned | **Domain:** Verification/Compute | **Who:** operator/VM

---

## T-211 -- IGPU-01 move the iGPU inference lane in-VM and delete `mios-igpu-server.ps1`  (WS-IGPU | P2 [VM] | L)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- every inference lane runs inside the image, and a PowerShell-as-program service disappears with it (Law 14).
**What+How:** Stand up a ROCm/Level-Zero iGPU lane inside the VM with its own launch script and quadlet, register it as an `[agents.*]`/lane entry in mios.toml so it routes like every other lane, then retire the native-Windows `mios-igpu-server.ps1` on :11436 together with the Tailscale hop that reached it.
**Where:** new lane launch script + quadlet | `usr/share/mios/mios.toml` (`[agents.*]`) | remove/deprecate the `mios-igpu-server.ps1` path
**Done When:** the iGPU lane serves inference from inside the VM and both the native Windows iGPU server and its Tailscale hop are gone from the tree and from the running host.
**Why:** one lane living outside the image breaks the single-artifact model -- it cannot be rolled back with `bootc rollback`, it needs a host-side network hop to be reachable, and it is a PowerShell program the language policy no longer permits.
**Dep:** Gated on T-210 probe #1 passing.
**Status:** planned | **Domain:** Compute/AI-lanes | **Who:** lanes agent

---

## T-212 -- IGPU-02 llama.cpp RPC fabric across lanes behind one logical endpoint + coopmat2 verify  (WS-IGPU | P2 | L)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- pooled cross-lane VRAM lets the fleet run a model no single device can hold.
**What+How:** Run a llama.cpp `rpc-server` per lane (phone, iGPU, dGPU, cluster), mapped onto `[agents.*.nodes.*]` / `[nodes.*]` in SSOT, and point agent-pipe's endpoint routing at one logical RPC endpoint so an oversized model shards transparently across them. Verify coopmat2 support on the Vulkan lane as part of the bring-up.
**Where:** `usr/share/mios/mios.toml` (`[nodes.*]`) | lane launch scripts | agent-pipe endpoint routing
**Done When:** a model larger than any single lane's VRAM answers a request through the one logical endpoint; coopmat2 is confirmed working on the Vulkan lane.
**Why:** today each lane is capped by its own device, so the largest model the fleet can run is the largest one card can hold, and idle VRAM on the other lanes is unreachable.
**Dep:** After T-210 and T-211.
**Status:** planned | **Domain:** Compute/AI-lanes | **Who:** lanes agent

---

## T-213 -- RDSK-01 Selkies WebRTC + NVENC remote-desktop lane with VNC fallback  (WS-RDSK | P3 | L)
**Goal:** E-19 Wire the shipped-but-unwired runtime capabilities -- a GPU host uses its hardware encoder for remote desktop instead of software rendering.
**What+How:** Add a Selkies (WebRTC + NVENC) or Neko remote-desktop lane as an `automation/` bake step plus a `.container` quadlet gated by an enable flag in mios.toml, so it is a-la-carte like every other sidecar. Keep the existing KasmVNC/llvmpipe path as the fallback for non-GPU hosts rather than replacing it.
**Where:** new `automation/` bake step | new `.container` quadlet | `usr/share/mios/mios.toml` (enable gate)
**Done When:** a GPU host streams the desktop over NVENC/WebRTC and a non-GPU host falls back to the VNC path with no manual switch.
**Why:** remote desktop currently runs through llvmpipe software rendering, so the GPU sits idle while the interactive session is unusable at high resolution.
**Dep:** Independent; GPU-host gated.
**Status:** planned | **Domain:** RemoteDesktop/GPU | **Who:** desktop agent

---

## T-214 -- WSL-01 rootfs-export -> `wsl --import` pipeline + a MiOS-owned updater for WSL  (WS-WSL | P2 | L)
**Goal:** E-20 The bootc-native install legs -- the same OCI artifact installs onto a third target, and stays upgradable there.
**What+How:** Add an `automation/` step that exports the built OCI image as a WSL-importable rootfs plus a `Justfile` wsl2 target that drives it, extending the existing scaffolding (`usr/lib/wsl-distribution.conf`, `config/artifacts/wsl2.toml`) rather than starting new config. Because `bootc upgrade` is inoperable inside WSL (Finding D), also ship a MiOS-owned update mechanism that refreshes an installed WSL distro from a newer image without bootc.
**Where:** new `automation/` rootfs-export step | `Justfile` (wsl2 target) | `usr/lib/wsl-distribution.conf` | `config/artifacts/wsl2.toml`
**Done When:** `wsl --import` of the exported rootfs yields a working MiOS distro, and the MiOS updater moves an already-installed WSL distro to a newer image with bootc absent.
**Why:** WSL is the dual-personality path onto every Windows box, but today the image cannot be imported there and any WSL install that did exist would be frozen forever with no upgrade route.
**Dep:** Independent; pairs with T-215 and T-216.
**Status:** in-progress | **Domain:** Packaging/WSL | **Who:** build agent

---

## T-215 -- WSL-02 air-gapped atomic upgrade: `skopeo copy` -> oci -> `bootc switch` + soft-reboot  (WS-WSL | P2 | L)
**Goal:** E-20 The bootc-native install legs -- an offline host upgrades from an OCI tarball on USB with zero egress.
**What+How:** Implement the offline upgrade route end to end: `skopeo copy … oci:/usb`, then `bootc switch --transport oci`, then `bootc upgrade --apply`. Split the kernel-versus-userspace delta so non-kernel updates apply via soft-reboot instead of a full reboot. `automation/43-uupd-installer.sh` already covers part of the updater -- extend it rather than adding a parallel path, and document the route.
**Where:** `automation/43-uupd-installer.sh` | new offline-upgrade path/doc
**Done When:** an air-gapped host upgrades from an OCI-on-USB image and a userspace-only update lands via soft-reboot without a full restart.
**Why:** an immutable OS whose only upgrade path needs a registry is not sovereign -- air-gapped fleets have no way to receive a security fix, and every userspace change costs a full reboot.
**Dep:** Independent.
**Status:** planned | **Domain:** Lifecycle/Offline | **Who:** build agent

---

## T-216 -- WSL-03 `.wslconfig` hygiene template + cosign self-verify on pull + `UserNS=auto`  (WS-WSL | P3 | M)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- the WSL update path verifies what it pulls, and rootful quadlets stop running with full namespace privilege.
**What+How:** Ship the not-yet-confirmed WSL tuning: a `.wslconfig` template with `sparseVhd` and `autoMemoryReclaim`, plus a `/mnt/shared_memory` tmpfs pre-mount hook. Add cosign self-verify-on-pull to the WSL updater -- `automation/42-cosign-policy.sh` and `automation/90-generate-sbom.sh` already sign, so this is consuming an existing signature, not creating a new chain -- and set `UserNS=auto` on the rootful `.container` templates.
**Where:** `config/artifacts/wsl2.toml` | `usr/lib/wsl-distribution.conf` | rootful `.container` templates | WSL updater
**Done When:** the `.wslconfig` template ships with `sparseVhd` and `autoMemoryReclaim`; the WSL updater refuses an unsigned or mis-signed image on pull; rootful quadlets carry `UserNS=auto`.
**Why:** MiOS signs its images and then the WSL updater ignores the signature, so the one install path that runs on an untrusted Windows host is also the one that will install anything handed to it -- while its VHD grows without bound.
**Dep:** After T-214.
**Status:** in-progress | **Domain:** WSL/Supply-chain | **Who:** build agent

---

## T-217 -- STD26-01 adopt the MCP `2026-07-28` wire: Streamable-HTTP, structured tool output, elicitation  (WS-STD26 | P2 | L)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- elicitation gives the tool surface a real human-in-the-loop primitive, and structured output makes tool results checkable.
**What+How:** Upgrade `mios_mcp.py` and the served `mcp.json` to the `2026-07-28` wire: stateless Streamable-HTTP transport, `Mcp-Method`/`Mcp-Name` headers, JSON-Schema-typed structured tool OUTPUT, elicitation as the HITL primitive, sampling, MCP Apps, and a local MCP Registry with `.well-known` Server Cards emitted from a new emitter. Keep the current stdio/consume surface working as a fallback so existing peers do not break.
**Where:** `usr/lib/mios/agent-pipe/mios_mcp.py` | `usr/share/mios/ai/v1/mcp.json` | `.well-known` server-card emitter
**Done When:** a `2026-07-28` MCP client connects over Streamable-HTTP, reads structured tool output and the Server Cards, and successfully elicits a response; the legacy stdio client still connects.
**Why:** on the old wire every tool result is unstructured text the model must re-parse, there is no protocol-level way to ask the operator before a risky action, and new-wire clients cannot talk to MiOS at all.
**Dep:** Independent; coordinate with T-221 (elicitation-based HITL) and WS-FED.
**Status:** planned | **Domain:** Standards/MCP | **Who:** federation agent

---

## T-218 -- STD26-02 A2A v1.0.0 AgentCard with JWS-over-JCS signature + standard task states  (WS-STD26 | P2 | L)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- a federated peer's identity is cryptographically verifiable before it is trusted.
**What+How:** Move the published AgentCard from 0.3.0 to v1.0.0 per `a2a.proto`, add `AgentCardSignature` as a JWS over the JCS-canonical card signed with the Ed25519 passport key (building on `mios_a2a_principal.py`, which already carries signed principals, and FED-G4), map swarm/DAG node status onto the standard A2A task states instead of MiOS-private names, and emit `TaskStatusUpdateEvent` push webhooks. Card assembly lives in `server.py`'s `_build_agent_card`; the signing policy belongs in `mios.toml [a2a.security]`.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py` | `usr/lib/mios/agent-pipe/server.py` (`_build_agent_card`) | `usr/share/mios/mios.toml` (`[a2a.security]`)
**Done When:** the published card validates as A2A v1.0 with a verifiable `AgentCardSignature`, and DAG/swarm progress is observable by a stock A2A client as standard task states with push updates.
**Why:** an unsigned 0.3.0 card means any host on the network can claim to be a MiOS peer, and MiOS-private status names make swarm progress invisible to every off-the-shelf A2A client.
**Dep:** Extends FED-G4/T-012; pairs with T-219.
**Status:** in-progress | **Domain:** Standards/A2A | **Who:** federation agent

---

## T-219 -- STD26-03 OASF Agent Directory + DID identity replacing the hand-maintained peer overlays  (WS-STD26 | P2 | L)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- peers are discovered and identity-resolved from a synced directory instead of a file an operator edits by hand.
**What+How:** Add a directory service (`mios_agentreg.py`) that publishes and consumes OASF-described records and resolves DID-based agent identities, then repoint agent-pipe's routing at it and retire the hand-maintained `ai/v1/mcp.json` and `a2a-peers.json` overlays as the source of peers. This is the highest-leverage federation move: it replaces two hand-edited registries with one syncable, identity-bearing one.
**Where:** `usr/lib/mios/agent-pipe/mios_agentreg.py` (new) | `usr/share/mios/ai/v1/mcp.json` | `a2a-peers.json`
**Done When:** peers register via OASF records carrying DID identity, the directory syncs between hosts, and agent-pipe routes from the directory rather than reading the static overlay files.
**Why:** every peer today is a hand-edited JSON line with no identity attached, so federation does not scale past a handful of hosts and there is nothing to authenticate a peer against.
**Dep:** Pairs with T-218; supersedes the FED-G3 overlay reload for the directory case.
**Status:** planned | **Domain:** Standards/Federation | **Who:** federation agent

---

## T-220 -- STD26-04 durable event history over swarm/DAG runs + a Memory-Block abstraction  (WS-STD26 | P3 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- recall and writes go through a typed memory abstraction, and a crashed run resumes instead of restarting.
**What+How:** Add a Temporal-style local event history over the `server.py` DAG executor so a crashed run replays from its recorded events, and introduce an explicit Memory-Block abstraction in `mios_memory.py` over raw pgvector rows so callers stop touching row shapes directly. Formalize `_admit` against the Agent Control Protocol (static risk + stateful trace + ledger). The sleep-time consolidation half is already covered by MEM-05/T-056 -- this task is only the durability plus Memory-Block delta.
**Where:** `usr/lib/mios/agent-pipe/server.py` (DAG executor) | `usr/lib/mios/agent-pipe/mios_memory.py`
**Done When:** a DAG run killed mid-execution resumes from the event history on restart, and recall/write paths go through Memory-Block with no raw-row access left in the callers.
**Why:** a crash loses a whole multi-step run today, and every caller reaching into raw pgvector rows means the schema can never change without breaking the agent plane.
**Dep:** After the Kernel Stage-2 rewire (A6/T-025) stabilizes the DAG path.
**Status:** planned | **Domain:** Durability/Memory | **Who:** orchestration agent

## T-221 -- STD26-05: Re-express the bespoke HITL gate on MCP elicitation + A2A task states  (WS-GUARD | P3 | M)
**Goal:** E-24 Autonomy guardrails: the agent plane cannot starve its own host -- a human approval gate any standards client can drive, so autonomy always has an interoperable stop button.
**What+How:** Keep the bespoke approval queue as the internal backend, but expose it over open standards: implement MCP elicitation (SEP-2322) request/response on the MCP surface and emit A2A `INPUT_REQUIRED`/`AUTH_REQUIRED` task states out of `mios_hitlflow.py` / `mios_arbiter.py`, so an external client can both trigger and satisfy a pending approval over the wire rather than through MiOS-private calls. No second queue -- the standards surfaces are adapters onto `mios_hitl.py`.
**Where:** `usr/lib/mios/agent-pipe/mios_hitl.py`, `usr/lib/mios/agent-pipe/mios_hitlflow.py`, `usr/lib/mios/agent-pipe/mios_arbiter.py`; the MCP and A2A surfaces.
**Done When:** A third-party standards client raises AND clears a HITL prompt end-to-end via elicitation / `INPUT_REQUIRED`, and the approval is visible in the existing bespoke queue (one queue, two faces).
**Why:** HITL is reachable only through MiOS-private calls today, so any external MCP/A2A client meets an approval it cannot see or answer and the task stalls forever.
**Dep:** T-217 (elicitation) + T-218 (task states).
**Status:** planned | **Domain:** Standards/HITL | **Who:** federation agent

## T-222 -- OAI-01: One multi-kind capability catalog -- recipes and skills as tagged `[routing]` rows  (WS-CODEMODE | P2 | M)
**Goal:** E-24 Autonomy guardrails -- every callable capability is one uniformly-scored, composition-ruled catalog behind the single /v1 front door, not three parallel registries.
**What+How:** `mios.toml [routing]` is `kind=tool`-only today (see the comment at ~line 3097). Extend the schema with `kind` + `domain` columns and fold recipes in as function-tools and skills in as description-only rows; teach the 2-stage classifier/catalog to score ACROSS kinds; enforce composition rules in the registry loader (recipes may compose tools, recipes may NOT compose skills).
**Where:** `usr/share/mios/mios.toml [routing]`; `mios_capreg.py`, `mios_manifest.py`, `mios_verbcatalog.py`, `mios_classify.py`.
**Done When:** Recipes and skills appear as catalog rows carrying `kind`/`domain`, the router demonstrably routes a turn to each kind, and a recipe→skill composition is rejected by the loader rather than silently accepted.
**Why:** Recipes and skills are invisible to the router, so the classifier can only ever pick a tool -- shipped capability sits unreachable and callers hand-wire around it.
**Dep:** Extends the shipped 2-stage router; overlaps ORCH code-mode (T-061).
**Status:** in-progress | **Domain:** Routing/Catalog | **Who:** agent-pipe agent

## T-223 -- OAI-02: Tier-1 `usage` detail fields, strict function schemas, cache-friendly prompt ordering  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- the /v1 contract reports the exact token facts that budgets, quotas and cost gates are computed from.
**What+How:** In the `server.py` usage assembler and streaming path, emit `usage.completion_tokens_details.reasoning_tokens` and `usage.prompt_tokens_details.cached_tokens` (both absent today); mark the tool surface strict (`strict:true`, `additionalProperties:false`) in the tool-schema builder; reorder assembled prompts static-content-first so upstream prompt caches can hit. While in the path, spot-verify the streaming `[DONE]` sentinel / tool-delta contract and `developer`-role acceptance.
**Where:** `usr/lib/mios/agent-pipe/server.py` (usage assembler + streaming path); `mios_worker_tools.py` / the tool-surface builder.
**Done When:** A live `/v1/chat/completions` response carries the reasoning + cached token detail objects, the advertised function schemas are strict, and a streaming run confirms the `[DONE]` and role contracts.
**Why:** Without the detail fields, per-session budgets and quota accounting cannot separate reasoning from output tokens or cached from fresh prompt tokens, so cost gates guess; non-strict schemas let models emit unvalidated tool args.
**Dep:** none -- independent; caps off the shipped Tier-0/1 conformance work.
**Status:** done-by-code | **Domain:** OpenAI-conformance | **Who:** agent-pipe agent

## T-224 -- OAI-03: Persistent PTY/tmux shell broker + PowerShell object-pipeline flattening  (WS-CODEMODE | P2 | M)
**Goal:** E-24 Autonomy guardrails -- agent shell work runs in one bounded, stateful substrate owned by the broker instead of unbounded inline execs in agent-pipe.
**What+How:** The ACI output-normalizer `mios_aci.py` shipped but the persistent-shell substrate did not. Add a PTY/tmux-wrapped shell broker under `usr/libexec/mios/` so `cwd`/env survive across turns, and place it with the coderun sandbox/broker -- NOT inline in agent-pipe. On the Windows side, flatten .NET object pipelines to plain text in the os-control executor before returning.
**Where:** new persistent-shell broker under `usr/libexec/mios/`; `usr/share/mios/windows/mios-oscontrol-server.ps1` (pipeline flattening).
**Done When:** Two sequential shell turns share `cwd` and exported env through the same PTY session, and a PowerShell command that would return objects arrives at the model as flat text.
**Why:** Every shell turn starts from scratch today, so an agent's `cd`/`export`/venv activation evaporates between steps and it burns tokens re-establishing state; PowerShell object output arrives as unusable serialized noise.
**Dep:** Pairs with the coderun broker (F3/T-072).
**Status:** done -- BOTH clauses land. Clause 1 (two turns share `cwd` and exported env) is the SHELL-01 substrate from T-167: `usr/libexec/mios/mios-shell-session` drives a tmux-backed PTY per chat under the bwrap baseline, and `run_in_shell` reaches it as a verb; the broker lives under `usr/libexec/mios/`, not inline in agent-pipe, as this task required. Clause 2 turned out to be WORSE than "serialized noise": measured against a real pwsh 7.6.5, a console-less runspace reports `WindowSize.Width == -1`, every formatter column collapses to zero, and an object-returning cmdlet returned a BLANK LINE with exit code 0 -- a silent wrong answer the agent cannot detect. `mios-powershell` now stages the caller's script VERBATIM and calls it from a wrapper (`& '<script>' | Out-String -Stream -Width N`), which flattens to plain text while keeping the caller's own error line numbers and letting a mid-script `exit N` return through `$LASTEXITCODE` instead of stranding the format buffer. Also fixed along the way: PowerShell 7 ANSI escapes now stripped via `$PSStyle.OutputRendering=PlainText`; formatter column padding trimmed before the JSON envelope; `--work-dir` moved into the wrapper so it no longer shifts every reported line number; and the no-staging fallback moved off `-Command -` (which reads stdin a line at a time, so a multi-line script NEVER parsed) onto `-EncodedCommand`. Every knob is SSOT: `mios.toml [powershell]` (flatten / flatten_width / enumeration_limit / plain_text / trim_trailing / stage_dir / the two caps that were bash literals), with the Windows staging path DERIVED from `stage_dir` rather than double-tracked. `tests/test-powershell-flatten.sh` guards it in two tiers (stub-argv, always; live pwsh when present) -- 22 assertions, negative-tested against three sabotages. Manual ch57. | **Domain:** OS-control/ACI | **Who:** os-control agent

## T-225 -- OAI-04: Run-template REPLAY -- intent-keyed zero-token DAG reuse  (WS-DURA | P2 | M)
**Goal:** E-24 Autonomy guardrails -- repeat work costs zero planning tokens, so a looping agent cannot burn budget re-planning the same intent.
**What+How:** The capture half shipped (`[run_template].enable=true`, `GET /v1/run-templates`). Build the reuse half: a matcher in `server.py` that keys an incoming turn to a stored DAG plan by intent-class and executes it directly, skipping the planning LLM call; gate on a confidence threshold read from `mios.toml [run_template]` and fall back to full planning below it.
**Where:** `usr/lib/mios/agent-pipe/server.py` (run-template matcher); `usr/share/mios/mios.toml [run_template]`.
**Done When:** A repeated intent executes its stored DAG with zero planning-model calls (verifiable in the request log), and a deliberately fuzzy variant falls back to planning rather than replaying the wrong plan.
**Why:** Captured templates are write-only today -- every identical request pays full planning latency and tokens, and the same intent can plan differently run to run.
**Dep:** Extends the shipped capture path.
**Status:** done -- the reuse half was blocked on a KEY, not on code: templates were keyed by `_run_template_class`, a hash of the PLAN's sorted tool names and edge count, which can only be computed AFTER the planner has run and so can never answer "should I plan?". Replay now keys on the TURN -- `mios_pipe/routing/replay.py` derives sorted unique significant tokens, so word order and punctuation stop mattering -- and both keys are stored, because they answer different questions. The matcher is deliberately MODEL-FREE: embedding the turn would buy better matching with the exact resource the feature exists to conserve. Exact key wins outright; otherwise Jaccard overlap must reach `[run_template].replay_threshold` (0.85) or the caller plans, and the score is returned on a miss too so the decision is auditable. Two empty token sets score 0.0, never 1.0 -- the emptiest input must not be the most confident one. Done-When proven by COUNTING planner HTTP calls behind a stub client: the repeated intent and a re-punctuated rephrasing each spent **0** planning calls and returned the stored 2-node DAG marked `replayed`, while an unrelated turn, a 0.56-overlap near-miss, and the default flag each spent exactly 1. The capture path gained `intent`/`intent_key` columns and `decompose_intent` stamps the turn onto the plan -- WITHOUT that one line every stored row is unreplayable and the feature is silently dead while looking wired, so the suite asserts it directly (my first round-trip test passed the intent in itself and did NOT catch its removal; rewritten, it does). Capture + the replay reader also moved out of `dag_exec.py` into `mios_pipe/routing/run_template.py`, taking that module 1327 -> 1297 lines. 32 assertions in `test_mios_replay.py`, negative-tested against three sabotages. Manual ch61. | **Domain:** Orchestration/Determinism | **Who:** agent-pipe agent

## T-226 -- KACT-01: Wire the `mios_batch` coalescing chokepoint at dispatch (default OFF)  (WS-GUARD | P3 | S)
**Goal:** E-24 Autonomy guardrails -- in-flight dedup/coalescing exists at the dispatch chokepoint so a retry storm cannot fan out N identical inferences.
**What+How:** `mios_batch.py` (imported at `server.py:158`) already holds the window/hold-flush logic, but nothing calls it. Add the server-side hold/flush chokepoint keyed on `(endpoint, model)` in the dispatch path, behind a `mios.toml` flag defaulting OFF -- native vLLM/SGLang already continuous-batch, so this is a safety valve, not a throughput feature.
**Where:** `usr/lib/mios/agent-pipe/server.py` (dispatch chokepoint); `usr/lib/mios/agent-pipe/mios_batch.py`; `usr/share/mios/mios.toml`.
**Done When:** With the flag on, concurrent same-`(endpoint,model)` requests demonstrably coalesce through one hold/flush window; with the flag at its default, dispatch is byte-identical to today (a proven no-op).
**Why:** Dead imported code that looks wired but is not: the module reads as an active guardrail during review while nothing bounds duplicate fan-out.
**Dep:** none -- independent.
**Status:** done -- the chokepoint is an httpx **request event hook** on the ONE shared `AsyncClient` from `_get_client()`, which is where every upstream call in the pipe already converges; no call site had to be edited. The client and the hook were extracted out of `server.py` into `mios_pipe/kernel/httpclient.py` (T-273's direction) so the feature does not grow the monolith -- `server.py` is 4979 -> 4975 lines and the oversize register ratcheted DOWN. The dead `import mios_batch` in `server.py` went with it, and `mios_batch` came off the `[drift].denylist` of imported-but-dead modules because it is now genuinely called. `mios_pipe/scheduler/batch.py` gains `Coalescer`, the async hold-and-flush the module's own AI-hint had always said server.py owned but nobody wrote: the first caller for a `(endpoint, model)` key opens the window and arms a loop timer, every caller waits on the group's event, and the group is SEALED the instant it flushes so a request arriving mid-release opens a fresh window instead of joining one on its way out. Native-batching lanes (vLLM/SGLang/llama.cpp, which run their own rolling scheduler) and a disabled coalescer both return WITHOUT awaiting. Clause 2 is satisfied in its strongest form: the hook is not merely inert at the default, it is **never registered** -- `_get_client()` builds the client with the exact same arguments as before, asserted by the test. Clause 1 is proven by timing three concurrent non-native POSTs through the real hook (0.121s for a 0.12s window, one group, one leader), plus max_size flushing without waiting the interval, distinct endpoints and distinct models never sharing a window, and no window left behind on any path. 13 new assertions in `test_mios_batch.py`, negative-tested against two sabotages (hook registered unconditionally; hook that never holds). | **Domain:** Scheduling | **Who:** agent-pipe agent

## T-227 -- KACT-02: SmartRouting -- real remote adapters, quality gate, per-day budget  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- escalation off the local lane is bounded by an enforced daily budget, never an open-ended spend.
**What+How:** `mios_smartroute.py` (`server.py:159`) already models local-first → paid-remote escalation on a quality-gate failure, but it is disabled by default and the remote-lane adapters are stubs (see the comment at `server.py:2924`). Implement the remote adapters, orchestrate the quality gate so a failing local answer triggers exactly one escalation, and key spend through `mios_quota.py` so the per-day budget is authoritative. Keep default-off.
**Where:** `usr/lib/mios/agent-pipe/mios_smartroute.py`, `mios_quota.py`, `server.py`.
**Done When:** A forced quality-gate failure escalates to a remote lane and returns; with the daily budget exhausted the same failure falls back to local instead of spending; with the feature at its default the path is inert.
**Why:** The escalation policy exists on paper only -- a quality failure silently returns the bad local answer, and there is no budget ceiling if someone flips it on as-is.
**Dep:** Pairs with T-228 (quota keying); needs remote API keys.
**Status:** in-progress (built-gated) | **Domain:** Routing/Cost | **Who:** agent-pipe agent

## T-228 -- KACT-03: Key quota on the verified principal and persist it  (WS-GUARD | P3 | S)
**Goal:** E-24 Autonomy guardrails -- token/turn budgets are per-identity and survive restart, so a hard stop is actually hard.
**What+How:** `mios_quota.py` counts globally and in memory. Re-key its counters on the verified principal from the inbound-auth/principal path, and persist them to a quota table in the pgvector store so a restart does not zero the ledger. Add the table to `postgres/schema-init.sql` alongside the existing account/config tables.
**Where:** `usr/lib/mios/agent-pipe/mios_quota.py`, `server.py`; `usr/share/mios/postgres/schema-init.sql` (quota table).
**Done When:** Two different verified principals accrue separate quota, and a restart of agent-pipe leaves both balances intact rather than reset to zero.
**Why:** One noisy caller consumes everyone's budget today, and any restart -- including a `bootc` upgrade -- hands an exhausted account a fresh allowance.
**Dep:** After FED-G1/T-001 principal extraction; pairs with T-227.
**Status:** done -- the tracker was already keyed per principal via `_match_user_cfg()`; what was missing was durability, so every restart -- including a `bootc` upgrade -- handed an exhausted account a fresh allowance. `quota_ledger` (principal, window_start, spent, updated_at) joins `schema-init.sql`, and the policy plane gained `quota_preload()` (startup, async) + `_quota_load`/`_quota_save` (synchronous hot path, fire-and-forget upsert). The RPM deque is deliberately NOT persisted: a sliding minute of request timestamps is meaningless after a restart, and replaying it would deny a caller for traffic sent before the process existed -- only the budget window, whose whole purpose is to outlive the process, is stored. `restore()` refuses a rolled-over window, so a stale row cannot resurrect spend the caller has since been forgiven. Every failure path degrades open: an unreachable store preloads nothing, never claims persistence, and never blocks work. PROVEN LIVE against a real PostgreSQL 16: alice and bob accrued 5.0/1.0 separately, a restart restored both (`boot 2: 2 persisted budget(s) restored`), and enforcement survived it -- alice +6.0 DENIED (5+6 > 10) while bob +6.0 ALLOWED. 11 assertions in `test_mios_quota.py` + 5 in `test_mios_policy.py` against a fake store, negative-tested against two sabotages (a preload that returns nothing; a restore that ignores a rolled-over window). | **Domain:** Cost/Identity | **Who:** agent-pipe agent

## T-229 -- KACT-04: Gossip/DHT discovery transport for federated peers  (WS-GUARD | P3 | M)
**Goal:** E-24 Autonomy guardrails -- A2A federation reaches WAN peers with no central registry, so reputation (and the redaction boundary) travels with membership.
**What+How:** `mios_gossip.py` exists with no transport underneath it. Wire a gossip/DHT transport that propagates membership plus the `mios_reputation.py` scores between peers, registered from `server.py` at startup. This is the WAN/mesh path and is explicitly distinct from FED-G5's LAN-local mDNS discovery -- do not collapse the two.
**Where:** `usr/lib/mios/agent-pipe/mios_gossip.py`, `mios_reputation.py`; `server.py`.
**Done When:** Two nodes with no shared registry discover each other and exchange reputation entries purely over gossip.
**Why:** Federation beyond the LAN needs a hand-maintained peer list today -- a single point of staleness and the one thing a sovereign, registry-free mesh must not have.
**Dep:** After WS-FED inbound auth; complements FED-G5/T-013.
**Status:** in-progress (built-gated) | **Domain:** Federation/Discovery | **Who:** federation agent

## T-230 -- KACT-05: Actually EXEC the per-verb risk-tier bwrap/seccomp wrapper  (WS-GUARD | P2 | M)
**Goal:** E-24 Autonomy guardrails -- a risky verb runs inside the sandbox the policy says it runs in, not merely next to a computed argv.
**What+How:** `mios_sandbox.py` classifies each verb into a risk tier and assembles the bwrap command line via `build_bwrap_argv()`, but the wrapper is never `exec`'d and no seccomp filter is applied -- the decision is computed and discarded. Make the dispatch path execute the built argv for tiered verbs and attach the seccomp profile, so the tier is enforcement rather than metadata.
**Where:** `usr/lib/mios/agent-pipe/mios_sandbox.py`; the verb-dispatch path in `usr/lib/mios/agent-pipe/server.py`.
**Done When:** A verb at a confined tier is observably running under bwrap (its process tree shows the wrapper and it cannot reach a path outside the bind set), and a syscall outside the seccomp profile is denied instead of succeeding.
**Why:** Security-critical false assurance: the code, the docs and any reviewer read "verbs are sandboxed by risk tier" while every verb in fact runs unconfined at agent-pipe's own privilege.
**Dep:** none.
**Status:** done -- and the premise needed correcting first. Run live, `mios-sandbox-exec --level enforce` ALREADY exec'd bwrap: `/proc/1/comm` read `bwrap`, a write outside the bind set failed read-only, and the network was gone. What the same process also reported was **`Seccomp: 0`** -- the filesystem and network were jailed while `mount`, `ptrace`, `keyctl`, `bpf`, `init_module` and `perf_event_open` stayed reachable from inside a jail that read as strict. That was the real gap and it is now closed. `mios_pipe/access/seccomp.py` assembles the classic-BPF program in pure stdlib (no libseccomp): validate the audit arch, compare the syscall number against the denylist, return EPERM (or kill) on a hit, ALLOW otherwise -- 31 instructions, 248 bytes. `mios-seccomp-filter` renders it from `[sandbox].seccomp_deny` and `mios-sandbox-exec` opens it on fd 9, unlinks it, and passes `--seccomp 9`. The syscall NUMBER table is treated as ABI, not trust: the sibling test re-derives it from the host's own `asm/unistd_64.h` and fails on any mismatch, because a wrong number denies the WRONG syscall silently. Only x86_64 ships -- an architecture with no verified table REFUSES to build a filter, as does an empty denylist and a chain past the 255-slot jump range, and at enforce level a filter that cannot be built exits 126 rather than running unfiltered: a filter that denies nothing still shows `Seccomp: 2` and reads as protection. The program's arch mismatch jumps to DENY, never ALLOW (the 32-on-64 bypass), asserted on the jump target itself. PROVEN LIVE under bubblewrap 0.9.0: `PID1=bwrap`, `Seccomp: 2` with 1 filter, `chroot()` -> "Operation not permitted", ordinary work unaffected, workspace writable, outside denied, nothing leaked. 25 assertions in `test_mios_seccomp.py` + 13 in `tests/test-sandbox-seccomp.sh` (generator + live tiers, the latter running in CI now that the runner installs bubblewrap), negative-tested against three sabotages. `build_bwrap_argv` turned out to describe a DIFFERENT confinement from the one that runs; it is labelled a reference shape at its definition and the reconciliation is recorded as T-309 rather than changed blind on a security path this environment cannot VM-verify. Manual ch62. | **Domain:** Security/Sandbox | **Who:** security agent

## T-232 -- UISHELL-01: Native QML Services + Swarm views replacing the web-Portal fallback  (WS-DESKTOP | P3 | M)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- the shipped desktop shell renders MiOS state natively instead of punting to a browser.
**What+How:** Phase-2 already exposes the `PortalData` properties; replace the "open web Portal" fallback in `Sidebar.qml` with native QML list views bound directly to those properties, adding a Services view and a Swarm view. Settle the Terminals question in the same pass: launch the real terminal emulator, or embed xterm.js -- pick one and implement it.
**Where:** `usr/share/mios/quickshell/` (new Services and Swarm views, `Sidebar.qml`).
**Done When:** Services and Swarm render live from `PortalData` inside the shell with no browser launch, and the Terminals path does whatever the recorded decision says.
**Why:** The shell advertises panels that just spawn a web page, so the "native desktop" is a browser shortcut and shell state and Portal state can disagree.
**Dep:** After Phase-2 (shipped).
**Status:** planned | **Domain:** UI/QML | **Who:** portal/UI agent

## T-233 -- UISHELL-02: Login popup so `PortalData.login()` needs no QML edit  (WS-DESKTOP | P3 | S)
**Goal:** E-22 Dotfiles projection -- the operator configures the shell through the shell, never by editing shipped source.
**What+How:** Add a small QML popup component (text field + submit button) that calls `PortalData.login()` with the entered credentials -- the piece deliberately deferred in Phase 2.
**Where:** `usr/share/mios/quickshell/` (new login popup component).
**Done When:** An operator authenticates from the popup and the shell shows authenticated Portal data, with no file under `usr/share/mios/quickshell/` modified.
**Why:** Logging in currently means hand-editing a QML file in a read-only `/usr` image -- effectively impossible for a normal operator.
**Dep:** none -- independent.
**Status:** planned | **Domain:** UI/QML | **Who:** portal/UI agent

## T-234 -- UISHELL-03: One SSOT key for the `mios-webshell` AI-sidebar endpoint  (WS-DEDUP-CROSSSURFACE | P3 | S)
**Goal:** E-09 One value, one name: the full de-duplication campaign -- the AI endpoint is declared once and read by every surface, per Law 7/Law 9.
**What+How:** The Surfer patch hardcodes the AI sidebar at `:3030` (OWUI) while the Windows Zen path points at agent-pipe -- two answers to one question. Choose the canonical endpoint, express it as a single SSOT key, and make `56-bake-surfer.sh` resolve the baked default from that key instead of a literal. Land it before the next Surfer rebuild so the baked artifact is correct rather than needing a re-bake.
**Where:** `automation/56-bake-surfer.sh`; the SSOT AI-endpoint key in `usr/share/mios/mios.toml`.
**Done When:** Both the Surfer and Zen paths resolve the sidebar endpoint from the same SSOT key, no `:3030` literal remains in the bake script, and a rebuilt Surfer opens the correct endpoint.
**Why:** Two browsers in the same image talk to two different AI backends, and the divergence is frozen into a baked artifact until someone notices.
**Dep:** Before the next Surfer rebuild.
**Status:** done -- `automation/67-bake-surfer.sh` no longer bakes ANY endpoint literal: the AI sidebar resolves `MIOS_BROWSER_AI_PROVIDER_URL` ([browser_ai].provider_url, the key the Zen path also reads) and the two cockpit buttons resolve MIOS_PORT_AGENT_PIPE / MIOS_PORT_HERMES. Two of the three former literals were RETIRED ports (3030, 8642). An unresolved value hard-fails the bake rather than freezing a guess, and the file is registered in `[docs].port_clean` so a retired number cannot return. Clause 3 (a rebuilt Surfer opens the endpoint) needs a bake to observe. | **Domain:** UI/Config | **Who:** portal/UI agent

## T-235 -- UISHELL-04: Decide Cockpit's native-vs-web posture and record it  (WS-DESKTOP | P3 | S)
**Goal:** E-22 Dotfiles projection -- the desktop-shell scope is a recorded decision, not an open Phase-4 question blocking downstream work.
**What+How:** Resolve the three-way Phase-4 trade-off for Cockpit -- keep the web-hosted tile, reimplement its views in QML, or render it through a Wayland-native web renderer -- and write the decision plus rationale into the design doc / ROADMAP note. Only schedule implementation work after the decision exists; if native wins, the work lands under `usr/share/mios/quickshell/`.
**Where:** the design doc / ROADMAP note; `usr/share/mios/quickshell/` if native is chosen.
**Done When:** A written Cockpit posture decision with rationale exists and is cross-referenced from the roadmap; follow-up tasks can cite it.
**Why:** An unmade decision keeps the Cockpit tile in limbo -- nobody can size the native-shell work, and each contributor assumes a different end state.
**Dep:** After T-232 (which informs native-shell scope).
**Status:** planned (decision) | **Domain:** UI/Architecture | **Who:** architect

## T-236 -- NAME2-01: Reconcile the agent-plane user SSOT -- inert 820/822 vs live `mios-ai`/850  (WS-NAME | P2 | M)
**Goal:** E-10 One canonical name: the unified names/keys registry -- SSOT states the identity the system actually runs as, so a projection can be trusted.
**What+How:** `mios.toml` declares `[services.hermes]` uid 820 (~line 7846) and `[services.agent_pipe]` uid 822 (~line 7868) while the live agent plane runs as `mios-ai`/850 -- an SSOT lie. Pick one resolution (repoint the SSOT to 850, or retire the inert users) and carry it through every consumer in one atomic change: the agent-pipe/hermes units, the firstboot `chown`, `tmpfiles.d` entries and the sudoers rules.
**Where:** `usr/share/mios/mios.toml`; the agent-pipe and hermes unit files; the firstboot chown step; `tmpfiles.d`; sudoers.
**Done When:** SSOT and every consumer name the same live agent-plane uid, and a tree-wide search returns no remaining 820/822 references.
**Why:** Anything generated from SSOT chowns and grants to a uid nothing runs as -- so the projection is wrong by construction and future identity work builds on a false baseline.
**Dep:** Under NAME-01/T-165's umbrella; do this before any further user-name churn.
**Status:** planned | **Domain:** SSOT/Identity | **Who:** naming agent

## T-237 -- NAME2-02: Rename agent-id `mios-daemon-agent` → `daemon-agent`  (WS-NAME | P3 | M)
**Goal:** E-10 One canonical name -- agent ids follow the one naming convention with no redundant `mios-` prefix.
**What+How:** Migrate the ~105 references across ~36 files (agent registries, `mios.toml [agents.*]`, env maps) from `mios-daemon-agent` to `daemon-agent` in a single atomic change so registries and env never disagree mid-flight. External contracts stay frozen -- rename the id, not the wire surface.
**Where:** the agent registries, `usr/share/mios/mios.toml [agents.*]`, the env maps, and the ~36 files carrying `mios-daemon-agent`.
**Done When:** No `mios-daemon-agent` string remains in the tree, the drift-check is green, and a live fan-out still resolves and dispatches to the agent under its new id.
**Why:** The prefixed id is a standing exception to the agent-id convention that every new agent copies, and a half-done rename would break dispatch at runtime.
**Dep:** After T-236 -- low-risk once the user SSOT is clean.
**Status:** blocked (Done-When is self-contradictory) -- the id `mios-daemon-agent` is ALSO a live wire-surface value: it is an alias in the llama-swap model map (`usr/share/mios/llamacpp/mios-llm-light.yaml:104`), i.e. a model tag clients request over `/v1`. The task says "External contracts stay frozen -- rename the id, not the wire surface", but the Done-When says "No `mios-daemon-agent` string remains in the tree". Both cannot hold. RESOLUTION NEEDED before this can land: keep `mios-daemon-agent` as a frozen model alias, ADD `daemon-agent` alongside it, and re-scope the Done-When to "no AGENT-ID occurrence remains" (84 occurrences across 28 files today, including generated projections `ai/v1/*.json` and `names.generated.txt`). The remaining Done-When clause -- "a live fan-out still resolves and dispatches under the new id" -- needs a running host; a half-done rename breaks dispatch at runtime, which is why this should not be landed blind. **Domain:** Naming | **Who:** naming agent

## T-238 -- NAME2-03: Mutable-module-state casing pass + `ContainerName=` audit  (WS-NAME | P3 | M)
**Goal:** E-10 One canonical name -- one spelling rule holds across Python module state and unit identifiers alike.
**What+How:** Finish the residual pass the naming refactor deferred: rename module-level mutable state (semaphores, caches, registries) in `server.py` and the `mios_*.py` modules to `_lower_snake`, and audit `ContainerName=` on every renamed `.container` unit so the container name matches its unit name. `server.py` Phase-1b renames already landed -- this is the remainder.
**Where:** `usr/lib/mios/agent-pipe/server.py` and the `mios_*.py` module state; the renamed `.container` units.
**Done When:** Every module-level global that is genuinely MUTATED at runtime (caches, registries, pools) is `_lower_snake`; every `ContainerName=` equals its unit name (or, for a template unit, the instantiated `<base>-%i` form); and the drift-check is green. REVISED: the original wording -- "every module-level *mutable* global" -- was measured and does not survive contact. 406 module-level UPPER_SNAKE names are reassigned at runtime via a `global` statement, but the large majority are dependency-INJECTED configuration constants set once by `configure()` (`REFINE_MODEL`, `WEB_RESEARCH_ENABLED`, `KNOWLEDGE_RECALL_K`...). UPPER_SNAKE is correct for those; renaming them would obscure that they are config, and would break every `configure()` call site, `server.py`'s verbatim re-imports (the surface-parity gate) and the AI-hint headers. The rule that actually serves the goal is mutated-at-runtime vs set-once-at-wiring, not the literal word "mutable".
**Why:** Mixed casing on shared mutable state hides which globals are process-wide, and a `ContainerName=` that disagrees with its unit makes `podman ps` output unmappable to `systemctl` state during an incident.
**Dep:** After T-236 and T-237.
**Status:** in-progress -- the `ContainerName=` clause is DONE and gated. The audit found three things: `mios-guacamole` and `mios-pxe-hub` declared no `ContainerName` at all (Quadlet would have named them `systemd-<unit>`, which no `systemctl` name matches -- the exact incident-mapping failure this task names), and `mios-llm-worker@` names `mios-llm-worker-%i`, which is CORRECT for a template unit and is now encoded as a rule rather than read as a defect. Both gaps are fixed in the SSOT and regenerated. `check_container_names` (gate 153 of 168) now checks the SSOT and the rendered units INDEPENDENTLY, so neither can drift alone, honours `[quadlets.enable]` (a gated-off container may render nothing but must still name itself correctly for the day it is switched on), and fails rather than passing vacuously over an empty tree. 14 assertions in `tools/test_check-container-names.py` plus a negative test, proven effective by neutering the gate. The gate ALSO caught a Law-8 violation nobody was looking for: `mios-cockpit-link.container` carried a header saying it was generated from `[containers.mios-cockpit-link]`, and that block did not exist -- the file claimed a provenance it did not have, and a regenerator that cleaned its output directory would have deleted it. The block is reconstructed and PROVEN correct by regenerating byte-identically. The casing clause remains open with a corrected rule (see the revised Done-When); the narrow rename is T-311. | **Domain:** Naming/Hygiene | **Who:** naming agent

## T-239 -- UKI-01: Ship the verity-rooted UKI build and the fapolicyd enforce promotion  (WS-SEC2 | P3 | L) [VM]
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- boot integrity is measured and executables are trust-gated, closing the chain at the bottom.
**What+How:** Promote the scaffolded path to shippable: `ukify` measures the composefs fs-verity digest into `mios-verity.efi` with matching `kargs.d`, and fapolicyd moves PERMISSIVE→enforce. Fix the four named defects first -- the inverted agent-codegen carve-out rule, the false `permissive` karg claim, the rootflags merge collision, and the carve-out review. Keep the whole promotion behind an explicit operator gate: a mis-signed UKI bricks boot.
**Where:** `automation/lib/ws7-uki-fapolicyd-build.sh`; `usr/share/mios/mios.toml [security.fapolicyd_observe]`, `[uki]`, `[packages.uki]`.
**Done When:** All four defects are fixed and a VM boots a verity-rooted signed UKI with fapolicyd in enforce while agent codegen still executes -- with observe-mode remaining the shipped default.
**Why:** The UKI/fapolicyd scaffolding reads as delivered while four known defects make enforce unsafe to enable, so the strongest boot- and exec-integrity controls in the image stay permanently off.
**Dep:** Extends WS-H/H7 (fapolicyd allow-list baking); VM-gated.
**Status:** in-progress (intentionally-deferred) | **Domain:** Security/Boot | **Who:** security/build agent

## T-240 -- A3F-01: Flip the CENTRAL path to pg-primary and close the un-mirrored writes  (WS-DB | P2 | M) [VM]
**Goal:** E-23 DB-driven configuration and vector recall -- PostgreSQL is the one agent datastore, with no write path still landing in the legacy store.
**What+How:** Finish the deferred CENTRAL (server.py + OWUI pipe) cutover. Fix each un-mirrored write site: `execute_skill last_used_at`, `_skill_invocation_close`, the `hitl_approve` audit UPDATE, and the four OWUI-pipe writes in `mios_agent_pipe.py` (~L1394/1620/1910/2310). Make the `_skill_attribute_tool_call` RELATE-edge schema decision -- a `tool_call_emissions` table or an `emitted_by_invocation` column -- and apply it in `schema-init.sql`. Then flip `[pgvector].db_backend` from dual to postgres (the `_PG_PRIMARY` gate) under VM verification.
**Where:** `usr/lib/mios/agent-pipe/server.py`; `usr/share/mios/owui/pipes/mios_agent_pipe.py`; `usr/share/mios/postgres/schema-init.sql`; `usr/share/mios/mios.toml [pgvector]`.
**Done When:** With `db_backend=postgres`, a live recall + skill round-trip passes and no write site bypasses pg; the RELATE-edge schema decision is applied in the schema.
**Why:** Dual-write with un-mirrored sites means the two stores are already silently divergent -- flipping today would drop skill usage timestamps and HITL audit rows on the floor.
**Dep:** CLI/daemon cutover already DONE; gated on an operator VM session.
**Status:** in-progress -- ALL THREE named data-loss deliverables are now closed. (1) `skill_tool_call` replaces the dropped `emitted` RELATE edge; (2) `_skill_invocation_open` INSERTs a real row (started_at/params/passport) and close UPDATEs it; (3) the four OWUI-pipe writes were NOT "un-mirrored" -- they addressed the DECOMMISSIONED datastore (`_DB_URL` defaulted to the retired `:8000`), and agent-pipe has owned `session`/`tool_call`/`event` since the extraction the pipe's own docstring calls complete. They are off unless MIOS_DB_URL is set. That file carried three further live defects (see manual ch54): it did not import at all (`Any` unimported in a Pipe-body annotation, no `from __future__ import annotations`), `BACKEND_URL` named RETIRED `:8640` on the never-resolving host.containers.internal, and `REFINE_ENDPOINT` named `:8450` = `[ports].k3s_api`. Both endpoints now resolve from SSOT; 6 assertions in `tests/test-owui-pipe-endpoints.py`; file registered in `[docs].port_clean`. STILL OPEN: the RELATE-edge MINER that consumes `skill_tool_call` (nothing reads the table yet). **Domain:** Data/Migration | **Who:** data agent

## T-241 -- OSCTL2-01: Thread an explicit target hwnd through the `pc_type` path  (WS-CODEMODE | P2 | M) [VM]
**Goal:** E-24 Autonomy guardrails -- OS-control actions land in the window the agent named, so a keystroke cannot leak into whatever stole focus.
**What+How:** Plumb a window handle end-to-end: `Resolve-EditElement(FromHandle)` → `/input/type`, route compound focus through the WINDOWS executor, and pass the hwnd down to `pc_type` so typing targets the resolved window rather than UIA's idea of focus. The UIA `SetValue` write-branch (`Invoke-UIASetValue` / `Invoke-TypeText`) already shipped; `Invoke-TypeText($text)` currently accepts no target hwnd. First check whether CU-01/T-038 already covers this and close as a duplicate if so.
**Where:** `usr/share/mios/windows/mios-oscontrol-server.ps1`; the `pc_type` dispatch in `usr/lib/mios/agent-pipe/server.py`.
**Done When:** A type into a named/handle-resolved BACKGROUND window lands in that window rather than the focused one, and read-back verification of the typed text passes.
**Why:** Typing follows ambient focus today, so anything that steals focus mid-action receives the agent's keystrokes -- a correctness and a disclosure hazard on a shared desktop.
**Dep:** Extends CU-01/T-038; gated on an operator live test.
**Status:** done | **Domain:** OS-control/Windows | **Who:** os-control agent

## T-242 -- VECTOR-00: V0 foundation -- unified DB, embed provenance, DB→TOML materialize, drift-gate 29  (WS-VECTOR | P1 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- a datastore that is a LOSSLESS projection of SSOT, provable by regeneration, before any authority moves to it.
**What+How:** Land the unified pgvector DB in `/var` with `emb`/`emb_model`/`emb_version` provenance columns. Add the INVERSE step the tree lacks -- a DB→TOML materializer peering `seed-db-config.py`, which today only seeds TOML→DB. Make the verb round-trip lossless so `section`, `examples`, `model_name`, `hidden`, `aliases`, `conflict_group`, `parallel_limit` and `max_result_chars` all survive TOML↔DB. Add drift-gate check 29 (`drift_projection`) that regenerates TOML from the DB and diffs -- the theme check-25 pattern, now spanning the build boundary. No behavior change in this step.
**Where:** `usr/share/mios/postgres/schema-init.sql`; `usr/libexec/mios/seed-db-config.py` plus a new DB→TOML materialize peer; `automation/98-drift-checks.sh` (check 29).
**Done When:** Check 29 regenerates TOML from the DB and diffs clean, the verb round-trip loses no field, and `just drift-gate` plus `test_mios_*` pass.
**Why:** Without a proven-lossless inverse and a gate on it, every later phase moves authority into a store that cannot demonstrate it still holds everything SSOT held.
**Dep:** First in the V-series -- depends on nothing beyond a running `mios-pgvector`.
**Status:** done-by-code (audited, gate executed) -- unified DB at `/var/lib/mios/pgvector` declared via tmpfiles; schema-init.sql is applied BOTH at initdb and by ExecStartPost psql; emb/emb_model/emb_version provenance on knowledge, agent_memory and config_kv with matching HNSW indexes; `usr/libexec/mios/materialize-config-toml.py` is a real DB->TOML inverse; `check_drift_projection` is registered and green. Nit: the `aliases` entry in supported_verb_fields is vacuous (both sides read `hidden_aliases`). | **Domain:** AI-plane/SSOT/DB | **Who:** DB/build agent

## T-243 -- VECTOR-01: V1 config read-path -- the DB becomes the runtime read, TOML fails open  (WS-VECTOR | P1 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- runtime config resolves from the layered DB while TOML stays the safety net, killing the write-only `system_config` drift.
**What+How:** Add a config resolver PEER of `mios_toml.py` that reads `config_kv`, `verb`, `domain_verb`, `recipe` and `routing_phrase` from the DB at runtime, overlay-first through `config_layer` (vendor < host < user < machine), with the existing TOML path as the fail-open fallback. Repoint `verbcatalog.py` and the other config consumers at it and retire the write-only `system_config` dead-drift. Flip authority per-surface only once the read-path, the lossless round-trip and the drift-gate are all green.
**Where:** `usr/lib/mios/mios_toml.py` plus the new DB resolver; `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py`; `usr/libexec/mios/seed-db-config.py`.
**Done When:** Config reads at runtime come from the DB with TOML fail-open proven by stopping pgvector, no consumer still reads `system_config`, and `just drift-gate` plus `test_mios_*` pass.
**Why:** `system_config` is written and never read -- config edits made through the DB path silently do nothing, so the DB looks authoritative while TOML quietly still rules.
**Dep:** After T-242 (lossless round-trip + materialize). Honors WS-NAME aliases and load-bearing legacy verbs -- fold-refactor, never blind-drop.
**Status:** completed (integrated DB config resolver peer into mios_toml) | **Domain:** AI-plane/SSOT/DB | **Who:** agent-pipe backend engineer

## T-244 -- VECTOR-02: V2 AI-plane vectors -- embed skill/verb/tool_call/event/session/directory  (WS-VECTOR | P2 | M)
**Goal:** E-23 DB-driven configuration and vector recall -- recall is a native indexed DB query rather than in-process caches the agent rebuilds each start.
**What+How:** Add `emb vector(768)` plus an HNSW `vector_cosine_ops` index to the `skill`, `verb`, `tool_call`, `event`, `session` and `directory_entry` tables over a text projection of each row, stamping `emb_model`/`emb_version` and filling them off the hot path via the `embed_backfill.py` worker pattern. Then retire the in-process verb-embeddings and apps-embeddings BM25/cosine caches in favour of native `<=>` queries.
**Where:** `usr/share/mios/postgres/schema-init.sql`; the embed-backfill worker and the in-process embedding caches under `usr/lib/mios/agent-pipe/`.
**Done When:** Each listed table carries a populated `emb` with provenance stamped, an HNSW recall query returns the expected rows, the in-process caches are gone, and `just drift-gate` plus `test_mios_*` pass.
**Why:** Recall quality depends on caches rebuilt per process, so results differ between workers and after every restart, and the DB columns that should serve them sit empty.
**Dep:** Not stated in source; sits after T-242/T-243 in the V-series (needs the V0 schema and the V1 read-path).
**Status:** completed | **Domain:** AI-plane/Vectorization | **Who:** agent-pipe backend engineer

## T-246 -- VECTOR-04: V4 accounts -- DB-owned ids, layered prefs, bidirectional write-back  (WS-ACCT | P2 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- the account plane is DB-owned end to end, with no second credential store drifting beside it.
**What+How:** Complete the account plane on the shipped WS-ACCT `account` table: add `home_dir`/`shell`, a `uid_alloc` SEQUENCE with `allocate_uid()`/`allocate_gid()` so ids are DB-owned rather than hand-assigned, and a layer-scoped `account_preference` table (with `emb`) so per-user dotfiles RENDER from the DB and static `etc/skel` can retire. Add bidirectional write-back: Linux pam/getent (NSS from `account` already works) and a Windows SAM watcher extending `MiOS-AccountSync.ps1`. Reconcile the `/etc/shadow` parallel store through pam write-back so the two credential planes cannot diverge.
**Where:** `usr/share/mios/postgres/schema-init.sql`; `automation/17-accounts-db.sh`; `usr/libexec/mios/mios-ai-firstboot` (account seeder); `C:\mios-bootstrap\src\autounattend\MiOS-AccountSync.ps1`; `etc/skel`.
**Done When:** A new account gets its uid from the DB sequence, its dotfiles render from `account_preference` with no `etc/skel` copy, a change made on the OS side flows back into the DB on both platforms, and `just drift-gate` plus `test_mios_*` pass.
**Why:** Ids are hand-assigned and `/etc/shadow` lives outside the DB, so the "DB-driven accounts" model is one-directional -- any OS-side account change silently desynchronizes the SSOT.
**Dep:** After T-242/T-243 (V0/V1). Builds on the shipped WS-ACCT account table and NSS `getpwnam`.
**Status:** in-progress -- the GID allocator bug is FIXED and proven against a live Postgres 16. `allocate_gid()` drew from `uid_alloc`, the same sequence `allocate_uid()` draws from, and mios-account-sync allocates gid before uid -- so a user-private group (uid == gid, the Fedora default `useradd -m` expects) was arithmetically unreachable. GIDs now have their own `gid_alloc` sequence. Reproduced end-to-end: legacy gives alice gid=1001/uid=1000, bob gid=1003/uid=1002; a fresh cluster now gives 1000/1000; an UPGRADED cluster gives 1004/1004 with no collision, because the seeder advances gid_alloc past max(account.gid) only -- advancing past uid_alloc as well would push a fresh cluster's first gid to 1001 and re-break the thing being fixed. STILL OPEN: `materialize-user-config.py` has no invoker and its `accounts.db_render_prefs` gate ships false; `mios_identity.account_preferences` is a second, dead preference table; `etc/skel` is still copied by `useradd -m`, contradicting the render-from-account_preference Done-When. The dead `mios_identity.account_preferences` duplicate is now REGISTERED and gated by the new check_schema_consumers, which names it the trap case: it is one letter from the live `account_preference` that materialize-user-config.py reads, so a writer aimed at the wrong name would look correct and lose every row. Resolve by dropping it or folding the live table into it -- do not leave both. | **Domain:** Accounts/Identity/DB | **Who:** identity/accounts agent

## T-247 -- VECTOR-05: V5 invert authority -- DB is SSOT, mios.toml becomes a generated export  (WS-VECTOR | P3 | L)
**Goal:** E-23 DB-driven configuration and vector recall -- the terminal WS-VECTOR state: one queryable, event-sourced SSOT with TOML as its build-time export.
**What+How:** Flip authority so the DB is the source of truth and `mios.toml` is a generated EXPORT materialized for the next image build. Make the configurator (`mios.html`) CRUD the DB directly, emitting `config_event` rows, and turn install/build/config/account mutations into an append-only event-sourced log with time-travel and rollback aligned to bootc atomic upgrades. Flip one surface at a time, and only after that surface's V1–V4 read-path and drift-gate are green.
**Where:** `usr/share/mios/configurator/mios.html`; `usr/share/mios/postgres/schema-init.sql` (`config_event` + event sourcing); `automation/98-drift-checks.sh`; the DB→TOML materialize tool.
**Done When:** A configurator edit writes the DB and emits a `config_event`, the regenerated `mios.toml` export diffs clean against the DB in the drift-gate, a time-travel rollback restores prior config, and `just drift-gate` plus `test_mios_*` pass.
**Why:** Until authority inverts, every DB capability is a mirror of a hand-edited file -- config has no history, no rollback, and two places a value can be changed.
**Dep:** LAST -- after V0–V4 (T-242, T-243, T-244, T-246) are green per-surface.
**Status:** planned | **Domain:** SSOT/DB/Configurator | **Who:** platform architect

## T-248 -- BAKE-01: Two-gate bake plan — a `core` allow-list baked unconditionally, à-la-carte members gated by enable  (WS-BAKEGATE | P1 | L)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- every published image carries the inference whales no matter how the operator's enable flags are set, while the bake still fits a standard runner.
**What+How:** Phase 0 already sharded the monolithic bound-images `RUN` (which exited 125 on disk-constrained runners) heavy-first into `usr/libexec/mios/mios-bake-group` plus `mios.toml [build].bake_groups` (L8470-8475) and five per-group `RUN`s in `Containerfile` (L181-190, `--mount=type=cache`, never `--squash`). Remaining structural work: add a `[build.bake]` SSOT section holding `core` (a fixed, SSOT-independent membership list), `groups` and `group_members.*`; add `tools/generate-bake-plan.py`, invoked by a new `automation/16-bake-plan.sh` ordered after `15-render-quadlets.sh`, that reads through `usr/lib/mios/mios_toml.py` and writes `/usr/lib/mios/bake/plan.d/NN-<group>.list` — emitting CORE members UNCONDITIONALLY (this generator holds the ONE branch where "core overrides SSOT" lives) and à-la-carte members only when their enable cascade resolves true. Add `.image` Quadlets for the two whales (`mios-llm-heavy.image`, `mios-llm-heavy-alt.image`) symlinked by `automation/08-system-files-overlay.sh` (~L178), a regenerate-and-diff drift-check in `98-drift-checks.sh`, and delete the Containerfile's inline Quadlet `sed`-scraping (Law 7/8).
**Where:** `usr/share/mios/mios.toml` (`[build.bake]`), `tools/generate-bake-plan.py` (new), `automation/16-bake-plan.sh` (new), `automation/08-system-files-overlay.sh`, `automation/98-drift-checks.sh`, `usr/share/containers/systemd/mios-llm-heavy.image` + `mios-llm-heavy-alt.image` (new), `usr/libexec/mios/mios-bake-group`, `Containerfile`
**Done When:** `just drift-gate` regenerates `plan.d/*.list` and diffs clean; the new check FAILS if a whale leaves `core`, if a core member is not fully qualified, or if referenced ⊄ emitted; `grep sed Containerfile` finds no Quadlet scraping.
**Why:** Today the bake membership is decided by inline shell in the Containerfile and by enable flags, so a single flipped flag silently publishes an image with no inference engine, and the unsharded RUN reproducibly exit-125s the runner — both failures only surface after a ~1h bake.
**Dep:** Phase 0 done, structural next; interlocks T-250 (groups collapse toward sys/cuda) and T-251 (digest-free SSOT).
**Status:** completed | **Domain:** Build/Bake | **Who:** build agent

## T-249 -- BLADE-01: Universal-core plus a blade-type activation gate — one image, role chosen by flag  (WS-BLADE | P1 | L)
**Goal:** E-16 The bake plane: what is present in the image, and can a stock runner hold it -- presence (bake) and role (activation) become orthogonal, so one universal image serves every blade type with zero image variants.
**What+How:** Add a `[blade]` SSOT section: `type` archetype (hybrid/compute/endpoint/controller/headless), `[blade.archetypes]` capability expansions, `[blade.requires]` service→capability "nodeSelector" map. Demote `usr/libexec/mios/role-apply` from an imperative actor to a marker-writing resolver that materializes `/etc/mios/blade.d/<cap>` and `/run/mios/blade.env` (autodetect retained). Generate one `usr/share/mios/dropins/blade-<cap>.conf` carrying `ConditionPathExists=/etc/mios/blade.d/<cap>` per capability from `[blade.requires]` (Law-8 generator plus drift-check) and wire it through `automation/41-mios-dropin-fanout.sh`. Deploy-time selection comes from karg `mios.blade=<type>` (generated `usr/lib/bootc/kargs.d/05-mios-blade.toml`), Ignition, Afterburn or autodetect; a `mios blade set|add-capability|status` verb touches markers and daemon-reloads with no reboot. Fold `[profile].role/features` into `[blade]`, add `mios-{compute,endpoint,controller}.target`, add a greenboot check, and keep `[blades.*]`/`[nodes.*]` as the orthogonal fleet-dispatch Axis B.
**Where:** `usr/share/mios/mios.toml` (`[blade]`), `usr/libexec/mios/role-apply`, `usr/share/mios/dropins/blade-<cap>.conf`, `automation/41-mios-dropin-fanout.sh`, `usr/lib/bootc/kargs.d/05-mios-blade.toml`, `usr/lib/systemd/system/mios-{compute,endpoint,controller}.target`, `usr/lib/greenboot/check/required.d/10-mios-role.sh`, `mios blade` verb
**Done When:** From one universal image, `mios-llm-heavy.service` is condition-skipped on a `controller` blade (zero VRAM) and starts on a `gpu-serving` blade; `mios blade add-capability gpu-serving` lights it hot with no reboot; the drop-in generator regenerates byte-identically under the drift-gate.
**Why:** Without an activation axis, role differences force either per-role image variants (breaking the one-image contract) or services that start on hardware that cannot run them, e.g. the heavy LLM unit crash-looping on a GPU-less controller.
**Dep:** Complements T-248 (bake vs activation orthogonality) and T-250 (activation `Condition*` unchanged by consolidation).
**Status:** done | **Domain:** Build/Activation | **Who:** build/systemd agent

## T-250 -- MIOSSYS-01: Collapse the ~18-image sidecar fleet onto the `mios-sys` + `mios-cuda` shared-base lineage  (WS-MIOSSYS | P1 | XL)
**Goal:** E-17 Shared-base consolidation: shrink the sidecar fleet to two lineages -- the bound-image store shrinks enough that a standard GitHub runner can bake and publish as a true equal to Forgejo.
**What+How:** Replace the ~18-image, ~60GB, zero-shared-blob sidecar fleet with two images of one base lineage, both `FROM ${BASE_IMAGE}` (ucore-hci:stable-nvidia): `localhost/mios-sys` (CUDA-free, ~6-8GB, shared python/node/chromium layers) and `localhost/mios-cuda` (shared CUDA/torch/flashinfer layer plus `vllm-venv`/`sglang-venv` and `llama-server`, ~15-18GB). Runtime stays Model A — one IMAGE, many CONTAINERS: shared `Image=`, per-service `Exec=`, and every unit's `User=`/`Group=`/`Condition*` untouched. Add `automation/57-mios-sys-build.sh` plus generated `usr/share/mios/{sys,cuda}/Containerfile`; add `[image.sys]`/`[image.cuda]` blocks; thread `MIOS_SYS_IMAGE`/`MIOS_CUDA_IMAGE` through `tools/lib/userenv.sh` and BOTH allowlists in `automation/15-render-quadlets.sh` (envsubst L73 and the bash fallback ~L87-127) plus `97-ssot-lint.sh`. Each member's Quadlet delta is a pure SSOT edit (repoint `Image=`, add `Exec=`); retarget `[build].bake_groups` to sys/cuda/extra. Migrate in Waves 0-3 (Wave 1 Go-binary tier, Wave 2 interpreted plus k3s/runner binaries, Wave 3 mios-cuda and the DB tier behind a smoke test). Ceph stays a separate image.
**Where:** `usr/share/mios/mios.toml` (`[image.sys]`/`[image.cuda]`/`[build].bake_groups`), `automation/57-mios-sys-build.sh` (new), `usr/share/mios/{sys,cuda}/Containerfile` (generated), `automation/15-render-quadlets.sh`, `automation/14-generate-quadlets.sh`, `automation/97-ssot-lint.sh`, `usr/libexec/mios/mios-bake-group`, `Containerfile`, the ~18 `usr/share/containers/systemd/*.container` members
**Done When:** The bound-image store drops to ~25GB with the largest single commit capped at the ~12GB CUDA/torch group; `generate-pod-quadlets.py --check` validates every regenerated `Image=`/`Exec=`; every `User=` and root exception is byte-identical (Law 6 untouched); a WSL blade still refuses to start pxe-hub even though its binary is now baked.
**Why:** Eighteen unrelated base images share no layers, so the store is ~60GB — over what a stock ubuntu-24.04 runner can hold, which is exactly why `PUBLISH` stays `false` and GitHub is not yet an equal publisher.
**Dep:** Locked ops decisions — newest packages tagged at build; ALL core consolidates; k3s binary consolidated (HA-compatible, privileged activation unchanged) with Pacemaker/corosync HA in CORE; rebuild on CVE/release; mios-cuda bake scope deferred to Wave 3. Enables T-252 GitHub equality; complements T-248 Phase 0 (sharding kept as safety margin).
**Status:** done | **Domain:** Build/Consolidation | **Who:** build agent

## T-251 -- SBOM-01: Extend build-time provenance past images to model and package hashes  (WS-SBOM | P2 | M)
**Goal:** E-15 SBOM and supply-chain hardening as compiled, gated policy -- every digest and checksum is resolved at build and recorded in the SBOM instead of being hand-pinned in SSOT.
**What+How:** All 12 hand-pinned `@sha256` digests were stripped from `mios.toml` (0 remaining) and 27 Quadlets regenerated digest-free, with `mios-bake-group` recording each resolved digest to `/usr/share/mios/artifacts/sbom/bound-images.tsv` (L173-178). Extend the same pattern to non-image artifacts: compute and record SHA-256 for downloaded GGUF models in `automation/38-llamacpp-prep.sh`, Safetensors weights in `automation/38-vllm-prep.sh`, and downloaded binaries/assets in `38-oh-my-posh.sh`, `42-cosign-policy.sh`, `13-ceph-k3s.sh`, `10-gnome.sh` and `09-fonts.sh`, writing to `/usr/share/mios/artifacts/sbom/models.tsv` and `binaries.tsv`, with the digest/checksum drift-checks validating the build-resolved values rather than literals.
**Where:** `automation/38-llamacpp-prep.sh`, `automation/38-vllm-prep.sh`, `automation/38-oh-my-posh.sh`, `automation/42-cosign-policy.sh`, `automation/13-ceph-k3s.sh`, `automation/10-gnome.sh`, `automation/09-fonts.sh`, `automation/98-drift-checks.sh`
**Done When:** No hand-maintained `@sha256` or checksum literal remains in `mios.toml` or in scripts for any runtime-pinned artifact; every resolved hash appears in the SBOM TSVs; the digest/checksum drift-checks pass against build-resolved values.
**Why:** Hand-pinned digests rot silently and reappear as the recurring "broad `git add` strips the pins, pod-quadlets gate turns red" failure, while unhashed model and binary downloads leave the largest artifacts in the image with no provenance at all.
**Dep:** Image side DONE; interlocks T-250 (digest-locks floating `:latest` sources at Wave 0) and T-252 (newest packages, tagged at build).
**Status:** done | **Domain:** SBOM/Provenance | **Who:** build agent

## T-252 -- RELTOP-01: Credential-driven registry selection — GHCR when creds exist, otherwise local/Forgejo  (WS-RELTOP | P2 | S)
**Goal:** E-17 Shared-base consolidation: shrink the sidecar fleet to two lineages -- GitHub and Forgejo become bit-for-bit equal publishers over one build path with no hardcoded registry.
**What+How:** Declare GitHub Actions and the Forgejo runner EQUAL bit-for-bit publishers with a LOCAL-first build. Keep `mios-ci.yml`'s `PUBLISH: 'false'` (L38) as an explicit CAPACITY gate — a stock ubuntu-24.04 runner cannot hold the ~60GB store — controlling the `MIOS_BAKE_BOUND_IMAGES` build-arg (L243) and the rechunk/push/cosign steps (L270+). Wire the registry selection itself ("default to GitHub/GHCR push+pull when credentials are present, else local/Forgejo") into the build driver and `install.env` credential detection through `tools/lib/userenv.sh`, so both CI runners and the local build resolve the target through the one selection path.
**Where:** `.github/workflows/mios-ci.yml`, `.forgejo/workflows/build-mios.yml`, `tools/lib/userenv.sh` / `install.env`
**Done When:** A build with GHCR credentials pushes and pulls GHCR; the same build with no credentials targets local/Forgejo; both CI runners and the local build share one selection code path; no registry hostname is hardcoded outside it.
**Why:** Without credential-driven selection each publisher needs its own hand-edited registry constant, which is how the two workflows drift into publishing different things from the same tree.
**Dep:** CI gate DONE; flipping `PUBLISH:'true'` is unblocked by T-250.
**Status:** done | **Domain:** Release/CI | **Who:** CI/build agent

## T-253 -- DEPRED-01: Collapse Hermes into agent-pipe at `:8640` and retire the redundant sidecars  (WS-DEPRED | P2 | L)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- one OpenAI front door on `ports.agent_pipe`, with every extra AI-plane hop and duplicate datastore removed.
**What+How:** Finish the ~70%-done collapse of MiOS-Hermes (`:8642`) into agent-pipe (`:8640`): (1) repoint `MIOS_AI_ENDPOINT` from `:8642` to `:8640` in `automation/lib/globals.sh:133` and in `mios.toml [ai]`/`[hermes]`, adding `8640` to `[security.nohc_allowlist]`; (2) retire the `:8641` prefilter hop by removing `mios-delegation-prefilter.service`; (3) absorb `gateway_sessions` by porting `usr/lib/mios/gateway-agent/session.py` into agent-pipe with opt-in replay; (4) decide browser/CDP (MCP `browser_*` verbs preferred, keeping `mios-hermes-browser` :9222 as a pure executor); (5) retire or alias `mios-gateway-agent.service`. In parallel, fold the Guacamole DB into pgvector and delete `mios-guacamole-postgres.container`, delete `mios-crowdsec-dashboard.container` and its pin, replace the cockpit-link socat with `systemd-socket-proxyd`, and replace open-webui (`:8033`) with a Quickshell SSE `/v1` client (gate OWUI to `edge-endpoint` first, then remove).
**Where:** `automation/lib/globals.sh`, `usr/share/mios/mios.toml` (`[ai]`/`[hermes]`/`[security.nohc_allowlist]`), `mios-delegation-prefilter.service`, `usr/lib/mios/gateway-agent/session.py`, agent-pipe `server.py`, `mios-hermes-browser.service`, `mios-gateway-agent.service`, `mios-guacamole-postgres.container`, `mios-crowdsec-dashboard.container`, the `mios-cockpit-link` unit
**Done When:** Every front end resolves `MIOS_AI_ENDPOINT` to `:8640`; `:8641`/`:8642` are retired or thin aliases; Guacamole runs on a pgvector DB/role; `mios-crowdsec-dashboard` and `mios-guacamole-postgres` no longer exist; a native SSE client streams `/v1/chat/completions`.
**Why:** Three ports for one AI contract means every consumer has to know which hop to call, a second Postgres duplicates the pgvector store in the bake, and the extra sidecars are pure image weight against the runner capacity limit.
**Dep:** Browser/CDP and the `hermes` CLI/Discord decisions are OPEN QUESTIONS; pairs with T-249 (OWUI gated to edge-endpoint) and T-250 (fewer images to consolidate).
**Status:** done-by-code | **Domain:** AI-plane/Deps | **Who:** agent-pipe backend engineer

## T-254 -- MDRIVE-01: Boot the universal image as a Hyper-V Gen 2 `.vhdx` off `M:` with a sovereign Ceph OSD  (WS-MDRIVE | P1 [VM] | L)
**Goal:** E-20 The bootc-native install legs -- a real bootc-managed MiOS boots from a bootc-cut disk image with a populated `/var`, proving the to-disk leg on operator hardware.
**What+How:** Deploy the universal image as a Hyper-V Generation 2 VM booting a `.vhdx` under `M:\MiOS-images\`, cut by `bootc install`/bootc-image-builder via `just vhdx` (`Justfile:217`), which already factory-populates `/var` and `/var/home` — the fix for the raw `wsl --import` deadlock. Add a `vhdx-m` Justfile recipe and `C:\mios-bootstrap\deploy-mios-hyperv-m.ps1` that loads the tar, cuts the vhdx if absent, creates the VM with `New-VM -Generation 2` off `M:`, sets `Set-VMFirmware -SecureBootTemplate MicrosoftUEFICertificateAuthority`, attaches the Ceph OSD vhdx, adds `netsh portproxy :8640`, and configures DDA/GPU-P. For sovereign storage, add a second dynamic `.vhdx` on `M:` as the single-node Ceph OSD backing `/var/home` (`var-home.mount`, `Type=ceph`), and relax `ConditionVirtualization=no` on `ceph-bootstrap.service`/`mios-ceph-bootstrap.service` to a config-flag gate (`[storage.cephfs].enable` / `/run/mios/ceph-enabled`); the 20GiB ext4 `/var/home` partition carved by `config/artifacts/vhdx.toml` stays as the `nofail` + `ConditionPathExists` fallback. dGPU via DDA is recommended (the iGPU keeps the Windows desktop); WSL2 `--import-in-place` remains an explicitly disposable preview because a bootc image bakes nothing into `/var` (Law 2) — only the installer populates it.
**Where:** `Justfile` (new `vhdx-m`), `config/artifacts/vhdx.toml`, `usr/lib/systemd/system/ceph-bootstrap.service` + `mios-ceph-bootstrap.service`, `usr/libexec/mios/ceph-bootstrap.sh`, `usr/share/mios/mios.toml` (`[storage.cephfs].enable`), `usr/lib/systemd/system-preset/95-mios-wsl.preset` (optional), `C:\mios-bootstrap\deploy-mios-hyperv-m.ps1` (new)
**Done When:** A MiOS Gen 2 VM boots from `M:\MiOS-images\mios-0.3.0.vhdx` with a populated `/var/home`, `bootc status` reports healthy, and `curl http://localhost:8640/v1/models` answers from Windows; with the OSD vhdx and `[storage.cephfs].enable=true`, `findmnt /var/home` reports `type ceph` and survives a root-vhdx rebuild; `bootc upgrade` and `bootc rollback` both work in-guest.
**Why:** Today the only Windows-side path is `wsl --import`, which deadlocks on an unpopulated `/var` and yields a system that is not bootc-managed — so there is no local way to prove an upgrade/rollback cycle before shipping.
**Dep:** Re-establish a Linux podman once (BIB and `bootc install` require it); GPU policy, Ceph-now-vs-later, OSD sizing and `ConditionVirtualization` scope are operator decisions. VM/operator-gated.
**Status:** planned | **Domain:** Deploy/Windows | **Who:** deploy agent

## T-255 -- DOCS: Planning-docs refactor — ADR system, generated index, lean thematic roadmap, Diátaxis  (WS-DOCS | P1 | L)
**Goal:** E-06 Test and documentation harness: negative self-tests, coverage, doc integrity -- an arriving agent can start any workstream cold from ONE self-contained file.
**What+How:** Consolidate planning docs into AI-agent-native form matching upstream patterns (MADR ADRs, KEP-style WS metadata, Diátaxis, Keep-a-Changelog + SemVer, an OpenAI-Model-Spec-style rules doc, `llms.txt`/`AGENTS.md`). Ship the ADR system under `usr/share/doc/mios/adr/` (README plus ADR-0001..0007, one backing every Part-21 workstream, governance recorded in ADR-0007); make `tools/roadmap-index.py` the generator for the roadmap index and the MiOS Spec, gated by a regenerate-and-diff check in `automation/98-drift-checks.sh` that also fails on a bad ADR, law or `ssot_key` reference; reduce `ROADMAP.md` to a theme-grouped active-only file (~≤600 lines) with Parts 1-20 archived losslessly under `usr/share/doc/mios/roadmap/history/`; retag any workstream marked `done` that is actually gated-off or never fired; and route agents through Diátaxis quadrants plus `llms.txt`/`AGENTS.md`.
**Where:** `usr/share/doc/mios/adr/*`, `tools/roadmap-index.py`, `automation/98-drift-checks.sh`, `ROADMAP.md`, `TASKS.md`, `usr/share/doc/mios/roadmap/history/*`, `CHANGELOG.md`, `llms.txt`, `AGENTS.md`
**Done When:** `just drift-gate` regenerates the roadmap index and the MiOS Spec byte-identically and fails on a bad ADR/law/`ssot_key` ref; the ToC lists all Parts; `ROADMAP.md` is active-only with Parts 1-20 archived and no workstream lost; no workstream is tagged `done` while gated off; the Diátaxis quadrants plus `llms.txt` route an agent to any workstream in ≤3 hops.
**Why:** A multi-thousand-line unstructured roadmap forces every new agent to re-derive context, and decisions with no ADR get silently re-litigated or reversed by the next session.
**Dep:** DOCS-01 done → DOCS-02 (schema + generator) → DOCS-03 (lean roadmap + archive) → DOCS-04 (retag) + DOCS-05 (Diátaxis) + DOCS-06 (MiOS Spec).
**Status:** done | **Domain:** Docs/Meta | **Who:** docs/tooling agent

## T-256 -- CAT-01: Flatten MiOS-Cat to a single owner — `mios-bootstrap` owns `cat/`  (WS-CAT | P1 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- the installer lives in exactly one repo at one shallow path, so there is one thing to fix when the deploy plane breaks.
**What+How:** Make `mios-bootstrap` the single canonical owner of MiOS-Cat at `C:\mios-bootstrap\cat\`. `git mv` the 3-5-level-deep `C:\mios-bootstrap\src\autounattend\medicat_installer\` nest up to `cat\`: launchers to `cat\`, FileChecker/hasher/bin/7z to `cat\lib\`, resources to `cat\resources\`, the Windows-ISO subsystem (`New-MiOSISO`, `mios-uup-fetch`, `New-MiOSAutounattend`, `Build-MiOSXboxISO`, `MiOS-Provision.lib`) to `cat\iso\`, translations to `cat\i18n\`. Then DELETE the byte-identical `C:\MiOS\src\autounattend\medicat_installer\` copy (`diff -q` confirms it is empty of differences) after verifying no live consumer — the flatten-campaign guardrail. This satisfies Law 1 (`C:\MiOS/usr/` IS `/usr`; a host installer must not live under it) and the two-repo no-double-track rule. This task captures the planned move; do not run destructive git operations as part of the decision capture.
**Where:** `C:\mios-bootstrap\cat\**` (new home), `C:\mios-bootstrap\src\autounattend\medicat_installer\**` (move source), `C:\MiOS\src\autounattend\medicat_installer\**` (delete)
**Done When:** One MiOS-Cat home exists at `cat\`; `C:\MiOS` contains no installer tree; a cross-repo `diff` finds no `medicat_installer` duplicate; the deepest path drops from `src\autounattend\medicat_installer\resources\ventoy\` to `cat\resources\ventoy\`.
**Why:** Two byte-identical installer copies in two repos mean every fix must be applied twice or the deployed stick silently runs the stale one, and the copy under `C:\MiOS/usr`-adjacent source violates Law 1.
**Dep:** First WS-CAT task; unblocks T-257/T-258/T-259. Verify-no-consumer gate before any delete.
**Status:** planned -- **NOT COMPLETABLE IN mios.git.** Every path in its Where line is `C:\mios-bootstrap\...` -- the move of `medicat_installer` into `cat/` and the retirement of `installation/MiOS-Cat.bat` both happen THERE. mios.git has no `cat/` tree to flatten (only the single `cat/loopback.cfg`, itself a candidate double-track). Tracked here because mios.toml is the shared cross-repo SSOT (Law 15); execute in mios-bootstrap.git. | **Domain:** Deploy/Cat | **Who:** deploy/installer agent

## T-257 -- CAT-02: One verb vocabulary across the tri-launcher, with all logic in `cat\lib\`  (WS-CAT | P1 | L)
**Goal:** E-21 One deploy front door: flatten every install path -- `cat <verb>` means exactly the same thing in PowerShell, sh and cmd, with zero duplicated business logic.
**What+How:** Give `cat\MiOS-Cat.{ps1,sh,bat}` one shared verb set — **stage · install · build · update · provision · manual** — implemented as a thin `switch`/`case`/`goto` dispatch, with every piece of business logic moved into a shared `cat\lib\` (a PowerShell module plus a bash lib). Port the advanced logic currently living only in the `.bat` (MiOS-Repo staging, WinPE DISM injection, git-pull self-update) into the canonical `.ps1` so the launchers reach parity (Law 9), then reduce the `.bat` to a WinPE/legacy-cmd shim that calls the `.ps1` whenever PowerShell is available. Demote every existing entry point (`Get-MiOS.ps1` `irm|iex`, the bootstrap curl, the UUP/autounattend ISO pipeline, `mios-kickstart.cfg`, the `just` build) to a verb back-end rather than a peer launcher, and make the interactive menu the no-verb default (`cat` opens the menu, `cat install` runs headless).
**Where:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh,bat}`, `C:\mios-bootstrap\cat\lib\MiOS-Cat.psm1` + `cat.sh` (new), the per-verb back-end shims into `cat\iso\` / `just` / bootstrap
**Done When:** `cat install` is headless-identical across `.ps1`, `.sh` and `.bat`; no business logic is duplicated between launchers; the no-verb invocation opens the menu; the `.bat` is a reduced WinPE shim.
**Why:** The three launchers currently implement different feature sets, so which one the operator happens to run decides whether staging, DISM injection and self-update happen at all.
**Dep:** After T-256 (single home). Pairs with T-259 (web one-liners fold into `cat install`).
**Status:** planned -- **NOT COMPLETABLE IN mios.git.** `bootstrap.ps1` <-> `Get-MiOS-Backend.ps1` <-> `MiOS-Cat.ps1` and the bash twin are all bootstrap files; the verb dispatcher and tri-launcher parity are bootstrap work. Tracked here because mios.toml is the shared cross-repo SSOT (Law 15); execute in mios-bootstrap.git. | **Domain:** Deploy/Cat | **Who:** deploy/installer agent

## T-258 -- CAT-03: Add the `[cat]` SSOT block and fix the dangling `drivepath`/`medicatver`/`cache_path` reads  (WS-CAT | P1 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- the installer reads its values from the real SSOT instead of silently falling back to hardcoded defaults.
**What+How:** MiOS-Cat today opens `..\..\..\..\mios.toml` (the 63 KB root seed copy) and looks for `drivepath`, `medicatver` and `cache_path` — keys that exist in NO `mios.toml` — so it quietly uses hardcoded defaults, violating Law 7 NO-HARDCODE and Law 8 SSOT-PROJECTION. Add a `[cat]` block to the real SSOT at `usr/share/mios/mios.toml` carrying `drivepath`, `medicatver`, `cache_path`, `repo_partition.label = "MiOS-Repo"`, `data_partition.label = "MiOS-Data"`, `data_partition.min_disk_gb = 512` and `models` (a reference to `[ai].bake_models`). Repoint MiOS-Cat to resolve the 597 KB SSOT through the shared `mios_toml` resolver rather than the seed, and add a check in `automation/98-drift-checks.sh` asserting the `[cat]` and `[colors]` reads actually resolve.
**Where:** `usr/share/mios/mios.toml` (new `[cat]` block), `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` + `cat\lib\` (SSOT resolve), `automation/98-drift-checks.sh` (new check)
**Done When:** No MiOS-Cat value that has an SSOT home is hardcoded; the `[cat]` and `[colors]` reads resolve against `usr/share/mios/mios.toml`; the drift-check fails when a `[cat]` key is missing.
**Why:** Every operator edit to those keys is a no-op today — the installer reads a file that does not define them and stages to a baked-in default drive and version, with no error to signal it.
**Dep:** After T-256. Interlocks with T-266 (seed-copy provenance) — confirm the 63 KB→597 KB relationship before repointing.
**Status:** planned | **Domain:** Deploy/Cat/SSOT | **Who:** SSOT/installer agent

## T-259 -- CAT-04: Fold the web one-liners (`irm|iex` ⇄ `curl`) into `cat install`  (WS-CAT | P1 | M)
**Goal:** E-21 One deploy front door: flatten every install path -- one native web-pulled entry that hands into the single guided installer from either shell.
**What+How:** Collapse the bodies of `C:\mios-bootstrap\{Get-MiOS,bootstrap,install}.ps1` and `bootstrap.sh` into thin `cat install` shims while keeping the published one-liner URLs stable. Wire the bidirectional handoff so `irm …/cat | iex` (Windows) and `curl -fsSL …/cat.sh | sh` (Linux/WSL) are the SAME front door reached from two shells: the `.ps1` shells out to the curl path for a Linux/WSL target (`wsl -e sh -c 'curl … | sh'`), and the `.sh` invokes `pwsh`/`powershell.exe` for a Windows-side action (Hyper-V VM create, WinPE). Both resolve the same `[cat]` SSOT and the same verb set, satisfying Law 9 ONE-CANONICAL-NAME on the entry surface.
**Where:** `C:\mios-bootstrap\{Get-MiOS,bootstrap,install}.ps1`, `C:\mios-bootstrap\bootstrap.sh`, `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}`
**Done When:** `irm …/cat | iex` and `curl …/cat.sh | sh` reach an identical verb set; `cat install` means the same thing regardless of shell; the legacy scripts are thin shims rather than peer implementations.
**Why:** Four independent bootstrap bodies drift apart and `Get-MiOS`'s `irm|iex` path currently orphans MiOS-Cat entirely, so the shell the operator happens to use changes what actually gets installed.
**Dep:** After T-257 (verb dispatch exists). Published `irm`/`curl` URLs stay unchanged.
**Status:** planned -- **NOT COMPLETABLE IN mios.git.** The `irm|iex` one-liners and their fold into `cat install` are bootstrap-owned. Tracked here because mios.toml is the shared cross-repo SSOT (Law 15); execute in mios-bootstrap.git. | **Domain:** Deploy/Cat | **Who:** deploy/installer agent

## T-260 -- CATREPO-01: Always-present small `MiOS-Repo` shadow-config partition plus the kickstart path fix  (WS-CATREPO | P1 | L)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- the USB shadow-config partition becomes the offline embodiment of the shareable open→configure→deploy link.
**What+How:** Populate a SMALL, always-present `MiOS-Repo` partition (P3, target ≤~16 GB) with the shadow-config brain: `mios.toml` (SSOT), `mios.html` (configurator), the MiOS Portal assets, a self-contained MiOS-Cat copy, and a small repos-clone of config/source (NOT the binary payload). Each payload class degrades open — online `git clone`, offline `robocopy`/`cp -r` from `MiOS-Repo/repos/`. Fix the kickstart path mismatch: the `.bat` stages repos to `%repodrive%:\mios-bootstrap` while `mios-kickstart.cfg` looks under `/mnt/usb/ventoy/repo/mios-bootstrap`; align both to one canonical `MiOS-Repo/repos/` and update the kickstart `%post`. Ventoy-bootable ISOs/WIMs stay on the Ventoy data partition, not P3. The 78 GB OCI tar, `just all` artifacts, model weights and package mirrors explicitly do NOT go here — they belong to MiOS-Data (T-261).
**Where:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage`), `usr/share/mios/mios.toml` (`[cat].repo_partition`), `…\resources\ventoy\mios-kickstart.cfg` (`%post` repo path), the `MiOS-Repo/` layout
**Done When:** A small stick carries the shadow-config brain (mios.toml + mios.html + Portal + MiOS-Cat + a small repos-clone) and fits any USB; a fully offline bare-metal kickstart install succeeds sourcing from `MiOS-Repo/repos/`; the kickstart repo path matches what the stager writes.
**Why:** The stager and the kickstart disagree on where repos live, so the offline `%post` finds nothing and the install falls back to network — the exact failure that makes the bare-metal leg unusable without egress.
**Dep:** After T-256/T-258 (single home plus `[cat]` SSOT). Sibling of T-261 (bulk store).
**Status:** planned | **Domain:** Deploy/Cat/Repo | **Who:** deploy/installer agent

## T-261 -- CATREPO-02: Separate `MiOS-Data` bulk store on large disks — OCI tar plus `just all` artifacts  (WS-CATREPO | P1 | L)
**Goal:** E-20 The bootc-native install legs -- a blank machine installs fully offline from a local OCI tarball on USB media.
**What+How:** On disks ≥128 GB only (gated by a `Get-Disk` size check), have `cat stage` create a SEPARATE `MiOS-Data` store carrying the bulk payload: the ~78 GB `podman save` of `localhost/mios:latest` for offline `podman load`, and the `just all` disk artifacts (`raw`/`iso`/`qcow2`/`vhdx`/`wsl2`, including the ADR-0005 `mios-<ver>.vhdx`). Degrade open: online `podman pull ghcr.io/mios-dev/mios`, offline `podman load MiOS-Data/images/*.tar`. Keep MiOS-Data physically distinct from the always-present small MiOS-Repo (T-260) so a small stick still deploys network-degraded while a 128 GB+ stick is fully offline.
**Where:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage` — `Get-Disk` gate plus `podman save`/copy), `usr/share/mios/mios.toml` (`[cat].data_partition`: `label`, `min_disk_gb = 128`), `MiOS-Data/images/`, the `just all` artifact paths (`M:\MiOS-images\`)
**Done When:** On a 512 GB+ disk, MiOS-Data is created separately from MiOS-Repo and an offline `podman load` plus `bootc switch` from USB succeeds; on a smaller disk MiOS-Data is skipped and only the small MiOS-Repo is written.
**Why:** With no local image store, a bare-metal install must pull ~78 GB over the network — so the "offline sovereignty" claim fails at exactly the sites that need it, and stuffing the tar onto the small partition makes the stick unwritable to ordinary USB media.
**Dep:** After T-260 (repo layout) and WS-BAKEGATE (defines which artifacts exist). Precedes T-262/T-263 (models and mirrors also live on MiOS-Data).
**Status:** planned | **Domain:** Deploy/Cat/Repo | **Who:** deploy/installer agent

## T-262 -- CATREPO-03: Model embedding on MiOS-Data plus `cat provision` (Law 12 offline)  (WS-CATREPO | P1 | L)
**Goal:** E-20 The bootc-native install legs -- the heavy inference lane comes up on a freshly installed host with zero network.
**What+How:** Read the models from SSOT, never invent them (Law 8): `[ai].bake_models` GGUF CSV (L5744) plus fleet tags (L6116), `[ai.vllm].bake_model` (L6724, `Qwen3-30B-A3B-Instruct-2507-AWQ`, ~16 GB) and `[ai.sglang].bake_model` (L6742). On the 512 GB+/MiOS-Data path, `cat stage` fetches each from Hugging Face into `MiOS-Data/models/` and verifies by checksum using the WS-SBOM resolved-not-hardcoded pattern from `automation/38-llamacpp-prep.sh`, turning the store into an offline HF mirror. `cat provision` then copies them into the deployed host offline: GGUFs into the llama.cpp model dir and the AWQ weights into `/usr/share/mios/vllm/model`, whose `config.json` is the `mios-llm-heavy` activation gate. This realizes Law 12 BAKE-NOT-FETCH as offline provisioning — the OCI image bakes engines only, MiOS-Data is the weight store. Model-redistribution licensing is an OPEN QUESTION (ADR-0008): if redistribution is disallowed, store a fetch-manifest plus checksums instead of the weights.
**Where:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage`/`cat provision`), `usr/share/mios/mios.toml` (`[ai].bake_models` L5744/L6116, `[ai.vllm].bake_model` L6724, `[ai.sglang].bake_model` L6742, `[cat].models`), `MiOS-Data/models/`, `/usr/share/mios/vllm/model` (provision target), `automation/38-llamacpp-prep.sh` (checksum pattern)
**Done When:** A deployed host's heavy lane starts with ZERO network because `/usr/share/mios/vllm/model/config.json` is present; the GGUFs and AWQ weights are provisioned offline from MiOS-Data; every model's checksum is verified against a build-resolved value rather than a hardcoded one.
**Why:** Without a weight store the engines ship but the models do not, so an air-gapped install boots an AI OS whose heavy lane is permanently condition-skipped.
**Dep:** After T-261 (MiOS-Data store exists). The model-redistribution decision gates whether weights or a manifest are stored.
**Status:** planned | **Domain:** Deploy/Cat/Models | **Who:** deploy/AI-plane agent

## T-263 -- CATREPO-04: Offline dnf/flatpak/pip mirrors on MiOS-Data plus `cat update` self-refresh  (WS-CATREPO | P2 | M)
**Goal:** E-20 The bootc-native install legs -- package resolution during an offline build or first boot comes from USB, with no external egress.
**What+How:** Build the offline package mirrors into `MiOS-Data/` on the 512 GB+ path: **dnf** via `reposync` plus `createrepo_c`, referenced by a kickstart `repo --baseurl=file://…`; **flatpak** via `flatpak create-usb` or an OCI bundle; **pip** via a `pip download` set or `bandersnatch` for the agent venvs. Each degrades open — live mirror when online, `file://` mirror when offline. Extend `cat update` to re-pull every payload class when online (repos, OCI image, models, mirrors) and re-stamp `MiOS-Data/manifest.json` with payload version and checksums so a deployed host can tell whether its store is current.
**Where:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat update` / mirror build), `MiOS-Data/{dnf,flatpak,pip}/`, `MiOS-Data/manifest.json`, `…\resources\ventoy\mios-kickstart.cfg` (`repo --baseurl=file://`), `usr/share/mios/mios.toml` (`[desktop].flatpaks` source list)
**Done When:** An offline build or first boot resolves all dnf, flatpak and pip packages from USB; `cat update` refreshes the store and re-stamps `manifest.json` when online.
**Why:** Even with the image and models local, first boot still reaches out for flatpaks and pip wheels, so an air-gapped install lands half-configured with no signal about how stale its store is.
**Dep:** After T-261 (MiOS-Data store). Lowest-urgency Tier-B item.
**Status:** planned | **Domain:** Deploy/Cat/Mirrors | **Who:** deploy/build agent

## T-264 -- CATFLAT-01: Dead-weight purge — leave nothing behind in the bootstrap root  (WS-CATFLAT | P2 | S)
**Goal:** E-21 One deploy front door: flatten every install path -- `cat/` tracks source only, so the installer repo is small enough to clone onto a stick.
**What+How:** After verifying no live consumer (the flatten-campaign guardrail), purge tracked cruft from the bootstrap root: `Get-MiOS.ps1.bom-bak`, `commit.patch` / `commit_a8faad4.patch` / `commit_else.patch` / `commit_skip.patch`, `temp.txt`, `temp2.txt` and `scratch.ps1` (~606 KB), and fold `R-DH-BOOTSTRAP-AUDIT.md` in if it is already absorbed. Drop the committed bundled binaries — the ~23 GB MediCat 7z, the Ventoy release zips and `bin\*.exe` — because they are downloaded artifacts, not source, while keeping the fetch-on-demand logic the `.bat` already implements (it curls Ventoy and 7z). Fold the MediCat i18n set down to MiOS strings only.
**Where:** `C:\mios-bootstrap\*.{patch,txt,ps1,bom-bak}` (cruft), `C:\mios-bootstrap\cat\` (bundled binaries, i18n), the `.bat` fetch-on-demand logic (keep)
**Done When:** `cat/` tracks source only; ~6 MB+ of tracked cruft no longer exists; the committed Ventoy/7z/MediCat binaries are gone while fetch-on-demand still succeeds end to end.
**Why:** Committed multi-GB binaries and stray patch/scratch files make the installer repo slow to clone and leave four abandoned patch files that a future agent will read as live state.
**Dep:** After T-256 (single-owner flatten). Verify-no-consumer before each delete.
**Status:** planned -- **NOT COMPLETABLE IN mios.git.** The bundled binaries to purge (`installation/bin/{7z.exe,7z.dll}`) are a bootstrap-owned double-track sitting in this tree; deleting them is the bootstrap repo's call under Law 15. Tracked here because mios.toml is the shared cross-repo SSOT (Law 15); execute in mios-bootstrap.git. | **Domain:** Deploy/Cat/Flatten | **Who:** cleanup agent

## T-265 -- CATFLAT-02: Generated ADR root breadcrumb plus spec cross-reference  (WS-CATFLAT | P2 | S)
**Goal:** E-06 Test and documentation harness: negative self-tests, coverage, doc integrity -- an agent landing in either repo root reaches the decision record in two hops.
**What+How:** Keep the ADRs baked at `usr/share/doc/mios/adr/` per Law 1 — a running MiOS carries its own *why* — and do NOT move them to `/etc` or a repo root. Instead satisfy "ADRs near the system root" with a breadcrumb generated from SSOT (Law 8, drift-checked, never hand-maintained): `C:\MiOS\ADR.md` as a pointer/index rendered by the `roadmap-index.py`-class generator, and `C:\mios-bootstrap\cat\ADR-0008.md` as a generated copy/symlink of the MiOS-Cat record so the installer repo is self-documenting. Link both from `llms.txt` and `AGENTS.md`.
**Where:** `C:\MiOS\ADR.md` (generated), `C:\mios-bootstrap\cat\ADR-0008.md` (generated copy/symlink), `usr/share/doc/mios/adr/` (unchanged, baked), `llms.txt`, `AGENTS.md`, the breadcrumb generator
**Done When:** An agent reaches the ADR index from either repo root in ≤2 hops; the breadcrumb regenerates byte-identically with the drift-gate green; the baked ADRs under `/usr` are unmoved.
**Why:** ADR-0008 governs the whole MiOS-Cat campaign but lives four directories deep in the other repo, so installer work gets done without ever reading the decision it must honor.
**Dep:** After T-256. Complements T-255 (the roadmap-index generator class).
**Status:** planned | **Domain:** Deploy/Cat/Docs | **Who:** docs/tooling agent

## T-266 -- CATFLAT-03: `mios.toml` seed-copy consolidation — flag the duplicates, then fix them  (WS-CATFLAT | P3 | M)
**Goal:** E-09 One value, one name: the full de-duplication campaign -- exactly one authoritative `mios.toml`, with any remaining copy explicitly generated and gated.
**What+How:** Settle the seed-copy question: the SSOT is `C:\MiOS\usr\share\mios\mios.toml` (597 KB), while `C:\MiOS\mios.toml` (63 KB) and `C:\mios-bootstrap\mios.toml` (68 KB) are seed/derived copies. Determine which is canonical versus generated, document the seed→SSOT relationship, and — if the seeds are generated — wire their regeneration plus a drift-check that fails on seed↔SSOT divergence. MiOS-Cat must read ONLY the 597 KB SSOT, which pairs directly with T-258; this duplication is the root cause of the T-258 dangling-read bug, so confirm the relationship before or alongside repointing.
**Where:** `C:\MiOS\usr\share\mios\mios.toml` (SSOT), `C:\MiOS\mios.toml` + `C:\mios-bootstrap\mios.toml` (seeds), the seed generator if one exists, `automation/98-drift-checks.sh`
**Done When:** One documented SSOT exists with explicitly-generated seeds (or a documented decision to keep them as-is); MiOS-Cat reads only the 597 KB SSOT; a drift-check guards seed↔SSOT drift.
**Why:** Three `mios.toml` files at three sizes and conflicting versions mean a consumer that resolves the 7x-smaller copy silently reads stale values — the observed cause of MiOS-Cat's hardcoded-default fallback.
**Dep:** Pairs with T-258 (SSOT repoint). Lowest priority — T-258 can land with a documented assumption and this closes it.
**Status:** done-by-code | **Domain:** Deploy/Cat/SSOT | **Who:** SSOT agent

## T-267 -- CONFIG-01: Fold `mios.html` into the MiOS Portal at `:8640/` — one web and API front door  (WS-CONFIG | P1 | L)
**Goal:** E-11 Unified config surface: mios.toml, the configurator and the Portal are one door at :8640/ -- a shareable link, a USB disk and a usable computer are the whole deployment kit.
**What+How:** Fold the standalone configurator `usr/share/mios/configurator/mios.html` INTO the MiOS Portal as a configurator *view*, so `mios.toml`, `mios.html` and the Portal are ONE config surface served at `:8640/` by agent-pipe: `GET /` serves the Portal with the configurator folded in and `/v1/*` serves the OpenAI API from the SAME front door (the ADR-0006 convergence). Wire the configurator view's read/write of `mios.toml` through `usr/lib/mios/agent-pipe/mios_portal.py`, addressing values by key and never by literal (Law 7) and projecting through the shared resolver (Law 8). "The Portal needs config too" resolves as: it is configured through the surface it is. The Portal at `:8640/` (or its `[portal].public_host` hosted equivalent) is the shareable link that bootstraps open → configure → deploy, and the USB MiOS-Repo shadow-config (T-260 / ADR-0008) is its offline embodiment.
**Where:** `usr/lib/mios/agent-pipe/mios_portal.py` (configurator view plus `mios.toml` read/write), `usr/lib/mios/agent-pipe/server.py` (`GET /` plus `/v1/*` one door), `usr/share/mios/portal/` (absorbs the configurator UI), `usr/share/mios/configurator/mios.html` (folded in / standalone retired), `usr/share/mios/mios.toml [portal]` (L220), `tools/mios-portal-app/` (Android client points at the same `:8640/`)
**Done When:** The configurator is a view inside the Portal at `:8640/`; `GET /` and `/v1/*` share the one door; every deployment type's config reads and writes `mios.toml` through that surface; the shareable link and the USB present the same surface online and offline.
**Why:** A standalone HTML configurator that edits a file nobody else reads is a second config path around the SSOT — the operator configures one thing and the running system honors another.
**Dep:** No hard dependency (the Portal and `:8640` `/v1` already exist). Converges with T-253 (the single `:8640` front-door collapse); governed by ADR-0007.
**Status:** done-by-code (audited) -- one FastAPI app serves both doors: `portal_router` is mounted at `server.py:4207`, with `/`, `/configure` and `/portal/configurator` (which reads MIOS_CONFIGURATOR_HTML at request time and injects the [colors] theme). GET/POST `/portal/config` validate-then-write the user layer and background-reseed the DB. Port prose needs repointing: the door is the `agent_pipe` key (8700); 8640 is in `[docs].retired_ports`. The standalone .desktop entry is retained by design. | **Domain:** Config/Portal | **Who:** agent-pipe / Portal backend engineer

## T-268 -- DEBT-01: Collapse the version/SSOT triplication to one projected token (TD-2)  (WS-DEBT | P1 | M)
**Goal:** E-02 Technical-debt retirement: the TD-1..TD-8 register -- the version literal is single-sourced so no build can resolve a stale copy.
**What+How:** Kill the measured triplication: there are 3× `mios.toml` — canonical `usr/share/mios/mios.toml` (10,869 lines) plus two diverged roots, `C:\MiOS\mios.toml` (claiming **0.2.4**) and `C:\mios-bootstrap\mios.toml` — while `VERSION` and SSOT `mios_version` both say **0.3.0**, compounded by **37× hardcoded `v0.2.4`** and 29× `v0.2.0` in `automation/*.sh` headers. Collapse to one projected token: strip the literal `vX.Y.Z` from every script header and project it from `[meta].mios_version` at render time (Law 7); make the two root `mios.toml` files generated projections of the SSOT (or delete them), documenting the seed→SSOT relationship alongside T-266; and add two drift-checks — "no literal version in headers" and "root `mios.toml` ⊆ SSOT". Near-zero risk, highest reach, and it directly closes the Law 9 / ADR-0009 violation. Do NOT touch `cat\MiOS-Cat.bat`/`.ps1` — a concurrent agent owns those.
**Where:** `C:\MiOS\VERSION`, `C:\MiOS\mios.toml`, `C:\mios-bootstrap\mios.toml`, `C:\MiOS\usr\share\mios\mios.toml` (`[meta].mios_version`), all `automation/*.sh` headers, `automation/98-drift-checks.sh` (two new checks)
**Done When:** One authoritative version token exists; no literal `v0.2.4` or `v0.2.0` remains in any `automation/*.sh` header; the two root `mios.toml` files are generated-or-deleted and drift-gated as `root ⊆ SSOT`; a build can no longer resolve a stale copy.
**Why:** A build that resolves the 7×-smaller root copy ships a manifest stamped 0.2.4 from a 0.3.0 tree, and 66 hardcoded version headers guarantee the next release bump is a partial one.
**Dep:** Phase −1, near-zero risk; unblocks WS-LANG (T-272) and the rest of WS-DEBT. Interlocks with T-266 (seed-copy provenance).
**Status:** done-by-code | **Domain:** Build/SSOT/Version | **Who:** SSOT/build agent

## T-269 -- DEBT-02: shellcheck CI gate plus elimination of the 9 `eval`-on-agent-args verbs (TD-1)  (WS-DEBT | P1 | M)
**Goal:** E-02 Technical-debt retirement: the TD-1..TD-8 register -- the agent-facing OS-control plane carries no shell-injection surface and the repo's shell conventions are machine-enforced.
**What+How:** Enforce the conventions the repo documents but never gates. (1) Add a `shellcheck -S warning` CI job over `automation/` and `usr/libexec/mios/` bash — today `shellcheck` appears only as `# shellcheck source=` comments with no lint job anywhere — plus a `just shellcheck` recipe. (2) Enforce `set -euo pipefail` on the **23 runtime verbs** that currently have no `set -e`. (3) Audit and eliminate the **9 verbs that `eval` on agent-derived arguments**, replacing each `eval` with an explicit arg-array dispatch or a `case` allowlist. This is TD-1, the top-ranked debt, spanning build, runtime and the agent-facing surface.
**Where:** `.github/workflows/mios-ci.yml` (new shellcheck job), `Justfile` (a `just shellcheck` recipe), the 23 unguarded and 9 `eval`-using verbs under `usr/libexec/mios/mios-*`
**Done When:** CI fails on a shellcheck warning; the 23 verbs carry `set -euo pipefail`; **zero** verbs `eval` on agent-derived args; every former `eval` site is an explicit allowlisted dispatch.
**Why:** An autonomous agent can already pass a crafted argument into nine verbs that `eval` it as shell on the OS-control plane, and 23 verbs continue past an error because they never set `-e`.
**Dep:** Phase −1, no new toolchain required. Interlocks with T-272 (the Rust verb-dispatcher port removes the `eval` surface structurally).
**Status:** done-by-code | **Domain:** Build/Security | **Who:** build/security agent

## T-270 -- DOTFILES-01: `[dotfiles.registry.*]` plus `mios-dotfiles-render`, an `apply` verb and both-sides gating  (WS-DOTFILES | P1 | L)
**Goal:** E-22 Dotfiles projection: one engine, every surface, both platforms -- mios.toml becomes the cross-platform system dotfiles, projected and drift-gated on Linux and Windows alike.
**What+How:** Generalize the already-landed palette+btop projection (where `usr/libexec/mios/mios-theme-render` gained a settings-surface concept, `[btop]`'s ~60 keys project the whole `etc/btop/btop.conf` on both platforms, and drift-check 25 `check_theme_projection` auto-extended and is green). (1) Promote the hardcoded Python `SURFACES` dict into an SSOT-authored `[dotfiles.registry.<surface>]` map with per-platform `target.<os>`, a `kind` axis (template / json-merge / registry / command / skip), `format`, `sources`, `platforms` and `condition`, transcribing the existing color and btop surfaces first as a pure refactor with check 25 staying green. (2) Fork `mios-theme-render` into `mios-dotfiles-render`: registry loaded via `mios_toml.load_merged()`, arbitrary `@MIOS:<section>.<key>@` tokens, format-aware merge that splices the MiOS block without clobbering foreign keys (Windows Terminal, VS Code `settings.json`), per-platform target resolution, and new `apply`/`diff` verbs that write to live HOME (`~/.config`, `%USERPROFILE%`, `%LOCALAPPDATA%`). (3) Add the `[shell]`, `[editor]`, `[git]`(→`[identity]`, Law 9) and `[ssh]` (`secret_ref` only — raw keys never in SSOT) domains. (4) Generalize check 25 into `check_dotfiles_projection` over the full registry, add the Windows runtime half `Test-MiOSProjection`, collapse the scattered `Install-MiOS*` bodies into thin registry-driven `Sync-MiOSDotfiles` calls, and add a `mios dotfiles apply/diff/drift` verb (`[verbs.dotfiles_*]`).
**Where:** `usr/share/mios/mios.toml` (`[dotfiles.registry.*]`, `[shell]`/`[editor]`/`[git]`/`[ssh]`; existing `[colors]`/`[theme]`/`[appearance]`/`[terminal]`/`[identity]`/`[btop]` remain as content), `usr/libexec/mios/mios-theme-render` (forks to `mios-dotfiles-render`, kept as a back-compat alias), `usr/libexec/mios/mios-sync-theme`, `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh`, `automation/98-drift-checks.sh` (check 25 → `check_dotfiles_projection`), `C:\mios-bootstrap\Get-MiOS.ps1` (`Sync-MiOSDotfiles`/`Test-MiOSProjection`), `usr/bin/mios`
**Done When:** The color and btop surfaces are registry-driven with check 25 green; editing `[theme].opacity` projects to the Linux CSS, the Windows Terminal `json-merge` block and the WSL bridge with foreign keys intact and both gates passing; `mios dotfiles apply` writes live HOME; no `Install-MiOS*` value that has an SSOT home is hand-typed.
**Why:** The surface list is a hardcoded Python dict today, so adding a dotfile means editing the engine rather than the SSOT, the Windows half has no gate at all, and nothing reaches live HOME — the operator's actual config stays untouched by the projection.
**Dep:** No hard dependency (palette and btop already landed). Interlocks with T-267 (the Portal edits the registry map) and ADR-0005/0008 (the overlay carries across deployments). OPEN QUESTIONS: per-platform secrets store; a deployment-type enum for `condition` (ADR-0010).
**Status:** done-by-code | **Domain:** Dotfiles/SSOT | **Who:** SSOT/theme agent

## T-271 -- TEMPLATE-01: Compiled file-pattern system, `mios new`, a conformance check and candidate Law 14  (WS-TEMPLATE | P1 | L)
**Goal:** E-04 One template per file type + the `mios new` scaffolder -- an agent learns MiOS formatting from a handful of templates, and non-conformant new files fail the build.
**What+How:** Author ~15 templates under `usr/share/mios/templates/` (`bash`, `python-tool`, `python-module`, `rust`, `typescript`, `powershell`, `toml-config`, `yaml`, `json-schema`, `markdown-doc`, `adr`, `roadmap`, `systemd-unit`, `quadlet` [generated], `automation-step`), each combining the shared AI-hint header block produced by the existing `usr/libexec/mios/mios-ai-tag` engine (so the header stays single-sourced) with a small per-type body skeleton whose STRUCTURE is also validated — closing the gap where only the header is checked. Declare each type in SSOT as `[templates.<type>]` with `match`/`comment`/`required_header`/`required_markers`/`generated`/`scaffold`. Land the scaffolder first as Python `usr/libexec/mios/mios-new` (`mios new <type> <name>`, reusing `mios-ai-tag`, filling canonical fields — next ADR number, next `automation/NN` ordinal, canonical ports and endpoints — from SSOT and registering the canonical name through `tools/generate-names-registry.py`), then absorb it into `miosd scaffold`. Add a golden round-trip compiler `tools/compile-templates.py` and a `check_template_conformance` drift-check implemented as a Python worker mirroring `check_hint_coverage → mios-ai-hint-coverage`, degrade-open, ratcheting soft→hard, with `check_hint_coverage` becoming its header subset. Types marked `generated=true` refuse to scaffold an editable file and instead scaffold the generator plus its `mios.toml` section (Law 8 authoritative). Candidate **Law 14 ONE-TEMPLATE-PER-TYPE** lands per ADR-0007 as this ADR plus a `[laws]` registry row (id 14) plus `check_template_conformance` as its `enforced_by` — but the `[laws]` edit and its enforcement are OPERATOR-GATED; do not edit the `[laws]` table without confirmation.
**Where:** `usr/share/mios/templates/*.tmpl` (new, ~15), `usr/share/mios/mios.toml` (`[templates]` schema; candidate `[laws]` id-14 row — OPERATOR-GATED), `usr/libexec/mios/mios-new` (new), `usr/libexec/mios/mios-ai-tag` (reused), `tools/compile-templates.py` (new), `automation/98-drift-checks.sh` (`check_template_conformance`), `usr/bin/mios` + `Justfile` (`mios new` / `just new`)
**Done When:** `mios new <type> <name>` produces a file that passes `check_template_conformance` and the golden compiler; a template that cannot produce a conformant file fails the build; the header check is provably the header subset of conformance; Law 14 is proposed with enforcement wired and the `[laws]` row awaiting operator sign-off.
**Why:** Only the AI-hint header is checked today, so every new file's body structure is improvised and each agent re-invents MiOS conventions by grepping neighbors — the drift that template conformance exists to stop.
**Dep:** No hard dependency (Python-first, offline-deterministic); folds into WS-LANG's `miosd` (T-272) once the Rust workspace exists. OPEN QUESTIONS: Law-14 operator confirmation; the next free drift-check number.
**Status:** done-by-code (audited, gate executed: `checked=1639 unconforming=0 ceiling=0`) -- 26 `[templates.<type>]` SSOT sections, 26 template bodies, `mios new` wired as a verb at `usr/bin/mios:337`, and three registered gates (check_template_conformance / check_templates_compilation / check_template_self_conformance). Bookkeeping: the law landed as id 16 ONE-TEMPLATE-PER-TYPE, not 14; `conformance-grandfathered.list` is a 429-line ratchet still to drain. | **Domain:** Build/Templates | **Who:** tooling/docs agent

## T-272 -- LANG-01: Stand up the Rust workspace and port the first fragile bash tool  (WS-LANG | P1 | L)
**Goal:** E-01 Compiled native tier: Rust-port the build orchestrator and the libexec tool fleet -- the strangler-fig migration begins with proven byte-parity before any shell is deleted.
**What+How:** Create the cargo workspace whose crates live behind one `miosd` static musl binary with subcommands `build|drift|verb|resolve|render|cat|scaffold|fmt`, built once in an early **cached Containerfile stage** and `COPY`'d to `/usr/libexec/mios/miosd`, invoked by thin `RUN`s so the immutable-image contract holds (Law 8 strengthened — `miosd render`/`drift`/`fmt` are the same regenerate-and-diff gate). Port the FIRST fragile bash tool: either the drift-runner (`automation/98-drift-checks.sh`, 44 `check_*` in ~3.1k lines of bash — highest resilience win, lowest coupling, several checks already Python-in-bash) or the verb dispatcher (which structurally removes the 9-verb `eval` surface) — running old and new side by side and diffing to identical before deleting the bash. Collapse the Law-13 resolver twin (`usr/lib/mios/mios_toml.py` ⇄ `tools/lib/userenv.sh`) into one crate exposing a `--shell` KEY=VAL emitter and a pyo3 face, ending the parity drift and retiring `check_userenv_parity`. OPEN QUESTION — workspace location: `C:\MiOS\src\` is already occupied by the in-tree C# `mios-launch.cs` and `autounattend/`, so the workspace goes elsewhere (candidates `C:\MiOS\tools\native\` or `src\mios-rs\`); do NOT clobber `src/`. Go is rejected as a second native tier (documented escape hatch only), the 66 `automation/NN-*.sh` OS-touching steps stay shell-thin, and the AI plane stays Python.
**Where:** the new cargo workspace (location OPEN — `C:\MiOS\tools\native\` or `src\mios-rs\`), `Containerfile` (early cached Rust stage plus `COPY`), `automation/build.sh` (reduced to a ~20-line shim), `automation/98-drift-checks.sh` (checks ported one at a time), `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh` (collapse into the crate), `C:\MiOS\src\mios-launch.cs` (later folds into `miosd cat`)
**Done When:** `miosd` bakes in a cached stage and is invoked by unchanged thin `RUN`s; the first ported tool runs byte-identical to the bash it replaces under a clean side-by-side diff, after which the bash is deleted; the resolver twin is one crate with pyo3 and `--shell` faces and `check_userenv_parity` is retired.
**Why:** The mechanical conscience of the tree is ~3.1k lines of untested bash, and the resolver exists as two hand-synced implementations whose divergence is only caught by a parity check that itself has to be maintained.
**Dep:** After T-268 (one version token) and T-269 (shellcheck gate) — Phase −1 unblocks the port. OPEN QUESTIONS: workspace location; the Go escape hatch; pyo3 versus subprocess for the AI-plane resolver binding.
**Status:** done-by-code | **Domain:** Build/Lang | **Who:** native-tooling agent

## T-273 -- Extract the `mios_dispatch.py` verb→bash chokepoint into `mios_pipe/` and finish the server.py decomposition (TD-5)  (WS-DEBT-PIPE | P2 | M)
**Goal:** E-02 Technical-debt retirement: the TD-1..TD-8 register -- the agent-pipe god-modules stop being unreviewable monoliths so the /v1 front door (NS-2) rests on decomposed, typed, testable Python.
**What+How:** The `mios_pipe/` refactor (103 files, 100% AI-hint-tagged) stopped short of the 4 largest flat modules. Extract `mios_dispatch.py` FIRST — it is the security-critical verb→bash chokepoint every verb passes through — into `mios_pipe/`, then continue extracting the remaining flat modules so `server.py` (currently **8,961 lines**: VRAM scheduler + `_db_*` helpers + auth middleware + agent streaming all intermixed) shrinks toward a thin composition root. Relocation ≠ decomposition: also split the 3 already-relocated 88–107 KB monoliths (`routing/chat.py`, `native_loop.py`, `federation/a2a.py`) where feasible. Replace the **9 bare `except:`** (out of 558 `except Exception`) with typed handlers. Add a new drift-check in `automation/98-drift-checks.sh` enforcing "no Python file > 800 lines". Python stays (Law 6, ML ecosystem) — the debt is the monolith, not the language.
**Where:** `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/mios_dispatch.py`, `usr/lib/mios/agent-pipe/mios_pipe/**` (incl. `routing/chat.py`, `native_loop.py`, `federation/a2a.py`), `automation/98-drift-checks.sh`
**Done When:** `mios_dispatch.py` is extracted and imported live with `check_unwired_modules` green; `server.py` is under the 800-line composition-root target; `grep -n 'except:$'` over `usr/lib/mios/agent-pipe/` returns nothing; and the new >800-line Python drift-check passes in `just drift-gate`.
**Why:** Today every verb invocation funnels through an un-decomposed, un-unit-testable dispatch module, and a 9k-line `server.py` mixing auth middleware with VRAM scheduling means any change risks a use-before-def NameError that only surfaces in the publish bake — the exact class that has already broken it.
**Dep:** none — independent Python-only refactor track; `check_unwired_modules` confirms each extraction is live.
**Status:** in-progress -- FIRST SPLIT LANDED. `mios_dispatch.py` 1178 -> 943 lines: the command BUILDER (`_dispatch_sandbox_profile`, `_sandbox_wrap_cmd`, `normalize_container_exec`, `_build_dispatch_cmd`) moved VERBATIM to `mios_pipe/routing/dispatch_cmd.py` with its own `configure()` seam; `mios_dispatch` re-imports the four names so its surface is byte-identical, and its configure() forwards the three injected values so ONE call still configures the whole chokepoint. The launcher proper and every gate (taint / HITL / Rule-of-Two / quarantine / broker socket I/O) stay put -- this module builds a command, it never runs one. Order mattered: the two security gates had zero tests, so they were covered FIRST (20 assertions, mutation-tested) and then deliberately NOT moved. Verified: all 156 agent-pipe tests, live route-parity against the real FastAPI app, and 18 isolation assertions in a new `test_mios_dispatch_cmd.py` that imports the module DIRECTLY -- proving the extraction is standalone rather than a file that merely moved. The `[refactor].oversize` ratchet did its job: it FAILED on the shrink until the entry was lowered to 943. REMAINING: `server.py` (4979) and the rest of mios_dispatch's launcher half. **Who:** AI-plane agent

## T-308 -- ROADMAP-01: One answer to "what is left?" -- summary-table/section status parity  (WS-TESTDOC | P1 | S)
**Goal:** E-09 One value, one name -- a task's status is recorded once and read the same way from either surface, so the roadmap cannot be driven to completion against a number that is wrong.
**What+How:** `TASKS.md` states every task's status twice -- a summary-table cell and the task's own `**Status:**` line -- with nothing keeping them in step; they had diverged in 49 of 286 rows. Settle every disagreement against the TREE rather than either prose surface (a status claiming completion has to name an artifact that exists), then add `check_tasks_status_parity` so the two can never drift again. Also run the `tools/` sibling unit tests: `check_module_test_coverage` requires one beside every `tools/` module but nothing ever executed them.
**Where:** `TASKS.md`; `tools/check-tasks-status-parity.py` + `tools/test_check-tasks-status-parity.py`; `automation/98-drift-checks.sh`; `tests/drift-gate-negatives.sh`; `Justfile`; `.github/workflows/mios-ci.yml`; `usr/share/doc/mios/manual/ch58-roadmap-status-parity.md`.
**Done When:** No row in `TASKS.md` disagrees with its own task section, the `?` placeholder is rejected wherever a section can answer it, the gate refuses to pass over an empty row set, and every `tools/test_*.py` runs in both `just drift-gate` and CI.
**Why:** 28 rows carried `?`, seven said `done-by-code` while the detail said `open`, and three P0 rows said `done` while the detail said `planned`. Whichever surface a reader trusted, they got a confident and different answer about what remained.
**Dep:** none -- independent.
**Status:** done -- all 49 disagreements settled: 10 detail lines were stale against a tree that already had the artifact (`_host_pressure_gate()` in `mios-daemon`, the `[budget]` section, `usr/share/mios/conductor/` behind `conductor_enable`, `kg_lookup`, the MLFQ ordering in `mios_pipe/scheduler/preempt.py`, the bitemporal `valid_from`/`valid_to` columns, `[code_mode]`, `--cache-reuse 256`, `[security.redact]` on the persist AND federate paths) and were rewritten WITH that evidence inline; the other 39 table cells took the section's newer verdict. `check_tasks_status_parity` (gate 152 of 167) compares the cell to the head token of the status, so a detail line may carry paragraphs of evidence and still be comparable to a one-word cell; it rejects `?`, rejects an unknown status word on either surface, fails on a section with no row, and fails rather than passing vacuously when the table parses to zero rows. Negative-tested both directions and proven effective by neutering the gate. Open count is now an honest **70**. `tools/test_render_globals.py` had been RED on the default branch: two assertions expected `_ps_assign` to expand `${MIOS_*}` when given no name table, while a contradictory guard made that branch unreachable -- resolved in favour of the tests, with `automation/lib/globals.ps1` proven byte-identical after the fix. Manual ch58. | **Domain:** Roadmap/Gates | **Who:** repo maintainer

## T-309 -- SBX-01: One answer to "what confinement does a verb get?"  (WS-GUARD | P3 | S)
**Goal:** E-09 One value, one name -- the sandbox's flag set is stated once, so a reviewer reading the policy module and an operator reading the wrapper reach the same conclusion.
**What+How:** `mios_sandbox.build_bwrap_argv` and `usr/libexec/mios/mios-sandbox-exec` both describe a bubblewrap invocation, and they DISAGREE: the function emits `--unshare-all` with no `--cap-drop` and no `--seccomp`; the wrapper unshares pid/ipc/uts, drops all capabilities, adds `--unshare-net` only at enforce-without-net, and (since T-230) attaches the seccomp filter. The function is dead code -- nothing but its own test calls it -- so it is a second, wrong answer to a security question. Decide which flag set is correct on a real host, make ONE of them authoritative, and either delete the other or bind them with a parity assertion the way the userenv twins are bound. `--unshare-all` also unshares the user and cgroup namespaces, which is why this needs VM verification rather than a desk edit.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py`, `usr/libexec/mios/mios-sandbox-exec`, `usr/lib/mios/agent-pipe/test_mios_sandbox.py`, `tests/test-sandbox-seccomp.sh`, and the two docs that cite `build_bwrap_argv`.
**Done When:** Exactly one definition of the confined argv exists, or a test fails when the two diverge; and a confined verb on a real host is observed running under the flag set the surviving definition names.
**Why:** A reader who consults the policy module today concludes verbs run under `--unshare-all` with capabilities intact. Neither half of that is true, and it is the kind of wrong belief that gets relied on in a review.
**Dep:** After T-230 (which added the seccomp flag the function does not model). Needs a VM/host to verify a namespace change safely.
**Status:** planned | **Domain:** Security/Sandbox | **Who:** security agent

## T-310 -- SEC-TLS-01: Five outbound clients disable TLS certificate verification  (WS-GUARD | P2 | S)
**Goal:** E-24 Autonomy guardrails -- an outbound probe cannot be silently answered by whoever is on the wire.
**What+How:** Five `httpx.AsyncClient(verify=False, ...)` call sites ship on the default branch: `mios_pipe/routing/turn.py:98` (node liveness probe), `mios_pipe/routing/portal.py:1159/1194/1217` (Portal service probes) and `mios_pipe/kernel/clusterhealth.py:314`. CodeQL rates this class high (`py/request-without-cert-validation`), and it is a real weakness rather than a false positive: any of these endpoints resolved to an `https://` URL is probed with certificate checking OFF, so a MITM answers the liveness/health question and the plane treats a hostile lane as live. The probable original reason is self-signed certificates on local lanes. The fix is to verify by DEFAULT and narrow the exception: keep verification off only for a loopback/unix-socket target, or supply the local CA, driven by one SSOT key rather than five literals -- for `http://` targets `verify` is irrelevant anyway, so the flag buys nothing in the common case and only weakens the uncommon one.
**Where:** `usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py`, `usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py`, `usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py`, plus the SSOT key and a drift-check forbidding a bare `verify=False`.
**Done When:** No `verify=False` literal remains outside the one narrow, SSOT-gated helper; a probe against a self-signed LOCAL lane still succeeds on a real host; a probe against an untrusted certificate fails instead of reporting the lane live; and a gate fails if a new `verify=False` appears.
**Why:** A liveness probe that cannot tell a real lane from an impostor is a routing decision made by the attacker. It is also the only remaining high-severity class CodeQL reports on this tree.
**Dep:** none -- independent. Was recorded rather than patched blind because the loosened path needed proving against a real certificate, which is exactly how it was then closed.
**Status:** done -- all five sites now resolve `PROBE_VERIFY_TLS`, defined ONCE in `mios_pipe/kernel/config.py` from `[security].probe_verify_tls` (default `true`). The key needed registering in `WALK_EMIT_KEEP` because `[security]` is a `WALK_MOSTLY_DEAD` section -- worth noting that `[profile]` sits in that same list, which is the mechanical reason `[profile].role` is read by nothing (T-315). PROVEN LIVE against a real self-signed TLS server on :18443: unset -> True -> refused; `true` -> True -> refused; `false` -> False -> HTTP 200; `0` -> False -> HTTP 200. Unknown values stay secure. Five new assertions in `test_mios_turn.py` fail if any site regains a `verify=False` literal, proven effective by re-introducing one (test went red, restored, green). `portal.py` was held at its exact 1675-line register by folding a needlessly-wrapped `fastapi.responses` import, and the docs ratchet stayed at 1724 -- neither register was raised. | **Domain:** Security/Transport | **Who:** security agent

## T-311 -- NAME2-04: Rename the globals that are truly MUTATED at runtime  (WS-NAME | P3 | M)
**Goal:** E-10 One canonical name -- casing tells a reader whether a module-level name is configuration or shared mutable state, without having to trace it.
**What+How:** T-238 measured 406 module-level UPPER_SNAKE names reassigned through a `global` statement and showed that renaming them wholesale would be wrong: most are dependency-injected configuration constants (`REFINE_MODEL`, `KNOWLEDGE_RECALL_K`) for which UPPER_SNAKE is correct. The residue is the smaller set that is MUTATED IN PLACE at runtime -- caches, registries, pools, locks: `_QUOTA_TRACKERS`, `_CRL_CACHE`, `_KV_LOCKS`, `_NODE_LIVE`, `_WORKER_TOOLS_CACHE`, `_SOURCES_REGISTRY`, `_CHAT_CANCEL`, `_MCP_POOL` and their peers. Build the discriminator first (a name is state if something calls a mutating method on it or subscript-assigns into it, not merely if it is rebound at wiring time), then rename that set to `_lower_snake` and gate the rule so it holds for new code.
**Where:** `usr/lib/mios/agent-pipe/**` (the identified state globals), `server.py`'s re-export block, and a new drift-check plus its sibling test.
**Done When:** Every module-level name mutated in place is `_lower_snake`, injected configuration constants are untouched, `check_pipe_extraction_parity` and the route-parity gate stay green, and a new gate fails when a mutated-in-place global is introduced in UPPER_SNAKE.
**Why:** A reader cannot currently tell `_VERB_CATALOG` (injected once, then read) from `_NODE_LIVE` (written from several coroutines) by looking. The second needs a concurrency argument; the first does not.
**Dep:** After T-238's measurement. Several of these names are injected BY NAME through `configure()` and re-exported verbatim by `server.py` for the surface-parity gate, so the rename must move all three surfaces together -- which is why it is its own task rather than a sweep.
**Status:** planned | **Domain:** Naming/Hygiene | **Who:** naming agent

## T-312 -- BLADE-01: Total `[urls]` -- one canonical address per service  (WS-BLADE | P1 | M)
**Goal:** E-09 One value, one name -- a service's address is stated once, so pointing it at another machine is an overlay rather than a refactor.
**What+How:** MEASURED: `[urls]` carries 9 of 41 addressable ports; the other 32 have their address hand-composed as `localhost:${MIOS_PORT_X}` in 1-18 files each (~125 non-generated, non-doc consumer files, ~338 references). Because all three pods are `Network=host`, every service genuinely IS on the host loopback -- so the ~600 `localhost` references are the architecture, not sloppiness, and offloading a service is purely an ADDRESSING change. Give every addressable port exactly one `[urls]` key; make consumers resolve `MIOS_URL_*`; add `check_service_urls` enforcing (a) every port has a URL or is registered non-addressable, and (b) no NEW consumer hand-composes an address, with a shrink-only per-file register draining the existing debt the way `[refactor].oversize` and `[schema].unconsumed` do. Offload then becomes an `/etc/mios/mios.toml` overlay -- no quadlet change, no code change.
**Where:** `usr/share/mios/mios.toml` (`[urls]` + the register), `tools/check-service-urls.py` + `tools/test_check-service-urls.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`, the consumer tranches.
**Done When:** Every numeric `[ports].*` key resolves to exactly one `[urls]` entry or a registered non-addressable reason; the gate fails on a new hand-composed address and on a register entry that grows or names a deleted file; and re-pointing one service at a remote host is proven by an `/etc/mios` overlay alone, with no file under `usr/` changed.
**Why:** This is the whole of "offload to a hosted MiOS", mechanically -- and the mechanism is now PROVEN by `tests/test-offload-overlay.py`, which writes an `/etc/mios` overlay, resolves in a child process as a booted host does, and asserts the named services move to the blade, the unnamed ones stay local, an empty override never wins (Law 1), and NO file under `usr/` changes. Sabotaging the host tier turns it red. **But the measurement inverted this task's direction.** `[urls]` emits `MIOS_URLS_*` and NO shipped code reads any of the twelve (the single `MIOS_URLS_FORGE` hit is sample data in `tools/test_render_globals.py`), while `MIOS_AI_ENDPOINT` is read by 72 tracked files, `MIOS_AGENT_PIPE_BACKEND` by 7, `MIOS_DB_URL` by 4, `MIOS_LLM_CPU_ENDPOINT` and `MIOS_CRAWL_SERVICE_URL` by 3 each. So migrating ~125 consumers onto `MIOS_URL_*` would stand up a SECOND canonical naming scheme beside the one already carrying the traffic -- the exact Law-9 violation this task exists to prevent, committed in Law 9's name. Corrected direction: a service's canonical address is whichever single key its consumers ALREADY resolve; offloading the AI plane means overriding `[ai].endpoint`, which works today. `[urls]` is the browser-openable surface (portal tiles, openInBrowser labels), to be scoped to that job or retired -- not the inter-service endpoint table. ADR-0016 Decision 1. It is required under every answer to the MiOS-Mini naming question, which is why it lands before that question is settled. ADR-0016 Decision 1.
**Dep:** none -- independent, and a prerequisite for T-313.
**Status:** done -- the classification half was already gated; `check_service_urls` (gate 154 of 168) requires every numeric `[ports]` key to resolve to exactly ONE canonical answer: a `[urls]` entry that templates its `${MIOS_PORT_*}`, or membership of the shrink-only `[urls].non_addressable` register. A port in NEITHER fails, so a new service cannot land without stating how it is addressed; a port in BOTH fails too, because two answers is the drift the gate exists to prevent. It also fails on a register entry naming a port that does not exist, on a duplicated entry, and rather than passing vacuously over an empty port table. 16 assertions in `tools/test_check-service-urls.py` plus a two-case negative test, both proven by sabotage. Current standing: **40 ports, 9 addressed, 31 registered.** A literal port number in a `[urls]` string deliberately does NOT count as coverage -- that is the hardcoding this task exists to replace. Note `agent_pipe` is registered rather than given a `[urls]` key because `MIOS_AI_ENDPOINT` is already its one canonical name under Law 5; a second would BE the Law-9 violation. Remaining: drain the register (the 9 uncovered ports that are actively hand-composed are `vllm`, `sglang`, `cpu_node`, `cockpit_link`, `adguard_ui`, `guacamole_web`, `opencode_gateway`, `firecrawl` -- `agent_pipe` excepted above), and add the second half of the gate: a shrink-only per-file register so no NEW consumer hand-composes an address. Seven of the registered ports cannot gain a `[urls]` entry until T-318 lands, because the SSOT port is not the port the service binds -- a canonical URL for those would be a worse lie than none. Earlier audit note corrected: the count is 9 of **40** (not 41 -- `stack_id` is an offset, not a port), and "all uncovered ports are addressed somewhere" measured REFERENCES; measured as hand-composed ADDRESSES the number is 9, and 7 ports are referenced nowhere outside the SSOT at all (T-318). First de-duplication landed: `[ai].endpoint` hardcoded `http://localhost:8700/v1` instead of resolving `${MIOS_PORT_AGENT_PIPE}` -- a Law-7 literal restating a port the SSOT already owns. Now templated; `MIOS_AI_ENDPOINT` resolves byte-identically (`http://localhost:8700/v1`) and check_no_hardcode / check_no_duplicate_value_key / check_var_closure / check_globals_generated / check_resolved_env_lossless all pass. Note that agent-pipe therefore needs NO `[urls]` entry -- `MIOS_AI_ENDPOINT` is its canonical name and Law 5 already points every consumer at it. 

**CLOSED by executing the inverted Decision 1 rather than the original plan.** The original plan was to migrate ~125 consumers onto `MIOS_URL_*`; measurement showed that would stand up a SECOND canonical naming scheme beside the one already carrying the traffic. So `[urls]` is now SCOPED to the browser-openable surface instead: every entry must use an `http`/`https` scheme, and `check_service_urls` fails anything else. Four entries were inter-service addresses wearing a tile's clothes -- `pgvector` was a `postgresql://` DSN, and `llm_light`/`hermes`/`crawl_service` were `/v1` API bases. Each already has exactly one canonical name its consumers resolve (`MIOS_DB_URL` 4 files, `MIOS_LLM_CPU_ENDPOINT` 3, `MIOS_HERMES_ENDPOINT` 1, `MIOS_CRAWL_SERVICE_URL` 3), so a `[urls]` key for them WAS the Law-9 violation this task exists to prevent. They moved to the register, whose comment now names the only two reasons an entry may appear there: the port serves no page a person opens, or its address is already stated on the key its consumers read. Standing: **40 ports, 6 browser-openable, 34 classified.** The register is no longer debt to drain -- it is a classification, and shrinking it further would mean inventing tiles for services that have no page. 6 assertions in `tools/test_check-service-urls.py` for the scheme rule plus a negative case proven by sabotage. | **Domain:** Topology/SSOT | **Who:** architect

## T-313 -- BLADE-02: `[blades]` becomes the machine registry; nodes gain a blade  (WS-BLADE | P2 | M)
**Goal:** E-09 One value, one name -- "which machine" is a first-class field, so capacity and reachability stop being inferred from an endpoint string.
**What+How:** `[blades]` is an EMPTY section today -- zero keys under a 30-line comment about nodes -- while the agent plane keeps `_BLADE_POOL`, `_ENDPOINT_BLADE` and `_LOCAL_BLADE` and `[admission].multiblade_enable` is `false`. Meanwhile `[nodes.*]` declares six nodes of which FIVE point at the same endpoint and the same model (`localhost:${MIOS_PORT_SGLANG}`, `mios-heavy`) and one ships empty, and `local-cpu` declares `lane = "gpu"` pointing at the GPU heavy lane -- so the "pool" is five aliases for one backend and there is no CPU lane at all. Collapse the node list to what actually exists FIRST, then make `[blades.<name>]` the machine registry (reachability, served addresses, capacity envelope) and give each node a `blade` field. Promote `health_gate`'s auto-join/drop semantics from the node to the blade.
**Where:** `usr/share/mios/mios.toml` (`[blades]`, `[nodes.*]`), `usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py` (`_load_node_pool`), `mios_pipe/scheduler/vram.py`, `mios_pipe/scheduler/admission.py`.
**Done When:** Every `[nodes.*]` entry names a blade that exists; no two node keys are aliases for the same (endpoint, model) unless the SSOT says so explicitly; the VRAM/admission blade machinery reads `[blades]` rather than inferring from endpoints; and a gate fails on an alias pair or an orphan node.
**Why:** Capacity fan-out currently believes it has five lanes when it has one backend, and the blade code has no SSOT to read. ADR-0016 Decision 2.
**Dep:** After T-312 (a blade serves addresses; addresses must be canonical first).
**Status:** done -- and this entry's OWN framing needed two corrections, both found by measurement.

**CORRECTION 1: `[blades]` being empty is CORRECT, not the defect.** `mios_pipe/scheduler/blades.py` resolves the local blade's name from `[identity].hostname` (env `MIOS_HOSTNAME` -> `[identity].hostname` -> `socket.gethostname()`), and its own docstring states the contract: *"a config with no `[blades.*]` and no blade fields resolves every endpoint to one local blade at the local budget -- i.e. exactly today"*. Declaring `[blades.mios]` in the vendor file would restate the hostname a second time (Law 9). The vendor `[blades]` table is for REMOTE blades an `/etc/mios` overlay adds; empty is the right vendor default. For the same reason **a node must NOT carry `blade = "local"`** -- omitting it IS the local-blade declaration. This entry's "give each node a `blade` field" is therefore withdrawn.

**CORRECTION 2: the blade machinery IS wired.** This entry says "the blade code has no SSOT to read". `server.py:_rebuild_blade_topology()` calls `local_blade_name()`, `load_blade_pool()` and `endpoint_blade_map()` at import and degrades open on failure; `_BLADE_POOL`/`_ENDPOINT_BLADE`/`_LOCAL_BLADE` are populated. What is off is `[admission].multiblade_enable = false`, which is a deliberate gate, not missing wiring. (My own first pass grepped only for `vram.configure(blade_pool=)` and concluded it was unwired -- wrong, and corrected here rather than acted on.)

**What WAS real, and is fixed.** The pool advertised six lanes over TWO reachable backends:
* **FOUR nodes were byte-identical** -- `local-dgpu`, `local-cpu`, `local-sglang`, `local-llamaswap` all declared `endpoint = ${MIOS_PORT_SGLANG}/v1`, `model = "mios-heavy"`, `lane = "gpu"`, `api = "openai"`. Behind per-lane and per-endpoint semaphores that is not four lanes, it is one backend counted four times.
* **`local-cpu` declared `lane = "gpu"` on the GPU endpoint**, so the pool had NO cpu lane at all while `[dispatch]` budgeted one (`lane_priority` `cpu:7`, `lane_concurrency_cpu = 2`). It now points at `mios-cpu-node` (`${MIOS_PORT_CPU_NODE}`, a bare llama.cpp `llama-server` on granite-4.1-8b with `n-gpu-layers 0`) with `lane = "cpu"`, `api = "llamacpp"`.
* **`local-llamaswap`'s own comment contradicted its fields** -- the prose describes "the llama.cpp multi-model + KV-paging lane (mios-llm-light.container on :11450 ... `api=llamacpp` => the pipe does /slots KV-paging here)" while the fields said SGLang, `api = "openai"`. And `:11450` is in `[docs].retired_ports`. It now points at `${MIOS_PORT_LLM_LIGHT}` with `api = "llamacpp"` and `model = "mios-agent-cpu"`, which the light lane's model map serves as a resident alias.
* **`local-dgpu` retired** as an exact duplicate of `local-sglang`; the engine names (`local-sglang`/`local-vllm`) are the consistent scheme, and the SSOT's own comment already noted the two are "mutually exclusive (both serve mios-heavy)".
* `local-igpu` keeps its empty endpoint -- that is a DECLARED-inert placeholder (`_load_node_pool` skips it), and the gate treats it as such rather than as a defect.

Standing: **5 nodes over 4 distinct endpoints, 0 alias pairs, a cpu lane that exists.** `check_node_pool` (gate 174 of 174) fails an exact alias, one endpoint declared as two lanes, a lane `[dispatch].lane_priority` does not budget, a `blade` naming no `[blades]` entry, and an endpoint with a BAKED local port -- that last one because a node whose port is a literal can never be repointed at a blade, which is the offload mechanism itself. Run against the shipped state it reproduced all three aliases. 17 assertions in `tools/test_check-node-pool.py` plus a three-case negative test proven by sabotage. | **Domain:** Topology/SSOT | **Who:** architect

## T-314 -- BLADE-03: Give greenboot's role-awareness an SSOT it actually reads  (WS-BLADE | P2 | S)
**Goal:** E-24 Autonomy guardrails -- a machine's critical set is DECLARED, not inferred from whatever happens to be enabled.
**What+How:** CORRECTED against the tree: the predicted rollback loop does NOT happen. `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh` opens every probe with `systemctl is-enabled --quiet "$unit" || return 0`, so a seat that never enables `mios-llm-light`/`mios-pgvector` passes cleanly. But it degrades open by accident, not by design: the script hardcodes its own four unit/port pairs and never reads `[greenboot].critical_services`. `MIOS_GREENBOOT_CRITICAL_SERVICES` is emitted by both `globals` twins and consumed by NO shipped code -- the same decorative-key failure as `[profile].role`. The three surfaces had already drifted: SSOT lists 3 services, the script probes 4 (adds `hermes`), and `check_greenboot` hardcoded the SCRIPT's 4 rather than the SSOT's 3, so script and gate agreed with each other while both ignored the source of truth. DONE: `check_greenboot` now reads `[greenboot].critical_services` from the SSOT, requires a required.d script to reference the unit in EXECUTABLE code (a comment no longer satisfies it), and fails on an empty critical set rather than passing vacuously. REMAINING: decide whether a seat's "critical" may include reaching its blade -- answering yes makes boot success network-dependent and collides with Law 12 (degrade open, never block boot), so it must be a recorded choice.
**Where:** `automation/98-drift-checks.sh` (`check_greenboot`, done), `usr/share/mios/mios.toml` (`[greenboot]`), `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh`, `usr/lib/greenboot/check/required.d/10-mios-role.sh`.
**Done When:** The critical set is stated once in the SSOT and read by both the gate and the probe script; the gate fails on a critical service with no health check and on an empty set; and the network-dependence question is answered in the SSOT rather than implied.
**Why:** A health check whose critical set is a hardcoded copy of itself cannot notice that it is wrong. Proven by sabotage: adding a bogus critical service to the SSOT left `check_greenboot` printing success, caught only by the unrelated projection gates. ADR-0016 consequences.
**Dep:** none -- the gate half landed independently of T-312.
**Status:** done -- gate reads the SSOT, and the blade-reachability question is ANSWERED: operator ruling is configurable-defaulting-to-no, so `[greenboot].blade_reachability_critical = false` now states it in the SSOT and Law 12 holds by default. **REVERSAL, and it is the second time this claim flipped.** This status previously said the predicted rollback loop "does NOT happen" because `40-mios-ai-plane.sh` opens each probe with `systemctl is-enabled --quiet "$unit" || return 0`. That reading was wrong: **`is-enabled` reports INSTALLATION, not whether a unit will start.** `Condition*` is evaluated at start time, so a capability-skipped unit is still enabled, and a Quadlet-generated unit reports `generated` -- which also exits 0. On a seat the guard therefore does not fire, greenboot probes `mios-pgvector` and `mios-llm-light` on ports nothing is listening on, the required check fails, and `bootc` gets a bad boot. Evidence level stated honestly: the units carry `[Install] WantedBy=` (verified) and the Condition-vs-enablement semantics are documented systemd behaviour, but this container has no system bus and no man pages, so that half is reasoning rather than measurement. FIXED without depending on which reading is right: the probe now asks THE SAME QUESTION the unit's own `ConditionPathExists` asks -- is `/etc/mios/blade.d/<cap>` present -- reading `MIOS_BLADE_CAPS` from `/run/mios/blade.env` and the unit's own `50-blade-*.conf` drop-ins. Under the pessimistic reading that removes a rollback loop; under the optimistic one it replaces an accident with a design. It degrades OPEN when the blade resolver has not run at all (Law 12). `tests/test-greenboot-blade-guard.sh` exercises the real predicate against a fixture tree with no systemd required -- 4 assertions (seat skips a gated unit, seat still probes the ungated front door, a serving blade probes it, and no-resolver degrades open) -- proven by sabotage and wired into CI. CLOSED: the probe is now DRIVEN by `[greenboot].critical_services`. A name resolves to its unit and port by convention (`mios-<n>.service`, `MIOS_PORT_<N>`), and the new `[greenboot.probe]` table carries only the exceptions -- `agent_pipe` needs `kind="http"` + `path="/v1/models"`, `hermes` binds `hermes-worker.service`. `hermes` is added to the critical set so the SSOT finally states what the script has always probed (it listed three while the script probed four). An empty critical set probes NOTHING rather than falling back to a hidden list. `check_greenboot` was rewritten to match: when a required.d script is SSOT-driven, "covered" no longer means "the script spells the unit name" -- it means the unit the probe WOULD DERIVE actually exists as a shipped unit or a declared container, so a bogus critical service still fails. Two more assertions in `tests/test-greenboot-blade-guard.sh` (6 total): the derivation produces exactly the four unit/port/kind/path tuples the hardcoded list did, and an empty set probes nothing. Both proven by sabotage. (Its `hermes.service` line, which could never run, now names `hermes-worker.service`: T-316.) | **Domain:** Lifecycle/Health | **Who:** architect

## T-315 -- BLADE-04: Finish WS-BLADE -- karg producer, role-apply demotion, `[profile]` fold  (WS-BLADE | P2 | M)
**Goal:** E-09 One value, one name -- one role system, stated once, acting in one place.
**What+How:** WS-BLADE was marked `done`; re-measured, three named deliverables are absent and the status is back to `active`. (1) `usr/lib/bootc/kargs.d/05-mios-blade.toml` does not exist -- `role-apply` parses `mios.blade=`/`mios.role=` out of `/proc/cmdline`, so the READER ships with no Law-8 producer and deploy-time role selection works only where an installer types the karg by hand. (2) `role-apply` was never demoted to the marker-writing resolver BLADE-01 specifies: it still calls `systemctl set-default --no-block` and `systemctl start --no-block`, so the declarative half (markers + `ConditionPathExists`) and the imperative half both run -- two schedulers racing for the same decision. (3) `[profile].role`/`features` was never folded into `[blade]`: `[profile].role = "developer"` is not one of the archetypes `role-apply` accepts (`hybrid|compute|endpoint|controller|headless|desktop|k3s*|ha*`), and `role-apply` never reads `[profile]` at all, so `"developer"` would fall through to `*) WARN: unknown role ... defaulting to headless`. Generate the karg from `[blade].type`; strip the `systemctl` calls; alias `[profile]` onto `[blade]` for one release then retire it. Keep `[blade]` (OS-role, Axis A) and `[blades]` (fleet, Axis B) orthogonal, as BLADE-01's own acceptance already requires -- and treat the one-letter difference as the Law-9 hazard it is.
**Where:** `usr/share/mios/mios.toml` (`[blade]`, `[profile]`), `usr/libexec/mios/role-apply`, `usr/lib/bootc/kargs.d/05-mios-blade.toml` (to generate), `tools/generate-blade-dropins.py`, `automation/98-drift-checks.sh`.
**Done When:** The karg has a generator and a regenerate-and-diff gate; `role-apply` writes markers and `/run/mios/blade.env` and starts nothing; `[profile]` resolves through `[blade]` or is gone; and a gate fails on a `[profile].role` that is not a legal `[blade].type`.
**Why:** The marker/drop-in/target/verb/greenboot chain genuinely ships and is drift-gated -- so "one image, role by flag" is a MECHANISM, not a proposal. What is left is subtraction, and a seat is then an archetype rather than a new image. ADR-0016 Decision 4.
**Dep:** none hard; pairs with T-312 (a seat is an archetype plus a `[urls]` overlay).
**Status:** done -- all three deliverables landed, and two of them were not what the plan said they were.

(1) **KARG PRODUCER** (landed earlier): `tools/generate-blade-karg.py` projects `[blade].type` into `usr/lib/bootc/kargs.d/05-mios-blade.toml` as a bare `kargs = ["mios.blade=<type>"]`, wired into `tools/sync-generated.sh` (step 4c) and gated by `check_blade_karg`, which regenerates in memory and diffs. It refuses an empty `[blade].type` and a type naming no archetype; the gate fails on a hand-edit AND on the file being absent, which is the state this started in.

(2) **`[profile]` IS GONE, NOT ALIASED.** The plan was "alias onto `[blade]` for one release, then retire". Measurement made the alias pointless. `[profile].role = "developer"` was not a legal archetype; `role-apply` read `[blade].type` and never `[profile]`; `MIOS_PROFILE_ROLE`/`MIOS_PROFILE_FEATURES` were emitted by both `globals` twins and consumed by no shipped code -- `mios_toml.py` already classed the whole section `WALK_MOSTLY_DEAD` and resurrected exactly those two through an explicit `WALK_EMIT_KEEP` exception; and the section's ONLY writer, `usr/libexec/mios/user-setup.sh`, emitted `Role` with a capital R, which no reader spells that way. Dead on both ends leaves nothing to alias. `[profile].features` was worse: its shipped values were `ai`/`virtualization`/`k3s`, and none of them is a capability any archetype grants. Retired outright; both keep-lists cleaned; `user-setup.sh` now migrates a legacy `role` onto `[blade].type`.

(3) **THE KARG PRODUCER HAD BROKEN THREE THINGS, SILENTLY.** `role-apply` guarded its remaining tiers with `if [[ -z "$ROLE" ]]`, and the generated karg is on EVERY cmdline -- so `ROLE` was never empty. In one commit, with no error anywhere: `/etc/mios/role.conf` stopped being read, so **`mios blade set` did nothing**; its `FEATURES=` stopped being read, so **`mios blade add-capability` was erased on the next boot** (role-apply wipes `/etc/mios/blade.d` every run); and the WSL / Blackwell / no-DRM fallbacks became unreachable. Replayed and proven with the shipped guard before the fix. The replacement is a precedence LADDER mirroring the config overlay's own tiers -- explicit karg (one differing from `[blade].type`) > `/etc/mios/role.conf` > `[blade].type` > hardware demotion of the vendor tier only to `[blade].fallback`. `role.conf` is now PARSED, not sourced (`.` ran it as root and clobbered the names it set). `mios.features=` used to `touch` any string into the capability namespace, so a typo made a dead marker and `mios.features=gpu-serving` was an undeclared escalation; capabilities are now the closed union of `[blade.archetypes]`.

(4) **THE `systemctl` REMOVAL IS NOT FREE, AND IS NOW CONDITIONAL RATHER THAN DELETED.** CORRECTION to an earlier note here: the six role targets are NOT identical boilerplate. Four are thin; `mios-hybrid.target` (the DEFAULT) has `Requires=graphical.target` + `Wants=k3s-agent.service`, and `mios-desktop.target` requires `gdm.service` plus the libvirt stack. `automation/88-finalize.sh` bakes `set-default multi-user.target`, so on the FIRST boot after install nothing but `role-apply`'s `systemctl start` reaches the role target -- delete it and a fresh desktop install boots to a text console. Baking a role target instead was considered and REJECTED: it puts `Requires=graphical.target` on the boot-critical path of headless hardware. So `set-default` (declarative, next-boot, starts nothing) runs when the default differs, and `start` fires ONLY when the resolved target differs from the one recorded in `/var/lib/mios/role.active`. Steady-state boots take neither branch, so the "two racing schedulers" are gone without a broken first boot.

(5) **FOUND EN ROUTE, FIXED.** The role targets did not form a switchable set: day-2 switching starts rather than isolates, so it depends on `Conflicts=`, and the DEFAULT archetype conflicted with nothing at all -- `mios blade set headless` on a hybrid blade started headless and left hybrid running. Now a complete pairwise graph across all 8 role targets, gated. `mios-hybrid.target` and `mios-k3s-worker.target` each declared `Alias=default.target.mios-<role>`; an alias must carry its unit's own suffix, so systemd can never install it, and because that alias WAS their entire `[Install]` section the default role target had no `WantedBy=` while all seven peers did. And `role-apply` matched `k3s*`/`ha*` as case globs, so `mios.blade=k3s` selected `mios-k3s-master.target` and then resolved to `[]` capabilities -- target up, whole service plane condition-skipped. Both are declared archetypes now, and the legacy spellings are DATA in `[blade.role_aliases]`, exact-match, so `k3sx` selects nothing.

**Shipped:** `usr/lib/mios/blade.sh` (ONE resolver, sourced by both `role-apply` and the `mios blade` verb, so they cannot drift); `check_role_ssot` (gate 172, 172 total) asserting `[blade].type` is an archetype, every archetype ships its derived target, aliases land on archetypes, the conflict graph is complete, no `Alias=` breaks its suffix, `[profile].role` cannot return illegally, neither keep-list resurrects the retired vars, and NO archetype name appears as a literal in the blade code -- the Law-12 floor is the generated karg and the demotion target is `[blade].fallback`. `mios blade` gained `list`, validates `set`/`add-capability` against the SSOT, and its `status` no longer prints a bare `$` where `systemctl get-default` belonged. 14 assertions in `tests/test-role-apply-precedence.sh` driving the real functions against fixtures (three sabotages proven), 26 in `tools/test_check-role-ssot.py`, and a five-case negative test. | **Domain:** Topology/SSOT | **Who:** architect

## T-316 -- ADDR-01: 17 executable retired-port fallbacks; Hermes binds an unassigned port  (WS-BLADE | P1 | M)
**Goal:** E-09 One value, one name -- a service has one port, and a missing variable fails loudly instead of dialling a dead one.
**What+How:** MEASURED. Hermes disagrees with itself five ways: `[ports].hermes = 8720`, `[ports].hermes_worker = 8730`, `hermes-worker.service` hardcodes `Environment=API_SERVER_PORT=8643`, `mios_pipe/kernel/config.py` + `context/grounding.py` fall back to `8642`, and `mios_pipe/health.py` falls back to `8720`. `hermes-worker.service` is the ONLY unit in the tree running `hermes gateway run`, and it binds a port the SSOT assigns to nothing; `hermes.service` and `hermes-agent.service` -- named by the greenboot probe, by unit comments and by the drift-check external-unit allowlist -- have no unit file, so `[ports].hermes` is addressed by `[urls].hermes` and by agent-pipe's backend while NOTHING binds it. Generalised: **17 executable `os.environ.get("MIOS_PORT_X", "<retired>")` defaults across 12 files** name the right variable and default to a port `[docs].retired_ports` says is gone (`8642`, `8640`, `8441`, `8442`, `8432`, `8633`). `check_doc_port_scheme` enforces Law 5 only over `[docs].port_clean` -- a list of DOCUMENTS -- so no gate has ever scanned executable code. Give `hermes-worker` its SSOT port; resolve the `hermes`/`hermes-agent`/`hermes-worker`/`mios-hermes` name tangle to one canonical unit (Law 9); replace every retired literal fallback with the SSOT value or a hard failure; extend the Law-5 scan to code behind a shrink-only register.
**Where:** `usr/share/mios/mios.toml` (`[ports]`, `[urls]`, `[docs].retired_ports`), `usr/lib/systemd/system/hermes-worker.service`, `usr/lib/mios/agent-pipe/mios_pipe/{kernel/config.py,context/grounding.py,health.py,routing/chat.py,routing/lanes_resolver.py,federation/a2a_client.py}`, `usr/lib/mios/agents/opencode-gateway/server.py`, `usr/lib/mios/gateway-agent/session.py`, `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh`, `automation/98-drift-checks.sh`.
**Done When:** No executable default names a retired port; the only shipped Hermes gateway binds the port the SSOT assigns it; one canonical Hermes unit name; and a gate fails on a new retired-port literal in code, not just in docs.
**Why:** ADR-0016 argues offload is "purely an addressing change". That promise is unkeepable while one service has five addresses and the gate that guards Law 5 has never looked at the code. A gate that reports success over a set excluding the thing it checks -- the tree's recurring defect class.
**Dep:** none -- independent, and it de-risks T-312 by draining the worst of the addressing debt first.
**Status:** done -- operator ruling: ONE Hermes, so ONE key. `[ports].hermes = 8720` survives and `hermes-worker.service` binds it (`Environment=PORT`/`API_SERVER_PORT` were hardcoded `8643`, a port `[ports]` assigned to nothing); `hermes_worker` is deleted. Its Environment block was stale throughout -- `SEARXNG_URL:8888` (retired), `HERMES_BACKEND_BASE_URL:11441` (retired), crawl4ai `11235` and firecrawl `3002` -- all four now carry SSOT values on both the unit and its `[units]` block. The greenboot line probed `hermes.service`, which has no unit file, so `systemctl is-enabled` always failed and the probe could never run; it now names `hermes-worker.service`. All 17 executable `os.environ.get("MIOS_PORT_X", "<retired>")` defaults across 12 files carry their SSOT value, and the 5 test fixtures pinned to the retired pgvector port were fixed too. **The deletion exposed a worse defect:** `[ports.categories]` allocates POSITIONALLY (`base + index * stride`), so removing one member renumbered the five services after it (`daemon_agent`/`model_router`/`arbiter`/`mcp`/`opencode_gateway` each slid down 10) and no gate would have objected -- the result was internally consistent. `render-ports.py` now treats an EMPTY member as a reserved slot that holds its index without naming a port; every other port is byte-identical to before. | **Domain:** Naming/Addressing | **Who:** architect

## T-318 -- ADDR-02: Seven sidecar ports were allocated but never bound  (WS-GUARD | P1 | M)
**Goal:** E-09 One value, one name -- the number in `[ports]` is the number the service binds, or the SSOT is describing a system that does not exist.
**What+How:** MEASURED. `[ports.categories.sidecar]` allocates `guacd 8560`, `redis 8565`, `chrome_cdp 8570`, `otelcol_otlp 8575`, `otelcol_ui 8580`, `pxe_hub_api 8585`, `forge_ssh_git 8590`, under a doc string that says these "were HARDCODED in Quadlets with no SSOT key at all (guacd 4822, redis 6380, Chrome CDP 9222, OTLP 4317, Jaeger 16686, matchbox 8081, Forgejo git-ssh 49922), so nothing could detect a collision when a container was added. Now allocated and collision-checked like everything else." **The second sentence is false.** All seven keys are referenced by ZERO Quadlets and by zero non-doc files anywhere in the tree; the upstream defaults are still hardcoded in the generated `[containers.*]` blocks -- `GUACD_PORT=4822` (mios-guacamole), `REDIS_URL=redis://127.0.0.1:6380` (firecrawl api + worker), `MIOS_CRAWL_CDP_URL=http://127.0.0.1:9222` (crawl4ai), Jaeger `16686` (otelcol Labels), `-address 0.0.0.0:8081` (pxe-hub Exec), `FORGEJO__server__SSH_PORT=49922` (forge). So the keys were lifted for collision-checking and the services were never repointed: the collision checker guards seven numbers nothing binds, while the seven numbers that ARE bound sit outside the SSOT and cannot collide-check at all. Repoint each `[containers.*]` block onto its `${MIOS_PORT_*}` key (both ends of each pair together -- guacd's binder and mios-guacamole's `GUACD_PORT`; the redis container and both firecrawl consumers; the CDP browser unit and crawl4ai), thread the new vars through BOTH allowlists in the quadlet renderer and `97-ssot-lint.sh`, then regenerate. Resolve `MIOS_PORT_CHROME_CDP_WORKER` while there: it is referenced twice in `[units]` with a `:-9223` fallback and has **no `[ports]` key at all**, so the primary/worker CDP split is half-declared.
**Where:** `usr/share/mios/mios.toml` (`[ports.categories.sidecar]` doc string, `[containers.mios-guacamole|mios-webtools-firecrawl-api|mios-webtools-firecrawl-worker|mios-webtools-crawl4ai|mios-otelcol|mios-pxe-hub|mios-forge]`, `[units]`), `automation/15-render-quadlets.sh` + `34-render-quadlets.sh` allowlists, `automation/97-ssot-lint.sh`, the regenerated `usr/share/containers/systemd/*.container`.
**Done When:** Every sidecar port key is referenced by the container that binds it; no upstream-default literal for these seven remains in a `[containers.*]` block; `chrome_cdp_worker` is a real key or the reference is removed; and a gate fails when a `[ports]` key is bound by nothing -- the check that would have caught this.
**Why:** A port allocated but not bound is worse than an unallocated one: it makes the collision checker report safety over a set that excludes every number actually in use. It also blocks T-312 -- a canonical `[urls]` entry for `guacd` would point at 8560 while guacd listens on 4822, which is a worse lie than having no entry. And it defeats offload outright: a service whose real port is not in the SSOT cannot be re-addressed by an `/etc/mios` overlay, which is the whole mechanism ADR-0016 Decision 1 rests on.
**Dep:** none -- independent, and a prerequisite for draining those seven from T-312's register.
**Status:** done -- the GATE landed and four of the seven are drained. `check_ports_bound` (tools/check-ports-bound.py) requires every numeric `[ports]` key to be referenced as `MIOS_PORT_<KEY>` by at least one file that could bind or dial it -- the SSOT itself, docs, generated projections and the task ledgers are excluded, because a surface that only DESCRIBES a port never proves one is bound. A key referenced nowhere and absent from the shrink-only `[ports].unbound` register fails; a key that IS referenced but still sits in the register also fails, so the register can only shrink. Run cold against the tree it independently reproduced exactly the seven found by hand. DRAINED (both ends moved together, and the rendered Quadlets now carry the placeholder): `guacd` -- its Exec had NO `-l` flag at all, so it bound the upstream default; now `-l ${MIOS_PORT_GUACD:-8560}` with mios-guacamole's `GUACD_PORT` following. `redis` -- the valkey listener plus BOTH firecrawl clients (`REDIS_URL` and `REDIS_RATE_LIMIT_URL` twice each). `pxe_hub_api` -- matchbox `-address`, a single end. `forge_ssh` -- **this one was a live bug**: `44-firewall-ports.sh` opens `MIOS_PORT_FORGE_SSH` (8410) while Forgejo listened on 49922, so git-over-SSH was firewalled off; it now binds what the firewall opens. All four are threaded through BOTH allowlists in `34-render-quadlets.sh` and both `userenv.sh` twins (still byte-identical, Law 13); `97-ssot-lint` went 12 -> 16 placeholders, 0 orphans. REGISTERED WITH REASONS, not drained: `chrome_cdp` (two CDP endpoints, :9222 primary and :9223 worker, share ONE key, and `MIOS_PORT_CHROME_CDP_WORKER` is referenced by `[units]` with no key at all -- the split is half-declared and needs deciding, not guessing); `otelcol_otlp`/`otelcol_ui` (the image is `jaegertracing/all-in-one:latest`, unpinned, and the v1/v2 env models for the OTLP and query ports differ, so a guess would relist a number the service does not bind -- note the Labels advertising :16686 are CORRECT today and must not move before the binding does); `forge_ssh_git` (a THIRD forge SSH number for a server with one SSH listener -- retire or assign deliberately). 15 assertions in `tools/test_check-ports-bound.py`, including one that fails if any of the four drains regresses, plus a two-case negative test proven by sabotage. 

**CLOSED.** All three remaining keys are resolved, and the last one was a live bug.

* **`otelcol_otlp` / `otelcol_ui` -- DRAINED.** The blocker was "the image is `jaegertracing/all-in-one:latest`, unpinned, and the v1/v2 env models differ". Measured rather than guessed: the `all-in-one` repository has NO 2.x tag at all (Jaeger v2 ships as `jaegertracing/jaeger`), and `:latest` and `1.76.0` were pushed the same day with the same digest -- so it is the v1 line, full stop. Upstream v1.76.0 source confirms the two flags (`cmd/query/app/flags.go`: `query.http-server.host-port`; `cmd/collector/app/flags/flags.go`: prefix `collector.otlp.grpc` + `host-port`, default `:4317`) and the flag->env mapping (`internal/config/config.go`: `AutomaticEnv()` with `NewReplacer("-","_",".","_")`, no `SetEnvPrefix`). So `COLLECTOR_OTLP_GRPC_HOST_PORT` and `QUERY_HTTP_SERVER_HOST_PORT` are the names, corroborated in-tree by the already-working `COLLECTOR_OTLP_ENABLED`. The image is now PINNED at `1.76.0` in `[image.sidecars]`, the bound-images list and the container's inline default; both ports are bound; the `:16686` Labels moved WITH the binding, as this entry required; and the one client moved too -- `[observability].otel_endpoint` was the literal `http://localhost:4317`, restating a port the SSOT owns. `otelcol_ui` also drained from T-312's register into `[urls]`, since a Jaeger UI is exactly the browser-openable surface `[urls]` is for; `otelcol_otlp` stays registered because `[observability].otel_endpoint` is already its one canonical name.

* **`forge_ssh_git` -- RETIRED.** It named a second Forgejo SSH listener that does not exist: `FORGEJO__server__SSH_PORT` and `FORGEJO__server__SSH_LISTEN_PORT` both resolve `MIOS_PORT_FORGE_SSH`, so there is one listener on 8410. Removed from `[ports]`, both registers and the category; index 6 of `sidecar` is now a RESERVED slot (`""`) so retiring it renumbered nothing.

* **`chrome_cdp` -- PINNED, SPLIT, and it was a LIVE BUG.** `usr/bin/mios-chrome` reads `MIOS_CHROME_CDP_PORT`, which the resolver emits as an alias of `MIOS_PORT_CHROME_CDP` -- so on any host with the MiOS environment loaded it launched Chrome with `--remote-debugging-port=8570`, while the flatpak flags file, `mios-hermes-browser`, crawl4ai and `[browser].cdp_url` all dialled 9222. The one consumer that HAD adopted the SSOT key was therefore the one consumer talking to nobody: exactly the harm "a port allocated but not bound" predicts, realised. Resolution: CDP is pinned at its real numbers (`chrome_cdp = 9222`, `chrome_cdp_worker = 9223`) rather than derived into the 8xxx band, because it is an external contract like DNS/53 -- DevTools, Playwright and `chrome://inspect` assume 9222 -- and because the primary browser's binder is `usr/share/mios/flatpak-flags/com.google.ChromeDev.flags`, a static flatpak argument file that cannot template a placeholder. `chrome_cdp_worker` is now a real key, closing the half-declared split (`[units]` referenced `MIOS_PORT_CHROME_CDP_WORKER` with a `:-9223` fallback and no `[ports]` entry). Every templatable consumer was repointed: `mios-chrome` onto the canonical name, `mios-hermes-browser` (whose fallback IS the primary binder, since the primary unit sets no `HERMES_BROWSER_CDP_PORT`), `mios-open-url`, `mios-cdp-fetch`, `mios-crawl4ai-service.py`, `[browser].cdp_url` and the crawl4ai Quadlet. No port number moved, so nothing could break.

**Standing:** 40 ports, **39 bound, 1 registered** (`chrome_cdp_worker`, whose only binder is an `Environment=` literal in a shipped `.service` -- systemd does not expand `${}` there, and the `[units]` placeholder that would render it is inert until T-317). `97-ssot-lint` went 16 -> 19 placeholders, 0 orphans; both `userenv.sh` twins stay byte-identical. Found and fixed en route in `mios-open-url`: `--profile` parsed into a variable nothing read, so the flag silently did nothing; it now says so. | **Domain:** Naming/Addressing | **Who:** architect





## T-323 -- MINI-02: A seat could not tell an unreachable blade from a broken model  (WS-BLADE | P1 | S)
**Goal:** E-09 One value, one name -- and one place to ask the only question a seat has.
**What+How:** MEASURED, live. `mios_pipe/routing/lanes.py` documents its own behaviour: *"The terminal (light) lane is returned as the floor even if its own probe is failing, so a turn degrades rather than dead-ends."* On a blade that is exactly right -- the light lane is local and nearly always up. On a SEAT every lane is remote, so `pick()` hands back a `Lane` pointing at a machine that is not there and the failure surfaces as a transport error on the next request. Reproduced by driving the real resolver with an all-dead probe: `pick("default") -> Lane('light', 'http://blade-01.mesh.mios.local:8500/v1', ...)`. For a seat that is the single most important distinction in the system -- *is the model broken, or is my blade gone?* -- and nothing answered it. `mios blade status` now does.
**Where:** `usr/lib/mios/blade.sh` (`_ssot_offload_targets`, `_url_is_local`), `usr/libexec/mios/mios-blade` (`status`), `tests/test-blade-reachability.sh`, `.github/workflows/mios-ci.yml`, `tools/check-role-ssot.py`.
**Done When:** One command reports every address this blade offloads to, whether each is local or remote, and whether it answers; a seat with an overlay reads REMOTE and a blade without one reads local; and it is proven against a real socket, not a mock.
**Why:** Deliberately NOT changed: the resolver's degrade-to-terminal behaviour, and `[greenboot].blade_reachability_critical = false`. A seat must not roll itself back because its blade rebooted (Law 12), and the hot path must not gain a new failure mode. The fix is DIAGNOSIS, not policy -- zero changes to routing.
**Dep:** after T-322, which is where the constraint was first written down.
**Status:** done -- `mios blade status` gained an **Offload targets** section listing `[ai].endpoint`, `[search].endpoint` and every `[nodes.*].endpoint` resolved through the merged overlay, each labelled `local`/`REMOTE` and `up`/`UNREACHABLE`. The local-vs-remote column IS the seat/blade tell: with no overlay every target is local; with a seat's overlay the offloaded ones read REMOTE. `${MIOS_PORT_*}` placeholders are expanded from the environment the resolver already populates -- never a second resolution of the TOML -- and an unexpanded one is reported `UNRESOLVED` rather than probed as a literal URL, since a URL with a `${...}` in it would always "fail" and hide the real problem.

Proven end to end against a REAL listening socket on an EPHEMERAL port: one target up, one target dead, and the nodes the overlay does not name still local. The ephemeral port matters -- the first version used a fixed one and passed against a stale listener left over from a manual run, which is the same "reports success over nothing" failure this ledger keeps recording, committed while writing the test for it. 6 assertions in `tests/test-blade-reachability.sh`, wired into CI, and proven by sabotage: collapsing the local/REMOTE label turns it red.

**Gate defect found and fixed en route.** `check_role_ssot`'s no-archetype-literal rule fired on `blade.sh` for the word `endpoint` -- inside the embedded python that READS `[blade.archetypes]`, where `endpoint` is a TOML key (`[ai].endpoint`), not a role. The rule now skips heredoc bodies, since a heredoc is not shell control flow, and a case arm AFTER the heredoc closes is still caught -- otherwise the exclusion would become a way to hide anything. Both directions asserted (31 assertions). | **Domain:** Topology/SSOT | **Who:** architect

## T-322 -- MINI-01: What actually differs between MiOS-Mini and a hosted MiOS  (WS-BLADE | P1 | S)
**Goal:** E-08 Derived surfaces are generated -- including the document that explains the design, because that is the one that rots first.
**What+How:** The requirement is a COMPARISON, and none existed: the difference between a seat and a fully hosted blade was spread across ADR-0016, `[blade.*]`, `[greenboot]` and half a dozen task entries, with no single place stating it and nothing keeping any of it true. Write it once, as a PROJECTION: `tools/generate-mini-vs-hosted.py` derives every number from `[blade.archetypes]`, `[blade.requires]`, `[blade].seat_side` and `[greenboot]`, emits `usr/share/doc/mios/reference/mini-vs-hosted.md`, and `check_mini_vs_hosted` (gate 175 of 176) regenerates in memory and diffs. A hand-edit fails; the file being absent fails.
**Where:** `tools/generate-mini-vs-hosted.py`, `tools/test_generate-mini-vs-hosted.py`, `usr/share/doc/mios/reference/mini-vs-hosted.md`, `tools/sync-generated.sh` (step 4a), `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`, `tools/check-manual-links.py`.
**Done When:** One document states the difference surface by surface; every number in it derives from the SSOT; a gate fails on a hand-edit; and the docs tree has no dangling explicitly-relative link.
**Why:** A prose comparison is exactly the artefact that goes stale the moment an archetype gains a capability -- and this tree already proved it: `audit-INDEX.md` linked to `audit-mios-mini.md` for the entire period after ADR-0016 Decision 3 reassigned that name to MiOS-Metal, and nothing noticed, because the link gate only ever covered `manual.md -> manual/ch*`.
**Dep:** after T-312/T-313/T-315/T-319 -- the comparison is only worth generating once the numbers it reads are true.
**Status:** done -- **the headline: a seat starts 6 units, a fully hosted `hybrid` starts 50, and they are the same image.** No MiOS-Mini Containerfile, no MiOS-Mini tag, no conditional bake; a seat is `[blade].type = "endpoint"` plus an `/etc/mios` overlay, and every difference is a RUNTIME difference. The document also pins the seat's defining constraint, which no prior entry stated: **a seat has zero local inference lanes.** All four -- `mios-llm-light`, `mios-llm-heavy`, `mios-llm-heavy-alt`, `mios-cpu-node` -- are capability-gated off, INCLUDING the lane `mios_pipe/routing/lanes.py` calls "the always-on floor" and forces terminal in every chain. When the blade is unreachable a seat has a front door that can reach nothing, and `[greenboot].blade_reachability_critical = false` means it does not roll back over it -- correct under Law 12, but it means the failure is silent. The model weights are baked regardless (Law 12 BAKE-NOT-FETCH), so a seat carries granite-4.1-8b, lfm2-700m and embeddinggemma and never loads any of them.

Greenboot behaves correctly on a seat and the document proves it: **1 of 4 critical services is probed** (`agent-pipe`, seat-side), the other three are skipped because their capability markers are absent -- the T-314 `_blade_activates` guard working, now visible in a table rather than asserted in a commit message.

**Found while writing it:** the docs tree had 4 dangling EXPLICITLY-relative links, one of which was `audit-INDEX.md -> ./audit-mios-mini.md`. `check_manual_links` now also asserts that every `./x` or `../x` link anywhere under `usr/share/doc/mios` resolves. Deliberately NOT widened to repo-root-relative paths (`usr/share/...`, `CLAUDE.md`): resolving those as file-relative would invent ~190 false findings, and a register that large is a campaign, not a gate. The narrow class is unambiguous and is now at zero. 4 new cases in `tools/test_check-manual-links.py` (9/9), including one asserting a repo-root-relative path stays OUT of scope.

10 assertions in `tools/test_generate-mini-vs-hosted.py`, three of which prove the numbers are DERIVED rather than typed -- add a gated unit and the hosted count moves; add a `seat_side` unit and BOTH totals move, because `seat_side` runs everywhere and is therefore not a difference between them. Two-case negative test proven by sabotage. | **Domain:** Docs/SSOT | **Who:** architect

## T-321 -- ADDR-04: A generator rewrote its own evidence  (WS-GUARD | P1 | S)
**Goal:** E-08 Derived surfaces are generated -- but a generator must not generate the test that proves it.
**What+How:** MEASURED. `tools/render-ports.py` documents itself as rewriting the flat `[ports]` table; it also runs `sync_fallbacks()`, which treats every `${MIOS_PORT_X:-N}` in `automation/`, `usr/`, `etc/` AND `tools/` as GENERATED and rewrites it to the SSOT value. That is right for source and wrong for a fixture: `tools/test_check-port-fallbacks.py` carries deliberately stale literals, because a fixture holding the CORRECT value produces no finding and its assertion then passes over nothing. Every full `sync-generated.sh` run silently corrected those fixtures and turned three assertions inert. `_SWEEP_SKIP` now excludes `/tools/test_` and `/tests/`, and `tools/test_render_ports.py` guards BOTH directions -- no fixture in the sweep, and the sweep still covering real source (>200 files, `mios-open-url` among them). Proven by sabotage: deleting the skip turns the guard red.
**Where:** `tools/render-ports.py` (`_SWEEP_SKIP`), `tools/test_render_ports.py`, `tools/test_check-port-fallbacks.py`, `usr/share/mios/mios.toml`, `tools/check-service-urls.py`, `tests/test-offload-overlay.py`.
**Done When:** No generator rewrites a test fixture; a gate fails on an address an `/etc/mios` overlay cannot move; and the offload proof covers local, localhost AND remote.
**Why:** Two defects of the same shape met here. A generator that fixes its own tests reports success over nothing -- the family this repo keeps finding. And `check_port_fallbacks` only exists because `sync_fallbacks` sees ONE idiom: it rewrites `${X:-N}` and is blind to `get("X","N")`, `... or N`, `Environment=X=N`, `_MiosPort 'X' N` and the `MIOS_<KEY>_PORT` alias -- which is exactly where all 54 stale literals in T-320 were hiding.
**Dep:** follows T-320, which produced the fixtures this protects.
**Status:** done -- and it surfaced a second finding that goes to the heart of MiOS-Mini. **Four addresses in operator-tunable sections hardcoded a bare port**: `[ai.host_thresholds].micro_endpoint` (:8500), `[browser_ai].provider_url` (:8200), `[converge.gateway].fallback_http` (:8720) and `[search].endpoint` (:8800). A bare port cannot be offloaded -- there is no key for an `/etc/mios` overlay to move -- so those four services were pinned to the machine no matter what a seat's overlay said. All four now template their `[ports]` key, and `check_service_urls` gained `bare_port_addresses()`: any `localhost`/`127.0.0.1` URL naming a declared port outside `[units]`/`[containers]` fails. 7 assertions plus a negative case proven by sabotage.

The offload proof was also RED and had to be rebuilt: scoping `[urls]` in T-312 removed the keys it asserted on. It now exercises the canonical keys (`[ai].endpoint`, `[search].endpoint`) plus a surviving tile, pins that the four inter-service keys left `[urls]` and that every remaining value is `http(s)`, and adds the assertion the requirement's own wording demanded -- **`test_local_localhost_and_remote_are_one_mechanism`**, which resolves the SAME overlay against `blade-01.mesh.mios.local`, `localhost` and a LAN IP and asserts all three land. "local, localhost or remote" are three VALUES of one mechanism, not three designs, and that is now executable.

CANDID NOTE for whoever reads this next: the breakage was invisible for a round because the ad-hoc shell loop used to report suite status was itself broken -- `printf '%s %s' "$(basename $t)" "$([[ $? -eq 0 ]] && echo PASS || echo FAIL)"` takes `$?` from `basename`, which always succeeds, so it printed PASS unconditionally. CI was never fooled: `.github/workflows/mios-ci.yml` runs the offload proof and the `tools/` sibling tests explicitly and would have failed. The lesson is the one this whole ledger keeps repeating, applied to the verification itself. | **Domain:** Build/SSOT | **Who:** architect

## T-320 -- ADDR-03: The front door bound a retired port  (WS-GUARD | P1 | M)
**Goal:** E-09 One value, one name -- the number a program falls back to is the number the SSOT says, or the SSOT is decoration.
**What+How:** MEASURED, while auditing what a seat actually runs. `usr/lib/systemd/system/mios-agent-pipe.service` carried `Environment=MIOS_PORT_AGENT_PIPE=8640` -- an UNCONDITIONAL assignment, and 8640 is in `[docs].retired_ports`. The agent-pipe binds whatever that variable says (`mios_pipe/kernel/config.py`: `PORT = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8700"))`), while `MIOS_AI_ENDPOINT` -- read by 72 tracked files -- resolves `http://localhost:8700/v1`. The front door listened where nobody knocked. Its own `[units]` block said `${MIOS_PORT_AGENT_PIPE:-8700}`, which is exactly T-317's stated harm on the most important unit in the tree. Three more units did the same: `mios-agents` pinned `MIOS_PORT_CODE_SERVER=8800` (which is SearXNG's live port), `mios-opencode-gateway` pinned the retired 8633 while its own `server.py` had already moved to 8780, and `mios-pgvector-backup` pinned the retired 8432, so the backup job dialled a database that is not there.
**Where:** `usr/lib/systemd/system/*.service`, `tools/native/mios-unit-gen/tests/golden/*`, `usr/libexec/mios/*`, `usr/lib/mios/**`, `usr/share/mios/mios.toml` (`[ports].stale_fallbacks`), `tools/check-port-fallbacks.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`.
**Done When:** No file pairs a `MIOS_PORT_<KEY>` name with a literal that disagrees with `[ports].<key>`; a gate fails on a new one; and the gate sees every idiom that hid one.
**Why:** `EnvironmentFile=` overrides `Environment=` regardless of line order (verified against upstream systemd's own `systemd.exec` documentation: *"Settings from these files override settings made with Environment="*, and the compiled-sources list puts `EnvironmentFile=` after `Environment=`), so `/etc/mios/install.env` could still move these ports -- the pin was a DEFAULT, not a block. That is what made this survivable and also what made it invisible: on a host with the env materialised the right number wins, and the wrong one only appears where the env is not loaded. Which is precisely the seat case, the firstboot case, and the Windows case.
**Dep:** none. Overlaps T-316 (17 executable retired-port fallbacks), which measured a narrower set with no gate behind it.
**Status:** done -- **54 stale literals across 50 files**, swept to their SSOT values; `check_port_fallbacks` (gate 173 of 173) now fails a new one. Severity ran in two bands. UNCONDITIONAL: the four `Environment=` pins above plus their four golden copies. ALWAYS-LIVE: `usr/libexec/mios/Setup-MiOSLanPortProxy.ps1` mapped ELEVEN ports under the comment *"Values mirror mios.toml [ports]"* -- and not one of the eleven did; they were an entire previous generation (8300/8033/8800/8090/8450/8899/8642/8119/8080/8444/8389). It runs on the WINDOWS side, where `MIOS_PORT_*` is never set, so the fallback was always what ran: the LAN port proxy forwarded eleven wrong ports, every time. The rest were `${X:-N}` / `get("X","N")` floors across the agent tooling.

Three idioms had to be found before the gate was honest, and each was found by the previous one failing to catch something. (1) The plain fallback. (2) The DOUBLE fallback -- `int(e.get("MIOS_PORT_PGVECTOR", "8600") or 8432)`, where the first sweep corrected the first literal and left the second, which is the one that runs when the variable is set-but-empty; nine files carried it. (3) The `MIOS_<KEY>_PORT` alias spelling (`MIOS_ARBITER_PORT`, `MIOS_DAEMON_AGENT_PORT`, `MIOS_OSCONTROL_PORT`) -- and `findings()` early-outed on `"MIOS_PORT_" not in body`, so a file using ONLY the alias was never opened at all. Its own unit test caught that; `mios-pc-control` was dialling 11437 for a service on 8950.

18 assertions in `tools/test_check-port-fallbacks.py` -- one per idiom, plus a comment (never a finding), a `[ports]`-less name (ignored), the register in both directions, and a guard that the walk actually visits >200 files, since a gate that scans nothing reports success over nothing. Four-case negative test proven by sabotage. `[ports].stale_fallbacks` ships EMPTY and shrink-only. One agent-pipe test had to change with the sweep and is worth naming: `test_mios_pg.py` asserted `d["port"] == 8432` -- the test ENCODED the retired number, so it would have gone red on the fix and green on the bug. It now reads `[ports].pgvector` from the SSOT instead of restating it, which is the same rule the gate enforces, applied one level up. | **Domain:** Naming/Addressing | **Who:** architect

## T-319 -- BLADE-05: The activation axis gates 3 of 23 services  (WS-BLADE | P1 | M)
**Goal:** E-09 One value, one name -- "a seat runs only what it needs" is a STATED taxonomy, not an empty default that silently means "everything".
**What+How:** MEASURED, and this is the gap between what ADR-0016 claims and what ships. The addressing half of offload is proven (`tests/test-offload-overlay.py`); the ACTIVATION half is a stub. `[blade.requires]` -- the capability->unit map that decides what a blade type starts -- had exactly ONE entry, `mios-llm-heavy`, against 22 Quadlet containers and 82 `mios-*.service` units, and exactly one capability drop-in existed (`blade-gpu-serving.conf`). So a seat (`[blade].type = "endpoint"`, which correctly expands to NO capabilities) skipped exactly one unit -- and that one is already gated off by default on VRAM grounds. **"MiOS-Mini offloads all services" was false: a seat started llm-light, pgvector, agent-pipe, searxng, crawl4ai, firecrawl, guacamole, forge, code-server and the rest, i.e. a full MiOS that also happened to point at a blade.** Added the two remaining GPU lanes on evidence (`mios-llm-heavy-alt` and the `mios-llm-worker@` template both carry a GPU device reference; `mios-cpu-node` and `mios-pgvector` do not), then built `check_blade_coverage` so the rest cannot stay silently unclassified. REMAINING, and it is a design decision rather than a defect: assign the 20 registered services to capabilities. The archetype vocabulary already exists (`gpu-serving`, `controller`); the open question is which services are core-of-core that a seat genuinely runs (the UX -- open-webui, guacamole/guacd, cockpit-link) versus serving-plane that a seat offloads (llm-light, cpu-node, pgvector, searxng, the three webtools, otelcol, forge + runner, ceph, k3s, pxe-hub, adguard). Each new capability needs an archetype that grants it, or the gate rejects it as unactivatable.
**Where:** `usr/share/mios/mios.toml` (`[blade.requires]`, `[blade.archetypes]`, `[blade].ungated`), `tools/check-blade-coverage.py` + `tools/test_check-blade-coverage.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`, `automation/48-mios-dropin-fanout.sh` (consumes the map at bake).
**Done When:** Every container is capability-gated or registered with a reason; a seat archetype leaves the serving plane condition-skipped and a `mios blade status` on an endpoint shows it; and the register is empty or every remaining entry names a service that genuinely runs everywhere.
**Why:** This is the half of MiOS-Mini that is NOT addressing. A seat that offloads its addresses but still starts every service has not offloaded anything -- it has doubled the work, running local copies while pointing at remote ones. ADR-0016 Decision 4.
**Dep:** none hard. The taxonomy is the operator's call; the gate makes the gap visible and un-forgettable in the meantime.
**Status:** done -- the taxonomy came from the requirement itself: *"MiOS-Mini is the full image just meant to offload ALL services"*. So every declared container requires `service-plane`, which every archetype grants EXCEPT `endpoint`; the three GPU lanes additionally require `gpu-serving` (repeated `ConditionPathExists` is an AND, so a lane needs both markers). Result, measured: hybrid 23/23, compute 23/23, controller 20, headless 20, desktop 20, **endpoint 0**. Only the seat's behaviour changes -- every other archetype activates exactly what it did before, because the GPU lanes were already skipped wherever `gpu-serving` was absent. The `[blade].ungated` register is DRAINED to `[]` and `check_blade_coverage` (gate 170) keeps it there: 23 of 23 capability-gated. `tests/test-seat-activates-nothing.py` is the executable definition of MiOS-Mini -- 8 assertions covering that the seat grants nothing, starts nothing, that no container is ungated, that non-seat roles still start the plane, that only GPU archetypes start the GPU lanes, that every required capability is grantable, and that a drop-in exists for each -- proven by sabotage (returning one container to ungated turns it red) and wired into CI. EXTENDED after the gate's OWN blind spot surfaced: `check_blade_coverage` counted CONTAINERS only and reported "23 of 23" over a set that excluded **18 long-running native `.service` units**, every one of which a seat still started. It now classifies **40 units** (containers and native units share one namespace -- a Quadlet named `x` generates `x.service`) into exactly one of three: capability-gated, `[blade].seat_side`, or the shrink-only `[blade].ungated` debt register. `seat_side` is a POSITIVE declaration rather than debt, because "offload all services" cannot mean "start nothing": a seat with no `mios-agent-pipe` has no way to reach its blade. Serving units gated off (`hermes-worker`, `k3s`, `mios-account-sync`, `mios-agents`, `mios-cron-director`, `mios-daemon`, `mios-finetune-serve`, `mios-mcp`, `mios-opencode-gateway`, `mios-policy-arbiter`); seat-side kept (`mios-agent-pipe`, `hermes-dashboard`, both CDP browsers, `mios-hermes-tail`, both `ttyd` bridges). EXTENDED AGAIN, because hand-classification could not have found the next layer. A DERIVED rule -- a unit that ACTIVATES a gated unit must carry that unit's capabilities, or it starts where its dependency is condition-skipped and fails forever -- flagged **11 units nobody had classified**: `mios-pgvector-backup`, `mios-embed-backfill`, `mios-skills-miner`, `mios-userdb-render`, `mios-sys-env-refresh`, `mios-passport-provision`, the three forge provisioners, `mios-k3s-master.target` and `hermes-worker`. Two of them carry `Requires=mios-pgvector.service`, so on a seat those timers would fire forever against a database the machine does not run -- which disproves the "a oneshot costs a seat nothing" assumption the gate's earlier scope rested on. Ten are now gated; `hermes-worker` is exempted in `[blade].soft_ok` because its pull is `Wants=` and it degrades to the light lane, so gating it `gpu-serving` would stop it on three archetypes where it works today. Two distinctions keep the rule correct rather than merely strict: `After=` is ordering and activates nothing, so it never propagates a gate; and "must be classified" is a different set from "may be gated" -- a oneshot needs no classification of its own but may legitimately be gated for what it activates. Standing: 40 units require a classification (33 gated, 7 seat-side, 0 ungated), plus 10 gated for what they activate. Proven by sabotage in three directions: ungate a container, ungate a unit that Requires a gated one, and empty the soft_ok exemption. Follow-ups noted rather than fixed blind: (1) the `controller` capability is GRANTED by two archetypes but REQUIRED by no unit, so it is decorative -- the gate checks that every required capability is grantable but not the converse; (2) `mios-cockpit-link` exists BOTH as a shipped `.service` (systemd-socket-proxyd) and as a `.container` whose Quadlet generates the same unit name, and generator output in `/run/systemd/generator` outranks `/usr/lib/systemd/system`, so the shipped unit is shadowed -- one of the two is dead and it is not clear which is intended. | **Domain:** Topology/SSOT | **Who:** architect

**Capability closure (landed with T-315).** `controller` was granted by four archetypes and required by NO unit, so a `controller` blade behaved exactly like a `headless` one -- a decorative capability, the same failure class as `[profile].role`. `mios-pxe-hub` now requires `["controller", "service-plane"]`: BLADE-01's own text names Matchbox/PXE as the controller-blade case, and the unit is `disable`d in `90-mios.preset` today, so gating it costs nothing that currently runs. `check_role_ssot` now enforces the REVERSE of `check_blade_coverage`'s rule -- every capability an archetype grants must be required by some unit -- so a decorative capability cannot come back.

**DECIDED (was open):** `mios-k3s` runs `k3s server`, a cluster control plane, and now requires `controller`. Blast radius measured before the change: the DEFAULT is unchanged -- `[blade].type = "hybrid"` grants `controller`, as do `controller`, `k3s-master` and `ha-node`. Only an explicitly-chosen `compute`, `desktop` or `headless` blade stops running it, which is the plain meaning of those names; `hybrid`'s own target wants `k3s-agent.service`, the AGENT, not the server.

**Also decided: the seat/blade line, and one unit that was on the wrong side of it.** A seat runs what the PERSON touches; a blade runs what the WORK needs. `mios-hermes-browser-worker` was `seat_side` and is not the person's browser -- it is a second headless Chrome on `profile-w2` whose only client is `hermes-worker`, which a seat does not run, so a seat started a browser for a worker it did not have. Now gated with its consumer; only the seat changes. The rule is mechanical and the mechanism is why it was missed: **the AI plane couples over ADDRESSES, not unit dependencies**, so the `Requires=`/`Wants=` walk that found eleven dependency violations structurally could not see this one (`hermes-worker` reaches it through `BROWSER_CDP_URL`). `check_blade_coverage` now also reads the port graph -- a seat-side unit binding a port whose every OTHER namer is gated fails -- with the person-facing exemption DERIVED, not declared: a port is person-facing when it has a browser-openable `[urls]` entry or is the one `[ai].endpoint` resolves. That is exactly why `mios-agent-pipe` is legitimate seat-side and the worker browser is not. 5 assertions in `tools/test_check-blade-coverage.py` plus a negative case proven by sabotage.

## T-317 -- UNITGEN-01: `[units]` is an SSOT that projects to nothing  (WS-BLADE | P1 | L)
**Goal:** E-08 Derived surfaces are generated -- a unit file is projected from the SSOT and proven so, or the SSOT is not one.
**What+How:** MEASURED, then closed in three moves. (1) **The renderer stopped inventing.** It injected a hardening baseline into every non-unconfined `[Service]`, so its output looked plausible while `[units.*]` stayed silent -- 20 shipped units carry hardening, 10 declare it. Removing the injection made the gap visible instead of hiding it. Four mechanical bugs went with it: sections came out in ALPHABETICAL order (fixed with `toml` `preserve_order`), each section's `comment` was emitted as a literal `comment=` directive that is not a systemd key at all, booleans rendered `AllowIsolate=true` where systemd's own spelling is `yes`, and no blank line separated sections. (2) **The golden master is gone.** `tests/golden/` was 172 files -- a byte copy of `usr/lib/systemd/system` -- and `test_golden_master_matches_systemd_tree` diffed the tree against it without ever calling the generator. It proved a copy is a copy, and it was RED when this task was picked up, because `hermes-worker.service` had been migrated in the tree and not in the copy. Deleted, along with `verify_golden_master()`; `tests/projection.rs` now renders FROM `mios.toml` and compares to the tree. (3) **The debt is counted.** `[unit_projection]` is a shrink-only register with a `max_drift` ratchet; `check_unit_projection` (gate 176) enforces its hygiene with no toolchain at all, and additionally runs `mios-unit-gen --check` when a built binary is present.
**Where:** `tools/native/mios-unit-gen/src/{lib,main}.rs`, `tools/native/mios-unit-gen/tests/projection.rs` (replaces `golden_master.rs`), `tools/check-unit-projection.py` + `tools/test_check-unit-projection.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`, `usr/share/mios/mios.toml` (`[unit_projection]`), 16 unit files under `usr/lib/systemd/system/`.
**Done When:** met on three of four clauses, and the fourth is stated rather than claimed. The golden test renders from `mios.toml`: **done**. `--check` runs in the drift gate: **done**. A hand-edit contradicting `[units.*]` fails the gate: **done for the 29 units that render faithfully, NOT for the 39 in the register** -- for those the gate asserts only that the register itself is honest. `render_units()` reproduces every shipped unit byte-for-byte: **not done, and not claimed**. The 68 declared units go from 68 drifted to **29 faithful / 39 registered**.
**Why:** This is why `hermes-worker.service` could bind a retired port while its own `[units]` block named a different one. A golden master that compares a copy to a copy is the tree's recurring defect class in its purest form: a gate reporting success over a set that excludes the thing it checks.
**Dep:** none -- independent.
**Status:** done

Standing numbers, reproducible with `MIOS_ROOT=. mios-unit-gen --check`:

| | count |
|---|---|
| shipped units in `usr/lib/systemd/system` | 120 |
| declared in `[units.*]` | 68 |
| of those, rendering faithfully | **29** |
| of those, registered in `[unit_projection].drift` | **39** (ceiling `max_drift = 39`) |
| shipped but NOT declared at all | **52** |

Draining one entry: `mios-unit-gen --render <unit> | diff - usr/lib/systemd/system/<unit>`, correct `[units.*]` (the file on disk is what boots, so it wins), then lower `max_drift`. The register only shrinks -- `tests/projection.rs` fails an entry that has STOPPED drifting as loudly as one that starts, so the count cannot be padded, and `check_unit_projection` refuses a ceiling left above the real count.

Four findings from the work, recorded honestly:
* **16 units were normalised, not fixed.** Their only difference from the rendering was blank-line placement. The tree is not consistent here -- measured across every shipped unit, a section is separated from the next by a blank line 208 times and glued 16, and a file's leading comment block is glued to its first header 94 times and separated 23. The renderer follows both majorities and those 16 files were rewritten to match. Whitespace-only was ASSERTED before each write, not assumed.
* **`[units]` does double duty.** `[units."x.service".Unit]` is the projection, but the same table also holds 16 bare `agent_pipe = "mios-agent-pipe.service"` name aliases for the globals resolver. Counting both made the projection look 16 units wider than it is. That is a Law 9 ONE-CANONICAL-NAME smell -- one table, two meanings -- left in place because splitting it moves emitted `MIOS_UNITS_*` names.
* **52 of 120 units are outside the projection entirely**, and that is the larger debt behind this entry. The register bounds only what `[units.*]` claims; a unit it never mentions is not drifting, it is unmanaged.
* **The negative test's second case was wrong on its first draft, and only checking it caught that.** Its "remove the last register entry" regex was unanchored, matched the end of `[security.privileged_units].unconfined` instead, and the case then passed on the ceiling mismatch while proving nothing about the register. Anchored inside `[unit_projection]`, with an in-mutation assert that an entry actually left, it now fails naming the dropped unit. | **Domain:** Build/SSOT | **Who:** build agent

## T-324 -- ADDR-05: Retired ports live on in shipped units and Quadlets  (WS-GUARD | P1 | M)
**Goal:** E-05 One canonical address per lane -- a retired port number cannot survive anywhere a machine or a person will read it.
**What+How:** MEASURED while deleting `tests/golden/`, which had been hiding six units carrying retired ports. Deleting it removed the hiding place, not the cause: **`check_doc_port_scheme` scans only the files named in `[docs].port_clean`**, an explicit allow-list of markdown, and no unit file or Quadlet has ever been on it. Sweeping `usr/lib/systemd/system` + `usr/share/containers/systemd` against `[docs].retired_ports` finds 23 occurrences across 9 files. Six are NOT comments:

| site | occurrence | why it matters |
|---|---|---|
| `mios-llm-heavy.container:32,33` | `Label=...openInBrowser=http://localhost:11441/v1/models` | a browser-openable label pointing at a retired port -- Podman Desktop offers the operator a dead link |
| `mios-agent-pipe.service:80` | `Environment=MIOS_KV_PAGING_HINTS=11436,11450` | `11450` is retired; the hint list names a lane that is gone |
| `mios-pgvector-backup.service:64` | `PORT="$MIOS_PORT_PGVECTOR"; [ -z "$PORT" ] && PORT="8432"` | a retired FALLBACK -- exactly the T-316 class, on the backup job |
| `mios-account-sync.service:16`, `mios-sys-env-refresh.service:36`, `mios-userdb-render.service:13` | `podman exec mios-pgvector pg_isready ... -p 8432` | **ambiguous -- do not "fix" blind** |

That last row is why this is its own task and not a drive-by. `8432` is in `[docs].retired_ports` as a HOST port key, but these three run `pg_isready` **inside** the container via `podman exec`, where the address is postgres's INTERNAL listen port -- and `mios-pgvector-backup.service:42` states in its own comment that the container's postgres listens on 8432. If that is true, the three are correct and the registry is what is wrong, because it conflates a host key with a container-internal one. Establish which before changing any of them: a wrong edit here breaks the readiness probe on the agent datastore.
**Where:** `automation/98-drift-checks.sh` (`check_doc_port_scheme`), `usr/share/mios/mios.toml` (`[docs].port_clean`, `[docs].retired_ports`), the 9 units listed above.
**Done When:** the retired-port sweep covers `usr/lib/systemd/system/**` and `usr/share/containers/systemd/**`; the six non-comment sites are resolved or justified; the host-vs-container-internal ambiguity on `8432` is settled in the SSOT rather than in a unit comment; comment-only occurrences are either rewritten to port KEYS or registered as shrink-only debt.
**Why:** T-316 and T-320 both found retired ports in EXECUTABLE positions, and both were found by hand. The gate that exists to catch them cannot see the tree where they live. | **Domain:** Naming/Addressing | **Who:** build agent

## T-325 -- SEC-01: the seat's tenancy boundary could not be switched on  (WS-GUARD | P0 | M)
**Goal:** E-04 A security control that cannot be turned on is not a control -- the SSOT key a consumer reads must be the key the SSOT declares.
**What+How:** MEASURED while grilling the MiOS-Mini/hosted difference, and it was worse than first recorded. `[security.nohc_allowlist]` opened at `mios.toml:2474` and **never closed**, so 15 keys below it parsed into the allowlist rather than `[security]`. A second runaway header, `[laws.projection_registry]`, swallowed two more. Every consumer reads `[security].<key>`, so every one of them silently took its compiled default:

| control | consumer | was |
|---|---|---|
| `api_require_auth` | `server.py:774` | always `false` -- the front-door bearer gate could not be turned on |
| `principal_bind_mode` | `context/grounding.py:551` | always `off` -- the owner of a memory row could not be bound to an authenticated caller |
| `rule_of_two_mode` | `server.py:2629` | always `off` -- the Rule-of-Two prompt-injection gate |
| `quarantine_mode` | `server.py:2635` | always `off` -- the CaMeL dual-context quarantine |
| `firewall_high_privilege_verbs` | `server.py:2595` | compiled list -- the semantic firewall's verb set |
| `taint_verbs`, `text_view_taint_prefixes` | `server.py:2598,3990` | compiled defaults -- what taints a session |
| `internal_tld_suffixes` | `server.py:3992` | compiled default |
| `api_caller_keys_path` | `server.py:778` | compiled default |
| `allowlist_hosts` | `server.py:2606` via `MIOS_SECURITY_ALLOWLIST_HOSTS` | the resolver emitted `MIOS_LAWS_PROJECTION_REGISTRY_ALLOWLIST_HOSTS`; **the name the code reads was emitted by nothing** |
| `provenance_taint` | `server.py:2624` | always `false` |

The misfiling is documented in the file itself: a comment above the duplicated `composefs_mode` read *"moved here to dedupe the second `[security]` section (strict TOML parsers reject duplicate sections)"*. Someone hit exactly this, deleted the second `[security]` header, moved one key -- and orphaned every other key under the header that was still open.

**Fixed:** the 17 keys are relocated into `[security]`; the two duplicate `composefs_mode`/`mask_systemd_remount_fs` declarations are deleted; `[security.nohc_allowlist]` now holds only its own `exempt_files`/`exempt_patterns`, and `[laws.projection_registry]` only `surfaces`. Both moves were validated by deep-comparing the parsed document before and after against an expected relocation, so an accidental extra edit could not pass. No `MIOS_SECURITY_NOHC_ALLOWLIST_*` name was referenced anywhere, so nothing broke; `allowlist_hosts` moving actually CLOSES a Law-9 hole, since the emitted name is now the name the code reads.
**Gate (the real deliverable):** `tools/check-ssot-consumer-keys.py` -- gate 177. It scans shipped Python for `_toml_section("<t>").get("<k>")` and asserts `<t>.<k>` exists. A key declared elsewhere in the SSOT is **MISPLACED** (one side has the wrong path); one declared nowhere is **UNDECLARED** (an optional escape hatch, or a dead read). `[ssot_consumers].unresolved` is the shrink-only register with a `max_unresolved` ratchet. 19 sibling tests, a 3-case negative test. Renaming `api_require_auth` out from under its consumer now fails with `security.api_require_auth is read at usr/lib/mios/agent-pipe/server.py:774 and is declared NOWHERE in the SSOT`.
**Where:** `usr/share/mios/mios.toml`, `tools/check-ssot-consumer-keys.py` + `tools/test_check-ssot-consumer-keys.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`.
**Done When:** met. The 17 keys sit where their consumers read them; the duplicates are gone; the gate exists and is registered; `MIOS_SECURITY_ALLOWLIST_HOSTS` is emitted under the name the code reads.
**Status:** done

**Standing: 19 unresolved reads -> 9**, all registered, none of them a security control:

| pair | kind | direction of the fix |
|---|---|---|
| `pgvector.memory_provider`, `pgvector.memory_guard_mode`, `pgvector.memguard_judge_mode` | MISPLACED -> `offline.*` | decide whether the memory guard is an `[offline]` concern or a `[pgvector]` one; moving changes emitted `MIOS_OFFLINE_*` names, so check references first |
| `ai.micro_model`, `ai.micro_endpoint` | MISPLACED -> `ai.host_thresholds.*` | the micro lane's model/endpoint are not host thresholds; likely the same runaway-header shape |
| `agent_passport.principal_mode` | MISPLACED -> `security.principal_mode` | the SSOT's own comment says the A2A federation reads `[agent_passport].principal_mode`; the key is in `[security]` |
| `security` under `[a2a]` | UNDECLARED | an optional override -- absent means the default bearer scheme. Either declare it or note that absence is the contract |
| `ai.permission_tiers` | UNDECLARED | `access/policy.py:97` -- verify whether the tier table is meant to be operator-tunable |
| `computer_use.hidpi_scale_factor` | UNDECLARED | `server.py:4306` -- a display scale factor is exactly the kind of thing Law 7 says belongs in the SSOT |

**Why:** the tree's recurring defect class, one level deeper than usual. Not a gate reporting success over the wrong set, but a CONSUMER reading the wrong set -- so the SSOT and the code disagree in silence, and every test that stubs the value passes. Nothing about a seat is safe to reason about until the controls that bound it are reachable. | **Domain:** Security/Federation | **Who:** architect

## T-326 -- BUILD-01: `sync-generated.sh` could not see a file git did not track  (WS-GUARD | P1 | S)
**Goal:** E-08 A regenerate-and-diff gate is only as good as the regeneration -- one pass must reach a fixpoint, or the gate can pass over a stale tree.
**What+How:** MEASURED the hard way, twice in one session. CI went red on `bbd453e` with `tools/manifest.json` missing the two tools that commit added, after a LOCAL sync and a LOCAL drift gate that both passed. The same shape put the narrative census +1 over its ceiling after another "clean" sync.

Root cause, and it is not a loop-count problem: **steps 6 and 7 census `git ls-files`.** `tools/generate-ai-manifest.py:45` and `usr/libexec/mios/mios-manual:676` both enumerate the git INDEX, so a newly created file is invisible to them until something tracks it. The sequence that bites is the ordinary one -- write a new tool, sync, watch the gate pass, `git add -A`, commit -- because the `git add` is what finally makes the file censusable, one commit too late. The script's own step-7 comment had noticed half of it (*"`git add` a new file BEFORE syncing, or its blocks land only once committed -- green locally, red in CI"*) and left the burden on the contributor.

**Fixed:** a `0/7` step registers intent-to-add (`git add -N`) for every untracked file under the censused trees before anything else runs, and NAMES each one it registered. `-N` stages no content, so it cannot turn a sync into an accidental commit of work in progress. Proven live: an untracked `tools/zz-t326-probe.py` created and then synced ONCE landed in both `tools/manifest.json` and `manual-corpus.tsv` (2 hits each) -- before the fix that needed a commit and a second pass.
**Where:** `tools/sync-generated.sh`.
**Done When:** met -- one invocation sees a new file. Remaining: a gate asserting the fixpoint property (run the generator twice, fail if the second pass changes anything) would close the class rather than this instance.
**Why:** every projection gate in this tree is regenerate-and-diff. A generator that cannot see a new file makes all of them conditionally correct, and the failure surfaces as a red CI run on a commit whose author watched the gate pass locally.
**Dep:** none. | **Domain:** Build/SSOT | **Who:** build agent

## T-327 -- SEC-02: make the seat's auth posture enforced by construction  (WS-GUARD | P0 | M)
**Goal:** E-04 A seat that points off-box must not be able to run without a tenancy boundary -- the posture is a property of the ROLE, not of an operator remembering a flag.
**What+How:** T-325 made `[security].api_require_auth` and `[security].principal_bind_mode` reachable; it deliberately changed neither default. Flipping them in the vendor SSOT is the WRONG next step and is refused here: a fully hosted MiOS is one machine on loopback with one human, where `api_require_auth = true` would demand a key from every client and `principal_bind_mode = enforce` would demand `/etc/mios/ai/v1/caller-keys.json` before the agent plane could answer its own front door. The SSOT already says as much -- *"Turn ON only with a loopback or firewall-scoped (172.16/12) bind ... operator-greenlight"*.

The roadmap-serving answer is to make the posture follow the ROLE, per ADR-0016 D5:

* **Vendor default stays off.** Loopback, single-tenant, no key. Enforced today by `check_vendor_urls`, which asserts the vendor `[ai].endpoint` is local.
* **A seat asserts its own posture at runtime.** When the resolved `MIOS_AI_ENDPOINT` is NOT loopback, `api_require_auth` must be on and `principal_bind_mode` must not be `off`. This cannot be a build-time gate: the off-box value arrives in the `/etc/mios` overlay, which the image never sees.
* **Degrade open, but LOUDLY** (Law 12). A seat with an off-box endpoint and auth off must still boot -- it must not brick a machine over a policy default -- but it must say so in the boot record, in `mios blade status`, and on the dashboard beside the blade-reachability state T-323 already computes. A silent seat is the failure mode being fixed; a refusing seat is a new one.
* **Firstboot provisions the key** so the posture is reachable without hand-editing: generate a caller key into `/etc/mios/secrets.env` (0600, Law 11) when a seat is resolved, so `enforce` is one flag away rather than a project.

**Where:** `usr/libexec/mios/role-apply` or `usr/lib/mios/blade.sh` (the posture assertion belongs beside the role resolution), `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh` (recorded, non-critical -- ADR-0016 D8), `usr/share/mios/mios.toml` (`[security]`), `tests/test-seat-auth-posture.sh`.
**Done When:** a seat with an off-box endpoint and `api_require_auth = false` boots, works, and SAYS so in three places; a seat with auth on and a provisioned key is silent; a hosted blade on loopback is unaffected in every case; the assertion is unit-tested against a fixture overlay rather than a live host.
**Why:** the operator answer to "should auth be on?" is "on a seat, yes; on a hosted box, it is noise". Encoding that in the role is the difference between a security control that exists and one that is documented. | **Domain:** Security/Federation | **Who:** architect
