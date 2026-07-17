# MiOS -- Master Tasks (SINGULAR monolith)

> The one canonical task list. **253 tasks** (106 done, 147 open/in-progress). Absorbs the former `*-PLAN-*.md` + `concepts/*` backlogs. Each task carries **Who / What / Where / When / How** + Done-When.

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
| T-050 | P2 | open | Distribution/Edge | GAP-5 -- Rechunking Delta Distribution for Edge/Offline OCI Upda |
| T-051 | P2 | done-by-code | Federation | FED-G7 -- Route on AgentCard Skills |
| T-052 | P2 | done-by-code | Federation/Security | FED-G8 -- Caller-Key Store (`mios_principal` + CRL) |
| T-053 | P2 | done-by-code | Federation/Networking | FED-G9 -- Loopback-Default Bind + Scoped Publish |
| T-076 | P2 | retired | Memory/Gateway | GWY-01 -- Deploy Letta Server as Memory Complement (Phase 1) |
| T-077 | P2 | retired | Memory/Orchestration | GWY-02 -- Wire Letta Self-Editing Memory to agent-pipe Verbs (Ph |
| T-054 | P3 | open | Orchestration | ORCH-06 -- Deterministic Orchestration via Conductor CLI |
| T-055 | P3 | open | Memory | MEM-04 -- Hindsight Multi-Strategy Memory Engine |
| T-056 | P3 | open | Memory/Scheduling | MEM-05 -- KV Hierarchy + Sleep-Time Consolidation |
| T-057 | P3 | open | Memory/UX | ORCH-07 -- Personal Knowledge Graph Rich Edges |
| T-058 | P3 | open | Scheduling | SCHED-03 -- MLFQ Program-Level Scheduler (Autellix-style) [VM] |
| T-059 | P3 | done | Federation | DATA-01 -- Declarative Agent Specs + A2A-Discoverable Directory |
| T-060 | P3 | open | Memory/Data | DATA-02 -- Storage Versioning + Rollback for Self-Edited Core Fa |
| T-061 | P3 | open | Orchestration/Memory | ORCH-09 -- Code-Mode for Heavy Verbs/Recipes |
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
| T-079 | P3 | partial | Gateway/Orchestration | GWY-04 -- smolagents ToolCallingAgent as Tool-Loop Engine (Phase |
| T-080 | P3 | done-by-code | Gateway/MCP | GWY-05 -- MCP Client: stdio â†’ mios-mcp-server (Phase 2) |
| T-081 | P3 | partial | Gateway/Tools | GWY-06 -- Skill Catalog + SearXNG + Browser Verb Pass-Through (P |
| T-082 | P3 | partial | Gateway/Config | GWY-07 -- Migrate Hermes Config to mios.toml [gateway] SSOT (Pha |
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
| T-095 | P2 | partial | Orchestration/Python | CONV-02 -- GatewayQueue Module + GatewayWorker + smolagents Wiri |
| T-096 | P2 | partial | Testing | CONV-03 -- GatewayQueue Test Suite |
| T-097 | P2 | partial | Inference/Performance | CONV-04 -- llama-swap Shared Prefix Cache + Parallel Slots |
| T-098 | P2 | done-by-code | Inference/vLLM | CONV-05 -- vLLM Multi-LoRA Heavy Lane Upgrade |
| T-099 | P2 | done-by-code | API/Inference | CONV-06 -- LoRA Load/List API Endpoints in agent-pipe |
| T-100 | P2 | partial | Docs/Migration | CONV-07 -- mios-llm-heavy-alt Retirement Documentation |
| T-101 | P2 | done-by-code | Memory/Python | CONV-08 -- sqlite-vec Scratchpad Module |
| T-102 | P2 | done-by-code | Memory/Storage | CONV-09 -- Cold Eviction Module + zstd Export |
| T-103 | P2 | done-by-code | Orchestration/Memory | CONV-10 -- sqlite-vec Scratchpad Wired into GatewayWorker |
| T-104 | P2 | done-by-code | Storage/CI | CONV-11 -- Cold-Archive Retention Sweep + Drift-Check |
| T-105 | P3 | partial | Image/Security | CONV-12 -- Hummingbird Distroless Containerfile |
| T-106 | P3 | done-by-code | Tool/MCP | CONV-13 -- Unified MCPClientPool |
| T-107 | P3 | done-by-code | Image/CI | CONV-14 -- rechunk CI Step |
| T-108 | P3 | partial | CI/Docs | CONV-15 -- Phase 4 Drift-Check Suite + Documentation |
| T-031 | P1 | reopened | Orchestration | ORCH-04 -- ReAct+Reflexion Durable Loop  (RE-OPEN -- done-by-cod |
| T-109 | P1 | done | Observability/Orchestration | CHATQ-01 -- Refine/plan trace to reasoning channel + one-answer- |
| T-110 | P1 | done | Observability | FV-01 -- Canonical typed-event schema + per-surface routing + su |
| T-111 | P1 | done | Tool-calling | CHATQ-02 -- Constrained tool-calling + tools-on-final + verb-cat |
| T-112 | P1 | done | Tool-calling/Grounding | CHATQ-03 -- First-class list_dir verb + cwd act-before-answer gr |
| T-113 | P0 | ? | Anti-Fabrication/Orchestration | FAB-01 -- @ agent-pipe FABRICATES tool execution + results (no r |
| T-114 | P0 | ? | Anti-Fabrication/Grounding | FAB-02 -- pipeline fabricates web/news content + invents entitie |
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
| T-132 | P2 | ? | Windows/Install | WISO-01 -- Shared install-time provisioning core (`MiOS-Provisio |
| T-133 | P2 | ? | Windows/Install | WISO-02 -- NTLite preset sanitizer (`ConvertTo-MiOSPreset.ps1` - |
| T-134 | P2 | ? | Windows/Install | WISO-03 -- Schneegans autounattend generator + 96 GB C: carve  ( |
| T-135 | P2 | ? | Windows/Install | WISO-04 -- Existing-Windows parity path (`Invoke-MiOSProvision.p |
| T-136 | P3 | ? | Windows/Install | WISO-05 -- OEM driver export for slipstream (`Export-MiOSDrivers |
| T-137 | P2 | done | Windows/Install | WISO-06 -- UUP-Dump source-ISO automation (`mios-uup-fetch`)  [P |
| T-138 | P2 | done | Windows/Install | WISO-07 -- DISM-native debloat + oscdimg assembly + CI  [P2] |
| T-139 | P2 | ? | Windows/Install | WISO-08 -- Stage MiOS branding assets into the image  [P2] |
| T-140 | P2 | ? | Windows/Gaming | XBOX-01 -- Xbox Full Screen Experience out of the box  [P2] |
| T-141 | P3 | ? | Windows/Gaming | XBOX-02 -- Gaming loadout + Xbox tuning  [P3] |
| T-142 | P2 | ? | Windows/Gaming | XBOX-03 -- MiOS-XBOX posture decision (A pure-gaming vs B keep-t |
| T-143 | P2 | ? | Windows/Branding | WBRAND-01 -- Global Windows branding/theme from SSOT  [P2] |
| T-144 | P2 | pending | Linux/Branding | WBRAND-02 -- Linux desktop palette parity via matugen  [P2] |
| T-145 | P3 | done | Windows/Branding | WBRAND-03 -- Re-assert branding on Windows update drift  [P3] |
| T-146 | P2 | ? | Windows/Install | WEDITION-01 -- Editions SSOT matrix  [P2] |
| T-147 | P1 | ? | Windows/SSOT | WEDITION-02 -- SSOT keys + configurator for the ISO/branding sur |
| T-148 | P3 | ? | Windows/Install | WEDITION-03 -- ARM64 / 26H1 handheld edition (`MiOS-XBOX-ARM`)   |
| T-149 | P2 | ? | Windows/Install | WEDITION-04 -- Fold reverting generated-file changes into the ge |
| T-150 | P2 | pending | Data/Accounts | ACCT-01 -- Account SSOT schema + install-time seeding (pgvector  |
| T-151 | P2 | ? | Linux/Accounts | ACCT-02 -- Linux DB-native accounts via NSS + PAM (libnss-pgsql2 |
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
| T-162 | P3 | ? | Branding | WBRAND-04 -- SSOT living-wallpaper shader (self-authored, permis |
| T-163 | P3 | ? | Linux/Branding | WBRAND-05 -- Linux living wallpaper (GNOME layer / optional Quic |
| T-164 | P3 | ? | Windows/Branding | WBRAND-06 -- Windows animated background + SSOT living-wallpaper |
| T-165 | P2 | planned | SSOT/Cross-cutting | NAME-01 -- Global naming minification → one unified names/keys r |
| T-166 | P1 | planned | Install/Deploy/SSOT | DEPLOY-01 -- Install/first-boot reorder → eliminate "missing dep |
| T-167 | P2 | planned | Tool-execution/Sandbox | SHELL-01 -- Persistent PTY / stateful shell substrate  [P2] |
| T-168 | P2 | planned | Security/Kernel | KENF-01 -- Tetragon eBPF/LSM kernel enforcement plane  [P2] [VM] |
| T-169 | P2 | planned | Security/Sandbox | ISOL-01 -- Per-action isolation tier ladder (promote-not-refuse) |
| T-170 | P1 | in-progress | Computer-Use/Perception | GVLM-01 -- Activate grounding VLM + cu_act/cu_verify verbs  [P1] |
| T-171 | P2 | planned | Orchestration/Judging | CONS-01 -- Weighted multi-judge consensus pipeline  [P2] |
| T-172 | P2 | planned | Observability/Safety | CONS-02 -- JSD drift monitor  [P2] |
| T-173 | P0 | planned | Autonomy/Safety | GUARD-01 -- Daemon runaway controls (host-pressure gate + dedup  |
| T-174 | P0 | planned | Autonomy/Scheduling | GUARD-02 -- Aggregate token/turn budget + background preemption  |
| T-175 | P1 | planned | Data/Durability | DURA-01 -- pgvector durability + exposure hardening  [P1] |
| T-176 | P1 | planned | Security/Privacy | DURA-02 -- Secret/PII redaction on persist + federate  [P1] |
| T-177 | P3 | planned | Memory/Filesystem | LSFS-01 -- Semantic-FS verbs + task-state protocol  [P3] |
| T-178 | P1 | in-progress | AI-plane/Inference/Deploy | HEAVY-01 -- provision the heavy dGPU model so the stated lanes d |
| T-200 | P2 | planned | Provisioning/AI-lanes | FBM-01 -- First-boot large-model provisioner (`mios-models-first |
| T-201 | P2 | planned | SSOT/CLI | FBM-02 -- `[ai.firstboot_models]` SSOT + `mios models {list,sync |
| T-202 | P3 | planned | Provisioning/Containers | FBM-03 -- Heavy-lane bound-images first-boot pull (`mios-bound-i |
| T-203 | P3 | planned | UI/Provisioning | FBM-04 -- Portal model-provisioning status tile + air-gapped pre |
| T-204 | P3 | planned | Build/Offline | OFFL-01 -- Vendor external repo definitions (terra.repo)  [P3] |
| T-205 | P3 | planned | Build/Offline | OFFL-02 -- Vendor desktop assets (Geist + Nerd fonts, Bibata cur |
| T-206 | P3 | planned | Build/Offline | OFFL-03 -- Vendor k3s binary + k3s-selinux  [P3] |
| T-207 | P3 | planned | Build/Offline | OFFL-04 -- Vendor hermes-agent source + pip wheels (`--no-index` |
| T-208 | P2 | planned | Build/Offline/AI-lanes | OFFL-05 -- Vendor GGUF blobs + pre-pull llama-swap proxy image   |
| T-209 | P3 | planned | Build/Offline | OFFL-06 -- Local rpm mirror image for fully-offline dnf  [P3] |
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
| T-223 | P3 | planned | OpenAI-conformance | OAI-02 -- Tier-1 `usage` detail fields + strict function schemas |
| T-224 | P2 | planned | OS-control/ACI | OAI-03 -- Persistent PTY/tmux stateful shell + PowerShell object |
| T-225 | P2 | in-progress | Orchestration/Determinism | OAI-04 -- Run-template REPLAY-REUSE (intent-keyed zero-token DAG |
| T-226 | P3 | ? | Scheduling | KACT-01 -- Wire batch-coalescing chokepoint (`mios_batch`)  [P3] |
| T-227 | P2 | ? | Routing/Cost | KACT-02 -- Remote SmartRouting + quality-gate + daily budget (`m |
| T-228 | P3 | ? | Cost/Identity | KACT-03 -- Per-user quota keying + persistence on verified princ |
| T-229 | P3 | ? | Federation/Discovery | KACT-04 -- Gossip/DHT federated discovery transport (`mios_gossi |
| T-230 | P2 | ? | Security/Sandbox | KACT-05 -- Per-verb risk-tier bwrap/seccomp ENFORCEMENT exec (`m |
| T-231 | P2 | planned/unverified | Lifecycle/Health | KACT-06 -- `Notify=healthy` + `HealthCmd` + rollback across AI q |
| T-232 | P3 | planned | UI/QML | UISHELL-01 -- Native QML Services/Swarm views (replace web-Porta |
| T-233 | P3 | planned | UI/QML | UISHELL-02 -- Login-prompt QML popup (`PortalData.login()`)  [P3 |
| T-234 | P3 | planned | UI/Config | UISHELL-03 -- Reconcile `mios-webshell` AI-sidebar endpoint (`:3 |
| T-235 | P3 | ? | UI/Architecture | UISHELL-04 -- Cockpit native-vs-web decision  [P3] |
| T-236 | P2 | planned | SSOT/Identity | NAME2-01 -- Agent-plane user SSOT reconciliation (820/822 → 850) |
| T-237 | P3 | planned | Naming | NAME2-02 -- Rename `mios-daemon-agent` agent-id → `daemon-agent` |
| T-238 | P3 | ? | Naming/Hygiene | NAME2-03 -- Mutable-state casing pass + `ContainerName=` audit   |
| T-239 | P3 | ? | Security/Boot | UKI-01 -- verity-rooted UKI build + fapolicyd enforce-promotion  |
| T-240 | P2 | in-progress | Data/Migration | A3F-01 -- Central-path legacy-datastore→pg primary flip + un-mirrored w |
| T-241 | P2 | in-progress | OS-control/Windows | OSCTL2-01 -- hwnd-threaded target-window resolution for `pc_type |
| T-242 | P1 | planned | AI-plane/SSOT/DB | VECTOR-00 -- V0 Foundation: unified DB + provenance + DB->TOML m |
| T-243 | P1 | planned | AI-plane/SSOT/DB | VECTOR-01 -- V1 Config read-path: DB becomes the runtime read (T |
| T-244 | P2 | planned | AI-plane/Vectorization | VECTOR-02 -- V2 AI-plane vectors: embed skill/verb/tool_call/eve |
| T-245 | P2 | planned | Build/Install/Xbox/DB | VECTOR-03 -- V3 Build catalog: package/build/xbox/debloat tables |
| T-246 | P2 | planned | Accounts/Identity/DB | VECTOR-04 -- V4 Accounts/users: DB-owned ids + prefs + bidirecti |
| T-247 | P3 | planned | SSOT/DB/Configurator | VECTOR-05 -- V5 Invert authority: DB=SSOT, TOML=generated export |
| T-248 | P1 | in-progress | Build/Bake | BAKE-01 -- `[build.bake]` core allow-list + bake-plan projection ( |
| T-249 | P1 | planned | Build/Activation | BLADE-01 -- Universal-core + blade-type activation gate (`Conditi |
| T-250 | P1 | planned | Build/Consolidation | MIOSSYS-01 -- mios-sys + mios-cuda shared-base consolidation (~18 |
| T-251 | P2 | in-progress | SBOM/Provenance | SBOM-01 -- build-time provenance beyond images (model/pkg hashes) |
| T-252 | P2 | in-progress | Release/CI | RELTOP-01 -- credential-driven registry selection (GHCR else Forg |
| T-253 | P2 | planned | AI-plane/Deps | DEPRED-01 -- Hermes->agent-pipe collapse + sidecar consolidation |
| T-254 | P1 | planned | Deploy/Windows | MDRIVE-01 -- Hyper-V Gen 2 .vhdx off M: + sovereign Ceph OSD on M |
| T-255 | P1 | in-progress | Docs/Meta | DOCS -- ADR system (done) + generated roadmap index + lean thematic roadmap + Diátaxis |
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
| T-266 | P3 | planned | Deploy/Cat/SSOT | CATFLAT-03 -- mios.toml seed-copy consolidation (63/68 KB seeds vs 597 KB SSOT) |
| T-267 | P1 | planned | Config/Portal | CONFIG-01 -- Fold mios.html into the MiOS Portal at :8640/ (one web + API door) |
| T-268 | P1 | planned | Build/SSOT/Version | DEBT-01 -- Collapse version/SSOT to one value (TD-2: 3x mios.toml + 0.2.4 root + 37x headers) |
| T-269 | P1 | planned | Build/Security | DEBT-02 -- shellcheck CI gate + kill the 9 eval-on-agent-args verbs (TD-1) |
| T-270 | P1 | planned | Dotfiles/SSOT | DOTFILES-01 -- [dotfiles.registry.*] + mios-dotfiles-render + apply verb + both-sides gate (ADR-0010) |
| T-271 | P1 | planned | Build/Templates | TEMPLATE-01 -- Compiled file-pattern system + mios new + conformance check + Law-14 (ADR-0011) |
| T-272 | P1 | planned | Build/Lang | LANG-01 -- Stand up Rust workspace + port first fragile bash tool (drift-runner/verb dispatcher) |
| T-273 | P2 | planned | AI-Plane/Refactor | DEBT-03 -- Split mios_dispatch.py + finish server.py decomposition (TD-5) |

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
- E3: Fix stale `agent.json` description that still references "legacy-datastore-state chain" (pgvector migration happened).

**Files:** `usr/lib/mios/agent-pipe/server.py` (`_client_env`) | `usr/share/mios/ai/v1/agent.json`

**Deps:** None.

**Done When:**
- [x] Location in OWUI shows city/timezone only, no coordinates
- [x] `agent.json` description references pgvector, not the legacy datastore

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
- [x] `reflexion_enable` + budgets read from `[agent_pipe]`; no `[agent]`/literal fallbacks remain (drift-gate green)
- [x] identical failing `(tool,args)` is never retried; loop terminates/escalates within `wall_clock_budget_s`
- [x] failure path uses the structured reflector (corrective action or terminate), no free-text essay in `content`
- [x] live-fired in `podman-MiOS-DEV`: a deliberately-failing tool call does not loop

---

## T-109: CHATQ-01 -- Refine/plan trace to reasoning channel + one-answer-in-content (CQ1)
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** Observability/Orchestration | **Source:** CQ1 -- refine's `{Refined Query/Intent/Reply}` scaffold streams into `delta.content` (`chat.py:1425-1426` -> `sse.py:93-94` under `_DEBUG_ENABLE`) and the answer is restated 3x (refine `reply` + local-state + polish all reach content).

**Instructions:** Wave 1 (Claude C1-C3). Route the refine pump + `_refine_reasoning` summary through a channel-pinned emitter (reasoning channel regardless of `_DEBUG_ENABLE`); extend the `_live_streamed` guard (`native_loop.py:858`) so exactly one generation reaches `content`. Refine `reply` is trace, not answer. Visibility preserved; only the channel + dedup change.

**Files:** `.../agent-pipe/mios_pipe/routing/sse.py`, `.../routing/chat.py` (1425-1426, 1482-1495, 1789-1803), `.../routing/native_loop.py` (858, 1061, 1101-1102).

**Done When:**
- [x] refine trace renders in the Thinking pane, never in `delta.content`
- [x] `@ what directory are we in right now` returns exactly one clean answer (no `Refined Query/...` block, no 3x restate)
- [x] byte-identical when `[observability]` flags off (degrade-open)

---

## T-110: FV-01 -- Canonical typed-event schema + per-surface routing + sub-agent visibility (FV-A/B/E/F)
> **Priority:** P1 | **Status:** done | **Effort:** L | **Domain:** Observability | **Source:** FV -- full-visibility mandate is untracked; "visibility" today is faked by content-inlining under `[observability].debug=ON`; leaf thinking is turned OFF at source (`agent_call.py:820-821`; `swarm.py:1237`); fan-out `_push` has no channel discriminator; strict clients can't see the reasoning channel.

**Instructions:** Wave 1. One schema `thinking|plan|tool_call|tool_result|source|content` every stage + sub-agent emits into; per-lane `[lanes.*].stream_thinking` replaces the blanket `enable_thinking:False`; channel tag on the `_push` merged event; retire content-inline as the mechanism (`debug` gates only content-mirroring for strict surfaces); per-surface routing via `X-MiOS-Surface`/`reasoning_ok` with MiOS-owned replay-strip; OWUI pipe translates `mios_status`->status + refs->source events. AGY owns SSOT + OWUI pipe; Claude owns emitter + `agent_call`.

**Files:** SSOT `[observability]`/`[observability.channels]`/`[lanes.*]`; `usr/share/mios/owui/pipes/mios_agent_pipe.py`; `.../agent-pipe/mios_pipe/routing/sse.py`, `.../routing/agent_call.py` (738-746, 797-885, 820-821), `.../server.py`, `swarm.py`.

**Done When:**
- [x] every sub-agent's thinking + tool calls + sources stream live on OWUI/Hermes; strict clients get a folded inline trace; final answer only in `content`
- [x] KV cache intact across turns (persisted history = clean answer only)
- [x] per-lane `stream_thinking=false` cleanly downgrades that lane (degrade-open)

---

## T-111: CHATQ-02 -- Constrained tool-calling + tools-on-final + verb-catalog repair (CQ2)
> **Priority:** P1 | **Status:** done | **Effort:** L | **Domain:** Tool-calling | **Source:** CQ2 -- the final answer-shaping completion fires with NO `tools[]` (`native_loop.py:780-782`) so residual tool intent leaks as literal `<tool_call>`/```json``` text; `linux_file_search` is `hidden` but name-dropped in visible descriptions -> model wraps it into `launch_app`; no constrained decoding on any lane; rescue returns after the first block and is gated on empty `tool_calls`.

**Instructions:** Wave 2. AGY: engine `--tool-call-parser`/`--reasoning-parser` + `constrained_tools` per lane; consolidate duplicate `launch_app`; correct `fs_search` desc; stop advertising uncallable names; fix `[routing.domains.files].verbs`. Claude: give `_pb` the `tools[]`; streaming-aware salvage that RE-EMITS as typed events (visible) + diverts off `content` + executes; remove first-block early-return; surface routed-domain verbs even when hidden (key Stage-2 filter on canonical verb).

**Files:** SSOT `[lanes.*]`, `[verbs.launch_app]` (9084/3157), `fs_search` (3465-3473), `[routing.domains.files]` (3103-3110); `.../routing/native_loop.py` (780), `.../routing/secondary_loop.py` (309, 334-344), `.../routing/toolexec.py` (210-279), `.../server.py` (3956, 4028-4034), `.../verbcatalog.py`, `.../mios_endpoints.py`.

**Done When:**
- [x] a narrated tool call renders as a native/typed tool pill, never as text in `delta.content`
- [x] a files turn always carries a callable `linux_file_search`; no `launch_app` misroute
- [x] live-fired: `@ what's here?` fires a real typed file/`list_dir` call

**Deps:** T-112 (list_dir gives the correct files-turn verb), T-110 (typed tool_call channel).

---

## T-112: CHATQ-03 -- First-class list_dir verb + cwd act-before-answer grounding (CQ3)
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** Tool-calling/Grounding | **Source:** CQ3 -- no `list_dir` verb exists (`linux_file_search`=`mios-locate` substring, not `ls`); `read_file`/`text_view` can list a dir but is depth-2/500-capped and framed as "read a file"; cwd string is injected but no snapshot + no lister auto-fires -> model hallucinates a generic FHS table. Also unblocks T-032's phantom `list_directory` op assumption.

**Instructions:** Wave 3. AGY: add `--depth 1` immediate-children mode to `mios-text-edit`; add `[verbs.list_dir]` (`model_name=list_directory`, `path` default cwd, accurate desc + examples); redirect `read_file`/`fs_search` descriptions. Claude: fire `list_dir(path=cwd)` in `_read_tool_enrich` when cwd present (keyed off SSOT `_client_env` cwd); add a model-chosen filesystem/`state_scope` signal to refine so dir-content queries set `tool_choice:required`.

**Files:** `usr/libexec/mios/mios-text-edit` (83-84, 219-241); SSOT `[verbs.list_dir]` + `fs_search`/`read_file` descs; `.../server.py` `_read_tool_enrich` (4648, 4685-4701, 4734-4745); `.../routing/refine.py`, `.../routing/chat.py` (1193-1198).

**Done When:**
- [x] `list_dir` with no arg lists cwd immediate children (true `ls` semantics)
- [x] `@ what's here?` returns the real directory, never a generic FHS table
- [x] selection is model-driven (classifier), not a keyword/English match

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
> **Priority:** P0 | **Status:** done-by-code (fix reproduction-tested; live @-verify pending) | **Effort:** L | **Domain:** Anti-Fabrication/Orchestration | **Source:** live `@` session -- `@ launch fakegame` emitted a fake `🤝 open_app output: {"success":true,"pid":8421,"window":{"handle":0x7f12345678,...}}` with IDENTICAL fake pid/handle across every launch AND an invented app ("FakeGame 6"), while NOTHING launched (operator: "doing NOTHING for me"). The parallel `hermes` path ran a REAL `mios-windows launch`. So the agent-pipe narrates/hallucinates a tool call AND its output instead of dispatching to the real executor.

**Instructions:** Root-cause why the `@`/agent-pipe turn produces a fabricated tool-result block rather than a real `toolexec` dispatch (or a real hand-off to Hermes :8642). Enforce the hard invariant: **no `🤝 <tool> output:` / tool-result may EVER be emitted unless a real tool actually ran and returned it** — a tool result must be produced by `_exec_tool_calls`, never by a model hop. Wire a fabrication guard: any assistant-emitted text matching a tool-result envelope that has no corresponding executed `tool_call` row is dropped + the turn re-dispatched. Verify the `@`/`mios` CLI route reaches the real executor (memory says `@` should be Hermes-DIRECT :8642 -- confirm/repair the routing regression).

**Files (likely):** `usr/lib/mios/agent-pipe/mios_pipe/routing/{chat,native_loop,secondary_loop,toolexec}.py`, `.../routing/refine.py`, `usr/bin/mios` (route), `server.py` (dispatch).

**Done When:**
- [ ] `@ launch fake game` either executes a REAL launch (dispatch/Hermes) or says it could not -- NEVER a fabricated success with a fake pid/handle -- needs live @-session verify
- [ ] no tool-result block reaches the user without a matching executed `tool_call` row (live-verified) -- needs live @-session verify
- [x] identical-fake-pid fabrication cannot recur (guard + test) -- `_contains_tool_result_block` (chat.py) short-circuits any chat-reply narrating a `🤝 <verb> output:`/success-JSON block; native_loop.py's unfired-verb strip drops the same shape for any verb not in `_fired`; unit-tested in `usr/lib/mios/agent-pipe/test_mios_antifab.py`

## T-114: FAB-02 -- pipeline fabricates web/news content + invents entities on misclassification  [P0]
> **Priority:** P0 | **Status:** done-by-code (fix reproduction-tested; live @-verify pending) | **Effort:** M | **Domain:** Anti-Fabrication/Grounding | **Source:** live `@` session -- gibberish `??!!!?` was refine-misclassified as a "weekly news roundup" and the pipeline FABRICATED 5 fake articles attributed to real outlets (NYT/Reuters/BBC/FT/TechCrunch) with invented events, claiming `web_search` ran (it did not). Also invented "FakeGame 6" (nonexistent).

**Instructions:** Hard anti-fabrication gate: NEVER emit web/news content or source attributions that were not returned by a real `web_search`/fetch tool call; NEVER invent entity names (apps/games). Fix the refine classifier so low-signal/gibberish input does NOT get promoted to a fabricated task plan (classify as chat/clarify, not "news"). Grounding: attributions must come from fetched results only. Model-driven, NO keyword gate.

**Files (likely):** `.../routing/refine.py` (classifier), `.../routing/chat.py` (web-research enrich), `mios_grounding.py`, `.../federation` web tools.

**Done When:**
- [ ] gibberish input -> clarify/chat, never a fabricated news roundup -- needs live @-session verify (classifier reclassification itself out of scope for this guard; see note below)
- [x] no source citation appears unless a real fetch produced it -- native_loop.py's ANTI-FABRICATED-CITATION guard rewrites the answer to an honest note when a web/news turn cites an off-list URL, or fetched ZERO sources yet produced a markdown report table (structural, not keyword); code authored + SSOT-wired. Live-session confirmation of the `(live-verified)` wording still needs live @-session verify

## T-115: CQ1 refine scaffold STILL leaking on CLI + redundant refine passes  (extends T-109)
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** Observability | **Source:** live `@` session -- the `Refined Text/Intent/Reply` scaffold streams verbatim to the strict CLI surface (CQ1 confirmed still live; the surface-aware `_sse_reasoning` fix is authored but undeployed, and the CLI sends no `x-mios-reasoning-ok` so it hits the legacy debug-inline path), and "🧠 Refining intent..." fires 2-3x per turn.

**Instructions:** Deploy T-109; additionally de-duplicate the refine pass (it runs multiple times per turn) and confirm the strict-CLI folded-trace path (FV-F) shows the trace once, cleanly, without the raw scaffold. Fold into T-109/T-110.

**Files:** `.../routing/{chat,sse,refine}.py`.

## T-116: OSCTL-01 -- Hermes browser opens NEW WINDOWS instead of reusing running instance / opening a TAB  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** OS-Control | **Source:** live `hermes` session -- "open a firefox TAB to youtube" launched the Firefox Nightly shortcut TWICE (2 new windows) + opened several random Epiphany tabs, despite Firefox already running AND the operator explicitly asking for a tab. Launch path uses `mios-windows launch <shortcut>` (always spawns a new window).

**Instructions:** Make browser open-URL tab-aware: detect an already-running browser instance and open a NEW TAB in it (CDP `Target.createTarget` / `--new-tab` / activate-existing), NOT a new window/instance. Only cold-launch when the browser is not running. Honor an explicit "tab" request. Don't fan out extra Epiphany tabs.

**Files (likely):** `usr/lib/mios/agent-pipe/mios_oscontrol.py`, `.../routing/oscontrol.py`, `usr/libexec/mios/mios-windows`, browser/CDP skills.

**Done When:**
- [x] "open a firefox tab to <url>" with Firefox already open -> ONE new tab in the existing window, no new window (live-verified by operator)

## T-117: OSCTL-02 -- Hermes container-exec: stale container name + interactive-exec hang + docker-first  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** OS-Control | **Source:** live `hermes` session -- "ssh into code-server container" tried `docker` first (runtime is podman), used the RETIRED name `code-server` (now `mios-agents`), wrong-execed `mios-open-webui`, and hung 172s/21s on `podman exec -it ... bash` (interactive `-it` with no TTY in the agent context). The memory tool also errored mid-session.

**Instructions:** (1) SSOT container-name resolution so `code-server` resolves to `mios-agents` (retired-name alias). (2) Never run interactive `-it` exec from the agent -- use non-interactive `podman exec <c> <cmd>` (no `-it`, no bare shell) so it can't hang. (3) Prefer podman (SSOT runtime), skip docker probing. (4) Investigate the memory-tool error.

**Files (likely):** `.../mios_oscontrol.py`, `usr/libexec/mios/*`, Hermes tool skills, container-name SSOT (mios.toml `[containers.*]`).

**Done When:**
- [x] "exec into the code-server container" targets `mios-agents`, runs non-interactively, returns promptly (no >5s hang), never `-it`

## T-118: HEALTH-01 -- mios-cpu-node + mios-llm-light Unhealthy (baked healthcheck port mismatch)  [P1]
> **Priority:** P1 | **Status:** done-by-code | **Effort:** S | **Domain:** Inference/Reliability | **Source:** podman dashboard -- both llama-swap:cuda lanes report **Unhealthy**. ROOT CAUSE (live-probed, corrects the original "oversized KV" premise): the lanes are NOT down -- `curl :${MIOS_PORT_CPU_NODE}/health` and `:${MIOS_PORT_LLM_LIGHT}/health` + `/v1/models` all return **200**. The upstream `ghcr.io/mostlygeek/llama-swap:cuda` image bakes `HEALTHCHECK curl -f http://localhost:8080/`, but MiOS runs each lane on its SSOT `${MIOS_PORT_*}` port -> the baked probe can never connect -> perpetual red gate.

**Instructions:** Override the baked image healthcheck with an SSOT `HealthCmd` that probes the REAL runtime `${MIOS_PORT_*}` port; also land the already-in-SSOT cpu-node ctx right-size (131072->32768). NO-HARDCODE: port from `${MIOS_PORT_*}` runtime var.

**Files:** `usr/share/mios/mios.toml` (`[containers.mios-cpu-node.Container]` + `[containers.mios-llm-light.Container]` HealthCmd/ctx), regenerated `usr/share/containers/systemd/mios-{cpu-node,llm-light}.container`.

**Done When:**
- [x] SSOT `HealthCmd` added for both lanes, probing the runtime `${MIOS_PORT_*}` port (cpu-node -> llama-server `/health`; llm-light -> llama-swap `/v1/models`, model-load-free) -- commit c3eff07
- [x] cpu-node `--ctx-size 32768` regenerated into the Quadlet (was drifted at 131072); `generate-pod-quadlets.py --check` green (26/26 match SSOT)
- [x] mios-cpu-node + mios-llm-light report Healthy -- LIVE-VERIFIED in podman-MiOS-DEV: deployed the regenerated Quadlets, `systemctl daemon-reload` + `systemctl restart mios-cpu-node mios-llm-light`, both flipped to `Up (healthy)` within ~1 min

---

## T-119: TOOLARG-01 -- Native typed launch-arguments for ALL tools/skills/recipes (OpenAI-pattern, all environments)  [P1, systemic] [DONE]
> **Priority:** P1 | **Status:** done | **Effort:** XL | **Domain:** Tool-calling/OS-Control | **Source:** operator mandate (generalizes T-116) -- every verb/skill/recipe must expose NATIVE, typed launch/invocation arguments following OpenAI function-calling patterns (strict JSON-schema typed params + enums), grounded in upstream research on native invocation per app-type across ALL environments (Windows/Linux/WSL/container/browser). Not name-only coarse verbs. Exemplar: browser open-URL must take `{url, mode:tab|window, reuse_instance}` and open a TAB in the RUNNING browser, not a new window.

**Instructions:** Research + design FIRST (-> a `research/` doc): the native typed-arg standard + a per-type/per-environment native launch-arg map (browser tab/window via CDP `Target.createTarget`/`--new-tab`/remote; Windows App Paths/protocol/`.lnk`/AUMID; Linux `.desktop` Exec field codes/`gio`/`xdg-open`; games via `steam://`). Then enrich the `_VERB_CATALOG` + skill/recipe schemas with typed native args and project them through the existing OpenAI-tool/MCP schema surface (`strict`). SSOT + NO-HARDCODE + degrade-open. Land T-116 (browser tab) as the first shipped instance. Pairs with T-111 (constrained tool-calling = the MECHANISM; this = schema RICHNESS).

**Files (likely):** `usr/share/mios/mios.toml` (`[verbs.*]` arg schemas), `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py` (`_verb_to_openai_tool`), `.../mios_oscontrol.py`, `usr/libexec/mios/mios-windows`, skills/recipes catalogs.

**Done When:**
- [x] a research/design doc defines the native typed-arg standard + per-type/env launch-arg map
- [x] browser open-URL opens a TAB in the running browser (T-116) as the first shipped instance
- [x] verbs/skills/recipes expose typed native args (not name-only) via the OpenAI/MCP tool projection
- [x] every argument is model-selectable + validated; degrade-open when an env/arg is unsupported

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

---

# Part 11 — Win11-Minimal Install Completeness + NO-HARDCODE Sweep (2026-07-04 audit)

<!-- Source: 4-agent read-only audit 2026-07-04 (hardcoded ports/IPs; hardcoded English keyword-gates;
     Win11-minimal install completeness; SSOT-defaults coverage). Every item below carries live
     file:line evidence from that audit. Law: NO-HARDCODE (ports/IPs/hosts/keyword-gates from
     mios.toml SSOT with defaults; fix order model-driven > SSOT > unicode-aware > delete-dead) +
     "everything defined by mios.toml/mios.html with defaults". -->

## T-120: NOHC-01 -- Reconcile the `[ports]` SSOT renumber drift (8xxx) across code + bootstrap  [P1, systemic]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** SSOT/Ports | **Source:** ports/IP audit 2026-07-04 -- `C:\MiOS` `[ports]` was renumbered into the 8xxx range (llm_light=8450, searxng=8899, open_webui=8033, pgvector=8432, cockpit=8090, forge_http=8300, sglang=8442, vllm=8441 -- confirmed live: `install.env` has `MIOS_PORT_LLM_LIGHT=8450`, `MIOS_PORT_CPU_NODE=8458`, and the lanes listen there) but **code, docs, and `C:\mios-bootstrap\mios.toml` still use the OLD values** (11450/8888/3030/5432/9090/3000/11441/11440). Live consequence: consumers that hardcode the old port hit a dead port (e.g. `mios-doctor:62` curls `localhost:11450` -> nothing listens -> false-negative health).

**Instructions:** Pick ONE authoritative `[ports]` table (the 8xxx renumber appears intended -- it is what `install.env`/the live lanes use). Propagate it: (1) sync `C:\mios-bootstrap\mios.toml` `[ports]` to match `C:\MiOS`; (2) resolve every code literal (T-121) from `${MIOS_PORT_*}`; (3) document the container-INTERNAL vs host-published port distinction if the 11xxx values are internal. Add a drift-check that fails when the two repos' `[ports]` tables diverge.

**Files:** `usr/share/mios/mios.toml` `[ports]` (~7615-7646), `C:\mios-bootstrap\mios.toml` `[ports]`, `automation/38-drift-checks.sh`.

**Done When:**
- [x] one `[ports]` table is authoritative and identical across both repos (drift-check enforces it)
- [x] the internal-vs-published port semantics are documented where 11xxx lane ports are legitimately internal
- [x] `mios-doctor`/health probes hit the live port and report the real state

## T-121: NOHC-02 -- De-hardcode port literals in libexec + agent-pipe code (22 sites)  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** NO-HARDCODE/Ports | **Source:** ports/IP audit 2026-07-04 -- 22 evidenced port literals in live code (not comments), most also mismatching the current SSOT.

**Instructions:** Replace each literal with a read from `${MIOS_PORT_*}` / `os.environ.get("MIOS_PORT_*", <SSOT-default>)`. P1 bare-literal sites: `mios-launch:173-179` (cockpit/owui/hermes/prefilter/searxng/forge alias dispatch), `mios-coderun-broker:65` (`:8640/v1/dispatch`), `mios-doctor:62,64,98,171` (`:11450`/`:3030` probes), `Get-MiOS.ps1:4150-4163` (`_ServiceCell -Port` literals), `Heal-MiOSLocalhostForwarding.ps1:33` (hardcoded port array), `build-mios.ps1:4721` (literal port map -- the sibling map at `:5567-5575` already resolves from `[ports]`; copy that pattern), `mios_pipe/routing/portal.py:773,775,864` (served JS `3030`/`8888`). P2 wrong-default fallbacks: `mios-compact:64`, `mios-cron-director:47`, `mios-daemon:87`, `mios-delegation-prefilter:66`, `mios-ingest:54`, `mios-ai-tag:298`, `mios-knowledge-search:48,61`, `gateway-agent/session.py:20`, `mios_pipe/memory/pg.py:79`, `gateway-agent/server.py:278`, `mios_endpoints.py:103`, `install-host-tools.ps1:501`. P3 served-prose: `grounding.py:432-436` (system-prompt bakes `:8640/:11450/:11441/:8642`), `mios-apps:587-591`, `mios-env-probe:189-191`.

**Files:** the ~22 files above.

**Done When:**
- [x] no bare port literal remains in code logic; each reads SSOT with the correct default
- [x] `grounding.py` system-prompt text renders ports from SSOT, not baked literals
- [x] a grep gate (T-125) passes

## T-122: NOHC-03 -- Register the 6 unowned first-party service ports in `[ports]` SSOT  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** SSOT/Ports | **Source:** SSOT-coverage + ports audits 2026-07-04 -- six named MiOS services have their port ONLY as a code literal, with no `[ports]` key and no `userenv.sh` bridge row.

**Instructions:** Add `[ports]` keys (+ `userenv.sh` bridge rows + configurator field) for: `prefilter=8641` (`mios-delegation-prefilter:48` `MIOS_PREFILTER_LISTEN_PORT`), `arbiter=8650` (`mios-policy-arbiter:19`), `oscontrol=11437` (`mios-pc-control:80`), `model_router=11442` (`mios-model-router:38`), `daemon_agent=8644` (`mios-daemon:3082`, `mios-os-control:341`), `mcp=8765` (`mios-mcp-server:735`, `kernel/config.py:134-135`). Then repoint each consumer at `${MIOS_PORT_*}`.

**Files:** `usr/share/mios/mios.toml` `[ports]`, `tools/lib/userenv.sh`, the 6 consumer scripts, `usr/share/mios/configurator/mios.html`.

**Done When:**
- [x] all 6 service ports exist in `[ports]` with defaults and bridge rows; consumers read them
- [x] the configurator exposes them

## T-123: NOHC-04 -- Purge baked operator identity + wire endpoint env vars to SSOT  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** S | **Domain:** NO-HARDCODE/Privacy | **Source:** SSOT-coverage audit 2026-07-04 -- `MIOS_PUBLIC_HOST` defaults to a SPECIFIC operator's Tailscale MagicDNS name `"mios.taildd86d0.ts.net"` baked into `mios_pipe/routing/portal.py:97` (portability + privacy leak). Plus endpoint env vars restate ports instead of reading their existing SSOT keys.

**Instructions:** (1) Remove the tailnet-host literal; default `MIOS_PUBLIC_HOST` to empty/`localhost` and source it from a new `[portal].public_host` SSOT key (degrade-open). (2) Wire these env defaults to their SSOT keys instead of restating ports: `MIOS_HERMES_ENDPOINT` (`kernel/config.py:178` -> `[hermes].endpoint`), `MIOS_HERMES_WORKER_ENDPOINT` (`:185` -> `[agents.hermes].endpoint`), heavy/vllm backends (`kernel/config.py:233-236`, `lanes_resolver.py:122-123`), `MIOS_A2A_DISCOVER_PORT` (`a2a_client.py:238` -> new `[a2a].discover_port`), `MIOS_PUBLIC_DOMAIN` (`a2a.py:478` -> new `[a2a].public_domain`). (3) Fix the orphaned `micro_*` SSOT: `micro_model`/`micro_endpoint` exist in `mios.toml` (~6184/6186) but `userenv.sh` has no bridge row, so `kernel/config.py:262-263` never sees them -> add the bridge rows.

**Files:** `mios_pipe/routing/portal.py`, `mios_pipe/kernel/config.py`, `mios_pipe/routing/lanes_resolver.py`, `mios_pipe/federation/a2a*.py`, `usr/share/mios/mios.toml` (`[portal]`, `[a2a]`), `tools/lib/userenv.sh`.

**Done When:**
- [x] no operator-specific hostname/tailnet id remains as a code default anywhere
- [x] every endpoint env var resolves from its SSOT section; `micro_*` defaults reach the pipe

## T-124: NOHC-05 -- De-hardcode English keyword-gates in agent-pipe  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** NO-HARDCODE/Routing | **Source:** keyword-gate audit 2026-07-04 -- code is mostly clean (router/classifier are model-driven/SSOT) but 4 decision-gating English matchers remain.

**Instructions:** (1) `chat.py:1301-1304` -- inline temporal word-list gating `_time_sensitive`: DELETE it and key off model-emitted `refined.news or refined.needs_recency`. This is the surviving twin of a bug ALREADY fixed at `web_research.py:661-668`; lift that fix verbatim. (2) `routing.py:233` -- hardcoded English connective alternation `(in|and|then|with|on|to)` in `_deterministic_action_route`: move to `mios.toml [routing].compound_connectives`, load via `_load_routing_phrases` (all other vocab in that function is already SSOT-injected). (3) `federation/a2a_client.py:190-192` -- peer modality classification by model-id substrings (`embed|bert|bge` / `diffuse|flux|dall|sd`): derive modality from the SSOT model/engine registry, degrade-open to text. (4) `mios_gateway_queue.py:114-116` -- tool-param JSON-schema `type` inferred from English param-name substrings: read types from the SSOT verb-catalog typed schema (pairs with T-119). Low-priority notes: `cua.py:187-188` (English GOAL_REACHED sentinel/negation -- tighten only if hardening the protocol parse), `mios-finetune:164` (layer-name convention list -- marginal).

**Files:** `mios_pipe/routing/chat.py`, `mios_pipe/routing/routing.py`, `mios_pipe/federation/a2a_client.py`, `mios_gateway_queue.py`, `usr/share/mios/mios.toml` `[routing]`.

**Done When:**
- [x] `chat.py` time-sensitivity is model-flag-driven (no word-list); parity with `web_research.py`
- [x] compound-connective list lives in SSOT; a2a modality + gateway param-types read from SSOT
- [x] non-English / paraphrased inputs route identically (no ASCII-keyword regression)

## T-125: NOHC-06 -- Extend NO-HARDCODE enforcement to ports/IPs in code (not just dates/.container)  [P2]
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** CI/Enforcement | **Source:** ports audit 2026-07-04 -- `usr/libexec/mios/mios-hardcode-lint` only checks date-literals + header/BOM; `check_container_ports` in `38-drift-checks.sh` only scans `.container` Quadlets. Port/IP hardcodes in `.py`/`.sh`/`.ps1` are currently UNENFORCED -- which is how the 22 T-121 sites accumulated.

**Instructions:** Add a `check_code_ports_ips` gate: flag bare port literals (`:\d{4,5}` / `localhost:\d+` / `127.0.0.1:\d+`) and routable IPv4 literals in code logic, with an SSOT allowlist for legitimate exceptions (loopback binds, `0.0.0.0`, documented `172.16/12`, upstream image refs, test fixtures, RFC1918 comments). Wire into `mios-hardcode-lint` + `just drift-gate`. Seed the allowlist from the audit's "NOT violations" set.

**Files:** `usr/libexec/mios/mios-hardcode-lint`, `automation/38-drift-checks.sh`, `usr/share/mios/mios.toml` (allowlist SSOT).

**Done When:**
- [x] the gate flags a newly-introduced `:8640` literal in a `.py`/`.sh` and passes on the cleaned tree (post T-121)
- [x] allowlist is SSOT-driven, not inline

## T-126: NOHC-07 -- SSOT hygiene: subnet IPs, dead bridge rows, configurator drift  [P3]
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** SSOT/Config | **Source:** ports + SSOT-coverage audits 2026-07-04.

**Instructions:** (1) `automation/lib/globals.sh:214-216` -- podman subnet/gateway literals (`10.89.0.0/24`, `10.89.0.1`) as env-fallback defaults with no SSOT key: add `[network]` keys and read them. (2) Prune dead `userenv.sh` bridge rows for removed toml keys (`ports.ollama`, `ports.ollama_cpu`, `ports.hermes_workspace`, `services.ollama_cpu.*`, `image.sidecars.ollama*`/`hermes_workspace*`). (3) Close configurator drift: expose `[ports]` keys missing from `mios.html` (`stack_id`, `hermes_worker`, `hermes_dashboard`, `crawl4ai`, `firecrawl`, `adguard_dns`), `[network.quadlet]` (`core_subnet`, `core_gateway`), `[a2a]` (`protocol_version`, `route_on_card_skills`, `mdns_service_type`, `mdns_refresh_sec`).

**Files:** `automation/lib/globals.sh`, `usr/share/mios/mios.toml` `[network]`, `tools/lib/userenv.sh`, `usr/share/mios/configurator/mios.html`.

**Done When:**
- [x] subnet defaults come from `[network]` SSOT; dead bridge rows removed; configurator has no missing-key drift vs `[ports]`/`[network.quadlet]`/`[a2a]`

## T-127: WIN-01 -- `Get-MiOS.ps1` entry-path prereq fallbacks (git + podman) before the fatal winget-only gates  [P1]
> **Priority:** P1 | **Status:** done | **Effort:** M | **Domain:** Install/Windows | **Source:** Win11-minimal audit 2026-07-04 -- on a fresh Win11 without winget, the canonical `irm|iex` one-liner DIES: `Get-MiOS.ps1:6497` `Require-Cmd "git"` hard-`exit 1`s, and git is only installed via winget (`Install-MiOSTerminalExtras`, `3246-3258`) which returns early if winget is absent (`3158-3161`). The robust PortableGit direct-download exists ONLY in `build-mios.ps1:8458-8480`, which runs AFTER the clone that needs git -- so it can never rescue the entry-path clone. Same shape for podman: `Get-MiOS.ps1:5141-5146` `exit 1` with no entry-path fallback.

**Instructions:** Add PortableGit and podman-setup.exe direct-download fallbacks to `Get-MiOS.ps1` BEFORE the `Require-Cmd git` / podman gates (mirror `Install-MiosPrereqDirect` / the `build-mios.ps1` fallbacks). URLs/pkgs from SSOT `[packages.windows]` / `[bootstrap.prereqs]` (NO-HARDCODE). Ensure `Git.Git` is in the SSOT Windows package list, not only a code fallback list.

**Files:** `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\mios.toml` (`[packages.windows]`, `[bootstrap.prereqs]`).

**Done When:**
- [x] on a winget-less minimal Win11, `irm|iex` self-installs git + podman and completes the clone/bring-up with zero manual steps

## T-128: WIN-02 -- Move the virtualization probe earlier (before disk-shrink + reboot)  [P2]
> **Priority:** P2 | **Status:** done | **Effort:** S | **Domain:** Install/Windows | **Source:** Win11-minimal audit 2026-07-04 -- the BIOS-virt-disabled probe (`VirtualizationFirmwareEnabled`/`HypervisorPresent`) lives only in `build-mios.ps1:8583`, i.e. AFTER `Get-MiOS.ps1` has already shrunk the disk, enabled features, and cloned. A virt-off machine burns a full partition + reboot cycle before failing.

**Instructions:** Run the virtualization probe in `Get-MiOS.ps1` Pass-2, before `Initialize-DataDisk`. Fail fast with the existing "enable VT-x/AMD-V in BIOS" remediation. No behavior change on virt-enabled hosts.

**Files:** `C:\mios-bootstrap\Get-MiOS.ps1`.

**Done When:**
- [x] a virt-disabled machine fails with clear remediation BEFORE any disk/reboot changes

## T-129: WIN-03 -- Podman CLI-only default + optional Desktop, and a login-time autostart "service"  [P2]
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Install/Windows | **Source:** Win11-minimal audit 2026-07-04 (proposed changes, captured as tasks -- NOT yet implemented; the audit agent's speculative edits were reverted pending operator approval).

**Instructions:** (1) Make "Podman for Windows" (CLI, `RedHat.Podman`) the primary/required install; gate Podman Desktop behind `[bootstrap.prereqs].install_podman_desktop` (default `false`). Update the winget-absent hint to point at the podman setup.exe. (2) Register a `MiOS-Autostart` Scheduled Task (AtLogon trigger, RunLevel Highest, hidden) that runs a staged `mios-autostart.ps1` which rebuilds PATH + `podman machine start <distro>` (so systemd inside the distro auto-starts every MiOS quadlet before the interactive desktop) -- the service-equivalent for a per-user WSL/podman-machine context, fail-soft, TOML-gated via `[bootstrap.autostart].enable`, with `HKCU\Run` fallback. Wire teardown into both reap paths (`Invoke-MiOSFullReap` + the `build-mios.ps1` uninstall here-string). NOTE the multi-user/SYSTEM-host caveat: the AtLogon task assumes a per-user podman machine.

**Files:** `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\build-mios.ps1`, `C:\mios-bootstrap\mios.toml` (`[bootstrap.prereqs]`, `[bootstrap.autostart]`).

**Done When:**
- [x] fresh install brings up podman CLI only (Desktop opt-in); the full quadlet stack auto-starts at logon before the desktop, with no UAC prompt; teardown removes the task

## T-130: WIN-04 -- Residual minimal-Win11 hardening (GPU driver / long-path / TLS / offline / entry reconciliation)  [P3]
> **Priority:** P3 | **Status:** done | **Effort:** M | **Domain:** Install/Windows | **Source:** Win11-minimal audit 2026-07-04.

**Instructions:** (1) Add a Windows-side GPU host-driver check/hint (NVIDIA/AMD/Intel) -- with no WSL-capable driver the AI plane silently degrades to CPU (`build-mios.ps1:3932-3947` wires `/dev/dxg`+CDI but never verifies the host driver). (2) Enable `LongPathsEnabled` (defensive). (3) Set `ServicePointManager` TLS 1.2 explicitly (down-level/.NET-old hosts). (4) Document offline/air-gap + proxy behavior (host irm/git/winget rely on system proxy). (5) Reconcile the two divergent "canonical" entry points: `bootstrap.ps1`'s docstring claims canonical but its irm path jumps straight to `build-mios.ps1` (which HAS the no-winget git/podman/wsl auto-install) and skips `Get-MiOS.ps1`'s M:\/elevation/WT staging -- pick one and make the other delegate.

**Files:** `C:\mios-bootstrap\build-mios.ps1`, `C:\mios-bootstrap\Get-MiOS.ps1`, `C:\mios-bootstrap\bootstrap.ps1`.

**Done When:**
- [x] GPU driver absence is detected + surfaced (not silent CPU fallback); long-path/TLS set; one canonical entry point; offline/proxy behavior documented


## T-131: WIN-05 -- Zero-touch offline multi-user Win11 provisioning via SSOT-generated autounattend.xml  [P2, strategic]
> **Priority:** P2 | **Status:** done | **Effort:** L | **Domain:** Install/Windows | **Source:** Win11-minimal audit 2026-07-04 (autounattend research). `autounattend.xml` on install media (or a mounted `unattend.iso` for VMs/Hyper-V) is the canonical, supported, OFFLINE way to preseed Windows Setup in WinPE, BEFORE OOBE (survives interactive-OOBE changes). `cschneegans/unattend-generator` is an MIT-licensed .NET lib (Win10/11 incl. 24H2/25H2), drivable from PowerShell 7.4+ (`Import-Module UnattendGenerator.dll` -> `[UnattendGenerator]::Serialize($gen.GenerateXml($config))`; no public HTTP API -> vendor the lib or use the GUI). Subsumes several audit gaps at the Setup layer: creates multiple LOCAL offline accounts (bypasses the MS-account requirement), runs FirstLogon/UserOnce scripts, partitions disk, enables long-paths (32767), strips bloatware, injects VM drivers. Aligns with the multi-tenant direction (all local offline accounts from SSOT).

**Instructions:** Design + build an SSOT-driven autounattend path: (1) add `[accounts]` (or extend `[identity]`) -- a list of local offline accounts (username / display / group Administrators|Users / first-logon); (2) `New-MiOSAutounattend` renders `autounattend.xml` from that list. **[OPERATOR DECISION]** vendor the MIT lib + pwsh 7.4 (cleaner SSOT; adds a .NET build dep) OR ship a static template personalized by a FirstLogon script from SSOT (no .NET dep). (3) FirstLogon script fires `irm Get-MiOS.ps1 | iex` = truly zero-touch. (4) carve `M:\` + enable long-paths + strip bloat at the Setup layer. (5) wrap into `unattend.iso` (VM/Hyper-V) or drop `autounattend.xml` on USB root. NO-HARDCODE: accounts/partitions/features all from SSOT. SECURITY: autounattend stores passwords plaintext/Base64 -> treat as first-boot temp credentials rotated on first logon (or derive from an SSOT secret at generation time). Relationship: this reduces but does not remove T-127 -- git/podman prereqs are moot inside the automated first-logon, but the plain `irm|iex`-on-an-existing-box path still needs T-127.

**Files:** `C:\mios-bootstrap\` new `New-MiOSAutounattend.ps1` (+ vendored MIT lib or static template + FirstLogon script), `C:\mios-bootstrap\mios.toml` (`[accounts]`/`[identity]`, `[bootstrap.autounattend]`).

**Done When:**
- [x] a fresh, minimal, OFFLINE Win11 machine boots MiOS media -> all SSOT-defined local accounts created, long-paths on, M:\ carved, bloat stripped, Get-MiOS runs at first logon -> full multi-user MiOS with ZERO manual steps (incl. OOBE)
- [x] first-boot passwords are temporary + rotated (no plaintext SSOT-secret leak)
- [x] the generator/template is SSOT-driven (accounts change in mios.toml -> answer file changes; drift-checked)

*Sources: cschneegans/unattend-generator (GitHub, MIT) + schneegans.de/windows/unattend-generator (usage/samples/Example.ps1); autounattend.xml media-root + unattend.iso second-optical-drive discovery; Win11 25H2 local-account install.*

---

<!-- Part 12: MiOS Custom Windows Editions -- UUP + NTLite/DISM + autounattend ISO Program (2026-07-04). Delivered under C:\mios-bootstrap\src\autounattend\ (commits a034894..997ee2f). MiOS-XBOX.iso and irm|iex share one provisioning core -> parity by construction. -->

## T-132: WISO-01 -- Shared install-time provisioning core (`MiOS-Provision.lib.ps1`)  [P2]
> **Priority:** P2 | **Status:** DONE (2026-07-04) | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO -- one core so MiOS-XBOX.iso + irm|iex never drift.

**Context:** The ISO autounattend and the existing-Windows provisioner were duplicating branding/layout/prefs logic (drift risk). Unify into one dot-sourced library.
**Files:** `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`
**Done When:**
- [x] SSOT reader + `Get-MiOSHostname`/`Get-MiOSAccounts` + `New-MiOSBrandingCommands`/`New-MiOSLinuxLayoutCommands`/`New-MiOSGlobalPrefCommands` + `New-MiOSProvisionCommands` emit plain reg/mkdir strings
- [x] dot-sourced by ConvertTo-MiOSPreset, New-MiOSAutounattend, Invoke-MiOSProvision; all parse; MiOS-Xbox.xml regenerates well-formed

## T-133: WISO-02 -- NTLite preset sanitizer (`ConvertTo-MiOSPreset.ps1` -> `MiOS-Xbox.xml`)  [P2]
> **Priority:** P2 | **Status:** DONE (2026-07-04) | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO.

**Context:** Operator NTLite Xbox presets strip WSL/VMP/Hyper-V (the MiOS podman substrate) and carry machine-specific identity (personal account name / machine name / driver-export paths) that must be sanitized to MiOS defaults.
**Files:** `src/autounattend/ConvertTo-MiOSPreset.ps1`, `MiOS-Xbox.xml`
**Done When:**
- [x] Posture B re-preserves WSL2/VMP/Hyper-V; SSOT hostname + credentialed accounts + AutoLogon; FirstLogonCommands = shared provisioning + nested `irm Get-MiOS.ps1 | iex`
- [x] MiOS naming/GUID/ISO label; 0 legacy identity refs; 280/282 debloat entries + all drivers preserved; well-formed

## T-134: WISO-03 -- Schneegans autounattend generator + 96 GB C: carve  (`New-MiOSAutounattend.ps1`)  [P2]
> **Priority:** P2 | **Status:** DONE (2026-07-04) | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO.

**Context:** MiOS ISOs shrink Windows C: to 96 GB and allocate the rest to MiOS; folder layout must be set pre-OOBE (Schneegans DefaultUser context).
**Files:** `src/autounattend/New-MiOSAutounattend.ps1`
**Done When:**
- [x] disk carve C: = `[autounattend].c_partition_gb` (96 GB) + M:=remainder (MIOS-DEV); `-FullDiskWindows` reverts to C:=whole-disk
- [x] pre-OOBE strip-and-rebuild in specialize pass; TPM/SecureBoot/RAM bypass; oscdimg inject; winutil tools drop; well-formed (98304 MB C:, M: Extend)

## T-135: WISO-04 -- Existing-Windows parity path (`Invoke-MiOSProvision.ps1`)  [P2]
> **Priority:** P2 | **Status:** DONE (2026-07-04) | **Effort:** S | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO.

**Context:** Existing Windows users don't reinstall; they must reach the SAME MiOS state as the fresh ISO.
**Files:** `src/autounattend/Invoke-MiOSProvision.ps1`
**Done When:**
- [x] creates SSOT accounts + LIVE-applies the same global branding/layout/prefs the ISO bakes + long-paths, then chains the nested bootstrap
- [x] shares `MiOS-Provision.lib.ps1` with the ISO path (no divergent copy)

## T-136: WISO-05 -- OEM driver export for slipstream (`Export-MiOSDrivers.ps1`)  [P3]
> **Priority:** P3 | **Status:** DONE (2026-07-04) | **Effort:** S | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO.

**Files:** `src/autounattend/Export-MiOSDrivers.ps1`
**Done When:**
- [x] `Export-WindowsDriver -Online` to an SSOT dest (default `M:\MiOS\drivers`, not a hardcoded Desktop path); self-elevates; feeds NTLite Drivers / DISM `Add-WindowsDriver`

## T-137: WISO-06 -- UUP-Dump source-ISO automation (`mios-uup-fetch`)  [P2]
> **Priority:** P2 | **Status:** done | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO -- source-ISO step.

**Instructions:** Wrap `rgl/uup-dump-get-windows-iso` (or `uup-dump/converter` + aria2 + a `ConvertConfig.ini` generated from SSOT) as a MiOS cmdlet; params from `[autounattend.iso]` (build/channel/edition/lang). Pin to **25H2 x64** (26H1 is ARM64-only, T-148). Output a checksummed source ISO to `M:\MiOS\iso\src\`.
**Done When:**
- [x] one command fetches a pinned, checksummed 25H2 x64 source ISO with no GUI; edition/apps/updates controlled from SSOT

## T-138: WISO-07 -- DISM-native debloat + oscdimg assembly + CI  [P2]
> **Priority:** P2 | **Status:** done | **Effort:** L | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO. **[OPERATOR DECISION]** DISM-native vs NTLite-licensed CLI.
>
> **Research (2026-07-04, verified + cited):** see `usr/share/doc/mios/concepts/dism-native-windows-iso-2026-07-04.md`. Verdicts: WSL2 is FULLY offline-bakeable (GitHub WSL MSI + distro rootfs `.tar` + `podman machine init --image <local>`; kernel bundled since WSL 1.0.0 GA); tiny11 standard maker = the reference DISM sequence (keep serviceability, avoid Core); OEM/branding/fonts/cursors bake via the offline `Users\Default\NTUSER.DAT` hive (accent needs a RunOnce backstop; `Segoe UI`->Geist only reskins legacy GDI, NOT WinUI3); local accounts + the scheduled task + a real `M:\` + `podman machine init` are FIRST-LOGON only; LabConfig bypass keys bake offline (Setup-only); pipeline runs headless on GitHub Actions `windows-2025` (install oscdimg, manage ~14 GB disk). Validation gap: air-gapped `podman --image` + 24H2/25H2 Setup UI.

**Instructions:** Strict = DISM-native debloat (appx/capability/feature removal + LabConfig) generated from the same SSOT remove-list (NTLite CLI is paid-only; keep as optional accelerator). Then oscdimg dual BIOS/UEFI build -> `MiOS-Win11.iso` / `MiOS-XBOX.iso`. GitHub-Actions: fetch -> customize -> assemble -> VM smoke-boot.
**Done When:**
- [x] a free/reproducible pipeline produces a bootable MiOS ISO from a UUP source with no paid tool; CI smoke-boots it in a VM and asserts accounts + WSL/VMP present (Posture B) + Get-MiOS reached

## T-139: WISO-08 -- Stage MiOS branding assets into the image  [P2]
> **Priority:** P2 | **Status:** done (2026-07-09) | **Effort:** S | **Domain:** Windows/Install | **Source:** Part 12 WS-WISO.

**Instructions:** Place `mios-wallpaper.jpg`, `mios-logo.bmp`, Bibata `.cur/.ani`, Geist fonts at the branding-referenced paths (`C:\Windows\Web\MiOS\`, `%SystemRoot%\Cursors\Bibata-Modern-Classic\`) during image customization so branding applies at first paint (not just first-logon).
**Done When:**
- [x] wallpaper/logo/lockscreen/cursor/font assets are present in the image; branding renders at OOBE/first paint

## T-140: XBOX-01 -- Xbox Full Screen Experience out of the box  [P2]
> **Priority:** P2 | **Status:** done (2026-07-09) | **Effort:** S | **Domain:** Windows/Gaming | **Source:** Part 12 WS-XBOX -- the operator reference used the WRONG ViVeTool IDs.

**Instructions:** Enable Xbox Mode via `vivetool /enable /id:58989070,59765208` (2026 IDs; requires 24H2 26100.7019+ and the Xbox app installed + signed in, since FSE is the home launcher) + auto-launch config. Replace the reference `unattend-01.ps1` Copilot/taskbar IDs with these FSE IDs. Win+F11 launches it.
**Done When:**
- [x] a fresh MiOS-XBOX boots into (or one Win+F11 away from) the Xbox full-screen/console experience with the Xbox app as home

## T-141: XBOX-02 -- Gaming loadout + Xbox tuning  [P3]
> **Priority:** P3 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Windows/Gaming | **Source:** Part 12 WS-XBOX.

**Instructions:** Adopt the reference `unattend-02/03.ps1` sanitized to MiOS: Xbox services Manual, Teredo/IPv6, Game Mode, Delivery Optimization, FSE regs; winget gaming apps (Steam/Vesktop/Zen). OEM branding -> MiOS (never a personal name).
**Done When:**
- [x] gaming services/tuning applied; gaming apps installed at first logon; no legacy operator branding

## T-142: XBOX-03 -- MiOS-XBOX posture decision (A pure-gaming vs B keep-the-brain)  [P2]
> **Priority:** P2 | **Status:** done (2026-07-09) | **Effort:** S | **Domain:** Windows/Gaming | **Source:** Part 12 WS-XBOX.

**Instructions:** Decide MiOS-XBOX gaming edition posture: A = WSL purged, no local brain (remote/cloud MiOS); B = keep WSL2 -> local MiOS agent stack alongside gaming. Reference is A; MiOS default recommendation = B. The sanitizer's `-KeepVirtualizationDisabled` toggles A.
**Done When:**
- [x] posture chosen + encoded in the editions SSOT; the sanitizer/generator emit the matching virtualization state

## T-143: WBRAND-01 -- Global Windows branding/theme from SSOT  [P2]
> **Priority:** P2 | **Status:** DONE (2026-07-04) | **Effort:** M | **Domain:** Windows/Branding | **Source:** Part 12 WS-WBRAND.

**Files:** `src/autounattend/MiOS-Provision.lib.ps1` (`New-MiOSBrandingCommands`)
**Done When:**
- [x] accent (#1A407F -> AABBGGRR), dark theme + transparency, wallpaper + lockscreen (PersonalizationCSP), OEM info, Dynamic Lighting RGB (accent-tracking), Geist UI font (Segoe UI substitute), Bibata cursor -- applied to Default hive + HKLM + first HKCU, all from SSOT

## T-144: WBRAND-02 -- Linux desktop palette parity via matugen  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** L | **Domain:** Linux/Branding | **Source:** Part 12 WS-WBRAND -- mios.git / deployed image.

**Instructions:** Seed a MiOS matugen config + template set; source color = SSOT `[colors].accent`, source image = SSOT `[branding].wallpaper`; regenerate GTK/Qt/base16 on wallpaper change. Flatpak theming via `org.gtk.Gtk3theme` + `flatpak override`. Geist + Bibata system-wide on Linux. OpenRGB profile from the accent.
**Done When:**
- [ ] Windows and Linux (incl. Flatpaks) render the SAME MiOS palette from one SSOT; wallpaper change reflows both

## T-145: WBRAND-03 -- Re-assert branding on Windows update drift  [P3]
> **Priority:** P3 | **Status:** done | **Effort:** S | **Domain:** Windows/Branding | **Source:** Part 12 WS-WBRAND.

**Instructions:** Windows re-enables/reverts Dynamic Lighting (and can reset accent) on some CU/feature updates -> have `mios update` re-assert `Software\Microsoft\Lighting` + branding from SSOT.
**Done When:**
- [x] post-update, RGB + accent + theme snap back to MiOS SSOT on next `mios update`

## T-146: WEDITION-01 -- Editions SSOT matrix  [P2]
> **Priority:** P2 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WEDITION.

**Instructions:** Add an `[editions]` matrix (name / channel / arch / posture / debloat-profile / accent) so ONE pipeline emits MiOS (full, Posture B) + MiOS-XBOX (gaming) from SSOT; wire the sanitizer/generator to select by edition.
**Done When:**
- [x] `mios-build-iso <edition>` reads the edition row and emits the correct ISO; no per-edition code forks

## T-147: WEDITION-02 -- SSOT keys + configurator for the ISO/branding surface  [P1]
> **Priority:** P1 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Windows/SSOT | **Source:** Part 12 WS-WEDITION -- generators degrade-open to MiOS defaults until added.

**Instructions:** Add to `mios.toml` + expose in `configurator/mios.html`: `[autounattend]` (computer_name, c_partition_gb=96, bootstrap_url, iso_out/label, `[[autounattend.accounts]]`), `[autounattend.layout]` (strip_defaults, strip_folders, linux_tree, lowercase_userfolders, strip_thispc), `[branding]` (oem_manufacturer/model/support_url/logo, wallpaper, lockscreen, wallpaper_style, ui_font, font_substitute, cursor/cursor_dir/cursor_scheme). Drift-check parity.
**Done When:**
- [x] every key the generators read exists in mios.toml with a MiOS default and a configurator control; changing it in mios.html changes the emitted ISO/answer file

## T-148: WEDITION-03 -- ARM64 / 26H1 handheld edition (`MiOS-XBOX-ARM`)  [P3]
> **Priority:** P3 | **Status:** done (2026-07-09) | **Effort:** L | **Domain:** Windows/Install | **Source:** Part 12 WS-WEDITION -- 26H1 = ARM64-only Snapdragon platform update (~Apr 2026), NOT x64.

**Instructions:** For a native-handheld Xbox FSE edition on Snapdragon X2, add an ARM64 UUP source track + ARM64 drivers/packages; keep the x64 gaming build on 25H2. Xbox full-screen is the native home on handhelds.
**Done When:**
- [x] an ARM64 MiOS-XBOX-ARM ISO builds from an ARM64 26H1 UUP source with ARM64 drivers; x64 pipeline unaffected

## T-149: WEDITION-04 -- Fold reverting generated-file changes into the generator source  [P2]
> **Priority:** P2 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Windows/Install | **Source:** Part 12 WS-WEDITION -- `Get-MiOS.ps1`/`build-mios.ps1`/`mios.toml` regenerate ~every 12 min, wiping direct edits.

**Instructions:** Locate the upstream generator that assembles `Get-MiOS.ps1`/`build-mios.ps1`/`mios.toml` and fold in: podman-CLI-only default (Desktop opt-in, T-129), multi-user `MiOS-Autostart` login task, and the `[autounattend]`/`[autounattend.layout]`/`[branding]` SSOT keys (T-147) -- so they survive regeneration.
**Done When:**
- [x] a regeneration cycle preserves the podman-CLI default, the autostart task, and the new SSOT sections

## T-150: ACCT-01 -- Account SSOT schema + install-time seeding (pgvector `account`)  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** L | **Domain:** Data/Accounts | **Source:** operator directive -- DB-driven GLOBAL account control plane (Part 12 WS-ACCT); extends WISO-01/T-132 + WEDITION-02/T-147 from one-shot seeding to a live SSOT.

**Instructions:** Extend pgvector `account` in `usr/share/mios/postgres/schema-init.sql`: kind `user|admin|service`, display, password_hash, uid/gid, groups + sudo/admin, os_targets `linux|windows|both`, enabled, meta. Seed rows from mios.toml `[[accounts]]`/`[identity]` at install (mios-bootstrap on Linux; `MiOS-Provision.lib.ps1` on Windows). LAW: separate the LOGIN account (`account.name`) from the DISPLAY name (`[user].name`) -- purge `MIOS_USER`=display-name usage from every consumer. Vendor default account = `user`/`user`.
**Files:** `usr/share/mios/postgres/schema-init.sql`, `usr/share/mios/mios.toml` (`[[accounts]]`), `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`.
**Done When:**
- [ ] a fresh install seeds the pgvector `account` rows from SSOT; the default `user`/`user` account exists in the DB
- [ ] no consumer resolves the login user from `MIOS_USER`/`[user].name` (the display-name leak is gone)

**Reality check (2026-07-10):** "pending" understates it -- the seeder DOES exist at `usr/libexec/mios/mios-ai-firstboot` (§"seed accounts into pgvector"): it computes SHA-512 hashes (`openssl passwd -6`) and `INSERT … ON CONFLICT DO UPDATE`s the primary `[identity]` account + every `[[autounattend.accounts]]` row, now including `uid`/`gid` (fixed 2026-07-10). It runs at firstboot (not the instructed mios-bootstrap/Provision location). Remaining: the `MIOS_USER` display-name purge (2nd box), and moving the seed earlier if firstboot is too late for the very first login.

## T-151: ACCT-02 -- Linux DB-native accounts via NSS + PAM (libnss-pgsql2 + pam_pgsql)  [P2]
> **Priority:** P2 | **Status:** in-progress (was falsely marked completed; two blocking bugs fixed 2026-07-10, end-to-end still UNVERIFIED) | **Effort:** L | **Domain:** Linux/Accounts | **Source:** operator directive -- "DBs control Linux accounts, live" (WS-ACCT).

**Instructions:** Wire `libnss-pgsql2` (NSS `passwd`/`shadow`/`group` served from pgvector) + `pam_pgsql` (PAM auth against the DB) so the DB is the live Linux account store; a DB edit reflects with no re-provision. `nsswitch.conf` order `files pgsql` so root/service accounts + a DB outage degrade-open. Flag-gate `[accounts].db_backed`; package via mios.toml `[packages.*]`.
**Files:** `automation/17-accounts-db.sh`, `usr/libexec/mios/mios-ai-firstboot` (the actual account seeder), `usr/share/mios/mios.toml`, `/etc/nsswitch.conf` drop-in, PAM stack.
**Reality check (2026-07-10):** the config (`17-accounts-db.sh`) and the account seed (`mios-ai-firstboot`, which DOES set `password_hash`/`is_admin`/`groups`) were wired but **non-functional** for two reasons, now FIXED: (a) every NSS/PAM connection string omitted the port -> libpq defaulted to :5432 while postgres listens on :8432, so `getent`/login stalled on `connect_timeout` and fell through to files; (b) the seeder's `INSERT` omitted `uid`/`gid`, so `getpwnam` resolved a NULL uid. **Still OPEN (cannot verify off a Fedora host):** `libnss-pgsql2`/`pam_pgsql` in `[packages.security]` are the *Debian* names; Fedora's is `libnss-pgsql` (beta, F36-era) and `pam_pgsql` may not be packaged for current Fedora at all -> the `dnf install` may fail and the NSS module may be absent. **Recommendation:** adopt the build-time-bake path (compile PG `account` -> `sysusers.d` + shadow at image build; a files-regenerating runtime daemon) and RETIRE the abandoned NSS modules from the boot-critical auth path.
**Done When:**
- [ ] `getent passwd <db-user>` resolves from pgvector; login authenticates via `pam_pgsql`; a DB edit reflects live  *(port + uid/gid bugs fixed; blocked on NSS-module availability -- unverified on a live Fedora host)*
- [ ] DB outage / local root + service accounts still work (files fallback)

## T-152: ACCT-03 -- Windows DB->SAM live account-sync service (MiOS-XBOX)  [P2]
> **Priority:** P2 | **Status:** completed | **Effort:** L | **Domain:** Windows/Accounts | **Source:** operator directive -- "DBs control Windows accounts, live"; MiOS-XBOX custom Windows edition (WS-ACCT + WS-XBOX).

**Instructions:** Windows has no NSS -> build a MiOS account-sync service (PowerShell `LocalAccounts`/SAM provisioning + optional custom Credential Provider) that watches the pgvector `account` SSOT and applies create/modify/disable/password to local SAM accounts LIVE; auto-create-at-first-login from the DB. Ships in MiOS-XBOX so gaming-edition user/admin accounts are DB-managed and editable from the same surfaces as Linux.
**Files:** `C:\mios-bootstrap\src\autounattend\` new `MiOS-AccountSync` service + provisioning lib; `usr/share/mios/mios.toml` `[accounts]`.
**Done When:**
- [x] editing an account in the DB creates/updates the matching Windows local account live (no re-provision)
- [x] MiOS-XBOX first-logon creates the DB-defined accounts (no MS-account)

**Reality check (2026-07-10):** `MiOS-AccountSync.ps1` creates/enables/disables accounts + toggles Administrators from the DB, BUT provisions each new user with a RANDOM 24-char password -- it NEVER applies the DB `password_hash`/password, so DB->Windows *password* control is a silent no-op (Windows can't accept a stored hash; `New-LocalUser` needs plaintext at create). Account-*existence* sync works; *credential* sync does not. Fix: a first-boot temporary secret (pgcrypto-sealed) + forced rotation, not a durable DB-applied password.

## T-153: ACCT-04 -- DB account management surfaces + consumer cutover  [P2]
> **Priority:** P2 | **Status:** completed | **Effort:** M | **Domain:** UI/Accounts | **Source:** operator directive -- "managed via DB management surfaces; global environments reflect live" (WS-ACCT).

**Instructions:** mios.html/configurator + MiOS App expose account CRUD (add/edit/disable user & admin, set password, groups/sudo, per-OS target) writing the pgvector `account` SSOT; both OSes reflect via T-151/T-152. Cut consumers (both dashboards, cockpit PAM, forge) over to read the account SSOT, never `MIOS_USER`/`[user].name`.
**Files:** `usr/share/mios/configurator/mios.html`, `usr/libexec/mios/mios-dashboard.sh`, `powershell/profile.ps1`, `usr/share/mios/mios.toml`.
**Done When:**
- [x] an account edit in mios.html reflects live on BOTH Linux and Windows
- [x] dashboards show the DB account (default `user`/`user`), never the operator display name

## T-154: MAO-01 -- Typed handoffs + parallel guardrails + tracing spans  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** M | **Domain:** Agents/Orchestration | **Source:** multi-agent research digest (Part 13 WS-MAO); verified OpenAI Agents SDK / Swarm pattern. See `research/multi-agent-orchestration-strategies-2026-07-05.md`.

**Instructions:** In agent-pipe, model handoffs as typed transfer functions returning `{target_agent, Result(context-update)}`; run input/output **guardrails in parallel** on a cheap model (validate + short-circuit); emit a **trace span per hop** (router/refine/synthesis/polish/swarm/council) into the native stream (feeds `feedback_everything_streams_natively_all_surfaces`). Add a server-side `context_variables` dict hidden from the tool schema (light shared state; heavy/volatile stays on-demand per the env-grounding law). All gated in `[agents.orchestration]`; degrade-open (missing guardrail model → pass-through).
**Files:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[agents.orchestration]`).
**Done When:**
- [ ] handoffs are typed transfers (not ad-hoc string routing); a hop failure is caught + traced, not silent
- [ ] input/output guardrails run in parallel and can short-circuit; every hop emits a trace span visible on OWUI/CLI
- [ ] `context_variables` carries light shared state without entering the tool schema

## T-155: MAO-02 -- Structured deliberation for consequential tasks (DCI concept), MODEL-gated  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** L | **Domain:** Agents/Council | **Source:** Part 13 WS-MAO; DCI CONCEPT (source `arXiv 2603.11781` UNVERIFIABLE/post-cutoff -- adopt concept, do NOT cite as authority).

**Instructions:** Upgrade the council hop to optional **structured deliberation**: archetype roles (Framer/Explorer/Challenger/Integrator) via **differentiated system prompts** (bias only -- NOT hardcoded capability), a **typed interaction grammar** (propose/challenge/evidence/reframe/synthesize/concede/…) so a challenge is structurally distinct from a proposal, **tension tracking** (disagreements preserved as first-class objects), and a bounded convergence loop terminating in a **Decision Packet** (action + residual objections + minority report + reopen-conditions) persisted to pgvector. **Cost: ~62× tokens; it HARMS routine tasks** -> the trigger is a **model-driven consequentiality classifier** (Law 7: no keyword gate), gated `[agents.orchestration].deliberation`, default **off**. Routine tasks stay on the cheap council path.
**Files:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/agents/`, `usr/share/mios/postgres/schema-init.sql` (decision_packet), `usr/share/mios/mios.toml`.
**Done When:**
- [ ] a model classifier (not a keyword list) decides deliberation vs cheap path; default off; routine tasks never pay the 62× cost
- [ ] deliberation emits a Decision Packet with a preserved minority report; disagreements are tracked, not averaged away

## T-156: MAO-03 -- Document-mutation + LISTEN/NOTIFY coordination lane on pgvector  [P3]
> **Priority:** P3 | **Status:** pending | **Effort:** M | **Domain:** Agents/Coordination | **Source:** Part 13 WS-MAO; OpenClaw CONCEPT (`arXiv 2603.11721` UNVERIFIABLE) built on existing pgvector.

**Instructions:** Add a decoupled async coordination mode: agents coordinate by **mutating shared rows/docs** in pgvector; a `LISTEN/NOTIFY` (or logical-decode) event bus wakes decoupled worker/daemon agents on mutation -- no direct message-passing, no polling. Every trigger/decision is a row (permanent audit trail); agents know only the shared schema (absolute decoupling). Reuse the MiOS-Daemon supervisor pattern for the subscribers. Flag-gated; degrade-open to the direct-call path.
**Files:** `usr/share/mios/postgres/schema-init.sql`, `usr/lib/mios/agent-pipe/server.py` or a new `usr/libexec/mios/mios-coord-bus`, `usr/share/mios/mios.toml`.
**Done When:**
- [ ] an agent row-mutation wakes a decoupled subscriber via NOTIFY (no polling); the exchange is fully reconstructable from DB rows
- [ ] bus down / disabled → falls back to direct dispatch (degrade-open)

## T-157: MAO-04 -- Manifest-guided progressive-disclosure retrieval  [P3]
> **Priority:** P3 | **Status:** pending | **Effort:** M | **Domain:** Agents/Memory | **Source:** Part 13 WS-MAO; OpenClaw CONCEPT (UNVERIFIABLE) -- an ADDITIONAL retrieval strategy, not a pgvector-recall replacement.

**Instructions:** For large/longitudinal document trees, add retrieval that walks a tree of nodes each carrying a natural-language `manifest` of its children, selecting subtrees via **LLM-select** (reason over descriptions + prune) to a depth bound -- instead of cosine-only similarity. Manifest maintenance is O(depth) per mutation (local update on write). Selectable per query-class from `[agents.orchestration]`; pgvector vector recall remains the default.
**Files:** `usr/lib/mios/agent-pipe/server.py` (retrieval strategy hook), `usr/share/mios/postgres/schema-init.sql` (node/manifest), `usr/share/mios/mios.toml`.
**Done When:**
- [ ] a longitudinal-tree query retrieves via manifest LLM-select traversal with pruned subtrees; precision beats flat vector recall on the target class
- [ ] manifests update locally on document mutation (no full re-embed of siblings)

## T-158: MAO-05 -- Identity-aware delegation: extend agent-passport/A2A (LDP concept)  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** M | **Domain:** Agents/A2A | **Source:** Part 13 WS-MAO; LDP CONCEPT (`arXiv 2603.18043` UNVERIFIABLE) extending the SHIPPED `agent-passport.json` + A2A card.

**Instructions:** Extend the existing MiOS agent identity (A2A card + `agent-passport.json` Ed25519 + `max_permission`) with `reasoning_profile`/`context_window`/`cost_hint`/capability fields for **metadata-aware routing** (cheap-fast model → simple subtasks; heavy lane → hard reasoning), **attested-vs-claimed quality** to defeat the **Provenance Paradox** (routing on self-reported score selects the WORST delegates -- attest via measured outcomes), **governed sessions** (persistent context; stop re-sending history each call), and **trust domains** (capability scopes / data-handling). Extends existing identity -- do NOT adopt the LDP wire protocol blind.
**Files:** agent-passport + A2A card generators (`usr/share/mios/agents/` / `usr/lib/mios/agent-pipe/`), `usr/lib/mios/agent-pipe/server.py` (router), `usr/share/mios/mios.toml`.
**Done When:**
- [ ] delegation routes on attested (measured) quality, not self-claimed score; a self-inflating delegate is not preferred
- [ ] a subtask's model tier is chosen from the delegate's `reasoning_profile`/`cost_hint`; sessions don't re-transmit full history each call

## T-159: MAO-06 -- Progressive payload / token-efficiency modes  [P3]
> **Priority:** P3 | **Status:** pending | **Effort:** M | **Domain:** Agents/A2A | **Source:** Part 13 WS-MAO; LDP CONCEPT (UNVERIFIABLE); feeds `feedback_native_typed_launch_args_all_tools`.

**Instructions:** Negotiate the richest mutually-supported delegation payload mode: text (auditable fallback) → **semantic-frame (typed JSON; ~37% token reduction claimed)** → embedding hints → semantic graph. Auto-fall-back down the chain on unsupported mode. Text mode always retained for auditability. Gated; measure the actual token delta before defaulting up.
**Files:** `usr/lib/mios/agent-pipe/server.py` / A2A transport, `usr/share/mios/mios.toml`.
**Done When:**
- [ ] two MiOS agents negotiate semantic-frame mode and fall back to text when unsupported; measured token reduction is logged
- [ ] no quality regression vs text on a delegation benchmark

## T-160: MAO-07 -- Cheap contribution evaluation → reputation (IntrospecLOO concept)  [P3]
> **Priority:** P3 | **Status:** pending | **Effort:** M | **Domain:** Agents/Reputation | **Source:** Part 13 WS-MAO; IntrospecLOO CONCEPT (UNVERIFIABLE); feeds the existing reputation workstream.

**Instructions:** Score each council/swarm agent's marginal contribution WITHOUT re-running the debate: post-session, prompt the remaining agents to re-decide while ignoring agent *j*'s inputs; the outcome delta ≈ leave-one-out at O(N) not O(T·N²). Write scores to the pgvector `reputation` table (down-weight consistently-negative/adversarial agents; surface high-value ones in future fan-outs). Gated; degrade-open (no scoring → equal weights).
**Files:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/postgres/schema-init.sql` (reputation), `usr/share/mios/mios.toml`.
**Done When:**
- [ ] each agent gets an O(N) introspective LOO contribution score after a council session; a positively-necessary agent scores > a redundant one
- [ ] scores feed reputation weighting in the next fan-out; no scoring model → equal weights (degrade-open)

## T-161: MAO-08 -- Selectable topology + debate protocol from SSOT  [P2]
> **Priority:** P2 | **Status:** pending | **Effort:** M | **Domain:** Agents/Orchestration | **Source:** Part 13 WS-MAO; verified swarm/mesh/hierarchical/pipeline + debate-protocol taxonomy.

**Instructions:** Make the fan-out **topology** (pipeline / hierarchical / swarm / mesh) and **debate protocol** (within-round / cross-round / rank-adaptive cross-round) selectable per task-class from `[agents.orchestration]` + the orchestrator's own judgement (Law 7: model-driven, no keyword gate). Document the trade-off: within-round maximizes peer-reference/interaction but converges slowly; rank-adaptive cross-round converges fastest. No single hardcoded choice.
**Files:** `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` (`[agents.orchestration]`).
**Done When:**
- [ ] topology + debate protocol are chosen per task-class from SSOT/orchestrator judgement, not a fixed hardcoded path
- [ ] switching protocol changes convergence/interaction behaviour as documented; default degrades open to the current fan-out

## T-162: WBRAND-04 -- SSOT living-wallpaper shader (self-authored, permissive)  [P3]
> **Priority:** P3 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Branding | **Source:** operator research digest (mesh gradients / WebGPU / Hyprland-Quickshell), filed for later. See `research/mesh-gradient-living-wallpaper-2026-07-06.md`.

**Instructions:** Author a small (~40-line) WGSL/GLSL mesh-gradient fragment shader whose colors come from SSOT `[colors].accent`/`[colors].bg` (the same values behind the static wallpaper + DWM accent + matugen). No third-party license -- OR Apache-2.0 BabylonJS if a full engine is wanted. **LAW: never vendor `firecmsco/neat` (MIT + Commons Clause) or any non-OSI dep into a shipped OS; verify every LICENSE at vendor time.** Degrade-open ladder: animated shader → static SSOT gradient (current baked JPG) → solid accent. Gated `[branding].living_wallpaper` (off by default).
**Files:** `usr/share/mios/branding/living-wallpaper.wgsl` (new), `usr/share/mios/mios.toml` (`[branding]`).
**Done When:**
- [x] the shader renders a mesh gradient from SSOT colors only (no hardcoded palette); disabled by default
- [x] auto-degrades to the static gradient on no-Vulkan/old-iGPU; no Commons-Clause/non-OSI dependency vendored

## T-163: WBRAND-05 -- Linux living wallpaper (GNOME layer / optional Quickshell)  [P3]
> **Priority:** P3 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Linux/Branding | **Source:** operator research digest (filed for later); depends on T-162.

**Instructions:** Render the T-162 shader NATIVELY on Linux (Qt6 RHI→Vulkan/OpenGL on the Mesa iGPU -- MiOS ships `[packages.gpu-mesa]`), not WebGPU-in-browser. GNOME/Wayland has no shader-wallpaper API → a minimal Wayland-background helper or `mpvpaper` video loop; an OPTIONAL Hyprland/Quickshell desktop profile may use a native `ShaderEffect` (refs: MIT `magetsu002/qs-wallpaper-picker`, `bjarneo/quickshell`). Universal fallback = pre-rendered loop. Gated + off by default.
**Files:** `usr/libexec/mios/mios-living-wallpaper` (new), `usr/share/mios/mios.toml`.
**Done When:**
- [x] the SSOT mesh gradient animates on a MiOS GNOME/Wayland desktop via the iGPU; falls back to static/video where unsupported
- [x] no browser/WebGPU-flag dependency on the Linux path

## T-164: WBRAND-06 -- Windows animated background + SSOT living-wallpaper keys  [P3]
> **Priority:** P3 | **Status:** done (2026-07-09) | **Effort:** M | **Domain:** Windows/Branding | **Source:** operator research digest (filed for later); MiOS-XBOX/MiOS-Win; depends on T-162.

**Instructions:** Add a MiOS-XBOX/MiOS-Win animated desktop background from the T-162 shader/palette (borderless WebView2/D3D canvas at background z-order, OR a pre-rendered loop -- most compatible). WebGPU-in-browser (WebView2/D3D12) is acceptable ONLY on Windows. Add `[branding].living_wallpaper` + `living_wallpaper_mode` (`shader|video|static`) to mios.toml + configurator; wire into the Windows branding path (`MiOS-Provision.lib.ps1` / `Set-MiOSIdentityOffline`, alongside the current static gradient).
**Files:** `usr/share/mios/mios.toml` (`[branding]`), `usr/share/mios/configurator/mios.html`, `C:\mios-bootstrap\src\autounattend\MiOS-Provision.lib.ps1`.
**Done When:**
- [x] `living_wallpaper_mode=static` keeps today's baked gradient (no regression); `shader`/`video` add the animated layer from SSOT colors
- [x] the mode is exposed in the configurator and read from the layered SSOT

## T-165: NAME-01 -- Global naming minification → one unified names/keys registry  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** XL | **Domain:** SSOT/Cross-cutting | **Source:** operator directive 2026-07-10.

**Instructions:** Collapse every authored name in MiOS (TOML keys, `MIOS_*` env vars, verbs, `globals.sh`/`.ps1` consts, configurator `data-key`s, emitters — ~1,290 today) onto ONE unified names/keys registry that is the naming SSOT. **No translation layer** — delete the 418-entry `userenv.sh` key→env table + the `globals` mirror; every surface sources the same canonical identifier directly from the one registry (generated, never mapped). **Fold similar** capabilities into one parametric entry; keep exactly one name per capability (minimal, combined). **NO loss of functionality** — rename/collapse only, via a compat-shim phase. Full workflow, convention, phased migration + drift-gate: `usr/share/doc/mios/reference/naming-unification.md`.
**Files:** `usr/share/mios/names.toml` (new registry) or `mios.toml [names]`, `tools/lib/userenv.sh` + `usr/lib/mios/userenv.sh` (delete table → generic sourcing), `automation/lib/globals.sh`/`.ps1`, `usr/lib/mios/mios_toml.py`, `automation/38-drift-checks.sh` (new gate), `usr/share/doc/mios/reference/naming-unification.md`.
**Done When:**
- [ ] one unified names/keys registry is the SSOT; every surface is generated from / sources it (no authored per-name mapping or translation anywhere)
- [ ] similar capabilities folded to one parametric entry; one canonical name per capability; legacy names + the userenv table deleted; zero functional regression
- [ ] a drift-gate regenerates + diffs the registry and fails on any new translation/duplicate; all `test_mios_*` + `just drift-gate` green

## T-166: DEPLOY-01 -- Install/first-boot reorder → eliminate "missing dependency" states  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Install/Deploy/SSOT | **Source:** operator directive 2026-07-10 (surfaced by the clean reinstall debug).

**Instructions:** Refactor + reorder the install and first-boot pipeline into a logical dependency DAG so a "missing dependency / prerequisite-not-ready / artifact-not-built" state is structurally impossible. (1) Model the producer→consumer DAG across `automation/NN-*.sh` + the `*-firstboot` units; encode edges as systemd `After=`/`Requires=`/`ConditionPathExists=`. (2) Replace fixed timeouts with readiness gates (poll the real health/socket/row/file signal + `Restart=on-failure`). (3) Make every producer atomic + retried + idempotent + completeness-self-checking (the `38-hermes-agent.sh` venv fix — install `-r requirements.txt` in one retried transaction — is the reference pattern; apply to the webtools/sandbox image builds, GGUF/vLLM fetch, forge bootstrap). (4) Topologically reorder the overlay/automation sequence. (5) Add a drift-gate that fails the build on any consumer-before-producer edge (missing `After=`/`Condition*=`). Full plan: `usr/share/doc/mios/reference/install-ordering.md`.
**Files:** `automation/38-hermes-agent.sh` (done), `usr/libexec/mios/mios-ai-firstboot`, `usr/libexec/mios/mios-webtools-firstboot.sh`, `usr/libexec/mios/forge-firstboot.sh`, the `*-firstboot`/`38-*` units + their `.service` `After=`/`Condition*=`, `automation/build.sh`, `automation/38-drift-checks.sh` (new gate), `usr/share/doc/mios/reference/install-ordering.md`.
**Done When:**
- [ ] every consumer step is gated on its producer's real readiness (no fixed-timeout aborts); every producer is atomic + retried + idempotent + completeness-checked
- [ ] a clean `podman-MiOS-DEV` reinstall deploys a fully-working system (AI plane + forge + webtools) with zero "missing dependency" failures
- [ ] a drift-gate fails the build on any consumer-before-producer edge; `just drift-gate` + `test_mios_*` green


<!-- Consolidation note: carried forward 11 NEW actionable tasks (T-167..T-177) from the 9 top-level 2026-06-14/15 plan docs. Everything else in those plans is ALREADY a T-* or already shipped in code: G3->T-049, G5->T-062/T-064, G6->T-035, G7->T-045/T-072/T-061, G8/K1->T-111, G10->T-011/T-051/T-022, G11->T-003/T-004, G2-arbiter->T-033 (+shipped mios-policy-arbiter), K5->T-037/T-026, W0-T1 SSOT-lint->shipped (38-ssot-lint.sh), W2-T1 passport->T-001/T-010/T-012/T-014, W2-T3 tracing->T-023, and the entire WS-A/B/C/D/E/H + tool-consolidation initiatives->shipped in code. Those are NOT duplicated below. -->
<!-- Format matches TASKS.md; header line adds Who (agent/role) + Source per the consolidation brief. Status judged from codebase greps, not from plan-doc intent. -->

---

## T-167: SHELL-01 -- Persistent PTY / stateful shell substrate  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Tool-execution/Sandbox | **Who:** agent-pipe backend engineer (Python + bwrap/tmux) | **Source:** AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md (G9)

**Context:** Every shell/code call is isolated -- `cwd`/`env`/history are discarded between turns. tmux, `mios-sandbox-exec`, `mios_aci`, and session-keying all exist, but there is no long-lived shell process the agent can write to across calls. Repo grep confirms no `mios_pty`/`mios-shell-session`/`run_in_shell` today; nothing in T-001..T-166 covers it.

**Instructions (WHAT + HOW):**
1. Add `mios_pty.py` (pure module, sibling to `mios_aci`): session-id keying, tmux-argv construction, and a marker-sentinel + per-command nonce protocol to capture completion/exit-code/cwd (hardened against output spoofing). Ship `test_mios_pty.py`.
2. Add `usr/libexec/mios/mios-shell-session`: tmux-backed bash, one session per chat, confined in the existing bwrap jail at `--level baseline` (reuse UID 828, no new container).
3. Bound output through the existing `mios_aci` normalizer (head+tail+marker elision).
4. Add `mios-shell-session-gc.{service,timer}` (idle reaper) + tmpfiles for `/var/lib/mios/shell-sessions`.
5. Register `[verbs.shell_session]` (model_name `run_in_shell`) + a `[shell_session]` config block in `mios.toml` (auto-projects to MCP/OpenAI/A2A -- no new dispatch code).

**Where (files):** `usr/lib/mios/agent-pipe/mios_pty.py` (new) + test | `usr/libexec/mios/mios-shell-session` (new) | `usr/lib/systemd/system/mios-shell-session-gc.{service,timer}` (new) | `usr/lib/tmpfiles.d/` | `usr/share/mios/mios.toml`

**When (deps/order):** None hard. Independent of other Part-17 items.

**Done When:**
- [ ] `exec --session t1 'cd /tmp && export FOO=bar'` then `exec --session t1 'echo $PWD $FOO'` returns `/tmp bar` (cwd+env persist across calls)
- [ ] A 5MB log returns ACI-elided (head+tail+marker), not truncated raw
- [ ] Idle sessions are reaped by the GC timer; `run_in_shell` appears on `/v1/tools`
- [ ] `test_mios_pty.py` passes (nonce/marker parse + exit-code capture)

---

## T-168: KENF-01 -- Tetragon eBPF/LSM kernel enforcement plane  [P2] [VM]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Security/Kernel | **Who:** security engineer (eBPF/Tetragon + bootc quadlets) | **Source:** AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md (G2-rest)

**Context:** The out-of-process intent arbiter (`mios-policy-arbiter` + `mios_pipe/access/arbiter.py`) is shipped, but there is no in-kernel enforcement of side-effects: a compromised AI process can still `execve`/connect outbound. The roadmap's only sandboxing is microVM/Kata (T-032, a refuse-into-VM model); no eBPF/LSM tripwire exists. eBPF is the layer that verifies side-effects the arbiter can only reason about.

**Instructions (WHAT + HOW):**
1. Add `mios-enforcer.container` running Cilium Tetragon (standalone, file-based TracingPolicies, no K8s) as user `mios-enforcer` -- a DOCUMENTED Law-6 privileged exception (CAP_BPF/CAP_SYS_ADMIN); add it to the `99-postcheck.sh` allowlist alongside mios-ceph/k3s with a header rationale.
2. Add `mios-enforcer-render` (compiles `mios.toml [security.policy]` -> Tetragon TracingPolicy YAML) + a firstboot oneshot; seed policies (`policies.d/*.yaml.tmpl`: exfil-block tcp_connect, exec-guard execve/LSM) cgroup-scoped to the AI + codemode units only.
3. Add `mios-enforcer-shipper` writing `enforcer_kill`/`enforcer_deny` rows back to the `event`/`tool_call` tables.
4. Add `[security.enforcer]` + `[security.policy]` SSOT sections + configurator cards + `mios-enforcer` sysuser.
5. Gate the unit `ConditionVirtualization` OFF on WSL2 (no BPF/LSM surface); enforcement is bare-metal only, ships in observe mode first.

**Where (files):** `usr/share/containers/systemd/mios-enforcer.container` (new) | `usr/libexec/mios/mios-enforcer-render` + `-shipper` (new) | `automation/99-postcheck.sh` (allowlist) | `usr/lib/sysusers.d/` | `usr/share/mios/mios.toml`

**When (deps/order):** After the arbiter (already shipped). Shares the dangerous-verb/taint set with T-033 (SEC-02).

**Done When:**
- [ ] In observe mode, a tainted process's disallowed `execve`/outbound connect emits a Tetragon Post event + a shipper row
- [ ] Flip to enforce -> the offending process is SIGKILLed
- [ ] Unit is inert (Condition-skipped) on the WSL2 dev VM; `bootc container lint` + Law-6 postcheck pass with the documented exception
- [ ] `[security.policy]` edit re-renders the TracingPolicy YAML (no hardcoded policy)

---

## T-169: ISOL-01 -- Per-action isolation tier ladder (promote-not-refuse)  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Security/Sandbox | **Who:** security engineer (OCI runtimes + agent-pipe dispatch) | **Source:** AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md (G4)

**Context:** Tiers 1-2 exist (`mios-sandbox-exec` bwrap, `mios-coderun-sandbox@` rootless podman) but gVisor/microVM are absent and the taint plane only REFUSES. Distinct from T-032 (SEC-01, hermetic microVM per tool): this is a tier-selection/promotion engine that runs a tainted/high-risk action in a *stronger* tier instead of blocking it.

**Instructions (WHAT + HOW):**
1. Add `[isolation]` table to `mios.toml`: ladder definition, taint->tier map, `taint_min_tier`, `default_code_tier`, `health_gate`; reuse the existing high-privilege verb set (do not re-list).
2. Add `mios_isolation.py` (pure tier-selection/promotion) + tests.
3. In dispatch, replace binary REFUSE-on-taint with `resolve_effective_tier()` -> run in the promoted tier, emit a `firewall_promote {from_tier,to_tier}` event; degrade-CLOSED to `firewall_block` if the floor tier is unavailable.
4. Register `runsc` (gVisor, tier 3) + `krun` (libkrun via crun, tier 4) as OCI runtimes; add USER-scope Quadlet templates reusing the hardened sandbox verbatim, `krun` gated `ConditionPathExists=/dev/kvm`.
5. Add `mios-coderun-tier` launcher + a gated `automation/NN-isolation-tiers.sh` build hook.

**Where (files):** `usr/lib/mios/agent-pipe/mios_isolation.py` (new) + test | `usr/lib/mios/agent-pipe/server.py` (dispatch taint branch) | `usr/share/containers/containers.conf.d/*-isolation-runtimes.conf` (new) | `usr/libexec/mios/mios-coderun-tier` (new) | `usr/share/mios/mios.toml`

**When (deps/order):** Shares the sandbox substrate with T-032/T-045; the promote decision should read the same dangerous-verb set as T-033/T-168.

**Done When:**
- [ ] Taint a session (external `open_url`) -> dispatch a high-priv verb -> `event` shows `firewall_promote` and the verb ran inside the promoted tier
- [ ] With `[isolation].enable=false`, behavior is byte-identical to today
- [ ] Tier-4 (microVM) Quadlet is inert on WSL2 (no `/dev/kvm`)
- [ ] `test_mios_isolation.py` passes (tier selection + degrade-closed)

---

## T-170: GVLM-01 -- Activate grounding VLM + cu_act/cu_verify verbs  [P1]
> **Priority:** P1 | **Status:** in-progress | **Effort:** M | **Domain:** Computer-Use/Perception | **Who:** computer-use engineer (llama.cpp vision + verbs) | **Source:** AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md (G1)

**Context:** The perception->action->verify chain (`mios-pc-vision`, `cu_ground`, `mios-verify-launch`) exists but is INERT: `usr/share/mios/llamacpp/mios-llm-light.yaml` already maps `qwen3-vl:4b` -> a staged Holo1.5-7B GGUF + mmproj, yet `mios.toml [ai].vision_grounding_model` is empty so the lane never activates, and there is no `cu_act`/`cu_verify` verb or `mios-cu-verify` tool. (T-038 CU-01 covers verify-after-action as a concept but not the model activation or these two verbs.)

**Instructions (WHAT + HOW):**
1. Bake/reference the vision GGUF (Holo1.5-7B Q4_K_M + mmproj-Q8_0, already named in `mios-llm-light.yaml`) into the bound `mios-llm-light` seed and set `[ai].vision_grounding_model="qwen3-vl:4b"` (+ `vision_grounding_enable` gate). Operator performs the actual weight fetch (classifier blocks assistant HF fetch); verify mradermacher filenames at bake time.
2. Add `usr/libexec/mios/mios-cu-verify` -- a visual Definition-of-Done tool (screen analogue of `mios-verify-launch`) that returns `{ok:false}` honestly when the lane is down (no fabrication).
3. Add a `cu_act` subcommand to `mios-computer-use` (ground->click->verify) and register `[verbs.cu_verify]` + `[verbs.cu_act]` (three-projection).
4. Set `[computer_use].verify_after_act`. Keep AT-SPI grounding as the deterministic fast path; VLM only on canvas/Electron misses.

**Where (files):** `usr/share/mios/mios.toml` (`[ai]`/`[computer_use]` keys + verbs) | `usr/share/mios/llamacpp/mios-llm-light.yaml` (already staged) | `usr/libexec/mios/mios-cu-verify` (new) | `usr/libexec/mios/mios-computer-use`

**When (deps/order):** Independent; rides the existing `cu_*` + verify tooling. Operator bake step gates final live verification.

**Done When:**
- [ ] `curl <light-lane>/v1/chat/completions model=qwen3-vl:4b` with a base64 screenshot returns coordinate JSON
- [ ] `mios-pc-vision <png> "the OK button"` returns `{x,y,confidence>0.5}`
- [ ] `mios-cu-verify "<criterion>"` returns `{ok:false}` honestly when the lane is down
- [ ] `cu_act`/`cu_verify` appear on `/v1/tools`; with `vision_grounding_enable=false` the path is inert

---

## T-171: CONS-01 -- Weighted multi-judge consensus pipeline  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Orchestration/Judging | **Who:** orchestration engineer (agent-pipe judge path) | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W3-T2); AIOS-MIOS-MASTER-PLAN K4

**Context:** The DCI critic/judge gives a yes/no verdict; GAP-1/GAP-2 (T-047/T-048) cover pre-synthesis diversity + confidence-bypass. A scored, reliability-weighted consensus (weighted-vote + Reciprocal-Rank-Fusion over 2-3 lanes) does not exist. No `mios_consensus` module or `[consensus]` section today.

**Instructions (WHAT + HOW):**
1. Add `mios_consensus.py` (pure): weighted_vote + RRF over 2-3 judge lanes; weights optionally sourced from `reliability_run` (T-049 gate output); degrade-open to a single judge on the fast CPU path. Ship `test_mios_consensus.py`.
2. Wire into the judge/synthesis path in `server.py` behind a `[consensus]` gate.
3. Add `[consensus]` SSOT section + configurator card.

**Where (files):** `usr/lib/mios/agent-pipe/mios_consensus.py` (new) + test | `usr/lib/mios/agent-pipe/server.py` (judge/synthesis) | `usr/share/mios/mios.toml`

**When (deps/order):** Builds on T-049 (reliability scorer) for weights; degrade-open so it functions without it.

**Done When:**
- [ ] Multi-judge DoD reached with a quorum; conflicting judges resolved by weighted vote
- [ ] Fast CPU path stays single-judge when `[consensus].enable=false`
- [ ] `test_mios_consensus.py` passes (weighted_vote + RRF math)

---

## T-172: CONS-02 -- JSD drift monitor  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Observability/Safety | **Who:** orchestration engineer (metrics + pgvector) | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W3-T3); AIOS-MIOS-MASTER-PLAN K4

**Context:** There is no distribution-drift alarm. A Jensen-Shannon-divergence monitor over intent/score/verdict distributions vs a frozen baseline is the early-warning signal for Goodhart/reward-hacking as self-improvement (T-062/T-064) and consensus (T-171) come online. Not built; no `mios_drift`/`drift_snapshot`/`/v1/drift` today.

**Instructions (WHAT + HOW):**
1. Add `mios_drift.py` (pure JSD over intent/score/verdict histograms vs a frozen baseline) + `test_mios_drift.py`.
2. Add a `drift_snapshot` table (`schema-init.sql`) storing the baseline + periodic samples.
3. Add `GET /v1/drift` + a `drift_alert` event when `JSD > threshold`.
4. Add `[drift]` SSOT section (threshold, window, `enable=false`).

**Where (files):** `usr/lib/mios/agent-pipe/mios_drift.py` (new) + test | `usr/share/mios/postgres/schema-init.sql` | `usr/lib/mios/agent-pipe/server.py` (`/v1/drift`) | `usr/share/mios/mios.toml`

**When (deps/order):** Pairs with T-171/T-049; can land independently as an observe-only alarm.

**Done When:**
- [ ] `JSD > threshold` emits a `drift_alert` event
- [ ] `GET /v1/drift` returns current divergence vs baseline
- [ ] `drift_snapshot` records a baseline row on first run

---

## T-173: GUARD-01 -- Daemon runaway controls (host-pressure gate + dedup + cron cap)  [P0]
> **Priority:** P0 | **Status:** planned | **Effort:** M | **Domain:** Autonomy/Safety | **Who:** agent-pipe/daemon engineer | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W0-T2)

**Context:** Five subsystems guard the shared 4090 with independent local heuristics that don't compose; the daemon->swarm runaway had no cumulative tripwire and no host-pressure circuit breaker. This is the direct fix for the live GPU-runaway incident and is not represented in T-001..T-166.

**Instructions (WHAT + HOW):**
1. Add `_host_pressure_gate()` to `mios-daemon`: cached loadavg + `nvidia-smi` (~5s TTL) guarding the classify/refusal/cron/suggestions loops (skip a tick under pressure).
2. Add per-`(source,kind,summary-hash)` dedup + cooldown so repeated identical high-sev classifications are suppressed.
3. Add a cron concurrency cap (track Popen) so cron actions cannot stack.
4. Feed a quiescence/auto-halt signal into cadence backoff.
5. Add a `[daemon]` section + configurator for the thresholds/TTL/cap (no hardcoded literals).

**Where (files):** `usr/libexec/mios/mios-daemon` | `usr/share/mios/mios.toml` (`[daemon]`) | configurator

**When (deps/order):** First-wave safety; composes with T-174 (budget) and the existing admission controller into one pressure signal.

**Done When:**
- [ ] Repeated identical high-sev classifications are suppressed (dedup+cooldown)
- [ ] Loops skip a tick under host pressure (gate fires)
- [ ] Concurrent cron actions cannot stack (cap enforced)
- [ ] `test_mios_daemon.py` covers the gate + dedup

---

## T-174: GUARD-02 -- Aggregate token/turn budget + background preemption  [P0]
> **Priority:** P0 | **Status:** planned | **Effort:** M | **Domain:** Autonomy/Scheduling | **Who:** agent-pipe scheduler engineer | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W0-T3)

**Context:** No cumulative token/turn ceiling exists; a background loop can consume unbounded GPU. Autonomous work is not first-class isolated at the queue. Not captured in T-001..T-166 (the priority scheduler has no aggregate budget signal).

**Instructions (WHAT + HOW):**
1. Add a cumulative token/turn ceiling debited per-conversation AND per-autonomous-source, hard-halting on exhaustion.
2. Give `mios_autonomous` its own low budget + the lowest dispatch priority so a foreground turn preempts background for the next GPU slot.
3. Add a `max_dispatch_depth` recursion bound.
4. Route via `[budget]`/`[dispatch]` SSOT + configurator.

**Where (files):** `usr/lib/mios/agent-pipe/server.py` | `usr/share/mios/mios.toml` (`[budget]`/`[dispatch]`)

**When (deps/order):** Pairs with T-173; both must compose into the single host-pressure signal the admission controller/swarm-width reads.

**Done When:**
- [ ] A background loop self-limits at its budget (hard-halt on exhaustion)
- [ ] A foreground turn preempts background for the next GPU slot
- [ ] Recursion beyond `max_dispatch_depth` is refused

---

## T-175: DURA-01 -- pgvector durability + exposure hardening  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Data/Durability | **Who:** platform/ops engineer (systemd timers + quadlets) | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W0-T4)

**Context:** pgvector holds the entire "brain" (knowledge, memory, passports, audit) with no backup, historically bound `0.0.0.0` on default creds, and is not bootc-rollback-versioned while the OS half is immutable -- an inverse-asymmetry risk. (Embed-on-write in `mios-ingest` is already handled elsewhere; backup + bind hardening are not.)

**Instructions (WHAT + HOW):**
1. Add `mios-pgvector-backup.{service,timer}` running a nightly `pg_dump` to `/var/lib/mios/backups` (declare the dir via tmpfiles, per NO-MKDIR-IN-VAR).
2. Bind pgvector to `127.0.0.1` by default; require a non-default password before any off-loopback bind.
3. Add a `[pgvector]` SSOT section for bind/creds/backup retention + configurator.

**Where (files):** `usr/lib/systemd/system/mios-pgvector-backup.{service,timer}` (new) | `usr/lib/tmpfiles.d/` | pgvector quadlet | `usr/share/mios/mios.toml` (`[pgvector]`)

**When (deps/order):** Independent; complements T-060 (DATA-02 storage versioning) and any schema-rollback work.

**Done When:**
- [ ] The backup timer runs and writes a restorable `pg_dump` to `/var/lib/mios/backups`
- [ ] `ss -ltnp` shows pgvector bound to `127.0.0.1` on defaults; off-loopback bind refused without a non-default password
- [ ] `bootc container lint` + NO-MKDIR-IN-VAR postcheck pass (dir via tmpfiles)

---

## T-176: DURA-02 -- Secret/PII redaction on persist + federate  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Security/Privacy | **Who:** agent-pipe backend engineer | **Source:** MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md (W2-T4)

**Context:** Secrets/PII are written verbatim to pgvector, broadcast on the scratchpad, and echoed over A2A. There is no redaction pass before persistence or federation. Not captured in T-001..T-166.

**Instructions (WHAT + HOW):**
1. Add a redaction filter applied before every pgvector write, scratchpad broadcast, and A2A echo (reuse/extend the existing persistence sanitization that already strips vendor names/paths).
2. Cover secret patterns (keys/tokens) + common PII; make patterns SSOT-configurable, not hardcoded English literals.
3. Gate via `[security]` (default-on for persist, degrade-open documented).

**Where (files):** `usr/lib/mios/agent-pipe/server.py` (persist/scratchpad/A2A echo paths) | `usr/share/mios/mios.toml` (`[security]`)

**When (deps/order):** Should precede any non-loopback A2A federation (composes with the passport gate T-001/T-014).

**Done When:**
- [ ] A secret/PII string in a turn is scrubbed before it reaches pgvector, the scratchpad, or an A2A echo
- [ ] Redaction patterns are read from SSOT (no hardcoded deny-list)
- [ ] `test_*` covers redact-on-persist and redact-on-federate

---

## T-177: LSFS-01 -- Semantic-FS verbs + task-state protocol  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** L | **Domain:** Memory/Filesystem | **Who:** agent-pipe engineer (verbs + pgvector) | **Source:** AIOS-MIOS-MASTER-PLAN-2026-06-14.md (K6)

**Context:** docs-index + pgvector + scratch exist, but there is no LSFS-style semantic-filesystem verb surface (mount/create/write/search/rollback/share over FS + pgvector) and no durable directory-prompt execution-state protocol (`tasks/backlog|in-progress|done.md`) the agent maintains across turns. Low-priority depth item, partly speculative; distinct from pgvector recall. Not in T-001..T-166.

**Instructions (WHAT + HOW):**
1. Add `[verbs.lsfs_*]` cmd-template verbs (mount/create/write/search/rollback/share) backed by FS + pgvector + nomic-embed (no new runtime dep; pure cmd-template so it auto-projects).
2. Add a `tasks` table (or `tasks/*.md` dir protocol) the agent reads/writes to persist backlog/in-progress/done state across turns; wire read into prompt assembly as a tool-sourced block (never `pre_llm_call` auto-prepend -- honors the no-injection rule).
3. Add an `[lsfs]` SSOT section + configurator.

**Where (files):** `usr/share/mios/mios.toml` (`[verbs.lsfs_*]`, `[lsfs]`) | `usr/share/mios/postgres/schema-init.sql` (`tasks`) | `usr/lib/mios/agent-pipe/server.py` (task-state read into assembly)

**When (deps/order):** Independent, last (P3). Reuses the memory/knowledge substrate.

**Done When:**
- [ ] `lsfs_write` then `lsfs_search` round-trips a semantic query over stored content
- [ ] `lsfs_rollback` restores a prior version of a semantic-FS entry
- [ ] Task-state survives a restart and is surfaced only via a tool call, not auto-injected

## T-178: HEAVY-01 -- provision the heavy dGPU model so the stated lanes deploy  [P1]
> **Priority:** P1 | **Status:** in-progress | **Effort:** M | **Domain:** AI-plane/Inference/Deploy | **Who:** inference/deploy agent | **Source:** live dGPU diagnosis 2026-07-10; the SSOT lane defaults (`[lanes.*]`, `[ai.host_thresholds]`, `lane_priority`).
**Instructions (WHAT + HOW):** Honor the ALREADY-STATED SSOT lane defaults -- do NOT re-decide which lane is default/optional. The only fix is to DEPLOY them by provisioning the heavy model. (1) **Provision the heavy-lane model** so `mios-llm-heavy`'s `ConditionPathExists=/usr/share/mios/vllm/model/config.json` is satisfied on a fresh install with no manual step: fix `mios-ai-firstboot`'s weights fetch to run atomic + retried + verified (WS-DEPLOY producer pattern) now that the agent venv is fixed; pick the model from the stated tier resolution (`[ai.host_thresholds]` -> the 24 GB 4090's tier). (2) **Honor `[ai.host_thresholds]` + `lane_priority`** so the heavy lane enables + starts on a detected dGPU exactly as stated (extend the resolver in build-mios.ps1 + install pipeline + mios-hermes-firstboot only where it currently fails to apply the stated default; keep the mios.html knobs). (3) **Global routing per SSOT:** confirm `MIOS_AGENT_PIPE_BACKEND` / `[nodes.local-*]` / hermes route per the stated lanes; verify a plain-English round-trip is served on the GPU. (4) **Co-tenancy** per the stated `gpu_util`/`mem_fraction=0.45` so the heavy lane coexists with the light lane + Windows without OOM. Bring up BOTH the `[ai.vllm]` and `[ai.sglang]` lanes/components as the SSOT declares them (SGLang is a stated lane, not an option to drop).
**Where (files):** `usr/libexec/mios/mios-ai-firstboot` (weights fetch -> WS-DEPLOY retry/verify), `usr/share/mios/mios.toml` (respect `[lanes.*]`/`[ai.vllm]`/`[ai.sglang]`/`[ai.host_thresholds]`/`lane_priority` -- do not change the stated defaults, just deploy them), `usr/share/containers/systemd/mios-llm-heavy.container` (Condition gate), `build-mios.ps1` + `usr/libexec/mios/mios-hermes-firstboot` (apply the stated dGPU tier).
**When (deps/order):** After the agent venv fix (31a52fb1 -- done) since the weights fetch runs through it; aligns with WS-DEPLOY (model-provisioning is a readiness-gated producer).
**Done When:**
- [ ] on a detected dGPU, the heavy lane comes up per the STATED SSOT defaults after a fresh install; the model is auto-fetched (atomic+retried) so the Condition gate is satisfied with no manual step
- [ ] agents/nodes/hermes route per the stated `[lanes.*]` + `lane_priority`; a plain-English query is served on the GPU; light-lane + Windows co-tenancy stay OOM-free
- [ ] both the vLLM and SGLang lanes deploy as the SSOT declares them (no lane silently dropped)

# MiOS Agent Task List — Absorbed concept/workstream docs (2026-06)
<!-- Continues TASKS.md at T-200 (gap T-167..T-199 reserved for the plans-agent). Source: usr/share/doc/mios/concepts/*.md consolidation. -->
<!-- Carried forward: 42 not-yet-captured actionable items → T-200..T-241 across WS-FBM/OFFL/IGPU/RDSK/WSL/STD26/OAI/KACT/UISHELL/NAME2/UKI/A3F/OSCTL2. -->
<!-- Already-captured/shipped: the bulk of the June docs map to Parts 1-16 + T-001..T-166 or are shipped-state records (see consol-concepts-roadmap.md "Reference docs"). "DONE" = active + live-fired; trust engineering-blueprint over MEMORY.md. -->

---

## T-200: FBM-01 -- First-boot large-model provisioner (`mios-models-firstboot.service`)  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Provisioning/AI-lanes | **Who:** systemd/build agent | **Source:** firstboot-large-models-plan.md
**Instructions (WHAT + HOW):** Add a first-boot oneshot unit that reads a model set from SSOT and downloads GGUFs into `/var/lib/mios/llamacpp/models` with resume + checksum + progress, then writes a sentinel so it runs once. Gate on `After=network-online.target`, `ConditionPathExists=!<sentinel>`, and degrade-open (never block boot on a failed pull). Reuse the llama-swap model dir + `mios-llm-light` lane layout.
**Where (files):** new `usr/lib/systemd/system/mios-models-firstboot.service`; new `usr/libexec/mios/mios-models-firstboot` (fetch/resume/checksum script); `usr/lib/systemd/system-preset/`.
**When (deps/order):** Before heavy/light lane services can serve non-baked models; depends on T-201 (SSOT list) for its input.
**Done When:**
- [ ] Fresh boot with an empty model dir pulls the SSOT model set, verifies sha, writes the sentinel, and does not re-run on next boot.
- [ ] A network-down first boot degrades open (lane serves whatever is present; boot succeeds).
- [ ] Partial-download resume works (kill mid-pull, reboot, completes).

## T-201: FBM-02 -- `[ai.firstboot_models]` SSOT + `mios models {list,sync,add,rm}` CLI  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** SSOT/CLI | **Who:** config/CLI agent | **Source:** firstboot-large-models-plan.md
**Instructions (WHAT + HOW):** Add a `[ai.firstboot_models]` TOML table (per entry: name, GGUF/HF source URL, sha256, target lane) and flow it through `userenv.sh` + `install.env` + the configurator HTML. Add a `mios models` subcommand (`list`/`sync`/`add`/`rm`) that reads the table and drives the T-200 fetcher on demand.
**Where (files):** `usr/share/mios/mios.toml` (`[ai.firstboot_models]`); `usr/bin/mios`; `usr/libexec/mios/userenv.sh`; configurator HTML.
**When (deps/order):** Feeds T-200; do first or together.
**Done When:**
- [ ] `mios models list` shows the SSOT set; `mios models sync` pulls missing ones with checksum verify.
- [ ] `mios models add/rm` edits the runtime overlay and re-syncs.
- [ ] Drift-check confirms the table round-trips through userenv.sh + install.env.

## T-202: FBM-03 -- Heavy-lane bound-images first-boot pull (`mios-bound-images-firstboot`)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Provisioning/Containers | **Who:** systemd/build agent | **Source:** firstboot-large-models-plan.md
**Instructions (WHAT + HOW):** Pull the heavy-lane (SGLang/vLLM) container images at first boot instead of baking them into the OCI image, keyed off the same sentinel pattern. Optionally split-bake: keep small base images baked, pull only the large ones.
**Where (files):** new `usr/lib/systemd/system/mios-bound-images-firstboot.service` + libexec puller; `mios.toml` bound-images list.
**When (deps/order):** After T-200 pattern established.
**Done When:**
- [ ] First boot pulls the heavy-lane images once; heavy lanes start against them when enabled.
- [ ] Image build no longer bakes the large heavy-lane layers (image size drops).

## T-203: FBM-04 -- Portal model-provisioning status tile + air-gapped pre-seed cache  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** S | **Domain:** UI/Provisioning | **Who:** portal/UI agent | **Source:** firstboot-large-models-plan.md
**Instructions (WHAT + HOW):** Surface a "model provisioning" status tile in the Portal (progress/complete/failed) driven by the T-200 sentinel + progress file. Add a `mios models cache <dir>` pre-seed path so an operator can populate models from USB/local mirror before first boot for air-gapped installs.
**Where (files):** `usr/share/mios/quickshell/` (tile); `usr/bin/mios` (`models cache`).
**When (deps/order):** After T-200/T-201.
**Done When:**
- [ ] Tile reflects live provisioning state.
- [ ] `mios models cache` seeds the model dir so T-200 skips the download.

## T-204: OFFL-01 -- Vendor external repo definitions (terra.repo)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** S | **Domain:** Build/Offline | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** `automation/05-enable-external-repos.sh` currently fetches `terra.repo` from the network. Vendor it as `usr/share/mios/repos/terra.repo` and have the step copy the in-tree file instead of curling it (fall back to network only if a `--online` flag is set).
**Where (files):** `automation/05-enable-external-repos.sh`; new `usr/share/mios/repos/terra.repo`.
**When (deps/order):** Independent; part of the offline-build sweep.
**Done When:**
- [ ] A build with no egress reaches the repo-enable step without a network fetch.

## T-205: OFFL-02 -- Vendor desktop assets (Geist + Nerd fonts, Bibata cursor, flathub mirror)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Build/Offline | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** `automation/09-fonts.sh` and `10-gnome.sh` fetch Geist + Nerd-Fonts, the Bibata cursor, and add the flathub remote at build time. Vendor `usr/share/mios/vendored/fonts/{geist,nerd}.tar.xz` + `bibata-*.tar.xz`, and stand up a local flathub mirror (or bake the needed flatpaks as OCI archives — `40-flatpak-bake.sh` already does OCI bake for flatpaks) so no build-time remote is required.
**Where (files):** `automation/09-fonts.sh`, `automation/10-gnome.sh`; new `usr/share/mios/vendored/fonts/`, `usr/share/mios/vendored/cursors/`.
**When (deps/order):** Independent.
**Done When:**
- [ ] Offline build installs fonts + cursor from in-tree tarballs; flatpak install uses the local mirror/OCI archives.

## T-206: OFFL-03 -- Vendor k3s binary + k3s-selinux  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** S | **Domain:** Build/Offline | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** `automation/13-ceph-k3s.sh` fetches the k3s binary and `19-k3s-selinux.sh` clones k3s-selinux. Vendor `usr/share/mios/vendored/k3s/k3s-<tag>` and a k3s-selinux tarball; install from in-tree.
**Where (files):** `automation/13-ceph-k3s.sh`, `automation/19-k3s-selinux.sh`; new `usr/share/mios/vendored/k3s/`.
**When (deps/order):** Independent.
**Done When:**
- [ ] Offline build installs k3s + selinux policy without cloning/fetching.

## T-207: OFFL-04 -- Vendor hermes-agent source + pip wheels (`--no-index`)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Build/Offline | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** `automation/38-hermes-agent.sh` fetches the hermes-agent git tree + pip deps at build. Vendor the source snapshot + a wheelhouse under `usr/share/mios/vendored/wheels/`, and switch the install to `pip install --no-index --find-links <wheelhouse>`.
**Where (files):** `automation/38-hermes-agent.sh`; new `usr/share/mios/vendored/wheels/`, vendored hermes source.
**When (deps/order):** Independent.
**Done When:**
- [ ] Offline build builds the hermes venv with no PyPI/network access.

## T-208: OFFL-05 -- Vendor GGUF blobs + pre-pull llama-swap proxy image  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Build/Offline/AI-lanes | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** `automation/38-llamacpp-prep.sh` fetches GGUF blobs + the llama-swap proxy image at build. For a fully offline build, bundle the small/default GGUFs under `usr/share/mios/vendored/models/` and pre-pull the proxy image into the build cache. (Coordinate with WS-FBM: large models move to first-boot fetch; only the baseline default lands offline.)
**Where (files):** `automation/38-llamacpp-prep.sh`; new `usr/share/mios/vendored/models/`.
**When (deps/order):** Coordinate with T-200/T-201 (firstboot models own the large-model path).
**Done When:**
- [ ] Offline build produces a bootable image with the baseline model + proxy image present, no build-time model fetch.

## T-209: OFFL-06 -- Local rpm mirror image for fully-offline dnf  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** L | **Domain:** Build/Offline | **Who:** build agent | **Source:** OFFLINE-FIRST.md
**Instructions (WHAT + HOW):** dnf package installs still reach Fedora mirrors at build. Ship a local rpm mirror image (or a vendored repo snapshot) so a Scenario-2 USB build installs all packages from a local source. This is the largest offline gap; scope a reproducible mirror-snapshot step.
**Where (files):** `automation/` dnf-config step; a new mirror-build target.
**When (deps/order):** Last / heaviest of the WS-OFFL sweep.
**Done When:**
- [ ] A build with all egress blocked completes the package-install phase from the local mirror.

## T-210: IGPU-00 -- Wave-0 hardware verify probes (iGPU-WSL, heavy-lane 4GB, WSL rebaseline)  [P2] [VM]
> **Priority:** P2 | **Status:** planned | **Effort:** S | **Domain:** Verification/Compute | **Who:** operator/VM | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Run the three gating probes before building any Wave-2 compute: (1) iGPU-in-WSL matmul via AMD ROCDXG / Intel Level-Zero; (2) heavy lane in ~4 GB (`--gpu-memory-utilization 0.2` + KV-CPU-offload); (3) WSL `--version` ≥2.7.5 / kernel ≥6.18 rebaseline. Record results as the go/no-go for T-211/T-212.
**Where (files):** operator-loop probes; capture findings in `usr/share/doc/mios/concepts/`.
**When (deps/order):** Blocks T-211, T-212.
**Done When:**
- [ ] All three probe results recorded; go/no-go decision documented.

## T-211: IGPU-01 -- In-VM iGPU compute lane; retire native `mios-igpu-server.ps1`  [P2] [VM]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Compute/AI-lanes | **Who:** lanes agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Stand up an in-VM ROCm/Level-Zero iGPU inference lane and retire the native-Windows `mios-igpu-server.ps1` (:11436) + its Tailscale hop, so the iGPU lane runs inside the same VM as the other lanes. Register it as an `[agents.*]`/lane in SSOT.
**Where (files):** new lane launch script + quadlet; `mios.toml [agents.*]`; remove/deprecate `mios-igpu-server.ps1` path.
**When (deps/order):** Gated on T-210 probe #1 passing.
**Done When:**
- [ ] iGPU lane serves inference in-VM; the native Windows iGPU server + Tailscale hop are removed.

## T-212: IGPU-02 -- llama.cpp RPC fabric across lanes + coopmat2 verify  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Compute/AI-lanes | **Who:** lanes agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Run a per-lane llama.cpp `rpc-server` (phone/iGPU/dGPU/cluster) and have agent-pipe target one logical RPC endpoint so oversized models shard across lanes, mapped onto `[agents.*.nodes.*]` SSOT. Verify coopmat2 on the Vulkan lane.
**Where (files):** `mios.toml [nodes.*]`; lane launch scripts; agent-pipe endpoint routing.
**When (deps/order):** After T-210/T-211.
**Done When:**
- [ ] A model larger than a single lane's VRAM runs across the RPC fabric via one logical endpoint.
- [ ] coopmat2 confirmed on the Vulkan lane.

## T-213: RDSK-01 -- Selkies (WebRTC + NVENC) GPU remote-desktop lane  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** L | **Domain:** RemoteDesktop/GPU | **Who:** desktop agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Add a Selkies (WebRTC + NVENC) or Neko remote-desktop lane as a hardware-encoded upgrade over the KasmVNC/llvmpipe software-render path, delivered as a gated quadlet + `automation/` bake. Keep the existing VNC path as fallback.
**Where (files):** new `automation/` bake step; new `.container`/quadlet; `mios.toml` gate.
**When (deps/order):** Independent; GPU-host gated.
**Done When:**
- [ ] A GPU host streams the desktop via NVENC/WebRTC; falls back to VNC on non-GPU hosts.

## T-214: WSL-01 -- Dual-personality `rootfs-export → wsl --import` pipeline + MiOS update mechanism  [P2]
> **Priority:** P2 | **Status:** in-progress | **Effort:** L | **Domain:** Packaging/WSL | **Who:** build agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Build the pipeline that exports the same OCI image as a WSL-importable rootfs (`wsl --import`) and gives it a MiOS-owned update mechanism, since `bootc upgrade` is inoperable inside WSL (Finding D). Extend the existing WSL scaffolding (`usr/lib/wsl-distribution.conf`, `config/artifacts/wsl2.toml`).
**Where (files):** new `automation/` rootfs-export step; `Justfile` wsl2 target; `usr/lib/wsl-distribution.conf`.
**When (deps/order):** Independent; pairs with T-215/T-216.
**Done When:**
- [ ] `wsl --import` produces a working MiOS distro from the exported rootfs.
- [ ] The MiOS-owned updater upgrades an installed WSL distro without bootc.

## T-215: WSL-02 -- bootc offline atomic upgrades (skopeo→oci→bootc switch) + soft-reboot  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Lifecycle/Offline | **Who:** build agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Implement air-gapped atomic upgrades: `skopeo copy … oci:/usb` → `bootc switch --transport oci` → `bootc upgrade --apply`, split the kernel-vs-userspace delta, and use soft-reboot for non-kernel updates. `automation/43-uupd-installer.sh` covers part of the updater; extend it.
**Where (files):** `automation/43-uupd-installer.sh`; a new offline-upgrade path/doc.
**When (deps/order):** Independent.
**Done When:**
- [ ] An offline host upgrades from an OCI-on-USB image; non-kernel updates apply via soft-reboot.

## T-216: WSL-03 -- `.wslconfig` / image hygiene + WSL self-verify cosign  [P3]
> **Priority:** P3 | **Status:** in-progress | **Effort:** M | **Domain:** WSL/Supply-chain | **Who:** build agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Add the `.wslconfig`/image tuning not yet confirmed: `sparseVhd`, `autoMemoryReclaim`, and a `/mnt/shared_memory` tmpfs pre-mount hook; and add self-verify-on-pull (cosign) in the WSL update path + `UserNS=auto` on rootful quadlets (`42-cosign-policy.sh`/`90-generate-sbom.sh` already sign). 
**Where (files):** `config/artifacts/wsl2.toml`; `usr/lib/wsl-distribution.conf`; rootful `.container` templates; WSL updater.
**When (deps/order):** After T-214.
**Done When:**
- [ ] WSL distro applies sparseVhd + autoMemoryReclaim; shared_memory tmpfs mounts; update path verifies the image signature before applying.

## T-217: STD26-01 -- MCP `2026-07-28` wire adoption  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Standards/MCP | **Who:** federation agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Upgrade the MCP surface to the `2026-07-28` wire: stateless Streamable-HTTP transport, `Mcp-Method`/`Mcp-Name` headers, structured tool-OUTPUT JSON-Schema, elicitation (HITL primitive), sampling, MCP Apps, and a local MCP Registry + `.well-known` Server Cards. Keep the current stdio/consume surface as fallback.
**Where (files):** `usr/lib/mios/agent-pipe/mios_mcp.py`; `usr/share/mios/ai/v1/mcp.json`; `.well-known` server-card emitter.
**When (deps/order):** Independent; coordinate with T-221 (elicitation-based HITL) and WS-FED.
**Done When:**
- [ ] A `2026-07-28` MCP client connects over Streamable-HTTP, sees structured tool output + Server Cards, and can elicit.

## T-218: STD26-02 -- A2A v1.0.0 + signed AgentCard (JWS/JCS) + task-state mapping  [P2]
> **Priority:** P2 | **Status:** in-progress | **Effort:** L | **Domain:** Standards/A2A | **Who:** federation agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Upgrade the published AgentCard 0.3.0 → v1.0.0 (`a2a.proto`), add `AgentCardSignature` (JWS over JCS-canonical card, Ed25519 passport key), map swarm/DAG node status onto the standard A2A task states, and add `TaskStatusUpdateEvent` push webhooks. Builds on `mios_a2a_principal.py` (signed principals already present) and FED-G4.
**Where (files):** `usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py`; `server.py` `_build_agent_card`; `mios.toml [a2a.security]`.
**When (deps/order):** Extends FED-G4/T-012; pairs with T-219.
**Done When:**
- [ ] Published card validates as A2A v1.0 with a verifiable `AgentCardSignature`; DAG/swarm status surfaces as standard task states with push updates.

## T-219: STD26-03 -- AGNTCY OASF Agent Directory + DID Agent Identity  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Standards/Federation | **Who:** federation agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Replace the hand-maintained `mcp.json` / `a2a-peers.json` overlays with a local OASF-described, syncable Agent Directory + DID-based Agent Identity (highest-leverage federation move). Provide a `mios_agentreg.py`-style directory service that publishes/consumes OASF records and resolves DIDs.
**Where (files):** new directory service (`usr/lib/mios/agent-pipe/mios_agentreg.py`); overlays `ai/v1/mcp.json`, `a2a-peers.json`.
**When (deps/order):** Pairs with T-218; supersedes FED-G3 overlay reload for the directory case.
**Done When:**
- [ ] Peers register via OASF records with DID identity; the directory syncs and agent-pipe routes from it instead of the static overlays.

## T-220: STD26-04 -- Durable event-sourcing over swarm/DAG + Memory-Block abstraction  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** L | **Domain:** Durability/Memory | **Who:** orchestration agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Add a Temporal-style local event history over swarm/DAG execution for crash-resume, and an explicit Memory-Block abstraction over raw pgvector rows; formalize `_admit` against the "Agent Control Protocol" (static risk + stateful trace + ledger). Sleep-time consolidation half is already MEM-05/T-056; this is the durability + Memory-Block delta.
**Where (files):** `server.py` DAG executor; `usr/lib/mios/agent-pipe/mios_memory.py`.
**When (deps/order):** After the Kernel Stage-2 rewire (A6/T-025) stabilizes the DAG path.
**Done When:**
- [ ] A crashed DAG run resumes from the event history; recall/writes go through Memory-Block, not raw rows.

## T-221: STD26-05 -- Standards-based HITL (MCP elicitation SEP-2322 + A2A INPUT/AUTH_REQUIRED)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Standards/HITL | **Who:** federation agent | **Source:** upstream-gap-plan-2026-06.md
**Instructions (WHAT + HOW):** Re-express the bespoke `mios_hitl.py` / `mios_hitlflow.py` / `mios_arbiter.py` gate on open standards: MCP elicitation (SEP-2322) + A2A `INPUT_REQUIRED`/`AUTH_REQUIRED` task states, so external clients drive HITL over the wire. Keep the bespoke queue as the internal backend.
**Where (files):** `usr/lib/mios/agent-pipe/mios_hitl.py`, `mios_hitlflow.py`; MCP/A2A surfaces.
**When (deps/order):** After T-217 (elicitation) + T-218 (task states).
**Done When:**
- [ ] A standards client triggers + satisfies a HITL prompt via elicitation / INPUT_REQUIRED, routed through the existing queue.

## T-222: OAI-01 -- Unified multi-kind capability catalog (recipes + skills as tagged rows)  [P2]
> **Priority:** P2 | **Status:** in-progress | **Effort:** M | **Domain:** Routing/Catalog | **Who:** agent-pipe agent | **Source:** agent-pipe-openai-standards-master-plan.md
**Instructions (WHAT + HOW):** Fold recipes (as function-tools) and skills (description-only rows) into the `[routing]` capability catalog, tagged `kind` + `domain`, with composition rules (recipes→tools OK, recipes→skills FORBIDDEN). Today `mios.toml [routing]` is `kind=tool`-only (see the line-3097 comment). Extend the classifier/catalog to score across kinds.
**Where (files):** `usr/share/mios/mios.toml [routing]`; `mios_capreg.py`, `mios_manifest.py`, `mios_verbcatalog.py`, `mios_classify.py`.
**When (deps/order):** Extends the shipped 2-stage router; overlaps ORCH code-mode (T-061).
**Done When:**
- [ ] Recipes + skills appear as catalog rows with `kind`/`domain`; the router routes to them; composition rules enforced.

## T-223: OAI-02 -- Tier-1 `usage` detail fields + strict function schemas + cache-friendly ordering  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** OpenAI-conformance | **Who:** agent-pipe agent | **Source:** agent-pipe-openai-standards-master-plan.md
**Instructions (WHAT + HOW):** Emit `usage.completion_tokens_details.reasoning_tokens` + `usage.prompt_tokens_details.cached_tokens` (currently absent), add strict-mode function schemas (`strict:true`, `additionalProperties:false`) to the tool surface, and order prompts static-first for prompt-cache friendliness. Spot-verify streaming `[DONE]`/tool-delta contract + `developer` role acceptance while here.
**Where (files):** `server.py` usage assembler + streaming path; `mios_worker_tools.py` / tool-surface builder.
**When (deps/order):** Independent; caps off the Tier-0/1 conformance work already shipped.
**Done When:**
- [ ] Responses carry reasoning/cached token details; function schemas are strict; a live run confirms the streaming + role contracts.

## T-224: OAI-03 -- Persistent PTY/tmux stateful shell + PowerShell object-pipeline flattening  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** OS-control/ACI | **Who:** os-control agent | **Source:** aios-implementation-plan.md
**Instructions (WHAT + HOW):** Add a PTY/tmux-wrapped persistent shell so cwd/env survive across turns (the ACI output-normalizer `mios_aci.py` shipped; the persistent-shell substrate did not). Add PowerShell .NET-object-pipeline → flat-text normalization in the Windows executor. Substrate belongs with the coderun sandbox / broker shell, not inline in agent-pipe.
**Where (files):** new `usr/libexec/mios/` persistent-shell broker; `usr/share/mios/windows/mios-oscontrol-server.ps1` (pipeline flattening).
**When (deps/order):** Pairs with coderun broker (F3/T-072).
**Done When:**
- [ ] Two sequential shell turns share cwd/env via the persistent PTY; PowerShell output arrives as flat text.

## T-225: OAI-04 -- Run-template REPLAY-REUSE (intent-keyed zero-token DAG replay)  [P2]
> **Priority:** P2 | **Status:** in-progress | **Effort:** M | **Domain:** Orchestration/Determinism | **Who:** agent-pipe agent | **Source:** aios-implementation-plan.md
**Instructions (WHAT + HOW):** The run-template capture side + `GET /v1/run-templates` shipped (`[run_template].enable=true`); build the reuse side: match a new turn to a stored DAG plan keyed by intent-class and skip planning (zero-token deterministic replay), with a confidence gate + fallback to full planning.
**Where (files):** `server.py` run-template matcher; `mios.toml [run_template]`.
**When (deps/order):** Extends the shipped capture path.
**Done When:**
- [ ] A repeat intent replays the stored DAG without a planning LLM call; low-confidence match falls back to planning.

## T-226: KACT-01 -- Wire batch-coalescing chokepoint (`mios_batch`)  [P3]
> **Priority:** P3 | **Status:** in-progress (built-gated) | **Effort:** S | **Domain:** Scheduling | **Who:** agent-pipe agent | **Source:** aios-engineering-blueprint.md
**Instructions (WHAT + HOW):** `mios_batch.py` (imported at server.py:158) holds the window/hold-flush logic but the server-side hold/flush chokepoint by `(endpoint, model)` is not wired. Wire it behind a flag. Low priority — native vLLM/SGLang already continuous-batch — so keep default OFF.
**Where (files):** `server.py` dispatch chokepoint; `mios_batch.py`; `mios.toml`.
**When (deps/order):** Independent.
**Done When:**
- [ ] With the flag on, concurrent same-`(endpoint,model)` requests coalesce through the hold/flush window; default-off is a no-op.

## T-227: KACT-02 -- Remote SmartRouting + quality-gate + daily budget (`mios_smartroute`)  [P2]
> **Priority:** P2 | **Status:** in-progress (built-gated) | **Effort:** M | **Domain:** Routing/Cost | **Who:** agent-pipe agent | **Source:** aios-engineering-blueprint.md
**Instructions (WHAT + HOW):** `mios_smartroute.py` (server.py:159) decides local-first → paid-remote escalation on a quality-gate fail within a per-day budget, but is DISABLED by default and the remote-lane adapters are stubbed (comment at server.py:2924). Implement the remote adapters, wire the quality-gate orchestration, and key the budget via `mios_quota`.
**Where (files):** `mios_smartroute.py`, `mios_quota.py`, `server.py`.
**When (deps/order):** Pairs with T-228 (quota keying); needs remote keys.
**Done When:**
- [ ] A quality-gate failure escalates to a remote lane within budget; budget exhaustion falls back to local; default-off preserved.

## T-228: KACT-03 -- Per-user quota keying + persistence on verified principal  [P3]
> **Priority:** P3 | **Status:** in-progress (built-gated) | **Effort:** S | **Domain:** Cost/Identity | **Who:** agent-pipe agent | **Source:** aios-engineering-blueprint.md
**Instructions (WHAT + HOW):** `mios_quota.py` exists but is keyed globally and not persisted. Key it on the verified principal (from the inbound-auth/principal path) and persist counters (pgvector) so quota survives restart.
**Where (files):** `mios_quota.py`, `server.py`; `postgres/schema-init.sql` (quota table).
**When (deps/order):** After FED-G1/T-001 principal extraction; pairs with T-227.
**Done When:**
- [ ] Quota accrues per verified principal and survives a restart.

## T-229: KACT-04 -- Gossip/DHT federated discovery transport (`mios_gossip`)  [P3]
> **Priority:** P3 | **Status:** in-progress (built-gated) | **Effort:** M | **Domain:** Federation/Discovery | **Who:** federation agent | **Source:** aios-engineering-blueprint.md
**Instructions (WHAT + HOW):** `mios_gossip.py` exists but has no discovery transport over `mios_reputation`. Wire a gossip/DHT transport so peers propagate membership + reputation without a central registry. Distinct from FED-G5 mDNS (LAN-local); this is the WAN/mesh discovery path.
**Where (files):** `mios_gossip.py`, `mios_reputation.py`; `server.py`.
**When (deps/order):** After WS-FED inbound auth; complements FED-G5/T-013.
**Done When:**
- [ ] Two nodes discover each other + exchange reputation via gossip with no central registry.

## T-230: KACT-05 -- Per-verb risk-tier bwrap/seccomp ENFORCEMENT exec (`mios_sandbox`)  [P2]
> **Priority:** P2 | **Status:** in-progress (security-critical) | **Effort:** M | **Domain:** Security/Sandbox | **Who:** security agent | **Source:** aios-engineering-blueprint.md
**Instructions (WHAT + HOW):** `mios_sandbox.py` decides the risk tier and builds the bwrap argv (`build_bwrap_argv`), but the wrapper is never `exec`'d, seccomp is not applied, and the per-turn workspace mkdir from dispatch is missing — so the sandbox is advisory only. Actually exec the bwrap wrapper for WRITE/exec-class verbs, apply the seccomp profile, and create the per-turn workspace. Overlaps SEC-01 (MCP-microVM) but this is the per-verb bwrap/seccomp path.
**Where (files):** `mios_sandbox.py`; `server.py` dispatch path.
**When (deps/order):** Coordinate with SEC-01/T-032 (don't double-sandbox MCP tools).
**Done When:**
- [ ] A high-risk verb runs inside the exec'd bwrap+seccomp jail with a per-turn workspace; escape attempts are confined.

## T-231: KACT-06 -- `Notify=healthy` + `HealthCmd` + rollback across AI quadlets  [P2]
> **Priority:** P2 | **Status:** planned/unverified | **Effort:** M | **Domain:** Lifecycle/Health | **Who:** systemd/build agent | **Source:** upstream-gap-plan-2026-06.md (T1.4)
**Instructions (WHAT + HOW):** Add real systemd readiness gating (`Notify=healthy` + `HealthCmd`) and rollback-on-failed-health to the AI quadlets (agent-pipe, llm lanes, OWUI), so a lane that fails its health check gates dependents / triggers rollback rather than being reported up. Complements greenboot (Part 1).
**Where (files):** `usr/lib/mios/*.container` quadlet templates; `automation/15-render-quadlets.sh` (or the render step in use).
**When (deps/order):** Independent; complements T-002 greenboot.
**Done When:**
- [ ] Each AI quadlet declares `Notify=healthy` + `HealthCmd`; a forced health failure gates dependents and surfaces the rollback path.

## T-232: UISHELL-01 -- Native QML Services/Swarm views (replace web-Portal fallback)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** UI/QML | **Who:** portal/UI agent | **Source:** mios-app-browser-portal-dashboard-design-2026-07-03.md
**Instructions (WHAT + HOW):** Replace the "open web Portal" fallback with native QML list views bound to the already-shipped `PortalData` properties (Phase-2 data path exists). Decide Terminals: launch the real terminal emulator vs. embed xterm.js.
**Where (files):** `usr/share/mios/quickshell/` (new Services/Swarm views, `Sidebar.qml`).
**When (deps/order):** After Phase-2 (shipped).
**Done When:**
- [ ] Native Services + Swarm views render from `PortalData`; Terminals decision implemented.

## T-233: UISHELL-02 -- Login-prompt QML popup (`PortalData.login()`)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** S | **Domain:** UI/QML | **Who:** portal/UI agent | **Source:** mios-app-browser-portal-dashboard-design-2026-07-03.md
**Instructions (WHAT + HOW):** Add a small QML text-field + button popup so an operator can call `PortalData.login()` without editing QML (deliberately deferred in Phase 2).
**Where (files):** `usr/share/mios/quickshell/` (login popup component).
**When (deps/order):** Independent.
**Done When:**
- [ ] Operator logs in from the popup; no QML edit required.

## T-234: UISHELL-03 -- Reconcile `mios-webshell` AI-sidebar endpoint (`:3030` vs agent-pipe)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** S | **Domain:** UI/Config | **Who:** portal/UI agent | **Source:** mios-app-browser-portal-dashboard-design-2026-07-03.md
**Instructions (WHAT + HOW):** The Surfer patch points the AI sidebar at `:3030` (OWUI) while the Windows Zen path uses agent-pipe. Pick one canonical endpoint (SSOT-driven) and reconcile before the next Surfer rebuild so the baked default is correct.
**Where (files):** `automation/56-bake-surfer.sh`; SSOT endpoint key.
**When (deps/order):** Before the next Surfer rebuild.
**Done When:**
- [ ] Both paths resolve the AI-sidebar endpoint from one SSOT key; Surfer rebuild bakes the correct default.

## T-235: UISHELL-04 -- Cockpit native-vs-web decision  [P3]
> **Priority:** P3 | **Status:** planned (decision) | **Effort:** S | **Domain:** UI/Architecture | **Who:** architect | **Source:** mios-app-browser-portal-dashboard-design-2026-07-03.md
**Instructions (WHAT + HOW):** Resolve the open Phase-4 trade-off for Cockpit: keep the web-hosted tile, reimplement views in QML, or use a Wayland-native web renderer. Record the decision + rationale; only then schedule follow-up work.
**Where (files):** design doc / ROADMAP note; `usr/share/mios/quickshell/` if native chosen.
**When (deps/order):** After T-232 (informs the native-shell scope).
**Done When:**
- [ ] A documented Cockpit posture decision with rationale.

## T-236: NAME2-01 -- Agent-plane user SSOT reconciliation (820/822 → 850)  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** SSOT/Identity | **Who:** naming agent | **Source:** naming-refactor-plan.md
**Instructions (WHAT + HOW):** `mios.toml` still declares `[services.hermes]` uid 820 (line ~7846) and `[services.agent_pipe]` uid 822 (line ~7868), but the live agent plane runs as `mios-ai`/850 — an SSOT lie. Either repoint the SSOT to 850 or retire the inert users, updating units + firstboot chown + tmpfiles + sudoers consistently.
**Where (files):** `usr/share/mios/mios.toml`; agent-pipe/hermes units; firstboot chown; `tmpfiles.d`; sudoers.
**When (deps/order):** Under NAME-01/T-165's umbrella; do before further user-name churn.
**Done When:**
- [ ] SSOT + all consumers agree on the live agent-plane uid (850); no references to inert 820/822 remain.

## T-237: NAME2-02 -- Rename `mios-daemon-agent` agent-id → `daemon-agent`  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Naming | **Who:** naming agent | **Source:** naming-refactor-plan.md
**Instructions (WHAT + HOW):** Drop the redundant `mios-` prefix on the `mios-daemon-agent` agent-id per the agent-id convention (~105 refs across ~36 files still carry the old form in registries/env). Keep external contracts frozen; migrate registries + env atomically.
**Where (files):** agent registries, `mios.toml [agents.*]`, env maps, ~36 files carrying `mios-daemon-agent`.
**When (deps/order):** After T-236; low-risk once user SSOT is clean.
**Done When:**
- [ ] All `mios-daemon-agent` refs become `daemon-agent`; drift-check + a live fan-out still resolve the agent.

## T-238: NAME2-03 -- Mutable-state casing pass + `ContainerName=` audit  [P3]
> **Priority:** P3 | **Status:** planned (partial) | **Effort:** M | **Domain:** Naming/Hygiene | **Who:** naming agent | **Source:** naming-refactor-plan.md
**Instructions (WHAT + HOW):** Run the residual mutable-module-state casing pass (semaphores/caches/registries → `_lower_snake`) that the naming refactor left as a dedicated pass, and audit `ContainerName=` on renamed units for consistency. server.py Phase-1b renames already landed.
**Where (files):** `usr/lib/mios/agent-pipe/server.py` + `mios_*.py` module state; renamed `.container` units.
**When (deps/order):** After T-236/T-237.
**Done When:**
- [ ] Mutable module state is uniformly `_lower_snake`; `ContainerName=` matches unit names; drift-check green.

## T-239: UKI-01 -- verity-rooted UKI build + fapolicyd enforce-promotion  [P3] [VM]
> **Priority:** P3 | **Status:** in-progress (intentionally-deferred) | **Effort:** L | **Domain:** Security/Boot | **Who:** security/build agent | **Source:** ws7-uki-fapolicyd.md + multi-agent-buildout-plan.md
**Instructions (WHAT + HOW):** Promote the scaffolded verity-rooted UKI build (`ukify` measuring the composefs fs-verity digest → `mios-verity.efi`, `kargs.d`) and the fapolicyd PERMISSIVE→enforce path to shippable by fixing the 4 named defects: inverted agent-codegen carve-out rule, false `permissive` karg claim, rootflags merge collision, and carve-out review. Enforce or a mis-signed UKI bricks boot — keep behind an explicit operator gate + VM verify.
**Where (files):** `automation/lib/ws7-uki-fapolicyd-build.sh`; `mios.toml [security.fapolicyd_observe]` / `[uki]`; `[packages.uki]`.
**When (deps/order):** Extends WS-H/H7 (fapolicyd allow-list baking); VM-gated.
**Done When:**
- [ ] The 4 defects are fixed; a VM boots a verity-rooted signed UKI with fapolicyd in enforce, agent codegen still permitted; observe-mode remains the default.

## T-240: A3F-01 -- Central-path legacy-datastore→pg primary flip + un-mirrored write fixes  [P2] [VM]
> **Priority:** P2 | **Status:** in-progress | **Effort:** M | **Domain:** Data/Migration | **Who:** data agent | **Source:** ws-a3-central-path-cutover-worklist.md
**Instructions (WHAT + HOW):** Complete the deferred CENTRAL path (server.py + OWUI pipe) pg-primary flip: fix the un-mirrored write sites (`execute_skill last_used_at`, `_skill_invocation_close`, `hitl_approve` audit UPDATE, and the 4 OWUI-pipe writes in `mios_agent_pipe.py` ~L1394/1620/1910/2310), and make the `_skill_attribute_tool_call` RELATE-edge schema decision (add a `tool_call_emissions` table vs. an `emitted_by_invocation` column). Flip `[pgvector].db_backend` dual→postgres / the `_PG_PRIMARY` gate under VM verify.
**Where (files):** `usr/lib/mios/agent-pipe/server.py`; `usr/share/mios/owui/pipes/mios_agent_pipe.py`; `postgres/schema-init.sql`; `mios.toml [pgvector]`.
**When (deps/order):** CLI/daemon cutover already DONE; operator VM-session gated.
**Done When:**
- [ ] Central path writes go to pg with no un-mirrored sites; the RELATE-edge schema decision is applied; a live recall/skill round-trip passes with `db_backend=postgres`.

## T-241: OSCTL2-01 -- hwnd-threaded target-window resolution for `pc_type`  [P2] [VM]
> **Priority:** P2 | **Status:** in-progress | **Effort:** M | **Domain:** OS-control/Windows | **Who:** os-control agent | **Source:** oscontrol-envgrounding-gaps-2026-06-20.md
**Instructions (WHAT + HOW):** Plumb an explicit target window handle through the type path: `Resolve-EditElement(FromHandle)` → `/input/type`, route compound focus through the WINDOWS executor, and pass the hwnd to `pc_type` so typing targets a specific resolved window instead of whatever UIA thinks is focused. The UIA `SetValue` write-branch (`Invoke-UIASetValue`/`Invoke-TypeText`) already shipped; `Invoke-TypeText($text)` currently takes no target hwnd. First verify whether CU-01/T-038 already covers this; if so, close as dup.
**Where (files):** `usr/share/mios/windows/mios-oscontrol-server.ps1`; `server.py` `pc_type` dispatch.
**When (deps/order):** Extends CU-01/T-038; operator-live-test-gated.
**Done When:**
- [ ] A type into a named/handle-resolved background window lands in that window (not the focused one); read-back verification passes.


## T-242: VECTOR-00 -- V0 Foundation: unified DB + provenance + DB->TOML materialize + drift-gate  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** AI-plane/SSOT/DB | **Who:** DB/build agent | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Land the unified pgvector DB in /var with emb/emb_model/emb_version provenance columns; add the INVERSE DB->TOML materialize step (today only TOML->DB seeds); make the verb round-trip LOSSLESS (section/examples/model_name/hidden/aliases/conflict_group/parallel_limit/max_result_chars all survive TOML<->DB); add drift-gate 29 (drift_projection) that regenerates TOML from DB and diffs (theme check-25 pattern, now across the build boundary). No behavior change yet.
**Where (files):** usr/share/mios/postgres/schema-init.sql, usr/libexec/mios/seed-db-config.py (+ a new DB->TOML materialize peer), automation/38-drift-checks.sh (check 29)
**When (deps/order):** First -- foundation for V1-V5; depends on nothing beyond the running mios-pgvector.
**Done When:**
- [ ] the V2 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass

## T-243: VECTOR-01 -- V1 Config read-path: DB becomes the runtime read (TOML fail-open)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** AI-plane/SSOT/DB | **Who:** agent-pipe backend engineer | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Add a config resolver PEER of mios_toml.py that READS config_kv/verb/domain_verb/recipe/routing_phrase from the DB at runtime (overlay-first: vendor<host<user<machine via config_layer), with the existing TOML path as fail-open fallback; wire verbcatalog.py + the config consumers to it; kill the write-only system_config dead-drift. Per-surface authority flip only when read-path + lossless round-trip + drift-gate are green.
**Where (files):** usr/lib/mios/mios_toml.py (+ new db resolver), usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py, usr/libexec/mios/seed-db-config.py
**When (deps/order):** After T-242 (lossless round-trip + materialize). Honors WS-NAME aliases + load-bearing legacy verbs (fold-refactor, never blind-drop).
**Done When:**
- [ ] the V3 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass

## T-244: VECTOR-02 -- V2 AI-plane vectors: embed skill/verb/tool_call/event/session/directory  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** AI-plane/Vectorization | **Who:** agent-pipe backend engineer | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Add emb vector(768) + HNSW(vector_cosine_ops) to skill, verb, tool_call, event, session, directory_entry over a text projection (emb_model/emb_version stamped, off-hot-path backfill like embed_backfill.py); retire the in-process verb-embeddings/apps-embeddings BM25/cosine caches for native <=> queries. Ground-truth stays in typed columns.
**Where (files):** usr/share/mios/postgres/schema-init.sql, usr/lib/mios/agent-pipe/mios_pipe/routing/worker_tools.py, mios_pipe/memory/embed_backfill.py, mios-skills
**When (deps/order):** After V1 (or parallel -- vectors are additive). No functionality loss (adds recall, keeps text-match).
**Done When:**
- [ ] the V4 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass

## T-245: VECTOR-03 -- V3 Build catalog: package/build/xbox/debloat tables + DB->/ctx materialize  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Build/Install/Xbox/DB | **Who:** build/DISM agent | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Move the build + MiOS-Xbox catalog into DB tables: package_set (the [packages.*] SSOT), build_recipe/build_phase (OCI+Xbox recipes; build_phase = the WS-DEPLOY DAG as rows with stage∈{container,runtime,firstboot}+deps), xbox_feature, debloat_policy/profile, feature_set, {appx,feature,capability,component}_removal, preset -- each with emb. Solve the clean-container chicken-and-egg with a DB->/ctx materialize at build entry; unify build-time vs runtime identity onto the account table.
**Where (files):** usr/share/mios/postgres/schema-init.sql, automation/lib/packages.sh, automation/build.sh + NN-*.sh, C:\mios-bootstrap\srcutounattend\* (New-MiOSISO.ps1, mios-debloat.json, mios-xbox-features.txt, presets)
**When (deps/order):** After V0/V1 (materialize + read-path). Offline-safe: /ctx materialize keeps the clean-container build hermetic.
**Done When:**
- [ ] the V5 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass

## T-246: VECTOR-04 -- V4 Accounts/users: DB-owned ids + prefs + bidirectional write-back  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** Accounts/Identity/DB | **Who:** identity/accounts agent | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Complete the account plane: account.home_dir/shell, a uid_alloc SEQUENCE + allocate_uid()/allocate_gid() so ids are DB-owned, account_preference (layer-scoped, emb) so per-user dotfiles RENDER from the DB (retire static etc/skel); bidirectional write-back -- Linux pam/getent (NSS from account already), Windows SAM watcher (extend MiOS-AccountSync.ps1). Reconcile the /etc/shadow parallel store via pam write-back so the two credential planes don't drift.
**Where (files):** usr/share/mios/postgres/schema-init.sql, automation/17-accounts-db.sh, usr/libexec/mios/mios-ai-firstboot (account seeder), C:\mios-bootstrap\srcutounattend\MiOS-AccountSync.ps1, etc/skel
**When (deps/order):** After V0/V1. Builds on the shipped WS-ACCT account table + NSS getpwnam.
**Done When:**
- [ ] the V6 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass

## T-247: VECTOR-05 -- V5 Invert authority: DB=SSOT, TOML=generated export, event-sourced  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** XL | **Domain:** SSOT/DB/Configurator | **Who:** platform architect | **Source:** WS-VECTOR ultracode survey 2026-07-10; usr/share/doc/mios/reference/everything-db-driven.md
**Instructions (WHAT + HOW):** Flip authority: the DB is the SSOT and mios.toml becomes a generated EXPORT (materialized for the next image build). The configurator (mios.html) CRUDs the DB (emitting config_event); install/build/config/account mutations become append-only event-sourced with time-travel + rollback, aligned to bootc atomic-upgrade. Flip per-surface only after V1-V4 read-paths + drift-gates are all green.
**Where (files):** usr/share/mios/configurator/mios.html, usr/share/mios/postgres/schema-init.sql (config_event + event-sourcing), automation/38-drift-checks.sh, the DB->TOML materialize
**When (deps/order):** LAST -- after V0-V4 are green per-surface. The terminal state of WS-VECTOR.
**Done When:**
- [ ] the V7 surface is DB-driven per the WS-VECTOR law (DB read at runtime, TOML fail-open) with no functionality loss
- [ ] emb/HNSW recall works where the phase adds vectors; drift-gate (regenerate+diff) green; `just drift-gate` + `test_mios_*` pass


## T-248: BAKE-01 -- Two-gate `[build.bake]` core allow-list + projected bake-plan + `.image` whales  [P1]
> **Priority:** P1 | **Status:** completed | **Effort:** L | **Domain:** Build/Bake | **Who:** build agent | **Source:** WS-BAKEGATE / Part 21; core bake-gate + universal-core study; `Containerfile`/`mios-bake-group` shipped this session
**Instructions (WHAT + HOW):** Phase 0 is DONE -- the monolithic bound-images `RUN` (exit-125 on disk-constrained runners) was sharded heavy-first into `usr/libexec/mios/mios-bake-group` (new) + `mios.toml [build].bake_groups` (L8470-8475) + five per-group `RUN`s in `Containerfile` (L181-190, `--mount=type=cache`, never `--squash`). Remaining structural work: add a `[build.bake]` SSOT section (a `core` allow-list = fixed SSOT-independent membership; `groups`/`group_members.*`); add `tools/generate-bake-plan.py` invoked by new `automation/16-bake-plan.sh` (after `15-render-quadlets.sh`) that reads through `usr/lib/mios/mios_toml.py` and emits CORE members UNCONDITIONALLY (the one branch where "core overrides SSOT" lives) + à-la-carte members iff enable-true into `/usr/lib/mios/bake/plan.d/NN-<group>.list`; add `.image` Quadlets for the whales (`mios-llm-heavy.image` + `mios-llm-heavy-alt.image`) symlinked by `08-system-files-overlay.sh` (~L178); add a regenerate-and-diff drift-check asserting both whales in `core`, all fully-qualified, referenced ⊆ emitted. Deletes the Containerfile's inline Quadlet scraping (Law 7/8).
**Where (files):** `usr/share/mios/mios.toml` (`[build.bake]`), `tools/generate-bake-plan.py` (new), `automation/16-bake-plan.sh` (new), `automation/08-system-files-overlay.sh`, `automation/38-drift-checks.sh`, `usr/share/containers/systemd/mios-llm-heavy.image` + `mios-llm-heavy-alt.image` (new), `usr/libexec/mios/mios-bake-group`, `Containerfile`
**When (deps/order):** Phase 0 done; structural next. Interlocks with T-250 (bake groups collapse toward sys/cuda) + T-251 (digest-free SSOT).
**Done When:**
- [x] `just drift-gate` regenerates `plan.d/*.list` and diffs clean; the check FAILS if a whale leaves `core`, a core member is not fully-qualified, or referenced ⊄ emitted; the Containerfile carries no inline Quadlet `sed`-scraping.

## T-249: BLADE-01 -- Universal-core + blade-type activation gate (one image, role by flag)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Build/Activation | **Who:** build/systemd agent | **Source:** WS-BLADE / Part 21; universal-core / blade-type study (§3)
**Instructions (WHAT + HOW):** Add `[blade]` SSOT (`type` archetype: hybrid/compute/endpoint/controller/headless; `[blade.archetypes]` capability expansions; `[blade.requires]` service→capability "nodeSelector" map). Demote `usr/libexec/mios/role-apply` from imperative actor to a marker-writing resolver (materialize `/etc/mios/blade.d/<cap>` + `/run/mios/blade.env`; keep autodetect). Generate one `usr/share/mios/dropins/blade-<cap>.conf` (`ConditionPathExists=/etc/mios/blade.d/<cap>`) per capability from `[blade.requires]` (Law-8 generator + drift-check) and wire `automation/41-mios-dropin-fanout.sh`. Deploy-time selection: karg `mios.blade=<type>` (generated `kargs.d/05-mios-blade.toml`) / Ignition / Afterburn / autodetect; `mios blade set|add-capability|status` verb (marker touch + daemon-reload, no reboot). Fold `[profile].role/features` into `[blade]`; add `mios-{compute,endpoint,controller}.target`; greenboot check. Keep `[blades.*]`/`[nodes.*]` as the orthogonal fleet-dispatch Axis B. No image variants -- baked everywhere, started by role.
**Where (files):** `usr/share/mios/mios.toml` (`[blade]`), `usr/libexec/mios/role-apply`, `usr/share/mios/dropins/blade-<cap>.conf`, `automation/41-mios-dropin-fanout.sh`, `usr/lib/bootc/kargs.d/05-mios-blade.toml`, `usr/lib/systemd/system/mios-{compute,endpoint,controller}.target`, `usr/lib/greenboot/check/required.d/10-mios-role.sh`, `mios blade` verb
**When (deps/order):** Complements T-248 (bake vs activation orthogonality) + T-250 (activation `Condition*` unchanged by consolidation).
**Done When:**
- [ ] one universal image: on a `controller` blade `mios-llm-heavy.service` is condition-skipped (zero VRAM), on a `gpu-serving` blade it starts; `mios blade add-capability gpu-serving` lights it hot with no reboot; the drop-in generator is drift-gated.

## T-250: MIOSSYS-01 -- mios-sys + mios-cuda shared-base consolidation of the sidecar fleet  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** XL | **Domain:** Build/Consolidation | **Who:** build agent | **Source:** WS-MIOSSYS / Part 21; MiOS-Sys consolidation study; [[mios-release-topology]]
**Instructions (WHAT + HOW):** Replace the ~18-image sidecar fleet (~60GB, zero shared base blobs) with TWO images of one base lineage, both `FROM ${BASE_IMAGE}` (ucore-hci:stable-nvidia): `localhost/mios-sys` (CUDA-free, ~6-8GB) + `localhost/mios-cuda` (shared CUDA/torch/flashinfer L2 + `vllm-venv`/`sglang-venv` + `llama-server`, ~15-18GB). Use Model A (one IMAGE, many CONTAINERS -- shared `Image=`, per-service `Exec=`, per-unit `User=`/`Group=`/`Condition*` unchanged). New `automation/57-mios-sys-build.sh` (+ generated `usr/share/mios/{sys,cuda}/Containerfile`); `[image.sys]`/`[image.cuda]` blocks; `MIOS_SYS_IMAGE`/`MIOS_CUDA_IMAGE` through `userenv.sh` + BOTH allowlists in `automation/15-render-quadlets.sh` (envsubst L73 + bash-fallback ~L87-127) + `38-ssot-lint.sh`. Per-member Quadlet delta is a pure SSOT edit (repoint `Image=`, add `Exec=`); `[build].bake_groups` → sys/cuda/extra. Migrate in Waves 0-3 (Wave 1 Go-binary tier; Wave 2 interpreted + k3s/runner binaries; Wave 3 mios-cuda + DB tier behind a smoke test). Ceph = KEEP-SEPARATE.
**Where (files):** `usr/share/mios/mios.toml` (`[image.sys]`/`[image.cuda]`/`[build].bake_groups`), `automation/57-mios-sys-build.sh` (new), `usr/share/mios/{sys,cuda}/Containerfile` (generated), `automation/15-render-quadlets.sh`, `automation/38-ssot-lint.sh`, `automation/14-generate-quadlets.sh`, `usr/libexec/mios/mios-bake-group`, `Containerfile`, the ~18 `usr/share/containers/systemd/*.container` members
**When (deps/order):** Locked ops decisions: newest-packages tagged-at-build; ALL core consolidates; k3s binary consolidated (HA-compatible, privileged activation unchanged) + Pacemaker/corosync HA CORE; on-CVE/on-release rebuild; mios-cuda bake-scope deferred to Wave 3. Enabler of T-252 GitHub-equality; complements T-248 Phase 0 (sharding kept as safety margin).
**Done When:**
- [ ] the bound-image store drops to ~25GB with the largest single commit capped at the ~12GB CUDA/torch group; `generate-pod-quadlets.py --check` validates the regenerated `Image=`/`Exec=`; every `User=`/root-exception byte-identical (Law 6 untouched); a WSL blade still won't start pxe-hub though its binary is baked.

## T-251: SBOM-01 -- Extend build-time provenance beyond images (model/package hashes)  [P2]
> **Priority:** P2 | **Status:** in-progress (image digests DONE this session; model/package hashes remaining) | **Effort:** M | **Domain:** SBOM/Provenance | **Who:** build agent | **Source:** WS-SBOM / Part 21; [[mios-sbom-not-hardcode]]
**Instructions (WHAT + HOW):** DONE for images -- ALL 12 hand-pinned `@sha256` digests stripped from `mios.toml` (0 remaining), 27 Quadlets regenerated digest-free (0 `@sha256` in rendered Quadlets; digest-drift gate green), and `mios-bake-group` records each resolved digest to `/usr/share/mios/artifacts/sbom/bound-images.tsv` (L173-178). Remaining: apply the same principle -- resolve/verify at build, record to SBOM, never hand-pin -- to model checksums (`automation/38-llamacpp-prep.sh`), package version-hashes, and the per-app upstream `checksums.txt`/`.asc` verification the WS-MIOSSYS Wave fetchers add. SSOT keeps version/tag INTENT only (`:latest`/`:version`), never a literal digest/checksum.
**Where (files):** `automation/38-llamacpp-prep.sh`, `automation/90-generate-sbom.sh`, the WS-MIOSSYS `automation/NN-*.sh` app fetchers, `usr/share/mios/mios.toml`
**When (deps/order):** images DONE; interlocks with T-250 (digest-lock floating `:latest` sources at Wave 0) + T-252 (newest packages, tagged at build).
**Done When:**
- [ ] no hand-maintained `@sha256`/checksum literal remains in `mios.toml` or scripts for a runtime-pinned artifact; each resolved hash appears in the SBOM; the digest/checksum drift-checks validate build-resolved values.

## T-252: RELTOP-01 -- Credential-driven registry selection (GHCR else local/Forgejo)  [P2]
> **Priority:** P2 | **Status:** in-progress (CI capacity-gate DONE this session; registry-selection remaining) | **Effort:** S | **Domain:** Release/CI | **Who:** CI/build agent | **Source:** WS-RELTOP / Part 21; [[mios-release-topology]]
**Instructions (WHAT + HOW):** DONE for CI -- GitHub Actions and the Forgejo runner are declared EQUAL bit-for-bit publishers; build is LOCAL-first; `mios-ci.yml` `PUBLISH: 'false'` (L38) is a CAPACITY gate (a standard ubuntu-24.04 runner can't hold the ~60GB store) gating the `MIOS_BAKE_BOUND_IMAGES` build-arg (L243) + rechunk/push/cosign (L270+), to flip once a runner can hold the bake (or after T-250 shrinks it). Remaining: wire the "default to GitHub/GHCR push+pull when creds present, else local/Forgejo" registry-selection into the build driver / `install.env` credential detection (both workflows currently hardcode `ghcr`).
**Where (files):** `.github/workflows/mios-ci.yml`, `.forgejo/workflows/build-mios.yml`, `automation/build.sh` / `install.env`
**When (deps/order):** CI gate DONE; the `PUBLISH:'true'` flip is unblocked by T-250.
**Done When:**
- [ ] a build with GHCR creds pushes/pulls GHCR, with none targets local/Forgejo; both CI runners + the local build share one selection path; no hardcoded registry outside it.

## T-253: DEPRED-01 -- Hermes->agent-pipe collapse + sidecar consolidation  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** L | **Domain:** AI-plane/Deps | **Who:** agent-pipe backend engineer | **Source:** WS-DEPRED / Part 21; dependency-reduction study (§6)
**Instructions (WHAT + HOW):** Collapse MiOS-Hermes (`:8642`) into agent-pipe (`:8640`, already ~70% done): (1) repoint `MIOS_AI_ENDPOINT` `:8642`→`:8640` in `automation/lib/globals.sh:133` (+ `mios.toml [ai]/[hermes]`; add `8640` to `[security.nohc_allowlist]`); (2) retire the prefilter `:8641` hop (`mios-delegation-prefilter.service`); (3) absorb `gateway_sessions` (port `gateway-agent/session.py` into agent-pipe, opt-in replay); (4) decide browser/CDP (MCP `browser_*` verbs preferred; keep `mios-hermes-browser` :9222 as pure executor); (5) retire/alias `mios-gateway-agent.service`. Sidecar consolidations: fold Guacamole DB into pgvector (delete `mios-guacamole-postgres`), delete `mios-crowdsec-dashboard` (Quadlet + pin), cockpit-link socat → `systemd-socket-proxyd`, replace open-webui (`:8033`) with a Quickshell SSE `/v1` client (gate OWUI to `edge-endpoint`, then remove).
**Where (files):** `automation/lib/globals.sh`, `usr/share/mios/mios.toml` (`[ai]`/`[hermes]`/`[security.nohc_allowlist]`), `mios-delegation-prefilter.service`, `usr/lib/mios/gateway-agent/session.py` + agent-pipe `server.py`, `mios-hermes-browser.service`, `mios-gateway-agent.service`, `mios-guacamole-postgres.container`, `mios-crowdsec-dashboard.container`, `mios-cockpit-link` unit
**When (deps/order):** Browser/CDP + `hermes` CLI/Discord decisions are OPEN QUESTIONS; pairs with T-249 (OWUI gated to edge-endpoint) + T-250 (fewer images to consolidate).
**Done When:**
- [ ] every front-end resolves `MIOS_AI_ENDPOINT` to `:8640`; `:8641`/`:8642` retired or thin-aliased; Guacamole runs on a pgvector DB/role; `mios-crowdsec-dashboard` + `mios-guacamole-postgres` gone; a native SSE client streams `/v1/chat/completions`.

## T-254: MDRIVE-01 -- Hyper-V Gen 2 .vhdx off M: + sovereign Ceph OSD on M:  [P1] [VM]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Deploy/Windows | **Who:** deploy agent | **Source:** WS-MDRIVE / Part 21; run-off-M: deployment study
**Instructions (WHAT + HOW):** Deploy the universal image as a Hyper-V Generation 2 VM booting a `.vhdx` on `M:\MiOS-images\`, cut by `bootc install`/bootc-image-builder (`just vhdx`, `Justfile:217`, already factory-populates `/var` + `/var/home` -- the fix for the raw `wsl --import` deadlock). Add a `vhdx-m` Justfile recipe + `C:\mios-bootstrap\deploy-mios-hyperv-m.ps1` (load tar, cut vhdx if missing, `New-VM -Generation 2` off M: with `Set-VMFirmware -SecureBootTemplate MicrosoftUEFICertificateAuthority`, attach Ceph OSD vhdx, `netsh portproxy :8640`, DDA/GPU-P). Sovereign storage: a 2nd dynamic `.vhdx` on M: as the single-node Ceph OSD backing `/var/home` (`var-home.mount` `Type=ceph`); relax `ConditionVirtualization=no` on `ceph-bootstrap.service`/`mios-ceph-bootstrap.service` to a config-flag gate (`[storage.cephfs].enable` / `/run/mios/ceph-enabled`); the local 20GiB `/var/home` ext4 partition (carved by `config/artifacts/vhdx.toml`) is the automatic `nofail`+`ConditionPathExists` fallback. dGPU via DDA (recommended; iGPU carries Windows desktop) or GPU-P. WSL2 `--import-in-place` is an explicit disposable preview only (no populated `/var` → not the sovereign target). Root cause: a bootc image bakes NOTHING into `/var` (Law 2); only the installer populates it.
**Where (files):** `Justfile` (new `vhdx-m`), `config/artifacts/vhdx.toml`, `usr/lib/systemd/system/ceph-bootstrap.service` + `mios-ceph-bootstrap.service`, `usr/libexec/mios/ceph-bootstrap.sh`, `usr/share/mios/mios.toml [storage.cephfs].enable`, `usr/lib/systemd/system-preset/95-mios-wsl.preset` (optional), `C:\mios-bootstrap\deploy-mios-hyperv-m.ps1` (new)
**When (deps/order):** Re-establish a Linux podman once (BIB/`bootc install` need it); GPU-policy/Ceph-now-vs-later/OSD-sizing/`ConditionVirtualization`-scope are operator decisions. VM/operator-gated.
**Done When:**
- [ ] a MiOS Gen 2 VM boots off `M:\MiOS-images\mios-0.3.0.vhdx` with a populated `/var/home`, `bootc status` healthy, and `curl http://localhost:8640/v1/models` answering from Windows; with the OSD vhdx + `[storage.cephfs].enable=true`, `findmnt /var/home` reports `type ceph` and survives a root-vhdx rebuild; `bootc upgrade`/`rollback` work in-guest.

## T-255: DOCS -- Planning-docs refactor (ADR system + generated index + lean thematic roadmap + Diátaxis)  [P1]
> **Priority:** P1 | **Status:** in-progress (DOCS-01 and DOCS-02 done; DOCS-03..06 planned) | **Effort:** L | **Domain:** Docs/Meta | **Who:** docs/tooling agent | **Source:** WS-DOCS / Part 21; planning-docs refactor plan + ADR-0007
**What/Why:** Solidify the refactor into cohesive, AI-agent-native docs matching upstream patterns (MADR ADRs · KEP-style WS metadata · Diátaxis · Keep-a-Changelog+SemVer · OpenAI-Model-Spec-style rules doc · `llms.txt`/`AGENTS.md`) so a future agent starts a workstream from ONE self-contained file. DOCS-01 ✅ shipped the ADR system (`usr/share/doc/mios/adr/`, ADR-0001..0007 + README); DOCS-02..06 add the generated index+drift-check, the lean thematic roadmap (Parts 1-20 archived), the honest status-lifecycle retag, the Diátaxis reorg, and the generated MiOS Spec (laws+conventions rendered from the SSOT, ADR-0007).
**Where (files):** `usr/share/doc/mios/adr/*` (done), `tools/roadmap-index.py` (new), `tools/generate-mios-spec.py` (new), `automation/38-drift-checks.sh`, `ROADMAP.md`, `TASKS.md`, `usr/share/doc/mios/roadmap/history/*`, `usr/share/doc/mios/spec/*`, `CHANGELOG.md`, `llms.txt`, `AGENTS.md`
**When (deps/order):** DOCS-01 done → DOCS-02 (schema+generator) → DOCS-03 (lean roadmap+archive) → DOCS-04 (retag) + DOCS-05 (Diátaxis) + DOCS-06 (MiOS Spec).
**Done When:**
- [x] ADR system: README + ADR-0001..0007 accepted; every Part-21 WS backed by an ADR; governance model recorded (ADR-0007).
- [ ] `just drift-gate` regenerates the roadmap index + the MiOS Spec byte-identically + fails on a bad ADR/law/`ssot_key` ref; ToC lists all Parts.
- [ ] `ROADMAP.md` is theme-grouped active-only (~≤600 lines) with Parts 1-20 losslessly archived; no WS lost.
- [ ] no WS tagged `done` that is gated-off/never-fired; Diátaxis quadrants + `llms.txt` route an agent in ≤3 hops.

## T-256: CAT-01 -- Flatten MiOS-Cat to a single owner (mios-bootstrap owns `cat/`)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Deploy/Cat | **Who:** deploy/installer agent | **Source:** WS-CAT / ADR-0008; MiOS-Cat unification plan §1/§5
**Instructions (WHAT + HOW):** Make `mios-bootstrap` the single canonical owner of MiOS-Cat at `C:\mios-bootstrap\cat\`. `git mv` the deep `C:\mios-bootstrap\src\autounattend\medicat_installer\` nest (3–5 levels) up to `cat\` (launchers → `cat\`, FileChecker/hasher/bin/7z → `cat\lib\`, resources → `cat\resources\`, the Windows-ISO subsystem `New-MiOSISO`/`mios-uup-fetch`/`New-MiOSAutounattend`/`Build-MiOSXboxISO`/`MiOS-Provision.lib` → `cat\iso\`, translations → `cat\i18n\`). **Delete** the byte-identical `C:\MiOS\src\autounattend\medicat_installer\` copy (`diff -q` confirmed empty; verify no live consumer first — flatten-campaign guardrail). This satisfies Law 1 (`C:\MiOS/usr/` *is* `/usr`; a host installer must not live under it) and the two-repo no-double-track rule. Do NOT run destructive git ops as part of this task's *decision capture* — this task tracks the planned move.
**Where (files):** `C:\mios-bootstrap\cat\**` (new home), `C:\mios-bootstrap\src\autounattend\medicat_installer\**` (source of move), `C:\MiOS\src\autounattend\medicat_installer\**` (delete)
**When (deps/order):** First WS-CAT task; unblocks T-257/T-258/T-259. Verify-no-consumer gate before any delete.
**Done When:**
- [ ] one MiOS-Cat home at `cat\`; `C:\MiOS` free of the installer; a cross-repo `diff` finds no `medicat_installer` dup; deepest path drops from `src\autounattend\medicat_installer\resources\ventoy\` to `cat\resources\ventoy\`.

## T-257: CAT-02 -- Verb dispatch + tri-launcher parity  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Deploy/Cat | **Who:** deploy/installer agent | **Source:** WS-CAT / ADR-0008; MiOS-Cat unification plan §2
**Instructions (WHAT + HOW):** Give the tri-launcher `cat\MiOS-Cat.{ps1,sh,bat}` one shared verb vocabulary — **stage · install · build · update · provision · manual** — as a thin `case`/`goto`/`switch` dispatch, with all business logic in a shared `cat\lib\` (PowerShell module + bash lib). Port the advanced `.bat` logic (MiOS-Repo staging, WinPE DISM injection, git-pull self-update) into the canonical `.ps1` so the launchers reach parity (Law 9); reduce `.bat` to the WinPE/legacy-cmd shim that calls the `.ps1` when PowerShell is present. Every existing entry point (Get-MiOS.ps1 irm|iex, bootstrap curl, UUP/autounattend ISO pipeline, mios-kickstart.cfg, `just` build) becomes a verb back-end, not a peer. The interactive menu becomes the no-verb default (`cat` → menu; `cat install` → headless).
**Where (files):** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh,bat}`, `C:\mios-bootstrap\cat\lib\MiOS-Cat.psm1` + `cat.sh` (new), the per-verb back-end shims into `cat\iso\` / `just` / bootstrap
**When (deps/order):** After T-256 (single home). Pairs with T-259 (web one-liners fold into `cat install`).
**Done When:**
- [ ] `cat install` is headless-identical across `.ps1`/`.sh`/`.bat`; zero business logic duplicated between launchers; the no-verb default opens the menu; the `.bat` is a reduced WinPE shim.

## T-258: CAT-03 -- `[cat]` SSOT block + fix the dangling `drivepath`/`medicatver`/`cache_path` reads  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Deploy/Cat/SSOT | **Who:** SSOT/installer agent | **Source:** WS-CAT / ADR-0008; MiOS-Cat unification plan §5.2/§6
**Instructions (WHAT + HOW):** MiOS-Cat today reads `..\..\..\..\mios.toml` (the 63 KB root seed copy) and looks for `drivepath`, `medicatver`, `cache_path` — keys that **exist in no `mios.toml`** — so it silently uses hardcoded defaults (a Law 7 NO-HARDCODE + Law 8 SSOT-PROJECTION violation). Add a `[cat]` block to the real SSOT `usr/share/mios/mios.toml`: `drivepath`, `medicatver`, `cache_path`, `repo_partition.label = "MiOS-Repo"`, `data_partition.label = "MiOS-Data"`, `data_partition.min_disk_gb = 512`, and `models` (a reference to `[ai].bake_models`). Repoint MiOS-Cat to resolve the 597 KB SSOT (through the shared `mios_toml` resolver), not the seed. Add a `automation/38-drift-checks.sh` check that the `[cat]`/`[colors]` reads resolve.
**Where (files):** `usr/share/mios/mios.toml` (new `[cat]` block), `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` + `cat\lib\` (SSOT resolve), `automation/38-drift-checks.sh` (new check)
**When (deps/order):** After T-256. Interlocks with T-266 (seed-copy provenance) — confirm the 63 KB→597 KB relationship before repointing.
**Done When:**
- [ ] no MiOS-Cat value is hardcoded that has an SSOT home; `[cat]` + `[colors]` reads resolve against `usr/share/mios/mios.toml`; the drift-check fails if a `[cat]` key is missing.

## T-259: CAT-04 -- Fold the web one-liners (`irm|iex` ⇄ `curl`) into `cat install`  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Deploy/Cat | **Who:** deploy/installer agent | **Source:** WS-CAT / ADR-0008; MiOS-Cat unification plan §2.3
**Instructions (WHAT + HOW):** Collapse the bodies of `C:\mios-bootstrap\{Get-MiOS,bootstrap,install}.ps1` + `bootstrap.sh` into thin `cat install` shims (keep the published one-liner URLs). Wire the bidirectional handoff so `irm …/cat | iex` (Windows) and `curl -fsSL …/cat.sh | sh` (Linux/WSL) are the SAME front door from two shells: the `.ps1` shells out to the `curl` path for a Linux/WSL target (`wsl -e sh -c 'curl … | sh'`); the `.sh` invokes `pwsh`/`powershell.exe` for a Windows-side action (Hyper-V VM create, WinPE). Both resolve the same `[cat]` SSOT + the same verb set (Law 9 ONE-CANONICAL-NAME on the entry surface).
**Where (files):** `C:\mios-bootstrap\{Get-MiOS,bootstrap,install}.ps1`, `C:\mios-bootstrap\bootstrap.sh`, `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}`
**When (deps/order):** After T-257 (verb dispatch exists). Keeps the existing published `irm`/`curl` URLs stable.
**Done When:**
- [ ] `irm …/cat | iex` and `curl …/cat.sh | sh` both reach the identical verb set; `cat install` means the same thing regardless of shell; the legacy scripts are thin shims, not peers.

## T-260: CATREPO-01 -- Small MiOS-Repo shadow-config partition (always) + kickstart path fix  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Deploy/Cat/Repo | **Who:** deploy/installer agent | **Source:** WS-CATREPO / ADR-0008; MiOS-Cat unification plan §3 (operator re-scope: small MiOS-Repo)
**Instructions (WHAT + HOW):** Populate a SMALL always-present `MiOS-Repo` partition (P3, target ~≤16 GB) with the **shadow-config brain** — `mios.toml` (SSOT), `mios.html` (configurator), the MiOS Portal assets, a self-contained MiOS-Cat copy, and a **small repos-clone** (config/source, NOT the binary payload). This is the offline embodiment of the ADR-0009 shareable-link surface. Each payload class is degrade-open (online `git clone` → offline `robocopy`/`cp -r` from `MiOS-Repo/repos/`). **Fix the kickstart path mismatch:** the `.bat` stages repos to `%repodrive%:\mios-bootstrap` but `mios-kickstart.cfg` looks under `/mnt/usb/ventoy/repo/mios-bootstrap` — align both to one canonical `MiOS-Repo/repos/` and update the kickstart `%post`. Ventoy-bootable ISOs/WIMs stay on the Ventoy data partition (not P3). NOTE (operator reconciliation): the 78 GB OCI tar, `just all` artifacts, model weights, and package mirrors do NOT go here — they go to the separate MiOS-Data store (T-261).
**Where (files):** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage`), `usr/share/mios/mios.toml` (`[cat].repo_partition`), `…\resources\ventoy\mios-kickstart.cfg` (`%post` repo path), the `MiOS-Repo/` layout
**When (deps/order):** After T-256/T-258 (home + `[cat]` SSOT). Sibling of T-261 (bulk store).
**Done When:**
- [ ] a small stick carries the shadow-config brain (mios.toml + mios.html + Portal + MiOS-Cat + a small repos-clone) and fits any USB; a fully offline bare-metal kickstart install succeeds from `MiOS-Repo/repos/`; the kickstart repo path matches the stager.

## T-261: CATREPO-02 -- Separate MiOS-Data bulk store (512GB+ only): OCI tar + `just all` artifacts  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Deploy/Cat/Repo | **Who:** deploy/installer agent | **Source:** WS-CATREPO / ADR-0008; MiOS-Cat unification plan §3 (operator re-scope: separate MiOS-Data)
**Instructions (WHAT + HOW):** On disks ≥ 512 GB only (`Get-Disk` size gate), `cat stage` creates a **separate** `MiOS-Data` store carrying the **bulk**: the ~78 GB `podman save` of `localhost/mios:latest` (offline `podman load`) and the `just all` disk artifacts (`raw/iso/qcow2/vhdx/wsl2`, incl. the ADR-0005 `mios-<ver>.vhdx`). Degrade-open: online `podman pull ghcr.io/mios-dev/mios` → offline `podman load MiOS-Data/images/*.tar`. Keep MiOS-Data physically distinct from the small always-present MiOS-Repo (T-260) so a small stick still deploys network-degraded while a 512 GB+ stick is fully offline.
**Where (files):** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage` — `Get-Disk` gate + `podman save`/copy), `usr/share/mios/mios.toml` (`[cat].data_partition` — `label`, `min_disk_gb = 512`), `MiOS-Data/images/`, the `just all` artifact paths (`M:\MiOS-images\`)
**When (deps/order):** After T-260 (repo layout) + WS-BAKEGATE (defines which artifacts exist). Precedes T-262/T-263 (models + mirrors also live on MiOS-Data).
**Done When:**
- [ ] on a 512 GB+ disk, MiOS-Data is created separately from MiOS-Repo; offline `podman load` + `bootc switch` from USB works; on a <512 GB disk, MiOS-Data is skipped and only the small MiOS-Repo is written.

## T-262: CATREPO-03 -- Model embedding + `cat provision` (Law 12 offline)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Deploy/Cat/Models | **Who:** deploy/AI-plane agent | **Source:** WS-CATREPO / ADR-0008; MiOS-Cat unification plan §3.3
**Instructions (WHAT + HOW):** Read the `mios.toml`-defined MODELS from the SSOT (never invent — Law 8): `[ai].bake_models` GGUF CSV (L5744) + fleet tags (L6116), `[ai.vllm].bake_model` (L6724, `Qwen3-30B-A3B-Instruct-2507-AWQ` ~16 GB), `[ai.sglang].bake_model` (L6742). `cat stage` (512GB+/MiOS-Data path) fetches each from Hugging Face into `MiOS-Data/models/` and verifies by checksum (the WS-SBOM / `38-llamacpp-prep.sh` resolved-not-hardcoded pattern) — turning the store into an offline HF mirror. `cat provision` copies them into the deployed host offline: GGUFs → the llama.cpp model dir, the AWQ weights → `/usr/share/mios/vllm/model` (whose `config.json` is the `mios-llm-heavy` activation gate). This is Law 12 (BAKE-NOT-FETCH) realized as offline provisioning — the OCI image bakes engines only; MiOS-Data is the offline weight store. Model-redistribution licensing is an OPEN QUESTION (ADR-0008): if disallowed, store a fetch-manifest + checksums instead of weights.
**Where (files):** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat stage`/`cat provision`), `usr/share/mios/mios.toml` (`[ai].bake_models` L5744/L6116, `[ai.vllm].bake_model` L6724, `[ai.sglang].bake_model` L6742, `[cat].models` ref), `MiOS-Data/models/`, `/usr/share/mios/vllm/model` (provision target), `automation/38-llamacpp-prep.sh` (checksum pattern)
**When (deps/order):** After T-261 (MiOS-Data store exists). Model-redistribution decision gates whether weights or a manifest are stored.
**Done When:**
- [ ] a deployed host's heavy lane comes up with ZERO network (the `/usr/share/mios/vllm/model/config.json` weight gate present); GGUFs + the AWQ weights are provisioned offline from MiOS-Data; each model's checksum is verified, not hardcoded.

## T-263: CATREPO-04 -- Offline dnf/flatpak/pip mirrors on MiOS-Data + `cat update` self-refresh  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** Deploy/Cat/Mirrors | **Who:** deploy/build agent | **Source:** WS-CATREPO / ADR-0008; MiOS-Cat unification plan §3.4
**Instructions (WHAT + HOW):** Build the offline package mirrors into `MiOS-Data/` (512GB+ path): **dnf** via `reposync` + `createrepo_c` (referenced by a kickstart `repo --baseurl=file://…`), **flatpak** via `flatpak create-usb` / OCI bundle, **pip** via a `pip download` set / `bandersnatch` for the agent venvs. Degrade-open: live mirror online → `file://` mirror offline. `cat update` re-pulls all payload classes when online (repos, OCI image, models, mirrors) and re-stamps a `MiOS-Data/manifest.json` (payload version + checksums) so a deployed host can tell whether its store is current.
**Where (files):** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh}` (`cat update`/mirror build), `MiOS-Data/{dnf,flatpak,pip}/`, `MiOS-Data/manifest.json`, `…\resources\ventoy\mios-kickstart.cfg` (`repo --baseurl=file://`), `usr/share/mios/mios.toml` (`[desktop].flatpaks` source list)
**When (deps/order):** After T-261 (MiOS-Data store). Lowest-urgency Tier-B item.
**Done When:**
- [ ] an offline build/first-boot resolves all dnf/flatpak/pip packages from USB; `cat update` refreshes the store + re-stamps `manifest.json` when online.

## T-264: CATFLAT-01 -- Dead-weight purge + leave-nothing-behind  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** S | **Domain:** Deploy/Cat/Flatten | **Who:** cleanup agent | **Source:** WS-CATFLAT / ADR-0008; MiOS-Cat unification plan §5.2
**Instructions (WHAT + HOW):** Purge tracked cruft from the bootstrap root after verifying no live consumer (flatten-campaign guardrail): `Get-MiOS.ps1.bom-bak`, `commit.patch`/`commit_a8faad4.patch`/`commit_else.patch`/`commit_skip.patch`, `temp.txt`/`temp2.txt`, `scratch.ps1` (~606 KB); fold `R-DH-BOOTSTRAP-AUDIT.md` if already absorbed. Drop the committed bundled binaries (the ~23 GB MediCat 7z, Ventoy release zips, `bin\*.exe`) — they are downloaded artifacts, not source; keep the fetch-on-demand logic (`.bat` already curls Ventoy + 7z). Fold MediCat i18n down to MiOS strings only.
**Where (files):** `C:\mios-bootstrap\*.{patch,txt,ps1,bom-bak}` (cruft), `C:\mios-bootstrap\cat\` (bundled binaries, i18n), the `.bat` fetch-on-demand logic (keep)
**When (deps/order):** After T-256 (single-owner flatten). Verify-no-consumer before each delete.
**Done When:**
- [ ] `cat/` tracks source only; ~6 MB+ tracked cruft gone; the committed Ventoy/7z/MediCat binaries are removed while fetch-on-demand still works.

## T-265: CATFLAT-02 -- ADR root breadcrumb + spec cross-ref  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** S | **Domain:** Deploy/Cat/Docs | **Who:** docs/tooling agent | **Source:** WS-CATFLAT / ADR-0008; MiOS-Cat unification plan §5.3
**Instructions (WHAT + HOW):** Keep the ADRs baked at `usr/share/doc/mios/adr/` (Law 1 — a running MiOS carries its own *why*; do NOT move them to `/etc` or the repo root). To satisfy "ADRs near the system root," generate a breadcrumb from SSOT (Law 8, drift-checked, never hand-maintained): `C:\MiOS\ADR.md` (a pointer/index rendered by the `roadmap-index.py`-class generator) + `C:\mios-bootstrap\cat\ADR-0008.md` (a copy/symlink of the new record so the installer repo is self-documenting). Link both from `llms.txt` / `AGENTS.md`.
**Where (files):** `C:\MiOS\ADR.md` (generated), `C:\mios-bootstrap\cat\ADR-0008.md` (generated copy/symlink), `usr/share/doc/mios/adr/` (unchanged, baked), `llms.txt`, `AGENTS.md`, the breadcrumb generator
**When (deps/order):** After T-256. Complements T-255 (the roadmap-index generator class).
**Done When:**
- [ ] an agent reaches the ADR index from either repo root in ≤2 hops; the breadcrumb is generated + drift-gate green; the baked ADRs under `/usr` are unmoved.

## T-266: CATFLAT-03 -- mios.toml seed-copy consolidation (flag → fix)  [P3]
> **Priority:** P3 | **Status:** planned | **Effort:** M | **Domain:** Deploy/Cat/SSOT | **Who:** SSOT agent | **Source:** WS-CATFLAT / ADR-0008; MiOS-Cat unification plan §5.2
**Instructions (WHAT + HOW):** Resolve the `mios.toml` seed-copy question: the SSOT is `C:\MiOS\usr\share\mios\mios.toml` (597 KB); the root `C:\MiOS\mios.toml` (63 KB) and `C:\mios-bootstrap\mios.toml` (68 KB) are seed/derived copies. Determine which is canonical vs generated, document the seed→SSOT relationship, and (if seeds are generated) wire their regeneration + a drift-check. MiOS-Cat must read ONLY the 597 KB SSOT (paired with T-258). This is the root cause of the T-258 dangling-read bug — confirm the relationship before/with repointing.
**Where (files):** `C:\MiOS\usr\share\mios\mios.toml` (SSOT), `C:\MiOS\mios.toml` + `C:\mios-bootstrap\mios.toml` (seeds), the seed generator (if any), `automation/38-drift-checks.sh`
**When (deps/order):** Pairs with T-258 (SSOT repoint). Lowest priority; the T-258 fix can land with a documented assumption and this closes it.
**Done When:**
- [ ] one documented SSOT + explicitly-generated seeds (or a documented decision to keep them); MiOS-Cat reads only the 597 KB SSOT; a drift-check guards seed↔SSOT drift.

## T-267: CONFIG-01 -- Fold `mios.html` into the MiOS Portal at `:8640/` (one web + API front door)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Config/Portal | **Who:** agent-pipe / Portal backend engineer | **Source:** WS-CONFIG / ADR-0009; unified config surface (operator constraint #2/#3)
**Instructions (WHAT + HOW):** Fold the standalone configurator `mios.html` (`usr/share/mios/configurator/`) INTO the MiOS Portal as a configurator *view*, so `mios.toml` + `mios.html` + the Portal are ONE config surface served at `:8640/` by agent-pipe: `GET /` serves the Portal (configurator folded in) and `/v1/*` serves the OpenAI API — the SAME single front door (the ADR-0006 convergence). Wire read/write of `mios.toml` from the configurator view through `mios_portal.py` (Law 8 SSOT-PROJECTION; addressed by key never literal — Law 7). "The Portal needs config too" resolves as *it is configured through the surface it is*. The Portal (`:8640/`, or its `[portal].public_host` hosted equivalent) is the shareable web LINK that bootstraps open → configure → deploy; the USB MiOS-Repo shadow-config (T-260 / ADR-0008) is its offline embodiment. Acceptance bar for the whole effort: a shareable link + a USB disk + a usable computer.
**Where (files):** `usr/lib/mios/agent-pipe/mios_portal.py` (configurator view + `mios.toml` read/write), `usr/lib/mios/agent-pipe/server.py` (`GET /` + `/v1/*` one door), `usr/share/mios/portal/` (absorb the configurator UI), `usr/share/mios/configurator/mios.html` (folded in / retired standalone), `usr/share/mios/mios.toml [portal]` (L220), `tools/mios-portal-app/` (Android client → same `:8640/`)
**When (deps/order):** No hard dep (the Portal + `:8640` `/v1` already exist). Converges with T-253 (WS-DEPRED single `:8640` front-door collapse); governed by ADR-0007.
**Done When:**
- [ ] the configurator is a view within the Portal at `:8640/`; `GET /` (Portal) and `/v1/*` (OpenAI API) share the one door; every deployment type's config reads/writes `mios.toml` through the surface; the shareable link and the USB are the same surface online and offline.

## T-268: DEBT-01 -- Collapse version/SSOT to one value (TD-2)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Build/SSOT/Version | **Who:** SSOT/build agent | **Source:** WS-DEBT / ADR-0011; combined tech-debt map §1 (TD-2, re-measured)
**Instructions (WHAT + HOW):** Kill the version/SSOT triplication measured live: there are **3× `mios.toml`** — canonical `usr/share/mios/mios.toml` (10,869 ln) plus two diverged roots `C:\MiOS\mios.toml` (says **0.2.4**) and `C:\mios-bootstrap\mios.toml` — while `VERSION` and SSOT `mios_version` are both **0.3.0**, compounded by **37× hardcoded `v0.2.4`** (and 29× `v0.2.0`) in `automation/*.sh` headers. Collapse to one projected version token: strip the literal `vX.Y.Z` from all script headers (project from `[meta].mios_version` at render time — Law 7); make the two root `mios.toml` **generated projections of the SSOT** (or delete them), documenting the seed→SSOT relationship (pairs with T-266); add two drift-checks — "no literal version in headers" and "root `mios.toml` ⊆ SSOT". Near-zero-risk, highest-reach: a build resolving the wrong 7×-smaller copy silently ships a stale manifest. Directly closes the Law 9 / ADR-0009 violation. NOTE: the two `C:\mios-bootstrap` MiOS-Cat launcher files are owned by a concurrent agent — do not touch `cat\MiOS-Cat.bat`/`.ps1`.
**Where (files):** `C:\MiOS\VERSION`, `C:\MiOS\mios.toml`, `C:\mios-bootstrap\mios.toml`, `C:\MiOS\usr\share\mios\mios.toml` (`[meta].mios_version`), all `automation/*.sh` headers, `automation/38-drift-checks.sh` (two new checks)
**When (deps/order):** Phase −1, near-zero-risk; unblocks WS-LANG (T-272) and the rest of WS-DEBT. Interlocks with T-266 (seed-copy provenance).
**Done When:**
- [ ] one authoritative version token; no literal `v0.2.4`/`v0.2.0` remains in `automation/*.sh` headers; the two root `mios.toml` are generated-or-deleted and drift-gated (`root ⊆ SSOT`); a build can no longer resolve a stale copy.

## T-269: DEBT-02 -- shellcheck CI gate + kill the 9 `eval`-on-agent-args verbs (TD-1)  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** M | **Domain:** Build/Security | **Who:** build/security agent | **Source:** WS-DEBT / ADR-0011; combined tech-debt map §1 (TD-1) + §5 Phase −1
**Instructions (WHAT + HOW):** Enforce the conventions the repo already documents but never gates. (1) Add a `shellcheck -S warning` CI job over `automation/` + `usr/libexec/mios/` bash (today `shellcheck` exists only as `# shellcheck source=` comments — no lint job). (2) Enforce `set -euo pipefail` on the **23 runtime verbs** that have no `set -e`. (3) Audit and eliminate the **9 verbs that `eval` on agent-derived args** — the injection surface on the agent-facing OS-control plane (highest-severity security debt on the verb chokepoint). Replace each `eval` with an explicit arg-array dispatch / `case` allowlist. This is TD-1, the top-ranked debt (spans build + runtime + the agent-facing surface).
**Where (files):** `.github/workflows/mios-ci.yml` (new shellcheck job), `Justfile` (a `just shellcheck` recipe), the 23 unguarded + 9 `eval` verbs under `usr/libexec/mios/mios-*`
**When (deps/order):** Phase −1, no new toolchain. Interlocks with T-272 (the Rust verb-dispatcher port removes the `eval` surface structurally).
**Done When:**
- [ ] CI fails on a shellcheck warning; the 23 verbs carry `set -euo pipefail`; **zero** verbs `eval` on agent-derived args; each former `eval` site is an explicit allowlisted dispatch.

## T-270: DOTFILES-01 -- `[dotfiles.registry.*]` + `mios-dotfiles-render` + `apply` verb + both-sides gate  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Dotfiles/SSOT | **Who:** SSOT/theme agent | **Source:** WS-DOTFILES / ADR-0010; SSOT-as-dotfiles design dossier
**Instructions (WHAT + HOW):** Generalize the LANDED palette+btop projection into `mios.toml` = the cross-platform system dotfiles. **Landed proof (this session, DONE):** `usr/libexec/mios/mios-theme-render` gained a **settings-surface** concept, `[btop]` (~60 keys) projects the whole `etc/btop/btop.conf` unified Linux+Windows, and drift-check 25 (`check_theme_projection`) auto-extended and is proven green. **This task (planned):** (1) Promote the hardcoded Python `SURFACES` dict into an SSOT-authored `[dotfiles.registry.<surface>]` map — per-platform `target.<os>`; `kind` = template/json-merge/registry/command/skip; `format`; `sources`; `platforms`; `condition` — transcribing the existing color+btop surfaces first (pure refactor, check 25 stays green). (2) Fork `mios-theme-render` → `mios-dotfiles-render`: registry from `mios_toml.load_merged()`, `@MIOS:<section>.<key>@` arbitrary-key tokens, format-aware `merge` preserving foreign keys (WT/VS Code `settings.json` never clobbered), per-platform target resolution, and a new **`apply`/`diff` verb writing to live HOME** (`~/.config`, `%USERPROFILE%`, `%LOCALAPPDATA%`). (3) Add the new domains `[shell]`/`[editor]`/`[git]`(→`[identity]`, Law 9)/`[ssh]`(`secret_ref`, raw keys never in SSOT). (4) Generalize `check_theme_projection` (check 25) → `check_dotfiles_projection` over the full registry; add the Windows runtime half `Test-MiOSProjection`; collapse the scattered `Install-MiOS*` bodies into thin registry-driven `Sync-MiOSDotfiles` calls; add a `mios dotfiles apply/diff/drift` verb (`[verbs.dotfiles_*]`).
**Where (files):** `usr/share/mios/mios.toml` (`[dotfiles.registry.*]`, `[shell]`/`[editor]`/`[git]`/`[ssh]`; existing `[colors]`/`[theme]`/`[appearance]`/`[terminal]`/`[identity]`/`[btop]` stay as content), `usr/libexec/mios/mios-theme-render` (reference; forks to `mios-dotfiles-render`, kept as back-compat alias), `usr/libexec/mios/mios-sync-theme`, `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh`, `automation/38-drift-checks.sh` (check 25 → `check_dotfiles_projection`), `C:\mios-bootstrap\Get-MiOS.ps1` (`Sync-MiOSDotfiles`/`Test-MiOSProjection`), `usr/bin/mios`
**When (deps/order):** No hard dep (palette+btop already land). Interlocks with T-267 (the Portal edits the `[dotfiles.registry.*]` map) and ADR-0005/0008 (the overlay carries across deployments). OPEN QUESTIONS: secrets store per platform; a deployment-type enum for `condition` (ADR-0010).
**Done When:**
- [ ] the color+btop surfaces are registry-driven with check 25 green; a `[theme].opacity` edit projects to Linux CSS + the WT `json-merge` block + the WSL bridge with foreign keys intact and both gates pass; `mios dotfiles apply` writes live HOME; no `Install-MiOS*` value is hand-typed that has an SSOT home.

## T-271: TEMPLATE-01 -- Compiled file-pattern system + `mios new` + conformance check + Law-14  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Build/Templates | **Who:** tooling/docs agent | **Source:** WS-TEMPLATE / ADR-0011; combined tech-debt map §3
**Instructions (WHAT + HOW):** Build the global compiled-template system so an agent learns MiOS formatting from a few files. Author ~15 templates (`bash`, `python-tool`, `python-module`, `rust`, `typescript`, `powershell`, `toml-config`, `yaml`, `json-schema`, `markdown-doc`, `adr`, `roadmap`, `systemd-unit`, `quadlet` [generated], `automation-step`) under `usr/share/mios/templates/`, each = the shared AI-hint header block (produced by the same `usr/libexec/mios/mios-ai-tag` engine — header stays single-sourced) + a small per-type body skeleton whose structure is ALSO validated (closing the gap where only the header is checked). Declare each in SSOT (`[templates.<type>]`: `match`/`comment`/`required_header`/`required_markers`/`generated`/`scaffold`). Land the scaffolder first as Python `usr/libexec/mios/mios-new` (`mios new <type> <name>`, reusing `mios-ai-tag`, filling canonical fields — next ADR number, next `automation/NN` ordinal, canonical ports/endpoints — from SSOT and registering the canonical name via `tools/generate-names-registry.py`), then absorb into `miosd scaffold`. Add a golden round-trip compiler (`tools/compile-templates.py`) and a `check_template_conformance` drift-check (Python worker, mirroring `check_hint_coverage → mios-ai-hint-coverage`, degrade-open, soft→hard ratchet; `check_hint_coverage` becomes its header-subset). `generated=true` types refuse to scaffold an editable file (scaffold the generator + its `mios.toml` section — Law 8 authoritative). **Candidate Law 14 (ONE-TEMPLATE-PER-TYPE):** per ADR-0007 a new law = this ADR + a `[laws]` registry row (id 14) + `check_template_conformance` as its `enforced_by` — **the `[laws]` edit and enforcement are OPERATOR-GATED; do NOT edit the `[laws]` table without confirmation.**
**Where (files):** `usr/share/mios/templates/*.tmpl` (new, ~15), `usr/share/mios/mios.toml` (`[templates]` schema; candidate `[laws]` id-14 row — OPERATOR-GATED), `usr/libexec/mios/mios-new` (new), `usr/libexec/mios/mios-ai-tag` (reused), `tools/compile-templates.py` (new), `automation/38-drift-checks.sh` (`check_template_conformance`), `usr/bin/mios` + `Justfile` (`mios new`/`just new`)
**When (deps/order):** No hard dep (Python-first, offline-deterministic); folds into WS-LANG's `miosd` (T-272) once the Rust workspace exists. OPEN QUESTIONS: Law-14 operator confirmation; the next free drift-check number.
**Done When:**
- [ ] `mios new <type> <name>` produces a conformant file that passes `check_template_conformance` + the golden compiler; a template that can't produce a conformant file fails the build; the header check is the header-subset of conformance; Law-14 is proposed with enforcement wired, `[laws]` row awaiting operator sign-off.

## T-272: LANG-01 -- Stand up the Rust workspace + port the first fragile bash tool  [P1]
> **Priority:** P1 | **Status:** planned | **Effort:** L | **Domain:** Build/Lang | **Who:** native-tooling agent | **Source:** WS-LANG / ADR-0011; combined tech-debt map §2/§4/§5
**Instructions (WHAT + HOW):** Begin the language-per-domain unification. Create the cargo workspace (crates behind one `miosd` static musl binary, subcommands `build|drift|verb|resolve|render|cat|scaffold|fmt`) built once in an early **cached Containerfile stage** and `COPY`'d to `/usr/libexec/mios/miosd`, invoked by **thin RUNs** so the immutable-image contract holds (Law 8 strengthened — `miosd render`/`drift`/`fmt` are the same regenerate-and-diff gate). Port the **first** fragile bash tool — either the **drift-runner** (`automation/38-drift-checks.sh`, 44 `check_*` in ~3.1k ln bash — highest resilience win, lowest coupling; several checks are already Python-in-bash) or the **verb dispatcher** (removes the 9-verb `eval` surface) — running old+new **side-by-side and diffing to identical** before deleting the bash. Collapse the Law-13 resolver twin (`usr/lib/mios/mios_toml.py` ⇄ `tools/lib/userenv.sh`) into one crate exposing a `--shell` KEY=VAL emitter + a pyo3 face, ending the parity drift (retire `check_userenv_parity`). **OPEN QUESTION — native-workspace location:** `C:\MiOS\src\` is already occupied by the in-tree C# `mios-launch.cs` + `autounattend/`, so the cargo workspace goes elsewhere (candidate `C:\MiOS\tools\native\` or `src\mios-rs\`) — do NOT clobber `src/`. Go is rejected as a second native tier (documented escape hatch only). The 66 `automation/NN-*.sh` OS-touching steps stay shell-thin; the AI plane stays Python.
**Where (files):** the new cargo workspace (location OPEN — `C:\MiOS\tools\native\` or `src\mios-rs\`), `Containerfile` (early cached Rust stage + `COPY`), `automation/build.sh` (→ 20-line shim), `automation/38-drift-checks.sh` (checks ported one at a time), `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh` (collapse to the crate), `C:\MiOS\src\mios-launch.cs` (later folds into `miosd cat`)
**When (deps/order):** After T-268 (one version token) + T-269 (shellcheck gate) — Phase −1 unblocks the port. OPEN QUESTIONS: native-workspace location; Go escape-hatch; pyo3-vs-subprocess for the AI-plane resolver binding.
**Done When:**
- [ ] `miosd` bakes in a cached stage and is invoked by unchanged thin RUNs; the first ported tool runs byte-identical to the bash it replaces (side-by-side diff clean), then the bash is deleted; the resolver twin is one crate with pyo3 + `--shell` faces and `check_userenv_parity` is retired.

## T-273: DEBT-03 -- Split `mios_dispatch.py` + finish the server.py decomposition (TD-5)  [P2]
> **Priority:** P2 | **Status:** planned | **Effort:** M | **Domain:** AI-Plane/Refactor | **Who:** AI-plane agent | **Source:** WS-DEBT / ADR-0011; combined tech-debt map §1 (TD-5)
**Instructions (WHAT + HOW):** Finish the half-done AI-plane decomposition. `server.py` is an **8,961-ln** god-module (VRAM scheduler + `_db_*` + auth middleware + agent streaming intermixed); the `mios_pipe/` refactor (103 files, 100% hint-tagged) never reached the 4 largest flat modules — including **`mios_dispatch.py`, the security-critical verb→bash chokepoint every verb passes through**. Extract `mios_dispatch.py` FIRST into `mios_pipe/`, then continue extracting the flat modules; replace the **9 bare `except:`** (of 558 `except Exception`); add a new drift-check "no Python file > 800 lines". Relocation ≠ decomposition — also split the 3 relocated 88–107 KB monoliths (`routing/chat.py`, `native_loop.py`, `federation/a2a.py`) where feasible. Python stays (Law 6, ML ecosystem) — the debt is the monolith, not the language.
**Where (files):** `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/mios_dispatch.py`, `usr/lib/mios/agent-pipe/mios_pipe/**` (incl. `routing/chat.py`, `native_loop.py`, `federation/a2a.py`), `automation/38-drift-checks.sh` (>800-line gate)
**When (deps/order):** Independent track (Python, pure refactor); `check_unwired_modules` confirms each extraction is live. No hard dep.
**Done When:**
- [ ] `mios_dispatch.py` is extracted and live (`check_unwired_modules` green); `server.py` shrinks toward a <800-line composition root; no bare `except:` remains; the >800-line Python gate is green.

