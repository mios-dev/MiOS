<!-- AI-HINT: Heavy-lane model selection for the shared 24GB RTX 4090 (2026-07). Decides MIOS_VLLM_BAKE_MODEL from a 14-candidate research pass. OPERATOR DECISION 2026-07-10: stelterlab/Qwen3-30B-A3B-Instruct-2507-AWQ @ 256k (see the DECISION section at top). Workflow had recommended openai/gpt-oss-20b (native MXFP4, first-party repo, only strong candidate that actually reaches the 128k mandate co-tenanted on a shared card) -- kept below as superseded. Runner-up: Qwen/Qwen3-14B-AWQ. Family-diverse alt honoring the SSOT intent: cyankiwi/Magistral-Small-2509-AWQ-4bit (Mistral, compressed-tensors W4A16 — NOT classic AutoAWQ). Every hf_repo below is grounded in the research JSON; do NOT invent repo ids. The SSOT still names Magistral 2509 — this doc argues gpt-oss wins on the 128k+trust axes and should carry the bake; keep Magistral as the diversity/SSOT-honoring alt. -->

# Heavy-lane model selection — shared 24GB RTX 4090 (2026-07)

## ✅ OPERATOR DECISION (2026-07-10) — Qwen3-30B-A3B-Instruct-2507-AWQ @ 256k

**Chosen:** `MIOS_VLLM_BAKE_MODEL = stelterlab/Qwen3-30B-A3B-Instruct-2507-AWQ` — Qwen3-30B-A3B-Instruct-2507
(MoE 30.5B-total / **3.3B-active**, **262144 native context**), INT4 **AWQ via vllm-project
`llm-compressor`** (~16GB, compressed-tensors format). Operator chose the **newest fittable MoE**
over the workflow's gpt-oss-20b pick, and wants the **full 256k**. Instruct = **non-thinking**
(fast agentic + tool-use); swap `Qwen/Qwen3-30B-A3B-Thinking-2507` for CoT reasoning.

**Recency (live-verified 2026-07-10):** the newest *frontier* (DeepSeek V4 Pro, Qwen 3.7 Max,
Qwen3-235B-A22B, Mistral Large 3) is **too large for a 24GB card** even at 4-bit — those are
big-GPU/API class. Among 24GB-fittable options the current MoE picks are Qwen3-30B-A3B-2507,
Qwen3.6-35B-A3B (newer but tighter fit), and gpt-oss-20b (roomier fit, but caps at 128k). So the
chosen model is the freshest that actually fits the hardware at the requested 256k.

**256k on a shared 24GB card — the honest mechanism:** a ~16GB 4-bit model leaves only ~4–8GB
of VRAM KV. A single 256k sequence needs ~12GB KV even at fp8 — more than fits. So **256k rides
the SGLang lane** (`[ai.sglang]`), whose **HiCache spills inactive KV to CPU RAM** + fp8 KV to
reach the full 262144. The **vLLM lane** (`[ai.vllm]`) carries the same model but PagedAttention
admits only as much as its ~4GB fp8-KV budget holds (well short of 256k) — use vLLM for
throughput at moderate context, SGLang for the 256k long-context turns.

**Config applied (commit 06c5f231, mios.toml):** both lanes `bake_model` + `max_model_len=262144`
+ `kv_cache_dtype=fp8`; vLLM `gpu_util=0.85 / quantization=compressed-tensors / tool_call_parser=hermes
/ v1_engine=true`; SGLang `mem_fraction=0.85 / hierarchical_cache=true / tool_parser=qwen25 /
reasoning_parser="" (Instruct)`. **Follow-up:** wire `--kv-cache-dtype`/`--quantization`/`--tool-call-parser`
into the heavy `.container` Exec + `MIOS_VLLM_*`/`MIOS_SGLANG_*` userenv mapping, then live-validate
on the GPU before enabling the lane.

---

## Workflow recommendation (superseded by the operator decision above)

**Recommendation:** set `MIOS_VLLM_BAKE_MODEL = openai/gpt-oss-20b` for the shared heavy lane.

**Context / constraints weighed:** single co-tenanted 24GB RTX 4090 (Windows + Granite 4.1
light lane also resident) · 128k context mandate with **fp8 KV cache** · reasoning +
native tool-use required · vLLM **>=0.11 (V1)** native serve · prefer **ungated Apache-2.0**
· recency · quant-repo trustworthiness. The MiOS SSOT names Magistral Small 2509; the
research shows that model **cannot co-achieve the full 128k mandate** on a shared card
(~14–16GB weights leave too little KV), and its only 2509 4-bit repos are single-community
quants. A better-fitting, first-party, ungated option clearly wins the bake — Magistral is
retained below as the SSOT-honoring, family-diverse alternative.

---

## Recommendation — `openai/gpt-oss-20b`

The only candidate that comfortably reaches the 128k mandate on the co-tenanted 24GB card,
and it does so from a **first-party OpenAI repo** with **native MXFP4 weights** (no
third-party quant to trust). MoE 21B-total / 3.6B-active → ~13GB effective load, leaving
~8–10GB for KV → 128k @ fp8 KV is real. Purpose-built agentic reasoner with a
low/medium/high **reasoning-effort dial** (ideal for a planner/critic/council swarm),
native function-calling, harmony response format. Apache-2.0, ungated. vLLM official
launch partner, mainlined into 0.11 V1. Family-diverse from both the Granite light lane
and the Qwen/Mistral heavy candidates.

### `[ai.vllm]` serve flags to set

```
--served-model-name   mios-heavy
--tool-call-parser     openai
--enable-auto-tool-choice
--reasoning-parser     openai_gptoss
--max-model-len        131072
--kv-cache-dtype       fp8
--async-scheduling
```

- **quantization:** none to pass — MXFP4 is native and auto-detected (do **not** add
  `--quantization awq_marlin`/`fp8`). The mxfp4/Marlin kernel path runs on Ada (4090 = sm_89).
- Pin a current **0.11.x** build (early gpt-oss builds leaked special tokens into tool
  names — GH #32587). Use high reasoning-effort for the hardest coding proofs to offset
  the 3.6B active-param depth.

---

## Runner-up — `Qwen/Qwen3-14B-AWQ`

Official Qwen AWQ (awq_marlin), ~10GB weights — the leanest fitting reasoner, so it also
clears 128k @ fp8 KV with the most headroom of the dense options. Apache-2.0, ungated,
verified weights in-repo. Strong hybrid-thinking reasoner/coder. The one chore: native
context is 32k, so 128k needs YaRN rope scaling.

```
--served-model-name   mios-heavy
--quantization         awq_marlin
--tool-call-parser     hermes
--enable-auto-tool-choice
--reasoning-parser     qwen3
--max-model-len        131072
--kv-cache-dtype       fp8
--rope-scaling         {"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}
```

(YaRN mildly degrades sub-32k prompts — enable only when 128k is actually needed. Prefer
gpt-oss as primary because it avoids the rope chore and ships from a first-party repo.)

---

## Family-diverse alternative (honors the SSOT) — `cyankiwi/Magistral-Small-2509-AWQ-4bit`

The exact 2509 the MiOS SSOT names, and the strongest reasoning+tool-use of the Mistral
Magistral family (24B dense, RL reasoning, native `[THINK]` traces, vision tower). Keep it
as the diversity pick if you want the SSOT model or a third distinct family. **Caveat:**
~16GB weights (heaviest 4-bit here) → realistic ~48–64k context co-tenanted; the **full
128k is not co-achievable** with the light lane running. Single community quanter (cyankiwi)
— validate a load before baking.

Key gotcha: despite the repo name, `config.json` `quant_method` is **compressed-tensors
(W4A16)**, not classic AutoAWQ. Serve with `--quantization compressed-tensors` (vLLM
auto-detects; do **not** pass `awq_marlin`).

```
--served-model-name   mios-heavy
--tokenizer-mode       mistral
--config-format        mistral
--load-format          mistral
--quantization         compressed-tensors
--tool-call-parser     mistral
--reasoning-parser     mistral
--enable-auto-tool-choice
--max-model-len        65536
--kv-cache-dtype       fp8
--limit-mm-per-prompt  {"image":10}
```

Leaner 2509 swap if you prefer a single-format, cleaner download from a reputable quanter:
`Intel/Magistral-Small-2509-int4-AutoRound` (~15GB, AutoRound int4; serve via
`--quantization auto-round`/gptq_marlin, same mistral parsers — verify the exact
`--quantization` value against its `config.json`, and note vLLM auto-round is newer/less
battle-tested). Do **not** chase a `cpatonn/Magistral-Small-2509-AWQ-4bit` repo — it
soft-404s to cyankiwi content (phantom).

---

## Comparison table

| Model | hf_repo | Quant | Weights | Fits 24GB (128k?) | License / Gated | vLLM parsers (tool / reasoning) | Recency |
|---|---|---|---|---|---|---|---|
| **gpt-oss-20b ★ PICK** | `openai/gpt-oss-20b` | MXFP4 native (MoE) | ~13GB | **Yes — hits 128k** (~8–10GB KV) | Apache-2.0 · ungated | `openai` / `openai_gptoss` | Aug 2025 |
| **Qwen3-14B-AWQ (runner-up)** | `Qwen/Qwen3-14B-AWQ` | AWQ4 (awq_marlin) | ~10GB | **Yes — 128k via YaRN** | Apache-2.0 · ungated | `hermes` / `qwen3` | Apr 2025 |
| **Magistral 2509 AWQ (SSOT alt)** | `cyankiwi/Magistral-Small-2509-AWQ-4bit` | W4A16 compressed-tensors (gs32) | ~16GB | Yes weights; **~48–64k, not 128k** | Apache-2.0 · ungated | `mistral` / `mistral` | 2509 (2025-09) |
| Magistral 2509 AutoRound | `Intel/Magistral-Small-2509-int4-AutoRound` | AutoRound int4 (gs128) | ~15GB | Yes; ~48–64k co-tenanted | Apache-2.0 · ungated | `mistral` / `mistral` | 2025 |
| Magistral 2506 true-AWQ | `abhishekchohan/Magistral-Small-2506-AWQ` | AWQ4 (awq_marlin), text-only | ~14GB | Yes; best KV of family, still not 128k co-tenant | Apache-2.0 · ungated | `mistral` / `mistral` | 2506 (older) |
| Qwen3-14B-FP8 | `Qwen/Qwen3-14B-FP8` | FP8 w8a8 | ~16.3GB | Tight; 128k only if heavy lane dominates | Apache-2.0 · ungated | `hermes` / `qwen3` | Apr 2025 |
| DeepSeek-R1-Distill-Qwen-32B AWQ | `Valdemardi/DeepSeek-R1-Distill-Qwen-32B-AWQ` | AWQ4 | ~16–17GB | ~32k, not 128k; Qwen-based (diversity minus) | MIT · ungated | `hermes` / `deepseek_r1` | Jan 2025 |
| GLM-Z1-32B GPTQ | `kaitchup/GLM-Z1-32B-0414-autoround-gptq-4bit` | GPTQ-Int4 | ~18–19GB | Tight ~16–32k, not 128k | MIT · ungated | `glm45` / `glm45` | Apr 2025 |
| Seed-OSS-36B AWQ | `QuantTrio/Seed-OSS-36B-Instruct-AWQ` | AWQ4 | ~20GB | Very tight ~8–16k, not 128k | Apache-2.0 · ungated | `seed_oss` / `seed_oss` | Aug 2025 |
| Qwen3-32B-AWQ | `Qwen/Qwen3-32B-AWQ` | AWQ4 | ~19.3GB | No (128k) — dedicated card only | Apache-2.0 · ungated | `hermes` / `qwen3` | Apr 2025 |
| Devstral-Small-2507 AWQ | `cyankiwi/Devstral-Small-2507-AWQ-4bit` | AWQ4 | ~14GB | Yes, near-128k — but **no reasoning parser** (coder, not reasoner) | Apache-2.0 · quant ungated | `mistral` / — | Jul 2025 |
| Magistral 2509 FP8 | `unsloth/Magistral-Small-2509-FP8-Dynamic` | FP8 dynamic | ~24GB | **No** — fills the card | Apache-2.0 · ungated | `mistral` / `mistral` | 2025 |
| Qwen3.6-27B-AWQ | `QuantTrio/Qwen3.6-27B-AWQ` | AWQ4 (community) | ~23.8GB | **No** + needs vLLM ≥0.19 | Apache-2.0 · ungated | `qwen3_coder` / `qwen3` | Apr 2026 |
| Hunyuan-A13B GPTQ | `tencent/Hunyuan-A13B-Instruct-GPTQ-Int4` | GPTQ-Int4 (80B MoE) | ~40GB+ | **No** — needs 2×24GB/48GB | custom hunyuan · ungated | yes (irrelevant) | 2025 |

★ = recommended bake. Rows below Seed-OSS are documented for elimination (don't-fit / wrong-role / engine-gap).

---

## Rationale (why gpt-oss over the SSOT-named Magistral)

1. **128k mandate is the deciding axis** and only gpt-oss-20b and Qwen3-14B actually reach
   it on a co-tenanted 24GB card; every Magistral 4-bit repo tops out ~48–64k co-tenanted.
2. **Repo trust:** gpt-oss ships MXFP4 **first-party from OpenAI** — no community quanter
   to validate, unlike the single-quanter Magistral/Seed/GLM repos.
3. **Agentic fit:** native tool-calling + a low/medium/high reasoning-effort dial suits the
   planner/critic/council swarm better than a fixed-depth dense model.
4. **License/engine:** Apache-2.0, ungated, mainlined in vLLM 0.11 V1 (launch partner) —
   zero gating friction, mature serve path.
5. **Diversity:** distinct from the Granite light lane and from Qwen/Mistral, so the two-lane
   plane spans three model families.
6. **SSOT honored, not ignored:** Magistral 2509 (`cyankiwi/...AWQ-4bit`, compressed-tensors)
   remains the family-diverse alt for anyone who wants the SSOT model at ~48–64k, and
   `Intel/Magistral-Small-2509-int4-AutoRound` is the cleaner-download swap.

**Doc path:** `C:/MiOS/usr/share/doc/mios/reference/heavy-model-selection-2026-07.md`
