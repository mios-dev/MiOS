<!-- AI-hint: The OpenAI public /v1 API surface is the ONE addressable AI contract across all of MiOS, exposed through a single front door (MIOS_AI_ENDPOINT, agent-pipe :8640); read before adding any AI endpoint, agent, lane, tool, or federated peer — none may speak a non-OpenAI shape. -->
<!-- AI-related: MIOS_AI_ENDPOINT, automation/lib/globals.sh:133, usr/share/mios/mios.toml [ai].endpoint + [hermes].endpoint + [ports] + [security.nohc_allowlist], usr/lib/mios/agent-pipe/server.py, usr/share/mios/ai/INDEX.md, usr/share/doc/mios/reference/api.md -->
---
adr: 0006
title: OpenAI-API-only AI contract (the governing AI standard)
status: accepted
date: 2026-07-12
deciders: [operator, ai-pair]
tags: [ai, openai, api, contract, agent-plane, endpoint, federation]
laws: [5]
ssot_keys: [ai.endpoint, hermes.endpoint, ports.hermes, ports.agent_pipe, security.nohc_allowlist]
related_ws: [WS-DEPRED]
supersedes: []
superseded_by: []
---

# ADR-0006: OpenAI-API-only AI contract (the governing AI standard)

## Status
Accepted — 2026-07-12. The contract is in force (Law 5). The single-front-door
*collapse* (Hermes → agent-pipe, WS-DEPRED) is partly DONE, partly PLANNED — see
Consequences for the honest split.

## Context

MiOS is an immutable bootc/OCI Fedora image that is **also** a local,
self-hosted, agentic AI OS. The "self-hosted agent OS" half ships *inside* the
image: inference lanes, an orchestration/dispatch gateway, a pgvector agent
datastore, and MCP/A2A tools. For any of this to compose — for agents, lanes,
tools, and federated peers to be *interchangeable* — there must be exactly one
addressable AI contract. If every component spoke a different shape (a vendor
proprietary chat API here, a bespoke local lane there, a retired port
elsewhere), nothing would be substitutable and every integration would be
bespoke.

MiOS already has **Law 5 (UNIFIED-AI-REDIRECTS):** every agent and tool targets
`MIOS_AI_ENDPOINT`; no vendor cloud URLs, no vendor-specific agent/product names,
no retired local lanes in code, docs, or commits (enforced by
`99-postcheck.sh:item12`). And it already has an established endpoint convention:
`MIOS_AI_ENDPOINT` is the one OpenAI-compatible front door, named by *function*
not by upstream tool, backed by a plane of lanes (llama.cpp light lane :8450,
optional heavy GPU lanes vLLM/SGLang, agent-pipe dispatch :8640, pgvector :8432,
SearXNG :8899). The `OpenAI-API-only` convention is already stated in `CLAUDE.md`.

What was missing was elevating that convention to an **explicit, ADR-level
standard** — the governing AI decision that everything else in the agent plane
derives from — and pinning it to the precise OpenAI surfaces. There is also a
live simplification (WS-DEPRED): the gateway plane currently has more than one
front door (`agent-pipe :8640`, a "Hermes" surface `:8642`, a `prefilter :8641`
hop), and the OpenAI-API-only standard is exactly the principle that says these
must collapse to **one**.

## Decision

**The OpenAI public API surface is the ONE addressable AI contract across all of
MiOS, exposed through a SINGLE front door named by `MIOS_AI_ENDPOINT`
(agent-pipe, `:8640`).** Every agent, lane, tool, and federated peer speaks
OpenAI `/v1`; there is no vendor-proprietary AI surface and no retired local API
shape anywhere in code, docs, or commits.

The addressable surfaces are the OpenAI public API, by name:
- **`/v1/chat/completions`** — the primary chat/completions surface (streaming SSE).
- **`/v1/responses`** — the Responses API (stateful/agentic surface), including
  **MCP via the Responses API**.
- **`/v1/embeddings`** — embeddings (backs pgvector RAG/recall).
- **`/v1/models`** — model discovery (front-ends populate their picker from it).
- **Function / tool calling** — the OpenAI tool-calling schema.
- **Structured outputs** — OpenAI structured-output / JSON-schema responses.

Every MiOS agent, lane, and node is therefore an **interchangeable OpenAI
endpoint**: a federated peer, a remote blade's lane, and the local light lane are
all reachable through the same `/v1` shape, so the agent-pipe can fan out across a
fleet and clients can target any of them identically. This is Law 5
(UNIFIED-AI-REDIRECTS) elevated to an explicit standard, and it is the reason
MiOS's agents/lanes/nodes are substitutable.

**One front door (WS-DEPRED).** The gateway plane collapses to a single
`/v1` front door at `agent-pipe :8640`. agent-pipe already owns the `/v1` surface
(`/chat/completions` + `/responses` + `/embeddings` + `/models`), the native
tool-loop, skills, sessions, auth (bearer→principal), MCP, and pgvector — so the
"Hermes" `:8642` surface and the `:8641` prefilter hop are folded in and retired,
keeping exactly ONE OpenAI front door rather than a `:8642` that secretly forwards
to `:8640`. `MIOS_AI_ENDPOINT` resolves to `http://localhost:8640/v1`.

## Rationale

- **Law 5 (UNIFIED-AI-REDIRECTS) made explicit.** Law 5 already forbids vendor
  cloud URLs, vendor-specific product names, and retired local lanes, and requires
  everything to target `MIOS_AI_ENDPOINT`. This ADR states the positive standard
  Law 5 implies: that endpoint speaks the OpenAI `/v1` contract, and *only* that.
- **Interchangeability is the payoff.** One contract makes agents, lanes, and
  nodes drop-in substitutable — the whole federated/fan-out design depends on it.
  A single front door means genuinely one entry point, not a chain of forwarders.
- **Upstream precedent.** The OpenAI API is the de-facto lingua franca of local
  inference — llama.cpp/llama-swap, vLLM, and SGLang all expose OpenAI-compatible
  `/v1` servers, so standardizing on it costs nothing and buys tool compatibility
  across the entire local-AI ecosystem. MCP via the Responses API is the
  standardized tool/agent transport.
- **Law 7 (NO-HARDCODE) alignment.** The front door is referenced by
  `MIOS_AI_ENDPOINT`, never a hardcoded literal; canonical ports are allowlisted in
  `mios.toml [security.nohc_allowlist]` rather than scattered as magic numbers.
- **Legacy already purged.** The AI plane is `/v1`-only: ollama/localai/surrealdb
  were entirely removed, `MIOS_OLLAMA_*`→`MIOS_LLM_*`, `local-ollama`→`local-llm`,
  and the retired `:8080`/`:11434` shapes were purged corpus-wide. This ADR
  ratifies that end-state as the standing standard so no proprietary or retired
  shape re-enters.

## Alternatives considered

- **Allow vendor-proprietary AI surfaces alongside OpenAI `/v1`.** Rejected:
  breaks interchangeability, re-introduces vendor lock-in, and violates Law 5. No
  vendor cloud URLs or product names in code/docs/commits.
- **Keep multiple front doors (agent-pipe `:8640` + Hermes `:8642` + prefilter
  `:8641`).** Rejected: `:8642` today is a thin shell whose own model is `:8640`
  and whose MCP verbs call back into `:8640`; the live Open WebUI front-end already
  bypasses `:8642` and points at `:8640`. Multiple doors is complexity with no
  contract benefit — collapse to one (WS-DEPRED).
- **Retain a retired local lane shape (`:11434`/`:8080`) for compatibility.**
  Rejected: nothing serves those; they are Law-5 violations if referenced. (A
  handful of `:8080` references are intentionally kept as *raw llama.cpp default*
  examples and test fixtures — not the MiOS endpoint — and must not be "fixed" into
  the endpoint.)

## Consequences

Positive:
- Every AI component is an interchangeable `/v1` endpoint; federation and fan-out
  are uniform; clients target one shape.
- One front door to secure, audit, and document.
- New agents/tools/lanes have a single integration target.

Negative / honest costs & DONE-vs-PLANNED:
- **DONE:** agent-pipe owns four of six gateway responsibilities outright (the
  `/v1` surface, the tool-loop, skills, auth); the live Open WebUI front-end
  already talks only to `:8640/v1`; the legacy `/v1`-only purge
  (ollama/localai/surrealdb removed, retired ports purged) is complete;
  `[security.nohc_allowlist]` allowlists `:8640` and `:8642`.
- **PLANNED (WS-DEPRED), the honest current state:** `MIOS_AI_ENDPOINT` today
  still resolves to **Hermes `:8642`** — `automation/lib/globals.sh:133` sets
  `: "${MIOS_AI_ENDPOINT:=http://localhost:${MIOS_PORT_HERMES}/v1}"` and
  `mios.toml [ports] hermes = 8642`. The load-bearing change is to repoint that
  default (and `[ai].endpoint`/`[hermes].endpoint`) to `${MIOS_PORT_AGENT_PIPE}`
  (`:8640`), add `8640` to `[security.nohc_allowlist]`, retire the
  `mios-delegation-prefilter.service` (`:8641`) hop, absorb `gateway_sessions`
  into agent-pipe, and retire/alias `mios-gateway-agent.service` (`:8642`,
  already `enable=false`). Until that lands, the standard is stated and mostly
  wired, but the single front door is agent-pipe *behind* a `:8642` default —
  the collapse finishes the decision.
- **OPEN QUESTION (blocks full removal of the upstream "Hermes" brain):** the
  browser/CDP path is the one true Hermes-only runtime capability (native
  `browser_*` against ChromeDev `:9222`). Recommended resolution: expose CDP as
  MCP `browser_*` verbs so agent-pipe drives it through its existing MCP path,
  keeping `mios-hermes-browser.service` as a pure executor. Also reconcile the
  `hermes` CLI/Discord/kanban surfaces bundled in the same venv — drop or re-home
  explicitly, don't orphan.

## Implementation

- `C:\MiOS\automation\lib\globals.sh:133` — the `MIOS_AI_ENDPOINT` default. Repoint
  `:${MIOS_PORT_HERMES}/v1` → `:${MIOS_PORT_AGENT_PIPE}/v1` (WS-DEPRED step 1).
- `C:\MiOS\usr\share\mios\mios.toml` — `[ai].endpoint` / `[hermes].endpoint`,
  `[ports] hermes = 8642` / `agent_pipe = 8640`, and
  `[security.nohc_allowlist]` (add `8640`; drop `8642` once removed).
- `C:\MiOS\usr\lib\mios\agent-pipe\server.py` — the single `/v1` front door:
  `/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, `/v1/models`,
  tool-loop, skills, sessions, auth, MCP, pgvector. Enforced by
  `automation/99-postcheck.sh:item12` (Law 5).
- Retire `mios-delegation-prefilter.service` (`:8641`); retire/alias
  `mios-gateway-agent.service` (`:8642`).
- Contract references: the full API contract is
  `usr/share/doc/mios/reference/api.md`; the agent-facing architectural contract is
  `usr/share/mios/ai/INDEX.md`. (Note: `usr/share/mios/docs/agents/AI-ARCHITECTURE.md`
  carries stale WSL-loopback ports — `mios.toml [ports]` is authoritative.)
- Cross-references: ADR-0001 (the AI-core bake group carries agent-pipe/pgvector
  as core-of-core), ADR-0005 (the run-off-M: portproxy forwards `:8640` — the
  front door named here).

## References

- OpenAI API reference (the addressable surfaces, by name):
  <https://platform.openai.com/docs/api-reference>
- OpenAI Chat Completions: <https://platform.openai.com/docs/api-reference/chat>
- OpenAI Responses API (agentic/stateful, MCP tool transport):
  <https://platform.openai.com/docs/api-reference/responses>
- OpenAI Embeddings: <https://platform.openai.com/docs/api-reference/embeddings>
- OpenAI function/tool calling: <https://platform.openai.com/docs/guides/function-calling>
- OpenAI structured outputs: <https://platform.openai.com/docs/guides/structured-outputs>
- Model Context Protocol (MCP): <https://modelcontextprotocol.io/>
- OpenAI-compatible local servers: llama.cpp
  (<https://github.com/ggml-org/llama.cpp>), vLLM
  (<https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html>), SGLang
  (<https://docs.sglang.ai/>).
- MiOS Law 5 (UNIFIED-AI-REDIRECTS): `usr/share/mios/mios.toml [laws]`,
  enforced by `automation/99-postcheck.sh:item12`.
- MiOS memory: AI-endpoint-canonical, legacy-purge → `/v1`-only.
