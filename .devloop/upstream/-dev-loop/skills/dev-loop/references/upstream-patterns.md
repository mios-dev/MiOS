# Upstream patterns — multi-harness, multi-agent "dev-loop-like" systems

Survey as of 2026-09-18. Sources: web research (cited inline), the official
Agent Skills spec (agentskills.io), harness vendor docs, and three
permissively-licensed projects reviewed at pinned commits (patterns copied
into this document with credit; nothing vendored into the repo). Everything
here is data for judgment, not law: AGENTS.md and this skill's gates win on
conflict.

## Credits — projects whose patterns are folded in below

| Project | License | Reviewed at commit | Pattern taken |
|---|---|---|---|
| [`nwiizo/ccswarm`](https://github.com/nwiizo/ccswarm) | MIT | `1cec7fe72886b2fffc4424637350f28f3130e6b4` | Master-orchestrator + domain-specialist agents on git worktrees; a dedicated quality-review agent between worker output and merge; session persistence so specialists keep context across tasks |
| [`ai-boost/awesome-harness-engineering`](https://github.com/ai-boost/awesome-harness-engineering) | CC0-1.0 | `fa3275de3db67ccf7f0c84912af6ea27f3d3719e` | The harness-engineering frame: orchestration, permissions, memory, evals, and observability treated as one control plane; AGENTS.md-as-contract templates |
| [`mraza007/baton`](https://github.com/mraza007/baton) | MIT | `7bb5fb73c08f31d897b7b64e85b3247a0292eebd` | Issue-driven loop: each GitHub Issue becomes one isolated worktree run with its own lifecycle and merge-back; the tracker, not the prompt, is the work queue |

## Patterns the ecosystem has converged on (and where this skill stands)

1. **Orchestrator–worker beats peer-to-peer as the first topology — and the
   manager's NATIVE multi-agent machinery is the default where it has one.**
   The manager holds user contract and task-level state; workers get narrow
   briefs and isolated contexts and return only final outputs plus artifact
   refs (Modern Agent Harness Blueprint 2026; ccswarm's master-orchestrator +
   specialist agents). Antigravity ships native subagents/workflows by
   default; an AGY manager uses those for its own lanes, and the reference
   orchestrator is how OTHER harnesses (Claude Code, Codex, …) join the loop.
   *This skill:* §11 L0/L1/L2 and `agy_host.sh` — aligned. Lane prompts stay
   narrow; reports are the only thing a host consumes.

   From ccswarm (MIT, credited above): a **quality-review agent between
   worker output and merge** is a role, not a phase — model it as a lane with
   `role: auditor` gating the wave; and **domain specialists keep sessions**
   (persistent context per specialty) — model it as one lane id reused across
   waves rather than fresh lanes per task.

   From baton (MIT, credited above): **the tracker is the work queue** — each
   issue maps to one lane (worktree, lifecycle, merge-back). On this skill:
   generate `lanes.json` entries from open issues/`tasks.jsonl` rather than
   hand-writing them.

2. **State on disk, context resets, structured handoffs.** The Ralph loop
   re-injects the goal into a fresh context each iteration and reads all state
   from the filesystem; harness engineering adds phase gates and handoff
   artifacts so work stays coherent across context windows (Addy Osmani,
   "Agent Harness Engineering"; NxCode/Augment guides). *This skill:*
   `.devloop/LEDGER.md`, `tasks.jsonl`, `devloop_report` — aligned; the ledger
   IS the handoff artifact.

3. **Worktree isolation per worker is the standard fence.** ccswarm, baton,
   Helmor (Apache-2.0), Sandcastle (MIT) all isolate each agent in a git
   worktree or sandbox and merge back through review gates. *This skill:*
   §11 worktree laws — aligned; our addition is the **two-sided gate run by
   the host** (positive + negative control), which none of the surveyed
   projects enforce mechanically. Keep it: it is this skill's differentiator.

4. **Event/issue-driven loops are the growing entry point.** baton polls
   GitHub Issues and turns each into an isolated worktree run; enterprise
   variants are event-driven (arXiv 2606.20058). *This skill:* lanes.json is
   the unit; an issue→lanes.json adapter is a natural, small future addition.

5. **Phase-gated single agents with human checkpoints outperform free-form
   swarms in production.** Plan–Execute–Verify with rigid gates and narrow
   tool access is what teams actually ship (Augment/NxCode 2026 guides;
   Google's June-2026 A2A production pattern routes failures to manual
   review). *This skill:* §1 lifecycle + §5 operator protocol — aligned; keep
   subagent counts low and gates rigid by default.

6. **Deterministic control planes around stochastic agents.** A2A-style
   shared session state, fail-safe routing, deterministic dispatch (arXiv
   2606.26924). *This skill:* the reference orchestrators are exactly that
   control plane; the 2026-09 live e2e reinforced it — determinism must
   extend to the manager's own dispatch (verbatim foreground command, scoped
   permission rules), because print-mode managers die with their children.

## Live-verified lessons folded back into this skill (2026-09-18)

From the mixed-lane e2e (`tests/e2e-mixed-lanes/`, AGY manager + AGY/Claude
lanes, all verified against git ground truth, never a manager's self-report):

- A headless print-mode manager that backgrounds the orchestrator reports
  SUCCESS while its exit kills every child (fixed: foreground-only dispatch in
  the manager prompt).
- Headless permission auto-denials can surface as `status: SUCCESS` with an
  empty response (`denied_actions` in the agy envelope; `permission_denials`
  in Claude's). Normalize downgrades both to `partial`.
- Scoped allowlists must match the model's habits: prefix rules match the
  first token only, and models prefix with `cd … &&`.
- Negative controls restore by copy-back; `git checkout --` restores from the
  index and destroys uncommitted lane work. The gate parks the pre-control
  diff first.

## Future patterns to track

- **Workflows → skills convergence** (Antigravity retires workflows
  2026-11-01; `/name` resolves from skills dirs). Shims are bridges only.
- **Agent Skills spec stewardship** under the Agentic AI Foundation: unknown
  frontmatter keys are ignored by conformant runtimes — expect richer
  optional metadata rather than new required keys.
- **A2A / cross-vendor session state** for lane-to-lane interface sync
  (today: `contracts.py` file exchange; A2A could replace polling).
- **Issue/event-driven lane generation** (baton pattern) on top of
  `lanes.json`.

Sources: [Modern Agent Harness Blueprint 2026](https://gist.github.com/amazingvince/52158d00fb8b3ba1b8476bc62bb562e3),
[Agent Harness Engineering — Addy Osmani](https://addyosmani.com/blog/agent-harness-engineering/),
[awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering),
[ccswarm](https://github.com/nwiizo/ccswarm), [baton](https://github.com/mraza007/baton),
[Augment: Harness Engineering](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents),
[Open-source agent orchestrators 2026](https://www.augmentcode.com/tools/open-source-agent-orchestrators),
[arXiv 2606.20058](https://arxiv.org/pdf/2606.20058), [arXiv 2606.26924](https://arxiv.org/pdf/2606.26924),
[Agent Skills spec](https://agentskills.io/home).
