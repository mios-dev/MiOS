# Project: MiOS Roadmap Workstreams Implementation (T-389 through T-400)

## Architecture
MiOS ("My OS") is an immutable bootc/OCI Fedora container workstation and local self-replicating agentic AI edge OS. The system combines:
1. Native Rust micro-node runtime (`src/mios-rs/mios-node/`) and companion Python edge libraries (`usr/libexec/mios/node/`) speaking a 16-byte fixed binary wire protocol.
2. Compiled Rust core systems daemons (`miosd`), type-safe SSOT validator (`mios-check`), and fast multi-call binary CLI dispatcher (`/usr/bin/mios`).
3. Strict SSOT configuration model driven by `usr/share/mios/mios.toml`, unified agent memory (`mios-pgvector`), OpenAI-compatible AI routing (`MIOS_AI_ENDPOINT`), and 7 CI validation checks.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | T-389 | Wasm host import for local hardware GPIO/I2C access on edge nodes | M1 | survey |
| 2 | T-390 | Dynamic CPU core pinning and cgroup limits for mios-node workers | M1 | survey |
| 3 | T-391 | CRDT state compaction and snapshot garbage collection in mios-node | M1 | survey |
| 4 | T-400 | Hardware watchdog timer integration `/dev/watchdog` in mios-node | M1 | survey |
| 5 | T-392 | Task offloading priority queue with work-stealing scheduler | M2 | survey |
| 6 | T-393 | Zero-copy network buffer pooling for mios-node frames | M2 | survey |
| 7 | T-394 | Edge node capability advertising in Announce frames | M2 | survey |
| 8 | T-395 | BLE beaconing for offline local mesh bootstrap | M2 | survey |
| 9 | T-396 | Automated fallback to Tailscale and WireGuard overlay when LAN broadcast is partitioned | M2 | survey |
| 10 | T-397 | Standalone compiled `miosd` daemon in Rust replacing Python supervisor loops | M3 | survey |
| 11 | T-398 | Rust implementation of SSOT `mios.toml` validation and type checker | M3 | survey |
| 12 | T-399 | High-performance binary CLI dispatcher `/usr/bin/mios` in Rust | M3 | survey |
| 13 | Test Suites | Authored unit & integration tests in `tests/test-*.py` and `src/mios-rs/` cargo tests; registered in `[ci.tiers] unit` in `usr/share/mios/mios.toml` | M4 | survey |
| 14 | Registries Parity | 8-field schema adherence across `TASKS.md`, `AGY-TASKS.md`, metrics rollup via `tools/roadmap-index.py` | M5 | survey |
| 15 | SSOT Sync & CI | Machine projections sync (`tools/sync-generated.sh`), 7 CI checks pass with exit code 0, clean git status | M5 | survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Edge Runtime & Hardware Layer | T-389 (Wasm GPIO/I2C), T-390 (CPU pinning/cgroups), T-391 (CRDT snapshot GC), T-400 (Watchdog) | none | DONE |
| 2 | M2: Mesh Network & Transport Layer | T-392 (Work-stealing queue), T-393 (Buffer pool), T-394 (Announce capabilities), T-395 (BLE bootstrap), T-396 (Overlay fallback) | M1 | DONE |
| 3 | M3: Rust Core Daemons & Tooling | T-397 (Rust `miosd`), T-398 (`mios-check` validator), T-399 (Binary CLI dispatcher) | M1, M2 | DONE |
| 4 | M4: Test Suites & CI Registration | Dedicated tests for T-389..T-400 in `tests/test-*.py` and `src/mios-rs/`, registered under `[ci.tiers] unit` in `mios.toml` | M1, M2, M3 | DONE |
| 5 | M5: Registries Parity, Sync & CI Verification | 8-field schema in `TASKS.md` / `AGY-TASKS.md`, `ROADMAP.md` update, `tools/sync-generated.sh`, 7 CI passes, clean commit/push | M1, M2, M3, M4 | DONE |

## Interface Contracts

### Hardware & Wasm Interface (T-389)
- Host imports in Wasm environment: `mios_sys_gpio_read(pin: u32) -> i32`, `mios_sys_gpio_write(pin: u32, val: u32) -> i32`, `mios_sys_i2c_transfer(bus: u32, addr: u32, w_ptr: u32, w_len: u32, r_ptr: u32, r_len: u32) -> i32`.
- Gated by `[nodes.hardware_allowlist]` in `usr/share/mios/mios.toml`.

### Watchdog Interface (T-400)
- Device: `/dev/watchdog` (or `/dev/watchdog0`).
- IOCTL ping heartbeat interval default: 5s, timeout: 30s. Safe shutdown writes `'V'` to disable timer.

### Wire Protocol Framing & Capability Payload (T-393, T-394)
- 16-byte fixed binary header: `Magic 0x4D49`, `Version 0x01`, `MessageType 0x02` (NodeAnnounce), `NodeID u32`, `PayloadLen u32`, `CRC32 u32`.
- Announce Payload: JSON/Bincode struct including `cpu_cores`, `ram_mb`, `vram_mb`, `has_npu`, `has_gpu`, `supported_tiers`, `hardware_pins`, `active_transports`.

### Work-Stealing Scheduler (T-392)
- Multi-tier priority: Critical (0), High (1), Normal (2), Low (3).
- Steal policy: Steals half of batch from victim worker's deque if local queue is empty.

### Daemon & SSOT Validator (T-397, T-398, T-399)
- `miosd daemon`: Async Tokio supervisor, RAM < 15MB, atomic state in `/var/lib/mios/daemon/state.json`.
- `mios-check`: Type-safe schema validator for `mios.toml`, enforcing port uniqueness, Law 7 non-empty strings, and ratchet floors.
- `/usr/bin/mios`: Multi-call CLI dispatcher routing known verbs to `/usr/libexec/mios/*` in < 5ms.

## Code Layout
- Rust micro-node runtime: `src/mios-rs/mios-node/`
- Rust daemons & tooling: `src/mios-rs/miosd/`, `src/mios-rs/mios-config/`, `src/mios-rs/`
- Python node modules: `usr/libexec/mios/node/`
- Python test suites: `tests/test-*.py`
- Configuration & SSOT: `usr/share/mios/mios.toml`
- Task registries: `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`
- Verification & sync tools: `tools/sync-generated.sh`, `tools/drift-checks.py`, `tools/roadmap-index.py`, `tools/ci-suites.py`
