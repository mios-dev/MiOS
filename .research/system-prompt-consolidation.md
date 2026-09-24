> **Monitor corrections (verified against the tree; read before acting on this document):**
> 1. Section 3 and the migration plan propose DELETING the repo-root artifact tarballs. Do not.
>    The operator confirmed they are the operator's training artifacts for mios-micro.
> 2. The audit calls the `not_mirrored` entry for AGENT-ARTIFACT-SYSTEM-PROMPT.md a silenced
>    gate. Measured, it is not: `not_mirrored` is the sync gate's own mechanism for
>    intentionally different files, and the canonical-plus-pointer pair is exactly that. It is
>    committed (f43cb3d). The real gap is that nothing checks the bootstrap copy STAYS a pointer.
> 3. The 'Claude Code loads neither repo's AGENTS.md' finding is CONFIRMED: 0 `@AGENTS.md`
>    import lines in either CLAUDE.md.

<!-- Research staging (.research/). Design input for the consolidation manager. Not a shipped prompt. -->
# System-prompt consolidation and partitioning: design

Date: 2026-09-24. Read-only synthesis of four research notes (harness instruction files, OpenAI prompt structure, projection and drift, internal audit), plus spot checks by the synthesizer.

**Pinned state (both trees are being edited while this was written):**
- **MiOS:** HEAD `1be9bf5` on `claude/mios-dev-loop-startup-4elr0n`; `origin/main` is `df42b9f`. There are uncommitted edits to `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.clinerules`, `usr/share/mios/mios.toml`, `TASKS.md` and `.devloop/*`.
- **mios-bootstrap:** HEAD `c156452`, up from `a3941d5` when the audit started. There are uncommitted edits to `CLAUDE.md`, `.cursorrules` and `.clinerules`.
- **Every lane below must re-read HEAD before it starts.**

---

## 1. Summary: the target shape

1. **Three planes, one canonical source each, never mixed.**
   - A, dev-harness contract: root `AGENTS.md` per repo.
   - B, runtime AI identity: `usr/share/mios/ai/prompts/*.md` fragments plus `mios.toml`.
   - C, external artifact and research agents: `.agents/agents/*.md`.
2. **Runtime prompts are split into ordered partitions:**
   - P10 identity
   - P20 policy (laws)
   - P30 tool contract
   - P35 grounding
   - P40 host overlay
   - P50 role
   - P60 user overlay
   - P70 task
   - P80 untrusted data

   Layers are added together by partition. A layer never replaces the whole prompt.
3. **One Rust generator, `tools/native/mios-prompt-gen`, with `--check`,** projects the fragments plus `mios.toml [laws]/[ports]/[ai]` into:
   - `usr/share/mios/ai/v1/system-prompts.json` (the OpenAI-format registry)
   - `/MiOS.md`, `hermes-soul*.md`, the Open WebUI prompt, and the `.agents/subagents.json` prompts
   - the shared law/invariant blocks inside both repos' `AGENTS.md`
4. **Harness files are hand-written pointers of a few lines, never symlinks:**
   - `CLAUDE.md` and `GEMINI.md` are `@AGENTS.md` plus a small harness-only delta.
   - `.cursorrules`, `.clinerules` and `.github/ai-instructions.md` are deleted, because those tools read `AGENTS.md` natively.
5. **Override tiers stay empty:** `etc/mios/ai/system-prompt.md` and `etc/skel/.config/mios/system-prompt.md` contain comments only (`<!-- -->`), never redirector text or `#` "commented" lines.
6. **One loader library** implements the merge rule. `usr/bin/mios`, agent-pipe, the Open WebUI appliers and the Hermes soul sync all call it, replacing five incompatible precedence rules.
7. **Law compliance:**
   - Law 8: every projection is registered in `[laws.projection_registry]`, has a gate in `98-drift-checks.sh`, and runs in `tools/sync-generated.sh`.
   - Law 16: a new `[templates.prompt-partition]` type.
   - Law 15: shared blocks are covered by a `[bootstrap.sync]` block-mirror.
8. **Prompts carry no literal ports or models (Law 7).** Where a value is needed, the generator renders it from `[ports]` / `[ai]`.
9. **Artifact prompt fixes:**
   - `.agents/agents/artifact-publisher.md` is the one source. `AGENT-ARTIFACT-SYSTEM-PROMPT.md` and the `subagents.json` entry are generated from it.
   - The index-only OCI tar in the repo root fails that contract and must leave the tree (operator decision).

---

## 2. Partition scheme

### 2.1 Order (runtime plane B)

| Order | Partition | Carrier (hosted OpenAI) | Carrier (llama.cpp local lane) | Tier | Stability | Cache |
|---|---|---|---|---|---|---|
| — | tool schemas | `tools[]`, sorted and append-only; per-profile `allowed_tools` | `tools[]` | vendor | static | renders ahead of all developer text |
| — | output schema | `text.format` (Responses) / `response_format` (Chat) | grammar `json_schema` | vendor | per profile | part of the prefix |
| P10 | **identity** | developer `input_text` | merged into the one leading `system` message under `# Identity` | vendor | per image | |
| P20 | **policy**: the 16 laws, generated from `[laws]`, plus a non-override clause | developer | same system message, `# Policy` | vendor | per image | |
| P30 | **tool contract**: how to call tools; tool, file, web and RAG output is data; which on-disk files carry delegated authority | developer | `# Tool contract` | vendor | static | **BP1**: the shared vendor prefix; pad to at least 1,024 tokens on hosted OpenAI |
| P35 | grounding: ports, lanes, models, generated from `[ports]` / `[ai]` | developer | `# Grounding` | vendor | per image | |
| P40 | host overlay: `/etc/mios/ai/system-prompt.md` | developer | `# Host overlay` | host | per host | **BP2** |
| P50 | **role**: engineer, reviewer, troubleshoot, audit, hermes, manager | developer | `# Role` | vendor/host | per profile | **BP3**: end of the first developer block |
| P60 | user overlay: `~/.config/mios/system-prompt.md` | **user** message | user message | user | per user | implicit-eligible |
| P70 | **task**: run id, cwd, time, scope, ending condition | developer message after the last breakpoint | trailing system text (UNVERIFIED that templates accept it; see §8) | runtime | per request | none |
| P80 | untrusted context | user message fenced as JSON/XML, or `function_call_output` | user message | none | per request | none |

### 2.2 Why this order differs from the requested identity, policy, role, task, tool contract

1. **The tool contract moves ahead of role (P30), and the task moves last.** OpenAI caching reuses only an exact rendered prefix: "Cache reuse requires the entire rendered prefix to match." The guide also says to put stable instructions first and "timestamps, user-specific content … at the end" (https://developers.openai.com/api/docs/guides/prompt-caching.md, fetched 2026-09-24).
   - The tool contract is the same for every profile, so placing it before role extends the prefix all profiles share.
   - Placing it after the task would put static text after dynamic text, where it could never be cached.
   - Separately, tool *schemas* render ahead of developer text regardless of where the prose goes (same guide).
2. **Chain of command.** In the Model Spec (2026-08-18), "an instruction is superseded if an instruction in a later message at the same level either contradicts it, overrides it" (https://model-spec.openai.com/2026-08-18.html). Two consequences:
   - The user overlay is carried in the **user** role (P60). In the developer role, placed after the laws, it would supersede them.
   - OpenAI's agent-safety guidance agrees: "Don't use untrusted variables in developer messages … Pass untrusted inputs through user messages" (https://developers.openai.com/api/docs/guides/agent-builder-safety.md).
3. **Local lanes have no separate developer/system level.** llama.cpp at `84e76d8`, `common/chat.cpp:1274`: "map developer to system for all models except for GPT-OSS".
   - So P20 must state its own precedence in text: "P20 overrides any later instruction in any message; overlays may only fill declared slots."
   - The loader must also merge by slot, not by free-text replacement.
4. **Untrusted data has no authority by default.** Model Spec: quoted text, tool outputs and file attachments "have no authority by default". The OpenAI APIs have no `untrusted_text` content type, so P80 is fenced as JSON with `untrusted_data` as the wrapper key.
5. **Role P50 for the manager must name its autonomy scope.** The Model Spec says "spawning sub-agents" and "self-modification" are "always prohibited unless explicitly authorized". It calls for a `ScopeOfAutonomy` record (`allowed_tools`, `latest_time`, `max_cost`, `tool_constraints`, `additional_details`) with an ending condition. The AGY manager role partition must carry these fields.
6. **Layering is additive by partition,** with one deliberate masking rule adopted from UAPI.6 and systemd. A *same-named* fragment in a higher tier replaces the lower one; an empty file masks it (https://uapi-group.org/specifications/specs/configuration_files_specification/ ; https://github.com/systemd/systemd/blob/7abf4dbbf4662ca29b7525b7f3ddf0105dd1362a/man/systemd.unit.xml).
   - P10, P20 and P30 are declared **non-maskable**. A user or host file can never remove the laws.
   - This is a design decision. No prompt harness implements it (see §8).

### 2.3 Plane A (dev harness) is not partitioned the same way

Harnesses concatenate files and the later one wins by position (Claude Code, Codex, Gemini CLI). There are no roles. In plane A:
- identity and policy are root `AGENTS.md`;
- the harness-only delta is `CLAUDE.md` / `GEMINI.md`;
- task is the user's prompt.

The shared text in plane A (the 16 laws, the Blade invariant, "Global code form") is a **generated block**, rendered from the same `[laws]` and the P10/P20 fragments. Both planes therefore state the laws from one source.

---

## 3. Canonical-source map

**Legend:**
- **CANONICAL**: hand-edited source of truth.
- **POINTER**: hand-written file of a few lines using a real import (`@AGENTS.md`).
- **GEN(g)**: generated by generator g and gated by `--check`.
- **GEN-BLOCK**: only the text between `MIOS-GEN` markers is generated.
- **EMPTY-SLOT**: comment-only override tier.
- **DELETE** / **MOVE**: remove the file, or move it to the path given.

`pg` means `tools/native/mios-prompt-gen`, which is new.

### 3.1 MiOS (`/home/user/MiOS`)

| Current file | Disposition | Owner |
|---|---|---|
| `AGENTS.md` (22,219 B) | CANONICAL for plane A. The laws, invariants and Global-code-form section become GEN-BLOCK(pg). Remove the "entry point for mios-bootstrap.git" text on line 5 and the "Owns: AI files (`usr/share/mios/ai/`)" text on line 62. Budget: 20,000 B or less (the Antigravity cap is 24,000 B). | MiOS |
| `CLAUDE.md` (16.5 KB) | POINTER: line 1 is `@AGENTS.md`, followed by a Claude-only delta of 60 lines or fewer (the confirm-before list, complete-replacement deliverables, memory/scratch paths). Remove the full 16-law duplicate, which moves into the AGENTS.md GEN-BLOCK. The AI-hint's "six architectural laws" goes away with it. | MiOS |
| `GEMINI.md` (8.9 KB) | POINTER: `@AGENTS.md`, then a Gemini-only delta. Remove the bootstrap self-description. | MiOS |
| `MiOS.md` (3,577 B) | GEN(pg): P10+P20+P30 rendered as Markdown. This is the file agent-pipe actually loads (`server.py:1691-1712`). Kept as a compatibility projection until L4 moves the loader onto the registry. Fix the "Fedora Rawhide/Silverblue" base-image claim. | MiOS |
| *(new)* `usr/share/mios/ai/prompts/10-identity.md`, `20-policy.md.in`, `30-tool-contract.md`, `35-grounding.md.in`, `roles/*.md` | CANONICAL runtime fragments. The `.in` files hold slots that pg fills from `[laws]` / `[ports]` / `[ai]`. | MiOS |
| `usr/share/mios/ai/system.md` (12,283 B) | GEN(pg) from P35 grounding plus P30. It stays at this path because `usr/bin/mios` and ~15 docs name it. Fix the stale build facts: single-stage, `phases/`, `PACKAGES.md`, and the gateway-agent entry. | MiOS |
| `usr/share/mios/ai/agent-contract.md` | GEN(pg): condensed P10+P20. It is the loader's fallback. | MiOS |
| `usr/share/mios/ai/INDEX.md` | CANONICAL architecture document. Its §3 law table (8 laws, stale) becomes GEN-BLOCK(pg) from `[laws]`. | MiOS |
| `usr/share/mios/ai/audit-prompt.md` | MOVE to `usr/share/mios/ai/prompts/roles/audit.md` (role only; drop the repeated identity and "six Laws"). | MiOS |
| `usr/share/mios/ai/hermes-soul.md`, `hermes-soul-full.md` | GEN(pg): P10+P20+P30 plus `roles/hermes.md`. The path is kept because `mios-hermes-soul-sync:8` and `mios-hermes-firstboot` read it. | MiOS |
| `usr/share/mios/ai/v1/system-prompts.json` (1,007 B, hand-written) | GEN(pg) in the shape given in §5. It currently hardcodes the retired port 8640 and uses a `role` field that collides with OpenAI message `role`. | MiOS |
| `etc/mios/system-prompts/mios-{engineer,reviewer,troubleshoot}.md` | MOVE to `usr/share/mios/ai/prompts/roles/{engineer,reviewer,troubleshoot}.md` (role content only). Law 1: vendor content does not belong in `/etc`. `/etc/mios/ai/prompts/roles/` becomes a masked override directory. Consumers: `mios-owui-apply-system-prompt`, `mios-owui-apply-knowledge`, and `globals.sh`/`.ps1` (via render-globals). | MiOS |
| `usr/share/mios/open-webui/system-prompts/mios-agent.md` | GEN(pg), read by `mios-owui-apply-system-prompt:34`. | MiOS |
| `mios.toml [owui.system_prompt].template` (2,633 chars) | DELETE the literal. `mios-owui-install-pipe:138` reads the generated `mios-agent.md`, or the registry, instead. | MiOS |
| hardcoded identity in `grounding.py` (`_arch_grounding`, the `_p_heavy` default 8530) | DELETE the literals. Read the registry or `[ports]` instead. | MiOS |
| `system-prompt.md` (root, 2,904 B) | POINTER for external chat apps: a few lines of prose naming `usr/share/mios/ai/system.md`. `install-mios-agents.sh:35` must stop copying it over `system.md` (see §6). | MiOS |
| `etc/mios/ai/system-prompt.md` (664 B, a redirector) | EMPTY-SLOT (`<!-- host overlay; see … -->` only). | MiOS |
| `etc/skel/.config/mios/system-prompt.md` (1,175 B; in `[bootstrap.sync].mirror_files`) | EMPTY-SLOT. Replace the `# - …` lines, which are active H1 headings, with `<!-- -->`. `sync-bootstrap.py` mirrors it byte-identically. | MiOS (mirrored) |
| `etc/mios/ai/config.json` (port 8640) | GEN(pg), or render from `[ports]`/`[ai]`. It is `not_mirrored`, but the bootstrap copy (8642) is a second value for the same path: see L6. | MiOS |
| `install-mios-agents.sh` | CANONICAL script. Stop writing to `/usr` and reverse its precedence. Remove the `8642` / `mi-os-7b` defaults and the "six Laws" question. | MiOS |
| `.cursorrules`, `.clinerules` (0 B at HEAD; the uncommitted tree adds text containing `8642`) | DELETE. Cursor and Cline read `AGENTS.md` natively. **Do not commit the uncommitted `8642` text.** | MiOS |
| `.github/ai-instructions.md` | DELETE. Copilot does not read this filename; it reads `AGENTS.md`. | MiOS |
| `.github/agents/*.agent.md` | GEN(pg) from `.agents/agents/*.md` plus Copilot frontmatter, or DELETE if unused. UNVERIFIED consumer. | MiOS |
| `.agents/rules/AGENTS.md` (3,910 B, no frontmatter) | DELETE. It is probably discarded by Antigravity (no `trigger:`), and root `AGENTS.md` is native. Any rule that is genuinely AGY-only goes in `.agents/rules/00-mios.md` with `trigger: always_on` frontmatter. The retired ports 8642 and 11434 go with it. | MiOS |
| `.agents/plugins/mios-cicd/rules/AGENTS.md` (604 B) | DELETE, or GEN(pg) with `trigger:` frontmatter. The plugin path is UNVERIFIED as a load location. | MiOS |
| `.agents/agents/artifact-publisher.md` | **CANONICAL for plane C** (the artifact agent). | MiOS |
| `.agents/agents/{mios-dev,pipeline-*}.md` | CANONICAL per agent. | MiOS |
| `.agents/subagents.json` | GEN(pg): each `system_prompt` rendered from `.agents/agents/<id>.md`, so the roster equals the directory. That adds `mios-dev`, which is missing today. | MiOS |
| `.agents/workflows/agents.md` | CANONICAL workflow. Its agent list becomes a GEN-BLOCK from the roster. | MiOS |
| `AGENT-ARTIFACT-SYSTEM-PROMPT.md` (3,229 B) | GEN(pg): the body of `artifact-publisher.md` with a `<!-- Source: … -->` marker. It stays a full copy because external chat apps have no import. Remove the restated OCI/dataset gates. | MiOS |
| `.mios/system-prompt.md` (17,294 B) | CANONICAL research/report contract (plane C, task tier). Fix the `mios-dev/mios-dev-loop` repo name (lines 20, 28 and 41) and `justfile` → `Justfile`. Settle the cloning contradiction (lines 385-387). | MiOS |
| `.prompt.MD` | POINTER (prose) to `.mios/system-prompt.md` and `artifact-publisher.md`. Remove the duplicated "daily run" paragraph. | MiOS |
| `.prompts/README.md` | CANONICAL catalog. Add the registry path. | MiOS |
| `artifact.md` (26,879 B; 11 of 21 embedded paths missing) | MOVE to `.research/archive/artifact-bundle-2026-09.md`, or DELETE. It is not a prompt. Its §16–18 task prompts go into `.agents/agents/`. | MiOS |
| `mios-training-oci-image-2026-09-24.tar` (index-only; `blobs/sha256/` empty) | DELETE from the tree after operator confirmation. It fails the artifact contract's descriptor-closure gate. | MiOS |
| `mios-{micro,ai-training-data}-artifact-2026-09-24.tar.gz`, `mios-devcontainer-harness-bundle-2026-09-2{1,2}.tar.gz` | DELETE or MOVE out of the source tree (operator decision). The contract says "never in a MiOS source checkout", and two of them hold stub scripts. | MiOS |
| `usr/share/mios/prompts/*.xml.md` (5 files) | CANONICAL task prompts (P70 templates). Remove each file's own `<role>` / identity text and reference a role id instead. `troubleshoot.xml.md` currently declares MiOS-Engineer. Fix "six Laws" and the `PACKAGES.md` path. | MiOS |
| `commands/{claude,codex,copilot,cursor,gemini}/*` (24–37 B stubs); `commands/agy` ≡ `commands/antigravity` | GEN(pg) from one command template, or DELETE the stubs. De-duplicate the `agy`/`antigravity` directories. | MiOS |
| `usr/share/mios/llamacpp/mios-llm-light.yaml` + `llama-swap.yaml` (byte-identical; one is a tracked symlink) | Keep one canonical name. Prompts cite only that name. Out of scope for prompt text beyond the citation. | MiOS |
| `usr/share/doc/mios/manual/system.md`, `mios.md`, `_harvest/*` | Not prompts. Already GEN(`mios-manual`). No change. | MiOS |

### 3.2 mios-bootstrap (`/home/user/mios-bootstrap`)

| Current file | Disposition | Owner |
|---|---|---|
| `AGENTS.md` (19,314 B; 16 retired-port literals; dead ADR link) | CANONICAL for bootstrap plane A. The shared laws, invariants and code-form section become a GEN-BLOCK mirrored from MiOS by a new `[bootstrap.sync].mirror_blocks`. Replace literal ports with `[ports]` key names. Remove the claim that bootstrap owns `usr/share/mios/ai/`. | bootstrap |
| `CLAUDE.md` | POINTER: `@AGENTS.md` plus a Claude-only delta. Fix the model table: phi4-mini is the *bootstrap* default, not the vendor default, and the thresholds are RAM keys, not VRAM keys. The uncommitted tree already disowns `usr/share/mios/ai/`. | bootstrap |
| `GEMINI.md` | POINTER: `@AGENTS.md` plus a delta; no literal ports. | bootstrap |
| `system-prompt.md` | POINTER (prose) to MiOS `usr/share/mios/ai/system.md`. Remove the port literal. | bootstrap |
| `.cursorrules`, `.clinerules` (hardcoded `8642`) | DELETE. | bootstrap |
| `AGENT-ARTIFACT-SYSTEM-PROMPT.md` (a pointer at `c156452`) | POINTER to the MiOS canonical. Remove the unsupported "Law 8 compliant" claim. Link a pinned ref or `main` *after* the MiOS fix merges. | bootstrap |
| `etc/skel/.config/mios/system-prompt.md` | MIRROR of MiOS (written only by `sync-bootstrap.py`; no lane edits it by hand). | MiOS (mirror) |
| `etc/mios/ai/config.json` (8642, `qwen3.5:2b`) | DELETE from bootstrap. It double-tracks a path MiOS generates. If an operator override is needed, it belongs in `~/.config/mios/mios.toml`. | → MiOS |
| `mios.toml [ai].endpoint = http://localhost:8642/v1` | Fix it to resolve from `[ports].agent_pipe`. This is a Law 7 and Law 5 retired-port violation. | bootstrap |

---

## 4. Per-harness loading table (checked 2026-09-24)

| Harness | What it reads | How it reaches the canonical `AGENTS.md` | Hazard / guard | Source |
|---|---|---|---|---|
| Claude Code | managed `/etc/claude-code/CLAUDE.md` → `~/.claude/CLAUDE.md` → ancestors `CLAUDE.md` → `CLAUDE.local.md`; `@path` imports up to 4 hops | `CLAUDE.md` line 1 is `@AGENTS.md`. Native AGENTS.md reading is **off** whenever a `CLAUDE.md` exists (default `claude-md-or-agents-md`). Plain text or a backticked `` `AGENTS.md` `` is **not** an import. | **Today neither repo's AGENTS.md is loaded.** Confirmed by this session: only the CLAUDE.md files were injected. `-dev-loop/CLAUDE.md` = `@AGENTS.md` works. | https://code.claude.com/docs/en/memory |
| Gemini CLI | `~/.gemini/GEMINI.md`, workspace plus ancestors up to `.git`, just-in-time subdirectories; default filename `GEMINI.md` only | `GEMINI.md` has `@AGENTS.md` (inlined; depth 5). The alternative, `.gemini/settings.json` `{"context":{"fileName":["AGENTS.md","GEMINI.md"]}}`, must **not** be combined with the import. | Choose the import: it needs no settings file, and workspace trust for project settings is UNVERIFIED. | https://geminicli.com/docs/cli/gemini-md/ ; https://geminicli.com/docs/reference/memport/ ; gemini-cli@`cc7e6ad3` |
| Antigravity (`agy`, IDE) | per directory: `AGENTS.md`/`GEMINI.md`, `.agents/{AGENTS,GEMINI}.md`, `.agents/rules/*.md` (direct children; frontmatter `trigger:` required); globals in `~/.gemini/` | Native: root `AGENTS.md` is read directly. The bare `@AGENTS.md` inside `GEMINI.md` does **not** inline in AGY (it only rewrites the path), so there is no double load. | 24,000 B per file (after `@[x](p)` includes); 20,000 tokens across global plus always-on rules. Rule files without frontmatter are silently dropped. The AGENTS.md vs GEMINI.md order is UNVERIFIED. | https://antigravity.google/docs/rules ; https://antigravity.google/docs/skills |
| Codex | `$CODEX_HOME/AGENTS{.override,}.md`, then per directory from the git root down to cwd | Native | 32 KiB combined (`project_doc_max_bytes`) | https://learn.chatgpt.com/docs/agent-configuration/agents-md |
| Cursor | `.cursor/rules/*.mdc`, nested `AGENTS.md`, **and** `CLAUDE.md` (always applied) | Native | It also loads `CLAUDE.md`, so keep the Claude delta small. Delete `.cursorrules` (legacy). | https://cursor.com/docs/context/rules ; https://cursor.com/help/customization/rules |
| Cline | `.clinerules` (file or directory), `.cline/rules/`, root `AGENTS.md` (toggle, on by default) | Native (root only) | UI rule creation turns `.clinerules` into a directory. Delete it. | https://docs.cline.bot/features/cline-rules ; cline@`dd2e190e` |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `AGENTS.md` (nearest wins); code review also reads `CLAUDE.md`/`GEMINI.md`/`REVIEW.md` since 2026-07-17 | Native | `.github/ai-instructions.md` is not a filename it reads. | https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions ; https://github.blog/changelog/2026-07-17-copilot-code-review-customization-and-configurability-improvements/ |
| OpenCode | the first category that matches among `AGENTS.md` > `CLAUDE.md` > `CONTEXT.md`, collected from cwd up to the worktree root | Native | `@file` is not expanded. An empty `AGENTS.md` blocks the fallback. | https://opencode.ai/docs/rules/ ; sst/opencode@`6df0d5d9` `instruction.ts` |
| MiOS runtime: `usr/bin/mios` | `resolve_system_prompt()`: env, user, host, `system.md` (twice) | Move to the shared loader. It reads `v1/system-prompts.json` and builds P10–P80. | Today `system.md` is loaded twice (no realpath dedupe), and `<!-- -->` comments are not stripped. | `usr/bin/mios:161-181` |
| MiOS runtime: agent-pipe | `_AGENT_CONTRACT_PATHS`: the first non-empty of `~/.config/mios/MiOS.md`, `/etc/mios/MiOS.md`, `/MiOS.md`, `agent-contract.md`×3 | Shared loader. `/MiOS.md` stays as a GEN compatibility projection. | Today it *replaces* rather than overlays, so a user `MiOS.md` drops the vendor laws. | `usr/lib/mios/agent-pipe/server.py:1691-1712` |
| MiOS runtime: Open WebUI | `mios-owui-apply-system-prompt` reads `open-webui/system-prompts/mios-agent.md`; `mios-owui-install-pipe` reads `[owui.system_prompt].template` | Both read the generated `mios-agent.md`. | How Open WebUI combines model, user and chat prompts is UNVERIFIED. | `usr/libexec/mios/mios-owui-apply-system-prompt:34`, `mios-owui-install-pipe:138` |
| MiOS runtime: Hermes | `mios-hermes-soul-sync` copies `hermes-soul.md` into the Hermes home, keeping `### MIOS-RUNTIME-CONTEXT-BEGIN` | `hermes-soul.md` is GEN. | Keep the marker contract. | `usr/libexec/mios/mios-hermes-soul-sync:8,12` |
| External chat apps and artifact agents | a pasted file | a GEN full-text copy (`AGENT-ARTIFACT-SYSTEM-PROMPT.md`), or a prose pointer (`system-prompt.md`, `.prompt.MD`) | no import mechanism | — |

**Global and OS tier:** Claude Code's `/etc/claude-code/CLAUDE.md` is the only system-wide harness path. Every other harness is per-user and must be seeded through `/etc/skel` if MiOS ever ships one. That is out of scope here; flag it for a later lane.

---

## 5. OpenAI-format projection: `usr/share/mios/ai/v1/system-prompts.json`

**Design rules:**
- Use the OpenAI list shape (`object: "list"`, `data`). Do **not** model the file on `/v1/prompts`, which "is scheduled to shut down on November 30, 2026" (https://developers.openai.com/api/docs/deprecations.md).
- Each partition holds a ready-to-send Responses API `message` item. Chat and llama.cpp forms are built mechanically by adapters.
- Content is inlined with a sha256 so the gate can regenerate and diff.
- No timestamps and no literal endpoint (Law 7).
- The field is `purpose`, not `role`, so it cannot be confused with the OpenAI message `role`.

```json
{
  "object": "list",
  "schema_version": "mios.system_prompts.v1",
  "generator": "tools/native/mios-prompt-gen",
  "sources": [
    "usr/share/mios/mios.toml#laws",
    "usr/share/mios/mios.toml#ports",
    "usr/share/mios/mios.toml#ai",
    "usr/share/mios/ai/prompts/"
  ],
  "chain_of_command": ["root", "system", "developer", "user", "none"],
  "merge": {
    "mode": "additive_by_partition",
    "mask": "same_name_higher_tier_replaces; empty_file_masks",
    "non_maskable": ["mios.identity", "mios.policy", "mios.tool_contract"],
    "dedupe": "realpath",
    "strip_html_comments": true,
    "local_backend_role_map": { "developer": "system" },
    "local_backend_join": "single_leading_system_message"
  },
  "data": [
    {
      "id": "mios.identity",
      "object": "mios.prompt_partition",
      "order": 10,
      "purpose": "identity",
      "tier": "vendor",
      "stability": "static",
      "authority": "developer",
      "source": "/usr/share/mios/ai/prompts/10-identity.md",
      "sha256": "<hex of item.content[0].text>",
      "cache_breakpoint_after": false,
      "maskable": false,
      "item": {
        "type": "message",
        "role": "developer",
        "content": [{ "type": "input_text", "text": "# Identity\n..." }]
      }
    },
    {
      "id": "mios.policy",
      "object": "mios.prompt_partition",
      "order": 20,
      "purpose": "policy",
      "tier": "vendor",
      "stability": "static",
      "authority": "developer",
      "source": "/usr/share/mios/ai/prompts/20-policy.md.in+mios.toml#laws",
      "sha256": "<hex>",
      "cache_breakpoint_after": false,
      "maskable": false,
      "item": {
        "type": "message",
        "role": "developer",
        "content": [{ "type": "input_text", "text": "# Policy\n..." }]
      }
    },
    {
      "id": "mios.tool_contract",
      "object": "mios.prompt_partition",
      "order": 30,
      "purpose": "tool_contract",
      "tier": "vendor",
      "stability": "static",
      "authority": "developer",
      "source": "/usr/share/mios/ai/prompts/30-tool-contract.md",
      "sha256": "<hex>",
      "cache_breakpoint_after": true,
      "maskable": false,
      "item": {
        "type": "message",
        "role": "developer",
        "content": [{
          "type": "input_text",
          "text": "# Tool contract\n...",
          "prompt_cache_breakpoint": { "mode": "explicit" }
        }]
      }
    },
    {
      "id": "role.engineer",
      "object": "mios.prompt_partition",
      "order": 50,
      "purpose": "role",
      "tier": "vendor",
      "stability": "per_profile",
      "authority": "developer",
      "source": "/usr/share/mios/ai/prompts/roles/engineer.md",
      "sha256": "<hex>",
      "cache_breakpoint_after": true,
      "maskable": true,
      "item": {
        "type": "message",
        "role": "developer",
        "content": [{
          "type": "input_text",
          "text": "# Role: engineer\n...",
          "prompt_cache_breakpoint": { "mode": "explicit" }
        }]
      }
    }
  ],
  "overlays": [
    { "id": "host", "order": 40, "authority": "developer", "path": "/etc/mios/ai/system-prompt.md", "empty_is": "absent" },
    { "id": "user", "order": 60, "authority": "user", "path": "~/.config/mios/system-prompt.md", "empty_is": "absent" },
    { "id": "env",  "order": 60, "authority": "user", "path": "${MIOS_AI_SYSTEM_PROMPT}", "empty_is": "absent" }
  ],
  "profiles": [
    {
      "id": "engineer",
      "partitions": ["mios.identity", "mios.policy", "mios.tool_contract", "mios.grounding", "role.engineer"],
      "allowed_tools": ["<names; the full tools[] list is identical across profiles>"],
      "prompt_cache_key": "mios:engineer",
      "text": { "format": {
        "type": "json_schema", "name": "mios_engineer_report_v1", "strict": true,
        "schema": { "type": "object", "properties": {}, "required": [], "additionalProperties": false }
      } },
      "scope_of_autonomy": null
    },
    {
      "id": "manager",
      "partitions": ["mios.identity", "mios.policy", "mios.tool_contract", "mios.grounding", "role.manager"],
      "allowed_tools": ["<names>"],
      "prompt_cache_key": "mios:manager",
      "text": null,
      "scope_of_autonomy": {
        "allowed_tools": ["<names>"],
        "latest_time": null,
        "max_cost": null,
        "tool_constraints": "sub-agents only in lane worktrees; no edits to AGENTS.md",
        "additional_details": "ending condition: goal stopping conditions hold or budget exhausted"
      }
    }
  ],
  "untrusted_envelope": { "carrier": "user", "format": "json", "wrapper_key": "untrusted_data" }
}
```

**Validation schema.** The file's own schema is published as OpenAI structured-output JSON: `{"type":"json_schema","name":"mios_system_prompts_v1","strict":true,"schema":{…}}` (https://developers.openai.com/api/docs/guides/structured-outputs.md).
- Every key is listed in `required`.
- Nullable fields use `["T","null"]`, for example `text`, `scope_of_autonomy`, `latest_time` and `max_cost`.
- `additionalProperties:false` on every object.
- The root must be an object, not `anyOf`.
- Do not use `allOf`, `not` or `if/then`.
- Enums:
  - `tier`: `vendor|host|user|runtime`
  - `stability`: `static|per_host|per_profile|per_user|per_request`
  - `authority`: `developer|user`
  - `purpose`: `identity|policy|tool_contract|grounding|role|task`

**Size note.** The OpenAI cache minimum for GPT-5.6 and later is 1,024 visible tokens. The vendor prefix P10–P30 should reach it on its own, or be padded (guide: "escape the minimum cacheable length cost trap"). llama.cpp `cache_prompt` has no minimum (`tools/server/README.md` @`84e76d8`).

**Carrier adapters** (implemented in the shared loader, not stored in the file):
- Hosted, stateless: send the partition items as `input` items.
- Hosted with `previous_response_id`: resend P10–P50 as top-level `instructions` on every turn. The docs say instructions are "not carried over"; `instructions` "cannot contain an explicit breakpoint".
- llama.cpp: join P10–P50 into ONE leading `system` message with `#` headers, and remove `prompt_cache_breakpoint`.

---

## 6. Drift and contradictions (with evidence)

Paths are relative to the MiOS repo unless the path says `bootstrap/`.

1. **Claude Code loads no `AGENTS.md` in either repo.**
   - Both `CLAUDE.md` files mention `AGENTS.md` only inside backticks, which is not an import.
   - The docs: "Claude sees AGENTS.md only if it decides to open the file" (https://code.claude.com/docs/en/memory).
   - This session was injected with both `CLAUDE.md` files and neither `AGENTS.md`. `-dev-loop` (`CLAUDE.md` = `@AGENTS.md`) was injected correctly.
2. **The code and the docs disagree on which prompt is canonical.**
   - ~15 files call `usr/share/mios/ai/system.md` canonical, for example both `AGENTS.md` §10, both `system-prompt.md`, `.cursorrules`, and `v1/system-prompts.json`.
   - `system.md` lines 4 and 14 say it is "NOT the identity SSOT" and that `/MiOS.md` is.
   - agent-pipe loads `/MiOS.md` (`server.py:1691-1712`).
   - `grounding.py:322`: `system.md` "is not otherwise injected at runtime".
3. **There are five incompatible precedence rules:**
   - agent-pipe: first non-empty file wins; replacement, user-first (`server.py:1691`);
   - `usr/bin/mios`: concatenates everything, with the user layer last (`usr/bin/mios:161-181`), and includes `system.md` twice (candidates `SHARE/"ai/system.md"` and `__file__/../share/mios/ai/system.md` resolve to the same file on a host);
   - `install-mios-agents.sh` wrappers: `system.md` first, so vendor wins (lines 42, 55, 68, 86);
   - `system.md` line 5: user layer lowest;
   - `v1/system-prompts.json`: declares a `resolution_order` that no code reads.
4. **`install-mios-agents.sh:35-36` copies the root redirector over `/usr/share/mios/ai/system.md`.**
   - The redirector points at itself.
   - It writes to `/usr`, which is read-only under composefs.
   - Its defaults are the retired `8642` and `mi-os-7b`, a model absent from `mios.toml`.
5. **The law count is 16, 6 or 8 depending on the file.**
   - The registry `mios.toml [laws]` has ids 1–16, and `CLAUDE.md:81` lists 16.
   - "Six": the `CLAUDE.md:1` AI-hint (verified in the file header), both `AGENTS.md` at line 73, `build-review.xml.md:3,14`, `troubleshoot.xml.md:19`, `mios-reviewer.md`, `audit-prompt.md`, `v1/metadata.json`.
   - "Eight": `INDEX.md:181-195`, where Law 8 is "K-I-S-S-LANGUAGES". In the registry, Law 8 is SSOT-PROJECTION.
6. **The invariant count differs.**
   - MiOS `AGENTS.md`, `GEMINI.md`, `.agents/rules/AGENTS.md` and the plugin rules say "Five".
   - `GEMINI.md:34-35` says "Five … following four" and then lists five.
   - The bootstrap files carry only the Blade invariant.
7. **The heavy lanes are swapped.** The quadlets: `mios-llm-heavy` = vLLM, `-alt` = SGLang.
   - These say heavy = SGLang `:11441`: bootstrap `CLAUDE.md:156`, bootstrap `AGENTS.md`/`GEMINI.md`, the `INDEX.md` Law 6 row, `artifact.md:83-96`.
   - `grounding.py` `_p_heavy` defaults to 8530 (the SGLang port).
8. **Retired or wrong ports** (`[docs].retired_ports` includes 8640, 8641, 8642, 11434, 11441, 11450, 3030, 8633, 8888, 8899):
   - `v1/system-prompts.json` `endpoint` = 8640 (verified);
   - `etc/mios/ai/config.json` 8640, and `bootstrap/etc/mios/ai/config.json` 8642 (the same path with two values);
   - `.agents/rules/AGENTS.md:21` (8642, 11434);
   - bootstrap `AGENTS.md` (16 literals), `CLAUDE.md`, `GEMINI.md`, `system-prompt.md`, `.cursorrules`;
   - bootstrap `mios.toml [ai].endpoint` 8642;
   - `artifact.md:198,414`;
   - the uncommitted MiOS `.cursorrules`/`.clinerules`;
   - pgvector given as `:5432` in `AGENTS.md:274,356`, `system.md:68`, `INDEX.md:38` and bootstrap files, while the quadlet uses `MIOS_PORT_PGVECTOR` (8600).
   - `MIOS_DOCS_PORT_CLEAN` (`automation/lib/globals.sh:1018`) omits `artifact.md`, `.agents/**`, `v1/*.json`, `.cursorrules` and `config.json`. That likely explains why these went undetected; how the checker consumes the list is UNVERIFIED.
   - Aside: `mios.toml` has a desktop-entry `ai_hint` naming "port 8899" (retired) for SearXNG, seen near `[bootstrap.sync]`.
9. **Model names disagree:**
   - vendor `mios.toml`: `granite4.1:8b` / `mistral-magistral-small-2509`, thresholds 16/8;
   - bootstrap `mios.toml`: `qwen3.5:*` / `phi4-mini`, thresholds 32/12;
   - bootstrap `CLAUDE.md:160-165` calls phi4-mini the "vendor default";
   - `config.json`: "MiOS AI" vs `qwen3.5:2b`;
   - `install-mios-agents.sh`: `mi-os-7b`;
   - `artifact.md`: `llama-3.3-70b-instruct`.
10. **Ownership of `usr/share/mios/ai/` is contradicted.** The directory exists only in MiOS, yet these say bootstrap owns it:
    - `AGENTS.md:62` (baked into the image as `/AGENTS.md` via `Containerfile:13`);
    - bootstrap `AGENTS.md`;
    - bootstrap `CLAUDE.md` at `a3941d5` (fixed in its uncommitted tree);
    - bootstrap `.cursorrules` at HEAD.

    `AGENTS.md:5` also calls itself the bootstrap entry point.
11. **The Law 15 gate: correction to one research note.**
    - `tools/sync-bootstrap.py:129-136` *does* fail on any file tracked in both repos but declared in neither `[bootstrap.sync]` list.
    - At `1be9bf5`, `AGENT-ARTIFACT-SYSTEM-PROMPT.md` was in neither list, so `check_bootstrap_sync` (`98-drift-checks.sh:4813`) should have been red.
    - The **uncommitted** `mios.toml` diff adds it to `not_mirrored`. That silences the gate, and it also means nothing compares the two copies.
    - Likewise `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `system-prompt.md`, `.cursorrules`, `.clinerules` and `etc/mios/ai/config.json` are all `not_mirrored`. The shared law text in them has **no** drift coverage, hence the `mirror_blocks` proposal (L2).
12. **The artifact prompt contradicts itself and the repository:**
    - The dev-loop repo is `mios-dev/-dev-loop` (`AGENT-ARTIFACT-SYSTEM-PROMPT.md` @`1be9bf5`, matching the local clone's origin) vs `mios-dev/mios-dev-loop` (`.mios/system-prompt.md:20,28,41`, which the artifact prompt says to treat as authoritative).
    - It says "fetch/sync repos" while `.mios/system-prompt.md:385-387` "does not authorize cloning".
    - It says artifacts belong "only in an isolated external workspace", yet the MiOS root tracks 5 artifact tarballs (verified with `git ls-files`).
    - `mios-training-oci-image-2026-09-24.tar` is index-only: `tar tf` shows `blobs/`, `blobs/sha256/`, `index.json` and `oci-layout` with no blob (verified). That is exactly the archive the contract says to reject.
    - `artifact-publisher` is defined three times with different wording (`.agents/agents/artifact-publisher.md`, `.agents/subagents.json`, `AGENT-ARTIFACT-SYSTEM-PROMPT.md`).
13. **The subagent roster diverges.** `.agents/agents/` has 6 files, including `mios-dev`; `subagents.json` has 5 (no `mios-dev`); `workflows/agents.md` lists 6.
14. **Law 8 and Law 16 gaps.**
    - `[laws.projection_registry].surfaces` (`mios.toml:2248-2280`, verified) lists no prompt surface.
    - `[templates.*]` (`mios.toml:10211-10409`) has no prompt type, only `markdown-doc`.
    - `v1/system-prompts.json` is hand-written; its only reader is `mios-owui-apply-knowledge:81`.
15. **`system.md` has stale build facts:**
    - it says "single-stage", but the Containerfile has 3 `FROM`s (verified: `ctx`, `rust-builder`, `${BASE_IMAGE}`);
    - it cites `usr/libexec/mios/phases/`, which is missing (the build runs `automation/NN-*.sh` via `automation/build.sh`);
    - it cites `usr/share/mios/PACKAGES.md`, which is missing;
    - it says `mios-gateway-agent.service` is Hermes, while `AGENTS.md:259` says it is the disabled replacement;
    - `MiOS.md` says the base is "Fedora Rawhide/Silverblue", while the Containerfile uses `ucore-hci:stable-nvidia`.
16. **Override tiers inject junk:**
    - the `etc/skel` template's `# - …` lines are H1 headings, so the model receives them as active instructions;
    - `etc/mios/ai/system-prompt.md` is a "Redirector" that gets injected as instructions;
    - `<!-- AI-hint -->` blocks are not stripped by the MiOS loaders.
17. **Antigravity budget.**
    - `AGENTS.md` is 22,219 B, 93% of the 24,000 B per-file cap.
    - AGY also loads `GEMINI.md` (8,932 B at HEAD) and the frontmatter-less `.agents/rules/AGENTS.md` (probably dropped), which restate the same material.
18. **`MiOS/GEMINI.md` was copied from bootstrap.** It calls itself the stub "on mios-bootstrap.git" at HEAD (lines 1, 5, 26). The uncommitted tree changes this.
19. **One model map has two names.** `llamacpp/mios-llm-light.yaml` and `llama-swap.yaml` are byte-identical, and different prompts cite different names.
20. **Dead links:**
    - `build-review.xml.md` cites `usr/share/mios/PACKAGES.md` (it lives at `usr/share/doc/mios/reference/PACKAGES.md`);
    - `.mios/system-prompt.md` says `justfile` (the file is `Justfile`);
    - bootstrap `AGENTS.md` links `cat/ADR-0008.md` (missing) and `bootstrap_install.md` (exists only in MiOS);
    - 11 of 21 paths embedded in `artifact.md` do not exist.
21. **Symlinks are hazardous on Windows.**
    - `Get-MiOS.ps1` (~line 5040) clones without `-c core.symlinks=true`. Git for Windows then checks symlinks out as text files containing the link target (https://gitforwindows.org/symbolic-links ; git `core.adoc`@`0f8e75ab`).
    - Therefore **no prompt file may be a symlink**. The 4 existing tracked symlinks are already exposed.

---

## 7. Migration plan: lanes with exclusive owned paths

**Conventions:**
- Every lane follows the dev-loop lane contract: no `git add/commit/push`, and no edits outside `owned_paths`. The manager (AGY) is the only writer of `.devloop/`, the ledger and merges.
- Every lane re-reads HEAD first, because both trees are under active edit (§ pinned state).
- Every lane runs `just drift-gate` as a baseline before editing and records any pre-existing red.
- **Positive** means the lane's gate passes on the finished tree.
- **Negative** means one planted edit to a *projection* (not a source) makes the named check fail and name the file. The tree is then restored, and `git diff` must show only the intended changes.

### Wave 1 (parallel; no shared paths)

**L1: ssot-registry**
- **Owns:** `usr/share/mios/mios.toml`, and `usr/share/mios/templates/prompt-partition.md` (new).
- **Changes:**
  - add `[templates.prompt-partition]`, the Law 16 template: HTML-comment provenance header, one `# <Partition>` H1, slot markers `{{laws}}` / `{{ports.<key>}}`, and no literal port or date;
  - add `[prompts]`: partition ids, order, tier, maskable, profiles, overlay paths;
  - add `[laws.projection_registry].surfaces` entries for every GEN row in §3 (generator `tools/native/mios-prompt-gen/src/main.rs`, check `check_prompt_projection`);
  - add `[bootstrap.sync].mirror_blocks = [{ file = "AGENTS.md", block = "mios-shared-laws" }]`;
  - add the missing `MIOS_DOCS_PORT_CLEAN` globs (`artifact.md`, `.agents/**`, `usr/share/mios/ai/v1/*.json`, `etc/mios/ai/config.json`) through whatever `mios.toml` key feeds `render-globals.py` (location UNVERIFIED);
  - delete `[owui.system_prompt].template` only after L4 lands (wave 3).
  - Coordinate with the in-flight uncommitted `mios.toml` diff (`not_mirrored` gained `AGENT-ARTIFACT-SYSTEM-PROMPT.md`).
- **Positive:** `just drift-gate` is green; `check_template_self_conformance` and `check_projection_registry` pass; `python3 -c 'import tomllib;tomllib.load(open("usr/share/mios/mios.toml","rb"))'`.
- **Negative:** plant a registry surface whose generator path does not exist. `check_projection_registry` must fail naming it.

**L7: artifact plane**
- **Owns:** `.agents/agents/**`, `.agents/workflows/**`, `.mios/system-prompt.md`, `.prompt.MD`, `.prompts/README.md`, `artifact.md`, and the 5 root `*.tar*` files.
- **Changes:**
  - make `artifact-publisher.md` the single canonical source and fold the §16–18 prompts of `artifact.md` into it;
  - fix the repo name everywhere (`mios-dev/-dev-loop`, matching `origin`; confirm the GitHub redirect status, UNVERIFIED);
  - resolve clone vs no-clone;
  - `justfile` → `Justfile`;
  - move `artifact.md` to `.research/archive/`;
  - **tarball deletion requires operator confirmation** (CLAUDE.md "confirm before `rm -rf`" spirit; these are tracked deliverables).
- **Positive:** `grep -rn "mios-dev/mios-dev-loop" .agents .mios .prompt.MD` returns nothing; `python3 -m json.tool` passes on any JSON touched; an OCI descriptor-closure script over each remaining `*.tar` exits 0.
- **Negative:** re-add the index-only `index.json` to a scratch tar. The closure check must fail and name the missing `sha256:7a513a…` blob.

**L6: bootstrap pointers** (repo `/home/user/mios-bootstrap`)
- **Owns:** `AGENTS.md` (outside the future GEN-BLOCK), `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.clinerules`, `system-prompt.md`, `AGENT-ARTIFACT-SYSTEM-PROMPT.md`, `etc/mios/ai/config.json`, and `mios.toml` (`[ai]` only).
- **Does not own:** `etc/skel/.config/mios/system-prompt.md` (a mirror written by L3 via `sync-bootstrap.py`).
- **Changes:**
  - `CLAUDE.md` / `GEMINI.md` → `@AGENTS.md` plus delta;
  - delete `.cursorrules` and `.clinerules`;
  - replace port literals with key names;
  - fix the model table and ownership text;
  - delete `etc/mios/ai/config.json` and remove it from MiOS `not_mirrored` (ask L1 through the manager);
  - fix `[ai].endpoint`.
- **Positive:** `head -1 CLAUDE.md GEMINI.md` prints `@AGENTS.md` for both; `grep -rnE '\b(8640|8641|8642|11434|11441|11450|3030|8633|8888)\b' AGENTS.md CLAUDE.md GEMINI.md system-prompt.md mios.toml` returns nothing; `wc -c AGENTS.md` is under 20,000; the bootstrap repo's own validator passes (name UNVERIFIED).
- **Negative:** plant `8642` into `GEMINI.md`. The retired-port scan must fail naming `GEMINI.md:<line>`.

### Wave 2 (depends on L1)

**L2: prompt generator and gates**
- **Owns:** `tools/native/mios-prompt-gen/**` (new crate), `tools/sync-generated.sh`, `automation/98-drift-checks.sh`, `tools/sync-bootstrap.py`.
- **Does not own:** `tools/native/Cargo.toml`, which is GEN by `generate-cargo-manifests.py`; regenerate it through `sync-generated.sh`.
- **Changes:** the generator reads `[prompts]`, `[laws]`, `[ports]`, `[ai]` and the fragments, and writes every GEN row. It has `--check`, which exits 1 when anything is stale (the rulesync `generate --check` pattern: https://rulesync.dyoshikawa.com/reference/cli-commands). Every output starts with `<!-- Source: <path> -->`, the ruler pattern (https://github.com/intellectronica/ruler). New gates:
  - `check_prompt_projection`: regenerate and diff every GEN surface, including the `AGENTS.md` GEN-BLOCK and `system-prompts.json`, plus validation against its strict schema.
  - `check_prompt_pointers`: `CLAUDE.md`/`GEMINI.md` in both repos start with `@AGENTS.md` and are at most 80 lines; no deleted harness file (`.cursorrules`, `.clinerules`, `.github/ai-instructions.md`, `.agents/rules/AGENTS.md`) exists; every `.agents/rules/*.md` has a `trigger:` frontmatter.
  - `check_prompt_budgets`: `AGENTS.md` under 20,000 B in each repo; the Codex chain under 32 KiB.
  - `check_prompt_no_symlink`: no prompt or harness file is a symlink (`git ls-files -s` mode 120000).
  - `check_prompt_no_literals`: no `[docs].retired_ports` value and no hardcoded `mios.toml` model id in any prompt surface.
  - `sync-bootstrap.py` gains `mirror_blocks`: it compares the text between `<!-- MIOS-GEN:BEGIN mios-shared-laws -->` and `END` in both repos' `AGENTS.md`.
  - **Do not** depend on rulesync or ruler at build time (Law 12, Law 14, Rust directive).
- **Positive:** `cargo test -p mios-prompt-gen`; `mios-prompt-gen --check` exits 0 on a clean tree; `just drift-gate` is green; `bash -n` on each edited shell file.
- **Negative, run as five separate plants, one at a time:**
  1. Append one byte to `usr/share/mios/ai/v1/system-prompts.json`. `check_prompt_projection` fails naming the file.
  2. Edit one law line inside the bootstrap `AGENTS.md` GEN-BLOCK. `check_bootstrap_sync` fails naming `AGENTS.md#mios-shared-laws`.
  3. Replace `CLAUDE.md` line 1 with `` See `AGENTS.md` ``. `check_prompt_pointers` fails.
  4. `ln -s AGENTS.md CLAUDE.md` in a scratch worktree. `check_prompt_no_symlink` fails.
  5. Create `.agents/rules/x.md` without frontmatter. `check_prompt_pointers` fails.

### Wave 3 (depends on L2)

**L3: runtime fragments** (MiOS)
- **Owns:**
  - `usr/share/mios/ai/prompts/**` (new);
  - `usr/share/mios/ai/{system.md,agent-contract.md,audit-prompt.md,hermes-soul.md,hermes-soul-full.md,INDEX.md}`, `usr/share/mios/ai/v1/system-prompts.json`;
  - `MiOS.md`, `etc/mios/system-prompts/**`, `etc/mios/ai/system-prompt.md`, `etc/mios/ai/config.json`;
  - `etc/skel/.config/mios/system-prompt.md` in both repos (the bootstrap copy only through `sync-bootstrap.py`);
  - `usr/share/mios/open-webui/system-prompts/**`, `usr/share/mios/prompts/*.xml.md`, root `system-prompt.md`.
- **Changes:**
  - author P10, P20.in, P30, P35.in and `roles/{engineer,reviewer,troubleshoot,audit,hermes,manager}.md` from the best current text: `MiOS.md` for identity, `CLAUDE.md` §laws for policy, and `upstream-research.xml.md:29` for correct lane facts;
  - move the `/etc` role files;
  - make the overrides EMPTY-SLOT;
  - run `mios-prompt-gen` to render every GEN target;
  - strip `<role>` from the task prompts;
  - fix the stale facts in §6 items 5, 7, 15 and 20.
- **Positive:** `mios-prompt-gen --check` exits 0; `just drift-gate` is green; `python3 -c 'import json;json.load(open("usr/share/mios/ai/v1/system-prompts.json"))'`; `grep -rn "six\s\+\(architectural \)\?[Ll]aws\|Eight Laws" usr/share/mios etc/mios MiOS.md` returns nothing.
- **Negative:** hand-edit a law line in generated `MiOS.md`. `check_prompt_projection` fails naming `MiOS.md`. Separately, put `# - be terse` into the `etc/skel` template in MiOS only; `check_bootstrap_sync` fails.

**L4: runtime loaders** (MiOS)
- **Owns:**
  - `usr/bin/mios`;
  - `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py`, `usr/lib/mios/agent-pipe/mios_grounding.py`;
  - a new `usr/lib/mios/agent-pipe/mios_pipe/prompts.py` (the shared loader), plus new tests `usr/lib/mios/agent-pipe/test_mios_prompt_loader.py`;
  - `usr/libexec/mios/mios-owui-apply-system-prompt`, `usr/libexec/mios/mios-owui-install-pipe`, `usr/libexec/mios/mios-owui-apply-knowledge`, `usr/libexec/mios/mios-hermes-soul-sync`;
  - `install-mios-agents.sh`.
- **Changes:**
  - one loader implements the §5 `merge` block (additive by partition, dedupe by realpath, strip HTML comments, non-maskable P10–P30, user overlay in the user role, adapters for hosted vs local);
  - every consumer calls it;
  - `install-mios-agents.sh` stops writing `/usr`, and its defaults resolve from `mios.toml`;
  - remove the hardcoded `_arch_grounding` text and the `_p_heavy=8530` default;
  - the Hermes `MIOS-RUNTIME-CONTEXT-BEGIN` contract is preserved.
  - Signal the manager, which tells L1 to delete `[owui.system_prompt].template`.
- **Positive:**
  - `cd usr/lib/mios/agent-pipe && python3 test_mios_prompt_loader.py`, asserting:
    - the vendor text appears exactly once;
    - `<!-- -->` is stripped;
    - a user file cannot remove P20;
    - the user overlay is emitted with `role:"user"`;
    - the llama.cpp adapter yields exactly one leading system message;
  - the existing `test_mios_*.py` pass; `just drift-gate` is green; `bash -n install-mios-agents.sh`.
- **Negative:** re-add the duplicate `__file__`-relative candidate to the loader. The exactly-once test must fail. Separately, a user file consisting only of an empty `20-policy.md` must not mask policy; the test fails if it does.

**L5: MiOS harness pointers**
- **Owns:** `AGENTS.md` (outside GEN-BLOCKs; the generator writes the block), `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.clinerules`, `.github/ai-instructions.md`, `.github/agents/**`, `.agents/rules/**`, `.agents/plugins/mios-cicd/rules/**`, `.agents/subagents.json`, `commands/**`, `AGENT-ARTIFACT-SYSTEM-PROMPT.md`.
- **Changes:**
  - apply the §3.1 dispositions;
  - `AGENTS.md` lines 5 and 62 fixed, shared block inserted, size under 20,000 B;
  - `subagents.json` and `AGENT-ARTIFACT-SYSTEM-PROMPT.md` rendered by `mios-prompt-gen` from L7's `.agents/agents/`;
  - de-duplicate `commands/agy` vs `commands/antigravity`.
  - Discard the uncommitted `8642` edits to `.cursorrules`/`.clinerules` by deleting both files.
  - AGENTS.md, CLAUDE.md and GEMINI.md are baked into the image (`Containerfile:13-15`), so a smaller file also shrinks `/ctx/rootmd`.
- **Positive:** `mios-prompt-gen --check` exits 0; `check_prompt_pointers` and `check_prompt_budgets` pass; `python3 -m json.tool .agents/subagents.json`; a fresh Claude Code session in `/home/user/MiOS` shows `AGENTS.md` in its injected context (manual probe, recorded in the ledger).
- **Negative:** delete the `mios-dev` entry from generated `subagents.json`. `check_prompt_projection` fails naming the roster. Separately, pad `AGENTS.md` to 24,001 B; `check_prompt_budgets` fails.

### Wave 4: manager only

- Update `[bootstrap.sync]` lists: remove `etc/mios/ai/config.json` from `not_mirrored` once bootstrap deletes it.
- Write the ledger entry, run the full `just drift-gate` in both repos, and merge.
- Probe the §8 items that decide design, especially AGY's handling of the AGENTS.md/GEMINI.md order and of an empty AGENTS.md, before closing the goal.

---

## 8. UNVERIFIED claims

**Harness behaviour**
1. Antigravity: the load order of `AGENTS.md` vs `GEMINI.md` in the same directory; its handling of an empty `AGENTS.md`; what it does when a file exceeds 24,000 B (docs say truncation; not probed).
2. Whether Antigravity loads a workspace `.agents/plugins/<name>/rules/`. The documented plugin-rule path is `~/.gemini/antigravity-cli/plugins/<name>/rules/`.
3. That Antigravity actually discards `.agents/rules/AGENTS.md` (the docs say frontmatter-less rules are dropped; not probed on agy 1.2.6).
4. Claude Code: whether an empty `CLAUDE.md` suppresses native AGENTS.md reading (inference: yes).
5. Cursor: the effect of an empty `.cursorrules`; whether `@file` inlines content; `.md` vs `.mdc` in `.cursor/rules` (its docs conflict).
6. Copilot: whether the 4,000-character code-review limit still applies; how empty files are handled.
7. Cline: whether it reads nested `AGENTS.md` (the code reads the root one only).
8. Gemini CLI: whether a project `.gemini/settings.json` needs workspace trust. The design avoids depending on it.

**OpenAI API and local engines**

9. Whether OpenAI implicit caching treats top-level `instructions` as part of the first developer block, and what the Conversations API does with `instructions`. The duplicate-accumulation risk of resending developer `input` items under `conversation` is an inference.
10. The exact rendered order of instructions, tools and output schema beyond the caching guide's illustration.
11. llama.cpp @`84e76d8`: whether `/v1/responses` supports `previous_response_id`/`conversation`; whether it tolerates `prompt_cache_breakpoint`; whether it enforces OpenAI `strict`; whether chat templates accept more than one system message, or one that is not first. This affects where P70 goes on local lanes.
12. How Open WebUI combines model-, user- and chat-level system prompts.

**Design decisions and repository facts**

13. The masking rule for prompt layers (§2.2 item 6) is a MiOS design choice with no prompt-harness precedent.
14. Whether GitHub redirects `mios-dev/mios-dev-loop` to `mios-dev/-dev-loop`.
15. How the port-clean checker consumes `MIOS_DOCS_PORT_CLEAN`, and which `mios.toml` key feeds it.
16. Whether the Windows build context is the `M:\` host clone, which would turn the symlink hazard into a build hazard rather than a working-tree one.
17. What consumes `.github/agents/*.agent.md`.
18. The name of the bootstrap repo's own validation entry point.
19. `ai-rules-sync` 0.10.0 features (not evaluated). rulesync 18.0.0 was published 2026-09-24 and ruler 0.3.44 on 2026-06-30 (npm registry); both are patterns only, not dependencies.
