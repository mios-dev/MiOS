<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "README.md"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
---
# MiOS Toolkit Scripts

This directory contains **standalone out-of-image tooling** that runs
*on a booted MiOS host* (or any Fedora/RHEL-family host, in
most cases). These scripts are **not part of the image build** — the
image-build scripts live in [`../automation/`](../automation/) and the
overlays live in [`../`](../).

Use these tools when you need to configure VFIO passthrough, isolate
CPUs for VM pinning, profile a host before deploying MiOS to it, or
troubleshoot Secure Boot / OVMF enrollment for Windows VMs.

> **All rules from [`../INDEX.md`](../INDEX.md) §3.2 (Bash) apply
> here too.** No `((VAR++))` under `set -euo pipefail`, quote every
> expansion, prefer `compgen -G` / `find -exec` / `read -ra`, etc.

---

## VFIO toolkit

For passing GPUs and USB controllers into KVM/QEMU VMs. See
[`../specs/knowledge/guides/vfio-toolkit-readme.md`](../specs/knowledge/guides/vfio-toolkit-readme.md)
for full documentation.

| Script | Purpose |
|--------|---------|
| `rtx4090-vfio-configurator.sh` | Opinionated RTX 4090 VFIO setup (MiOS's primary GPU) |
| `universal-vfio-configurator.sh` | Generic VFIO configurator — any GPU, any USB controller |
| `vfio-verify.sh` | Verify VFIO binding, IOMMU groups, host lockout |
| `iommu-visualizer.sh` | Pretty-print IOMMU group membership |

---

## CPU isolation & pinning

For pinning VM vCPUs to host physical cores, isolating cores from the
Linux scheduler, and configuring NUMA locality. See the full guide
at [`../specs/knowledge/guides/cpu-isolation-guide.md`](../specs/knowledge/guides/cpu-isolation-guide.md).

| Script | Purpose |
|--------|---------|
| `universal-cpu-isolator.sh` | Generic CPU isolation — grub kargs, systemd cpuset, irqbalance tuning |
| `vm-cpu-pin-manager.sh` | Pin specific VM vCPUs to host physical cores |
| `configure-xbox-cpu.sh` | Xbox-VM-specific CPU configuration (8 dedicated cores) |

---

## Host profiling & assessment

Run these **before** installing MiOS on a new host to get a
full picture of the hardware, virtualization capabilities, and
deployment readiness.

| Script | Purpose |
|--------|---------|
| `system-profiler.sh` | CPU / memory / GPU / storage inventory |
| `system-assess.sh` | Full system assessment — virtualization, IOMMU, Secure Boot, TPM |
| `mios-build-assess.sh` | MiOS-specific readiness check |
| `run-all-profilers.sh` | Chain every profiler, produce consolidated report |
| `profiler-menu.sh` | Interactive menu wrapping the profilers |
| `profile-compare.sh` | Diff two profiler outputs (e.g. before/after a change) |
| `quick-summary.sh` | One-screen system summary |

---

## Windows VM / Secure Boot helpers

For Xbox-cloud-style Windows VMs with Secure Boot + TPM. The XML files
are libvirt domain templates; the shell scripts patch OVMF firmware
and enrollment.

| File | Purpose |
|------|---------|
| `apply-final-config.sh` | Apply the final known-good config to a Windows VM |
| `check-ovmf-enrollment.sh` | Check OVMF NVRAM for correct Vendor-signed keys |
| `fix-ovmf-enrollment.sh` | Fix broken OVMF enrollment |
| `find-ovmf-firmware.sh` | Locate the right OVMF firmware on the host |
| `get-secureboot-ovmf.sh` | Download a SB-compatible OVMF build |
| `fix-secureboot-now.sh` | Emergency Secure Boot fixer |
| `fix-xbox-secureboot.sh` | Xbox-VM-specific Secure Boot fix |
| `Xbox-AutoEnroll.xml` | libvirt domain with PK/KEK/db/dbx auto-enrollment |
| `Xbox-Final-NoAutoSelect.xml` | libvirt domain — final config, no boot menu auto-select |
| `win11-secureboot-template.xml` | Generic Windows 11 + Secure Boot libvirt template |

---

## Theming

| Script | Purpose |
|--------|---------|
| `bibata-suite.sh` | Install and configure the Bibata cursor theme across GNOME/GTK/Qt |

---

## Legacy mega-scripts

Kept for reference. New work should **not** extend these — they
predate the current `automation/NN-*.sh` modular design.

| Script | Purpose |
|--------|---------|
| `mios-full.sh` | Standalone one-shot MiOS provisioner (188 KB — everything in one file, pre-refactor) |
| `mios-build.sh` | Earlier Linux-side orchestrator (superseded by `Justfile` + `../mios-build-local.ps1`) |

If you find yourself wanting to modify either of these, stop and work
on the modular replacement in `../automation/` instead.

---

## How these scripts interact with the bootc image

- The **image build** (Containerfile + `../automation/`) produces the OS.
- These **toolkit scripts** run on a host that's already booted —
  either a MiOS host, or a Fedora/RHEL host preparing to
  become one.
- Nothing in this directory is copied into the image by default.
- If you want one of these tools inside the image (e.g. `vfio-verify.sh`
  pre-installed for diagnostics), copy it into
  `../usr/local/bin/` and reference it from the relevant
  `../automation/NN-*.sh` or `../systemd/` unit. Don't symlink from here.

---

*See [`../INDEX.md`](../INDEX.md) §8 for what System Code / other AI
agents should not do in this directory (summary: don't modernize
working scripts unprompted, don't rewrite bash into other languages).*

---
### 📚 Bootc Ecosystem & Resources
- **Core:** [containers/bootc](https://github.com/containers/bootc) | [bootc-image-builder](https://github.com/osautomation/bootc-image-builder) | [bootc.pages.dev](https://bootc.pages.dev/)
- **Upstream:** [Fedora Bootc](https://github.com/fedora-cloud/fedora-bootc) | [CentOS Bootc](https://gitlab.com/CentOS/bootc) | [ublue-os/main](https://github.com/ublue-os/main)
- **Tools:** [uupd](https://github.com/ublue-os/uupd) | [rechunk](https://github.com/hhd-dev/rechunk) | [cosign](https://github.com/sigstore/cosign)
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Sole Proprietor:** MiOS Project
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
