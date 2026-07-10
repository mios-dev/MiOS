<!-- AI-hint: Re-architecture plan (2026-06-15) to move MiOS from prose-stuffed prompts to NATIVE OpenAI patterns — Structured Outputs (json_schema+strict) for refine/router classification, lean MiOS-specific system prompts, Chat-Completions (not Responses). Synthesized by the mios-native-openai-patterns ultracode workflow (3 agents, cited). Proven in-repo template: _route_domain server.py:11598-11638. -->

# MiOS Native-OpenAI-Patterns Re-architecture (2026-06-15)

## Principle (cited)
A 2025/2026 model already knows how to emit JSON and call tools — you don't re-teach that in prose; you **enforce structure with schemas + roles and keep prompts lean**. With `response_format:{type:"json_schema",strict:true}` the decoder is *constrained* to schema-valid output (every field present, types right, enums valid) — `json_object` mode guarantees valid JSON but NOT schema adherence. (openai.com structured-outputs; developers.openai.com prompt-guidance "trust tool handling… don't port legacy over-specification"; anthropic.com effective-context-engineering "minimal viable context"; model-spec.openai.com role precedence Root>System>Developer>User.)
**Proven in-repo:** `_route_domain` (`server.py:11598-11638`) already uses strict json_schema + `enum` + `chat_template_kwargs:{enable_thinking:False}` + in-code enum validation against the same `:11450` lane. WS-H = copy that template. **Backend gotcha (solved there):** llama.cpp #20345 silently drops the grammar when thinking is on → must pair the schema with `enable_thinking:False`.

Strict-mode rules every schema obeys: all props in `required`; `additionalProperties:false` everywhere (kills invented verbs); "optional"=nullable union `["string","null"]`; validation keywords ignored (only structure+enums enforced); a safety **refusal** returns `refusal` + `content=null` → guard before `json.loads`.

## WS-H1 — Refine classifier → Structured Outputs  **[P1, highest value]**
Owner: `server.py` `_REFINE_SYSTEM_LITE` (6722-6896), payload (7935-7941), parse (7995-8035).
- Add `_refine_response_format(verb_names, agent_names, domain_names)` → strict json_schema for the envelope `{intent enum[chat,dispatch,agent,multi_task], refined_text, news, web, local_state, needs_location, browser_action, domain_type, state_scope?, inventory_filter?, intended_outcome?, target_agent?(enum agents+null), hint_tools[](enum verbs), tool?(enum verbs+null), args?(object additionalProperties:true — the one escape hatch), reply?, tasks?[]}`. **Enums projected from `_VERB_CATALOG.keys()` / agents / `_ROUTING_DOMAINS` (SSOT, never hardcoded).**
- Payload: add `response_format` + `chat_template_kwargs:{enable_thinking:False}`; **drop the `/no_think` suffix** (7934); replace the obsolete "NO response_format" comment (7930-7933) with the `_route_domain`/#20345 pointer.
- Parse: collapse the 3-tier fallback (8003-8028) to one happy path + refusal guard; drop `_loads_lenient`/`_salvage_refine_dispatch` from the refine success path (keep `<think>`-strip defensively).
- Prompt trim: delete the `Fields:` block (6726-6816) + emission/anti-invention prose (the enum makes an unlisted verb undecodable); **KEEP** the chat/dispatch/agent/multi_task judgement, "classify by NEED not keyword", local-vs-external, domain_type=both→multi_task split, the GROUNDING/no-fabrication rule, the LANGUAGE rule. ~175→~65 lines.
- **Remove the interim WS-G word-heavy recency/web prose once this verifies** (the `news`/`web` booleans are enum-typed; the kept NEED + GROUNDING rules carry the meaning).
- Gate behind `MIOS_REFINE_STRUCTURED` (SSOT toggle, default-on after verify; fallback to prose+lenient on out-of-enum/refusal).

## WS-H2 — Router → Structured Outputs  **[P2]**
Owner: `_ROUTER_SYSTEM` (1887-2054), payload (2076 `json_object`), parse (2102-2107).
- Upgrade `json_object`→strict json_schema `{action enum[dispatch,chat,agent], tool?(enum verbs+null), args?}` + `enable_thinking:False`; delete the `"action" not in parsed` guard (now unreachable).
- **Delete the hand-written `[WRITE]/[READ]` verb table in `_ROUTER_SYSTEM` (~1400 tok)** — it duplicates `_VERB_CATALOG` in prose (SSOT violation); the `tool` enum IS the projection. ~1400→~150 tok. Gate `MIOS_ROUTER_STRUCTURED`.

## WS-H3 — Lean, MiOS-specific prompts  **[P2]**
Keep only MiOS-specific facts the model can't know (what MiOS is, its tools/ports/CLIs, dual Win/Linux nature, failure-mode playbooks, anti-"Smart Window" identity, grounding rules); delete generic agent-behavior prose ("act don't narrate", "never fabricate", "how to call a tool").
- `hermes-soul.md` 47.5KB/~11.9k tok → ~3k tok (long-form to lazy `hermes-soul-full.md`).
- `_AGENT_CONTRACT` (~1355 tok, injected 4×/turn at 12525/19856/21034/23016) → ~400 tok (cut the generic half; keep fleet pointer + refined-query-carry + thinking-block convention).
- `_CLIENT_TOOLS_IDENTITY` (19802, ~330 tok) keep (justified MiOS-specific). `system.md`/OWUI cover: light pass.
- Consolidate generic identity into ONE authoritative developer-role message (Model-Spec precedence); per-hop injections carry only the MiOS runtime delta.

## WS-H4 — Responses API decision  **[decided]**
**STAY on Chat Completions + `tools` + `response_format`.** Responses' wins (server-side state, hosted tools, cache) are OpenAI-cloud features; the local fleet (llama.cpp :11450, SGLang :11441, vLLM :11440) universally implements Chat Completions + response_format but only partial Responses. Keep agent-pipe's internal loop Responses-shaped (turn id, typed items, KV paging) so a cloud Responses lane is additive later. Structured outputs work identically under both — zero rework.

## Backend feasibility
Light lane `:11450` (llama.cpp via llama-swap, `--jinja`, micro=LFM2-700M) supports json_schema via GBNF — **already exercised by `_route_domain`**. All classifier calls resolve here → migrate now. Heavy/heavy-alt (SGLang/vLLM, gated off) also support it but aren't on the classifier path. The only gotcha = #20345 (pair schema with `enable_thinking:False`).

## Phased rollout (SSOT toggles via mios.toml→install.env; enums from _VERB_CATALOG)
- Ph0: keep the interim WS-G guard live (done).
- Ph1: WS-H1 refine→structured (helper + payload + parse-collapse + prompt-trim + remove interim edit), gated `MIOS_REFINE_STRUCTURED`.
- Ph2: WS-H2 router→structured + delete the prose verb table, gated `MIOS_ROUTER_STRUCTURED`.
- Ph3: WS-4a-e (planner DAG / swarm planner / DCI / critic / reflect) — same template; kills the swarm-planner `_loads_lenient` crutch (#20345 again).
- Ph4: WS-H3 prompt trim (prose-only).

## Verification (read-only / curl-probe; operator verifies behavior in OWUI)
Offline unit: schemas satisfy strict-mode; `tool`/`action` enums == `sorted(_VERB_CATALOG.keys())` (SSOT-parity test catches prose-table drift); no lenient parse on refine success path. Live curl battery to `:11450` with each schema + `enable_thinking:False`: 200 + non-empty content + valid json + intent/action in-enum across chat/dispatch/agent/multi_task/local/news/web. Journal: refine `parse_fail` + router `None` → ~zero. Token before/after vs targets. Behavioral: operator confirms Forza-vs-Discord routing, "open discord" no fan-out, domain_type=both still splits.

## Risks
Grammar-compile latency (bounded enums; cached) · #20345 regression on a backend swap (in-enum validate + empty/refusal guard → fall through to council; `MIOS_*_STRUCTURED=false` reverts) · `args` not strictly typed (downstream validates) · over-trimming SOUL/contract (trim generic only, keep MiOS facts, lazy `-full.md`, prose revert) · enum staleness if someone reintroduces a hand-written list (SSOT-parity unit test fails the build).

## Key refs
Refine: 6722-6896 / build 7889-7912 / payload 7935-7941 (/no_think 7934, obsolete comment 7930-7933) / parse 7995-8035. Router: 1887-2054 / 2076 / 2102-2107. **Template to copy: `_route_domain` 11598-11638** (#20345 at 11601). Endpoints: REFINE :11450 (2158), ROUTER (1326), PLANNER (1344). Backend: `usr/share/mios/llamacpp/mios-llm-light.yaml` (--jinja 52/101). Trim targets: `usr/share/mios/ai/{hermes-soul,hermes-soul-full,system}.md`, agent-contract.md (inject 12525/19856/21034/23016), `_CLIENT_TOOLS_IDENTITY` 19802, OWUI mios-agent.md.
