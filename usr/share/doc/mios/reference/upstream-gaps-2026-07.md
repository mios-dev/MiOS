<!-- AI-HINT: Prioritized upstream-vs-MiOS gap report (2026-07). Grounded in a 44-item research pass across 7 subsystems (inference lanes, pgvector-RAG, agent orchestration/MCP, bootc-OCI, embeddings, security/egress, GPU/CDI/VFIO, Windows DISM). Each gap cites the upstream source + the exact MiOS file/line that lags. Use the Top-10 table for sequencing; do not invent gaps beyond what is cited here. -->

# Upstream-vs-MiOS Gap Report — 2026-07

This report consolidates a 44-item research pass comparing MiOS against current upstream practice across seven subsystems. Overlapping findings have been merged (notably the two cross-encoder-reranking entries), and speculative or already-satisfied items dropped; every remaining gap is grounded in a specific upstream source and an exact MiOS file/line that lags it.

Severity reflects impact on the single-operator, shared-4090, continuously-available agent-plane mandate. Effort is a rough sizing: **S** = a flag/config flip, **M** = a bounded feature, **L** = a subsystem, **XL** = a cross-cutting build/boot-chain track.

## Top 10 highest-leverage gaps

| # | Subsystem | Gap | Upstream source | Severity | Effort |
|---|-----------|-----|-----------------|----------|--------|
| 1 | inference-lanes | FP8 KV cache missing → KV capacity halved, forced max_model_len below the 128k mandate | vLLM/SGLang `--kv-cache-dtype fp8` | high | S |
| 2 | inference-lanes | vLLM heavy lane pinned to legacy V0 engine (`v1_engine=false`) — V0 removed in vLLM 0.11 | vLLM V1 engine (default since 0.8, V0 removed 0.11) | high | S |
| 3 | bootc-oci | Cosign signature policy stale + internally unsatisfiable → CI signing not actually enforced on `bootc upgrade` | Sigstore cosign keyless + containers-policy.json | high | S |
| 4 | pgvector-rag | No hybrid BM25+vector fusion on memory/RAG recall despite hybrid-capable schema | RAG SOTA dense+sparse + RRF | high | M |
| 5 | pgvector-rag / embeddings | No cross-encoder reranking stage on knowledge/RAG retrieval (merged finding) | bge-reranker-v2-m3 / Qwen3-Reranker | high | M |
| 6 | embeddings-models | Embedding call path sends raw text — no EmbeddingGemma query/document task prefixes | EmbeddingGemma-300m required prompt templates | high | M |
| 7 | embeddings-models | Model swapped nomic→EmbeddingGemma under same name AND same emb_version → two vector spaces collide | Embedding-version hygiene (MiOS's own WS-A3) | high | M |
| 8 | inference-lanes | No speculative decoding on heavy lanes — biggest remaining single-stream latency lever | vLLM EAGLE-3 / SGLang EAGLE3 | high | M |
| 9 | bootc-oci | bootc soft-reboot unused → every userspace-only update hard-reboots the whole agent plane | `bootc upgrade --soft-reboot=auto` | high | M |
| 10 | security-egress | Every runtime security control ships default-off (degrade-open) — no secure-by-default baseline | Secure-by-default (Codex CLI, Tigera/Datadog guidance) | high | M |

---

## inference-lanes

Scope: vLLM :8441 / SGLang :8442 heavy lanes + llama.cpp/llama-swap :8450 light lane.

### 1. FP8 KV cache missing on both heavy lanes (high, S)
- **Upstream:** vLLM `--kv-cache-dtype fp8` (fp8_e5m2/e4m3) and SGLang `--kv-cache-dtype fp8_e5m2` roughly double concurrent KV capacity on Ada/Hopper — a documented, recommended 24GB-fit technique (docs.vllm.ai optimization guide, V1 guide).
- **Current MiOS state:** FP8 KV is deferred. `usr/share/mios/mios.toml:6673` comment ("pair with --kv-cache-dtype fp8 to fit 131072") and `:6690` both acknowledge it, but no `kv_cache_dtype` key exists in `[ai.vllm]` or `[ai.sglang]`; the lanes run BF16/FP16 KV.
- **Recommendation:** Add `kv_cache_dtype = "fp8"` (fp8_e5m2 on Ada) to both `[ai.vllm]` and `[ai.sglang]`, render into the Quadlet args, and raise `max_model_len` back toward 131072 once verified. Highest-value VRAM-fit change; unblocks the 128k mandate the config already documents as blocked.

### 2. vLLM heavy lane pinned to legacy V0 engine (high, S)
- **Upstream:** vLLM V1 has been default since v0.8.0 (Jan 2025); V0 was frozen June 2025 and fully removed in v0.11.0 (Oct 2025). V1 gives chunked-prefill-by-default, prefix caching, and spec decode under one scheduler (docs.vllm.ai/en/stable/usage/v1_guide, RFC #18571).
- **Current MiOS state:** `usr/share/mios/mios.toml:6675`: `v1_engine = false  # --v1: enable modern vLLM V1 engine`. On a current vLLM image this forces a removed code path (fails to start on >=0.11) or is a stale no-op; the `--v1` flag comment does not match how V1 is now selected (`VLLM_USE_V1`, now implicit).
- **Recommendation:** Set `v1_engine = true` (or drop the flag and pin vLLM >=0.11 so V1 is implicit). Remove the `--v1` literal from whatever renders `MIOS_VLLM_*`; verify the Quadlet no longer passes a V0-only arg. Gives chunked-prefill-by-default with zero model changes.

### 3. No speculative decoding on either heavy lane (high, M)
- **Upstream:** vLLM EAGLE-3 via `--speculative-config` (up to ~2.5x end-to-end; Red Hat "Fly Eagle3 fly" Jul 2025) plus n-gram proposals needing no draft model; SGLang `--speculative-algorithm EAGLE3 --speculative-draft-model-path` with Spec-V2 overlap scheduling.
- **Current MiOS state:** `[ai.vllm]` (`mios.toml:6668-6675`) and `[ai.sglang]` (`:6683-6692`) expose gpu_util, prefix_caching, parsers, HiCache, unified-radix-tree — but no `speculative_algorithm`/`draft_model`/`num_speculative_tokens` key at all. The Quadlets serve pure autoregressive decode.
- **Recommendation:** Add a spec-decode block rendered into `MIOS_VLLM_*`/`MIOS_SGLANG_*` (e.g. `spec_algo='eagle3'`, `draft_model=...`, `num_spec_tokens=3`). Pick an EAGLE3 head matching the served heavy model (Qwen3/Magistral have public checkpoints); fall back to n-gram (vLLM) for the zero-extra-VRAM path on code/repetitive turns. Ship disabled-by-default like the lanes themselves.

### 4. SGLang lane runs `--disable-cuda-graph` (high, M)
- **Upstream:** SGLang CUDA graph is on by default and reduces kernel-launch overhead for materially better decode throughput. The recommended path for VRAM pressure is FP8 KV + mem-fraction tuning, not disabling CUDA graph.
- **Current MiOS state:** `mios.toml:6690` describes the live lane as "the 8B + --disable-cuda-graph lane" — the validated config sacrifices CUDA-graph decode to avoid OOM at higher context.
- **Recommendation:** Drop `--disable-cuda-graph`, add `--kv-cache-dtype fp8` (gap 1) and tune mem_fraction to reclaim headroom; keep `--cuda-graph-max-bs` modest for a single-user lane. If a specific backend truly needs it off, gate behind a documented `[ai.sglang]` toggle instead of baking it in.

### 5. llama.cpp light lane disables prompt-prefix cache reuse (medium, S)
- **Upstream:** llama-server `--cache-reuse N` reuses a matching KV prefix across requests; the standard single-user pattern is a non-zero reuse window plus `--parallel`/`--np` for shared-prefix concurrency.
- **Current MiOS state:** `usr/share/mios/llamacpp/mios-llm-light.yaml:65` and `:121` both serve `--parallel 1 --cache-reuse 0`, while adjacent comments (`:58`, `:90`) explicitly prescribe "CONV-04: --cache-reuse 256 ... --np 4". The literal cmd was never updated to match the note — every chat/refine turn reprocesses the shared system-prompt prefix from scratch.
- **Recommendation:** Change the granite4.1:8b and lfm2:700m cmd lines to `--cache-reuse 256` (and `--np 4`). Low risk, immediate TTFT win on every agent turn.

### 6. llama.cpp light lane uses no speculative decoding (medium, M)
- **Upstream:** llama.cpp speculative decoding via `--model-draft` / `--spec-type {draft-simple,draft-eagle3,draft-dflash,ngram-cache}` + `--spec-draft-n-max`. ngram-cache needs no draft model and helps code/repetitive output; a same-tokenizer small draft gives ~2x on decode.
- **Current MiOS state:** `mios-llm-light.yaml:118-124` (granite4.1:8b) has flash-attn and q8_0 KV but no `--model-draft`/`--spec-type`; the resident group (`:191-199`) co-loads only granite + lfm2 + embed, with lfm2 (different family/tokenizer) unusable as a Granite draft.
- **Recommendation:** Add `--spec-type ngram-cache` to the granite/coder lane first (zero extra VRAM), or provision a same-tokenizer Granite-family draft GGUF and wire `--model-draft --spec-draft-n-max`. Gate behind an `[ai.spec]`-style toggle so 8GB profiles can skip it.

---

## pgvector-rag

### 7. No hybrid BM25+vector fusion on recall (high, M)
- **Upstream:** Hybrid dense+sparse with Reciprocal Rank Fusion is the de-facto production standard (StackAI/Atlan advanced-RAG guides 2026); pgvector 0.8.x supports parallel tsvector + HNSW queries fused app-side. MiOS already ships an RRF implementation (`rerank_rrf_k=60`) in `usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py` — but only for tool-surface selection.
- **Current MiOS state:** `mios_pipe/memory/pg.py` `build_recall()` emits only `ORDER BY emb <=> %(qvec)s::vector LIMIT k`; the `knowledge.fts` GIN index (`usr/share/mios/postgres/schema-init.sql:44`) is never queried; `mios_rag` (`schema-init.sql:445-451`) and `usr/libexec/mios/mios-rag` cmd_query do raw top-k cosine with no lexical arm. Lexical/exact-match signal (identifiers, error codes, rare tokens) is lost.
- **Recommendation:** Add an `fts` generated tsvector + GIN index to `mios_rag`; run a parallel `websearch_to_tsquery('simple', ...)` ranked query alongside the vector query and RRF-fuse the rank lists (reuse the existing `rerank_rrf_k=60` helper). Keep degrade-open so a missing FTS arm falls back to pure cosine.

### 8. No cross-encoder reranking stage on knowledge/RAG retrieval (high, M) — merged
> Merges the two research entries on cross-encoder reranking (pgvector-rag and embeddings-models). The current "rerank" is a metadata blend (`_blend_rank`), not a relevance reranker; mios_rag returns raw cosine top-k.
- **Upstream:** Cross-encoder rerankers yield +10–48% NDCG@10 (Databricks/Pinecone 2025); Anthropic Contextual Retrieval pairs contextual embeddings with a reranker for up to 67% fewer retrieval failures. Servable options: bge-reranker-v2-m3 (~568M, GGUF, llama.cpp `--reranking`) or Qwen3-Reranker-0.6B (Apache-2.0, 32k ctx) at ~0.4–0.6 GB q8_0.
- **Current MiOS state:** `mios_pipe/memory/pg.py` `recall`/`build_recall` (~L615) returns `ORDER BY emb <=> qvec LIMIT k` with only an app-side threshold; `knowledge` reranks via `_blend_rank` in `mios_pipe/memory/knowledge.py` (metadata only). The cross-encoder is documented but default-OFF and scoped only to tool dispatch (`mios.toml:2020-2023`, `rerank_xenc`); the mios-llm-light `--reranking` lane is not provisioned.
- **Recommendation:** Provision the bge-reranker-v2-m3 (or Qwen3-Reranker-0.6B) `--reranking` GGUF lane, join the resident group (~0.5 GB), and add an over-fetch (k*4, ~60 already fetched) → cross-encoder rerank → top-k stage to `_recall_knowledge_pg` and mios-rag cmd_query. Default it ON for RAG recall the way `tool_rerank` is for tools, gated by an SSOT flag so it degrades to the blend/cosine path when the lane is absent.

### 9. All embedding columns are full-fat `vector(768)`, halfvec unused (medium, M)
- **Upstream:** pgvector 0.8.x `halfvec` + `halfvec_cosine_ops` HNSW: ~50% storage reduction and faster index build at negligible recall cost even well under 2000 dims (Neon "don't use vector, use halfvec" 2025; jkatz05.com quantization writeup).
- **Current MiOS state:** `schema-init.sql:9-11` comment ("768 < pgvector's 2000-dim HNSW limit ... so no halfvec needed") incorrectly conflates the dimension ceiling with the storage/perf rationale; all emb columns are `vector(768)` (knowledge:26, agent_memory:68, mios_rag:449, config_kv:561, plus WS-VECTOR skill/verb/event/tool_call/directory_entry/session/build-catalog tables:618-788).
- **Recommendation:** Migrate emb columns to `halfvec(768)` with HNSW `halfvec_cosine_ops`, and cast the query vector `::halfvec` in build_recall/mios-rag. Do it behind a schema/emb_version bump so the embed-backfill re-stamps rows; keep `vector(768)` as fallback for any table showing recall regression.

### 10. Naive fixed-size chunking with no context enrichment; destructive re-ingest (medium, L)
- **Upstream:** Anthropic Contextual Retrieval (2024): prepend an LLM-generated per-chunk context blurb before embedding → up to 49% (with rerank, 67%) fewer failures. Jina late chunking: embed the full doc then pool chunk spans to retain cross-chunk context.
- **Current MiOS state:** `usr/libexec/mios/mios-rag` `_chunks()` is fixed 700-char paragraph splitting (CHUNK_CHARS=700, OVERLAP=150); cmd_ingest TRUNCATEs `mios_rag` and re-embeds every file every run — no incremental update, no context prefix, no semantic/late chunking.
- **Recommendation:** Add an optional contextual-retrieval pass (1–2 sentence chunk context via mios-llm-light, prepended before embedding) and/or late chunking; make ingest incremental (hash per source, re-embed only changed files) instead of TRUNCATE+rebuild.

### 11. No query transformation before retrieval (medium, M)
- **Upstream:** Advanced-RAG 2025 standard: query rewriting, HyDE, and multi-query fan-out + RRF materially raise recall, especially for chat-style follow-ups (Atlan "12 Advanced RAG Techniques" 2026).
- **Current MiOS state:** `mios_pipe/memory/knowledge.py` `_recall_knowledge_pg` and mios-rag embed the query as-is (`await _embed_one(query)`); the only pre-processing is `_recall_floor()`'s possessive heuristic and the `_shares_anchor` topical guard — no LLM rewrite/expansion.
- **Recommendation:** Add an optional, default-off LLM query-rewrite/HyDE step (mios-llm-light) that expands the retrieval query, or a multi-query fan-out whose result lists are RRF-fused, before embedding — reusing the existing RRF constant. Skip for volatile/latency-critical turns.

### 12. No quantized two-stage retrieval option (low, L)
- **Upstream:** pgvector 0.8.x binary quantization via `bit` + `bit_hamming_ops` HNSW with a full-precision rescore pass — large index-size/latency reductions at scale, rescore recovering recall (jkatz05.com; pgvector 0.8.0 notes).
- **Current MiOS state:** No use of `bit`/`bit_hamming_ops`, `sparsevec`, or coarse-then-rescore anywhere in `schema-init.sql` or `mios_pipe/memory/pg.py`; all recall is single-stage full-precision cosine.
- **Recommendation:** For larger tables (event, tool_call, directory_entry, knowledge at scale) add an optional binary-quantized HNSW expression index used as a coarse first stage, then rescore top candidates against the halfvec/vector column. Keep default-off until corpus size justifies it.

---

## agent-orchestration

### 13. MCP consumer ignores resources / prompts / sampling (high, L)
- **Upstream:** MCP spec 2025-11-25: resources, prompts, and sampling are core client capabilities (2025-11-25 adds sampling tool-calling). Reference TS/Python SDKs implement full handlers.
- **Current MiOS state:** `mios_pipe/federation/mcp.py`: `_mcp_probe_server` (L476-527) and `_mcp_probe_stdio` (L384-440) call only initialize + tools/list; `_mcp_call_tool` (L546-573) forwards only tools/call. Docstring L24-27 scopes resources/prompts/sampling as unimplemented. MiOS publishes resources (`http_caps.py /v1/resources`) but never consumes a peer's.
- **Recommendation:** On probe, also call resources/list and prompts/list and register them into a peer catalog (alongside the `mcp.<server>.<tool>` namespace); add resources/read and prompts/get forwarders; register a `sampling/createMessage` handler routing the server's request to `MIOS_AI_ENDPOINT` (local lanes are an ideal sampling backend) behind the existing permission/arbiter gate.

### 14. No MCP elicitation handler (medium, M)
- **Upstream:** MCP 2025-06-18 (elicitation) + 2025-11-25 (URL-mode elicitation for OAuth/credential/payment): `elicitation/create` is a server→client request the client answers by prompting the user.
- **Current MiOS state:** No `elicitation/create` handler anywhere in `mios_pipe/federation/mcp.py` (grep: zero hits). A complete HITL stack sits unused for this: `mios_pipe/access/hitl.py` + `hitlflow.py`. Remote tools that need a missing param or confirmation mid-call fail or hang.
- **Recommendation:** Add an `elicitation/create` handler that bridges to `access/hitl.py`: render the server's requestedSchema as a HITL prompt, gate URL-mode elicitations through the arbiter/policy, and return the accept/decline/cancel envelope the spec defines.

### 15. No OAuth 2.1 resource-server flow for remote MCP servers (medium, M)
- **Upstream:** MCP 2025-06-18 (OAuth authorization, server as resource server) + 2025-11-25 (OIDC discovery + incremental scope consent).
- **Current MiOS state:** `mios_pipe/federation/mcp.py` `_mcp_render_headers` (L154-162) only substitutes `${ENV_VAR}` into static bearer headers; `_mcp_http_rpc` (L165-198) sends them verbatim with no 401 challenge, token cache, or refresh. MiOS cannot consume hosted/authenticated remote servers requiring an interactive grant.
- **Recommendation:** Add an OAuth resource-server path: on a 401 with WWW-Authenticate, run OIDC discovery + (dynamic) client registration, drive the auth-code/device grant through the elicitation/HITL bridge (gap 14), cache+refresh tokens per server id, and request incremental scopes as tools demand them.

### 16. MCP tool results treated as opaque; no structured output / Tasks (medium, M)
- **Upstream:** MCP 2025-06-18 (structured tool output: outputSchema + structuredContent) + 2025-11-25 (Tasks: track long-running work, poll status, retrieve results).
- **Current MiOS state:** `mios_pipe/federation/mcp.py` registers only inputSchema (L508-518, L424-433 — no outputSchema); `_mcp_call_tool` (L546-573) returns `resp['result']` raw with a hard 120s timeout and no task polling. The A2A half already implements a full task lifecycle (`federation/a2a.py` `_A2A_TASKS`, L990+) — the two federation surfaces are asymmetric.
- **Recommendation:** Capture outputSchema at registration and validate/normalize structuredContent on tools/call (reuse existing strict-schema validation); detect a Tasks-style pending result and poll to completion instead of blocking a single call, mirroring the A2A task store.

### 17. DAG planner is not constrained-decoded (medium, M)
- **Upstream:** 2025-2026 structured-output SOTA: strict json_schema + constrained decoding (Outlines/vLLM guided_json, llama.cpp GBNF/json_schema) drives schema-adherence failures below 0.1% vs 2–5% for plain JSON mode.
- **Current MiOS state:** `mios_pipe/routing/planner.py:400` uses `response_format {type: json_object}` then leans on lenient JSON salvage; the strict pattern already exists in `routing/classify.py:105-117` (json_schema + strict:true + enable_thinking:False, gated `MIOS_ROUTER_STRUCTURED`). A malformed plan silently falls through, losing the whole decomposition.
- **Recommendation:** Give `decompose_intent` a strict json_schema for the DAG (nodes[] with tool enum-constrained to `_VERB_CATALOG` keys, agent enum-constrained to `_AGENT_REGISTRY` keys, deps as string arrays) plus `chat_template_kwargs enable_thinking:False`, reusing the classify.py pattern; keep lenient salvage as fallback.

### 18. Flat always-on memory — no tiering, decay, or procedural tier (medium, L)
- **Upstream:** Agent-memory SOTA 2026 (Letta/MemGPT, Mem0, Zep): episodic/semantic/procedural taxonomy + small always-in-context core + retrieval layer + explicit forgetting/decay + recency/temporal weighting.
- **Current MiOS state:** `mios_pipe/memory/memory.py` default `PgVectorMemoryProvider.retrieve` (L56-57) is verbatim cosine recall with no decay/tier/forgetting; the Letta core/archival backend (L100-219) is present but default-OFF (`memory_backend` defaults 'false', L210-213). No procedural tier, no eviction/decay job — stale/superseded facts accumulate and compete with fresh ones.
- **Recommendation:** Add recency/decay scoring to recall ranking, a periodic forgetting/consolidation job (demote or summarize stale rows), and a distinct procedural-memory scope for learned tool-use patterns; consider promoting the Letta tiered backend to the default managed path.

---

## bootc-oci

### 19. bootc soft-reboot unused (high, M)
- **Upstream:** `bootc upgrade --soft-reboot=auto` (GA in RHEL 10 image mode, Nov 2025; bootc #1350) uses systemd soft-reboot + `/run/nextroot` so a no-kernel-change update re-emerges in seconds without touching the running kernel; `auto` falls back to hard reboot when kernel/kargs changed.
- **Current MiOS state:** `automation/43-uupd-installer.sh` enables `uupd.timer` running a plain `bootc upgrade` and disables the native timers; a repo-wide grep for soft-reboot/nextroot in `automation/*.sh` finds zero hits. No mios.toml knob; `bootc.md` command table omits `--soft-reboot`. Every userspace-only update cold-starts mios-llm-*, agent-pipe, Hermes and pgvector — undercutting the continuously-available pitch.
- **Recommendation:** Add a `[updates] soft_reboot = "auto"` knob and wire uupd/bootc to pass `--soft-reboot=auto` on apply (uupd forwards bootc flags). Split kernel vs userspace deltas so agent-plane downtime drops from a full reboot to seconds on the common case; keep greenboot health-gating on the nextroot swap.

### 20. Container signature policy stale + internally unsatisfiable (high, S)
- **Upstream:** Sigstore cosign keyless + containers-policy.json(5) sigstoreSigned: for a scope, all array requirements must be satisfied, and the Fulcio identity must match the certificate SAN (the actual workflow ref).
- **Current MiOS state:** `usr/lib/containers/policy.json` for `ghcr.io/mios-dev/mios` (a) points the keyless Fulcio identity at `.../build.yml@refs/heads/main` under repo `MiOS-DEV/MiOS`, but the real workflow is `.github/workflows/mios-ci.yml` on repo `mios-dev/MiOS` — the SAN won't match; and (b) ANDs a keyed `mios-cosign.pub` requirement that CI never produces (CI signs keyless-only, `cosign sign --yes`, no `--key`). `automation/42-cosign-policy.sh` installs this verbatim, so CI signing is not enforced on `bootc upgrade`.
- **Recommendation:** Fix the Fulcio identity to a certIdentityRegExp/subjectRegExp matching the real `mios-ci.yml@refs/heads/main` (correct repo casing), and either drop the unproducible keyed requirement or actually emit a keyed signature in CI. Add a drift-gate check that the policy identity matches the live signing workflow.

### 21. No OS-level factory-reset / recovery path (medium, M)
- **Upstream:** bootc experimental `install reset` — non-destructive factory reset that provisions a fresh stateroot from the current image while preserving user data (bootc #404). Complements `systemd factory-reset.target`.
- **Current MiOS state:** `usr/libexec/mios/mios-day0-reset` header: "not a 'factory reset' — the host stays fully provisioned"; it wipes only AI DB tables and runtime dirs. No `bootc install reset` wiring, no `factory-reset.target` unit, no mios verb exposing an OS reset. Returning to a clean image state requires a full BIB reinstall.
- **Recommendation:** Ship an OS-reset path on `bootc install reset --experimental` (behind a mios.toml flag and an explicit `mios reset --os` verb) plus a factory-reset.target hook. Keep mios-day0-reset as the lighter AI-state-only tier.

### 22. composefs is verity-only (tamper-evident, not tamper-proof) (medium, XL)
- **Upstream:** bootc experimental composefs-native backend (#1190) + "sealed images" = composefs root digest embedded in a Secure-Boot-signed UKI, via `[composefs] enabled = signed` + keypath, for a cryptographic boot chain (All Systems Go 2025).
- **Current MiOS state:** `automation/40-composefs-verity.sh` writes `[composefs] enabled = verity` (never `signed`); `23-uki-render.sh` only flattens kargs into `/usr/lib/kernel/cmdline` and defers actual `ukify build` to a CI pipeline that does not do it. `mios.toml [security]` (~line 6625) files signed/sealed images as an unimplemented "Day-N+1" item. The composefs.md doc overstates the posture as "require fs-verity signatures on every file", which verity mode does not provide.
- **Recommendation:** Stand up the sealed-image track: build a signing key, switch prepare-root.conf to `enabled = signed` on bare-metal targets, generate a real signed UKI embedding the composefs digest, and gate on Secure Boot — turning the already-produced cosign identity into an enforced boot root-of-trust. Correct the composefs.md claim in the interim.

### 23. Bound-images implementation diverges from bootc-native LBI lifecycle (medium, M)
- **Upstream:** bootc LBI doc (2025): bootc auto-pulls discovered LBIs into bootc-owned `/usr/lib/bootc/storage` on install and re-manages them on every `bootc upgrade`, honoring the Image field of `.image`/`.container` units.
- **Current MiOS state:** Containerfile final RUN (~L156-221) loops over `/usr/lib/bootc/bound-images.d/*.container` and `podman --root /usr/lib/containers/storage pull`s each Image=, expanding `${VAR:-default}` fallbacks inline; storage lives in an additionalimagestore, not bootc's. Bound images are `.container`, not `.image`, and tags float — frozen at build time (the root cause behind open task #12).
- **Recommendation:** Pin every bound Image= to a digest (kills #12 non-determinism), and adopt bootc-native LBI: `.image` Quadlets resolved into `/usr/lib/bootc/storage` so bootc versions/pre-stages them atomically with the OS on upgrade.

### 24. No sysext/confext runtime extensions — monolithic ~50GB image (medium, L)
- **Upstream:** systemd-sysext(8)/confext(8) extend /usr+/opt and /etc at runtime from `.raw` images without rebuilding the base (Fedora sysexts project; bootc guidance recommends sysext for optional/large components).
- **Current MiOS state:** `tools/mios-sysext-pack.sh` exists (packs into `/usr/lib/extensions/mios-accelerator.raw`) but the Containerfile leaves its RUN commented out as a no-op ("current build is FHS-overlay-only"). No confext usage; /etc deltas ride the monolithic image (~21 baked bound images, ~50GB).
- **Recommendation:** Move optional/heavy subsystems (heavy inference lane, GPU CDI toolkits, dev tooling) into sysext `.raw` images merged via systemd-sysext.d, and use confext for togglable /etc deltas — shrinking the base and letting operators layer/unlayer without a rebuild. Re-enable the mios-sysext-pack RUN once a source tree is staged.

---

## embeddings-models

### 25. Embedding call path sends raw text — no task-prompt prefix (high, M)
- **Upstream:** google/embeddinggemma-300m (Sept 2025; arXiv 2509.20354) requires prompt templates — queries use `task: search result | query: {q}`, documents use `title: none | text: {doc}`. nomic-embed-text similarly mandates `search_query:`/`search_document:` prefixes. MTEB numbers assume these templates.
- **Current MiOS state:** `usr/lib/mios/agent-pipe/server.py` `_embed_one` (~L7232) posts `{"input": text}` verbatim; `var/lib/mios/embeddings/ingest_local.py` `embed_batch` (~L52) posts raw chunk text. A repo-wide grep for the template strings returns zero hits. The same symmetric function embeds both stored docs and live queries, so the trained query/document asymmetry is never applied.
- **Recommendation:** Add task-prompt wrapping in the one embed seam: document template on ingest/store (ingest_local.py, knowledge writes), query template on recall (server._embed_one query path). Make the prefix pair model-aware (map keyed off embed_model). Re-embed the corpus after enabling.

### 26. Model swapped nomic→EmbeddingGemma under same name AND same emb_version (high, M)
- **Upstream:** Embedding-versioning hygiene — and MiOS's own WS-A3 design in `mios_pipe/memory/pg.py build_recall`, which scopes recall to `emb_version` precisely to stop mixing incompatible vector spaces. EmbeddingGemma is a distinct space from nomic-embed-text despite both being 768-d.
- **Current MiOS state:** `mios-llm-light.yaml:128-152` points the `nomic-embed-text` lane at `embeddinggemma-300m-qat-q8_0.gguf` while keeping the served name; `mios.toml:5636` still sets `emb_version = "nomic-768-v1"` and `:6025` keeps `embed_model = "nomic-embed-text"`. `pg.build_recall` only filters when emb_version differs, so old nomic + new EmbeddingGemma vectors collide in one namespace = silent recall degradation on pre-swap rows.
- **Recommendation:** Bump emb_version to e.g. `embeddinggemma-768-v1` (and the emb_model stamp) so the filter isolates spaces, then run the existing backfill (`mios_embed_backfill.py` / `force-revectorize.sh`) to restamp+re-vectorize under the new version with correct prompt prefixes. Optionally rename the served model off `nomic-embed-text`.

### 27. Cross-encoder reranking on RAG recall — merged into pgvector-rag gap 8 (high)
> The research entry on serving a bge-reranker-v2-m3 / Qwen3-Reranker GGUF lane for the knowledge/RAG path is folded into **pgvector-rag gap 8** above (same defect, same fix). Its model-lane provisioning detail (join the resident group at ~0.5 GB, default ON for RAG) is captured there.

### 28. No dedicated reasoning model actually served (medium, L)
- **Upstream:** For a single 24GB dGPU the 2025 reasoning-per-VRAM SOTA is an MoE: Qwen3-30B-A3B-Thinking-2507 (~3B active) or GPT-OSS-20B (Apache-2.0, native reasoning, ~13GB MXFP4). Dense Magistral Small 2509 (~14GB AWQ) is competitive but heavier to co-reside.
- **Current MiOS state:** `mios.toml [ai.vllm]/[ai.sglang]` (~L6668-6689) are GATED/disabled by default (VRAM); `big_ram_model = mistral-magistral-small-2509` (L6219) is intended but not baked (task T-178 pending); `teacher_model` falls back to granite4.1:8b (L9232). Light-lane ctx was forced to 32k to co-fit an ~11GB SGLang reservation (`mios-llm-light.yaml:79-83`), leaving no room for a 14GB dense heavy model. All heavy/reasoning/teacher traffic silently degrades to the 8B.
- **Recommendation:** Prefer GPT-OSS-20B (~13GB MXFP4) as the heavy lane — Apache-2.0, native reasoning, non-Qwen (keeps family diversity), co-resides with the light lane on the 24GB 4090 without collapsing chat ctx — or provision the intended Magistral. Bake weights (`[ai.vllm].bake_model`) and health-gate so `[nodes.local-vllm]` auto-joins; then teacher/heavy stops degrading to the 8B.

### 29. EmbeddingGemma Matryoshka unused; embed ctx misconfigured (low, S)
- **Upstream:** EmbeddingGemma MRL supports truncating 768→512/256/128 with minimal quality loss (renormalize after slicing) for lower HNSW memory; max sequence length is 2048 tokens.
- **Current MiOS state:** `mios-llm-light.yaml:150` serves `--ctx-size 8192` (beyond the model's 2048 trained length, so >2048-token chunks embed degraded); `ingest_local.py:59-63` plumbs a `dimensions`/`MIOS_AI_EMBED_DIMS` knob that is undocumented, unused, and possibly ignored by llama.cpp. Everything stores `vector(768)`.
- **Recommendation:** Drop the embed lane `--ctx-size` to 2048 and enforce ≤2048-token chunking on ingest. Optionally add an opt-in 256-d MRL profile (client-side truncate + L2-renormalize, new emb_version + vector(256) column) for large collections to ~3x-shrink the HNSW index; keep 768 default.

---

## security-egress

### 30. Every runtime security control ships default-off (high, M)
- **Upstream:** Secure-by-default baseline — Codex CLI ships sandboxing enabled by default (Landlock+seccomp); 2025 container/LLM guidance (Tigera, Oligo, Datadog) recommends block-all-egress-by-default and runtime guardrails as the shipped default, not opt-in.
- **Current MiOS state:** `mios.toml`: `[security.egress].mode="off"`, `[security.mcp_sandbox].enable=false`, `[security.fapolicyd_observe].enable=false`, `[security.mtls].enable=false`, `[security].provenance_taint=false`. The strong lethal-trifecta semantic firewall in `mios_pipe/access/firewall.py` is gated behind `PROVENANCE_TAINT_ENABLE` (false). A stock install runs with no active egress control, no MCP sandbox, no injection firewall, no mTLS.
- **Recommendation:** Flip low-risk, non-bricking controls to safe default-on: ship `egress.mode="audit"` (logs, drops nothing) and `provenance_taint=true` so the injection firewall is live; keep `enforce`/mcp_sandbox opt-in. Document a one-command `mios security harden` that promotes audit→enforce after the operator reviews audit logs.

### 31. Agent egress firewall is L3 IP/CIDR-only — no FQDN filtering (high, L)
- **Upstream:** Cilium `toFQDNs` / Calico DNS egress policies + NetworkSets (2025): default-deny egress with a per-domain allowlist, because LLM/API endpoints resolve to rotating CDN IPs (static IP allowlists are unmaintainable and DNS-tunneling-bypassable). Tigera guidance restricts DNS to prevent discovery/C2.
- **Current MiOS state:** `tools/generate-egress-firewall.py` `build_ruleset()` emits only `ip daddr {CIDR} accept`; `[security.egress].allow` accepts CIDRs/IPs only. `usr/share/mios/security/egress.nft` always-allows `100.64.0.0/10` (tailnet) and `172.16.0.0/12` (WSL gateway) wholesale — a very wide exfil surface. DNS (:53) is never constrained for the agent uid.
- **Recommendation:** Add FQDN-allowlist support: either a resolver that periodically expands `[security.egress].allow_domains` into nftables named sets via `nft add element`, or route the agent's DNS through a filtering resolver (dnsmasq/CoreDNS allowlist) and drop direct :53 egress. Tighten the always-allow /10 and /12 to the specific hosts actually needed.

### 32. Secret redaction is a narrow static-regex pass, outbound-only (high, M)
- **Upstream:** Yelp detect-secrets / GitGuardian / gitleaks (2025) entropy+plugin model: HexHighEntropyString, Base64HighEntropyString, plus AWS (AKIA…), GCP, Slack (xoxb-), JWT, PEM detectors. Regex-only scanners are documented as insufficient.
- **Current MiOS state:** `mios_pipe/redact.py` has only 5 API-key patterns (sk-, sk-ant-, hf_, ghp_, Bearer) + email + `MIOS_*` env pattern. No high-entropy detector; no AWS/GCP/Slack/JWT/PEM coverage. Its docstring says it sanitizes "before written to persistent storage or federated" — so untrusted tool output flowing into the model context is never scrubbed.
- **Recommendation:** Add an entropy-based plugin (Shannon threshold on token-like substrings) plus detectors for AWS AKIA, GCP `AIza`, Slack `xox[baprs]-`, JWT `eyJ`, and `-----BEGIN * PRIVATE KEY-----`. Vendor `detect-secrets` if a dependency is acceptable. Also invoke `redact()` on inbound untrusted tool/web output, not just outbound persistence.

### 33. Per-verb dispatch sandbox has no seccomp filter and no Landlock (medium, L)
- **Upstream:** Codex CLI baseline: Landlock LSM + seccomp enabled by default is the strongest local-agent confinement; gVisor is the cloud standard. A syscall filter is what contains a kernel-facing exploit after cap-drop.
- **Current MiOS state:** `usr/libexec/mios/mios-sandbox-exec` builds a bwrap profile with `--ro-bind / /`, `--unshare-*`, `--cap-drop ALL`, optional `--unshare-net`, but no `--seccomp` fd and no Landlock (and no `--unshare-user`). By contrast `usr/libexec/mios/mios-coderun-codemode` advertises "seccomp allowlist, Landlock PID-1" — that hardening is not applied to the write/interactive verb-dispatch tier.
- **Recommendation:** Feed bwrap a seccomp BPF filter fd (deny keyctl/ptrace/mount/bpf/userfaultfd/clone-new-userns) for the write/interactive profiles, and add Landlock filesystem/network rules mirroring the ro-root+workspace posture. Reuse the codemode runner's existing policy so the two sandboxes converge.

### 34. SBOM is generated but never signed/attested; no SLSA provenance (medium, M)
- **Upstream:** cosign 2.x `cosign attest --type cyclonedx` + SLSA v1.0 build-provenance attestations in Rekor (2025): signing an image alone gets SLSA L2; attestations push toward L3.
- **Current MiOS state:** `automation/90-generate-sbom.sh` runs Syft and writes CycloneDX+SPDX only into the image filesystem. `.github/workflows/mios-ci.yml` keyless-signs every image (`cosign sign --yes`) — good — but there is no `cosign attest` for the SBOM and no SLSA provenance anywhere in CI. Downstream verifiers cannot tie the SBOM or build steps to the artifact.
- **Recommendation:** In CI after signing, run `cosign attest --yes --type cyclonedx --predicate sbom.cdx.json <digest>` and emit SLSA provenance (slsa-github-generator or `cosign attest --type slsaprovenance`). Extend `42-cosign-policy.sh`/policy.json to require the SBOM+provenance attestations at verify time.

---

## gpu-cdi-vfio

### 35. No NVIDIA MPS control daemon on the shared 4090 (high, L)
- **Upstream:** NVIDIA CUDA MPS r590 (Dec 2025): `nvidia-cuda-mps-control -d` runs one server multiplexing multiple client contexts for genuine concurrent execution and space-partitioning — the recommended pattern for packing multiple inference processes onto one GPU.
- **Current MiOS state:** `usr/libexec/mios/mios-cdi-detect` only runs `nvidia-ctk cdi generate` (whole-GPU spec); every lane in `mios-llm-light.container`, `mios-llm-worker@.container`, `mios-llm-heavy.container` declares `AddDevice=nvidia.com/gpu=all`. No MPS daemon unit, no MPS pipe/log dirs, no `CUDA_MPS_*` env. Co-resident lanes run as independent CUDA contexts the driver serializes with time-slicing — no true concurrent kernels, full context-switch overhead.
- **Recommendation:** Ship an MPS control daemon as a host service/Quadlet (`nvidia-cuda-mps-control -d` with `CUDA_MPS_PIPE_DIRECTORY`/`CUDA_MPS_LOG_DIRECTORY` on a tmpfiles path), bind those dirs into each lane (CDI containerEdits or shared Volume), and set `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE` per lane. Gate to bare-metal NVIDIA (MPS is degraded on the WSL2 /dev/dxg path).

### 36. No per-lane VRAM partitioning or OOM guard (high, M)
- **Upstream:** `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT` (CUDA 11.5+, MPS r590) sets a hard per-client pinned-device-memory cap, e.g. `"0=10G"` — the standard way to fence co-tenant GPU memory.
- **Current MiOS state:** Only `mios-llm-heavy.container` sets a bound (`--gpu-memory-utilization 0.45`); `mios-llm-light` and `mios-llm-worker@` set no VRAM cap; there is no VRAM budget table in mios.toml and no cross-lane coordinator. light+worker+heavy (plus Windows) have no shared ceiling and can collectively exhaust the 24GB card.
- **Recommendation:** Introduce a VRAM budget in mios.toml summing to <24GB minus Windows headroom, and enforce it: via `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT` per lane once MPS lands (gap 35), and immediately by adding explicit caps to each lane env (llama.cpp context/ngl sizing, worker gpu-memory-utilization) so a second lane cannot OOM the primary.

### 37. CDI device refs are coarse whole-GPU `=all` for every lane (medium, L)
- **Upstream:** NVIDIA k8s-device-plugin sharing config + GPU Operator (2025): `sharing.mps.resources`/`timeSlicing` with `replicas`/`renameByDefault` advertise one GPU as multiple named devices, writing per-slice CDI edits (MPS pipe mounts, thread-percent env).
- **Current MiOS state:** `mios-cdi-detect` emits only a whole-GPU `nvidia.com/gpu=all` spec, and `mios-gpu-passthrough` hardcodes `AddDevice=nvidia.com/gpu=all` for every quadlet. No named sub-device/replica concept exists.
- **Recommendation:** Have mios-cdi-detect additionally synthesize MPS-backed CDI device entries (e.g. `nvidia.com/gpu=mps-light`, `=mps-heavy`) whose containerEdits carry the MPS pipe mount + per-slice thread/mem limits, then wire each lane to its own slice. Make whole-GPU-vs-sliced a mios.toml toggle.

### 38. VFIO passthrough is static (reboot-time binding) (medium, L)
- **Upstream:** Single-GPU passthrough SOTA (2025): libvirt qemu hooks (prepare/release) + driverctl dynamically unbind nvidia and bind vfio-pci at VM start, reverse at stop — no reboot (QEMU 9.0+/OVMF 2024.02/libvirt 10.6+).
- **Current MiOS state:** Binding is static via `usr/lib/bootc/kargs.d/{01-mios-vfio.toml,20-vfio.toml,13-rtx50-vfio-workaround.toml}` + `vfio-config.sh` (writes vfio-pci.ids and /etc/modprobe.d/vfio.conf, requires reboot). The existing hook `usr/lib/libvirt/hooks/qemu` only runs `virsh nodedev-reset` (FLR), never rebinds drivers. You cannot flip the 4090 between host-AI and a VM without a reboot — incompatible with the shared-4090 goal.
- **Recommendation:** Extend the libvirt qemu hook to do dynamic bind/unbind (detach nvidia_drm/nvidia + bind vfio-pci on prepare; reverse on release), ship driverctl, and drive it off the VM's hostdev list. Keep the FLR step as the post-bind reset.

### 39. VFIO configurator is Arch/CachyOS-oriented, partly inert on bootc (medium, M)
- **Upstream:** bootc/Fedora immutable model: kernel args in `/usr/lib/bootc/kargs.d/*.toml`, initramfs drivers in dracut conf.d — not `/etc/mkinitcpio.conf`, grub-mkconfig, or interactive read prompts (and MiOS's own LAW USR-OVER-ETC).
- **Current MiOS state:** `usr/libexec/mios/vfio-config.sh` calls `mkinitcpio -P`, `grub-mkconfig`, writes `/etc/mkinitcpio.conf`, and blocks on interactive `read` prompts; `vfio-toggle.sh` already notes UKI/composefs ignore /etc/default/grub. The configurator's bootloader/initramfs branches are dead on MiOS.
- **Recommendation:** Replace the mkinitcpio/grub interactive branches with a non-interactive bootc-native path: write bootc kargs.d + a dracut conf.d vfio drop-in and reconcile via bootc; keep vfio-toggle's `--add`/`--remove` as the declarative front door and delete the Arch-only code paths.

### 40. Hand-rolled WSL2 CDI specs pin a stale cdiVersion (low, S)
- **Upstream:** CNCF CDI spec 1.x (current 1.1.0; Docker 28.2+ enables CDI by default, Podman 5.x native) — cdiVersion should reflect the minimum features used and track the maintained line.
- **Current MiOS state:** `mios-cdi-detect` writes `cdiVersion: "0.6.0"` literally in all three WSL2 specs (nvidia/amd/intel), and `usr/share/doc/mios/upstream/cdi.md` shows `cdiVersion: 0.5.0`. Static, never derived from features used.
- **Recommendation:** Prefer `nvidia-ctk cdi generate` (stamps the correct minimum version) wherever available; for WSL2 fallbacks let the toolkit compute the version or bump to a current 0.8.x/1.x baseline consistent with the shipped podman; update the doc example to match.

---

## windows-dism-xbox

### 41. Pure-DISM build never services boot.wim / winre.wim, applies no Dynamic Updates (high, L)
- **Upstream:** Microsoft Learn "Update Windows installation media with Dynamic Update": mount winre.wim + boot.wim + install.wim and apply SafeOS DU (e.g. KB5077180/KB5095615) to winre.wim, Setup DU (KB5074110) to boot.wim, plus the WinRE Secure-Boot DUs KB5079271/KB5072537 (2026). These carry the Secure Boot 2026 cert rollover and WinRE hardening.
- **Current MiOS state:** `New-MiOSISO.ps1` `Invoke-MiOSImageServicing` (`src/autounattend/New-MiOSISO.ps1:711-953`) mounts only `sources\install.wim` (single Pro index) and never mounts boot.wim/winre.wim; `Build-MiOSBootableIso` (:956-969) reads etfsboot/efisys only for oscdimg. WinPE/WinRE ship verbatim from source media. The retired NTLite preset DID service them (`presets/xbox-minimal-ultra-plus.xml:712-729`). An image built without these can fail Secure Boot and recovery (Reset/BitLocker unlock) on current firmware.
- **Recommendation:** Add a DU-servicing stage: (1) mount `sources\boot.wim` indexes 1+2, apply the latest Setup DU via Add-WindowsPackage, commit; (2) mount winre.wim, apply SafeOS DU, re-inject the refreshed winre.wim back into install.wim before its Dismount -Save; (3) SSOT-pin the DU KBs alongside the UUP build pin. Assert WinRE version post-apply.

### 42. Pure-DISM path injects no cumulative update; not checkpoint-CU aware (high, M)
- **Upstream:** Microsoft Learn "Checkpoint cumulative updates" (24H2/Server 2025+): the latest LCU may require prerequisite checkpoint CUs, applied together in one DISM /Add-Package against a folder of the target LCU + all checkpoints. MS 2025-2026 guidance shifted offline patching to DISM /Add-Package (KB5074109 sequencing).
- **Current MiOS state:** `New-MiOSISO.ps1` has zero Add-WindowsPackage calls. Update integration exists only via UUP conversion flags in `mios-uup-fetch.ps1` (updates=1 at :146, AddUpdates at :271) — i.e. whatever the UUP-dump snapshot bundles; the `-SourceIso` path (operator supplies a stock retail ISO) ships a completely unpatched baseline. On 24H2+ that box can't necessarily jump straight to current patch level.
- **Recommendation:** Add an SSOT-gated Add-WindowsPackage update stage to Invoke-MiOSImageServicing: stage current SSU/LCU/.NET-CU (+ checkpoint CUs) in one folder and call DISM /Add-Package so checkpoint chaining resolves in one pass; run it BEFORE the existing `/StartComponentCleanup /ResetBase` (:924) so ResetBase baselines the patched store. Make it mandatory on `-SourceIso` where UUP AddUpdates can't help.

### 43. Offline driver injection targets only install.wim, never boot.wim (medium, M)
- **Upstream:** Microsoft Learn media-dynamic-update / MDT practice: inject boot-critical storage + network drivers into boot.wim (both indexes) so Setup can enumerate disks/network on current hardware (Intel VMD/RST RAID, newer NVMe, 2.5GbE).
- **Current MiOS state:** `Invoke-MiOSImageServicing` bakes host drivers via `Export-WindowsDriver -Online` + `Add-WindowsDriver -Path $mount` (the mounted install.wim) only (`New-MiOSISO.ps1:794-806`); boot.wim is never mounted. The native converter's AddDrivers (`mios-uup-fetch.ps1:240-254`) also stages into the OS image. On hardware whose storage/NIC driver isn't inbox in WinPE, Setup can't see the disk/network and dead-ends before install.wim is applied.
- **Recommendation:** Reuse the exported host DriverStore set and Add-WindowsDriver into both boot.wim indexes (1=WinPE, 2=Setup) in the new boot.wim servicing stage; restrict to boot-critical classes (storage/net) to keep WinPE small. SSOT-gate via the existing `bake_host_drivers` flag.

### 44. Baked payloads use no DISM /Apply-CustomDataImage single-instancing (low, M)
- **Upstream:** Microsoft Learn DISM /Apply-CustomDataImage (/SingleInstance): OEM preinstall technique that dehydrates/single-instances added payload against the base image to reclaim footprint.
- **Current MiOS state:** `Invoke-MiOSImageServicing` robocopies the whole mios-bootstrap repo (~34MB) into ProgramData\MiOS\repo (`New-MiOSISO.ps1:833-841`) plus staged scripts/payloads (:816-828); the size win relies solely on `Export-WindowsImage -CompressionType Max` (:950). No CDI/single-instancing.
- **Recommendation:** Low priority given MiOS removes rather than preloads apps. If the baked payload grows (models, larger appx), evaluate packaging it as a custom data image applied with DISM /Apply-CustomDataImage /SingleInstance instead of robocopy-into-WIM; at minimum keep relying on Export -CompressionType Max and keep the embedded .git excluded. Track as an option, not a required change.
