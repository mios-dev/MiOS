# MiOS Knowledge Index (v1)

The authoritative pointers for an MiOS Agent or external tool that
needs to know "what doc covers X." Paths assume a real MiOS host with
the canonical FHS in place; everything below is bind-mounted into the
Open WebUI container so MiOS-Agent's knowledge collection (registered
by `mios-owui-apply-knowledge`) reads each one directly from these
locations.

## Agent self-knowledge (load-bearing)

| File | Purpose |
|---|---|
| `/usr/share/mios/ai/system.md` | Canonical MiOS system prompt -- agent identity, stack table, architectural laws, Day-N loop, interaction rules |
| `/usr/share/mios/ai/INDEX.md` | System interface reference -- API surface, profile/env layering, ports, pipeline phases |
| `/usr/share/mios/ai/hermes-soul.md` | Hermes-Agent persona seeded into `~/.hermes/SOUL.md`; truthfulness rules + delegation discipline |
| `/usr/share/mios/ai/audit-prompt.md` | MiOS audit/review checklist |
| `/usr/share/mios/open-webui/system-prompts/mios-agent.md` | OWUI-side reinforcement prompt for the MiOS-Agent model |
| `/usr/share/mios/ai/v1/system.md` | Stable-URL v1 mirror of `system.md` (for tools that pin to the v1 surface) |
| `/usr/share/mios/ai/v1/knowledge.md` | This file |

## Versioned data surface (`v1/`)

JSON manifests served at the `/v1/<file>` agent surface. Tools that
pin to the v1 schema read these directly (no parsing of the
human-prose docs).

| File | Content |
|---|---|
| `/usr/share/mios/ai/v1/models.json` | OpenAI-compatible models listing (per Architectural Law 5) |
| `/usr/share/mios/ai/v1/tools.json` | Hermes tool catalog -- terminal, file, web, delegation, skills, memory, todo, session_search, code_execution |
| `/usr/share/mios/ai/v1/mcp.json` | MCP server registry -- agents read this to populate `tools=[{type:"mcp", server_url:...}]` for `/v1/responses` |
| `/usr/share/mios/ai/v1/surface.json` | Per-port service surface map (mirrors INDEX.md §6 in machine-readable form) |
| `/usr/share/mios/ai/v1/context.json` | Agent context + endpoint metadata |
| `/usr/share/mios/ai/v1/config.json` | Minimal AI connection config (base_url, default_model, key) |
| `/usr/share/mios/ai/v1/system-prompts.json` | Index of available system prompts under `/etc/mios/system-prompts/` |

## Stack roles (the seven seams under "MiOS Agent")

| Role | Process / binary | Port | Purpose |
|---|---|---|---|
| **MiOS-Hermes** | `hermes-agent.service` (host-direct, venv at `/usr/lib/mios/hermes-agent/.venv/bin/hermes`) | `:8642` | OpenAI-compat agent gateway: sessions, tool-calling, kanban, skills, memory |
| **MiOS-Prefilter** | `mios-delegation-prefilter.service` | `:8641` | HTTP forwarder; injects `tool_choice=delegate_task` on fan-outable user prompts |
| **MiOS-Inference** | `ollama.service` (Quadlet) | `:11434` | Raw model + embeddings backend |
| **MiOS-Delegate** | `qwen3:1.7b` children spawned by `delegate_task(tasks=[...])` | (in-proc) | CPU-side parallel fanout pool (≤6 concurrent, depth 2) |
| **MiOS-OpenCoder** | `opencode` at `/usr/lib/mios/opencode/bin/opencode` | (ACP over stdio) | Coding sub-agent reachable via `delegate_task(... acp_command:"opencode")` |
| **MiOS-Search** | `mios-searxng.service` (Quadlet) | `:8888` | Local SearXNG; backs `web_search` + OWUI's web-augmentation toggle |
| **MiOS-OWUI** | `mios-open-webui.service` (Quadlet) | `:3030` | Browser front-end; routes through MiOS-Prefilter → MiOS-Hermes |

## Architectural laws (host-installed)

| File | Purpose |
|---|---|
| `/CLAUDE.md` | Claude-Code-specific overrides (loading order, deltas, scratch dirs) |
| `/AGENTS.md` | Generic agents.md-standard architectural laws + agent guidance |
| `/.cursorrules`, `/.clinerules`, `/GEMINI.md` | Per-tool agent entry points (Cursor, Cline, Gemini) |
| `/.github/ai-instructions.md` | GitHub Copilot |

## Operator docs

| File | Purpose |
|---|---|
| `/usr/share/mios/docs/day-0/BOOTSTRAP.md` | First-time bootstrap install flow |
| `/usr/share/mios/docs/day-0/FIRST-BOOT.md` | First-boot service ordering + sentinel files |
| `/usr/share/mios/docs/day-n/SELF-REPLICATION.md` | The Day-N self-build loop -- MiOS builds the next MiOS |
| `/usr/share/mios/docs/root-origin/REPO-IS-ROOT.md` | The "repo IS the OS root" contract |
| `/usr/share/mios/docs/root-origin/DUAL-WHITELIST.md` | mios.git + mios-bootstrap.git sharing one filesystem via `.gitignore`-as-whitelist |
| `/usr/share/mios/docs/terminal/INVOCATIONS.md` | One-liner irm/iex install invocations |

## Cookbooks (worked examples)

| File | Purpose |
|---|---|
| `/usr/share/mios/cookbooks/local-rag-day0.md` | Stand up local RAG on day-0 |
| `/usr/share/mios/cookbooks/ingest-kb.md` | Ingest a knowledge base into the local stack |
| `/usr/share/mios/cookbooks/finetune-flow.md` | Local fine-tune pipeline |

## Hermes skills (the agent's playbook)

| File | When the agent should reach for it |
|---|---|
| `/usr/share/mios/hermes/skills/mios-environment/SKILL.md` | Anything touching MiOS-specific paths/services -- the surface map |
| `/usr/share/mios/hermes/skills/parallel-fanout/SKILL.md` | Whenever 2+ independent terminal/file/web calls would otherwise serialise -- delegate to MiOS-Delegate instead |

## Host system prompts (operator-overridable role personas)

| File | Role |
|---|---|
| `/etc/mios/system-prompts/mios-engineer.md` | Engineer role -- design + implement |
| `/etc/mios/system-prompts/mios-reviewer.md` | Reviewer role -- audit + critique |
| `/etc/mios/system-prompts/mios-troubleshoot.md` | Troubleshoot role -- diagnose + repair |

## Single source of truth for configuration

| File | Purpose |
|---|---|
| `/usr/share/mios/mios.toml` | Vendor defaults (immutable, USR-OVER-ETC) -- the SSOT |
| `/etc/mios/mios.toml` | Host override (operator-managed) |
| `~/.config/mios/mios.toml` | Per-user override (highest precedence) |
| `/usr/share/mios/PACKAGES.md` | All RPM installs (fenced ` ```packages-<category> ` blocks) |

## Repo + build entry points (for tool-side context)

| File (in the git working tree) | Purpose |
|---|---|
| `/Containerfile` | OCI image build definition (single-stage with `ctx` scratch context) |
| `/Justfile` | Linux build orchestrator (invokes the ~48 phase scripts under `/usr/libexec/mios/phases/`) |
| `/SECURITY.md` | Hardening, SELinux, sysctl, firewall posture |
| `/CONTRIBUTING.md` | Code conventions + submission process |
