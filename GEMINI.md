> _`/GEMINI.md` — per-tool stub for the **Gemini CLI** on MiOS. Identity SSOT is
> **`/MiOS.md`** (the canonical MiOS AI system identity, OpenAI agent-prompting
> pattern). This stub does NOT re-state the agent identity, posture, or
> tool-loop — it only records Gemini-CLI-specific loading order and the
> endpoint binding. No hardcoded topics, apps, or keywords._

# GEMINI.md

## Role and Objective

Gemini CLI runs as a **MiOS agent**. **Operate under `/MiOS.md`** — that file is
the single canonical system identity (Role & Objective · Persistence ·
Tool-calling · Planning & Decomposition · Output · Standard) for every agent on
this host. Load it and behave exactly as it specifies; everything below is the
Gemini-CLI delta only.

## Loading order

Layered identity SSOT (highest wins):

1. Load `/MiOS.md` (vendor canonical).
2. Apply `/etc/mios/MiOS.md` if present (host/admin override).
3. Apply `~/.config/mios/MiOS.md` if present (per-user override).

## Standard — endpoint binding

Gemini routes through the same **OpenAI-API-compatible** endpoint as every other
MiOS agent (`MIOS_AI_ENDPOINT`, default `http://localhost:8080/v1`) per
**Architectural Law 5 (UNIFIED-AI-REDIRECTS)**. Runtime is **llama.cpp /
llama-swap** (GGUF); identity is injected per-request by agent-pipe. **No
`gemini.googleapis.com` endpoints; no proprietary protocols** — function-calling
and the tool-calling loop go through the OpenAI-compatible surface only.
