# Harness Adapters — any harness as host, any harness as lane

Read this before launching more than one lane, or when the host is not the same harness as the
lane. Facts below are as of September 2026 and drift monthly; §4 of SKILL.md applies to these
flags too — verify against `<cli> --help` before relying on one.

## 1. Where the skill and the `/dev-loop` command live

| Harness | Skill dir (project → user) | Slash command shim (`commands/…`) | Invoke | Args token |
|---|---|---|---|---|
| Claude Code | `.claude/skills/dev-loop/` → `~/.claude/skills/dev-loop/` | `.claude/commands/dev-loop.md` | `/dev-loop <obj>` | `$ARGUMENTS` |
| Antigravity (IDE + `agy`) | `.agents/skills/dev-loop/` (or `.agent/`) → `~/.gemini/config/skills/dev-loop/` (older builds: `~/.gemini/antigravity/skills/`) | `.agent/workflows/dev-loop.md` *(workflows retire 2026-11-01; after that the skill's own description triggers it)* | `/dev-loop <obj>` | prompt text |
| Gemini CLI | `.gemini/skills/dev-loop/` or `.agents/skills/dev-loop/` → `~/.gemini/skills/` | `.gemini/commands/dev-loop.toml` | `/dev-loop <obj>` | `{{args}}` |
| Codex CLI | `.agents/skills/dev-loop/` → `~/.agents/skills/dev-loop/` | `.codex/prompts/dev-loop.md` (or `~/.codex/prompts/`) | `/dev-loop <obj>` / `$dev-loop` | `$ARGUMENTS` |
| Cursor | `.cursor/skills/dev-loop/` | `.cursor/commands/dev-loop.md` (+ optional always-on rule `.cursor/rules/dev-loop.mdc`) | `/dev-loop` | prompt text |
| GitHub Copilot (VS Code + `copilot` CLI) | `.github/skills/dev-loop/` → `~/.copilot/skills/` | `.github/prompts/dev-loop.prompt.md` (+ optional agent `.github/agents/dev-loop.agent.md`) | `/dev-loop` | `${input}` |
| OpenCode | `.opencode/skills/dev-loop/` | `.opencode/command/dev-loop.md` | `/dev-loop <obj>` | `$ARGUMENTS` |
| Hermes-Agent | `~/.hermes/skills/dev-loop/` (agentskills.io compatible; auto-exposed as `/dev-loop`) | n/a | `/dev-loop` | prompt text |
| OpenAI-compatible runtime (Open WebUI pipe, custom) | pass `SKILL.md` as system context (Open WebUI core has no SKILL.md discovery) | n/a — expose `dev_loop` from `openai-tools.json` as a host-side tool | tool call | JSON |

`scripts/install.sh` / `install.ps1` copies the skill and every shim into the right places for
the harnesses it detects (`--all` to install for all, `--user` for user scope). The current spec
(agentskills.io, 2025-12) makes conformant runtimes ignore unrecognized frontmatter keys, so
extra keys are legal — but the claude.ai Skills API still rejects them, so install strips
frontmatter to the portable keys outside Claude Code, and heavy Claude-only keys
(`context: fork`, `disable-model-invocation`) stay on the **shim**. Keep angle brackets out of
frontmatter entirely (spec safety note: prompt-injection surface).

**Antigravity workflows retire 2026-11-01** (they stop being indexed or slash-invocable). After
that, `/dev-loop` resolves directly from the skill itself: `.agents/skills/dev-loop/` (workspace)
or `~/.gemini/config/skills/dev-loop/` — the one global path all three surfaces (IDE, agent,
`agy` CLI) read. The workflow shims installed today are a bridge, not the destination.

## 2. Headless lane command templates (`harness` field → command)

`adapters.py build` renders these; `{obj}` = the lane prompt (objective + lane contract + the
instruction to end with the `devloop_report` block), `{wt}` = absolute worktree path, `{n}` =
`max_turns`, `{t}` = `timeout_s`. Every command runs with `cwd={wt}` and an **outer wall-clock
`timeout`** — no harness is trusted to stop itself.

| `harness` | Command (cwd = worktree) | Objective | Native JSON envelope | Turn / time caps | Tool / permission control | Done signal |
|---|---|---|---|---|---|---|
| `claude-code` | `claude -p "{obj}" --output-format json --permission-mode dontAsk --allowedTools "…" --json-schema <report schema>` *(`--max-turns` was removed from the CLI — gone by 2.1.276; budget = outer timeout + `--max-budget-usd`)* | `-p` | `{result, structured_output, session_id, is_error, num_turns, total_cost_usd, permission_denials}` | `--max-budget-usd`, outer timeout | `--allowedTools` scoped rules + hooks (`allowed-tools` frontmatter alone is *not* enforced) | exit 0 ∧ `is_error=false` ∧ **`permission_denials` empty** ∧ report |
| `codex` | `codex exec --json --cd "{wt}" --sandbox workspace-write --ask-for-approval never --ephemeral --output-schema <file> -o <last.txt> "{obj}"` | positional | JSONL events; `-o` file holds the schema-validated final message | no max-turns → outer timeout | `--sandbox` / `--ask-for-approval`; **`--cd` is the write fence, `--add-dir` is not (#24214)**; never `--full-auto` (overrides `--sandbox`); `.git/` read-only ⇒ host commits | exit 0 ∧ report |
| `gemini-cli` *(legacy alias; consumer Gemini CLI ended 2026-06-18 — prefer `antigravity`)* | `gemini -p "{obj}" --output-format text --yolo` | `-p` (stdin appends) | text; fenced report parsed (**`--output-format json` aborts on any non-fatal tool error, #9281**) | none → outer timeout | trusted folders / policy engine; `--yolo` auto-approves | exit 0 ∧ report |
| `antigravity` | `agy -p "{obj}" --output-format json --print-timeout {t}s --dangerously-skip-permissions` *(surface verified against agy 1.2.6, 2026-09)* | `-p` | `{conversation_id, status, response, num_turns, usage, structured_output, denied_actions}` | `--print-timeout` (default 5m!) + outer timeout | `permissions.allow` rules (`command(...)`, `read_file(...)`, `write_file(...)`) in `~/.gemini/antigravity-cli/settings.json`; `--sandbox` | exit 0 ∧ report ∧ **`denied_actions` empty** (headless auto-denials still report `status: SUCCESS` with an empty response); **exit 12 = partial timeout** |
| `copilot` | `copilot -p "{obj}" --output-format json --add-dir "{wt}" --no-ask-user -s --allow-tool=… --deny-tool='shell(git push:*)' --deny-tool='shell(git commit:*)'` | `-p` | JSON | none → outer timeout | `--allow-tool`/`--deny-tool` (deny always wins, even under `--allow-all-tools`); `--agent <name>` → `.github/agents/<name>.agent.md` | exit 0 ∧ report |
| `opencode` | `opencode run --format json [--agent a] [--model m] "{obj}"` (cwd = worktree) | positional | JSON events (**subagent parts dropped, #49300 — keep lanes single-agent**) | none → outer timeout | `opencode.json` permissions (last matching rule wins); `-c` to continue | exit 0 ∧ report |
| `cursor` | `agent -p --output-format json --force --workspace "{wt}" [--model m] "{obj}"` | positional | one JSON object on completion | none → outer timeout | `.cursor/cli.json` permissions; **without `--force` print mode applies nothing** | exit 0 ∧ report |
| `openai-compatible` | `python3 scripts/devloop_worker.py --lane {lane_json} --report {report}` | user message | the `report` tool call (strict schema) | `max_turns` loop + `timeout_s` | server-side + client-side validation; blocked-command regex | `report` tool called |
| `custom` | `lane.worker.command` with `{obj} {wt} {report} {lane_json} {n} {t} {skill}` placeholders | template | whatever it prints | outer timeout | yours | exit 0 ∧ report |

Corrections to earlier drafts: `claude -w <name> -p` is real but creates *its own* worktree under
`.claude/worktrees/` — the orchestrator already made one, so use `cwd` instead. `gemini code -w …`,
`cloudcode cli …`, `openai-agent-cli …`, `gh copilot run …`, `antigravity run …`, `cursor-cli …`, and
`opencode run -d … -p …` **do not exist**; the forms above are the shipped ones. `adapters.py probe`
checks each installed binary's `--help` for the flags the adapter relies on — run it at install and
after every CLI upgrade; flags drift monthly.

**A lane's tool allowlist must cover its own controls.** The lane prompt tells the worker to run
both controls itself and a scoped rule like `Bash(python3:*)` does not match a compound
`negative_control_cmd` (`trap …; printf …; python3 …`), so the worker self-reports `blocked` and
the host — which refuses to merge on any non-`done` report even when its own gates hold — parks
the lane (observed live with claude-code + Haiku, 2026-09). Grant lanes plain `Bash` (the
worktree is the fence) or write controls as single non-compound commands.

**Restore controls by copy, never by `git checkout --`.** `git checkout -- <file>` restores from
the INDEX, and a lane's fix is uncommitted and unstaged when the host gate runs — so that trap
silently replaces the fix with the seeded bug, the tree-restored check fails, and the work is
destroyed (observed live 2026-09; the gate now parks the pre-control diff so the evidence
survives). Write `cp f .nc.bak; trap 'mv .nc.bak f' EXIT; …` — correct regardless of git state.

**Exit codes** are not fully enumerated by any vendor: branch on zero vs non-zero and read the
structured output for the real reason. Known traps the adapter handles: Claude denied-permission
⇒ exit 0 + `permission_denials` (downgraded to `partial`); Claude auto-mode aborts after 3
consecutive / 20 total classifier denials; a mid-turn kill exits 143; `agy` 12 = partial timeout.

**Report extraction (`adapters.py normalize`).** Claude (`--json-schema`) and Codex
(`--output-schema`) enforce the `devloop_report` schema natively; for every other harness the lane
prompt ends with "finish with a ```json block containing `devloop_report`". `normalize` unwraps the native envelope
(`result` / `response` / last `agent_message` / raw stdout), finds the last such block, validates
required keys, and writes the canonical report. If none is found it synthesises
`status: partial` (or `budget` on timeout, `halted` on non-zero exit with no output) with
`unverified: ["no devloop_report block emitted"]`. The host's own gates decide merging either way.

## 2b. Host via MCP — the harness-independent path

`scripts/devloop_mcp.py` exposes the orchestrator over MCP stdio (`.mcp.json` registers it in the
plugin; any other host adds `{"mcpServers":{"dev-loop":{"command":"python3","args":["<skill>/scripts/devloop_mcp.py"]}}}`).
It is stateless (2026-07-28 model; also answers the older `initialize` handshake) and returns
explicit handles: `validate_lanes` → `run_lanes` (headless from MCP) → `report`; `gate` for one lane;
`tasks_next` / `task_set` / `ledger` / `scaffold` for the artifact layer; `probe` for CLI drift.
Claude Desktop, Codex, Gemini/Antigravity, Copilot, Cursor, OpenCode and Open WebUI can therefore host
the loop without the shell shims. ACP-hosted editors (Zed, JetBrains) drive a lane agent through the
vendor ACP adapter and get the same `devloop_report`.

## 3. Host topologies — what is native, what is glue

| Link | A — Antigravity host | B — Claude Code host | C — Codex / OpenAI-compatible host |
|---|---|---|---|
| Host → same-vendor sub-agents | **native** `invoke_subagent` (Gemini-model only; `workspace: branch` = worktree; depth ≤ 10) | **native** `.claude/agents/*.md`, Agent tool, `isolation: worktree`, depth ≤ 5 | partial: `codex agents` / `codex queue` (`[features] multi_agent=true`); worktrees manual |
| Host → Claude Code lanes | **glue**: `run_command` → `claude -p …` (Terminal policy "Proceed in Sandbox" + `claude` on Allow list) | native (subagents) or glue for parallel CLI instances | **glue**: subprocess |
| Host → Codex lanes | **glue** | **glue**: Bash → `codex exec --json` | native-ish + glue |
| Host → Gemini / `agy` lanes | native for `agy` subagents; glue for `gemini` | **glue** (e.g. the `antigravity-for-claude-code` plugin) | **glue** |
| Host → Copilot / OpenCode / Cursor lanes | **glue** (`run_command`) | **glue** (Bash) | **glue** |
| Host → OpenAI-compatible lanes | **glue**: spawn `devloop_worker.py` | **glue** | **glue** (or expose `dev_loop` as a tool) |
| Hermes-Agent as host | `delegate_task(acp_command="copilot")` native; `terminal()` → any CLI (glue) | | |
| Worktree isolation | native for subagents; orchestrator for external lanes | native (`-w`, `isolation: worktree`) + orchestrator | orchestrator |

"Glue" = the host calls `scripts/devloop.sh` / `DevLoop.ps1` (or `adapters.py` directly) from its
shell tool and reads `.devloop/run-*/report-*.json`. That is the same code path in every topology,
which is why the skill stays universal: the host changes, the lane contract does not.

**Host checklists.**
- *Antigravity host:* **native-first** — Antigravity ships multi-agent patterns and workflows by
  default, so its own lanes run as native subagents (`invoke_subagent` with `workspace: branch`,
  the lane contract as the prompt, reporting into `.devloop/run-*/`) or native workflows; the
  reference orchestrator is how OTHER harnesses join the loop, and the headless `agy -p` lane
  template is the fallback when native subagents are out of reach. Terminal Command Auto
  Execution = "Proceed in Sandbox" (or "Always Proceed" inside a VM); add `claude`, `codex`,
  `gemini`, `agy`, `python3`, `git` to the Allow list; use `/tasks` to watch background lanes.
  For a **headless `agy` manager**, prefer scoped allow rules over
  `--dangerously-skip-permissions` — in `~/.gemini/antigravity-cli/settings.json`
  (Deny > Ask > Allow; verified against the CLI permissions docs and live runs, 2026-09):
  `{"permissions": {"allow": ["read_file(*)", "write_file(*)", "command(sh)",
  "command(python3)", "command(git)", "command(cat)", "command(ls)", "command(head)",
  "command(tail)", "command(mkdir)", "command(cp)", "command(mv)", "command(printf)",
  "command(echo)", "command(jq)", "command(cd)"]}}`. Prefix rules match the FIRST token
  only (`cd …&&` needs `command(cd)`), `list_dir` is not a valid action name, and an
  unanchored manager invents paths in its trusted workspace instead of the run's repo —
  `agy_host.sh` now pins the run root in the prompt.
  And in print mode the manager MUST run `devloop.sh` synchronously in the foreground: a
  headless `agy -p` answers once and exits, killing every backgrounded child with it — a manager
  that "launches and awaits" reports SUCCESS while nothing merges (observed live, 2026-09;
  `agy_host.sh` bakes this instruction into the manager prompt). Two more print-mode facts,
  both observed live: `run_command` auto-backgrounds anything still running after its
  `WaitMsBeforeAsync` parameter (the prompt pins it to 30 min for the dispatch), and
  **`invoke_subagent` fails under headless `agy -p`** *(STALE as of 1.2.6 -- see the correction below)* — the manager attempts it first and takes
  the documented fallback (full plan through `devloop.sh`), which carried a verified green run
  (gates, merges, integration, truthful report). The native subagent path needs an interactive
  Antigravity session (IDE or `agy` TUI).
  **CORRECTION (measured, 1.2.6): `invoke_subagent` does NOT fail headlessly.** Three probes,
  all `status: SUCCESS`, no `denied_actions`: (a) inside a held stream-json session, and (b) in
  plain single-shot `agy -p=`, and (c) single-shot with no prior `define_subagent` at all. A
  `subagent` step is emitted carrying each child's own `conversation_id`. The paragraph above is
  retained because the fallback it describes is sound, but its premise is not: native AGY fan-out
  IS reachable headlessly, so `agy_host.sh`'s rule forbidding it under `--headless` is
  over-restrictive **as an availability claim**. Its *lifetime* rationale still holds: every
  subagent in those probes finished INSIDE the dispatching turn, and a single-shot `-p`
  process still exits when the turn ends, taking an unfinished subagent with it. The leading
  suspect for the original failure -- a settings file voided by an invalid `toolPermission`
  -- was tested and **eliminated**: with the file voided and `permission_mode` degraded to
  `request-review`, `invoke_subagent` still succeeded. The cause remains unexplained.
  **Resolution:** the rule is now keyed on process lifetime, not on being unattended.
  `agy_host.sh --session` holds a stream-json session open across turns
  (`scripts/agy_session.py`), so native lanes survive their dispatch and the host polls
  until each writes `.devloop/native/report-<id>.json`; `--headless` keeps the
  orchestrator-only rule. Controls: `tests/test_agy_dispatch_rule.py`.
  **Separately, `-p` single-shot is not the only headless mode.**
  `agy --input-format stream-json --output-format stream-json --print-timeout 0 -p=''` holds a
  **stateful multi-turn session** on stdin: one NDJSON `{"event":"user","message":{...}}` per line,
  one `result` event per turn, one `conversation_id` throughout -- verified by a two-turn session
  where turn 2 recalled turn 1's state. A caller holding this session does not need the
  synchronous-foreground workaround above, because nothing is backgrounded and nothing is killed.
  That is a property of the held session; it is **not** what makes subagents work, as (b) and (c)
  above show. **Status of the poll loop: UNEXERCISED.** In the first end-to-end `--session` run
  (2026-09-19, two research lanes) the manager dispatched native subagents, gated both lanes and
  merged both -- all inside ONE turn (`num_turns: 1`, zero polls). It announced "I am ending my
  turn now so the host can provide follow-up turns" and then simply kept working. So that run
  proves native fan-out and merge discipline under a headless manager; it does **not** prove the
  poll loop, because the turn never ended. The mechanism that justifies `--session` over
  `--headless` is still untested in the case it was built for: a subagent outliving its turn. Flag order is load-bearing: bare `-p` swallows the next token as its prompt. Full
  protocol, event shapes and failure asymmetries: `references/translation-layer.md` 5.1a.
  **Watching an AGY-managed run (`--tmux`).** `devloop.sh` has had a tmux grid since the
  beginning (`devloop.sh:52`), but the AGY path never used it: the manager ran as one opaque
  process whose only signal was the envelope, at the end. `agy_host.sh … --session --tmux` now
  opens a tmux session with the manager in pane 0 and `scripts/agy_monitor.py --follow` in pane 1,
  both reading the SAME NDJSON stream that `agy_session.py --events-out` tees (default
  `.devloop/native/session-events.ndjson`). Attach with `tmux attach -t <session>`; without
  `--tmux` the stream is still written, so a monitor can be started later or from elsewhere.
  Degrades to a plain run when tmux is absent, and says so.

  **Monitoring/reporting task (surfacing a run in a Claude client).** `agy_monitor.py <stream>
  --once --report-out <file>` emits one JSON status from the same state the pane renders — so the
  operator's pane and the reporting agent can never disagree. Its `verdict` is derived from the
  stream, never from the harness's own `status`: `working`, `refused` (denials present),
  `vacuous` (a result claiming success with no text and no tool calls), `no_result` (a stream
  that produced no result event at all — measured, an all-unknown-event stream does exactly
  this), `no_stream` (the file does not exist, which is NOT a quiet healthy run), `errored`.
  Exit 2 on `vacuous`/`no_result`/`no_stream` so a caller can gate on it. It also counts and
  surfaces non-JSON lines rather than dropping them: agy writes its warnings and bare-text
  errors into the same stream, and those are precisely the lines saying a run is doing nothing.
  Spawn a Claude Code subagent that polls `--once` on an interval and reports the verdict, and a
  run being denied or idling becomes visible in the client while it happens instead of at the end.
  Controls: `tests/test_agy_monitor.py`.

  `scripts/agy_host.sh <lanes.json> [--headless]` launches `agy` pre-loaded as this manager.
  Multiple **Antigravity lanes** beyond `invoke_subagent`'s Gemini-only limit run as separate
  `agy -p` processes (`harness: antigravity` in `lanes.json`) side by side with multiple
  `claude-code` lanes; all of them reuse one cached credential, so on a headless box the Secret
  Service keyring must be running first (`scripts/env/agy-keyring.sh`; see `references/environment.md`)
  or every lane re-asks for auth and hangs its budget away.
- *Claude Code host:* same-vendor lanes as subagents with `isolation: worktree` (still pass
  `git -C`); cross-vendor lanes via Bash → orchestrator; `PreToolUse` hook blocking `git add -A`
  and `.env` writes; `SubagentStop` hook gating on the report block.
- *Codex / OpenAI-compatible host:* run the orchestrator; if the host is a bare model, expose the
  `dev_loop` function from `openai-tools.json` and have your runtime execute the orchestrator.
- *Copilot / OpenCode / Cursor host:* same — their shell tool runs the orchestrator; for Copilot
  add `--allow-tool='shell(sh:*)'` (or run interactively), for OpenCode grant `bash` in
  `opencode.json`, for Cursor allow `Shell(sh)` in `.cursor/cli.json`.

## 4. Cross-harness command matrix (harness-native commands → loop stage)

Use the native command when it exists; the fallback column always works.

| Loop stage | Claude Code | Antigravity / `agy` | Gemini CLI | Codex CLI | Shell fallback |
|---|---|---|---|---|---|
| Pre-flight | `/doctor` | `agy --version`, `/tasks` | `gemini --version` | `codex --version` | `devloop.sh --check` |
| Context / memory | `/init`, `/memory`, `CLAUDE.md` | Knowledge Base, `.agent/rules/` | `GEMINI.md`, `/memory` | `AGENTS.md`, `/init` | `AGENTS.md` |
| Plan (§2–3) | plan mode, `/plan` | Implementation Plan artefact | `/plan` (if extension) | plan mode | DoD block in repo docs |
| Execute a lane (§11) | subagent / `claude -p` | `invoke_subagent` / `agy -p` | `gemini -p` | `codex exec --json` | `devloop.sh lanes.json` |
| Refactor | `/simplify` | skill / `/boost` | — | — | `ruff --fix`, `cargo clippy --fix` |
| Diff audit (§12) | `/diff` | Walkthrough artefact | — | `codex review --base main --json` | `git diff --cached --stat` |
| Test & repair (§6) | `/debug` | Walkthrough + `/tasks` | — | — | project gate cmd |
| Security review | `/security-review` | skill | — | — | `gitleaks`, `bandit`, `cargo audit`, `npm audit` |
| Compaction | `/compact <focus>` | `/compact` | `/compress` | `/compact` | rotate session log |
| Cost / telemetry | `/cost` | `usage` in JSON envelope | `stats` in JSON | — | `.devloop/run-*/report-*.json` |

## 5. Contract-file bridging (one canonical `AGENTS.md`)

```
AGENTS.md                      # canonical, < 32 KiB (Codex cap)
CLAUDE.md                      # first line: @AGENTS.md
GEMINI.md                      # "Follow AGENTS.md; additions below."
.agent/rules/00-agents.md      # same pointer (Antigravity; 12 000-char cap per rule file)
.github/copilot-instructions.md# same pointer
.cursor/rules/agents.mdc       # same pointer
```
Loader semantics differ (Codex/Claude concatenate nearest-last; Zed first-match; Copilot unranked),
so the pointers must be *pointers*, not competing content.
