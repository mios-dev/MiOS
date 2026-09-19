# dev-loop — universal autonomous engineering loop (v7.6.0)

One repo, three things:

1. **A Claude Code plugin** — `.claude-plugin/plugin.json`, seven skills (`/dev-loop`, `/goal`, `/research`, `/review`, `/ship`, `/triage`, `/websearch`), five agents (`orchestrator`, `lane-worker` in an isolated worktree, `auditor`, `triage`, `researcher`), and enforcement hooks.
2. **A portable skill set** (Agent Skills open standard) plus thin command shims for Antigravity, Gemini CLI, Codex, Copilot, Cursor, OpenCode, Hermes-Agent — installed by `skills/dev-loop/scripts/install.sh` / `.ps1`.
3. **An MCP server** (`skills/dev-loop/scripts/devloop_mcp.py`, registered by `.mcp.json`) so any MCP-capable host drives the orchestrator: `validate_lanes`, `run_lanes`, `gate`, `report`, `tasks_next`, `task_set`, `ledger`, `scaffold`, `probe`.
4. **Harness-neutral glue** in `skills/dev-loop/scripts/`: `adapters.py` (9 lane harnesses, gates, probe, ledger), `devloop.sh` / `DevLoop.ps1` (worktree lane orchestrators), `artifacts.py` (AGENTS.md, GOALS, ROADMAP, MADR ADRs, tasks.jsonl → TASKS.md, DoD, checklists, CHANGELOG, ledger), `goal.py`, `research.py`, `review.py`, `ship.py`, `triage.py`, `devloop_worker.py` (OpenAI-compatible worker), `contracts.py` (cross-lane interface exchange), `verify_harness.py`; docs in `references/`, schemas/templates in `assets/` (agentskills.io layout).

## Install

```sh
# Claude Code (plugin — recommended)
claude plugin marketplace add /path/to/dev-loop        # or a git URL
claude plugin install dev-loop@dev-loop-marketplace     # commands appear as /dev-loop:goal etc.
# local dev:  claude --plugin-dir /path/to/dev-loop

# Everything else (and Claude Code skills-only fallback), project scope, plus the canonical artifacts
sh skills/dev-loop/scripts/install.sh --all --scaffold
pwsh skills/dev-loop/scripts/install.ps1 -All -Scaffold
```

Required Claude Code settings: `"worktree": {"baseRef": "head"}`; version ≥ 2.1.219. Run `python3 skills/dev-loop/scripts/adapters.py probe` after installing or upgrading any harness CLI.

## Conformance
`sh skills/dev-loop/scripts/validate.sh` — agentskills.io validator on every skill (sub-skills as the six-key copies other harnesses receive), plugin/hook/agent shapes, schemas, syntax, and `claude plugin validate --strict` when the CLI is present. Details and sources: `skills/dev-loop/references/conformance.md`.

## Use

- `/dev-loop <objective>` — one task through the loop. `/dev-loop lanes:<lanes.json>` — parallel lanes in any mix of harnesses (schema: `assets/lane-schema.json`, example: `assets/lanes.example.json`).
- `/goal dev <objective>` — define stopping conditions, decompose into tasks, iterate until `goal.py eval` passes.
- `/research …` → `/dev-loop …` → `/review` → `/ship <branch>`; `/triage <failing cmd>` before touching code.

Any harness can be the host; any harness can run a lane (`references/harness-adapters.md`). State lives on disk (`.devloop/`), never in the context window (`references/artifacts.md`).

## Environments: devcontainers (Fedora default) + Claude Code on the web

The environment layer ships **inside the skill** (`skills/dev-loop/scripts/env/`, docs in
`references/environment.md`), so every dev-loop install carries it. It is distro-aware —
**Fedora/RHEL (dnf5/dnf/microdnf) first, Debian/Ubuntu (apt) second** — idempotent, and
location-independent.

**Devcontainers:** `.devcontainer/devcontainer.json` is **Fedora 44** (this repo's default
image); `.devcontainer/ubuntu/` is the Ubuntu 24.04 variant. Both bake the keyring stack plus
Node + Claude Code for `claude-code` lanes, provision at `postCreateCommand`, and re-arm the
keyring at `postStartCommand` — after a container restart no new login is needed.

**Claude Code on the web:** the SessionStart hook (`.claude/settings.json` →
`.claude/hooks/session-start.sh`) runs the same provisioning on every remote session.

**First-run login — two commands, from any of these environments** (Antigravity has no
non-interactive auth; the driver walks agy's entire first-run TUI and *proves* the result with a
live headless probe):

```sh
bash skills/dev-loop/scripts/env/agy-login.sh                  # 1. prints the Google auth URL
bash skills/dev-loop/scripts/env/agy-login.sh --code '<code>'  # 2. finishes onboarding + verifies
```

Defaults chosen for you (flags to override): Google's "share Interactions data" checkbox OFF
(`--telemetry` to opt in — that consent belongs to the human), workspace trust YES
(`--no-trust`). Already signed in? Either command detects it and skips straight to the
verification probe. Containers are ephemeral: a brand-new container needs the login once. The
keyring is empty-password (credential recoverable by anyone with container access) — acceptable
for a single-user ephemeral session only.

## AGY as manager (topology A, this repo's default)

`AGENTS.md` (the constitution — law in every harness) makes Antigravity the L0 manager of all
dev-loop sub-agents in this repo. It dispatches any mix of lanes, including **multiple
concurrent Antigravity lanes** (separate `agy -p` processes) **and multiple concurrent Claude
Code lanes** (`claude -p`), each in its own git worktree with its own two-sided gate:

```sh
python3 skills/dev-loop/scripts/adapters.py probe                     # flags drift monthly — check first
sh skills/dev-loop/scripts/agy_host.sh my-lanes.json                  # interactive manager
sh skills/dev-loop/scripts/agy_host.sh my-lanes.json --headless       # unattended manager (JSON out)
```

The manager is **native-first**: Antigravity's own multi-agent machinery (subagents via
`invoke_subagent` with `workspace: branch`, native workflows) runs its own lanes by default;
the reference orchestrator is how Claude Code and other harnesses join the loop. Harness-native
loop commands inside lanes are allowed and never replace the gates.

Model defaults (operator policy, 2026-09): Claude Code lanes run `--model opus --effort xhigh`
(the alias tracks the newest Opus release; the manager assigns lower tiers — sonnet/haiku,
lower effort — to light lanes); Antigravity lanes default to `gemini-3.8-flash-high`; the
headless manager runs `gemini-3.1-pro-high` (`AGY_HOST_MODEL` / `AGY_HOST_EFFORT` override;
per-lane `worker.model` / `worker.effort` win). Verified live: the full AGY-managed mixed-lane
e2e (`tests/e2e-mixed-lanes/`) passes end to end under scoped agy permission rules. Upstream
pattern survey, with patterns copied and credited at pinned commits (nothing vendored):
`skills/dev-loop/references/upstream-patterns.md`.

Mixed-lane example: `skills/dev-loop/assets/lanes.agy-manager.example.json` (2 AGY lanes +
2 Claude Code lanes + an AGY auditor). The manager runs every merge gate itself; lanes never
commit, and a lane whose negative control passes is never merged.

## SCOPE staged review (v7.6.0, merged from the dev-loop v2.x lineage)

`/review` now runs the full **SCOPE** oversight model (Staged Code Oversight with Proportional
Escalation, after Greiler's staged-review work): Stage 1 agent review (severity × dimension
findings; secret scan covers keyword assignments AND bare token formats — AKIA/ghp_/sk-/AIza/
xox), Stage 2 steering-developer ownership with Agent-Dev Loop sizing (≤ 600 lines / ≤ 20
files), Stage 3 proportional peer escalation (Understanding Need × Change Risk × Established
Assurance → escalation tier), recorded in a Living Oversight Record
(`OVERSIGHT_RECORD.md` + `.devloop/scope_review_*.json`). The goal/ship/research/triage engines
took the same lineage's refinements, and `scripts/git_lock.py` plus a stale-`index.lock`
sweep in the adapters' git retry protect multi-lane git contention.
