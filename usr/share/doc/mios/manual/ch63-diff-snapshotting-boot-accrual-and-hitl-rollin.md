<!-- AI-hint: Chapter 63: Diff Snapshotting, Boot-Cycle Accrual & HITL Image Roll-in Pipeline. -->
# <a name="63_diff_snapshotting_boot_accrual_and_hitl_rollin"></a>Chapter 63: Diff Snapshotting, Boot-Cycle Accrual & HITL Image Roll-in Pipeline

> Part V: Security & Governance of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#63_diff_snapshotting_boot_accrual_and_hitl_rollin`

#### Overview

MiOS enforces an immutable operating system model where `.git ≡ /`. On a running workstation, human operators and autonomous agents continuously tune configurations, synthesize skills in `/var/lib/mios/ai/skills/`, and modify tool scripts.

To bridge live mutable modifications back into immutable OCI image layers across system power cycles, MiOS implements the **Diff Snapshotting, Boot-Cycle Accrual & HITL Image Roll-in Pipeline** (governed by ADR-0018 and `WS-DIFFCYCLE`).

#### <a name="63_pre_poweroff_snapshot"></a>63.1 Pre-Poweroff Snapshotting Hook

During system shutdown, reboot, or kexec events, `usr/lib/systemd/system-shutdown/mios-diff-snapshot` intercepts the power-down sequence:
1. Performs a fast git diff against the system root (`.git ≡ /`).
2. Scans `/etc/mios/` and `/usr/share/mios/` for uncommitted file modifications.
3. Dumps a structured JSON snapshot containing timestamps, diff patches, and calling user IDs to `/var/lib/mios/snapshots/boot-diffs/<timestamp-boot-id>.json`.
4. Executes with a strict 3-second timeout to avoid delaying shutdown.

#### <a name="63_startup_diff_accrual"></a>63.2 Startup Diff Accrual & Risk Classification

On subsequent boot cycles, `usr/libexec/mios/mios-diff-accrue` parses historical diff snapshots recorded since the last image bake:
* **Safe / Additive Tier**: Dotfiles, Wi-Fi network keyfiles, synthesized skills, theme color adjustments, and documentation updates.
* **High-Risk / Consequential Tier**: Kernel parameters (`kargs.d`), PAM authentication policies, root binaries, firewall rules, and container runtime settings.

The classification ledger is exported to `/var/run/mios/accrued-diffs.json` for consumption by desktop and CLI interfaces.

#### <a name="63_interactive_hitl_review"></a>63.3 Interactive Human-In-The-Loop Review

The operator audits accrued modifications through:
* **Desktop GUI**: Quickshell drawer (`usr/share/mios/shell/components/DiffReview.qml`) presenting side-by-side file diffs with checkboxes.
* **Terminal CLI**: `mios diff audit` command allowing interactive patch staging.

Unreviewed diffs remain active in the live mutable layer without blocking login or user workflows.

#### <a name="63_autonomous_bake_and_greenboot"></a>63.4 Autonomous Image Bake & Greenboot Ratchet

When diffs are approved:
1. `usr/libexec/mios/mios-diff-bake` commits approved changes to the local repository root.
2. Triggers a low-priority background build inside `podman-MiOS-DEV`.
3. The resulting OCI image layer is staged via `bootc switch --staged`.
4. On the next boot, `/etc/greenboot/check/required.d/60-mios-diff-bake-verify.sh` verifies service health. If any regression is detected, Greenboot triggers an immediate atomic rollback to the prior deployment and quarantines the offending patch.
