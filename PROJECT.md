# Project: MiOS Task Backlog Implementation & CI Gate Parity

## Architecture
MiOS is an immutable, bootc/OCI-shaped Fedora workstation that is also a local, self-replicating, agentic AI operating system. The system layout mirrors the root filesystem (`.git` is `/`):
- `automation/`: Image build, overlay, and drift check scripts.
- `usr/share/mios/`: Singular SSOT (`mios.toml`), profiles, branding, templates.
- `usr/libexec/mios/`: Runtime utilities, tools, and daemon interfaces.
- `usr/lib/mios/`: Python core services (`agent-pipe` FastAPI server, daemons).
- `etc/mios/`: Host-level override layer.
- `src/mios-rs/` & `tools/native/`: Rust workspaces for daemon, build driver, and drift checker tooling.
- `tools/`: CI validation scripts, AST checkers, code generators.
- `tests/`: Automated test suites and regression tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Template Drift Hygiene | Remove un-tracked backup artifacts (`toml-config.bak`) to satisfy `compile-templates.py` and `98-drift-checks.sh` | M1 | CI Survey |
| 2 | Shutdown Diff Snapshotting | Capture `/var` mutations on shutdown into versioned diffs (`WS-DIFFCYCLE`, ADR-0018, T-872, AGY-2470) | M2 | TASKS.md / ADR-0018 |
| 3 | Boot Cycle Accrual Engine | Accrue and roll in verified runtime diffs across boot cycles (T-873, AGY-2471) | M2 | TASKS.md / ADR-0018 |
| 4 | Edge Wire 16B Framing | Verify and enforce 16-byte fixed binary header framing (`0x4D49` magic, CRC32, opcodes) (WS-NODE, ADR-0020, T-890, AGY-2488) | M3 | TASKS.md / ADR-0020 |
| 5 | Micro-Mesh Opcode Dispatch | Implement wire message handler and opcode dispatching logic for task offload and state sync (T-891, AGY-2489) | M3 | TASKS.md / ADR-0020 |
| 6 | Automated Test Coverage | Provide unit and regression tests in `tests/` registered in `tools/ci-suites.py` for all implemented features | M2, M3 | R2 / ci-suites.py |
| 7 | Task Schema & Parity Sync | Update `TASKS.md`, `AGY-TASKS.md`, and `ROADMAP.md` in lockstep with 100% 8-field schema compliance | M4 | R1, R3 |
| 8 | CI Gate Verification & Git Finalization | Execute all 6 CI gates, verify clean working tree, and finalize commits to `main` | M5 | R3, R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Template & Drift Hygiene | Resolve `usr/share/mios/templates/toml-config.bak` and verify drift-check gates | none | DONE |
| M2 | Shutdown Diff Snapshotting (`WS-DIFFCYCLE`) | Implement shutdown diff snapshotting & boot cycle accrual (`usr/libexec/mios/`, `tests/`) | M1 | DONE |
| M3 | Edge Micro-Mesh Wire Protocol (`WS-NODE`) | Implement 16-byte wire framing, opcode dispatch, and validation tests | M1 | DONE |
| M4 | Task Registry & Parity Synchronization | Update task metadata in `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md` | M2, M3 | DONE |
| M5 | CI Gate Verification & Git Commit Finalization | 100% verification across all 6 gates, clean working tree, commit to `main` | M4 | DONE |

## Key Milestone Outputs
- **M1**: Removed `usr/share/mios/templates/toml-config.bak`. All 26 templates pass `tools/compile-templates.py`.
- **M2**: Implemented `usr/libexec/mios/diff-accrual.py`, `usr/libexec/mios/diff-accrual.sh`, and `tests/test-diff-accrual.py`. Unit tests passing (3/3 tests).
- **M3**: Implemented `usr/libexec/mios/mios-node-wire.py` and `tests/test-node-wire.py`. Unit tests passing (8/8 tests). Registered in `usr/share/mios/mios.toml` `[ci.tiers.unit]`.
- **M4**: Synchronized `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md` for `T-872..T-874`, `T-890..T-892`, and `AGY-2470..AGY-2472`, `AGY-2488..AGY-2490` with full 8-field schema compliance.
- **M5**: Executed all 6 CI verification gates (100% PASS), committed changes to `main` (`5e96206bbeae6452e1c6d67e45ea922cbc18ca20`), clean working tree.

## Interface Contracts
### `WS-DIFFCYCLE` (`usr/libexec/mios/diff-accrual.sh` / `tests/test-diff-accrual.sh`)
- Input: `/var` state snapshot directory, ostree deployment commit metadata.
- Output: Versioned diff archive in `/var/lib/mios/diffs/diff-<timestamp>.tar.zst` and JSON ledger at `/var/run/mios/accrued-diffs.json`.
- Return Code: `0` on successful snapshot/accrual, non-zero with diagnostic log on conflict.

### `WS-NODE` Wire Protocol (`src/mesh/` / `usr/libexec/mios/mios-node-wire.py` / `tests/test-node-wire.py`)
- Header Format: 16 bytes Network Byte Order (`>HBBIII` / `!2sBBIII`).
  - Bytes 0..1: `0x4D 0x49` (`MI`)
  - Byte 2: `0x01` (Version)
  - Byte 3: Opcode (`0x01`..`0x07`)
  - Bytes 4..7: `NodeID` (`u32`)
  - Bytes 8..11: `PayloadLen` (`u32`)
  - Bytes 12..15: `CRC32` (`u32`)
- Return: Validated frame or error packet.

## Code Layout
- Automation & Linters: `automation/`
- Runtime Utilities: `usr/libexec/mios/`
- Configurations & SSOT: `usr/share/mios/`
- Python Core Services: `usr/lib/mios/`
- CI & Schema Tools: `tools/`
- Automated Tests: `tests/`
- Task Registries: `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`
