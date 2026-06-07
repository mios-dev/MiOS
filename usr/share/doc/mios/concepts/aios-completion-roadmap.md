# MiOS → complete AIOS: research synthesis + continuation roadmap (2026-06-07)

Synthesis of four cited research passes (AIOS reference architecture; kernel resource
management; tool + federation layer; safety/governance/reliability) against MiOS's
current state. **Verdict: MiOS already implements the canonical AIOS six-manager
kernel + LLM-syscall discipline and meets or exceeds table-stakes on ~13 of 16
components.** The gaps to be a *complete* AIOS by the 2025-26 reference are
concentrated, defined, and mostly additive.

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

## Complete-AIOS checklist — MiOS status
PRESENT (≥ reference): LLM-core abstraction (llama.cpp+llama-swap, OpenAI Tier-0/1/2
+/v1/responses) · Context Manager (`_kv_paging`/`_kv_slot_action` KV snapshot/restore
+ `mios_kvfork` prefix-fork) · Storage Manager (pgvector durable + cosine recall) ·
Tool Manager server side (82 verbs+recipes+skills, 3-projection catalog, tool_search) ·
Multi-agent orchestration (swarm decompose→synthesis, priority gate) · MCP **serve** +
A2A **publish** · HITL + determinism-replay · request-cancellation · self-improvement
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
   (delegate to a peer) are wired but dormant (vendor-empty `mcp.json`/`a2a-peers.json`).
   Self-test loop: register **MiOS's own** A2A card + MCP endpoint in the overlays →
   verify the client round-trips (A2A Message→Task→Artifact; MCP tools/list+tools/call)
   → then a 2nd MiOS node over Tailscale. Turns a remote node into a real swarm worker.

### P2 — high value, additive
3. **Memory self-edit + pressure-flush (MemGPT/Letta).** Expose `memory_append` /
   `memory_replace` verbs (agent-curated pinned pgvector tier) + a 70%/100%-of-`n_ctx`
   trigger that evicts oldest FIFO turns and writes a **recursive summary** into the
   scratchpad head. Complements (doesn't replace) KV-paging. Basis: arXiv:2310.08560.
4. **Semantic firewall (CaMeL-class).** Provenance/taint tag on every tool result
   carried through the scratchpad; a policy gate in `dispatch_mios_verb` that blocks a
   **side-effecting** verb driven by **tainted** (untrusted web/RAG) data without HITL
   approval (wire to the existing HITL queue). Policies in mios.toml SSOT (no hardcoded
   deny-lists). Basis: dual-LLM/CaMeL (arXiv:2503.18813), OWASP LLM01/LLM06.
5. **Code-mode for heavy verbs/recipes.** Route multi-step verb chains + the recipe
   layer through a sandboxed code-exec lane so intermediate blobs (web corpora, file
   contents, DB rows) stay out of model context; only filtered results return. Basis:
   Anthropic code-execution-with-MCP (98.7% token cut), Cloudflare Code Mode.

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
The historic gap — the AIOS *kernel* — has largely closed this and prior sessions. The
single highest-leverage move is **P1#1 (turn-boundary preemption)** because both halves
exist and only need wiring; the single most *strategic* move is **P1#2 (federation
consume)** because it converts MiOS from a one-operator ensemble into a true federated
agent OS. Everything in P1–P3 is additive + fail-safe; only P4 needs the operator.

Sources: AIOS arXiv:2403.16971 · Cerebrum arXiv:2503.11444 · MemGPT arXiv:2310.08560 ·
vLLM/PagedAttention arXiv:2309.06180 · CaMeL arXiv:2503.18813 · Voyager arXiv:2305.16291 ·
MCP (modelcontextprotocol.io) · A2A (a2a-protocol.org) · AGNTCY (docs.agntcy.org) ·
Anthropic code-execution-with-MCP / multi-agent-research · OTel GenAI semconv.
