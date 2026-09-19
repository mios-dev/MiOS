# AGENTS.md — constitution for this repository

Canonical contract file. `CLAUDE.md`, `GEMINI.md`, and `.agent/rules/00-agents.md` are pointers
to this file; loaders differ, so those files must stay pointers. Per the dev-loop skill
(`skills/dev-loop/SKILL.md` §0), this file is law: where it and the skill disagree, this file wins.

## What this repository is

The `dev-loop` plugin/skill set (see `README.md`), plus an environment layer (`skills/dev-loop/scripts/env/`, devcontainers in `.devcontainer/`)
that provisions Google Antigravity's CLI (`agy`) inside Claude Code on the web containers.

## Orchestration topology (binding)

- **L0 host / manager: Antigravity (`agy`), native-first.** All multi-lane dev-loop runs
  launched from this repository default to topology A of
  `skills/dev-loop/references/harness-adapters.md` §3 — AGY is the manager of all sub-agents and
  uses its NATIVE multi-agent machinery (subagents via `invoke_subagent` with
  `workspace: branch`, native workflows) for its own lanes by default. The dev-loop's reference
  orchestrator is how OTHER harnesses join the loop, not a replacement for AGY's native
  patterns. Launch with `sh skills/dev-loop/scripts/agy_host.sh <lanes.json>`.
  **Native lanes require a manager whose process outlives a turn.** `--session` holds a
  stream-json NDJSON session open across turns and is the unattended mode that keeps the
  native topology above; `--headless` is single-turn `agy -p` and routes every lane through
  the reference orchestrator instead, because a subagent that has not finished when the turn
  ends dies with the process. This is a lifetime constraint, not an availability one --
  `invoke_subagent` itself works headlessly (measured 1.2.6, four probes, including one with
  `settings.json` voided). Controls: `tests/test_agy_dispatch_rule.py`. The first `--session`
  run dispatched, gated and merged two native lanes in ONE turn, so the poll loop that keeps a
  session alive past a turn end is implemented but **not yet exercised** -- do not cite it as
  proven.
- **Lanes: any mix, multiple instances allowed.** Native Antigravity subagents and multiple
  concurrent Claude Code lanes (`claude -p`) run side by side; other harnesses stay available
  through the orchestrator. Harness-native loop commands (`/dev-loop` shims, Claude Code's
  `/loop`-style commands, AGY workflows) are allowed inside lanes — they map onto loop stages
  and never replace the gates. Every lane keeps the dev-loop lane contract: exclusive
  `owned_paths`, its own two-sided gate, no `git add/commit/push`, no edits to this file.
- **Model policy (operator, 2026-09):** Claude Code lanes default to the newest Opus
  (`--model opus --effort xhigh`); the manager may assign lower tiers (sonnet, haiku, lower
  effort) to light lanes. Antigravity lanes default to `gemini-3.8-flash-high`; the manager
  itself runs `gemini-3.1-pro-high`.
- **The manager is the only writer to shared state** (`AGENTS.md`, `.devloop/`, merges). Lanes
  report `contract_updates`; the manager writes them here.
- **Fallback:** when `agy` is unavailable or unauthenticated, a Claude Code session may host the
  run (topology B) but must say so in its report; it does not silently become the standing manager.
- **Permissions for the headless manager (operator decision, 2026-09-18):** `--yolo`
  (`--dangerously-skip-permissions`) is authorized whenever the run is requested via a
  `/dev-loop`-style command. Scoped `permissions.allow` rules remain the default elsewhere; note
  that models habitually prefix dispatch commands with `cd … &&`, and prefix rules match only the
  first token, so a scoped allowlist needs `command(cd)` too.
- Reference example for a mixed AGY + Claude Code run:
  `skills/dev-loop/assets/lanes.agy-manager.example.json`.

## Environments (devcontainer default: Fedora; also Claude Code on the web)

Canonical scripts: `skills/dev-loop/scripts/env/` (docs: `references/environment.md`; there is
no other copy — no wrappers). Distro-aware: Fedora/RHEL dnf first, Debian/Ubuntu apt.
`.devcontainer/` defaults to **Fedora 44**; `.devcontainer/ubuntu/` is the apt variant.

- `bash skills/dev-loop/scripts/env/setup-antigravity.sh` — idempotent provisioning (also run
  by the SessionStart hook in `.claude/settings.json` and devcontainer `postCreateCommand`).
- `bash skills/dev-loop/scripts/env/agy-login.sh` — first-run login, two steps: no args prints
  the Google auth URL; `--code '<code>'` finishes onboarding (telemetry consent OFF unless
  `--telemetry`; workspace trust YES unless `--no-trust`) and chains into the live probe.
- `bash skills/dev-loop/scripts/env/agy-doctor.sh [--probe]` — health/auth verification.
- `skills/dev-loop/scripts/env/cloud-fedora-setup.sh` — **cloud environments** (claude.ai/code,
  `claude --cloud`, routines) are not devcontainers: the VM is a fixed Ubuntu 24.04 image and
  replacing the base image is unsupported, so this is the setup script to paste into the
  environment dialog. It builds `dev-loop-fedora:44` and installs `/usr/local/bin/fedora`
  (same paths, same `$PWD`). Measured 60s first run, 1.4s cold-session self-heal.
  Details: `references/environment.md` § Fedora in a Claude Code *cloud environment*.
- The keyring holds the AGY credential unencrypted-at-rest (empty-password keyring) — accepted
  for ephemeral single-user containers only. Never print or export the credential.

## Working rules

- Follow `skills/dev-loop/SKILL.md`: DoD before code, two-sided verification, explicit-path
  staging only (never `git add -A`), secrets scan before commit, ledger entry before ending.
- Gates for changes to this repo: `sh skills/dev-loop/scripts/validate.sh` must pass;
  shell edits get `bash -n` / `sh -n`; JSON edits must `json.load`.
- Harness CLI flags drift monthly: run `python3 skills/dev-loop/scripts/adapters.py probe`
  before relying on any lane command template.
