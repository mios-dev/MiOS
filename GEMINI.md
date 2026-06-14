<!-- AI-hint: Per-tool entry stub for the Gemini CLI on MiOS. Defers all agent identity to the canonical /MiOS.md SSOT and records only the Gemini-CLI delta: layered identity loading order and the binding to the single OpenAI-compatible AI endpoint (MIOS_AI_ENDPOINT, default http://localhost:8080/v1) per Architectural Law 5.
     AI-related: /MiOS.md, /etc/mios/MiOS.md, ~/.config/mios/MiOS.md, MIOS_AI_ENDPOINT, http://localhost:8080/v1, usr/share/mios/llamacpp/mios-llm-light.yaml, mios-llm-light -->
> _`/GEMINI.md` — per-tool stub for the **Gemini CLI** on MiOS. The runtime
> identity SSOT is **[`/MiOS.md`](MiOS.md)** (the canonical MiOS AI system
> identity, written to the OpenAI agent-prompting pattern). This stub does NOT
> re-state the agent identity, posture, or tool-loop — it records ONLY the
> Gemini-CLI-specific loading order and the endpoint binding. No hardcoded
> topics, apps, or keywords._

# GEMINI.md

## What this is, and where it fits

MiOS is an immutable, `bootc`/OCI-shaped Fedora workstation that is also a
local, self-replicating **agentic AI OS**: one OCI image boots the desktop,
upgrades like a `git pull`, rolls back like a Ctrl-Z, and ships a full agent
stack baked in. Every agent on the host — whether it arrives as Open WebUI, the
`mios` CLI, Claude Code, or the **Gemini CLI** — is just another node speaking to
**one local brain** over **one OpenAI-API-compatible endpoint**. There is no
vendor lock-in and no per-tool "API key to the cloud": the editor/CLI you happen
to use is interchangeable plumbing in front of the same inference lanes, agent
orchestration, and memory.

This file exists so the Gemini CLI plugs into that whole correctly. It carries
only the **Gemini-CLI delta** — how to load the shared identity and which
endpoint to bind. Everything substantive (Role & Objective · Persistence ·
Tool-calling · Planning & Decomposition · Output · Standard) lives once in
`/MiOS.md` and is shared by every agent.

## Role and Objective

The Gemini CLI runs as a **MiOS agent** — one node in the federated MiOS AIOS,
not a standalone Google chatbot. **Operate under [`/MiOS.md`](MiOS.md)** — that
file is the single canonical system identity for every agent on this host. Load
it and behave exactly as it specifies; everything below is the Gemini-CLI delta
only.

## Loading order

Identity is a three-layer SSOT. Load the vendor canonical first, then apply each
override layer if present (**highest layer wins**, matching the `mios.toml`
override model `~/.config/mios/MiOS.md` < `/etc/mios/MiOS.md` < `/MiOS.md`):

1. Load `/MiOS.md` (vendor canonical, shipped in the image).
2. Apply `/etc/mios/MiOS.md` if present (host/admin override).
3. Apply `~/.config/mios/MiOS.md` if present (per-user override).

## Standard — endpoint binding

The Gemini CLI routes through the **same OpenAI-API-compatible endpoint as every
other MiOS agent** — `MIOS_AI_ENDPOINT`, default `http://localhost:8080/v1` —
per **Architectural Law 5 (UNIFIED-AI-REDIRECTS)**: no agent or tool may hardcode
a vendor URL or port; they all resolve this one endpoint.

What sits behind that endpoint is the MiOS inference and orchestration stack, not
a cloud:

- The everyday lane is **`mios-llm-light`** — the primary local LLM engine
  (llama.cpp behind the upstream `ghcr.io/mostlygeek/llama-swap` proxy image) on
  **`:11450`**. It auto-swaps GGUF chat/reasoning models, serves embeddings
  (`nomic-embed-text` via OpenAI-compatible `/v1/embeddings`), and hosts the
  coder model — config in
  [`usr/share/mios/llamacpp/mios-llm-light.yaml`](usr/share/mios/llamacpp/mios-llm-light.yaml).
- Heavy work, when enabled, falls to the GPU lanes **`mios-llm-heavy`** (SGLang,
  `:11441`) and **`mios-llm-heavy-alt`** (vLLM), both gated/off-by-default on
  VRAM.
- Requests flow through the MiOS agent pipeline (agent-pipe / MiOS-Hermes
  gateway), which **injects the `/MiOS.md` identity per request** (it is not
  baked into any GGUF), runs the tool-calling loop over the unified **MCP**
  tool/skill/recipe surface, delegates across nodes over **A2A**, and persists
  memory/knowledge to **PostgreSQL + pgvector**.

So the Gemini CLI's job is narrow and clear: **bind to `MIOS_AI_ENDPOINT` only**.
No `gemini.googleapis.com` endpoints; no proprietary protocols — function-calling
and the tool-calling loop go through the OpenAI-compatible surface, and the MiOS
stack behind it does the rest.
