<!-- AI-hint: Specifies the architectural transition from Ollama to llama.cpp via the llama-swap proxy to enable fleet-wide KV-cache checkpointing, restoration, and forking for the AIOS Context Manager.
     AI-related: /usr/share/mios/llamacpp/models/.ready, /usr/share/mios/llamacpp/models/, mios-daemon, mios-llama-swap, mios-llamacpp-embed, mios-ollama, mios-ollama-cpu, mios-llamacpp, mios-ai, mios-llama-swap.container -->
# Ollama → llama.cpp Engine Conversion for KV-Cache (WS-10) — draft

> Status: DRAFT (2026-06-04). Operator directive: convert the ollama inference
> stack to **llama.cpp** to unlock **KV-cache** (the AIOS Context Manager:
> checkpoint / restore / fork) across ALL lanes, not just the iGPU. Companion to
> `postgres-pgvector-unification.md`.
>
> **This supersedes the 2026-06-01 engine verdict** ("no wholesale conversion —
> keep ollama as the multi-model lane manager"). That verdict's blocker was real
> (ollama's multi-model auto-swap daemon has no llama.cpp equivalent) — so the
> linchpin of this draft is **llama-swap**, the proxy that restores on-demand
> multi-model swapping for llama.cpp. Without llama-swap, all-llama.cpp regresses
> model management; with it, the conversion is viable.

## 1. Why — KV-cache is the whole point

The AIOS Context Manager (gap #3) needs `kv_checkpoint` / `kv_restore` /
`kv_fork`. Engine reality (from the engine-strategy audit):

- **ollama = ✗** no KV save/restore at all. Only `keep_alive` residency
  (VRAM→RAM→evict); a swap *unloads*, never checkpoints. ollama can never reach
  context-paging.
- **llama.cpp = ✓** real, usable today: `--slot-save-path` + `POST
  /slots/{id}?action=save|restore` writes a conversation's KV to disk and
  restores near-instantly. **Already proven in MiOS** on the iGPU lane:
  `_kv_paging` (server.py) demand-pages the OpenAI `/v1/chat/completions` path —
  measured `n_saved:62` round-trip with `--parallel 1` (one slot, deterministic
  routing).

Converting every lane to llama.cpp **generalizes `_kv_paging` from one node to
the whole fleet** + enables `kv_fork` (slot copy → parallel cognitive paths for
the swarm). That is the operator's "compress / write-to-disk / clean state on
load-unload" requirement, fleet-wide.

## 2. The linchpin — llama-swap (restores multi-model)

ollama's killer feature is the multi-model daemon (auto-load, LRU evict, hot
swap). llama.cpp is one-model-per-process. **llama-swap** (FOSS, MIT) is the
standard fix: a small proxy that, per requested `model`, launches/swaps the right
`llama-server` on demand and exposes ONE OpenAI `/v1` endpoint per lane. It gives
back ollama's "many models, auto-loaded" UX while every server underneath is
llama.cpp (so KV-paging works). Config = a YAML mapping `model → gguf path +
server flags (--ctx-size, --n-gpu-layers, --parallel 1, --slot-save-path)`.

This replaces the ollama `/api/ps` residency subsystem with llama-swap process
orchestration (its `/running` + swap), which `_admit`/`_reclaim_idle_vram` query
instead of `/api/ps`.

## 3. Target per-lane architecture

| Lane | Today | After |
|---|---|---|
| dGPU (:11434, CUDA) | ollama daemon | llama-swap → `llama-server --n-gpu-layers 999 --slot-save-path …` per model |
| CPU light (:11435) | ollama-cpu | llama-swap → CPU `llama-server` (micro/router/refine/polish) |
| iGPU (:11436, Vulkan, Windows) | llama.cpp already | unchanged (already the model) |
| Embeddings | ollama nomic-embed | dedicated `llama-server --embedding` (nomic-embed GGUF), OpenAI `/v1/embeddings` |
| Heavy/KV-tiering (gated) | vLLM quadlet (off) | **still vLLM** — PagedAttention + APC + LMCache are strictly better for the high-concurrency heavy lane; llama.cpp KV-paging is the per-conversation tier, vLLM is the throughput tier. Not either/or. |

KV-cache primitives (server.py): generalize the existing `_kv_paging` from the
`kv_paging_hints="11436"` gate to **every llama.cpp endpoint** (it already keys
off `_endpoint_is_llamacpp`); add `kv_fork` = `/slots/{src}?action=save` →
restore into a new slot/conversation for parallel branches.

## 4. Conversion blast radius (re-verify against current `server.py` first)

The OpenAI `/v1` seam already exists and is engine-agnostic (Law 5);
`_endpoint_is_ollama`/`_endpoint_is_llamacpp`/`_binding_api`/
`_endpoint_supports_tool_choice` are config-first `api=` switches; llama.cpp is
already a recognized `api` value; `_kv_paging` already works. So the conversion
is mostly **routing the lanes through the existing `/v1` path instead of the
ollama `/api/chat` path**, plus model orchestration. Audited touch-points:

- **~13 ollama-native `/api/chat` call sites** (refine, polish, router, planner,
  judge, knowledge, fan-out ×2, tool-loop; + mios-daemon; + ~4 OWUI-pipe sites)
  carry ollama-only fields (`think`, `keep_alive`, `format:json`,
  `options.{num_ctx,num_gpu,num_thread}`) and **NDJSON** streaming (≠ OpenAI
  SSE). → route via the `/v1` chat path; map options to `llama-server` launch
  flags (llama-swap config) instead of per-request `options`.
- **`/api/ps` VRAM residency subsystem** (`_ollama_resident`/`_vram_checkpoint`/
  `_ollama_unload`/`_reclaim_idle_vram`/`_is_warm`) → llama-swap `/running` +
  swap (process orchestration; one-model-per-proc).
- **`_embed_one` `/api/embeddings`** → `/v1/embeddings` on the embedding server.
- **2 hardcoded `:11434`/`:11435` ollama detections** (judge, daemon) → route
  through `_endpoint_is_ollama` (SSOT), since those ports become llama.cpp.
- **`hermes_backend_url`** (mios.toml) → one-line `/v1` swap.
- **Model provisioning**: replace `MIOS_OLLAMA_BAKE_MODELS` + `ollama create`
  (Modelfile) with **baked `.gguf` files** + the llama-swap model map. Modelfile
  `SYSTEM` is portable (the runtime contract.md overrides it); `num_ctx/num_gpu`
  → launch flags.

## 5. Quadlets / SSOT

- New `mios-llama-swap` quadlet (per lane, or one with multiple model groups) +
  `mios-llamacpp-embed`; retire `mios-ollama` / `mios-ollama-cpu`. Bound-images
  (Law 3), `User=`/`Delegate=yes` (Law 6).
- `mios.toml [ai].engine = "llamacpp"`; `[llamacpp]` (slot-save-path, parallel=1,
  ctx, model map path); ports unchanged (:11434/:11435 now llama-swap). Image
  SSOT `[image.sidecars].llama_swap` + `.llamacpp` (FOSS: `ghcr.io/
  ggml-org/llama.cpp:server`, MIT).

## 6. Risks (honest)

- **Swap cold-start latency** — llama-swap loads a model per swap (no warm
  multi-model pool). Mitigate: pin the hot models (refine/polish/router) to
  always-resident servers; swap only the long tail. The existing admission +
  lane caps already serialize cold loads.
- **Tool-calling robustness** — llama.cpp function-calling uses `--jinja` chat
  templates + grammar; historically finickier than ollama (the iGPU lane already
  needs `no_tool_choice_hints` + the per-lane tool-cap because grammar-
  constraining all ~71 verbs times out). Carry those forward; validate the
  function-call path per model before cutover.
- **One-model-per-process VRAM** on the shared 4090 — fewer concurrent models
  than ollama's pool. The vLLM heavy lane + KV-paging offset this.

## 7. Staged plan (drafts → build, reversible)

1. **Embeddings first** (lowest risk): stand up `llama-server --embedding`
   (nomic-embed GGUF) on a new port; flip `_embed_one` + OWUI RAG to it; verify
   768-dim parity. ollama still serves chat.
2. **llama-swap on the CPU light lane** (:11435): micro/router/refine/polish
   models; verify the `/v1` path + tool-calls + KV-paging on a non-critical lane.
3. **Generalize `_kv_paging`** to all llama.cpp endpoints; add `kv_fork`.
4. **dGPU lane** (:11434) → llama-swap; migrate the ~13 call sites to `/v1`;
   replace the `/api/ps` subsystem with llama-swap `/running`.
5. **Model provisioning** → `.gguf` bake + llama-swap map; retire Modelfiles/
   `ollama create`.
6. **Retire ollama** quadlets once parity (chat + tools + embeddings + KV) holds.
7. vLLM heavy lane stays the gated throughput tier (VRAM-blocked today).

Net: KV checkpoint/restore/fork fleet-wide (the AIOS Context Manager fully
realized), all on a FOSS (MIT) engine, with llama-swap preserving multi-model
ergonomics. Re-verify the `server.py` touch-points (3-day-old audit) as step 0.

---

## Build status — additive engine step (2026-06-04): llama-swap infra DONE (gated)

Stood up the llama.cpp multi-model lane ALONGSIDE ollama, GATED OFF until GGUFs
are provisioned (nothing live moves). **KEY FINDING:** the agent-pipe is ALREADY
ready for the swap — `_endpoint_is_llamacpp` (server.py:2249) is config-first
(`api="llamacpp"` → `_kv_paging` fires on ANY endpoint, no port hardcode) and
`/v1` is engine-agnostic (Law 5). So WS-10 is **infra + GGUF provisioning**, not
a server.py rewrite.

New / edited:
- `usr/share/containers/systemd/mios-llama-swap.container` — llama-swap quadlet
  (host-net, CUDA CDI, config + models + slot-save mounts, uid 827). Inert via
  `ConditionPathExists(/usr/share/mios/llamacpp/models/.ready)`.
- `usr/share/mios/llamacpp/llama-swap.yaml` — model-map TEMPLATE: chat models
  (qwen3.5:4b, gemma4:e4b) with `--parallel 1 --slot-save-path` (KV-pageable) +
  nomic-embed-text `--embedding` (replaces the ollama embed lane).
- SSOT: `[ports].llama_swap=11450`, `[image.sidecars].llama_swap`
  (`ghcr.io/mostlygeek/llama-swap:cuda`), `[services.llamacpp]` (uid 827),
  `[llamacpp]` (enable=false, slot_dir/models_dir/config).
- Identity/wiring: sysusers (mios-llamacpp 827 + mios-ai), tmpfiles (slot dir),
  userenv (llamacpp.* / llama_swap maps), 15-render allow-list. TOML + `bash -n`
  validated.

REMAINING (operator / live — cannot be done or verified offline):
1. **GGUF PROVISIONING** (the real prerequisite). MiOS bakes OLLAMA models, not
   GGUFs. Need an offline GGUF bake (download/convert qwen3.5-4b / gemma4-e4b /
   nomic-embed-text → `/usr/share/mios/llamacpp/models/*.gguf` + `touch .ready`).
2. **VERIFY THE TEMPLATE live**: llama-swap image tag + `cmd`/`proxy`/`ttl`
   schema + the llama-server binary path inside the image + `--config`/`--listen`
   flags + `--n-gpu-layers` sizing for the shared 4090.
3. **WIRE THE LANE**: add `[nodes.local-llamaswap]` (endpoint
   `http://localhost:11450/v1`, `api="llamacpp"`) → auto-joins the swarm +
   KV-pages, zero pipe changes.
4. **CUTOVER (later)**: point `_embed_one` (server.py:15026) at the llama-swap
   embed endpoint; migrate the chat lanes off ollama; retire ollama.
