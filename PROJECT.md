# Project: MiOS iGPU Inference Lane, RPC Compute Fabric & Rust Hardcode-Lint Consolidation

## Architecture
MiOS local neural infrastructure and verification tooling operate across the Windows host and WSL2 container boundaries under Architectural Laws 5 (UNIFIED-AI-REDIRECTS), 7 (NO-HARDCODE), 8 (SSOT-PROJECTION), and 14 (TARGET-LANGUAGES):
- **Windows Host iGPU Inference Lane (T-211)**: AMD Radeon iGPU (0x13c0) is driven natively on Windows via Vulkan using `llama-server.exe` managed by `usr/share/mios/windows/mios-igpu-server.ps1`. The service binds strictly to `127.0.0.1` on port `8540` (`MIOS_PORT_LLM_IGPU`), enforcing DirectX `GpuPreference=1;` for low-power AMD iGPU execution with zero RTX 4090 dGPU VRAM allocation. The `mios-ainode.exe` mock facade is purged in favor of real `llama.cpp` inference.
- **Federated llama.cpp RPC Fabric (T-212)**: Bridges host AMD iGPU and container NVIDIA RTX 4090. A Windows-native `rpc-server.exe` binds to the AMD iGPU on port `8540`/`8550` with `$env:GGML_VK_DISABLE_COOPMAT = '1'`. The WSL2 coordinator (`llama-server`/`llama-swap`) on port `8500` offloads model layers across localhost loopback using `--rpc 127.0.0.1:8540 --split-mode layer --tensor-split 24,4`, exposing a single logical OpenAI endpoint at `http://localhost:8500/v1` (`MIOS_AI_ENDPOINT`).
- **Compiled Rust Static Tooling (T-1161 / AGY-1457)**: `usr/libexec/mios/mios-hardcode-lint` is ported to a high-performance native Rust crate at `tools/native/mios-hardcode-lint/` registered in `usr/share/mios/mios.toml` `[build.native.categories.cli].binaries`. It provides 100% CLI argument, exit code, and stdout/stderr output parity with static musl linkage.
- **Standing Gate Certification & Two-Sided Controls**: Every modified gate, script, and binary is verified by positive controls and negative planted defect controls, passing all 5 standing gates (`phase-registry`, `ratchet-direction`, `credential-literals`, `version-literals-ssot`, `signature-policy`), `ci-suites.py --check`, `sync-bootstrap.py --check`, and `sync-generated.sh`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Purge Mock Hijack in `mios-igpu-server.ps1` | Remove `mios-ainode.exe` mock bypass (lines 85–99) to run authentic `llama-server.exe` | M1 | T-211 / Survey |
| F2 | Localhost & Law 5 Standardization for iGPU | Bind `mios-igpu-server.ps1` strictly to `127.0.0.1` and remove Tailscale IP dependencies | M1 | T-211 / Survey |
| F3 | Low-Power GPU Routing (`GpuPreference=1;`) | Enforce DirectX `UserGpuPreferences` `GpuPreference=1;` and `--device` AMD regex matching with `-fit off` | M1 | T-211 / Survey |
| F4 | SSOT Inference Category Port Derivation | Add `llm_igpu` and `rpc_igpu` to `[ports.categories.inference].members` (8540, 8550) in `usr/share/mios/mios.toml` | M1 | T-211 / Survey |
| F5 | Local GGUF Model Fallback & GitHub Asset Fix | Resolve local models from `\\wsl$\podman-MiOS-DEV\var\lib\mios\llamacpp\models\` and fix GitHub release array parsing | M1 | T-211 / Survey |
| F6 | Cross-Lane llama.cpp RPC Server Configuration | Implement `-Mode Rpc` in `mios-igpu-server.ps1` and systemd unit for `llama-rpc-server` | M2 | T-212 / Survey |
| F7 | Federated Multi-Lane Compute Sharding | Federate coordinator under `llama-server --rpc <host>:<port> --split-mode layer` | M2 | T-212 / Survey |
| F8 | Vulkan Cooperative Matrix Fallback | Detect/enforce safe Vulkan compute shader fallback via `GGML_VK_DISABLE_COOPMAT=1` on iGPU | M2 | T-212 / Survey |
| F9 | Rust Port of `mios-hardcode-lint` | Implement `tools/native/mios-hardcode-lint/` in Rust with `regex`, `toml`, `walkdir` | M3 | T-1161 / Survey |
| F10 | Hardcode-Lint Parity & Strangler Migration | Wire Rust binary into `98-drift-checks.sh:check_no_hardcode` with full CLI parity | M3 | T-1161 / Survey |
| F11 | Two-Sided Verification Controls | Implement positive controls and negative defect plants across iGPU, RPC, and lint | M4 | R5 / Survey |
| F12 | Standing Gates & Sync Certification | Pass all 5 standing gates, `ci-suites.py --check`, `sync-bootstrap.py --check`, and `sync-generated.sh` | M4 | R5 / Survey |
| F13 | Comprehensive E2E Testing Suite (Tiers 1-4) | Requirement-driven opaque-box test suite covering all features, boundaries, and scenarios | M5 | R5 / E2E Track |
| F14 | Tier 5 Adversarial Coverage Hardening | White-box adversarial stress tests and coverage audit | M5 | R5 / E2E Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | iGPU Localhost OpenAI Lane (T-211) | Refactor `mios-igpu-server.ps1`, eliminate mock, bind `127.0.0.1`, wire `mios.toml` port 8540, enforce `GpuPreference=1;` | none | IN_PROGRESS |
| M2 | Federated llama.cpp RPC Fabric (T-212) | Configure `rpc-server` on Windows iGPU, coordinator federation in `llama-swap.yaml`, Vulkan coopmat fallback | M1 | PLANNED |
| M3 | Rust `mios-hardcode-lint` (T-1161) | Implement `tools/native/mios-hardcode-lint`, register in `mios.toml`, verify 100% parity against Python oracle | none | PLANNED |
| M4 | Two-Sided Controls & Standing Gates | Two-sided test suites, standing gates certification, `sync-generated.sh`, clean repo state | M1, M2, M3 | PLANNED |
| M5 | E2E Test Suite & Adversarial Hardening | Pass 100% of E2E test suite (Tiers 1-4) and Tier 5 adversarial coverage hardening | M4 | PLANNED |

## Interface Contracts
### `mios-igpu-server.ps1` ↔ Localhost Callers (T-211)
- Host/Port: `http://127.0.0.1:8540`
- Wire protocol: HTTP/1.1 REST
- Endpoints:
  - `GET /health` → `{"status":"ok"}`
  - `GET /v1/models` → `{"object":"list","data":[{"id":"mios-igpu",...}]}`
  - `POST /v1/chat/completions` → Standard OpenAI JSON streaming/non-streaming response
- Hardware execution: Exclusively AMD Radeon iGPU (`0x13c0`), zero RTX 4090 VRAM.

### Coordinator `llama-server` ↔ `rpc-server` (T-212)
- Wire protocol: TCP raw RPC (`--rpc 127.0.0.1:8540`)
- Partitioning: Pipeline parallelism (`--split-mode layer --tensor-split 24,4`)
- Logical endpoint: `http://localhost:8500/v1/chat/completions` fronted by `llama-swap`

### `tools/native/mios-hardcode-lint` ↔ `automation/98-drift-checks.sh` (T-1161)
- CLI invocation: `mios-hardcode-lint <ROOT_DIR>`
- Exit codes:
  - `0`: Clean tree or `MIOS_HARDCODE_LINT_SOFT=1` with non-blocking issues.
  - `1`: Found hardcoded IP, port, date in string/comment, bad header, or Ventoy violation.
- Stdout parity: `[mios-hardcode-lint] PASS: <N> file(s) scanned; no date-in-comment/string / header crash-risk / port-IP hardcode.`

## Code Layout
- `usr/share/mios/windows/mios-igpu-server.ps1` — Windows host iGPU & RPC launcher script
- `usr/share/mios/mios.toml` — Primary SSOT: `[ports]`, `[lanes]`, `[nodes]`, `[build.native]`
- `usr/share/mios/llamacpp/llama-swap.yaml` — Multi-lane model routing & federation config
- `usr/libexec/mios/mios-model-router` — Python model router CLI
- `tools/native/mios-hardcode-lint/` — New compiled Rust static binary crate
  - `Cargo.toml`, `src/main.rs`, `src/lint.rs`, `src/exempt.rs`
- `automation/98-drift-checks.sh` — Gate runner with strangler integration
- `tests/test-igpu-lane-e2e.py` — Positive & negative verification suite for iGPU/RPC
- `tests/test-hardcode-lint-parity.py` — Parity and two-sided verification suite for Rust lint
