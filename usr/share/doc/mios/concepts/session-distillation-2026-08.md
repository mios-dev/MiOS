<!-- AI-hint: Master architectural distillation and full-spectrum systems synthesis for MiOS. -->
<!-- AI-related: ROADMAP.md, TASKS.md, AGY-TASKS.md, ADR.md, usr/share/doc/mios/adr/, usr/share/mios/mios.toml -->
# Master Session Architectural Distillation & Full-Spectrum Systems Synthesis

## 1. Executive Summary

This document synthesizes the complete architectural consensus, technical specifications, and system invariants established during the comprehensive MiOS system design and roadmap expansion sessions. 

MiOS ("My OS" / "MyOS") is built on a singular premise: an **immutable, bootc/OCI-shaped Fedora workstation** that is simultaneously a **local, self-replicating, agentic AI operating system** where `.git ≡ /`.

---

## 2. Four Load-Bearing Invariants

To eliminate common architectural drift, the following four invariants are enforced across all documentation and implementations:
1. **`/var` Persists by Default**: On bootc/ostree systems, `/var` is persistent storage (not a volatile tmpfs). Database state (`pgvector`), VM disks, large model weights, and snapshots persist here across boots.
2. **Unified Kernel Image (UKI) vs MOK Separation**: Pre-boot security is governed by a signed UKI (`shim -> systemd-boot -> UKI` with immutable baked kargs, PCR 7). Out-of-tree runtime driver modules (NVIDIA akmods) are signed at build time by a local Machine Owner Key (MOK) enrolled in hardware NVRAM (PCR 14).
3. **Graphics Virtualization (Venus vs CUDA)**: The `venus` VirtIO protocol is strictly a graphics/Vulkan transport. CUDA execution inside a guest virtual machine mandates whole-device discrete GPU passthrough (`vfio-pci`).
4. **GPU Fractioning Limit**: Mediated vGPU fractioning (`mdevctl`/SR-IOV) requires a physical host-side driver. On a driver-free host, whole-device passthrough via `vfio-pci` is the sole supported model; vGPU fractioning requires an explicit opt-in.

---

## 3. Core Architectural Subsystems Settled

### A. Shutdown Diff Snapshotting & Boot-Cycle Accrual (`WS-DIFFCYCLE` / ADR-0018)
* **Pre-Poweroff Capture**: `usr/lib/systemd/system-shutdown/mios-diff-snapshot` records live git diffs and `/etc` changes before reboot/shutdown into `/var/lib/mios/snapshots/boot-diffs/`.
* **Startup Classification**: `usr/libexec/mios/mios-diff-accrue` categorizes changes into Safe vs High-Risk tiers.
* **Interactive HITL Review**: Quickshell UI (`DiffReview.qml`) and CLI (`mios diff audit`) let operators review and approve diffs.
* **Autonomous Bake & Rollback**: Approved changes are committed to `.git` and synthesized into a new OCI layer via `podman-MiOS-DEV`. Greenboot post-bake health checks guarantee automated atomic rollback if regressions occur.

### B. Preemptive Priority Scheduling & DCI Deliberation (`WS-SCHED` / `WS-ORCH` / ADR-0019)
* **Token-Boundary Preemption**: High-priority interactive turns preempt lower-priority background tasks via `_CHAT_CANCEL`. Background KV slots are serialized to `/var/lib/mios/llamacpp/slots/`, freeing GPU VRAM immediately.
* **Consequentiality-Gated DCI**: 4-agent structured debate (Framer, Explorer, Challenger, Integrator) activates on high-consequence mutations (security, partitioning, kernel args); read queries execute via direct low-latency single turns.
* **Manifest-Guided Retrieval & LOO Scoring**: Progressive-disclosure retrieval paired with Leave-One-Out (LOO) marginal contribution evaluation.

### C. Edge Micro-Mesh `mios-node` & Rust Native Subsystem (`WS-NODE` / `WS-LANG` / ADR-0020)
* **16-Byte Binary Wire Framing**: Ultra-low overhead binary protocol with Ed25519 ChaCha20-Poly1305 encryption.
* **Dual-Tier Sandboxing**: Tier-1 fuel-bounded Wasm (`wasmtime`) for sensor/telemetry tasks; Tier-2 rootless Podman containers for complex tool execution.
* **Hierarchical Work-Stealing**: Localhost ($<500	ext{ms}$) -> LAN Peer ($<5	ext{ms}$) -> WAN Tailscale Coordinator.
* **Native Rust Stack**: Compiled `miosd` daemon, `mios-check` validator, `mios` CLI dispatcher, and `mios-wallpaperd` living wallpaper renderer.

### D. Storage, Database Durability & V5 Authority Inversion (`WS-DURA` / `WS-STRG`)
* **SSOT Authority Inversion (V5)**: PostgreSQL `config_kv` is the live runtime authority. `materialize-config-toml.py` writes changes back to disk with atomic rename.
* **Disaster Recovery**: Pre-upgrade automated `zstd` database dumps (`mios-backup-pgvector.timer`) and strictly additive schema migrations.
* **CephFS Integration**: Multi-tenant directory subvolume quotas and RADOS S3 object storage for model weights.

### E. Hardware Virtualization, VFIO & Looking Glass B6 (`WS-VFIO`)
* **Dynamic GPU Switching**: Unbind display manager and bind discrete GPU to `vfio-pci` without host reboot.
* **Looking Glass B6**: Zero-latency inter-VM frame streaming via `/dev/kvmfr0` IVSHMEM with SPICE direct socket input capture.
* **Audio & Storage**: Sub-5ms PipeWire JACK scream audio bridge and VirtIO-FS shared directory mounts.

### F. Dotfiles & Live Multi-Surface Theme Engine (`WS-DOTFILES` / ADR-0010)
* **Unified Projection**: `mios.toml` projects themes and configurations to Linux (GTK CSS, Hyprland, Sway, tmux, btop) and Windows (Terminal, Registry, WebView2).
* **Live IPC Synchronization**: Portal updates send `SIGHUP` to running daemons and WebGL shader uniform updates to `mios-wallpaperd` for instant visual transitions.

### G. OpenAI API Standards & MCP Tool Gateway (Law 2 / Law 5 / ADR-0006)
* **Strict OpenAI Contract**: Every tool, model lane, and skill is exposed via standard OpenAI `/v1/chat/completions` and `/v1/responses` function-calling interfaces through `agent-pipe`.
* **Zero Vendor Lock-in**: No proprietary protocols or vendor-cloud dependencies.

---

## 4. Workstream & Task Statistics Matrix

* **Total Active Tasks**: 449 tasks in `TASKS.md` (211 open, 238 closed/validated).
* **AGY Schema-Compliant Tasks**: 426 tasks in `AGY-TASKS.md` with full 8-field verification schema.
* **Total ADRs**: 20 Architecture Decision Records (17 accepted, 3 proposed).
* **CI Validation Gates**: 100% green across status parity, schema completeness, AGY task IDs, roadmap index, and CI test suites.
