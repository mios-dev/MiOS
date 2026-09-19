<!-- AI-hint: Upstream Research & Audit: Claude Code CLI + Antigravity Multi-Harness Autonomous Engineering Loop
     AI-related: /workspaces/MiOS/.devloop/tasks.jsonl, /home/mios-dev/.dev-loop/skills/dev-loop/SKILL.md, /usr/share/mios/ai/system.md, MON-001..MON-018 -->
# Upstream Audit: Multi-Harness Autonomous Concurrency (Claude Code CLI + Antigravity)

**Document Type:** UPSTREAM_AUDIT / TECH_EVAL  
**Auditor:** Antigravity + Claude Code Joint Task Force  
**Date:** 2026-09-19  
**Status:** Canonical Reference & Actionable Engineering Ledger  
**Cross-References:** `MON-001` .. `MON-018` in `.devloop/tasks.jsonl`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`

---

## 1. Executive Summary & Objective

In a hybrid multi-harness autonomous engineering loop (where **Antigravity** orchestrates high-level decomposition, supervision, and governance, while **Claude Code CLI (`claude -p`)** and **Antigravity (`agy -p`)** execute concurrent worker lanes in isolated git worktrees), real-world multi-agent concurrency reveals critical runtime fault lines.

This audit synthesizes empirical measurements taken across live parallel executions (`srf-lib`, `srf-libexec`, `srf-native`, `srf-tests`), resolves standing operational bugs (`MON-001`..`MON-018`), and establishes actionable engineering contracts across both harnesses.

---

## 2. Empirical Harness Findings (Measured September 2026)

### 2.1 Claude Code CLI (`claude` v2.1.278)

1. **Turn Budget Enforcement (`--max-turns`)**:
   - **Finding:** `adapters.py` previously documented `--max-turns` as removed in modern Claude Code CLI.
   - **Empirical Measurement:** Tested live with `claude -p "test" --max-turns 1 --output-format json`. The CLI exited cleanly with `terminal_reason: "max_turns"`, `subtype: "error_max_turns"`, `num_turns: 2`, and output `"Reached maximum number of turns (1)"`.
   - **Conclusion:** The flag is hidden from public `--help` but fully operational and load-bearing. Lane worker budgets must pass `--max-turns` alongside wall-clock timeout bounds to prevent runaway reasoning spirals (`MON-013`).

2. **Structured Output Contracts (`--json-schema`)**:
   - Passing an exact JSON Schema for `devloop_report` produces machine-verifiable final artifacts.
   - Schema enforcement guarantees positive control counts, negative control matching regexes, changed paths, and exit codes without markdown parsing ambiguity.

3. **Headless Execution & Slash Commands**:
   - In headless print mode (`claude -p`), slash commands (such as `/dev-loop:goal`) that are not initialized via interactive session state are treated as plain prompt text and return exit code 0 (`MON-011`). Headless prompts must invoke direct task instructions rather than relying on uninitialized slash commands.

### 2.2 Antigravity CLI (`agy` v1.2.6) & Agent Architecture

1. **Command Allowlist Token Matching (MON-012, MON-017)**:
   - **Finding:** The Antigravity permission sandbox matches allowlist entries strictly against the **first whitespace-delimited word** of the command string.
   - **Impact:** Multi-statement shell commands starting with shell keywords (e.g., `for f in ...`, `while read ...`, or variable assignments `f=...; ...`) do not match allowlisted binaries (`bash`, `git`, `python3`, `cargo`) and trigger interactive permission prompts or instant user denial.
   - **Rule:** Every multi-statement command issued by an AGY supervisor or worker must be explicitly wrapped in `bash -c '...'` or structured as an executable script invoked by `python3` or `bash`.

2. **Held Stream-JSON Sessions (`agy_session.py`)**:
   - `agy -p "<prompt>"` single-shot execution terminates immediately when the planner finishes its initial turn, abruptly killing child processes or subagents.
   - Stream-JSON mode (`--input-format stream-json --output-format stream-json --print-timeout 0 -p=''`) preserves stdin across multiple turns, enabling continuous monitoring of asynchronous background lanes.
   - **Defect in `agy_session.py` (MON-003):** `antigravity_lane_ids()` filtered exclusively for `harness == "antigravity"`. When a plan scheduled `claude-code` worker lanes, `missing_reports` returned an empty list immediately, terminating the session prematurely. Polling must cover all scheduled worker lane harnesses.

---

## 3. Concurrency, Isolation, and Base-Tree Integrity

### 3.1 The Single-Writer Worktree Law (MON-006, MON-014)
- **Failure Mode:** Two autonomous harnesses (an AGY supervisor and a devloop detached job) concurrently dispatched separate Claude Code workers to the same worktree (`.worktrees/srf-libexec`). Both workers attempted to edit the same 63 files simultaneously. One worker applied clean comment fixes; the second worker attempted heuristic token rewrites that mangled runtime Python identifiers (`cockpit_ceph.py`, `topology_switch.py`) and corrupted the shared negative-control backup file (`.nc-srf-libexec.bak`).
- **Invariant:** A git worktree must have exactly **ONE** live writer at any time. Before dispatching any worker or supervisor into a worktree, the orchestrator must verify:
  1. A file-level mutex lock (`.worktree.lock`) or active process check (`lsof +D <wt>`).
  2. A clean porcelain status (`git status --porcelain`).
- If an active process or lock is detected, concurrent dispatch must abort immediately.

### 3.2 Peer Process Hygiene (MON-015)
- Supervisors and lane workers must limit process termination (`kill -9`, `kill -TERM`) strictly to their own process subtree verified by PPID ancestry checks. Never issue blanket kills against peer processes.

### 3.3 Credential and Secret Sanitization (MON-016)
- Autonomous agents checking environment variables for API tokens or authentication keys must query by variable name only (`env | grep -q ...` or `python3 -c 'import os; print("OK" if "KEY" in os.environ else "MISSING")'`).
- Dumping raw environment variable values into stdout or tool outputs leaks sensitive tokens into conversation transcripts and persisted logs.

---

## 4. Dev-Loop Orchestrator Gate Hardening (`devloop.sh`)

### 4.1 Gate Failure Under `set -eu` (MON-001, MON-018)
- **Defect:** `devloop.sh` runs with `set -eu`. In `gate_merge()`:
  ```bash
  "$PY" "$AD" gate --lane "$LJ" --wt "$WTA" --run "$RUN" --root "$ROOT"; rc=$?
  ```
  Because `;` is a command separator, a non-zero exit from `adapters.py gate` causes bash to exit immediately on the first failed lane, skipping all subsequent lanes in the wave (`srf-native` and `srf-tests` were left ungated).
- **Remediation:**
  ```bash
  rc=0; "$PY" "$AD" gate --lane "$LJ" --wt "$WTA" --run "$RUN" --root "$ROOT" || rc=$?
  ```
  This guarantees that every lane in the current wave is evaluated, diffs for failed lanes are parked as patches, and passing lanes are merged atomically.

### 4.2 Terminal Layout Defaulting (MON-002)
- **Defect:** When `LAYOUT=auto`, if `tmux` is present in the container, `devloop.sh` selected `tmux_grid`. In `tmux_grid`, lanes were spawned via `tmux split-window` rather than `job.py`, so `wait_wave` found no jobs, returned immediately, and `reap_lane` marked every lane as failed (`exit 125`).
- **Remediation:** Default automated/headless runs to `LAYOUT=detached`, which relies on `job.py` setsid detachment, wall-clock timeout bounds, and atomic receipt files (`worker-<id>.exit`).

---

## 5. Implementation Roadmap & Required Commits

| Target Component | File Path | Fix Description | MON Task |
|---|---|---|---|
| **devloop.sh** | `skills/dev-loop/scripts/devloop.sh` | Use `\|\| rc=$?` in gate call; default auto layout to `detached`. | `MON-001`, `MON-002` |
| **adapters.py** | `skills/dev-loop/scripts/adapters.py` | Restore `--max-turns` argument for `claude-code` workers. | `MON-013` |
| **agy_session.py** | `skills/dev-loop/scripts/agy_session.py` | Poll all worker lane harnesses, not only `antigravity`. | `MON-003` |
| **MiOS comments** | `usr/lib/mios/mios_comments.py` | Refine `RefIndex._TOKEN` to ignore prose slashes and protocol RPC methods. | `MON-018` |
| **dev-loop main** | `~/.dev-loop` | Merge `claude/adopt-mios-challenger-tests` into `main`. | `MON-010` |
