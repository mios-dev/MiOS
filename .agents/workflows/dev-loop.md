---
name: dev-loop
description: MiOS Autonomous Development Loop for Antigravity CLI (AGY)
author: MiOS Core Team
tags: [dev-loop, autonomous, mios, rust, testing]
---

# MiOS Dev-Loop Workflow (AGY)

This workflow defines the autonomous dev-loop lifecycle when executed by Google Antigravity CLI (`agy`) or its subagents.

## Lifecycle Phases

### 1. Definition of Done & Controls
- Identify target task in `TASKS.md` or `.devloop/tasks.jsonl`.
- Define the positive control (command that verifies expected behavior).
- Define the negative control (command that fails when behavior is absent).
- Record stopping conditions.

### 2. Implementation Phase
- Follow Linux FHS guidelines (`usr/` for static files, `etc/` for runtime overrides).
- Favor Rust static binaries in `tools/native/` over shell/Python scripts.
- Bind all agentic calls to `MIOS_AI_ENDPOINT` using strict OpenAI schemas.
- Ensure secrets are stored/accessed via native Linux Keyring, never plaintext.

### 3. Verification & Standing Gates
Execute the mandatory gates:
```bash
python3 <test_file>
python3 tools/ci-suites.py --check
src/mios-rs/target/debug/mios-gate phase-registry --root /workspaces/MiOS
src/mios-rs/target/debug/mios-gate ratchet-direction --root /workspaces/MiOS
src/mios-rs/target/debug/mios-gate credential-literals --root /workspaces/MiOS
src/mios-rs/target/debug/mios-gate version-literals-ssot --root /workspaces/MiOS
src/mios-rs/target/debug/mios-gate signature-policy --root /workspaces/MiOS
```

### 4. Projection Synchronization & Artifacting
```bash
bash ./tools/sync-generated.sh
git diff --exit-code
```

### 5. Completion Receipt
Emit the `devloop_report` JSON object summarizing the task, tests, controls, and diff stats.
