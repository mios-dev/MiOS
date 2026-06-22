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
