---
name: opencode-delegation
description: |
  When the operator asks for multi-file code work, file-system navigation,
  multi-step PC control loops, or anything that benefits from snapshot-
  rollback + diff-preview edits — delegate to OpenCoder via Hermes's
  NATIVE delegate_task with acp_command="opencode". The opencode binary
  is installed locally; it speaks ACP over stdio.
metadata:
  hermes:
    requires_tools: [delegation]
---

# opencode-delegation — when to dispatch to the specialist coder

<!-- MiOS-managed: pointer to Hermes's NATIVE delegate_task mechanism.
     Delete the marker to take ownership. -->

OpenCoder (the SST/anomalyco opencode 1.15+ binary at
`/usr/lib/mios/opencode/bin/opencode`) is your specialist for tasks
where its native discipline beats spawning a qwen3:1.7b sibling:

* **Multi-file refactors / renames / moves** — opencode's `edit` +
  `patch` tools do string-replace + unified-diff with snapshot
  rollback. You don't have an equivalent natively.
* **"Read N files, edit M files" loops** — opencode's `read` +
  `glob` + `grep` + `edit` chain is purpose-built; it caches reads
  and presents diffs before applying.
* **PC-control workflows that need code-aware reasoning** — when
  the task is "look at this script + click the resulting button +
  edit the config + retry", opencode's session model + snapshot
  history outperforms ad-hoc terminal calls.
* **Long-running coding work** with rollback guarantees — its
  `Snapshot.Service` captures the filesystem state per session.

## How to delegate

Use your native `delegate_task` tool with `acp_command`:

```
delegate_task(tasks=[{
  "goal": "Refactor the auth middleware to extract token validation into its own module. Files: src/auth/*.py.",
  "acp_command": "opencode",
}])
```

Hermes's delegation runtime spawns `opencode` as an ACP-over-stdio
subagent, hands it the goal, and folds its final response back into
your turn as a tool result. opencode uses the same Ollama backend
you do (same model pool), so no extra VRAM contention.

## When NOT to delegate to opencode

* **Single-shot file reads** — your `file` tool is faster.
* **One-line terminal commands** — `terminal` tool, not opencode.
* **MiOS surface stuff** (mios-find, mios-windows launch, etc.) —
  those are your direct tools; opencode doesn't know about them.
* **Anything the operator wants you (MiOS-Agent) to be the visible
  actor for** — delegation is invisible to the operator's chat;
  if they're watching for "MiOS-Agent did X", they see your final
  summary not opencode's internal steps.

## Operator's mental model

Operator sees: "MiOS-Agent did the refactor". Under the hood: you
delegated to opencode, which used its read/edit/patch + snapshot
discipline, and you summarised the result back. Same Ollama
backend, complementary tool surfaces. Per the operator's 2026-05-16
integration analysis: "Hermes is the lifestyle / orchestration
agent, opencode is the specialist coding agent that gets
dispatched".
