# Project: MiOS Roadmap Workstreams T-449 to T-470

## Architecture
MiOS is an immutable, bootc/OCI-shaped Fedora workstation that is also a local, self-replicating agentic AI OS.
The roadmap workstreams T-449 through T-470 encompass:
1. **Security & Schema Validation**: FIDO2/CTAP2 token LUKS2 enrollment (`usr/libexec/mios/sec/`) and automated Windows unattend XML schema validation (`usr/libexec/mios/win/`).
2. **System UX, Theming & Multi-Desktop Integration**: Living wallpaper shaders, cross-platform palette synchronization, Quickshell status bar, tmux theme generation, fastfetch generation, Hyprland/Sway configs, audio feedback, notification daemon, GNOME Shell extension, editor configs, btop themes, font scaling, biometric lock, focus audio, and clipboard sync (`usr/libexec/mios/ux/`).
3. **Autonomous Diff Snapshot & Image Bake Lifecycle**: Pre-shutdown diff capture, boot diff accrual risk classification, operator diff auditing, background OCI image synthesis inside podman-MiOS-DEV, and Greenboot post-bake health gating (`usr/libexec/mios/deploy/`, `usr/libexec/mios/sec/`, `usr/libexec/mios/ux/`).
4. **Architectural Invariants**:
   - `max_libexec_verbs = 285/285` strictly preserved by placing all 22 modules in depth-4 subdirectories (`sec/`, `win/`, `ux/`, `deploy/`).
   - `ps_lines = 22618/22618` preserved (all implementations in Python 3 standard library with deterministic mock harnesses).
   - 8-field task schema adherence in `TASKS.md` and `AGY-TASKS.md`.
   - Dedicated unit test suites in `tests/test-*.py` registered in `[ci.tiers] unit` in `usr/share/mios/mios.toml`.
   - Complete 7-gate repository CI verification and clean git status.

## Feature Inventory
| # | Task | Feature | Description | Target Path | Milestone | Source |
|---|------|---------|-------------|-------------|-----------|--------|
| 1 | T-449 | LUKS2 FIDO2 Token Enrollment | Portable drive LUKS2 FIDO2 / CTAP2 token enrollment helper | usr/libexec/mios/sec/fido2_enroll.py | M1 | ORIGINAL_REQUEST §R1 |
| 2 | T-450 | Windows Unattend XML Validation | Automated validation of Windows unattend XML schema against XSD rules | usr/libexec/mios/win/unattend_validate.py | M1 | ORIGINAL_REQUEST §R1 |
| 3 | T-451 | Living Wallpaper Shader Renderer | Real-time living wallpaper GLSL fragment shader renderer with telemetry | usr/libexec/mios/ux/living_wallpaper.py | M2 | ORIGINAL_REQUEST §R1 |
| 4 | T-452 | Cross-Platform Theme Sync | Palette synchronizer writing directly to Windows Registry and GTK3/4 CSS | usr/libexec/mios/ux/theme_sync.py | M2 | ORIGINAL_REQUEST §R1 |
| 5 | T-453 | Quickshell Status Bar Telemetry | Status bar component streaming live LLM VRAM and agent turns | usr/libexec/mios/ux/status_bar.py | M2 | ORIGINAL_REQUEST §R1 |
| 6 | T-454 | Tmux Theme Generator | Terminal multiplexer tmux theme generator deriving active pane styles | usr/libexec/mios/ux/tmux_theme.py | M2 | ORIGINAL_REQUEST §R1 |
| 7 | T-455 | Fastfetch Config Generator | Fastfetch configuration generator projecting host hardware and AI specs | usr/libexec/mios/ux/fastfetch_gen.py | M2 | ORIGINAL_REQUEST §R1 |
| 8 | T-456 | Window Manager Config Generator | Hyprland and Sway tiling WM configuration generator from SSOT | usr/libexec/mios/ux/wm_config_gen.py | M2 | ORIGINAL_REQUEST §R1 |
| 9 | T-457 | Audio Feedback Daemon | Audio feedback daemon playing subtle non-intrusive sound cues | usr/libexec/mios/ux/audio_feedback.py | M2 | ORIGINAL_REQUEST §R1 |
| 10 | T-458 | System Notification Daemon | Notification daemon routing agent-pipe / Hermes alerts to desktop | usr/libexec/mios/ux/notification_daemon.py | M2 | ORIGINAL_REQUEST §R1 |
| 11 | T-459 | GNOME Shell Top Panel Extension | GNOME Shell indicator showing active agent status and quick links | usr/libexec/mios/ux/gnome_extension.py | M3 | ORIGINAL_REQUEST §R1 |
| 12 | T-460 | VS Code & Cursor Config Generator | Editor configuration generator with pre-configured OpenAI local endpoint | usr/libexec/mios/ux/editor_config_gen.py | M3 | ORIGINAL_REQUEST §R1 |
| 13 | T-461 | Btop Theme Renderer | Btop theme renderer outputting exact RGB hex colors from [colors] SSOT | usr/libexec/mios/ux/btop_theme.py | M3 | ORIGINAL_REQUEST §R1 |
| 14 | T-462 | Dynamic Font Scaler | Dynamic font size scaler for High-DPI displays across terminal & desktop | usr/libexec/mios/ux/font_scaler.py | M3 | ORIGINAL_REQUEST §R1 |
| 15 | T-463 | Biometric Screen Lock Manager | Screen lock manager with biometric FIDO2 and fingerprint authentication | usr/libexec/mios/ux/biometric_lock.py | M3 | ORIGINAL_REQUEST §R1 |
| 16 | T-464 | Focus Ambient Audio Generator | Ambient background audio generator for deep focus programming | usr/libexec/mios/ux/focus_audio.py | M3 | ORIGINAL_REQUEST §R1 |
| 17 | T-465 | Cross-Platform Clipboard Sync | Clipboard synchronizer between host and VMs with token redaction | usr/libexec/mios/ux/clipboard_sync.py | M3 | ORIGINAL_REQUEST §R1 |
| 18 | T-466 | Shutdown Diff Snapshot Hook | Systemd pre-poweroff diff snapshot hook capturing git & /etc diffs | usr/libexec/mios/deploy/diff_snapshot.py | M4 | ORIGINAL_REQUEST §R1 |
| 19 | T-467 | Diff Accrual Risk Classifier | Startup diff accrual analyzer classifying safe vs high-risk modifications | usr/libexec/mios/deploy/diff_accrual.py | M4 | ORIGINAL_REQUEST §R1 |
| 20 | T-468 | Interactive Diff Auditor | Quickshell and CLI interactive diff auditor enabling operator approval | usr/libexec/mios/ux/diff_auditor.py | M4 | ORIGINAL_REQUEST §R1 |
| 21 | T-469 | Autonomous Image Bake Service | Background OCI image synthesis service rolling diffs into bootc images | usr/libexec/mios/deploy/image_bake.py | M4 | ORIGINAL_REQUEST §R1 |
| 22 | T-470 | Greenboot Post-Bake Health Gate | Greenboot health gate with automated fallback on diff regressions | usr/libexec/mios/sec/greenboot_gate.py | M4 | ORIGINAL_REQUEST §R1 |
| 23 | Tests | Dedicated Unit Test Suites | 22 test suites in tests/test-*.py registered in mios.toml | tests/test-*.py | M5 | ORIGINAL_REQUEST §R2 |
| 24 | CI | Registry Parity & CI Gates | Parity update in TASKS.md / AGY-TASKS.md, projections sync, 7 CI gates | TASKS.md, tools/ | M6 | ORIGINAL_REQUEST §R3, §R4 |
| 25 | Final | Full Verification & Commit | Reviewer, Challenger, Forensic Auditor review and clean git push | origin/main | M7 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Security & Schema Validation | T-449 (fido2_enroll.py), T-450 (unattend_validate.py) | none | PLANNED |
| M2 | System UX & Theming Part 1 | T-451 through T-458 (ux/*.py) | none | PLANNED |
| M3 | System UX & Theming Part 2 | T-459 through T-465 (ux/*.py) | none | PLANNED |
| M4 | Diff Snapshot & Image Bake Lifecycle | T-466, T-467, T-469 (deploy/), T-468 (ux/), T-470 (sec/) | none | PLANNED |
| M5 | Test Suite Authoring & CI Registration | 22 unit test suites in tests/test-*.py registered in mios.toml | M1, M2, M3, M4 | PLANNED |
| M6 | Task Registries Parity, Projections & CI Gates | TASKS.md, AGY-TASKS.md, sync-generated.sh, 7 CI gates | M5 | PLANNED |
| M7 | Gate Review, Forensic Audit & Git Delivery | Independent Reviewers, Challenger, Forensic Auditor, Git Commit | M6 | PLANNED |

## Interface Contracts
### General Module Standards
- Every engine is a Python 3 script with `#!/usr/bin/env python3` shebang, executable permissions, and strict standard library usage.
- Supports standard CLI arguments: `--json`, `--mock`, `--dry-run`, `--verbose`, `--help`.
- Exit codes: `0` for success, non-zero for failure.
- Returns structured JSON to stdout when `--json` is specified.
- Mock mode (`--mock`) executes full logic paths deterministically without accessing real hardware devices, network endpoints, or external daemons.

### M1: Security & Schema Validation
- `fido2_enroll.py`: `--device <path>`, `--pin`, `--touch`, `--recovery-key`, `--status`, `--json`, `--mock`.
- `unattend_validate.py`: `--input <path>`, `--schema <path>`, `--strict`, `--json`, `--mock`.

### M2 & M3: System UX & Theming
- Integrates with `usr/lib/mios/mios_toml.py` to retrieve `colors()`, `get("theme.*")`, `get("identity.*")`.
- `living_wallpaper.py`: `--mode <mode>`, `--shader <path>`, `--fps <num>`, `--json`, `--mock`.
- `theme_sync.py`: `--target <gtk|windows|all>`, `--out <path>`, `--apply`, `--json`, `--mock`.
- `status_bar.py`: `--stream`, `--interval <sec>`, `--json`, `--mock`.
- `tmux_theme.py`: `--out <path>`, `--json`, `--mock`.
- `fastfetch_gen.py`: `--out <path>`, `--json`, `--mock`.
- `wm_config_gen.py`: `--target <hyprland|sway|all>`, `--out <dir>`, `--json`, `--mock`.
- `audio_feedback.py`: `--event <event_name>`, `--volume <num>`, `--json`, `--mock`.
- `notification_daemon.py`: `--listen`, `--post <msg>`, `--level <info|warn|error>`, `--json`, `--mock`.
- `gnome_extension.py`: `--install`, `--status`, `--json`, `--mock`.
- `editor_config_gen.py`: `--target <vscode|cursor|all>`, `--out <dir>`, `--endpoint <url>`, `--json`, `--mock`.
- `btop_theme.py`: `--out <path>`, `--json`, `--mock`.
- `font_scaler.py`: `--dpi <num>`, `--scale <factor>`, `--apply`, `--json`, `--mock`.
- `biometric_lock.py`: `--lock`, `--unlock`, `--fido2`, `--fingerprint`, `--json`, `--mock`.
- `focus_audio.py`: `--mode <noise|binaural|drone>`, `--duration <sec>`, `--json`, `--mock`.
- `clipboard_sync.py`: `--sync`, `--redact`, `--direction <host-to-vm|vm-to-host>`, `--json`, `--mock`.

### M4: Diff Snapshot & Image Bake Lifecycle
- `diff_snapshot.py`: `--reason <shutdown|manual>`, `--out-dir <path>`, `--json`, `--mock`. Output: `/var/lib/mios/snapshots/boot-diffs/<timestamp-boot-id>.json`.
- `diff_accrual.py`: `--snapshot-dir <path>`, `--out <path>`, `--classify`, `--json`, `--mock`. Output: `/var/run/mios/accrued-diffs.json`.
- `diff_auditor.py`: `--input <path>`, `--approve <ids>`, `--reject <ids>`, `--stage`, `--json`, `--mock`. Output: `/var/run/mios/staged-bake-diffs.json`.
- `image_bake.py`: `--staged-diffs <path>`, `--tag <name>`, `--switch`, `--json`, `--mock`.
- `greenboot_gate.py`: `--check`, `--rollback-on-failure`, `--quarantine-dir <path>`, `--json`, `--mock`.

## Code Layout
- `usr/libexec/mios/sec/`: Security engines (`fido2_enroll.py`, `greenboot_gate.py`)
- `usr/libexec/mios/win/`: Windows tooling engines (`unattend_validate.py`)
- `usr/libexec/mios/ux/`: System UX, theming, window management, audio, editors, and diff auditor
- `usr/libexec/mios/deploy/`: Image deployment, snapshot, accrual, and image bake lifecycle engines
- `tests/test-*.py`: Dedicated unit test suites for each engine
- `usr/share/mios/mios.toml`: SSOT containing `[ci.tiers] unit` suite list, `[colors]`, `[theme]`
- `TASKS.md` & `AGY-TASKS.md`: Task tracking registries
