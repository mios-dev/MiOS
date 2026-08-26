# Project: MiOS Roadmap Workstreams (T-382 Onwards)

## Architecture
- Module boundaries:
  - AI Plane (`usr/libexec/mios/ai/`, `usr/lib/systemd/system/mios-self-heal.service`): Self-healing remediation agent (`self_heal.py`) and synthetic Q&A generation pipeline (`synthetic_qa.py`).
  - Agent-Pipe (`usr/lib/mios/agent-pipe/`): Dynamic persona synthesis (`mios_persona.py`) and bounded reflection loop convergence (`mios_deliberate.py`).
  - Distributed Micro-Node Mesh (`src/mios-rs/mios-node/`, `usr/libexec/mios/node/`): Async Tokio TCP frame codecs, heartbeat monitor with 3-strike dead-peer eviction, and Ed25519/X25519/ChaCha20-Poly1305 mutual handshake and AEAD wire encryption.
  - CI & SSOT Registries: `usr/share/mios/mios.toml`, `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`, machine projections generated via `sync-generated.sh`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | T-382 / AGY-1980 | Autonomous self-healing code remediation agent triggered on systemd failures | M1 | Survey (TASKS.md / AGY-TASKS.md) |
| 2 | T-383 / AGY-1981 | Synthetic training Q&A data pipeline generating datasets from local documentation | M1 | Survey (TASKS.md / AGY-TASKS.md) |
| 3 | T-384 / AGY-1982 | Dynamic agent persona synthesis based on task domain classification | M1 | Survey (TASKS.md / AGY-TASKS.md) |
| 4 | T-385 / AGY-1983 | Bounded reflection loop convergence with semantic delta metrics | M1 | Survey (TASKS.md / AGY-TASKS.md) |
| 5 | T-386 / AGY-1984 | Async Tokio TCP frame reader and writer actor for mios-node | M2 | Survey (TASKS.md / AGY-TASKS.md) |
| 6 | T-387 / AGY-1985 | Node heartbeat monitor and automatic 3-strike dead-peer eviction | M2 | Survey (TASKS.md / AGY-TASKS.md) |
| 7 | T-388 / AGY-1986 | Ed25519 mutual handshake and ChaCha20-Poly1305 wire encryption | M2 | Survey (TASKS.md / AGY-TASKS.md) |
| 8 | CI & SSOT Sync | CI suite registration, 8-field schema task parity, SSOT machine projections sync, and 7 CI checks verification | M3 | Survey (Tooling / CI) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: AI Plane & Agent-Pipe | T-382 (Self-heal), T-383 (Synthetic QA), T-384 (Persona), T-385 (Reflection) | none | DONE |
| 2 | M2: Mesh Protocol & Node | T-386 (Async Frame), T-387 (Heartbeat Eviction), T-388 (Wire Crypto) | none | DONE |
| 3 | M3: Registries & CI Sync | CI test suites registration, TASKS/AGY-TASKS parity, SSOT sync, 7 CI gates verification, and clean commit | M1, M2 | DONE |

## Code Layout
- `usr/libexec/mios/ai/self_heal.py` — Autonomous self-healing diagnostic daemon (modular subdirectory preserves `max_libexec_verbs = 285/285`)
- `usr/lib/systemd/system/mios-self-heal.service` — Systemd service unit for self-healing daemon
- `usr/libexec/mios/ai/synthetic_qa.py` — Synthetic Q&A generator from documentation and ADRs
- `usr/lib/mios/agent-pipe/mios_persona.py` — Dynamic agent persona synthesis and intent classification
- `usr/lib/mios/agent-pipe/mios_deliberate.py` — Bounded reflection loops with convergence criteria
- `src/mios-rs/mios-node/src/net.rs` / `usr/libexec/mios/node/wire.py` — Async Tokio frame reader and writer
- `src/mios-rs/mios-node/src/heartbeat.rs` / `usr/libexec/mios/node/discovery.py` — Node heartbeat monitor & dead-peer eviction
- `src/mios-rs/mios-node/src/crypto.rs` / `usr/libexec/mios/node/wire.py` — Ed25519/X25519/ChaCha20-Poly1305 wire encryption
- `tests/test-self-healing.py` — Test suite for T-382
- `tests/test-synthetic-qa.py` — Test suite for T-383
- `tests/test-agent-persona.py` — Test suite for T-384
- `tests/test-bounded-reflection.py` — Test suite for T-385
- `tests/test-node-async-net.py` — Test suite for T-386
- `tests/test-node-heartbeat-eviction.py` — Test suite for T-387
- `tests/test-node-crypto-handshake.py` — Test suite for T-388
- `usr/share/mios/mios.toml` — SSOT configuration with `[ci.tiers] unit` test registration
- `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md` — Task registries and roadmap index

## Interface Contracts
### `self_heal.py` ↔ `systemd` / `agent-pipe`
- Captures journald error logs (`journalctl -u <unit> -n 100`)
- Enforces circuit breaker (max 3 restarts / 15 min)
- Strictly forbids writes to `/usr` (only `/etc` overrides and `/var` configuration)
- Logs RCA to `/var/log/mios/self-heal.log`

### `synthetic_qa.py` ↔ Local Markdown Corpus
- Harvests docs from `/usr/share/doc/mios/` and `cat/ADR-*.md`
- Redacts secrets, tokens, credentials before emitting JSONL records
- Emits multi-turn Q&A format compatible with `mios-opencode` fine-tuning

### `mios_persona.py` ↔ `agent-pipe/server.py`
- Classifies user request domain across 6 categories (`kernel_systems`, `database_storage`, `security_crypto`, `networking_mesh`, `ai_inference`, `devops_ci`, `generalist`)
- Injects specialized domain guidelines while preserving canonical system prompt laws

### `mios_deliberate.py` ↔ `agent-pipe/server.py`
- Evaluates semantic delta between reflection iterations
- Exits early if delta < 0.05 ("converged_diminishing_returns") or iteration >= 3 ("max_iterations")

### `net.rs` / `wire.py` ↔ Micro-Node Mesh
- 16-byte fixed binary header framing (`0x4D49`, version 1, opcode, node_id, payload_len, CRC32)
- Async stream decoding and encoding over Tokio TCP connections

### `heartbeat.rs` / `discovery.py` ↔ Routing Table
- 5s heartbeat interval, 3-strike dead peer detection (15s eviction threshold)
- Emits peer eviction events and prunes routing table

### `crypto.rs` / `wire.py` ↔ Inter-Node Security
- Ed25519 node identity signatures + X25519 ECDH key exchange
- HKDF-SHA256 key derivation -> ChaCha20-Poly1305 AEAD payload encryption
