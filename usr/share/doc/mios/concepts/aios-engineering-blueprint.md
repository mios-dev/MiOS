<!-- AI-hint: The MiOS AIOS engineering blueprint -- maps the 5-phase Agentic-OS reference taxonomy (architecture / memory / orchestration / security / benchmarking) onto MiOS's ACTUAL code (every component tagged wired-live / built-gated / partial / missing with the exact module/file), cross-referenced to verified external sources (AIOS kernel, Letta/MemGPT K-LRU, Q4 KV-cache arxiv 2603.04428, MS Conductor, MCP, OWASP Agentic Top-10, CLASSic + tau-bench/SWE-bench/OSWorld). Doubles as the code-grounded gap register -> WS task roadmap. Built from a 5-agent code-grounding pass + web verification, 2026-06-21.
     AI-related: ../../../../../usr/lib/mios/agent-pipe/mios_kernel.py, ../../../../../usr/lib/mios/agent-pipe/server.py, ../../../../../usr/share/mios/mios.toml, ../../../../../Containerfile, ./aios-implementation-plan.md, ./ws-a3-surreal-to-pg-cutover.md -->
# MiOS as an Agentic Operating System — Engineering Blueprint

This document maps the standard Agentic-OS (AIOS) reference taxonomy onto MiOS's
**actual implementation**. Unlike a generic survey, every component is tagged
against real code (`wired-live` = active in the running stack · `built-gated` =
implemented but flag/VRAM/operator-gated · `partial` = core exists, central-path
wiring/coverage incomplete · `missing`) with the exact module, and cross-checked
against verified external sources. The **Gap Register** at the end is the
code-grounded roadmap (each item carries its WS task id).

Grounding method: a 5-agent code-read of the live tree (one per phase) + web
verification of every cited external claim. Status reflects the tree at
2026-06-21; the live VM may differ where operator-gated.

MiOS's thesis: an AIOS need not be a research kernel *or* enterprise middleware —
it can be an **immutable, edge-native, fully-local OS** (bootc/ostree/composefs)
whose agent plane is a kernel-shaped orchestrator behind one OpenAI-compatible
endpoint. The repo root **is** the system root; `mios.toml` is the single source
of truth; six Architectural Laws keep the image deterministic and the AI plane
unified + least-privileged.

---

## Phase 1 — Architecture: the LLM-as-CPU kernel on an immutable OS

| AIOS reference design | MiOS implementation | Status |
|---|---|---|
| LLM-as-CPU kernel: Router (intent) + Dispatcher (mode) + manager seams | `mios_kernel.py` composes Router+Dispatcher+5 manager slots; `mios_router.py` (intent→RouteDecision: chat/dispatch/multi_task/dag/agent); `mios_dispatcher.py` (mode→handler) | wired-live (Stage 1); **Stage 2 hot-path rewire pending — WS-A11/#15** |
| Scheduler Manager (anti-starvation priority) | `mios_sched.py` `PriorityGate`: per-verb priority, waiter queue, `starvation_s` aging | wired-live |
| Context Manager (token-budget packing) | `mios_ctxpack.py` `pack()` + `mios_tokenize.py` seam ([ai].tokenizer_backend) | wired-live |
| Memory Manager (pluggable recall/store) | `mios_memory.py` `MemoryProvider` ABC + `PgVectorMemoryProvider` | wired-live |
| Tool Manager (per-verb conflict/parallel-limit) | `mios_toolconflict.py` `ConflictGate` (per-verb Semaphore + conflict_group mutex; deadlock-free fixed acquire order) | wired-live |
| Access Manager (PDP: RBAC + HITL + risk tier) | `mios_pdp.py` `resolve_ceiling()` fail-closed; gates surface-build **and** dispatch | wired-live |
| Inference lanes (LiteLLM-shaped resolver) | `mios_lanes.py` `LaneResolver` + `[ai].heavy_engine` collapsing SGLang/vLLM/light; TTL health cache + per-lane cooldown, never 404s | wired-live |
| Immutable OS (bootc/ostree/composefs) | `Containerfile` single-stage bootc + bound-images bake; `kargs.d/*.toml`; `automation/40-composefs-verity.sh` ([security].composefs_mode) | wired-live |
| Multi-vendor GPU passthrough (CDI/VFIO) | `automation/41-gpu-cdi-toolkits.sh` (amd-ctk + intel-cdi), `35-gpu-passthrough.sh` (VFIO), kargs `iommu=pt`; `mios-cdi-detect` | wired-live |
| Three-projection capability surface (verbs/MCP/A2A) | `mios.toml [verbs.*]` SSOT → MCP (`ai/v1/mcp.json`, opt-in) + A2A (`[agents.*]`); `mios_manifest.py` projection | wired-live; **unify recipes/skills DAG pending — WS-2/#11** |
| Unified endpoint orchestrator | `mios-agent-pipe.service :8640` (Law-5 `MIOS_AI_ENDPOINT`); refine→route→council→dispatch→verify→polish | wired-live |

**Verdict:** MiOS realizes the Rutgers *AIOS: LLM Agent Operating System* kernel
taxonomy (Agent Scheduler / Context / Memory / Tool / Storage / Access managers)
as concrete, unit-tested modules — but, unlike a middleware framework, on a
genuinely immutable, GPU-native, fully-local OS. The one structural gap is that
the kernel decomposition is **built and tested in isolation but not yet the live
chat path** (server.py still owns the inline pipeline); WS-A11 Stage 2 is the
behind-an-interface rewire, deliberately staged because it is the central path.

---

## Phase 2 — Memory: tiers, K-LRU virtual memory, KV-cache, filesystem-as-memory

| AIOS reference design | MiOS implementation | Status |
|---|---|---|
| Hierarchical tiers (working/core/episodic/semantic) | `scratch` (working) · `agent_memory` (core) · `event`+`skill`+viking (episodic) · `knowledge` pgvector HNSW (semantic) — `postgres/schema-init.sql` | partial: core-tier (`agent_memory`) recall is tool-driven/off-by-default by the **no-context-injection** rule, not auto-recalled |
| Agentic virtual memory + K-LRU eviction (Letta/MemGPT) | `mios_evict.py` — parameterized pg K-LRU + TTL: evicts oldest, never-hot, never-satisfied, low-access rows; tiered TTL→overflow sweep | wired-live |
| Persistent quantized KV-cache context switching | `mios_kvfork.py` + `mios_kvgc.py` — llama.cpp `/slots` save/restore prefix cache + TTL/size-capped GC | wired-live (NVIDIA/llama.cpp analog of the Apple-Silicon Q4 paper) |
| Filesystem-as-memory | `mios-viking` tiered `viking://` VFS (L0/L1/L2) over skills/knowledge/memory; offline | wired-live |
| Embedding-version hygiene | `emb_model`+`emb_version` stamped on every vector (WS-A2); `mios_embed_backfill` | wired-live |
| Context compaction (rolling summary) | `mios_compact.py` deterministic planner; triggered over token budget | wired-live |
| Multi-tenant memory (owner_user + RLS) | RLS policies + `owner_user` columns exist in `schema-init.sql` | **partial — app layer doesn't `SET LOCAL mios.owner_user` per request — WS-5/#27** |

**Verdict:** MiOS's memory plane is one of its strongest areas — the K-LRU
virtual-memory paradigm (per *MemGPT*), persistent KV-cache switching (analogous
to *Agent Memory Below the Prompt*, arXiv 2603.04428 — that paper is Apple-Silicon
Q4; MiOS's NVIDIA analog is llama.cpp slot-save prefix caching), and even the
filesystem-as-memory finding are all implemented. The deliberate divergence:
core-tier recall is **tool-driven, never auto-injected**, honoring MiOS's
no-context-injection rule. The real gap is making it multi-tenant (RLS app-wiring).

---

## Phase 3 — Orchestration: deterministic vs dynamic, scheduling, sleep-time

| AIOS reference design | MiOS implementation | Status |
|---|---|---|
| Dynamic vs deterministic-DAG routing | `mios_router.py`/`mios_dispatcher.py`/`mios_kernel.py` (Stage 1) + inline DAG planner in server.py | DAG/swarm live **inline**; kernel split `built-gated` (Stage 2 — WS-A11/#15) |
| Deterministic DAG (cf. MS Conductor, zero-token routing) | server.py DAG executor (`swarm_saturate` ready-queue, `deepen_enabled`); deterministic `[routing]` lead/trail-phrase SSOT | DAG wired-live |
| OS scheduling (FIFO / RR / preemptive priority) | `mios_sched.py` FIFO+priority (live); `mios_preempt.py` RR time-slice + snapshot/restore (built) | FIFO+priority wired-live; **RR preemption not wired to the engine — WS-A12/#16** |
| Batch coalescing by (endpoint, model) | `mios_batch.py` window logic (pure) | **built-gated — server-side hold/flush not wired (native engines already continuous-batch) — #19** |
| Orchestrator-worker hop-budget guard | `mios_hopbudget.py` — via-chain loop detection + `effort_width` swarm sizing | wired-live |
| Sleep-time compute / self-improvement | `mios_selfimprove.py` analyze (observe/surface half) | **built-gated — observe-only; loop-closure + background daemon (interval_min=0) pending — WS-11/#32** |
| Recurring tasks | `mios-cron-director` daemon (5-field cron, LLM-gated rules) | wired-live |
| Remote-core escalation (cost/quality SmartRouting) | `mios_smartroute.py` decision logic + `mios_quota.py` | **built-gated — remote adapters stubbed, quality gate not orchestrated — WS-A16/#20** |

**Verdict:** Core orchestration (priority scheduling, hop-budget, DAG/swarm,
cron) is live; the higher-order schedulers (RR preemption, batch coalescing,
remote SmartRouting) and the sleep-time *act* half are built-and-tested but
flag-gated pending central-path wiring. MiOS already embodies the Conductor
insight (deterministic, zero-token routing via the `[routing]` SSOT) alongside
dynamic LLM fan-out — a hybrid, not one or the other.

---

## Phase 4 — Security: OWASP Agentic Top-10, zero-trust, sandboxing

OWASP Top-10 for Agentic Applications (2026) coverage, code-grounded:

| # | Threat | MiOS control | Status |
|---|---|---|---|
| ASI01 | Goal hijack / prompt injection | `mios_secset.py` taint set + semantic taint-firewall gating | wired-live (no ML intent-divergence detector — gap) |
| ASI02 | Tool misuse / unauthorized action | `mios_pdp.py` PDP (surface+dispatch) + `mios_toolconflict.py` | wired-live |
| ASI03 | Privilege escalation | per-verb capability ceilings | partial — **multi-user quota/RLS — WS-5/WS-6 (#27/#26)** |
| ASI04 | Supply chain / dependency poisoning | CycloneDX+SPDX SBOM (`90-generate-sbom.sh`) + passport signing | built-gated — **inbound signature verification missing** |
| ASI05 | Insecure code execution / RCE | verb gating + HITL + script cap | wired-live; **per-verb seccomp/bwrap sandbox not active — WS-A13/#22** |
| ASI06 | Insecure A2A comms | `mios_a2a_principal.py` signed principal + text-digest binding; mTLS PKI tooling | wired-live; inbound enforce wiring incomplete |
| ASI07 | Cascading/recursive calls | `mios_hopbudget.py` hop budget + loop detection | wired-live (audit captured; no real-time anomaly alert) |
| ASI08 | Memory poisoning | single-user taint + pgvector audit | partial — **multi-tenant RLS — WS-5/#27** |
| ASI09 | HITL abuse / approval bypass | `mios_hitl.py` block gate + `mios_arbiter.py` out-of-process arbiter (WS-9) | wired-live |
| ASI10 | Rogue agents / unauthorized delegation | `mios_reputation.py` peer reputation + `mios_crl.py` CRL + A2A sig | wired-live; `principal_mode='enforce'` wiring incomplete — **WS-A10/#25** |

Cross-cutting: zero-trust principal verification (`mios_principal.py` + `mios_crl.py`,
code-complete+tested), UID-scoped egress firewall (`tools/generate-egress-firewall.py`,
operator-applied), mTLS PKI provisioning (advisory, `enable=false`), fapolicyd
allow-listing (audit-mode available, enforce operator-documented).

**Verdict:** Security is broad and real — 8/10 OWASP items wired-live with the
out-of-process HITL arbiter, capability PDP, CRL/reputation federation, and
taint-firewall all live. The two material enforcement gaps are **OS-level sandbox
execution** (WS-A13: `mios_sandbox.py` decides the tier but the bwrap/seccomp
*wrapper* isn't invoked yet) and **multi-tenant isolation** (WS-5/6: RLS policies
exist but aren't activated per-request), which keep the system single-tenant-safe.

---

## Phase 5 — Benchmarking: CLASSic mapping + the capability-benchmark gap

| CLASSic dimension | MiOS instrumentation | Status |
|---|---|---|
| **C**ost | `mios_quota.py` cost model + budget | built-gated (default unlimited; remote adapters stubbed) |
| **L**atency | `mios_trace.py` per-request spans | wired-live (real-time; no historical percentile dashboard) |
| **A**ccuracy | `var/lib/mios/evals/` (domain knowledge eval) | wired-live for MiOS-domain; **no SWE-bench/OSWorld/τ-bench runner — missing** |
| **S**tability | `mios_stress.py` load harness + circuit breaker | wired-live (no SLA history) |
| **S**ecurity | `automation/38-drift-checks.sh` (11 checks) + `38-ssot-lint` + `99-postcheck` | wired-live (build-time; no runtime assertion fw) |

Plus: HITL validation (`mios_hitl` + arbiter), per-request tracing, SSOT
round-trip drift detection, and module-test-coverage gate (drift-check 11 —
every `mios_*.py` ships a unit test).

**Verdict + the closing gap:** MiOS has the *operational* CLASSic stack (cost,
latency, stability, security, build-time fitness gates). The capability-benchmark
gap is now **partially closed**: `mios_bench.py` + `mios-bench` (committed) provide
the research-grounded scoring core — unbiased `pass@k`, τ-bench `pass^k` ("all k
succeed", arXiv 2406.12045), the i.i.d. `p**k` reliability form, and the CLASSic
rollup — with an offline `score` mode (any results JSON) and a `run` mode that
drives the agent-pipe endpoint. **Remaining:** the live trial execution + curated
task suites (τ-bench / OSWorld subset against the computer-use verbs) need the VM
endpoint + external datasets — the scoring half is done and unit-tested (35
asserts).

---

## Gap Register → roadmap (code-grounded; maps to WS tasks)

| Gap | Owner task | What remains (offline-authorable vs VM-loop) |
|---|---|---|
| Kernel Stage-2 hot-path rewire | WS-A11/#15 | central-path: delegate `chat_completions`→`kernel.handle()`; VM-verify (staged, see ws-decompose-stage2-plan) |
| RR time-slice preemption wiring | WS-A12/#16 | wire `mios_preempt` to engine (snapshot/restore via `/slots`); VM-verify |
| Remote SmartRouting + quality gate | WS-A16/#20 | implement remote lane adapters + orchestrate score gate; needs remote keys |
| Risk-tier sandbox **enforcement** | WS-A13/#22 | argv-builder `mios_sandbox.build_bwrap_argv` DONE (web-verified flags, 14 asserts); remaining = `exec` it + seccomp + workspace mkdir from dispatch; VM-verify (security-critical) |
| Principal `enforce` + inbound auth | WS-A10/#25 | ASGI auth middleware + `principal_mode=enforce` path; VM-verify |
| Multi-tenant RLS app-wiring | WS-5/#27 | `SET LOCAL mios.owner_user` per request + principal extraction |
| Per-user quota keying/persistence | WS-6/#26 | key `mios_quota` on verified principal + persist |
| Capability registry unification | WS-2/#11 | structured recipes/skills DAG + one RBAC-filtered manifest + generative refusal |
| pods→.pod quadlets / k3s bridge | WS-7/#28 | `.pod` quadlet gen; k3s regen-diff needs live pods (VM) |
| Gossip/DHT federated discovery | WS-A18/#30 | discovery transport over `mios_reputation` |
| Self-improve loop closure | WS-11/#32 | background daemon (interval) + replay-gated *act* half |
| Capability-benchmark harness | (new) | scoring core DONE (`mios_bench` + `mios-bench`: `pass@k`/`pass^k`/CLASSic, 35 asserts); remaining = live trial run + task suites (τ-bench/OSWorld) against :8640 (VM) |
| VLM perception→act→verify | WS-8/#12 | ground a VLM lane + unify computer-use; VM helper |
| Port-literal SSOT collapse | WS-0B/#5 | `.service` env can't `${}`-expand — VM-build-loop |

The recurring shape: **the pure cores are built + unit-tested; what remains is
central-path wiring that must be verified live in the `just build` → boot loop**
(the operator's domain — this assistant builds/launches nothing). Where a gap is
fully offline-authorable (registry unification, sandbox wrapper, quota keying,
benchmark harness), it can be staged as a flag-gated, inert-until-enabled module
following the established sibling-module pattern.

---

## References (web-verified 2026-06-21)

- **AIOS: LLM Agent Operating System** (Mei et al.) — the kernel taxonomy (Agent
  Scheduler / Context / Memory / Tool / Storage / Access managers). arXiv.
- **MemGPT / Letta** — agentic virtual memory + tool-driven paging/eviction. arXiv.
- **Agent Memory Below the Prompt: Persistent Q4 KV Cache…** — [arXiv 2603.04428](https://arxiv.org/abs/2603.04428)
  (Apple-Silicon Q4; MiOS analog = llama.cpp slot-save). Latency figures are the
  paper's (M4 Pro), NOT MiOS measurements.
- **Microsoft Conductor** — deterministic YAML+Jinja2 zero-token DAG routing.
  [github.com/microsoft/conductor](https://github.com/microsoft/conductor) ·
  [MS Open Source blog](https://opensource.microsoft.com/blog/2026/05/14/conductor-deterministic-orchestration-for-multi-agent-ai-workflows/)
- **CLASSic framework** (Cost/Latency/Accuracy/Stability/Security) — [Aisera](https://aisera.com/blog/ai-agent-evaluation/) ·
  *Beyond Accuracy* [arXiv 2511.14136](https://arxiv.org/html/2511.14136v1)
- **τ-bench** (`pass^k` reliability) — [arXiv 2406.12045](https://arxiv.org/abs/2406.12045);
  SWE-bench Verified (500); OSWorld (369 tasks); WebArena.
- **Model Context Protocol (MCP)** — Anthropic; tool-poisoning + gateway ACLs.
- **OWASP Top 10 for Agentic Applications (2026)** — ASI01–ASI10.
- **bootc / ostree / composefs**, **CDI / VFIO**, **fapolicyd**, **gVisor**,
  **Firecracker** — standard immutable-OS + isolation building blocks.

> Companion docs: `aios-implementation-plan.md` (workstream sequencing),
> `ws-a3-surreal-to-pg-cutover.md` + `ws-a3-central-path-cutover-worklist.md`
> (the memory/DB cutover), `ws-decompose-stage2-plan-2026-06-20.md` (kernel Stage-2).
