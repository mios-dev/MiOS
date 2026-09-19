# Conformance — what this plugin is built against (mid-September 2026)

Run `sh skills/dev-loop/scripts/validate.sh` (CI gate). Items are MUST / SHOULD / MAY; each names its source.

## Agent Skills open standard (agentskills.io; living spec, six frontmatter keys)
- MUST `SKILL.md` frontmatter ⊆ {name, description, license, compatibility, metadata, allowed-tools}; `metadata` is a string→string map. → core skill as shipped; sub-skills after `artifacts.py strip-frontmatter` (what `install.sh` does for non-Claude harnesses).
- MUST `name` ≤ 64 chars, lowercase/digits/hyphens, no `--`, equals the directory name; `description` ≤ 1024 chars; body < 500 lines / ~5000 tokens.
- MUST resources in `scripts/` (code), `references/` (docs, plural), `assets/` (templates, schemas, examples) — one level deep. No root `reference/`.
- SHOULD validate with the reference SDK: `pip install skills-ref` → `agentskills validate <skill dir>`.
- MAY Claude Code extensions (`context: fork`, `agent`, `argument-hint`, `disable-model-invocation`, `hooks`, `effort`, `model`) on skills that only ship inside the plugin; stripped for every other harness and before any claude.ai/Skills API upload.
- MAY signing/provenance — no standard exists; ship `sha256sum -c` manifests or sigstore yourself if you need it.

## Claude Code plugin (code.claude.com/docs/en/plugins-reference, hooks)
- MUST `.claude-plugin/plugin.json` with `name`; only that file inside `.claude-plugin/`; **no `entrypoint`**; path keys `skills|agents|hooks|commands|mcpServers|lspServers|outputStyles` only; correct types (`keywords` array).
- MUST `hooks/hooks.json` = `{"hooks": {"<Event>": [{"matcher"?, "hooks": [{"type": "command", "command": "...", "timeout"?, "async"?, "if"?}]}]}}` — events keyed by name in the current 33-event list; handler key is `command` (or `url` / `server`+`tool` / `prompt`). Not `{"hooks":[{"event":…,"script":…}]}`.
- MUST agents `agents/*.md` with frontmatter `name` + `description`; `isolation` only `worktree`; no `hooks`/`mcpServers`/`permissionMode` (ignored in plugin agents).
- MUST components at plugin root; no root `commands/` unless every file in it is a Claude command (ours live in `shims/<harness>/` to avoid recursive auto-discovery).
- SHOULD `claude plugin validate <plugin dir> --strict` green (validate the plugin dir, not only the marketplace — issue #60725); `${CLAUDE_PLUGIN_ROOT}` for bundled paths; `worktree.baseRef: "head"`; version ≥ 2.1.219.
- SHOULD Stop gates emit JSON `{"decision":"block"}` (plugin exit-2 Stop hooks are unreliable, #10412) and honour `stop_hook_active` + a hard cap.
- SHOULD protect `.claude/settings.json` and run `/sandbox` with `sandbox.failIfUnavailable: true` (CVE-2026-25725 lesson).

## Contract files (agents.md — Linux Foundation / AAIF, no schema)
- SHOULD `AGENTS.md` is the single source of truth; `CLAUDE.md` = `@AGENTS.md` (< 200 lines), `GEMINI.md`, `.agents/rules/`, `.github/copilot-instructions.md` (+ `.github/instructions/*.instructions.md` `applyTo`), `.cursor/rules/*.mdc`, `opencode.json` `instructions`, Codex `AGENTS.override.md` are pointers → `artifacts.py bridges`.

## Interop
- SHOULD expose the orchestrator as an **MCP server** (2026-07-28 model: stateless, explicit handles; also answers the ≤2025 `initialize` handshake) → `scripts/devloop_mcp.py`, registered in `.mcp.json`. Tools: `validate_lanes`, `run_lanes`, `gate`, `probe`, `tasks_next`, `task_set`, `ledger`, `report`, `scaffold`.
- MAY **ACP** (agentclientprotocol.com, wire v1) for editor hosts: run any lane agent under Zed/JetBrains through the vendor adapter (`claude-code-acp`, `codex-acp`, Gemini/agy native). Not bundled — the lane contract and report block are the same.
- MAY **A2A** v1.0 only for remote, cross-organisation lane delegation; not a dependency.
- First-class lane adapters: Claude Code (Agent SDK/`-p`), OpenAI (Codex + Responses/Agents SDK + any Chat Completions server), Antigravity `agy` (Gemini CLI kept as a legacy alias; consumer Gemini CLI access ended 2026-06-18), Copilot CLI, Cursor `agent`, OpenCode.

## Safety (OWASP LLM Top 10 2026, OWASP Agentic ASI01–ASI10 v2.01, SLSA/sigstore, OpenSSF)
- MUST least-privilege tool lists per agent/skill; destructive ops behind `PreToolUse` deny + operator confirmation (ASI01 goal hijack, ASI02 tool misuse, LLM 2026 #3 excessive agency).
- MUST secrets gate (`gitleaks` — feature-complete, security patches only; successor **Betterleaks** drop-in — plus GitHub push protection) and supply-chain gate (`osv-scanner`, ecosystem audits, provenance) before merge/dependency change.
- SHOULD OS sandbox per harness (Claude `/sandbox` Seatbelt/bubblewrap, Codex Seatbelt/Landlock/bubblewrap, Antigravity terminal sandbox, OpenCode permissions, Cursor `cli.json`); bounded autonomy (`maxTurns`, `timeout_s`, `max_budget_usd`; re-approve long MCP task TTLs).
- MAY mutation gate (`lane.mutation_cmd`; threshold project-defined, ~0.8 on changed files as a starting point).
