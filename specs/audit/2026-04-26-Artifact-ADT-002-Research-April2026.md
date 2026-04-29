<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "audit"
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
> **Source Reference:** MiOS-Core-v0.1.1
---

# MiOS Live Research Notes — April 2026

> **LIVE DOCUMENT** — Updated synchronously by parallel research agents.
> Each section is owned by a specific research thread. Findings are appended
> as discovered. Cross-reference between sections freely.
>
> Last sweep started: 2026-04-19
> Last iterative pass: 2026-04-25 (scheduled-research-daily)

---

## INDEX

1. [bootc Upstream (containers/bootc)](#1-bootc-upstream)
2. [bootc-image-builder (BIB)](#2-bib)
3. [Universal Blue / ucore-hci](#3-universal-blue)
4. [Fedora bootc / FCOS / OCI Transition](#4-fedora-bootc-fcos)
5. [composefs / OSTree](#5-composefs-ostree)
6. [Podman Quadlet / systemd Integration](#6-quadlet-systemd)
7. [WSL2 / systemd Integration](#7-wsl2-systemd)
8. [Sigstore / cosign / Supply-Chain](#8-sigstore-cosign)
9. [kargs.d Spec & bootc Lint Rules](#9-kargs-lint)
10. [NVIDIA Container Toolkit / CDI](#10-nvidia-cdi)
11. [Renovate / Digest Pinning](#11-renovate)
12. [Security / SELinux / CrowdSec](#12-security)
13. [Desktop Stack — GNOME 50.x / Wayland](#13-desktop-stack--gnome-50x--wayland) (added 2026-04-25)
14. [Waydroid / Android Emulation](#14-waydroid--android-emulation) (added 2026-04-25)

---

## 1. bootc Upstream

*Research thread: containers/bootc GitHub releases, issues, changelog, spec changes*

<!-- FINDINGS BEGIN -->
### Repo / project status

- **Repo moved:** `containers/bootc` → **`bootc-dev/bootc`** (github.com/bootc-dev/bootc). All old `containers/bootc` URLs redirect. Update any hardcoded links in docs.
- **CNCF Sandbox:** bootc accepted January 21, 2025 — largest single CNCF intake batch (13 projects). Stable API/CLI guaranteed going forward.
- **Current stable release:** v0.1.1 (April 14, 2025). v1.15.x line is the current series as of research date.
- **Website:** https://bootc.dev/bootc/ (redirects from bootc-dev.github.io/bootc/)

### Release highlights (v1.9 → v1.15) (updated 2026-04-26: live research verified)

| Version | Date | Key additions |
|---------|------|---------------|
| v1.9.0 | 2024 | Major composefs/image sealing merge. |
| v1.11.0 | 2025 | kargs.d support; experimental factory reset. |
| v1.12.0 | 2025 | `upgrade --download-only` flag; `container inspect` verb. |
| v1.14.0 | 2026 | Pre-flight disk space checks; `/usr` overlay status. |
| v1.15.1 | 2026 | **Current stable.** Intel VROC fix; `--karg-delete`. |

**Workarounds integrated (April 2026):**
- **NVIDIA 595+ Stability:** Injected `NVreg_UseKernelSuspendNotifiers=1` for open modules to resolveAda/Blackwell suspend cycles.
- **WSL v0.1.1 User Session:** Gated `systemd-networkd-wait-online.service` on `!wsl` to prevent login timeouts.
- **WSL 0.0.0.0 Permissions:** Enforced 0755 on `wsl-user-generator` via tmpfiles.d to fix security regression breaking user sessions.

**bootc v0.1.1 notable:** `bootc container lint` expanded — now checks for missing `tmpfiles.d` entries and warns. This is actionable for MiOS: ensure every `/var/lib/<service>` directory that a service needs is declared in `tmpfiles.d/`.

### Filesystem semantics (authoritative)

| Path | Semantics | Notes |
|------|-----------|-------|
| `/usr` | **Immutable** — composefs-covered, read-only | All OS content should live here |
| `/etc` | **3-way merge** on upgrades (base↔local↔new) | Set `etc.transient = true` for fully ephemeral |
| `/var` | **Persistent state** — excluded from updates | Content added to image NOT propagated on update; use `tmpfiles.d` to pre-create dirs |
| `/run` | API filesystem — **do not ship content here** | |
| `/usr/etc` | Internal bootc implementation detail | **Never place files here explicitly** — lint rejects it |
| `/usr/local` | Mutable by default in bootc | Derives ship mutable /usr/local; "final" images may symlink to `/var/usrlocal` |

### bootc container lint — full check list (as of v1.15.x)

1. `/usr/lib/bootc/kargs.d/*.toml` — syntax validation (flat `kargs = [...]` only; no section headers)
2. Multiple kernels in `/usr/lib/modules` — only one kernel per image supported
3. Files explicitly placed in `/usr/etc` — forbidden path
4. Missing `tmpfiles.d` entries for `/var` directories (warning, not error, as of v0.1.1)
5. Non-UTF-8 filenames anywhere in the image
6. Stale logfiles left in image (warns to clean these in final stage)
7. kargs.d `match-architectures` value validation (must be Rust std arch names)

**MiOS action:** `bootc container lint` is already the last `RUN` in the Containerfile — correct. Ensure `99-cleanup.sh` runs before it and removes all log files.

### Mutable filesystem options

- **`[root] transient = true`** — writable root (all dirs) until reboot; `/var` symlinks provide persistence
- **`[root] transient-ro = true`** — privileged processes can remount overlay upper dir as writable in isolated namespaces; regular processes see read-only
- **State overlays** (`ostree-state-overlay@opt.service`) — writable overlay on specific paths; changes persist across reboots but are overridden by image content on update

### `--karg-delete` (v0.1.1+)

New `bootc kargs edit --karg-delete <arg>` command allows removing a kernel argument from the local bootloader config without an image rebuild. Useful for ad-hoc debugging. Does NOT modify kargs.d — local only, lost on next `bootc upgrade`.

### Composefs verity requirements (hard constraint)

- `[composefs] enabled = verity` requires the **target filesystem** to support `fsverity`
- **Supported:** ext4 (kernel ≥ 5.4), btrfs (kernel ≥ 5.15)
- **NOT supported:** XFS — bootc errors at install time if target is XFS with verity mode
- MiOS BIB config uses `ROOTFS=ext4` — correct for verity mode

### greenboot-rs (health check / rollback)

- greenboot Rust rewrite (`greenboot-rs`) approved for Fedora 43 (September 2025)
- Shell-based greenboot deprecated in favor of greenboot-rs v0.1.1+
- Functions: runs health check scripts on every boot; reboots if required checks fail; rolls back to previous deployment after N failed reboots
- Check scripts: drop scripts into `/etc/greenboot/check/required.d/` (must succeed) or `/etc/greenboot/check/wanted.d/` (advisory only)
- **MiOS-role consolidation (April 2026):** Successfully merged the asynchronous logic into the extensionless `role-apply` engine. The system now handles initialization, hardware detection (Blackwell), and role application in a single non-blocking pass. Redundant `role-apply.sh` removed. Project baseline promoted to v0.1.1.

### bootc upgrade / switch / rollback / factory-reset

| Command | Effect |
|---------|--------|
| `bootc upgrade` | Pull newer image from registry; stage for next boot (A/B style) |
| `bootc upgrade --download-only` | Pull and stage but do NOT apply on next reboot; explicit apply required |
| `bootc switch ghcr.io/other/image:tag` | Change tracked image (same as upgrade semantically); preserves /etc and /var |
| `bootc rollback` | Swap bootloader ordering to previous deployment; discard any staged upgrade |
| `bootc install reset` | Non-destructive factory reset: new stateroot (`state-<year>-<serial>`); fresh deploy from current image; old state preserved on disk |

**Rollback caveat:** `bootc rollback` does NOT work on composefs-native deployments as of v1.15.x. Use greenboot-rs for automated rollback (it falls back to previous OSTree deployment). Manual rollback requires booting to GRUB menu and selecting previous entry.

**Soft reboot (RHEL 10 / Fedora 44+ feature):** New `bootc soft-reboot` (or `systemctl soft-reboot`) allows applying an OS image update without a full hardware reboot — uses kernel's kexec mechanism. Significantly reduces downtime for OS updates on servers. MiOS-2 on Fedora stable (F42/F43) does not yet have this feature; monitor for inclusion in F44+.

### Physically bound vs logically bound images

| Type | Where content lives | Pre-fetched by bootc? | Bandwidth on update |
|------|--------------------|-----------------------|---------------------|
| **Physically bound** | Inside the bootc OCI image layers | N/A (already in image) | Always downloaded with OS image |
| **Logically bound** | Separate OCI image; declared in `/usr/lib/bootc/bound-images.d/` | ✅ Yes — on `bootc upgrade`/`install` | Only downloaded when app image changes |

**Logically bound path:** `/usr/lib/bootc/bound-images.d/` — symlinks to Quadlet `.image` or `.container` files in `/usr/share/containers/systemd/`. bootc pre-fetches the referenced images into `/usr/lib/bootc/storage`.

**MiOS candidates for logically bound:**
- `crowdsec-dashboard` (metabase container)  
- `mios-guacamole` + `mios-guacd` containers
- Future: monitoring (Prometheus node_exporter, Grafana)

### 2026-04-20 update — composefs-native backend still not rollback-capable

Per bootc issue #1190 (composefs-native backend umbrella), the composefs-native backend is **still under active development** and has not achieved feature parity with the ostree backend. Work in progress (as of Feb–Apr 2026):

- Garbage collection fixes (@Johan-Liebert1, @cgwalters)
- Making updates/switches idempotent
- `/etc` merge implementation
- initramfs integration for composefs-native-finalize
- Cross-distro CI (Fedora, openSUSE, RHEL 10)

Explicitly missing as of 2026-04:
- `bootc rollback` on composefs-native — still returns "This feature is not supported on composefs backend"
- `bootc upgrade --download-only` on composefs-native — not implemented (Red Hat Developers confirmed Feb 2026)
- `/etc` three-way merge on composefs-native — partial

**MiOS implication:** Stay on OSTree backend (not composefs-native) for MiOS-2 production. The `[composefs] enabled = verity` setting in `prepare-root.conf` is composefs-over-ostree, which IS rollback-capable via greenboot-rs falling back to previous ostree deployment. Do not confuse this with the experimental composefs-native *backend* — those are distinct.

### 2026-04-20 update — Konflux takes over bootc artifact builds in Fedora 44

Fedora 44 ChangeSet confirms: **Konflux becomes the build pipeline for bootc-based artifacts**, replacing the legacy pipeline. Fedora CoreOS builds also migrate to Konflux. This is upstream infrastructure, not a MiOS action item, but:

- `quay.io/fedora/fedora-bootc:rawhide` content will be Konflux-built starting with F44 (release target April 28, 2026)
- Digest pins in `image-versions.yml` may see more frequent churn during the transition window (April–June 2026)
- Renovate `minimumReleaseAge: "3 days"` for digest updates remains appropriate

No action required from MiOS.

### 2026-04-25 update — bootc v0.1.1 still latest; new install-time issues to watch

Confirmed via github.com/bootc-dev/bootc/releases (sweep on 2026-04-25): **v0.1.1 (April 14, 2026) remains the most recent tag**. v0.1.1 / v0.1.1 not cut yet. Open install-time issues filed against `main` (April 2026) that are relevant to MiOS BIB outputs:

| Issue | Title | MiOS impact |
|-------|-------|----------------|
| #2132 | `install to-disk` should create bigger ESP (~2 GiB) for composefs+UKI | Future composefs+UKI build path; current BIB ESP sizing already comfortable. **Watch when MiOS adopts UKI.** |
| #2131 | `install to-disk` should NOT create a BIOS partition for composefs+UKI | UEFI-only flag relevant once UKI lands. Currently inert. |
| #2130 | Leftover block devices after install (loopback) | May affect CI runners that retry BIB builds in same VM; mitigate by cleaning loop devices in `cleanup_after_build()` if it ever surfaces. |
| #2122 | Install configuration files NOT sourced when using `--src-imgref` | MiOS does not use `--src-imgref` in CI today; safe. |
| #2137 | `--download-only` flag for `bootc switch` | Feature request; would let MiOS pre-stage major version upgrades. Track for future feature. |
| #2119 | Path-trigger support for the composefs-native backend | Tracking-only; MiOS stays on ostree backend (see #1190 below). |
| #2112 | Container signature policy enforcement configuration | Aligns with MiOS `/etc/containers/policy.json` strategy; track for any required config-file changes. |

No build-breaking regressions identified for the current MiOS pipeline.

### 2026-04-25 update — composefs-native backend (#1190) status

Re-checked tracking issue. Still **open and not feature-complete**. No new resolution events in April 2026 beyond the prior 04-20 summary. **Rollback remains unsupported on composefs-native**, so the MiOS guidance ("stay on ostree backend; use composefs-over-ostree via `prepare-root.conf`") is unchanged. The bootcrew/ project (opensuse-bootc, arch-bootc, debian-bootc) has been consolidated into `bootcrew/mono`, indicating the cross-distro work is now centralized but still experimental.
<!-- FINDINGS END -->

---

## 2. BIB (bootc-image-builder)

*Research thread: BIB releases, config schema changes, new artifact types, known bugs*

<!-- FINDINGS BEGIN -->
### Supported artifact types

| BIB `--type` value | Output | Notes |
|--------------------|--------|-------|
| `qcow2` | `output/qcow2/disk.qcow2` | Default; QEMU/KVM |
| `raw` | `output/image/disk.raw` | Bare metal, can dd to disk |
| `vhd` | `output/vpc/disk.vhd` | Hyper-V (VHD); use `qemu-img convert` for VHDX |
| `vmdk` | `output/vmdk/disk.vmdk` | VMware |
| `anaconda-iso` | `output/bootiso/install.iso` | Bootable installer ISO |
| `ami` | `output/image/disk.raw` (+ AMI manifest) | AWS EC2 |
| `gce` | `output/image/disk.tar.gz` | Cloud Cloud |
| `pxe-tar-xz` | tarball | PXE netboot |
| `bootc-installer` | varies | For `bootc install` workflows |

**WSL2 tarball:** Not natively a BIB type. Export a running MiOS container with `podman export` or use `wsl --import`. A native `wsl` output type is on the BIB roadmap but not yet landed as of April 2026.

### CLI flags

```
--type <format>          Artifact type (repeatable for multi-format builds)
--rootfs <fs>            Target rootfs: ext4 (default), xfs, btrfs
--output <dir>           Output directory (default: current dir)
--chown <uid:gid>        Change output dir ownership (use in CI to avoid root-owned files)
--use-librepo            Use librepo for RPM downloads (faster, more robust, recommended)
--target-arch <arch>     Cross-arch build (experimental; requires QEMU binfmt_misc)
--progress <mode>        verbose | term | debug | auto
--log-level <level>      debug | info | warn | error
--in-vm                  Rootless build mode using KVM VM (required for rootless)
```

**MiOS CI relevance:** The `build-artifacts.yml` correctly uses `--use-librepo=True` and `--chown "$(id -u):$(id -g)"`. The `--type` is set per matrix leg.

### config.toml schema (customizations)

```toml
[customizations]
  [customizations.kernel]
  append = "mitigations=auto"          # Additional kargs on top of kargs.d

  [[customizations.user]]
  name = "admin"
  password = "$6$..."                   # Pre-hashed via openssl passwd -6
  key = "ssh-ed25519 AAAA..."
  groups = ["wheel", "sudo"]

  [[customizations.filesystem]]
  mountpoint = "/var"
  minsize = "20 GiB"

  [[customizations.filesystem]]
  mountpoint = "/boot"
  minsize = "1 GiB"

  [customizations.installer]
  # Anaconda ISO only:
  kickstart = { contents = "..." }      # Inline kickstart
  modules = { enabled = ["..."], disabled = ["..."] }  # Anaconda modules

  [customizations.iso]                  # anaconda-iso only
  volume_id = "MiOS"
  application_id = "MiOS Installer"
  publisher = "MiOS-DEV"
```

**Known limitations:**
- `btrfs` rootfs: cannot set custom `/var` subdirectory mountpoints at build time (BIB limitation, not bootc limitation)
- Not all Blueprint options from osbuild are supported in BIB — primarily the subset above
- `customizations.kernel.append` is additive on top of image's kargs.d — use kargs.d for image-level args; BIB config for install-time overrides

### rootfs selection guidance

| rootfs | composefs verity? | Notes |
|--------|------------------|-------|
| `ext4` | ✅ Yes | Recommended for MiOS; fsverity supported kernel ≥ 5.4 |
| `btrfs` | ✅ Yes | Alternative; fsverity supported kernel ≥ 5.15 |
| `xfs` | ❌ No | fsverity NOT supported; `composefs.enabled = verity` will error at install |

MiOS uses `ROOTFS=ext4` — correct for verity mode.

### Podman Desktop BootC extension

- v1.6 (January 2025): interactive build config creator, Linux VM support (experimental)
- Allows GUI-driven BIB builds from Podman Desktop without writing TOML manually
- Useful for MiOS's Windows host — can drive BIB builds through Podman Desktop UI

### Rootless builds

Rootless BIB (no `--privileged`) requires `--in-vm` flag which uses KVM to run the build in an ephemeral VM. This avoids privileged container requirements on shared CI runners. Requires KVM device access (`/dev/kvm`) on the runner.

### Known BIB issues / actionable items for MiOS

1. **`--use-librepo=True`** — note the capital `True` (Python-style boolean); lowercase `true` is silently ignored in some BIB versions. MiOS `build-artifacts.yml` already uses capital `True` — correct.
2. **VHDX**: BIB produces VHD; MiOS correctly post-converts with `qemu-img convert -f vpc -O vhdx -o subformat=dynamic`. This is the right pattern — BIB has no native VHDX output.
3. **Disk space on ubuntu-24.04 runners:** BIB builds consume 30-40 GB. MiOS correctly uses `jlumbroso/free-disk-space@main` to reclaim ~40 GB before the build step.
4. **BIB pulls base image from registry:** BIB re-pulls the image from GHCR inside the privileged container; that's why `sudo podman pull` before the BIB run step is needed (to pre-warm `/var/lib/containers/storage` which is bind-mounted in).

### 2026-04-20 update — BIB status

- **No WSL2 native artifact type yet.** osautomation/bootc-image-builder#172 (feature request: `wsl2`/`tar.gz` output for Windows users) remains open. MiOS's WSL delivery continues to rely on `podman export` + `wsl --import` — documented pattern is still correct.
- **FIPS-enabled RHEL bootc image builds** now documented (March 2026 Red Hat reference). Not applicable to MiOS (Fedora base), but confirms the BIB config schema is stable.
- **BIB via Konflux for Fedora:** Fedora 44 shifts FCOS + fedora-bootc builds to Konflux. BIB itself is unchanged — the publishing pipeline is what moved. MiOS's usage (`quay.io/centos-bootc/bootc-image-builder:latest`) is unaffected.
<!-- FINDINGS END -->

---

## 3. Universal Blue / ucore-hci

*Research thread: ucore-hci changelog, NVIDIA kmod updates, MOK changes, new features*

<!-- FINDINGS BEGIN -->
### Release/tag history

**Image tags and variant hierarchy (as of April 2026):**

ucore uses a layered image architecture with distinct variant tiers:

- `ghcr.io/ublue-os/ucore-minimal:<tag>` — Base layer; kernel + SELinux + cgroups v2 only
- `ghcr.io/ublue-os/ucore:<tag>` — Adds Cockpit, podman, ZFS, netavark, aardvark-dns, Tailscale, etc.
- `ghcr.io/ublue-os/ucore-hci:<tag>` — Adds KVM/QEMU/libvirt, Ceph, SR-IOV tooling — the primary base for MiOS-2

**Tag naming convention:** (updated 2026-04-20: added LTS stream + lts-nvidia-lts tags)

| Tag suffix | Meaning |
|---|---|
| `stable` | Pinned to current Fedora stable (Fedora 42 as of April 2026) |
| `stable-nvidia` | Stable + pre-signed NVIDIA **open** kernel modules (595.x series as of Apr 2026) |
| `stable-nvidia-lts` | **NEW** — Stable + NVIDIA **580 LTS** open kmods (for users who need the longer-support branch) |
| `stable-zfs` | Stable + ZFS kmod (OpenZFS, GPL-signed) |
| `stable-nvidia-zfs` | Stable + both NVIDIA + ZFS |
| `lts` | **NEW LTS stream** — Pinned to CentOS Stream 10 / long-support base |
| `lts-nvidia` | LTS base + NVIDIA open (latest) |
| `lts-nvidia-lts` | LTS base + NVIDIA 580 LTS |
| `testing` | Based on Fedora Rawhide / pre-release |
| `testing-nvidia` | Rawhide + NVIDIA open kmods |
| `testing-nvidia-lts` | **NEW** — Rawhide + NVIDIA 580 LTS |

**MiOS-2 uses `stable-nvidia`**, meaning it tracks Fedora stable (not Rawhide) with pre-signed NVIDIA open kernel modules. This is important: **MiOS-2's kernel is from Fedora stable, not Rawhide**. The MiOS-1 Rawhide variant is separate.

**Notable architectural changes (2025–2026):**

- The sister project `ublue-os/cayo` is now under active development as a bootc-native HCI successor to ucore-hci. cayo is fully composefs-native from the start. MiOS should monitor this for a potential MiOS-2 base migration in v3.x.
- ucore-hci moved from akmod-built NVIDIA proprietary modules to **NVIDIA open kernel modules (kmod-nvidia-open)** as default. Proprietary module path remains available via the `stable` tag with manual override.
- ucore adopted the `ublue-os/packages` COPR as the canonical source for `uupd`, `ublue-os-just`, `ublue-polkit-rules`, and `ublue-rebase-helper`.
- Rechunking migrated from `hhd-dev/rechunk` toward `bootc-base-imagectl rechunk --max-layers 67`.
- The `ujust` alias pattern is standardized: `just --justfile /usr/share/ublue-os/just/main.just --working-directory /`. MiOS should implement equivalent `mios-just` recipes.

**Known recent tag changes requiring attention:**
- Do NOT use `latest-nvidia` — this tag name does not exist in the ucore-hci registry; the correct stable production tag is `stable-nvidia`.
- The `stable` stream tracks Fedora 42 as of April 2026. When Fedora 43 becomes current stable (expected October 2026), digests will roll automatically under the same `stable` tag.
- Digest pinning is strongly recommended: `stable-nvidia` is a mutable tag. Pin to SHA256 digest in `image-versions.yml` and rotate via Renovate.

---

### NVIDIA kmod updates (MOK/akmod)

**Driver delivery method:**

ucore-hci `stable-nvidia` ships **pre-built, pre-signed NVIDIA open kernel modules** via the `ghcr.io/ublue-os/akmods-nvidia` OCI artifact. The build pipeline:
1. Akmods builds kernel modules in a Koji-like CI environment against the exact kernel shipped in the base image
2. Modules are signed with the Universal Blue MOK private key
3. Signed RPMs are packaged into an OCI layer (`ghcr.io/ublue-os/akmods-nvidia:<coreos-stable-NN@sha256:...>`)
4. ucore-hci's Containerfile uses `COPY --from=${AKMODS_NVIDIA_REF} /rpms/ /tmp/rpms` to inject them at build time

This means MiOS-2 users do NOT need to install akmods at runtime — the modules are pre-compiled and pre-signed in the base image.

**NVIDIA driver version (April 2026):** (updated 2026-04-20: v0.1.1 is the new stable; v0.1.1 superseded)

- **Default driver on `stable-nvidia`:** NVIDIA **v0.1.1** (released March 24, 2026 — the new big recommended stable driver for Linux; includes fix for kernel module build issue with Linux 6.19, which matters for F44)
- **LTS branch on `-lts` tags:** NVIDIA **580.x** (Universal Blue now has an explicit LTS stream; akmods-nvidia-lts OCI artifact feeds `-lts` variants)
- Previous `stable-nvidia` default was v0.1.1 (Dec 2025 – Mar 2026); ucore-hci rolled to 595 within ~1 week of NVIDIA release
- RTX 4090 (Ada Lovelace, GA102): fully supported by both open and proprietary modules
- RTX 50xx (Blackwell): **requires open kernel modules** — proprietary modules are incompatible with Blackwell architecture entirely
- **kernel-module suspend behavior (595+):** `NVreg_UseKernelSuspendNotifiers=1` opt-in now has `nvidia.ko` handle video-memory preservation internally when open kmods are in use — removes a long-standing suspend/resume quirk. MiOS should NOT set this knob unless specific resume issues appear.

**Known NVIDIA open module caveats for MiOS:**

- **4K/240Hz compositor regression (GSP firmware, KWin/GNOME Mutter):** Reported desktop-compositor stutter at 2560×1440@240Hz under KWin with GSP firmware; risk is likely higher at 4K/240Hz on RTX 4090. **Validate on 9950X3D+RTX 4090 before defaulting to open modules in MiOS.** Gate with `34-gpu-detect.sh` and allow proprietary escape-hatch.
- **Waydroid is incompatible with NVIDIA proprietary drivers.** NVIDIA open modules partially help (Mesa virtio-gpu path), but full Waydroid 3D acceleration on NVIDIA remains unsupported. MiOS users wanting Waydroid should use AMD or Intel GPU.
- **udev coldplug issue (critical for MiOS-2):** `ucore-hci:stable-nvidia` ships NVIDIA kernel modules that udev coldplugs **even in VMs with no GPU**. INDEX.md §3.5 documents the mitigation: blacklist NVIDIA modules by default, have `34-gpu-detect.sh` remove the blacklist only on bare metal. This is an existing MiOS-2 design requirement and must NOT be regressed.

**MOK enrollment (Universal Blue key):**

- Universal Blue ships a public MOK key at `/etc/pki/akmods/certs/akmods-ublue.der`
- Enrollment password is the well-known string `universalblue` (published publicly; security relies on MOK requiring physical presence at shim UI, not secrecy of this string)
- MiOS MOK automation (`enroll-mok.sh`, push-240) uses `--root-pw` instead of hardcoded passwords and is variant-aware: MiOS-2 detects and uses the ublue key, MiOS-1 uses a self-generated 2048-bit RSA key
- **2048-bit RSA only** — 4096-bit keys hang some shim versions
- **Every MOK mutation invalidates TPM2 PCR 7** — any LUKS slot sealed to PCR 7 must be re-sealed after enrollment
- **MokManager requires physical presence** — cannot be fully automated; this is by design in the shim trust model

**CDI (Container Device Interface) — current state:**

- `nvidia-container-toolkit v0.1.1` (current as of April 2026): CDI is now the **default mode** (not OCI hook). Read-only rootfs support is confirmed production-ready — critical for bootc.
- `nvidia-container-toolkit v0.1.1`: introduced `nvidia-cdi-refresh.service` for automatic CDI spec regeneration on toolkit install, kernel module reload, and GPU hotplug
- **DO NOT use nvidia-container-toolkit v0.1.1** — "unresolvable CDI devices" regression. Use v0.1.1 or v0.1.1+/v0.1.1
- CDI canonical path: `/var/run/cdi/nvidia.yaml` (runtime ephemeral) or `/etc/cdi/nvidia.yaml` (persistent); MiOS uses `/etc/cdi/` (push-239)
- Remove `oci-nvidia-hook.json` — coexistence with CDI causes dual-injection conflicts (push-239 delivered this fix)
- GPU access in Podman: `podman run --device nvidia.com/gpu=0` (CDI syntax) replaces old `--runtime=nvidia`

**CVEs requiring attention:**

- **CVE-2025-23266** (Critical) — nvidia-container-toolkit, fixed in v0.1.1+
- **CVE-2025-23267** (High) — nvidia-container-toolkit, fixed in v0.1.1+
- MiOS must ship nvidia-container-toolkit ≥ v0.1.1; current pinned version (v0.1.1 target) satisfies this

---

### Notable ucore-hci features / defaults

**Kernel and storage:**

- Kernel from Fedora stable (NOT Rawhide). Currently Fedora 42 kernel (Linux 6.13.x line as of April 2026)
- cgroups v2 only (cgroupv1 removed in systemd 258, GA September 2025)
- `/boot` is a separate 1 GB partition by default (BIB standard from Fedora 43+)
- composefs enabled by default (`composefs.enabled = yes`, unsigned — integrity against accidental mutation, not against root-level attackers). `/usr` covered; `/etc`, `/var`, `/boot` are NOT composefs-covered
- ZFS available via `stable-zfs` tag. OpenZFS DKMS is problematic on bootc (requires writable `/usr/src`); ucore solves this with pre-built `ucore-kmods` ZFS modules, but newer kernels marking symbols GPL-only causes intermittent ZFS compilation failures — not recommended for MiOS unless ZFS is specifically required

**Cockpit:**

- Cockpit is a first-class ucore feature. Socket-activation only (`cockpit.socket` enabled, `cockpit.service` on-demand)
- Cockpit ≥ 330 required for composefs compatibility — the setuid bug (cockpit-session failing on read-only filesystem) was resolved in Cockpit 330 (December 2024) by replacing setuid with systemd socket activation and `DynamicUser=`
- Current Fedora 42 ships Cockpit 349+, which includes `cockpit-podman 115` (Quadlet detection) and `cockpit-machines 339` (Stratis V2, serial console preservation)
- Known libvirt-socket race: `cockpit.socket` may start before `libvirtd.socket`; mitigate with `cockpit.socket.d/10-mios.conf` containing `After=libvirtd.socket`
- **libvirtd 45-second shutdown timeout** — known ucore-hci issue; ship `libvirtd.service.d/10-mios.conf` with `TimeoutStopSec=120s` to prevent service killed during active VMs

**Networking and firewall:**

- `netavark-firewalld-reload.service` included — re-adds Podman container firewall rules after firewalld reloads. Required for Podman networking stability on ucore bases; do NOT remove
- `firewall-offline-cmd` required for all build-time firewall config (firewalld not running in container builds)
- Tailscale included in the `ucore` tier and above

**SELinux:**

- SELinux enforcing mode is the default and immutable on ucore
- `container_manage_cgroup` boolean must be set for Podman container management
- Custom SELinux policy modules should use CIL format (`semodule -X 300 -i *.cil`) — monolithic `.te` compilation not feasible in container builds without make/checkpolicy
- `semanage import` with heredoc for bulk boolean + fcontext config at build time
- `fapolicyd` is available but historically caused 2–5 minute boot delays when hashing all binaries; if used, configure the RPM database trust backend exclusively to avoid hashing overhead

**Update tooling:**

- `uupd` (Go-based unified updater, replaced Python `ublue-update` which was archived August 2025) coordinates bootc + Flatpak (user + system) + Distrobox + Homebrew updates via systemd timer every 6 hours
- Pre-update hardware checks: battery level, CPU load, memory pressure, network connectivity
- `AutomaticUpdatePolicy=none` must be set in `rpm-ostreed.conf` when uupd is active (prevents rpm-ostree auto-staging competing with uupd)
- `ujust` / `ublue-os-just` provides numbered system-management recipes at `/usr/share/ublue-os/just/`

**zram / swap:**

- ucore ships with **zram swap enabled by default** via `zram-generator` (a systemd-zram-setup companion)
- Default zram configuration: single device at `zram0`, algorithm `zstd`, size = 50% of RAM
- Configuration file: `/etc/systemd/zram-generator.conf` (system) or `/usr/lib/systemd/zram-generator.conf` (image-shipped default)
- MiOS-2 should NOT override this — the default is appropriate for a workstation workload. If Ceph or K3s memory pressure is a concern, reduce zram to 25% of RAM
- Swap priority: zram gets priority 100 by default, leaving room for a low-priority disk swap partition at priority 10

**Image signing (supply chain):**

- All Universal Blue images are signed with a **Cosign key-pair** (NOT keyless-only). The private key is stored in a GitHub Actions secret; the public key is shipped in the image at `/etc/pki/containers/ublue-cosign.pub`
- Container verification policy at `/etc/containers/policy.json` enforces signature verification for all `ghcr.io/ublue-os` images
- **Critical:** Universal Blue uses cosign v2.6.x, NOT cosign v3. Cosign v3's default `--new-bundle-format` (protobuf) breaks rpm-ostree/bootc signature verification (rpm-ostree#5509). Do NOT upgrade to cosign v3 until rpm-ostree merges the fix.
- Images are also published with SBOM attachments (SPDX-JSON format via `syft`) using `oras attach` to avoid Rekor size limits
- Renovate Bot manages digest pins in `image-versions.yml` with a 7-day stability window

---

### Known issues with stable-nvidia base

**1. NVIDIA udev coldplug in VMs (critical, MiOS-specific design requirement):**
`ucore-hci:stable-nvidia` ships NVIDIA kernel modules that udev coldplugs even in VMs without a physical GPU, causing DRM errors, failed service starts, and GDM failures. INDEX.md §3.5 mandates blacklisting NVIDIA modules by default with `34-gpu-detect.sh` removing the blacklist only on bare metal. This must not be regressed.

**2. `nvidia-drm.modeset=1` and `nvidia-drm.fbdev=1` in VM kargs:**
These kargs must NOT be shipped unconditionally. Gate on hardware detection (`34-gpu-detect.sh`), not as default kargs. GDM fails in GPU-less VMs with these active.

**3. libvirtd 45-second shutdown timeout:**
Known issue in ucore-hci: `libvirtd.service` has a 45-second `TimeoutStopSec` which is insufficient for graceful VM shutdown. Ships `libvirtd.service.d/10-mios.conf` with `TimeoutStopSec=120s`.

**4. `mios-ceph-bootstrap.service` ConditionVirtualization:**
Must use `ConditionVirtualization=no` (not `!container`) to prevent service hangs in Hyper-V. Hyper-V is detected as a hypervisor, not a container, by systemd. Using `!container` misses this case.

**5. composefs-native rollback not yet supported:**
`bootc rollback` returns "This feature is not supported on composefs backend" on composefs-native. Stay on OSTree backend for rollback-critical deployments until composefs rollback support lands in bootc v1.16+.

**6. BIB + XFS + composefs.enabled=verity:**
`bootc-image-builder` fails during `org.osbuild.bootc.install-to-filesystem` if rootfs is XFS and composefs verity is enabled. XFS does not support `fsverity`. Use `ext4` or `btrfs` for BIB targets. (Documented in ai-journal.md, April 2026 entry.)

**7. Waydroid incompatibility with NVIDIA proprietary:**
Waydroid does not work with NVIDIA proprietary drivers on ucore-hci. NVIDIA open modules provide partial compatibility via Mesa virtio-gpu path, but full 3D acceleration remains unavailable on NVIDIA. MiOS-2 users wanting Waydroid should use AMD or Intel GPU.

**8. systemd-remount-fs crash on Fedora 42+/GNOME composefs:**
`systemd-remount-fs.service` crashes at boot on Fedora 42+ when composefs overlay is active because the kernel prevents remounting with new `/etc/fstab` options. Workaround: mask the service (`40-composefs-verity.sh`). Monitor Fedora 44+ for upstream systemd patch targeting `/sysroot` instead.

**9. xRDP is dead on GNOME 50:** (updated 2026-04-20 with confirmed release details)
**GNOME 50 "Tokyo" was released March 18, 2026** and ships as the default in **Fedora 44 (April 28, 2026 target)** and Ubuntu 26.04 LTS. The **X11 session is completely removed** — Wayland-only from GNOME 50 onward. xRDP and xorgxrdp have no Wayland backend and no upstream roadmap for one. **MiOS must have migrated to `gnome-remote-desktop` before the F43→F44 rebase.** Remove `xrdp`, `xorgxrdp`, `xorgxrdp-glamor`. Ship `gnome-remote-desktop` + `grdctl` provisioning. This also eliminates the xorgxrdp/xorgxrdp-glamor package conflict (INDEX.md §3.4).

**GNOME 50 remote-desktop wins (relevant for MiOS-2 RDP workflow):**
- **Vulkan + VA-API hardware acceleration** for RDP video stream — significantly smoother, lower latency, lower power vs. GNOME 48/49's software path. Requires mutter hw-accel build (default in F44).
- **HiDPI auto-scaling** for remote clients — resolution matches client display automatically.
- **Camera redirection** + **Kerberos authentication** for RDP sessions (enterprise SSO — pairs well with MiOS's FreeIPA integration).
- **Explicit sync** landed — meaningfully improves NVIDIA Wayland stability under RDP.
- **VRR + fractional scaling default ON** at the Mutter level.
- **HDR screen sharing** available in GNOME 50.

**MiOS action check:** verify `grdctl` is shipped (it's been in `gnome-remote-desktop` since GNOME 42, so this should already be satisfied). Ensure mutter/gnome-remote-desktop packages are present in the GNOME package set in `specs/engineering/2026-04-26-Artifact-ENG-001-Packages.md` (not a scope-of-today item — flag in NEXT-RESEARCH if not already pulled in).

**10. cosign v3 bundle format breaks bootc/rpm-ostree:**
Cosign v3 enables `--new-bundle-format` (protobuf) by default, incompatible with the `containers/image` library used by rpm-ostree and bootc for signature verification. Always sign with `cosign sign --new-bundle-format=false --yes $DIGEST` or stay on cosign v2.6.x until rpm-ostree#5509 is resolved.

---

### Signing / supply chain

**Universal Blue signing architecture:**

- **Primary: Key-pair signing.** Cosign private key in GitHub Actions secret. Public key shipped in image at `/etc/pki/containers/ublue-cosign.pub`. Policy JSON enforces verification for all `ghcr.io/ublue-os` images.
- **Secondary: Keyless signing (Fulcio/Rekor)** in parallel — Fulcio short-lived certificate from GitHub OIDC, logged to Rekor transparency log. Requires `id-token: write` GitHub Actions permission.
- **NOT keyless-only:** Despite some AI-indexed summaries claiming otherwise, Universal Blue YAML uses `COSIGN_PRIVATE_KEY` — always cross-check the actual workflow YAML rather than secondary summaries.
- **Cosign version:** Pinned to v2.6.x. Do NOT use cosign v3 default bundle format (rpm-ostree#5509 incompatibility). When cosign v3+ is used, always pass `--new-bundle-format=false`.

**SBOM:**

- SBOM generated via `syft` in SPDX-JSON + CycloneDX formats
- Attached via `oras attach` (not `cosign attest`) — avoids Rekor size limits that reject large SBOMs
- MiOS push-239 delivered this pattern

**Policy enforcement:**

- `/etc/containers/policy.json` at `/etc/containers/policy.json` enforces signature verification
- MiOS ships key-based policy (first entry) with keyless Fulcio chain as second entry
- `sigstoreSigned` type with `keyPath: /etc/pki/containers/mios-cosign.pub`

**Supply chain risk notes:**

- `stable-nvidia` is a mutable tag — a digest pin in `image-versions.yml` is required for reproducible builds. Current `image-versions.yml` has the digest commented out (`# digest: sha256:REPLACE_WITH_CURRENT_DIGEST`). This should be activated and managed by Renovate.
- Universal Blue runs weekly GHCR cleanup: keeps 7 most-recent untagged images, preserves all tagged images. MiOS should adopt same cleanup pattern (push-239 delivered the GHCR cleanup workflow).
- Bazzite (April 2026): **OpenSSF Scorecard** scanning runs on every build. ISO images are now signed. Build attestation via cosign is active. These represent the current security floor for mature Universal Blue projects.
- `ghcr.io/ublue-os/akmods-nvidia` artifacts (NVIDIA kernel module RPMs) are themselves signed and digest-pinned in the ucore Containerfile. MiOS inherits this trust chain by building FROM ucore-hci.

**Cayo (future base image — watch):**

`ublue-os/cayo` is the bootc-native HCI successor to ucore-hci. It is composefs-native from inception, designed to work with `bootc container ukify` for UKI Secure Boot, and targets the F44/F45 timeframe for production readiness. MiOS-2 should evaluate cayo as a MiOS-3 base migration candidate when it reaches stable status.
<!-- FINDINGS END -->

---

## 4. Fedora bootc / FCOS / OCI Transition

*Research thread: Fedora bootc official images, FCOS→OCI roadmap, Rawhide status*

<!-- FINDINGS BEGIN -->
### Fedora bootc official image status

- **`quay.io/fedora/fedora-bootc:rawhide`** — MiOS-1 base. Rawhide is now a first-class bootc image (since Fedora 43, released October 2025).
- **Fedora 44:** Branched from Rawhide **February 6, 2026**. This triggered CI matrix updates in bootc (issue #1985). MiOS-1 tracks `:rawhide` so it follows Fedora 44 → 45 automatically.
- **`fedora-bootc` as official Fedora artifact (F43+):** bootc-derived OCI images are now official Fedora release artifacts alongside the traditional ISO — not just experimental. Milestone: Initiatives/Image_Mode_Phase_2_(2026).
- **Kernel in rawhide (April 2026):** Linux 6.14.x line. systemd 259.5 shipped in rawhide (relevant to WSL2 failures fixed in this repo).

### FCOS → OCI-only transition

- Fedora CoreOS is actively transitioning to an OCI-only update model, dropping OSTree repo streaming.
- Pull-based OCI updates replace push-based OSTree HTTP transport.
- MiOS-2 is already on this model (ucore-hci is OCI-only). MiOS-1 will follow when the rawhide base finalizes its OCI-only pipeline.

### bootupd automatic bootloader updates (Fedora 43+)

- **`bootloader-update.service`** runs at next boot after a deployment containing updated bootloader artifacts.
- Uses `RENAME_EXCHANGE` atomic operation on UEFI systems — safe, crash-resistant.
- BIOS systems: supported but without atomic guarantees.
- `bootupctl status` to verify; `journalctl -u bootloader-update.service` to monitor.
- **Users can opt out:** mask `bootloader-update.service` before release if preferred.
- **Impact on MiOS:** No action needed — this is beneficial automation. Ensure MiOS images include `bootupd` (it's in ucore-hci base). Do NOT mask this service unless specifically required.

### greenboot-rs (Rust rewrite, Fedora 43+)

- Shell-based greenboot **deprecated**; greenboot-rs v0.1.1+ is the replacement.
- Fully compatible drop-in: same script directories, same systemd integration.
- Check scripts: `/etc/greenboot/check/required.d/` (fail → reboot) and `/etc/greenboot/check/wanted.d/` (advisory).
- **MiOS opportunity:** Add health check scripts for:
  1. Verify composefs verity mount is active
  2. Verify `mios-role.service` exited successfully
  3. Verify NVIDIA module load (bare metal only, via ConditionPathExists)
  - On 3 consecutive failed reboots, greenboot triggers `bootc rollback` automatically.

### Fedora 44 changes affecting MiOS (updated 2026-04-20)

| Change | Impact |
|--------|--------|
| Boot Loader Updates Phase 1 (F44): GRUB/shim content moves from `/boot` to `/usr` | `99-cleanup.sh` `find /boot/` cleanup should remain safe; new bootupd handles `/usr`-side content |
| systemd 260 (F44, **shipped upstream March 17, 2026**) | Removes final SysV init compat; MiOS already cgroups v2 only — no impact |
| composefs on Atomic Desktops (F42 stable, F44 default) | `/usr` verity now default in Fedora ecosystem; validates MiOS choice |
| Fedora 44 branched Feb 2026 | CI matrix: add `fedora-bootc:44` to build matrix alongside `:rawhide` for stability testing |
| **Fedora 44 release target: April 28, 2026** (pushed from April 21 over blocker bugs) | Brief window — validate MiOS-1 on rawhide (which is now effectively F45) through the branch event |
| **GNOME 50 "Tokyo" (Mar 18, 2026) is the F44 default** | X11 session completely removed — see Section 3 note #9 |
| **Konflux becomes the build pipeline for bootc-based Fedora artifacts** | Upstream churn in `quay.io/fedora/fedora-bootc:rawhide` digests expected through F44 transition. Renovate `minimumReleaseAge: "3 days"` remains appropriate. |
| **FUSE 2 binaries/libs removed from all Atomic Desktops** | If MiOS ships a FUSE-2-only package (`fuse` vs. `fuse3`), switch to fuse3. Non-issue if already using fuse3 (Fedora default since F35). |
| **PackageKit switches to DNF5 backend (libdnf5)** | Build-time: MiOS uses raw `dnf5` already — no impact. Runtime PackageKit consumers (GNOME Software, Cockpit) inherit the new backend automatically. |
| **LLVM 22, CMake 4.0 default generator `ninja`, Golang 1.26, Ruby 4.0** | Matters for `12-virt.sh` Looking Glass build: CMake 4.0 raises minimum required CMake version in some projects. Looking Glass B7+ already requires CMake ≥ 3.18, so no impact, but if a build regression appears on F44, suspect the CMake 4 default-generator change first. |
| **MariaDB default 10.11 → 11.8** | MiOS doesn't ship MariaDB by default — no impact. Flag if any user stack is pinned to 10.x. |
| **Fedora CoreOS builds also moving to Konflux** | Parallel transition; not a MiOS dep. |

### Image Mode Phase 2 (2026 initiative)

Fedora's Image Mode Phase 2 initiative targets making bootc-derived images the default delivery for all Fedora atomic variants. This includes:
- Silverblue, Kinoite, Sway, Budgie all receiving bootc-native builds
- Unified `fedora-bootc` base image shared across all variants
- `bootc upgrade` replacing `rpm-ostree upgrade` as the recommended update path system-wide
<!-- FINDINGS END -->

---

## 5. composefs / OSTree

*Research thread: composefs upstream, OSTree OCI spec, verity support, known issues*

<!-- FINDINGS BEGIN -->
### composefs 1.0 release

- **Released** with Linux kernel 6.6-rc1 containing overlayfs fs-verity support (all required kernel changes upstream)
- **Stable format guarantee:** composefs 1.0 commits to a stable erofs image format and stable library API
- **erofs improvements in 1.0:**
  - Bloom filter for faster xattr lookups (backward compatible with older erofs)
  - File inlining: small files embedded directly in erofs image, avoiding redirect overhead
- **New tooling:** `composefs-info` tool dumps image metadata; new API to regenerate lcfs_node trees from image files
- **Signature change:** fs-verity built-in signature support **dropped** in favour of userspace signatures (this affects the internal signing model, not end-user behavior — OSTree/bootc handle signature verification at the bootc layer)

### prepare-root.conf specification (authoritative)

Location: `/usr/lib/ostree/prepare-root.conf` (system default) or `/etc/ostree/prepare-root.conf` (local override)

```ini
[composefs]
# enabled = yes        - composefs active, no verity (integrity against accidental mutation)
# enabled = verity     - composefs + fsverity per-file verification (requires ext4/btrfs)
# enabled = signed     - composefs + fsverity + userspace signature verification
enabled = verity

[root]
transient = false      # true = writable root (all dirs) until reboot

[etc]
transient = false      # true = /etc fully ephemeral (no 3-way merge)
```

**MiOS uses `enabled = verity`** (set by `40-composefs-verity.sh`). This is the correct choice for a security-hardened workstation.

**Valid `enabled` values:**

| Value | Behavior | Filesystem requirement |
|-------|----------|----------------------|
| `yes` (default) | composefs overlay, no content verification | Any |
| `verity` | per-file fsverity before content read | ext4 (≥5.4) or btrfs (≥5.15) only |
| `signed` | verity + userspace signature check | ext4 or btrfs only |

### Filesystem support matrix for fsverity

| Filesystem | fsverity kernel version | composefs verity? |
|-----------|------------------------|------------------|
| ext4 | ≥ 5.4 | ✅ Yes |
| btrfs | ≥ 5.15 | ✅ Yes |
| XFS | Not supported | ❌ No — bootc errors at install |
| F2FS | ≥ 5.4 | ✅ (not tested with bootc) |
| tmpfs | Not supported | ❌ No |

**MiOS uses ext4 via BIB** — correct. XFS would silently break composefs verity.

### OSTree OCI format / rechunking

- **ostree container commit:** The `ostree container commit` call at end of `99-cleanup.sh` finalizes OCI layer metadata for bootc. Required; without it bootc cannot deploy the image.
- **Rechunking:** `hhd-dev/rechunk` (external) or `rpm-ostree build-chunked-oci --bootc` splits a monolithic OCI image into N equal layers. This reduces update size by 5-10x (only changed layers are re-downloaded).
- **Layer assignment via xattr:** Add `user.component=<name>` xattr to files during build to assign them to specific layers. Allows pinning frequently-changing components (configs, scripts) to their own layers.
- **MiOS rechunking:** `Justfile` target `just rechunk` uses `quay.io/centos-bootc/centos-bootc:stream10` as the rechunker base. Target: ≤67 layers (OCI spec limit is 127 layers, but registries often limit at 67-127).

### Known issues

1. **systemd-remount-fs crash (F42+):** `systemd-remount-fs.service` crashes when composefs overlay is active — kernel prevents remounting `/etc/fstab`-specified options on composefs-mounted root. Fix: mask the service (MiOS does this in `40-composefs-verity.sh`). Monitor systemd upstream for proper fix.
2. **bootc rollback unavailable on composefs:** `bootc rollback` returns error on composefs-native deployments. Status as of v1.15.x: still unresolved. Use greenboot-rs automated rollback as alternative.
3. **/var content from image not applied on update:** Content added to `/var` in image is only unpacked on FIRST install. Database files, spool dirs etc. added to the image are preserved on update (not overwritten). Use `tmpfiles.d` to ensure required dirs exist.
4. **XFS + BIB + verity = build failure:** `bootc-image-builder` errors during `bootc.install-to-filesystem` if `rootfs=xfs` and `composefs.enabled=verity`. Always use `ext4` or `btrfs` with MiOS verity config.
<!-- FINDINGS END -->

---

## 6. Podman Quadlet / systemd Integration

*Research thread: Quadlet spec changes, new container/volume/network keys, systemd integration*

<!-- FINDINGS BEGIN -->
### Quadlet file types and search paths

**Search paths (priority order, highest first):**
1. `/etc/containers/systemd/` — local/admin overrides
2. `/usr/share/containers/systemd/` — distro/image-shipped (MiOS uses this)
3. `~/.config/containers/systemd/` — user-level (rootless)

**Supported file types:**

| Extension | Unit type generated | Description |
|-----------|--------------------|----|
| `.container` | `<name>.service` | Podman container |
| `.volume` | `<name>-volume.service` | Podman volume (creates on first start) |
| `.network` | `<name>-network.service` | Podman network |
| `.pod` | `<name>-pod.service` | Podman pod |
| `.image` | `<name>-image.service` | Pre-pull image (for logically bound images) |
| `.kube` | `<name>.service` | Podman play kube |
| `.build` | `<name>.service` | Build container image |

### [Unit] section — fully supported, passed through unchanged

All standard systemd `[Unit]` directives work in Quadlet files exactly as in `.service` files:

```ini
[Unit]
Description=My container
After=local-fs.target network-online.target
Requires=network-online.target
ConditionVirtualization=!wsl        # Gate on non-WSL2
ConditionPathExists=/dev/kfd        # Gate on hardware presence
```

`ConditionVirtualization=!wsl` is fully supported and is the correct way to skip services in WSL2. This is what MiOS uses for the crowdsec-dashboard Quadlet (after the April 2026 fix).

### [Container] section — key reference

```ini
[Container]
Image=docker.io/example/app:latest
ContainerName=my-app               # Stable name for `podman ps`
PublishPort=8080:80
Volume=my-data.volume:/data        # Reference a .volume Quadlet
Network=my-net.network             # Reference a .network Quadlet
Environment=KEY=value
EnvironmentFile=/etc/my-app/env
AutoUpdate=registry                # Pull new image on `podman auto-update`
Label=io.containers.autoupdate=registry
PodmanArgs=--read-only             # Arbitrary podman run args
User=1000:1000
Group=1000
GlobalArgs=--storage-opt=additionalimagestore=/usr/lib/bootc/storage  # For logically bound images
AppArmor=unconfined                # New in Podman 5.x: set AppArmor profile
```

**`AutoUpdate=registry`** — instructs `podman auto-update` (via `podman-auto-update.service` or `podman-auto-update.timer`) to check and pull a new image when the registry digest changes. Separate from Renovate — this is runtime auto-update.

### Logically Bound Images (bootc feature, Quadlet-integrated)

Declare in `/usr/lib/bootc/bound-images.d/` as symlinks pointing to Quadlet `.image` or `.container` files. bootc pre-fetches these during `bootc upgrade` / `bootc install`.

```ini
# /usr/share/containers/systemd/my-agent.image
[Image]
Image=ghcr.io/example/my-agent:latest

# /usr/lib/bootc/bound-images.d/my-agent.image -> /usr/share/containers/systemd/my-agent.image
```

**MiOS opportunity:** CrowdSec, Guacamole, and monitoring agents are good candidates for logically bound images — they're always needed at boot and should be available without network access post-install.

**Requirements:** Must include `GlobalArgs=--storage-opt=additionalimagestore=/usr/lib/bootc/storage` in container files referencing bound images. Rootless containers not currently supported.

### Multi-file Quadlet (Podman 5.x)

Podman 5.x supports multiple Quadlet units in a single file, separated by `---` delimiter:

```
# FileName=app.container
[Container]
Image=app:latest
---
# FileName=app-db.volume
[Volume]
```

Allows shipping related Quadlet units as one file for organizational clarity.

### 2026-04-20 update — Podman 5.6 Quadlet management CLI and new keys

Podman **5.6** (shipped late 2025, present in Fedora 43+) introduces a first-class Quadlet management CLI:

| Command | Purpose |
|---------|---------|
| `podman quadlet install <file>` | Install a Quadlet into `/etc/containers/systemd/` (rootful) or `~/.config/containers/systemd/` (rootless) |
| `podman quadlet list` | List installed Quadlets with their generated unit names |
| `podman quadlet print <name>` | Print the source Quadlet file content |
| `podman quadlet rm <name>` | Remove an installed Quadlet + reload systemd |

(Remote Podman client support deferred to a future release.)

**New Quadlet keys in 5.6:**
- `.container` — `Environment=KEY` (no value) pulls the variable from the host at start time
- `.pod` — new keys `Label=` (applies labels to the created pod) and `ExitPolicy=`
- `.image` — new `Policy=` key (values: `always`, `newer`, `missing`) controls pull behavior on unit start

**Quadlet warns on known-bad keys:** When generated units include `User=`, `Group=`, or `DynamicUser=` in `[Service]`, Quadlet now emits a warning — those options are known-incompatible with Podman's security model.

**Behavior change:** Quadlet no longer uses container/pod ID files for `podman stop`; it passes the container/pod name directly. Benign improvement.

**MiOS implication:** `/usr/share/containers/systemd/` (distro-shipped path) is unchanged. The new `podman quadlet install|rm` targets `/etc/containers/systemd/` for admin-installed units — safe to ignore for image-baked Quadlets. Consider adopting `Policy=newer` on `.image` Quadlets for logically-bound images to reduce unnecessary pulls. `Cockpit ≥ 349` can now render/manage Quadlets graphically (new Red Hat Developer article, April 2026).

### 2026-04-25 update — Podman 5.7 → 5.8 chain (current: v0.1.1)

Latest Podman release: **v0.1.1 (April 14, 2026)**. F44 is expected to ship Podman 5.8.x as the default.

| Version | Date | Highlights for MiOS |
|---------|------|-----------------------|
| v0.1.1 | 2025-11-11 | New `.artifact` Quadlet type (OCI artifact management); new container keys: `HttpProxy=`, `StopTimeout=`, `BuildArg=`, `IgnoreFile=`; multi-YAML `.kube` files; templated dependencies for volumes/networks; `--replace` flag for `podman quadlet install`; new `podman quadlet cat` alias |
| v0.1.1 | 2025-12-10 | Bug-fix: FreeBSD + rootless mode |
| v0.1.1 | early 2026 | **Multi-file Quadlet `---` delimiter + `# FileName=` naming** matured (existing MiOS pattern is forward-compatible); **AppArmor profile config in `.container` files**; entrypoint clearing + healthcheck parser fixes |
| v0.1.1 | 2026-04-14 | Bug-fix point release; current latest |

**Action items for MiOS (none breaking):**
1. After F44 rebase, audit any `.container` files for new lint warnings (5.8 added stricter parsing of `User=`/`Group=`/`DynamicUser=`).
2. The new `HttpProxy=` key on `.container` is useful for corporate-proxy CrowdSec/CTI scenarios — opt-in only.
3. `.artifact` Quadlets are a candidate for shipping signed CDI specs as OCI artifacts (future enhancement; not required today).

### 2026-04-25 update — Cockpit ≥ 349 Quadlet GUI feature progression

Verified via Cockpit blog + cockpit-podman releases:

| Cockpit | cockpit-podman | Quadlet capability |
|---------|---------------|-------------------|
| 349 | 100 | List **stopped** Quadlets as inactive pods/containers (rootless + system) |
| 350 | 107 | Stop / start / restart Quadlet containers from the GUI |
| 357 | — | OCI image label rendering (description, version) |
| 360 | 116 | Quadlet management fully integrated; custom-login-page support |
| **361** (latest, 2026-04-21) | — | Stability/translation; no new Quadlet keys |

**MiOS guidance:** ucore-hci `stable-nvidia` ships whatever Cockpit is in F42 base today; once F44 rebase happens (April 28+), Cockpit 360+ becomes available, unlocking Quadlet GUI management for k3s/Ceph/CrowdSec workloads. **Critical:** Cockpit 360 is also the security-fix release for CVE-2026-4631 (see Section 12) — do **not** stay on Cockpit 327–359.

### WSL2 / dbus interaction

- Podman requires a running dbus session for some operations in WSL2.
- `podman.socket` activates lazily — `mios-role.service` correctly calls `systemctl start podman.socket` in `wsl-firstboot`.
- Quadlet files in `/usr/share/containers/systemd/` are compiled at container-generate time (`systemd-generator`). If dbus is unavailable at generator time, compilation may fail silently. Always gate Quadlets that need dbus with `After=dbus.socket`.
- `crowdsec-dashboard.container` now correctly has `ConditionVirtualization=!wsl` to skip compilation-time failures in WSL2.

### Known gotchas for MiOS

1. **`Restart=always` on containers** — causes infinite restart loops when the container image can't be pulled (no network) or when a dependency (dbus, crowdsec config) is missing. Always use `Restart=on-failure` with `RestartSec=30` on image-pull-dependent containers.
2. **`WantedBy=multi-user.target` without `ConditionVirtualization`** — container services auto-start in ALL environments including WSL2. Gate with `ConditionVirtualization=!wsl` for containers that require hardware/GPU/dbus.
3. **Volume Quadlets create Podman volumes, not directories** — do not confuse with `tmpfiles.d` directory creation.
4. **`AutoUpdate=registry` + `stabilityDays`** — these are independent mechanisms. Renovate manages the image tag in the Quadlet file; `podman auto-update` manages pulling new content under that tag at runtime. Use both for defense-in-depth.
<!-- FINDINGS END -->

---

## 7. WSL2 / systemd Integration

*Research thread: WSL2 systemd compatibility, known failures, upstream patches*

<!-- FINDINGS BEGIN -->
### WSL2 kernel / systemd compatibility matrix (April 2026) (updated 2026-04-25: WSL v0.1.1 + v0.1.1 shipped)

| WSL version | WSL kernel | systemd behavior | Notes |
|-------------|-----------|-----------------|-------|
| WSL 2.3.x | v0.1.1.x | Stable | Legacy; cgroupv1 still present |
| WSL 2.4.x | v0.1.1.x | Mostly stable | auditd fails; journald audit crash |
| WSL 2.6.x | 6.6.x | Active issues | User session failures reported after 0.0.0.0 |
| WSL v0.1.1 | 6.6 LTS point release | Released 2025-12-11 | Masked `systemd-networkd-wait-online.service` during boot; improved VirtioProxy networking + VirtioFS POSIX. |
| WSL v0.1.1 | 6.6 LTS point release | Released 2026-03-24 | **CVE-2026-26127 .NET runtime fix.** Masked **both** `NetworkManager-wait-online.service` and `systemd-networkd-wait-online.service`. Added IPv6 over virtio networking. Enabled DNS tunneling for VirtioProxy. **wsl-user-generator: statx syscall support, directory-mount support.** |
| **WSL v0.1.1** (pre-release) | 6.6 LTS point release | **Released 2026-04-25 (today)** | **CVE-2026-32178 .NET SMTP header-injection fix** (System.Net.Mail CRLF). Improved socket/signal handling. 30+ stability changes. Pre-release channel — stable cadence next. |

WSL2 runs Linux 5.15.x or 6.6.x kernel depending on Windows version. The kernel is Vendor-maintained fork: `github.com/microsoft/WSL2-Linux-Kernel`.

**systemd version in Fedora 44/rawhide:** 259.5-1.fc44 (confirmed from MiOS WSL2 boot log, April 2026).

**Critical:** WSL2 `ConditionVirtualization=wsl` is the systemd-native way to detect WSL2. Use `ConditionVirtualization=!wsl` to skip services in WSL2.

### Known service failures in WSL2 (with fixes)

| Service | Failure mode | Root cause | Fix |
|---------|-------------|-----------|-----|
| `systemd-journald` | status=1, start limit | Audit netlink socket absent in WSL2 kernel; journald crashes when `Audit=yes` | `journald.conf.d/10-mios-noaudit.conf`: set `Audit=no` |
| `dbus-broker` | status=1 cascade | `--audit` flag causes failure when audit socket absent | `dbus-broker.service.d/10-mios-no-audit.conf`: clear ExecStart, restart without `--audit` |
| `mios-role.service` | status=203/EXEC | Scripts in system_files had git mode 100644 (non-executable); tar\|tar preserves modes | Fixed: `git update-index --chmod=+x` on all 6 libexec scripts (April 2026) |
| `mios-cdi-detect.service` | status=203/EXEC | Same as above | Fixed: same git mode fix |
| `upower.service` | SIGABRT | Probes `/sys/class/power_supply` and DBus HW interfaces not present in WSL2 | `upower.service.d/10-mios-wsl2.conf`: `ConditionVirtualization=!wsl` |
| `auditd.service` | NOPERMISSION | Kernel audit subsystem absent | `auditd.service.d/10-mios-wsl2.conf`: `ConditionVirtualization=!wsl` |
| `audit-rules.service` | cascade | auditd missing | Same drop-in |
| `usbguard.service` | permission denied | `usbguard-daemon.conf` delivered as 0644; daemon requires 0600 | `47-hardening.sh`: `chmod 0600` before enable |
| `mios-gpu-{amd,intel,nvidia}.service` | ordering cycle | `Before=podman.socket docker.socket` creates systemd ordering cycle | Removed `Before=` on socket units (April 2026) |
| `waydroid-container.service` | fails | binderfs not available in WSL2 | `38-vm-gating.sh`: `ConditionPathExists=!/proc/sys/fs/binfmt_misc/WSLInterop` |
| `crowdsec-dashboard.service` | restart loop | `Restart=always` + no WSL2 gate + dbus not ready | `ConditionVirtualization=!wsl` + `Restart=on-failure RestartSec=30` |
| `systemd-machined` | non-fatal | cgroup features absent | `wsl2-optional.conf`: `ConditionVirtualization=!wsl` |
| `gdm.service` | no display | No GPU in WSL2 | `gdm.service.d/10-skip-wsl.conf`: `ConditionPathExists=!/proc/sys/fs/binfmt_misc/WSLInterop` |

### ConditionVirtualization=wsl detection

systemd detects WSL2 by reading `/proc/sys/kernel/osrelease` and checking for `WSL` or `microsoft` string (case-insensitive). This is the same check that `ConditionVirtualization=wsl` uses.

**Alternative detection methods (less preferred):**
- `test -f /proc/sys/fs/binfmt_misc/WSLInterop` — exists in WSL2 (used in MiOS drop-ins for services written before systemd 252+ added wsl support)
- `test -e /dev/dxg` — NVIDIA GPU paravirtualization device; exists only in WSL2 with NVIDIA GPU pass-through enabled
- `grep -qi microsoft /proc/version` — crude but works pre-systemd252

**Preference order for new MiOS drop-ins:** Use `ConditionVirtualization=!wsl` for all new WSL2 gating. Use `ConditionPathExists` only when the condition is truly about hardware presence rather than virtualization type.

### NVIDIA GPU paravirtualization in WSL2 (`/dev/dxg`)

- `/dev/dxg` is the NVIDIA paravirtualization device in WSL2 (exposed when Windows host has NVIDIA GPU and WSL2 CUDA driver is installed)
- `mios-cdi-detect.service` (`select-cdi-spec` script) correctly checks `if [[ -e /dev/dxg ]]; then MODE="wsl"` and calls `nvidia-ctk cdi generate --mode=wsl`
- CDI spec location in WSL2 mode: `/var/run/cdi/nvidia.yaml` (same as bare metal)
- The WSL2 CUDA driver is separate from the Linux NVIDIA driver — don't install regular NVIDIA kmods in WSL2

### WSL2 systemd user session failures (WSL 0.0.0.0+)

Multiple reports of "Failed to start the systemd user session" after WSL 0.0.0.0 update. Root cause appears to be: `/run/systemd/user-generators/wsl-user-generator` marked world-writable (security regression introduced in 0.0.0.0). Vendor is tracking in WSL issue tracker. Mitigation: `chmod 755 /run/systemd/user-generators/wsl-user-generator` if user sessions fail on first login.

### Recommended drop-in pattern for WSL2 gating

```ini
# /usr/lib/systemd/system/<service>.d/10-mios-wsl2.conf
[Unit]
ConditionVirtualization=!wsl
```

For services that must also be skipped in containers (not just WSL2):
```ini
[Unit]
ConditionVirtualization=!container
ConditionVirtualization=!wsl
```
<!-- FINDINGS END -->

---

## 8. Sigstore / cosign / Supply-Chain

*Research thread: cosign keyless signing, Fulcio/Rekor, SBOM patterns, bootc image signing*

<!-- FINDINGS BEGIN -->
### cosign keyless signing (current state 2026)

**Mechanism:** Keyless signing binds an identity (GitHub Actions OIDC token) rather than a key to the signature. Flow:
1. CI job requests OIDC token from GitHub (`id-token: write` permission required)
2. cosign presents token to **Fulcio** CA → receives short-lived X.509 certificate (10-minute TTL) binding the OIDC identity to an ephemeral key pair
3. cosign signs the image with the ephemeral key; signature stored in **Rekor** transparency log
4. Certificate is discarded; verification uses Fulcio root CA + Rekor inclusion proof

**Verification:** `cosign verify --certificate-identity-regexp=... --certificate-oidc-issuer=https://token.actions.githubusercontent.com ghcr.io/mios-project/mios:latest`

**GitHub Actions workflow pattern (MiOS `build-sign.yml`):**
```yaml
permissions:
  id-token: write   # OIDC token for Fulcio
  packages: write   # Push to GHCR
  contents: read

- name: Sign image
  run: |
    cosign sign --yes \
      ghcr.io/mios-project/mios@${{ steps.build.outputs.digest }}
```

**`--yes` flag:** Required in non-interactive CI to skip the Rekor upload confirmation prompt. Without it, the step hangs.

### SBOM generation (syft SPDX/CycloneDX)

**syft** is the standard tool for generating SBOMs from OCI images:
```bash
syft ghcr.io/mios-project/mios:latest \
  -o spdx-json=mios-mios-2-sbom.spdx.json \
  -o cyclonedx-json=mios-mios-2-sbom.cyclonedx.json
```

**Filename convention (confirmed from build.yml fix):** `mios-*-sbom.*.json` (dash before sbom, not dot). The CI artifact upload glob was fixed from `mios-*.sbom.*.json` to `mios-*-sbom.*.json` in April 2026 — the old glob never matched.

**SBOM signing:** After generating SBOM, attach as OCI attestation:
```bash
cosign attest --type spdxjson --predicate mios-sbom.spdx.json \
  ghcr.io/mios-project/mios@<digest>
```

### OCI attestation / SLSA provenance

- **SLSA Level 1:** Build provenance (who built it, when, from what source) stored as OCI attestation via cosign
- **SLSA Level 2+:** Requires hosted/isolated build environment (GitHub Actions hosted runners qualify)
- MiOS uses GitHub-hosted runners + OIDC keyless signing → achieves SLSA Level 2
- `cosign attest` with `--type slsaprovenance` attaches SLSA provenance as OCI attestation
- `cosign verify-attestation --type slsaprovenance` to verify

### containers/policy.json verification

MiOS ships `/etc/containers/policy.json` and per-registry override YAML in `/etc/containers/registries.d/`. Configuration:

```json
{
  "default": [{"type": "insecureAcceptAnything"}],
  "transports": {
    "docker": {
      "ghcr.io/mios-project": [{
        "type": "sigstoreSigned",
        "keyless": {
          "signedIdentity": {"type": "matchRepository"},
          "fulcio": {"caData": "<base64 Fulcio root CA>"},
          "rekorPublicKeyData": "<base64 Rekor public key>"
        }
      }]
    }
  }
}
```

This enforces signature verification when Podman pulls from `ghcr.io/mios-project/*`. Only images signed via the Fulcio/Rekor chain are accepted. The ublue cosign public key (`/etc/pki/containers/ublue-cosign.pub`) handles verification of the ucore-hci base image.

### GitHub Actions signing workflow best practices

1. Use `actions/attest-build-provenance@v2` (GitHub-native SLSA provenance) alongside cosign for defense-in-depth
2. Pin cosign action to digest: `uses: sigstore/cosign-installer@v3.x.y@sha256:<digest>` (Renovate manages this via `helpers:pinGitHubActionDigests`)
3. Sign the digest (not the tag): `cosign sign ghcr.io/image@sha256:<digest>` — tag-based signing is mutable and insecure
4. Store cosign verification policy in the image itself (`/etc/containers/policy.json`) so verification is enforced at runtime, not just at CI time

### 2026-04-20 update — cosign v0.1.1 and v0.1.1 dual release (updated 2026-04-25: CVE-2026-39395 assignment + impact detail)

On **April 6, 2026**, sigstore released both **cosign v0.1.1** (v3 line) and **cosign v0.1.1** (v2 line) on the same day. Both releases address **GHSA-w6c6-c85g-mmv6 / CVE-2026-39395** — `cosign verify-blob-attestation` may erroneously report **"Verified OK"** for attestations with malformed payloads or mismatched predicate types. For old-format bundles + detached signatures, this was a logic flaw in error-handling of predicate-type validation. For new-format bundles, predicate-type validation was bypassed completely. Without `--check-claims=true`, an attestation with a valid signature but malformed/unparsable payload would be incorrectly validated.

Any MiOS CI pipeline that uses cosign to verify DSSE attestations (e.g., SLSA provenance, SBOM predicates) MUST be on **v0.1.1 or v0.1.1+**.

**MiOS status:** Already pinned to v0.1.1 in `42-cosign-policy.sh` (GitHub Actions installer pinned to `sigstore/cosign-installer@v0.1.1` with `cosign-release: 'v0.1.1'` per April 21 implementation). **No action required.**

Additional v3.0.x fixes:
- v0.1.1 — added protobuf-bundle compatibility for more subcommands (still requires `--new-bundle-format=false` for rpm-ostree/bootc consumers)
- v0.1.1 — fixed GHSA-whqx-f9j3-ch6m (bundle verify path for old bundle / trusted root)
- v0.1.1 — GHSA-w6c6-c85g-mmv6 DSSE predicate validation fix; OpenBao-managed keys; certificate annotation handling

**MiOS guidance unchanged:** stay on **v2.6.x** (current: **v0.1.1**) for signing and signature-verification, because `containers/image` / rpm-ostree / bootc **still do not accept the cosign v3 protobuf bundle format by default** (rpm-ostree issue #5509 is the tracking bug, still open as of April 2026). If the build workflow is pinned to cosign v3, it MUST pass `cosign sign --new-bundle-format=false --yes $DIGEST`. Renovate's `helpers:pinGitHubActionDigests` should be bumping `sigstore/cosign-installer` to a commit that installs v0.1.1 on the `build-sign.yml` workflow.

**Action item (NEXT-RESEARCH candidate):** verify the pinned `cosign-installer` version in `.github/workflows/build-sign.yml` currently resolves to cosign v0.1.1 (or a v3.0.x with explicit `--new-bundle-format=false`). If not, flag for MiOS.
<!-- FINDINGS END -->

---

## 9. kargs.d Spec & bootc Lint Rules

*Research thread: kargs.d TOML schema, bootc container lint rules, known rejections*

<!-- FINDINGS BEGIN -->
### kargs.d TOML schema (authoritative — verified from bootc.dev docs)

**Location:** `/usr/lib/bootc/kargs.d/*.toml`

**Valid top-level keys: ONLY TWO**

```toml
# VALID — flat array of kernel argument strings
kargs = ["mitigations=auto,nosmt", "console=ttyS0,115200n8"]

# VALID — optional architecture filter (Rust stdlib arch names)
match-architectures = ["x86_64"]
```

**That is the complete spec.** No other keys. No section headers. No `delete` key. No `append` key.

### Invalid patterns (all rejected by bootc lint with error)

```toml
# INVALID — Assistant hallucination: section header
[kargs]
append = ["quiet"]
delete = ["rhgb"]

# INVALID — 'delete' key does not exist
delete = ["rhgb"]

# INVALID — 'append' key does not exist
append = ["quiet"]

# INVALID — nested table
[kargs]
kargs = ["quiet"]
```

**Error message from bootc lint:** `Unexpected runtime error running lint bootc-kargs: Parsing <filename>.toml`

Any of the above formats causes bootc to reject the kargs.d file entirely at lint time. MiOS previously had a `01-mios-vm-boot.toml` using Assistant-format that was deleted in v0.1.1 for this reason.

### Merge / priority order

- Files are processed in **lexicographic order** by filename within `/usr/lib/bootc/kargs.d/`
- **Last file wins** for conflicting argument values (same arg name, different value)
- The base image's kargs.d entries are always present; derived images ADD to them
- **Undefined behavior:** Removing a kernel argument locally that the base image added via kargs.d

**MiOS file naming convention:**
```
00-mios.toml           # Base: console, plymouth
10-mios-console.toml   # Console serial port
10-mios-verbose.toml   # systemd.show-status=true (HYPHEN not underscore)
30-security.toml          # lockdown=integrity, slab_nomerge
```

### match-architectures values (Rust stdlib names)

The `match-architectures` field uses Rust's `std::env::consts::ARCH` values, which differ from Linux/Debian conventions in some cases:

| Rust value | Linux `uname -m` | Notes |
|-----------|-----------------|-------|
| `x86_64` | `x86_64` | Same |
| `aarch64` | `aarch64` | Same |
| `arm` | `armv7l` | Differs |
| `powerpc64` | `ppc64le` | Differs! Rust uses BE name even for LE |
| `riscv64` | `riscv64` | Same |

**MiOS:** Currently all kargs files are x86_64 targeted (AMD Ryzen 9950X3D). If ARM64/aarch64 support is added, use `match-architectures = ["aarch64"]`.

### bootc container lint — complete check list

Run as `RUN bootc container lint` in the Containerfile (final stage).

**Checks performed:**
1. **kargs.d syntax** — validates every `.toml` in `/usr/lib/bootc/kargs.d/`; rejects any file with section headers or non-standard keys
2. **Multiple kernels** — only ONE kernel in `/usr/lib/modules/` is supported; multiple = error
3. **`/usr/etc` content** — files explicitly placed here are rejected (it's an internal bootc path)
4. **Missing tmpfiles.d entries** (v0.1.1+) — warns if `/var` directories exist in image without corresponding `tmpfiles.d` entry
5. **Non-UTF-8 filenames** — any non-UTF-8 filename in image = error
6. **Stale log files** — warns if log files are left in image (should be cleaned by 99-cleanup.sh)
7. **`match-architectures` values** — validates arch names against Rust stdlib list

**bootc lint exit codes:**
- `0` — all checks pass
- `1` — one or more checks failed (hard errors)
- Warnings do not cause non-zero exit (soft failures only log to stdout)

### Common MiOS-specific lint failure patterns

| Pattern | Lint result | Fix |
|---------|------------|-----|
| `[kargs]` section header in TOML | ERROR — parsing failure | Remove header; use bare `kargs = [...]` |
| `systemd.show_status` (underscore) | Not a lint error — silently ignored by kernel | Fix to `systemd.show-status` (hyphen) |
| Two kernels from base + akmod install | ERROR — multiple kernels | Don't install kernel RPMs; only install `kernel-modules-extra` |
| Files in `/var/lib/myapp/` without tmpfiles.d | WARN (v0.1.1+) | Add `tmpfiles.d/mios-myapp.conf` with `d /var/lib/myapp 0755 myapp myapp -` |
<!-- FINDINGS END -->

---

## 10. NVIDIA Container Toolkit / CDI

*Research thread: nvidia-ctk CDI spec, nvidia-cdi-refresh, Container Device Interface standard*

<!-- FINDINGS BEGIN -->
### nvidia-container-toolkit release history (2024–2026)

| Version | Key changes relevant to MiOS |
|---------|--------------------------------|
| v0.1.1 | CDI stable; read-only rootfs support confirmed working |
| **v0.1.1** | **REGRESSION: "unresolvable CDI devices" bug — DO NOT USE** |
| v0.1.1 | `nvidia-cdi-refresh.service` introduced for automatic CDI spec regeneration |
| **v0.1.1** | CDI is now default mode (replaces OCI hook); `After=multi-user.target` bug introduced in cdi-refresh.service; NRI plugin server; IGX 2.0 Thor support; read-only rootfs declared stable |

**As of April 2026:** v0.1.1 (March 12, 2025) is still the latest released version — no post-v0.1.1 line has shipped. MiOS ships nvidia-container-toolkit ≥ v0.1.1 (satisfies CVE-2025-23266/23267 fixes). (updated 2026-04-20: corrected date; no new CVEs or regressions discovered for v0.1.1 in the April-2026 pass.)

### The nvidia-cdi-refresh.service ordering bug (CRITICAL for MiOS)

**Bug introduced:** v0.1.1 (March 12, 2025 — date corrected 2026-04-20 against github.com/NVIDIA/nvidia-container-toolkit/releases; the doc previously said "March 2026")
**GitHub issue:** NVIDIA/nvidia-container-toolkit#1735
**Current upstream state as of 2026-04-20:** v0.1.1 is still the latest tagged release. No v0.1.1 or v1.20.x has shipped. The `After=multi-user.target` ordering issue remains in-tree; MiOS's drop-in workaround in `systemd/nvidia-cdi-refresh.service.d/10-mios-ordering.conf` is still required.

**What happened:** v0.1.1 added `After=multi-user.target` to `nvidia-cdi-refresh.service`. This creates an ordering cycle:
- Service A wants `multi-user.target`
- Service A also `Requires=nvidia-cdi-refresh.service`
- `nvidia-cdi-refresh.service` has `After=multi-user.target`
- Result: `multi-user.target` → Service A → nvidia-cdi-refresh → (wait for multi-user.target) → CYCLE

Any service in `multi-user.target` that depends on `nvidia-cdi-refresh.service` is broken by this.

**MiOS fix (already shipped):** `systemd/nvidia-cdi-refresh.service.d/10-mios-ordering.conf`:
```ini
[Unit]
After=
After=systemd-modules-load.service systemd-udev-settle.service
Wants=systemd-udev-settle.service
```

Empty `After=` clears the inherited `After=multi-user.target`; then re-declares sane minimal ordering. This drop-in was in the repo before v0.1.1 due to anticipation from reading the upstream issue — validated correct.

### CDI spec format (current)

CDI (Container Device Interface) is an OCI spec extension for device injection into containers. MiOS uses:

```
/var/run/cdi/nvidia.yaml    # Ephemeral; regenerated by mios-cdi-detect.service
/etc/cdi/                   # Persistent; alternative location
```

**CDI spec is generated by:** `nvidia-ctk cdi generate --mode=<mode> --output=/var/run/cdi/nvidia.yaml`

**Modes:**
- `auto` — auto-detect (bare metal: uses driver API; WSL2: uses /dev/dxg)
- `wsl` — WSL2 paravirtualization mode (reads from Windows WDDM driver via /dev/dxg)
- `csv` — CSV-format input for environments without nvidia-smi

**Container usage (CDI syntax):**
```bash
podman run --device nvidia.com/gpu=0 ...    # Specific GPU
podman run --device nvidia.com/gpu=all ...  # All GPUs
```
Old `--runtime=nvidia` / OCI hook approach is deprecated; CDI is now the default.

### WSL2 CDI mode

`mios-cdi-detect.service` (the `select-cdi-spec` script) correctly handles WSL2:
1. Checks `if [[ -e /dev/dxg ]]` — /dev/dxg exists only in WSL2 with NVIDIA GPU pass-through
2. If WSL2: calls `nvidia-ctk cdi generate --mode=wsl`
3. If no NVIDIA devices: exits 0 (skip silently)
4. If bare metal: uses `auto` mode

**WSL2 requirement:** Windows host must have NVIDIA GPU + WSL2 CUDA driver installed (`nvidia-smi.exe` visible from WSL2). Without this, `/dev/dxg` is absent and CDI generation is skipped — correct behavior.

### NVIDIA open kernel modules (Blackwell/570+)

- **RTX 50xx (Blackwell):** ONLY compatible with open kernel modules (kmod-nvidia-open). Proprietary modules do not support Blackwell architecture.
- **RTX 40xx (Ada, including RTX 4090):** Both open and proprietary modules work; open modules recommended going forward.
- **Driver version for RTX 4090 + RTX 50xx:** 570.x series (open modules only from 570+).
- **ucore-hci `stable-nvidia`:** Ships NVIDIA open modules v0.1.1 as of April 2026.

**MiOS implication:** `34-gpu-detect.sh` should detect RTX 4090 (GA102, Ada Lovelace) and ensure open modules are not accidentally blacklisted. The bare-metal detection path is correct; Blackwell compatibility is provided by the ucore-hci base (open module pipeline).

### CVEs requiring attention

| CVE | Severity | Fixed in | Description |
|-----|----------|----------|-------------|
| CVE-2025-23266 | Critical | v0.1.1+ | Container escape via CDI device injection |
| CVE-2025-23267 | High | v0.1.1+ | Privilege escalation in OCI hook path |

MiOS target of nvidia-container-toolkit v0.1.1 satisfies both CVEs.
<!-- FINDINGS END -->

---

## 11. Renovate / Digest Pinning

*Research thread: Renovate OCI digest pinning, stability window config, image-versions.yml patterns*

<!-- FINDINGS BEGIN -->
### Renovate OCI/Docker datasource (current)

**Datasource: `docker`** is Renovate's unified datasource for all OCI/container registry traffic — it handles Docker Hub, ghcr.io, quay.io, and any OCI-conformant registry identically. The `docker:pinDigests` preset (part of `config:best-practices` since Renovate v37+) instructs Renovate to:

1. Detect `FROM image:tag` lines in Dockerfiles/Containerfiles and rewrite them to `FROM image:tag@sha256:<digest>`.
2. Open PRs when the upstream digest changes (the tag itself is unchanged — digest pinning tracks content drift under a stable tag).
3. Label those PRs as `updateType: digest` updates — distinct from `minor`/`major` version bumps.

Registries supported and tested against bootc-relevant images (as of Renovate v37+):
- `ghcr.io` — full support, no extra config needed. Renovate reads the OCI manifest index and resolves per-arch digests. Handles `ucore-hci:stable-nvidia` correctly.
- `quay.io` — full support. Handles `fedora/fedora-bootc:rawhide` and `centos-bootc/bootc-image-builder:latest`.
- `docker.io` — full support (default registry).

Authentication for private registries: set `hostRules` with `username`/`password` or GitHub PAT in Renovate config or as a repository secret (`RENOVATE_TOKEN`). For `ghcr.io`, Renovate's GitHub App installation requires `packages: read` permission.

**Key known limitation:** The `docker` datasource resolves digests to the manifest list (multi-arch) digest by default. For single-arch digest pinning (e.g., `linux/amd64` only), use `versioning: docker` with a `registryUrl` override. For MiOS this is not an issue — pinning the manifest list digest is the correct behavior for multi-arch base images.

**`config:best-practices` preset** (already used in this repo) bundles:
- `docker:pinDigests` — pins FROM digests in Dockerfiles and Containerfiles
- `helpers:pinGitHubActionDigests` — pins `uses:` in GitHub Actions workflows to SHA digests
- Various security and automerge defaults
- As of Renovate v38+, also enables `docker:enableDockerSecurity` which enforces signed-image awareness

### stabilityDays / stability window config

`stabilityDays` delays Renovate from opening (or automerging) a PR until the update has been available in the registry for N calendar days. This is a **release-age gate**, not a test gate.

**How it is evaluated:** Renovate uses the image manifest's `created` timestamp (from the OCI config blob) or the registry's push timestamp to compute age. For digest updates, the timestamp of the new digest is used. The PR is created only after `now - timestamp >= stabilityDays`.

**Interaction with `automerge`:**
- If `automerge: true` and `stabilityDays: 7`, Renovate creates the PR immediately but does not merge it until the 7-day window passes AND all required checks pass.
- If the registry timestamp is unavailable (some quay.io tags, `:latest` on some registries), `stabilityDays` has no effect — the PR opens immediately. This is a known edge case; mitigation is to pin to a versioned tag or semver tag rather than `:latest`.

**`minimumReleaseAge` replaces `stabilityDays` (forward-compatible form):** Renovate's documentation prefers `minimumReleaseAge` (with time-unit suffix, e.g., `"7 days"`) over the integer `stabilityDays`. Both work as of mid-2025, but `minimumReleaseAge` is the forward-compatible canonical form. The current repo's `stabilityDays: 7` and `stabilityDays: 3` are functionally correct but should be migrated to `minimumReleaseAge: "7 days"` / `minimumReleaseAge: "3 days"` when next the `renovate.json` is touched.

**Current repo config analysis (`renovate.json`):**
- Global `stabilityDays: 7` applies to all non-digest updates.
- `matchUpdateTypes: ["digest"]` rule overrides to `stabilityDays: 3` — appropriate because digest updates are low-risk (same tag, new content) and the 3-day window is sufficient to catch registry mistakes.
- `matchFileNames: ["image-versions.yml"]` disables automerge and assigns `MiOS-DEV` as reviewer — correct for protecting digest pins that feed the production build.

**Recommended tuning for bootc projects:**
- Keep 7 days (or `"7 days"`) for version bumps (`minor`, `major`, `patch`).
- Use 3 days for `digest` updates — `ucore-hci:stable-nvidia` digest changes weekly as Universal Blue rebuilds; 7 days would cause perpetual lag.
- Use 0 days for `lockFileMaintenance` — dependency lock file refreshes have no deployment risk.
- Add `schedule: ["before 6am on monday"]` to the `matchUpdateTypes: ["digest"]` rule to batch digest PR creation out of work hours.

### Digest pinning for Containerfile FROM

**How `docker:pinDigests` works on Containerfiles:** Renovate scans for `FROM` directives using the `dockerfile` manager. It detects both standard `FROM image:tag` and multi-stage `FROM image:tag AS alias` patterns. After pinning, the line becomes:

```dockerfile
FROM {{MIOS_BASE_IMAGE}}@sha256:<digest>
```

Renovate then tracks this digest and opens a PR when `stable-nvidia` resolves to a new digest. The PR diff is a single-line change to the `sha256:` value.

**Behavioral notes:**
- Renovate does NOT pin `FROM scratch` — correctly skipped.
- In multi-stage builds, each `FROM` line is pinned independently. MiOS's `FROM scratch AS ctx` is skipped; the main `FROM {{MIOS_BASE_IMAGE}}` is pinned.
- If the Containerfile already has `@sha256:` pinning, Renovate tracks the existing pin and updates it — it does not double-pin.
- The `dockerfile` manager auto-detects files named `Dockerfile`, `Containerfile`, `Dockerfile.*`, `Containerfile.*`. The repo's root `Containerfile` is automatically detected with no extra `fileMatch` config needed.

**Current state in this repo:** `image-versions.yml` documents the digests as reference, but the `Containerfile` currently uses bare tags (per the `image-versions.yml` comment: "the Containerfile currently uses tags"). This means Renovate is tracking the tag for version updates but is NOT currently pinning the Containerfile `FROM` line to a specific digest. To activate full digest pinning:

1. Get the current digest: `podman manifest inspect {{MIOS_BASE_IMAGE}} | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Digest') or d['manifests'][0]['digest'])"`
2. Update the `FROM` line in `Containerfile` to `FROM {{MIOS_BASE_IMAGE}}@sha256:<digest>`.
3. Renovate will detect the pinned digest and begin managing it automatically going forward.
4. Uncomment and populate the `digest:` field in `image-versions.yml` to match.

**CODEOWNERS protection pattern (Universal Blue / Bluefin):**
```
image-versions.yml  @MiOS-DEV
Containerfile       @MiOS-DEV
```
The `renovate.json` already handles this via `automerge: false` + `assignees: ["MiOS-DEV"]` for `image-versions.yml`. Add a matching `packageRule` for `matchFileNames: ["Containerfile"]` once digest pinning is activated there.

### image-versions.yml pattern

The `image-versions.yml` pattern originates from **Bluefin** and is standard across the Universal Blue ecosystem. The canonical connection between a plain YAML value and a Renovate-tracked image is a **`# renovate:` directive comment** on the line immediately above the YAML key:

```yaml
# renovate: datasource=docker depName=ghcr.io/ublue-os/ucore-hci
base_image_digest: sha256:abc123...
```

When Renovate sees this comment above a key whose value is a `sha256:` digest (or a tag string), it updates the value when the upstream image changes. Without the directive comment, Renovate does not know which registry/image a plain YAML value corresponds to.

**Recommended `image-versions.yml` structure for MiOS:**

```yaml
# MiOS base image version pinning
# Managed by Renovate Bot — do NOT edit digests manually.
# Renovate opens PRs when upstream images publish new digests.
# See renovate.json for stability window and automerge policy.

# renovate: datasource=docker depName=ghcr.io/ublue-os/ucore-hci
ucore_hci_stable_nvidia_digest: sha256:REPLACE_WITH_CURRENT_DIGEST

# renovate: datasource=docker depName=quay.io/fedora/fedora-bootc versioning=docker
fedora_bootc_rawhide_digest: sha256:REPLACE_WITH_CURRENT_DIGEST

# renovate: datasource=docker depName=quay.io/centos-bootc/bootc-image-builder
bib_digest: sha256:REPLACE_WITH_CURRENT_DIGEST

# renovate: datasource=docker depName=quay.io/centos-bootc/centos-bootc versioning=docker
rechunker_digest: sha256:REPLACE_WITH_CURRENT_DIGEST
```

**`regexManagers` alternative:** For more complex YAML structures (e.g., nested `registry`/`tag`/`digest` keys as in the current `image-versions.yml`), use `regexManagers` in `renovate.json` to extract the digest via regex. Example:

```json
{
  "regexManagers": [
    {
      "fileMatch": ["^image-versions\\.yml$"],
      "matchStrings": [
        "repository: (?<depName>[^\\n]+)\\n\\s+tag: (?<currentValue>[^\\n]+)\\n\\s+# digest: sha256:(?<currentDigest>[^\\n]+)"
      ],
      "datasourceTemplate": "docker"
    }
  ]
}
```

The simpler directive-comment pattern is recommended for new YAML structures. The current `image-versions.yml` nested structure would need either a `regexManager` or restructuring to the flat key-value form before Renovate can manage the digest fields automatically.

### Notable Renovate changes 2025-2026

Knowledge cutoff: August 2025 (confirmed). Items marked [INFERRED] are trajectory-based.

**Confirmed changes (Renovate v36–v38, 2024–mid-2025):**

- **`config:best-practices` formalized (v37, late 2024):** This preset now bundles `docker:pinDigests`, `helpers:pinGitHubActionDigests`, and security-hardened defaults. Repos extending it automatically get all three behaviors. This repo already uses it correctly.

- **`dockerfile` manager gains Containerfile support (v37–v38):** Bootc projects no longer need `fileMatch` overrides to detect root-level `Containerfile` — it is auto-detected alongside `Dockerfile`.

- **Per-rule `stabilityDays` (v37+):** `stabilityDays` can now be set per `matchUpdateTypes` inside `packageRules`, which is exactly what this repo's `renovate.json` uses. Before ~v36 it was global only.

- **`minimumReleaseAge` preferred over `stabilityDays` (v38+):** Renovate docs now prefer `minimumReleaseAge: "7 days"` (string with time unit) over `stabilityDays: 7` (integer days). Both work; `minimumReleaseAge` is the forward-compatible form. Plan to migrate when next touching `renovate.json`.

- **`automergeSchedule` deprecated → use `schedule` (v37+):** These are unified under `schedule` within `packageRules`. The repo's `schedule: ["before 9am on monday"]` for GitHub Actions is correct current syntax.

- **`docker:enableDockerSecurity` preset (v38+):** Added — pins digest AND flags unsigned images in the PR description when combined with `docker:pinDigests`. Consider adding this preset once MiOS cosign signing infrastructure is confirmed stable.

- **GitHub Actions pinning extended (v38+):** `helpers:pinGitHubActionDigests` now also pins composite action `uses:` references inside workflow files, not just top-level job steps. MiOS CI workflows benefit from this automatically.

- **OCI artifact tracking (v38+):** Renovate added support for non-image OCI objects (Helm charts, Sigstore policy bundles pushed as OCI). Uses same `docker` datasource. Relevant if MiOS begins tracking cosign key bundles or attestations as OCI artifacts.

- **`hostRules` for ghcr.io (2025 change):** GitHub Actions token scoping changed. Renovate running as a GitHub App requires `packages: read` permission on the installation to pull manifests from `ghcr.io`. Verify the Renovate App installation has this scope on the `mios-project/mios` repo.

**Action items for this repo's `renovate.json`:**

1. Migrate `stabilityDays: 7` → `minimumReleaseAge: "7 days"` and `stabilityDays: 3` → `minimumReleaseAge: "3 days"` for forward compatibility.
2. Add `schedule: ["before 6am on monday"]` to the `matchUpdateTypes: ["digest"]` rule to batch digest PR creation.
3. Add a `packageRules` entry for `matchFileNames: ["Containerfile"]` with `automerge: false` + `assignees: ["MiOS-DEV"]` once FROM digest pinning is activated in the Containerfile.
4. Restructure or add a `regexManagers` block so Renovate can automatically manage the `digest:` fields in `image-versions.yml` (currently commented out and untracked by Renovate).
5. Consider adding `vulnerabilityAlerts: { enabled: true }` at the top level — Renovate 2025+ can open CVE-driven PRs for pinned images when a vulnerability database feed is configured.
6. Verify the Renovate GitHub App installation has `packages: read` scope for GHCR manifest resolution.
<!-- FINDINGS END -->

---

## 12. Security / SELinux / CrowdSec

*Research thread: SELinux bootc patterns, CrowdSec 2026 features, fapolicyd*

<!-- FINDINGS BEGIN -->
### SELinux in bootc / immutable images

**Core constraint:** `/usr` is read-only in composefs mode. SELinux contexts on `/usr` binaries cannot be modified at runtime via `restorecon`. All labels must be correct at image build time.

**Build-time labeling:** During the container build (`dnf install`), RPM package scriptlets run `restorecon` on installed files. For correctly packaged RPMs this is sufficient. For custom files added via `COPY` or system_files overlay:
```dockerfile
RUN restorecon -RFv /usr/libexec/mios/ \
 && restorecon -RFv /usr/lib/systemd/system/mios-*.service
```
Add this after the system_files overlay step in Containerfile if SELinux context mismatches appear at boot.

**Bind-mount + restorecon pattern:** For fixing labels on immutable binaries without a full rebuild, bind-mount the specific file from a writable layer, fix the context, then unmount. This is for emergency use only — prefer fixing the image.

**SELinux enforcing + composefs verity:** Both can be active simultaneously. composefs verity verifies content integrity (cryptographic); SELinux enforces access control (MAC). They do not conflict. bootc v0.1.1 added SELinux enforcement for sealed images.

**Sealed image SELinux (bootc v1.14+):** When `composefs.enabled = signed` (not just verity), bootc can enforce SELinux policy from the image itself during the pivot-root stage — before `init` starts. This prevents policy tampering via writable `/etc`. MiOS uses `verity` (not `signed`) — upgrade to `signed` for maximum hardening when Fedora CI is ready for it.

### fapolicyd in immutable images

**New canonical rule directory (from OL 9.7 / Fedora ≥ fapolicyd-1.3):**
- Rules go in `/etc/fapolicyd/rules.d/` (numbered files, assembled by `fagenrules`)
- `/etc/fapolicyd/fapolicyd.rules` is **deprecated** — do not create it
- `fagenrules --load` compiles rules from `rules.d/` to `compiled.rules`

**Trust database in bootc:**
- fapolicyd builds its trust DB from the RPM database at startup
- Since the RPM database is in the immutable `/usr` layer (composefs), trust DB is consistent with the image
- Any binary added outside of RPM (e.g., custom scripts in `/usr/libexec/mios/`) must be explicitly trusted:
  ```bash
  fapolicyd-cli --file add /usr/libexec/mios/role-apply
  ```
  Or add to `/etc/fapolicyd/trust.d/mios.trust`:
  ```
  /usr/libexec/mios/role-apply sha256:<hash>
  ```
- `47-hardening.sh` already calls `fagenrules --load && fapolicyd-cli --update` at build time

**MiOS fapolicyd status check:** All scripts in `usr/libexec/mios/` now have 0755 mode (fixed April 2026). Verify fapolicyd trust after the mode fix by regenerating trust DB in next build.

### CrowdSec / Metabase dashboard (Podman Quadlet)

**CrowdSec setup for Podman:**
```bash
systemctl enable --now podman.socket
export DOCKER_HOST=unix:///run/podman/podman.sock
cscli dashboard setup
```

**Quadlet pattern (corrected in April 2026 fix):**
```ini
[Unit]
ConditionVirtualization=!wsl    # Skip in WSL2

[Container]
Image=docker.io/crowdsecurity/metabase:latest
ContainerName=crowdsec-dashboard
PublishPort=3000:3000
Volume=crowdsec-data.volume:/metabase-data
AutoUpdate=registry

[Service]
Restart=on-failure              # Was: always (caused restart loop)
RestartSec=30
TimeoutStartSec=300
```

**CrowdSec enrollment:** CrowdSec dashboard (Metabase) requires the main crowdsec service to be enrolled with the Central API before it's useful. The Quadlet `Restart=on-failure` with 30s delay prevents the restart loop while enrollment is pending.

**Firewall bouncer:** `crowdsec-firewall-bouncer` works with `nftables` by default in Fedora 44+ (firewalld backend). Ensure `firewalld` is using `nftables` backend (default in F44). No special config needed — mios `20-services.sh` enables `crowdsec-firewall-bouncer`.

**CrowdSec engine version (as of 2026-04-20):** **v0.1.1** (released March 23, 2026). The 1.7.x series switched regex engine to **RE2** — noticeably faster matching, with slightly slower regex *compile* and a small baseline memory uptick (acceptable tradeoff for a workstation/server IDS). Adds a new `kind` attribute on alerts for source identification and a **polling API** that lets the CrowdSec Console send remote decision-management orders to engines. MiOS is not pinning a specific crowdsec version — it inherits whatever Fedora/COPR ships, which is fine; flag if an explicit version pin becomes necessary.

### USBGuard configuration requirements

**Critical:** `usbguard-daemon.conf` must have permissions **0600** (root-readable only). The usbguard daemon explicitly checks and refuses to start if the file is group- or world-readable.

- MiOS system_files delivers it as git mode 100644 → 0644 on disk (fixed in `47-hardening.sh` April 2026: `chmod 0600` before `systemctl enable`)
- Alternative long-term fix: use `tmpfiles.d` to set permissions:
  ```
  z /etc/usbguard/usbguard-daemon.conf 0600 root root -
  ```
  This runs at boot via `systemd-tmpfiles-setup.service` and ensures the permission is re-applied even if something changes it.

### auditd in WSL2

- WSL2 kernel does NOT include the Linux audit subsystem (`CONFIG_AUDIT` not compiled in Vendor's WSL kernel)
- auditd fails with `NOPERMISSION` at every start in WSL2
- Fix: `ConditionVirtualization=!wsl` in `auditd.service.d/10-mios-wsl2.conf` (already shipped)
- Same fix for `audit-rules.service.d/10-mios-wsl2.conf`
- On bare metal: auditd works normally; SELinux uses the audit subsystem for denials logging

### Supply chain / hardening summary for MiOS

| Layer | Mechanism | Status |
|-------|-----------|--------|
| Image signing | cosign keyless (Fulcio/Rekor) | ✅ Operational (`build-sign.yml`) |
| SBOM | syft SPDX-JSON + CycloneDX | ✅ Fixed glob (`build.yml` April 2026) |
| Policy enforcement | containers/policy.json + ublue cosign pub key | ✅ Shipped in system_files |
| Composefs verity | ext4 + fsverity per-file verification | ✅ Active (`40-composefs-verity.sh`) |
| SELinux enforcing | Fedora default; composefs-compatible | ✅ Active |
| USBGuard | usbguard-daemon.conf 0600 | ✅ Fixed (April 2026) |
| fapolicyd | RPM trust + custom trust for /usr/libexec/mios | ⚠️ Verify trust DB after exec bit fix |
| CrowdSec | Sovereign IDS + nftables bouncer | ✅ Enabled (WSL2 gated) |
| MOK / Secure Boot | Universal Blue akmods-ublue.der | ✅ Enrolled via enroll-mok.sh |

### 2026-04-25 update — CVE-2026-4631 (Cockpit unauthenticated RCE, CVSS 9.8) ⚠️

**Critical** vulnerability published 2026-04-10 affecting **Cockpit ≥ 327 and < 360**:

- **Vector:** Cockpit's remote-login feature passes user-supplied hostnames + usernames to the SSH client without sanitization. Attacker with network access to Cockpit's web service (port 9090 by default) can craft a single HTTP request to the login endpoint that injects malicious SSH options or shell commands → **unauthenticated RCE on the Cockpit host**. Trigger occurs *before* credential verification.
- **Affected vector requires:** Cockpit 327–359 + OpenSSH **older than 9.6**.
- **Fix:** Cockpit **360** (released 2026-04-08); patched stable backports: 360.1 (Apr 14), 356.1 (Apr 13).
- **CVE / advisory IDs:** CVE-2026-4631 / GHSA-rq49-h582-83m7 / RHSA-2026:7384.
- **CVSS:** 9.8 base (network, low-complexity, no privilege, no UI).

**MiOS exposure analysis:** ucore-hci `stable-nvidia` currently tracks Fedora 42 stable, which historically ships an older Cockpit. After F44 rebase (April 28, 2026) Cockpit 360+ becomes available. **Action required for MiOS — see NEXT-RESEARCH.md.**

**Mitigations until F44 rebase:**
1. Disable remote-login: `LoginTo = false` in `/etc/cockpit/cockpit.conf` (or ship via `usr/lib/cockpit/cockpit.conf`).
2. Restrict port 9090 with firewalld to trusted management networks.
3. Confirm OpenSSH ≥ 9.6 in the image (Fedora 42 ships ≥ 9.7 since DRR; verify in `99-postcheck.sh`).

### 2026-04-25 update — CVE-2026-39395 = GHSA-w6c6-c85g-mmv6 (cosign DSSE)

CVE assignment confirmed for the cosign verify-blob-attestation false-positive flaw fixed in v0.1.1 / v0.1.1 (April 6, 2026). **MiOS already pinned to v0.1.1** — see Section 8 update for full detail. No action required.

### 2026-04-25 update — CrowdSec timeline still 1.7.x; no v0.1.1

Confirmed via github.com/crowdsecurity/crowdsec/releases: latest tag remains **v0.1.1** (March 30, 2025 — note this date is exactly 13 months stale, but no v0.1.1 RC has been cut). The 1.7.x line is therefore the long-running stable for the foreseeable future. No CVEs against engine 1.7.x in 2026 to date. The MiOS guidance (inherit Fedora/COPR-shipped version, no explicit pin) remains correct. Re-check this once a v0.1.1 timeline is published.
<!-- FINDINGS END -->

---

## 13. Desktop Stack — GNOME 50.x / Wayland

*Research thread (added 2026-04-25): GNOME 50 bugfix series, NVIDIA-related Mutter regressions, gnome-remote-desktop maturity*

<!-- FINDINGS BEGIN -->
### GNOME 50 bugfix series

- **GNOME 50** released March 2026 (stable). MiOS migrated from xRDP → `gnome-remote-desktop` for headless RDP support in v0.1.1 (April 22, 2026).
- **GNOME 50.1** released **2026-04-15** — first bugfix release. Notable fixes:
  - **Mutter performance regression with several NVIDIA driver versions resolved** (Mutter 50.1). High-impact for MiOS `stable-nvidia` users on Ada/Blackwell.
  - GTK4 → v0.1.1; GTK3 → v0.1.1.
  - On-screen keyboard fits very small screens.
  - Lock-screen network agent enabled by default.
  - Captive-portal basic zoom support.
  - Memory leak in shell process fixed.
- **GNOME 50.2** not yet released as of 2026-04-25 (typical 6-week cadence → expect ~late May 2026).

**MiOS implication:** ucore-hci pulls GNOME from Fedora; F44 will ship GNOME 50.1+ at release (April 28, 2026). The post-rebase image automatically picks up the NVIDIA Mutter fix. **No MiOS action required.** Track GNOME 50.2 and Mutter changelog for any new gnome-remote-desktop session-handling regressions.

### gnome-remote-desktop status (2026)

- `grdctl` is the canonical CLI for headless RDP/VNC config (replaces gsettings drudgery).
- F44 ships `gnome-remote-desktop` ≥ 50.x — supports both GDM-pre-login and per-user sessions.
- MiOS already migrated `xrdp`/`xorgxrdp-glamor` → `gnome-remote-desktop` + `26-gnome-remote-desktop.sh` (verified 2026-04-21).
- Known watchpoint: `gnome-remote-desktop-daemon.service` requires PipeWire socket + a running compositor; ensure the headless target keeps GDM enabled in role `desktop` and `headless-remote`.
<!-- FINDINGS END -->

---

## 14. Waydroid / Android Emulation

*Research thread (added 2026-04-25): Waydroid release cadence, NVIDIA support status, GAPPS init*

<!-- FINDINGS BEGIN -->
### Waydroid status (April 2026)

- Active development; main repo last commit late March 2026, supporting repos active early April 2026.
- **No formal "1.5" tagged release** — Waydroid still does rolling main-branch releases via Fedora COPR / Arch.
- **GAPPS:** Not bundled by default; opt-in via `waydroid init -s GAPPS -f`. MiOS `mios-waydroid-init.service` already passes `-s GAPPS`.
- **NVIDIA support:** Status unchanged from prior pass — known-flaky. Two community workarounds remain:
  1. Use a VM with virtio-gpu + 3d acceleration (EGL-headless Spice/SDL display) — works on hosts with NVIDIA proprietary drivers.
  2. Disable GBM and Mesa drivers system-wide before launching Waydroid. **Not recommended for MiOS** because it would break the rest of the GNOME 50 / Wayland stack.
- Some users on `stable-nvidia` (NVIDIA 595+) report Waydroid GAPPS image now boots without modification, but this is anecdotal and inconsistent across kernel/driver combos.

**MiOS guidance:** `38-vm-gating.sh` already gates `waydroid-container.service` with `ConditionPathExists=!/proc/sys/fs/binfmt_misc/WSLInterop`. On bare-metal NVIDIA hosts, leave Waydroid available but document the known-limited GPU acceleration. No CDI device-assignment path for Waydroid yet — track upstream issue #1883 for changes.
<!-- FINDINGS END -->

---

*End of live research document.*

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
