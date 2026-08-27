# Project: MiOS Roadmap Workstream Batch (T-573 to T-582)

## Architecture
MiOS is an immutable, bootc/OCI-shaped Fedora workstation and a local, self-replicating agentic AI OS.
This project batch implements 10 sequential roadmap tasks (T-573 through T-582) spanning hardware power management, living wallpaper occlusion throttling, declarative MCP gateway orchestration, acoustic wake-word filtering, and declarative Nix subsystem integration.

### Core Architectural Invariants:
1. **USR-OVER-ETC**: Default templates and schemas in `/usr/share/mios/` and `/usr/lib/`; `/etc/mios/` and `~/.config/mios/` for runtime overrides.
2. **NO-MKDIR-IN-VAR**: All `/var` persistent paths (e.g. `/var/nix`) declared declaratively via systemd tmpfiles (`usr/lib/tmpfiles.d/50-nix.conf`), never created via runtime build `mkdir`.
3. **BOUND-IMAGES**: All container and runtime tool dependencies strictly version-bound in `mios.toml`.
4. **BOOTC-CONTAINER-LINT**: Read-only `/usr` FHS layout compliant with bootc/ostree constraints.
5. **UNIFIED-AI-REDIRECTS**: All AI tool calls, agent invocations, and MCP schemas conform strictly to OpenAI-API-compatible surface contracts (`/v1/chat/completions`, JSON schema function definitions).
6. **UNPRIVILEGED-QUADLETS**: User-facing daemons run in unprivileged user sessions (`usr/lib/systemd/user/`).
7. **Legibility Ratchet Discipline**: Python modules modularized in domain subdirectories (`usr/libexec/mios/hw/`, `usr/libexec/mios/ux/`, `usr/libexec/mios/audio/`, `usr/libexec/mios/config/`) to preserve the `max_libexec_verbs = 285` ceiling.

---

## Feature Inventory
| # | Task | AGY ID | Feature | Description | Milestone | Status | Source |
|---|------|--------|---------|-------------|-----------|--------|--------|
| 1 | T-573 | AGY-2171 | Power Supply Detector & Inference Downscaler | `usr/libexec/mios/hw/powerd.py` & service | M1 | DONE | Survey |
| 2 | T-574 | AGY-2172 | Power Profile Benchmark Suite | `tests/test-power-profile-transitions.py` | M1 | DONE | Survey |
| 3 | T-575 | AGY-2173 | Living Wallpaper Occlusion Engine | `usr/libexec/mios/ux/wallpaperd.py` & service | M2 | DONE | Survey |
| 4 | T-576 | AGY-2174 | Wallpaper Frame Pacing Benchmark Suite | `tests/test-wallpaper-occlusion-throttle.py` | M2 | DONE | Survey |
| 5 | T-577 | AGY-2175 | Declarative MCP Server Lifecycle & Schema Converter | `usr/lib/mios/agent-pipe/mios_mcp.py` | M3 | DONE | Survey |
| 6 | T-578 | AGY-2176 | MCP Tool Discovery & Execution Test Suite | `tests/test-mcp-gateway-handshake.py` | M3 | DONE | Survey |
| 7 | T-579 | AGY-2177 | Three-Stage Acoustic Wake-Word Filter Chain | `usr/libexec/mios/audio/wakeword.py` & service | M4 | DONE | Survey |
| 8 | T-580 | AGY-2178 | Acoustic Wake-Word Benchmark Suite | `tests/test-acoustic-wakeword-pipeline.py` | M4 | DONE | Survey |
| 9 | T-581 | AGY-2179 | Multi-User Nix Subsystem & Tmpfiles Store | `automation/59-tools.sh` & tmpfiles | M5 | DONE | Survey |
| 10 | T-582 | AGY-2180 | Declarative Nix Flake Projection Generator | `usr/libexec/mios/config/nix_project.py` & template | M5 | DONE | Survey |
| 11 | — | — | SSOT Synchronization & Task Registry Parity | `sync-generated.sh`, `mios-sync-toml`, 7 CI Gates | M6 | DONE | Survey |
| 12 | — | — | Git Delivery & Remote CI Validation | Commit `325b8496` pushed to `origin/main` | M7 | DONE | Survey |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Hardware Powerd & Downscaler | T-573 (`powerd.py`, unit test `test-power-profile-transitions.py`, service) | None (T-572 done) | DONE |
| M2 | Living Wallpaper Occlusion | T-575 (`wallpaperd.py`, unit test `test-wallpaper-occlusion-throttle.py`, service) | M1 | DONE |
| M3 | Declarative MCP Gateway | T-577 (`mios_mcp.py`, `server.py`, unit test `test-mcp-gateway-handshake.py`) | M2 | DONE |
| M4 | Three-Stage Acoustic Wake-Word | T-579 (`wakeword.py`, unit test `test-acoustic-wakeword-pipeline.py`, service) | M3 | DONE |
| M5 | Declarative Nix Subsystem | T-581/T-582 (`59-tools.sh`, `50-nix.conf`, `nix_project.py`, flake template) | M4 | DONE |
| M6 | SSOT Sync & 7 CI Gates Verification | CI registration in `mios.toml`, `TASKS.md`/`AGY-TASKS.md` parity, 7 CI gates pass | M1..M5 | DONE |
| M7 | Gate Review, Audit & Git Delivery | Reviewers, Challengers, Forensic Auditor (PASS), Commit `325b8496` pushed | M6 | DONE |

---

## Key Artifacts Delivered
- `usr/libexec/mios/hw/powerd.py` & `usr/lib/systemd/system/mios-powerd.service`
- `usr/libexec/mios/ux/wallpaperd.py` & `usr/lib/systemd/user/mios-wallpaper.service`
- `usr/lib/mios/agent-pipe/mios_mcp.py`
- `usr/libexec/mios/audio/wakeword.py` & `usr/lib/systemd/user/mios-wakeword.service`
- `automation/59-tools.sh`, `usr/lib/tmpfiles.d/50-nix.conf`, `usr/share/mios/nix/nix.conf`
- `usr/share/mios/nix/flake-template.nix`, `usr/libexec/mios/config/nix_project.py`
- Test Suites: `test-power-profile-transitions.py` (11 tests), `test-wallpaper-occlusion-throttle.py` (10 tests), `test-mcp-gateway-handshake.py` (15 tests), `test-acoustic-wakeword-pipeline.py` (18 tests), `test-nix-project.py` (10 tests), `test-empirical-stress-t573-t582.py` (28 tests)
- Commit: `325b849638e456706db36b711760e822c0a94f4b` on `origin/main`
