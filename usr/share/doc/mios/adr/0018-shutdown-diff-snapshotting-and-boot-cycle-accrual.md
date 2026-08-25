<!-- AI-hint: Captures pre-poweroff diffs, accrues them across boot cycles, provides interactive HITL review, and rolls approved diffs into new immutable OCI layers. -->
<!-- AI-related: usr/libexec/mios/mios-diff-snapshot, usr/libexec/mios/mios-diff-accrue, usr/libexec/mios/mios-diff-audit, usr/libexec/mios/mios-diff-bake, usr/share/mios/mios.toml [build.bake], [security.diff_policy], /etc/greenboot/check/required.d/60-mios-diff-bake-verify.sh -->
---
adr: 0018
title: "Shutdown diff snapshotting, boot-cycle diff accrual, and HITL image roll-in pipeline"
status: accepted
date: 2026-08-25
deciders: [operator, ai-pair]
tags: [diff, snapshot, shutdown, boot-cycle, hitl, bake, greenboot, self-replication]
laws: [1, 3, 7, 8, 12]
ssot_keys: [build.bake, security.diff_policy, build.roll_in]
related_ws: [WS-DIFFCYCLE, WS-BUILD, WS-SEC]
supersedes: []
superseded_by: []
---

# ADR-0018: Shutdown diff snapshotting, boot-cycle diff accrual, and HITL image roll-in pipeline

## Status

**Accepted.** Settles the continuous feedback loop from live mutable filesystem changes back into immutable bootc OCI image layers across system power cycles.

## Context

MiOS is an immutable operating system with a self-developing premise: `.git ≡ /`. On a running host, human operators and autonomous agents make configuration tweaks in `/etc`, tune `mios.toml`, install user dotfiles, synthesize new skills in `/var/lib/mios/ai/skills/`, and modify tool scripts.

On a standard immutable OS, live mutable overrides in `/etc` and `/var` drift indefinitely from the baked image layer. If the host pulls an upstream OCI update or is re-imaged, un-baked local modifications risk being orphaned or causing configuration merge conflicts.

Furthermore, an autonomous operating system must capture all modifications before a shutdown or reboot event, present a clean summary of changes accrued across boot cycles, and allow the operator to audit and bake verified modifications permanently into the next OCI image deployment.

## Decision

### 1. Pre-Poweroff Diff Snapshotting Hook
A dedicated systemd shutdown unit (`usr/lib/systemd/system-shutdown/mios-diff-snapshot`) is registered to execute before unmounting filesystems during shutdown, reboot, or kexec events:
* Inspects `/` (`.git ≡ /`) for modified tracked files and untracked additions.
* Dumps a structured JSON snapshot containing timestamps, modified file paths, git diff patches, and calling user IDs to `/var/lib/mios/snapshots/boot-diffs/<timestamp-boot-id>.json`.
* Executes within a strict 3-second timeout to prevent delaying host shutdown.

### 2. Boot-Cycle Diff Accrual & Risk Classification
On system startup, `usr/libexec/mios/mios-diff-accrue` parses historical diff snapshots recorded since the last image bake:
* **Safe / Additive Tier**: User dotfiles, Wi-Fi profiles, synthesized skills, color palette adjustments, and documentation updates.
* **High-Risk / Consequential Tier**: Kernel parameters, PAM authentication configs, root binaries, firewall rules, and container runtime settings.
* Outputs a structured audit ledger to `/var/run/mios/accrued-diffs.json`.

### 3. Interactive Human-In-The-Loop (HITL) Review
The operator is notified of accrued diffs via Quickshell (`DiffReview.qml`) or terminal CLI (`mios diff audit`):
* Visual side-by-side diff viewer with per-change checkboxes.
* Operator approves or rejects proposed additions.
* Non-blocking: un-reviewed diffs remain in the live mutable layer without interrupting normal interactive sessions.

### 4. Autonomous Background Image Roll-In
When diffs are approved:
* `usr/libexec/mios/mios-diff-bake` commits approved changes to the local repository root.
* Triggers a low-priority background build inside `podman-MiOS-DEV`.
* The newly synthesized image layer is staged via `bootc switch --staged` to become the active boot target on the subsequent power cycle.

### 5. Greenboot Post-Bake Health Ratchet
On the next boot:
* Greenboot health check `/etc/greenboot/check/required.d/60-mios-diff-bake-verify.sh` validates that all services initialize cleanly.
* If any service panics or fails health checks, Greenboot automatically initiates an atomic rollback to the previous deployment and marks the offending diff as quarantined in the audit ledger.

## Consequences

- Live system modifications are never lost across power cycles and are deterministically promoted into immutable image layers.
- The operator maintains explicit human-in-the-loop governance over system state transitions.
- Failed automated bakes roll back autonomously without bricking the host.
