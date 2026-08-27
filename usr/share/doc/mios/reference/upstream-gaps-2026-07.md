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

*Note: Upstream gap remediation verified and active in current codebase builds.*
