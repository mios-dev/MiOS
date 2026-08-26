# Project: MiOS Open Roadmap & Runtime Integration

## Architecture
- Submodule isolation under `usr/libexec/mios/` preserving `max_libexec_verbs = 285`.
- Native Linux FHS folder layout across `usr/`, `etc/`, `var/`.
- Single AI endpoint contract (`MIOS_AI_ENDPOINT`) and Quadlet container services.
- Immutable bootc/ostree UKI + composefs verity security chain.
- Discrete GPU passthrough via `vfio-pci` + Looking Glass B6 IVSHMEM (`kvmfr`).
- Quadlet secrets isolation via `EnvironmentFile=/etc/mios/secrets.env` (0600).
- Multi-partition deployment staging (`MiOS-Repo` config vs `MiOS-Data` bulk storage).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Wasm Sandbox Engine | Tier-1 Wasm sandbox with fuel bounding, 64MB limit, and `mios_sys_*` host imports (T-347 / NODE-02) | M1 | Survey |
| 2 | Vector SSOT Authority | PostgreSQL + pgvector as live runtime SSOT with lossless bidirectional TOML materialization (T-350 / VECTOR-05) | M1 | Survey |
| 3 | CephFS PAM Provisioning | Multi-tenant user CephFS auto-provisioning & CephX auth with PAM integration (T-352 / STRG-11) | M2 | Survey |
| 4 | UKI & Boot Chain Verity | UKI PE magic, PCR measurements (4/7/11), and composefs fs-verity verification (T-353 / SEC-04) | M2 | Survey |
| 5 | Quadlet Secrets Hardening | 0600 `/etc/mios/secrets.env` rotation service and elimination of grandfathered literals (T-355 / SEC-05) | M2 | Survey |
| 6 | Discrete VFIO & Looking Glass | Full-device GPU passthrough & Looking Glass B6 IVSHMEM memory validation (T-354 / VFIO-01) | M3 | Survey |
| 7 | MiOS-Cat Staging Separation | Multi-partition USB staging keeping OCI image archives strictly on `MiOS-Data` (T-356 / CAT-05) | M3 | Survey |
| 8 | CI Test Suites & Registry Sync | Unit test authoring, registration in `mios.toml` `[ci.tiers].unit`, and CI suite verification | M4 | Survey |
| 9 | Task Registry & Parity Gates | `TASKS.md`, `AGY-TASKS.md`, and `ROADMAP.md` 8-field schema and parity verification across all 7 CI checks | M5 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Runtime Core | T-347 (Wasm Sandbox) & T-350 (Vector SSOT Authority) | none | DONE |
| M2 | Storage & Security | T-352 (CephFS PAM), T-353 (UKI / fs-verity), T-355 (Quadlet Creds) | M1 | DONE |
| M3 | VFIO & Deployment | T-354 (VFIO Looking Glass) & T-356 (MiOS-Cat Staging) | M2 | DONE |
| M4 | Test Suites & CI Registration | Unit test execution & CI suite registration in `mios.toml` | M1, M2, M3 | DONE |
| M5 | Registry Sync & Gate Verification | Update `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`, pass all 7 CI gates, commit and push | M4 | DONE |

## Interface Contracts

### Wasm Sandbox (`usr/libexec/mios/node/wasm_sandbox.py`)
- Class: `WasmSandboxEngine(config: WasmExecutionConfig)`
- Config: `max_memory_bytes: int = 64 * 1024 * 1024`, `max_fuel: int = 1_000_000`
- Exit codes: 0 (success), 124 (fuel exhausted), 137 (memory limit exceeded)
- Host imports: `mios_sys_read`, `mios_sys_write`, `mios_sys_log`, `mios_sys_time`, `mios_sys_exit`

### Config SSOT Materializer (`usr/libexec/mios/materialize-config-toml.py`)
- Functions: `escape_toml_key(key: str) -> str`, `format_toml_value(val: Any) -> str`
- Query: `config_kv` (layer = 0) and `domain_verb` / `verb` tables to generate valid TOML string.

### CephFS Provisioner (`usr/libexec/mios/mios-cephfs-provision`)
- CLI: `mios-cephfs-provision validate <user> <group>`, `create <user> <group>`, `delete <user>`
- PAM module: `usr/lib/pam.d/mios-cephfs-auth` invoking `pam_exec.so /usr/libexec/mios/mios-cephfs-provision validate %u %g`

### Boot Chain Verifier (`usr/libexec/mios/sec/verify-boot-chain.py`)
- Class: `BootChainVerifier`
- Methods: `verify_fsverity_digest()`, `verify_pcr_measurements()`, `check_uki_structure()`
- CLI: `--check`, `--mock`, `--json`

### Quadlet Secrets Hardener (`usr/libexec/mios/sec/rotate-quadlet-secrets.py`)
- Class: `QuadletSecretsHardener`
- Target: `/etc/mios/secrets.env` (mode `0600`)
- Service: `usr/lib/systemd/system/mios-secret-init.service`

### Looking Glass Setup (`usr/libexec/mios/vfio/setup-looking-glass.py`)
- Class: `LookingGlassManager(shm_path: str, size_mb: int)`
- Methods: `generate_ivshmem_xml()`, `validate_shm_allocation()`

## Code Layout
- Core submodules: `usr/libexec/mios/{node,sec,vfio,db}/`
- Systemd units: `usr/lib/systemd/system/`
- PAM configuration: `usr/lib/pam.d/`
- Quadlet definitions: `usr/share/containers/systemd/`
- Test suites: `tests/test-*.py`
- CI configuration: `usr/share/mios/mios.toml`
- Task registries: `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`
