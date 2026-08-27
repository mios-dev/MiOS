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
| # | Task | AGY ID | Feature | Description | Milestone | Source |
|---|------|--------|---------|-------------|-----------|--------|
| 1 | T-573 | AGY-2171 | Power Supply Detector & Inference Downscaler | `usr/libexec/mios/hw/powerd.py` & service | M1 | Survey |
| 2 | T-574 | AGY-2172 | Power Profile Benchmark Suite | `tests/test-power-profile-transitions.py` | M1 | Survey |
| 3 | T-575 | AGY-2173 | Living Wallpaper Occlusion Engine | `usr/libexec/mios/ux/wallpaperd.py` & service | M2 | Survey |
| 4 | T-576 | AGY-2174 | Wallpaper Frame Pacing Benchmark Suite | `tests/test-wallpaper-occlusion-throttle.py` | M2 | Survey |
| 5 | T-577 | AGY-2175 | Declarative MCP Server Lifecycle & Schema Converter | `usr/lib/mios/agent-pipe/mios_mcp.py` | M3 | Survey |
| 6 | T-578 | AGY-2176 | MCP Tool Discovery & Execution Test Suite | `tests/test-mcp-gateway-handshake.py` | M3 | Survey |
| 7 | T-579 | AGY-2177 | Three-Stage Acoustic Wake-Word Filter Chain | `usr/libexec/mios/audio/wakeword.py` & service | M4 | Survey |
| 8 | T-580 | AGY-2178 | Acoustic Wake-Word Benchmark Suite | `tests/test-acoustic-wakeword-pipeline.py` | M4 | Survey |
| 9 | T-581 | AGY-2179 | Multi-User Nix Subsystem & Tmpfiles Store | `automation/59-tools.sh` & tmpfiles | M5 | Survey |
| 10 | T-582 | AGY-2180 | Declarative Nix Flake Projection Generator | `usr/libexec/mios/config/nix_project.py` & template | M5 | Survey |
| 11 | — | — | SSOT Synchronization & Task Registry Parity | `sync-generated.sh`, `mios-sync-toml`, 7 CI Gates | M6 | Survey |
| 12 | — | — | Git Delivery & Remote CI Validation | Commit & push to `c:\MiOS` & `c:\mios-bootstrap` | M7 | Survey |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Hardware Powerd & Downscaler | T-573 (`powerd.py`, unit test `test-power-profile-transitions.py`, service) | None (T-572 done) | PLANNED |
| M2 | Living Wallpaper Occlusion | T-575 (`wallpaperd.py`, unit test `test-wallpaper-occlusion-throttle.py`, service) | M1 | PLANNED |
| M3 | Declarative MCP Gateway | T-577 (`mios_mcp.py`, `server.py`, unit test `test-mcp-gateway-handshake.py`) | M2 | PLANNED |
| M4 | Three-Stage Acoustic Wake-Word | T-579 (`wakeword.py`, unit test `test-acoustic-wakeword-pipeline.py`, service) | M3 | PLANNED |
| M5 | Declarative Nix Subsystem | T-581/T-582 (`59-tools.sh`, `50-nix.conf`, `nix_project.py`, flake template) | M4 | PLANNED |
| M6 | SSOT Sync & 7 CI Gates Verification | CI registration in `mios.toml`, `TASKS.md`/`AGY-TASKS.md` parity, 7 CI gates pass | M1..M5 | PLANNED |
| M7 | Gate Review, Audit & Git Delivery | Reviewers, Challengers, Forensic Auditor (HARD VETO), Git push across both repos | M6 | PLANNED |

---

## Interface Contracts

### 1. Power Daemon Contract (`usr/libexec/mios/hw/powerd.py`)
- CLI:
  - `--status --json`: Returns `{"power_source": "AC"|"BATTERY", "cpu_epp": "balance_performance"|"power", "active_model_tier": "heavy"|"light_3b", "paused_containers": [...]}`
  - `--set-state [ac|dc]`: Triggers deterministic profile transition
  - `--mock`: Headless mock mode
  - `--daemon`: Starts daemon event loop
- Service: `usr/lib/systemd/system/mios-powerd.service`

### 2. Wallpaper Occlusion Contract (`usr/libexec/mios/ux/wallpaperd.py`)
- CLI:
  - `--status --json`: Returns `{"rendering": true|false, "fps": 0|60, "gpu_load_pct": 0.0|1.8, "occluded": true|false}`
  - `--socket <path>`: Listens on `/run/user/$UID/mios-wallpaper.sock` for telemetry JSON updates
  - `--set-occluded [true|false]`: Sets occlusion state
  - `--mock`: Headless mock mode
- Service: `usr/lib/systemd/user/mios-wallpaper.service`

### 3. MCP Manager Contract (`usr/lib/mios/agent-pipe/mios_mcp.py`)
- Configuration: `[mcp.servers.<name>]` in `mios.toml`
- Core API:
  - `load_servers_from_toml(toml_data: dict) -> List[McpServerSpec]`
  - `convert_mcp_to_openai_schema(mcp_tool: dict, server_id: str) -> dict` -> strict OpenAI `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`
  - `async dispatch_tool_call(server_id: str, tool_name: str, arguments: dict) -> dict`

### 4. Acoustic Wake-Word Contract (`usr/libexec/mios/audio/wakeword.py`)
- CLI:
  - `--status --json`: Returns `{"state": "listening"|"triggered"|"idle", "vad_active": bool, "wakeword_detected": bool, "cpu_usage_pct": float}`
  - `--process-pcm <path>`: Processes raw PCM audio file through 3 stages (RNNoise -> Silero VAD -> OpenWakeWord)
  - `--threshold <float>`: Float detection threshold (default 0.6)
  - `--mock`: Deterministic mock mode
- Service: `usr/lib/systemd/user/mios-wakeword.service`

### 5. Nix Integration Contract (`usr/libexec/mios/config/nix_project.py`)
- Tmpfiles: `usr/lib/tmpfiles.d/50-nix.conf` (`L+ /nix - - - - /var/nix`)
- Configuration: `usr/share/mios/nix/nix.conf`
- Template: `usr/share/mios/nix/flake-template.nix`
- CLI:
  - `--render-flake [--output <path>]`: Reads `mios.toml` (`[dotfiles]`, `[packages]`, `[shell]`), outputs flake
  - `--validate-flake <path>`: Checks Nix flake syntax
  - `--mock`: Headless mock mode

---

## Code Layout
- `usr/libexec/mios/hw/`: Hardware monitoring and power management modules
- `usr/libexec/mios/ux/`: Desktop environment, living wallpaper, and UX modules
- `usr/lib/mios/agent-pipe/`: Agent-pipe router, federation, and MCP gateway integration
- `usr/libexec/mios/audio/`: Voice front-end, acoustic filter chain, and wake-word detection
- `usr/libexec/mios/config/`: Declarative projection generators (Nix flakes, dotfiles)
- `usr/share/mios/nix/`: Vendor templates and configuration files for Nix subsystem
- `usr/lib/tmpfiles.d/`: Declarative `/var` filesystem storage specifications
- `usr/lib/systemd/system/` & `usr/lib/systemd/user/`: Systemd service units
- `tests/`: Automated unit test suites (`test-power-profile-transitions.py`, `test-wallpaper-occlusion-throttle.py`, `test-mcp-gateway-handshake.py`, `test-acoustic-wakeword-pipeline.py`, `test-nix-project.py`)
