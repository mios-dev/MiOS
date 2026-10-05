# MiOS Universal Multi-Agent & Multi-Harness Coordination Architecture

> **Canonical Upstream Standard**: Conforms to the **Agentic AI Foundation (AAIF)** under the **Linux Foundation**, the **AGENTS.md** open standard, and the **Model Context Protocol (MCP)** JSON-RPC 2.0 specification.
> **Law of Harness Neutrality**: No single harness (Antigravity, Claude Code, OpenAI Codex, OpenCode, Gemini CLI, Goose, Aider, or remote cloud endpoints) is permanently hardcoded as the coordinator. Any AI harness can be dynamically promoted to Orchestrator or dispatched as a specialist Worker.

---

## 1. Architectural Principles

1. **Harness Agnosticism & Dynamic Promotion**:
   - Any compliant agent harness running on `localhost`, in a container/VM, or via authenticated remote API can request, lease, or be promoted to the `orchestrator` or `monitor` role. No harness is permanently hardcoded as master or worker; any agent CLI invoked can be promoted dynamically.
   - Coordinator leases are managed dynamically in `/home/user/.local/state/mios/agent-relay/state.json` with heartbeats and cooperative peer messaging (`mios_agent_send` / `mios_agent_ack`).
   - If a coordinator session pauses or disconnects, an active worker or sentinel can claim the lease and resume orchestration without loss of state.

2. **Strict Invariant Conformance**:
   - **Architectural Law 5 (UNIFIED-AI-REDIRECTS)**: All agent harnesses bind strictly to `$MIOS_AI_ENDPOINT` (`:8500` / `:8700` / `:8642`). Zero cloud vendor API URLs; zero credential leaks.
   - **The 5 MiOS Architectural Invariants**: `/var` persistence on bootc/ostree; UKI bootloader signing; `venus` VirtIO GPU vs CUDA VFIO passthrough; driver-free host GPU passthrough; Blade hardware ownership.
   - **Two-Sided Verification Gates**: Every change requires positive controls (valid implementations pass) and planted negative controls (mutations/defects fail deterministically naming the plant).

3. **Live Desktop Visibility & Headless Automation (tmux-mcp + MiOS-MCP)**:
   - Headless automation slots run under bounded, discoverable sockets (`/run/mios-tmux/` or `/tmp/mios-tmux/`) supporting up to 32 concurrent slots.
   - Interactive desktop panes run in the user's visible session (`tmux -L mios-human` or GNOME terminal), allowing operators and agents to inspect live executions side-by-side in `mios mon` (Tab 4: `MiOS-Ai` and Window 1: `MiOS-Agents`).

---

## 2. Canonical Subagent Topology (AAIF Standard)

All agent configurations in `.agents/agents/*.md` and `.agents/subagents.json` map to the 8 canonical roles:

| Canonical Role | Primary Mandate | Tools Access | Staging & Merge Authority |
| :--- | :--- | :--- | :--- |
| **`orchestrator`** | Multi-lane dev-loop workflow coordinator, task queue manager, lease arbitrator. | Read, Write, Subagent, Task, Schedule | Shared state only (`tasks.jsonl`, `AGENTS.md`) |
| **`worker`** | Core Linux OS engineer, static Rust binary compiler, unit test author. | Read, Write, Run Command | Isolated worktrees only (`.devloop/worktrees/`) |
| **`auditor`** | Independent gatekeeper verifying standing gates, ratchets, and credentials. | Read-Only, Run Command | Zero write permissions; issue pass/fail verdicts |
| **`reviewer`** | SCOPE staged code reviewer inspecting AST, invariants, and two-sided controls. | Read-Only, Run Command | Zero write permissions; verdict APPROVE / REQUEST_CHANGES |
| **`challenger`** | Adversarial stress tester executing race conditions, fuzzing, and egress checks. | Read-Only, Run Command | Zero write permissions; emits reproducible failure traces |
| **`explorer`** | Codebase reconnaissance, dependency mapper, EARS criteria author. | Read-Only, Run Command | Zero write permissions; emits reconnaissance reports |
| **`publisher`** | SSOT projection sync, UKI drop-ins, SBOMs, and OCI release packaging. | Read, Write, Run Command | Projection targets (`tools/sync-generated.sh`) |
| **`developer`** | Canonical MiOS OS and substrate developer maintaining core system contracts. | Read, Write, Run Command | Full substrate within architectural boundaries |

---

## 3. Inter-Agent Workload Coordination via MiOS-MCP

Agents communicate through the local high-performance JSON relay (`/home/user/.local/state/mios/agent-relay/state.json`).

### 3.1 Relay Registration Protocol
Every active agent session registers using the standard MCP tool `mios_agent_register`:
```json
{
  "agent_id": "<harness>:<session-or-uuid>",
  "kind": "codex | claude | opencode | agy | gemini | copilot | aider",
  "label": "<Human-readable display label>",
  "token": "<optional auth token>"
}
```
The relay engine privately assigns a session lease, tracks activity through `receive` and `ack` operations, and persists active session metadata (including dynamic role and TTL expiry) within `/home/user/.local/state/mios/agent-relay/state.json`.

### 3.2 Structured Messaging & Acknowledgment
Agents exchange asynchronous peer messages using `mios_agent_send`, `mios_agent_receive`, and `mios_agent_ack`:
1. **Send**: Caller emits message with unique `message_id`, `from`, `to`, `message`. Status is set to `queued`.
2. **Receive / Observe**: Recipient or observer fetches pending messages for its agent ID.
3. **Acknowledge**: Recipient updates status to `received` with timestamp, then transmits reply. Unacknowledged messages trigger a yellow pending counter `(1p)` in `mios mon`.

---

## 4. Live Desktop Sub-Pane Spawning Protocol (tmux-mcp)

When an agent needs to spawn sub-tasks live on the desktop or in headless slots:

### 4.1 Native Slot Dispatch
The orchestrator or peer agent calls `mios_tmux_nested_workflow` or `execute-command`:
```json
{
  "agent": "codex | claude | opencode | agy",
  "task": "Run verification suite tests/test-agy-agent-pipeline.py and reply with status",
  "timeoutSeconds": 300,
  "slot": 1
}
```

### 4.2 Desktop Interactive Sub-Pane Split
To open a live sub-pane visible to the human desktop operator:
```bash
# Target the user's interactive tmux session
tmux -L mios-human split-window -h -p 50 \
  "export MIOS_AI_ENDPOINT='http://localhost:8642/v1'; mios agent <name> '<prompt>'"
```
The child agent executes in full view, inherits the unified AI redirect environment, communicates over the MCP relay, and safely cleans up on completion.

### 4.3 Desktop and Terminal Interaction Mechanics
Detailed keybindings, readline shortcuts, input sigils (`!`, `@`, `%`, `?`, `??`), and streamlined slash commands (`/new`, `/resume`, `/fork`, `/compact`, `/plan`, etc.) are formally defined in [docs/design/doc-desktop-terminal-interaction.md](file:///C:/MiOS/docs/design/doc-desktop-terminal-interaction.md). All agent CLIs operating in MiOS terminal planes conform to these interaction patterns.

---

## 5. Worktree Isolation Contract

1. **Dedicated Worktree per Lane**: Every implementation lane operates in `.devloop/worktrees/<lane-id>/` on branch `devloop/<lane-id>`.
2. **Disjoint Ownership**: No two concurrent lanes may modify the same files.
3. **No Direct Trunk Pushes**: A lane never pushes directly to `main`. It reports its exit receipt, passes positive and negative verification gates, and undergoes reviewer approval before the orchestrator merges.
4. **Clean Handoff**: Each lane emits a structured 4-section `handoff.md` (`Summary`, `Changed Files`, `Verification Evidence`, `Residual Risks / Blockers`).
