# Project: MiOS Native Static Binaries Hardening & Consolidation

## Architecture
MiOS native executable infrastructure consists of two Cargo workspaces (`tools/native/` and `src/mios-rs/`) operating under Architectural Law 14 (WS-LANG / ADR-0011).
- **Toolchain & Linkage**: Production Linux binaries are compiled for `x86_64-unknown-linux-musl` with `-C target-feature=+crt-static`, `rust-lld`, and static-pie (`DF_1_PIE`). Standalone binaries contain no `PT_INTERP` or `DT_NEEDED` glibc dependencies.
- **Shared Daemon Infrastructure**: Repetitive socket discovery, UID verification, process spawning, and dynamic SSOT resolution across daemons (`mios-agent-relay`, `mios-wallpaperd`, `mios-launch`, `mios-edge-status`, `mios-ai-config`) are consolidated into `tools/native/mios-service-core`.
- **Script Consolidation & Ratchet Restoration**: Stale Python twins (`mios-toml-get`, `check-template-conformance`, `compile-templates.py`, `audit-version-literals.py`) are retired in favor of compiled native Rust equivalents; colliding phases in `automation/` are folded to bring `legibility-ratchet` into full compliance with zero ceiling increases.
- **SSOT Dynamism & Law 5**: All runtime parameters are resolved from `usr/share/mios/mios.toml` dynamically. Zero hardcoded ports, zero vendor-cloud endpoints, and zero secret literals.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Static Linkage Audit | Automated audit of ELF headers in `tools/native/` and `src/mios-rs/` asserting absence of `PT_INTERP` and `DT_NEEDED` glibc dependencies | M1 | T-1148 / R1 |
| F2 | Static Linkage Standing Gate | `mios-gate static-linkage` and `98-drift-checks.sh:check_static_linkage` to gate binary static linkage in CI | M1 | T-1148 / R1 |
| F3 | Stale Python Twins Retirement | Retire redundant scripts (`usr/libexec/mios/mios-toml-get`, `check-template-conformance`, `compile-templates.py`, `audit-version-literals.py`) in favor of existing native Rust crates | M2 | T-1161 / R2 |
| F4 | Automation Phase Consolidation | Fold colliding phases (`02-uki-bootloader.sh` into `76-uki-render.sh`, `24-gpu-pv-shim.sh` into `20-hardware.sh`) restoring `max_automation_phases=77` | M2 | T-1161 / R2 |
| F5 | Libexec Verb Consolidation | Replace forwarding shims with native `miosd`/symlinks to restore `max_libexec_verbs=310` | M2 | T-1161 / R2 |
| F6 | Shared Daemon Crate (`mios-service-core`) | Scaffold and implement shared crate in `tools/native/mios-service-core` for socket discovery, UID checks, and SSOT helpers | M3 | T-1162 / R3 |
| F7 | Daemon Refactoring | Refactor `mios-agent-relay`, `mios-wallpaperd`, and `mios-launch` to consume `mios-service-core` | M3 | T-1162 / R3 |
| F8 | Two-Sided Verification & Gate Pass | Implement positive and negative controls for all modified gates and binaries | M4 | R5 / Standing Gates |
| F9 | Repo Sync & Drift Reconciliation | Reconcile `build-mios.ps1` gnullvm detection across `MiOS` and `mios-bootstrap`, running clean `sync-bootstrap.py` and `sync-generated.sh` | M4 | R5 / Standing Gates |
| F10 | E2E Testing Suite (Tiers 1-4) & Adversarial Hardening (Tier 5) | Full 4-tier E2E testing suite + adversarial coverage audit | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Static Linkage Gate (T-1148) | Implement `verify_static_elf` integration in `mios-gate static-linkage` and `check_static_linkage` in `98-drift-checks.sh` | none | PLANNED |
| M2 | Script Consolidation (T-1161) | Retire stale Python twins, fold colliding automation phases, and restore legibility ratchets | M1 | PLANNED |
| M3 | Shared Daemon Components (T-1162) | Scaffold `tools/native/mios-service-core` and refactor daemons | M1 | PLANNED |
| M4 | Gate & Sync Reconciliation | Reconcile `build-mios.ps1`, pass all 5 standing gates, `ci-suites.py`, and `sync-generated.sh` | M2, M3 | PLANNED |
| M5 | E2E Verification & Hardening | Pass 100% of E2E test suite (Tiers 1-4) and Tier 5 adversarial hardening | M4 | PLANNED |

## Interface Contracts
### `mios-gate` ↔ `automation/98-drift-checks.sh`
- CLI command: `mios-gate static-linkage --root <PATH>`
- Exit code 0: All standalone Linux release ELF binaries in `<PATH>` are static (no `PT_INTERP`, no `DT_NEEDED`, valid `DF_1_PIE` for x86_64).
- Exit code 1: Any standalone Linux binary is dynamically linked or corrupt; prints offending binary and reason to stderr.

### `mios-service-core` ↔ Daemon Binaries (`mios-agent-relay`, etc.)
- `mios_service_core::socket`:
  - `find_active_socket(candidates: &[&str]) -> Result<PathBuf, SocketError>`
  - `verify_socket_owner(path: &Path) -> Result<bool, SocketError>`
- `mios_service_core::ssot`:
  - `require_port(key: &str) -> Result<u16, ConfigError>`
  - `resolve_endpoint(key: &str) -> Result<String, ConfigError>`

### CLI Entrypoint Compatibility
- All symlinked or consolidated commands (`mios-toml-get`, `check-template-conformance`, etc.) preserve identical CLI flags, stdout output, stderr messages, and exit codes.

## Code Layout
- `tools/native/mios-service-core/` — New shared workspace crate
  - `Cargo.toml`
  - `src/lib.rs`, `src/socket.rs`, `src/ssot.rs`
- `src/mios-rs/mios-gate/` — Linkage gate extension
  - `src/static_linkage.rs`, `src/main.rs`
- `automation/98-drift-checks.sh` — Gate runner addition
- `usr/share/mios/mios.toml` — SSOT phase and tier registrations
- `tools/sync-bootstrap.py` — Mirror authority
