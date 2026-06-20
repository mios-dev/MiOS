<!-- AI-hint: Research + conformance record for MiOS's A2A protocol surface and Open Agent Passport — the 2026 native standards for inter-agent interop and verifiable agent identity — and how MiOS exposes both alongside its OpenAI-compatible API.
     AI-related: usr/lib/mios/agent-pipe/server.py, usr/share/mios/mios.toml, /.well-known/agent-card.json, /.well-known/agent-passport.json -->

# A2A + Agent Passport — OpenAI & native conformance (2026-06-20)

Operator directive: *"make sure A2A and agent passports are researched to be
OpenAI and native."* This records the research, the authoritative specs, and how
MiOS conforms — exposing **both** the native agent standards **and** the
OpenAI-compatible API on the same front door (`agent-pipe` :8640).

## A2A (Agent2Agent) — native inter-agent protocol

- **Spec:** Agent2Agent Protocol **v0.3.0** — <https://a2a-protocol.org/v0.3.0/specification/>
  (open project, a2aproject/A2A). Core objects: **AgentCard, Task, Message,
  Artifact**. Discovery via **`/.well-known/agent-card.json`**. JSON-RPC 2.0
  transport (`message/send`, `tasks/get`, ...). There is **no `v1.0.0`** tag —
  0.3.x is current GA, so MiOS pins `protocolVersion: "0.3.0"` honestly.
- **AgentCard required fields (v0.3.0):** `name, description, url, version,
  protocolVersion, capabilities, skills, defaultInputModes, defaultOutputModes,
  preferredTransport`. Optional: `provider, iconUrl, documentationUrl,
  securitySchemes, security, additionalInterfaces, supportsAuthenticatedExtendedCard,
  signatures` (JWS).
- **MiOS conformance (`_build_agent_card`, agent-pipe):**
  - All required fields present; skills are SSOT-derived from `[agents.*]`.
  - **OpenAI + native:** the card's primary `url` = the native JSON-RPC endpoint
    `/a2a` with `preferredTransport: "JSONRPC"` (a STANDARD A2A transport, so a
    strict peer can drive MiOS natively), and **`additionalInterfaces`** advertises
    BOTH `{JSONRPC /a2a}` and `{OpenAI /v1}`. Previously the card claimed a bespoke
    `preferredTransport: "OpenAI"` with no native interface — fixed 2026-06-20.
  - Task/Message/Artifact lifecycle verified live: `POST /a2a message/send` →
    `Task(state=completed)` with proper Message history + `artifacts[]`.
  - Capabilities advertised: streaming, pushNotifications, stateTransitionHistory,
    contextSharing.
- **Follow-ups (optional, not blocking):** AgentCard `signatures` (JWS) for card
  integrity; `securitySchemes`/`security` once auth is enforced on `/a2a`.

## Agent Passport — native verifiable identity

- **Spec:** **Open Agent Passport v0.1.0** (Cubitrek, 2026-04-28) —
  <https://cubitrek.com/blog/agent-passport>. One signed JSON at
  **`/.well-known/agent-passport.json`**; **Ed25519** (RFC 8032) over a
  **canonical JSON** of the document with `signature.value` emptied; public key
  published as a **DNS TXT** at `_agent-passport.{domain}`
  (`v=ap1; kid=<keyId>; alg=ed25519; pk=<base64url>`). Answers identity questions
  the A2A card does not: who issued the agent, allowed **scope** + **spend
  ceiling**, **human-in-the-loop** escalation/SLA, **decision-audit** + **terms**
  URLs, compliance (data classification, regions, subprocessors), validity window,
  revocation. Context: NIST AI Agent Standards Initiative (Feb 2026); OAuth/OIDC
  were built for humans, not programmatic/ephemeral agents.
- **MiOS implementation (`_build_agent_passport`, agent-pipe, new 2026-06-20):**
  - Serves the full **v0.1.0** schema at `/.well-known/agent-passport.json`,
    SSOT-derived from `[agent_passport]` + `[identity]` (no hardcoded identity;
    agent = the advertised "MiOS AI" model).
  - **Ed25519-signed** (canonical JSON, `signature.value=""` rule) when a private
    key is provisioned (`[agent_passport].signing_key_path` / `MIOS_AGENT_PASSPORT_KEY`);
    otherwise **degrades open** — schema-valid but UNSIGNED and flagged
    (`x-mios-unsigned`) so the operator can later add a key + DNS TXT to make it
    verifiable. This is the #60 "signed principal / passport" foundation.
  - To make it verifiable: set `signing_key_path` to an Ed25519 key and publish the
    DNS TXT at `signing_key_dns` (both documented in `mios.toml [agent_passport]`).

## Net

MiOS is discoverable as a **native A2A agent** (JSON-RPC `/a2a`, v0.3.0 AgentCard,
Task/Artifact) **and** an **OpenAI-compatible** model ("MiOS AI" on `/v1`),
advertised together via `additionalInterfaces`, and publishes a **native Open
Agent Passport** for verifiable identity. The internal lane/model ids and service
unit names stay as plumbing; only wire-advertised identity is "MiOS AI".

Sources: <https://a2a-protocol.org/v0.3.0/specification/> ·
<https://github.com/a2aproject/A2A> · <https://cubitrek.com/blog/agent-passport>
