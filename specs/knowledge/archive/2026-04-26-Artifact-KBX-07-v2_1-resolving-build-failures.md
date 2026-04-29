<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
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

# MiOS v0.1.1: resolving every build and boot failure

**The Hyper-V Gen2 boot hang is almost certainly caused by GNOME 50's complete removal of the X11 backend colliding with xorgxrdp Enhanced Session Mode**, creating a GDM crash loop that prevents the system from ever reaching a login prompt. This single architectural incompatibility — Mutter 50 is Wayland-only, xorgxrdp requires X11 — explains why the kernel boots fine but the system never reaches userspace. Secondary contributing factors include potentially missing Hyper-V dracut modules in the initramfs and possible plymouth-masking dependency deadlocks. The remaining issues (lint warnings, service ordering, BIB GPG failures, memory alignment) are all solvable with targeted fixes documented below.

---

## The Mutter 50 X11 removal breaks Enhanced Session completely

The single most important discovery is that **GNOME 50 / Mutter 50 completely removes the X11 backend**. This is not a deprecation — the entire X11 code path is gone. Since xorgxrdp is fundamentally an X11 technology that creates virtual Xorg sessions for RDP clients, it cannot function under Wayland-only Mutter 50. The boot hang sequence plays out like this:

1. Kernel loads successfully (hyperv_drm, EXT4, modules — all visible in the log through ~6.9s)
2. systemd starts services, reaches `graphical.target`
3. GDM 50 launches, attempts to start a Wayland session via Mutter 50
4. xrdp/xorgxrdp services try to initialize but find no X11 backend available
5. GDM/gnome-shell crashes, restarts, crashes again — an infinite restart loop
6. The system never reaches a login prompt

This diagnosis is reinforced by community reports confirming that **"any distro running Wayland-only Desktop interface such as GNOME 49+ will not be able to take advantage of the XRDP Software package."** The hyperv_drm driver compounds the issue: while it supports Wayland compositing via KMS modesetting, it lacks a Mesa 3D userspace driver (`hyperv_drm_dri.so` does not exist), which can cause gnome-shell compositor failures when GPU-accelerated rendering is attempted.

**Immediate fix — boot with `systemd.unit=multi-user.target`** to bypass GDM entirely and confirm the diagnosis. If the system reaches a text login, GDM/xorgxrdp is confirmed as the culprit. The permanent solutions are:

- **Disable xrdp services**: `systemctl mask xrdp xrdp-sesman` and switch to GNOME Remote Desktop (`gnome-remote-desktop`), which is Wayland-native and supports RDP natively
- **Use `gnome-remote-desktop` for Enhanced Session**: This is the forward-looking approach — it works with Wayland and can bind to `vsock` for Hyper-V transport
- **Alternatively, switch to XFCE or MATE** for the Hyper-V target, as these desktops still support X11

## Missing dracut modules and plymouth masking are secondary hang causes

Even if the GDM/xorgxrdp issue is resolved, two other problems can cause Hyper-V boot hangs. **First, the initramfs may lack critical Hyper-V kernel modules.** A confirmed Fedora 43 Hyper-V boot failure was traced to `hv_storvsc` (synthetic SCSI controller) being absent from the initramfs — without it, the VM cannot detect its virtual disk and hangs indefinitely. Since MiOS builds from `ucore-hci:stable-nvidia`, the base image's dracut configuration may not include Hyper-V modules unless explicitly configured.

Add this to the Containerfile to guarantee multi-surface boot support:

```dockerfile
RUN echo 'hostonly="no"' > /usr/lib/dracut/dracut.conf.d/10-generic.conf
RUN echo 'add_drivers+=" hv_vmbus hv_netvsc hv_storvsc hv_utils hv_balloon hv_sock hid-hyperv hyperv_keyboard hyperv_drm "' > /usr/lib/dracut/dracut.conf.d/50-hyperv.conf
RUN echo 'add_drivers+=" virtio_blk virtio_net virtio_scsi virtio_pci "' > /usr/lib/dracut/dracut.conf.d/51-virtio.conf
RUN set -xe; kver=$(ls /usr/lib/modules); \
    env DRACUT_NO_XATTR=1 dracut -vf /usr/lib/modules/$kver/initramfs.img "$kver"
```

**Setting `hostonly="no"` is critical** — it generates a generic initramfs with broad driver support rather than one tailored to the build host's hardware.

**Second, masking plymouth creates a potential systemd dependency deadlock.** If `display-manager.service` symlinks to `gdm-plymouth.service` (rather than `gdm.service`), or if any systemd unit carries a hard `Requires=` or `After=` dependency on `plymouth-quit-wait.service`, the masked units create an unfulfillable dependency chain. Verify with `systemctl cat display-manager.service` and check for plymouth ordering. Consider adding `plymouth.enable=0` to the kernel command line instead of masking, which cleanly tells plymouth to no-op without breaking dependency resolution. Also add **NVIDIA module conditional loading** — when booting in Hyper-V without GPU passthrough, nvidia kernel modules probe for non-existent hardware and may delay boot. Use `systemd-detect-virt` (returns `microsoft` for Hyper-V) in a first-boot service to conditionally blacklist nvidia modules.

## Additional diagnostic steps to pinpoint the hang

If the GDM fix alone doesn't resolve the issue, these additional kernel boot parameters isolate other potential causes:

- **`enforcing=0`** — rules out SELinux policy mismatches causing silent service failures (bootc images can have incorrect SELinux labels if the build environment differs from the deployment target)
- **`ostree.prepare-root.composefs=0`** — rules out composefs mount failures, which are documented to cause "failed to mount" errors during ostree-prepare-root on certain upgrade paths
- **`systemd.log_level=debug`** combined with a serial console (`console=ttyS0,115200n8`) — captures exactly which systemd unit is blocking boot
- **`systemctl list-jobs`** via serial console during the hang — shows all pending/waiting jobs and identifies the deadlocked unit

## Lint warnings are non-fatal today but will become errors

The three lint warnings — `var-log` (dnf5.log), `var-tmpfiles` (k3s manifests), and non-directory files in `/var` — **do not currently break bootc deployments** but represent real semantic issues. The bootc team is actively moving toward making these fatal at install time (tracked in bootc issue #960). The underlying problem is that `/var` in bootc follows Docker VOLUME semantics: **content is unpacked only on initial installation and is never updated by subsequent `bootc update` operations.** This means k3s manifests shipped in `/var/lib/rancher/k3s/server/manifests/` will be frozen at the version from first install.

The fixes are straightforward. For build artifacts, add a cleanup block at the end of the Containerfile:

```dockerfile
RUN dnf clean all && \
    rm -f /var/log/dnf5.log && \
    rm -rf /var/cache/ldconfig && \
    bootc container lint
```

For k3s manifests, the correct bootc pattern is to **move versioned content to `/usr`** and use a symlink or first-boot copy service:

```dockerfile
RUN mkdir -p /usr/share/k3s/server/manifests && \
    mv /var/lib/rancher/k3s/server/manifests/*.yaml /usr/share/k3s/server/manifests/
```

Then create a tmpfiles.d entry for the directory structure and a first-boot service that copies or symlinks manifests from `/usr/share/` to `/var/lib/rancher/`. This ensures manifests update with the OS image rather than being frozen at initial install. Alternatively, if first-install-only semantics are acceptable, add tmpfiles.d entries to silence the lint:

```dockerfile
RUN cat > /usr/lib/tmpfiles.d/k3s-dirs.conf << 'EOF'
d /var/lib/rancher 0755 root root - -
d /var/lib/rancher/k3s 0755 root root - -
d /var/lib/rancher/k3s/server 0755 root root - -
d /var/lib/rancher/k3s/server/manifests 0755 root root - -
EOF
```

## The Flatpak service enable fails because of Containerfile ordering

The `10-gnome.sh` script calling `systemctl enable mios-flatpak-install.service` fails because the unit file lives in `` which gets `COPY`'d in a later Containerfile step. **`systemctl enable` only creates symlinks — it requires the unit file to exist at that moment.** This is a classic ordering bug with three clean fixes:

**Option A (simplest):** Move `COPY  /` before the `RUN automation/` step so unit files exist when `systemctl enable` runs.

**Option B (Bluefin-style):** Use a multi-stage build with `--mount=type=bind`:
```dockerfile
FROM scratch AS ctx
COPY  /system_files
COPY automation/ /scripts

FROM ${BASE_IMAGE}
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    cp -r /ctx/* / && /ctx/automation/10-gnome.sh
```

**Option C (explicit post-COPY enable):** Remove the `systemctl enable` from `10-gnome.sh`, keep the COPY where it is, then add a separate step:
```dockerfile
RUN automation/10-gnome.sh
COPY  /
RUN systemctl enable mios-flatpak-install.service
```

For the Flatpak installation itself, **every major Universal Blue project uses first-boot systemd services, never build-time embedding.** Bazzite uses `bazzite-flatpak-manager.service` with version tracking for idempotency. Bluefin uses `brew-setup.service` with lists in `/etc/preinstall.d/`. None embed Flatpaks at container build time because Flatpak data installs to `/var/lib/flatpak`, which has the same Docker VOLUME semantics — updates would never propagate.

## BIB's Terra GPG failure is a confirmed upstream bug

The ISO build failure (`Could not read a file:// file for file:///etc/pki/rpm-gpg/RPM-GPG-KEY-terra44`) is **a confirmed bug tracked as bootc-image-builder issue #1188**, filed January 2026 and still open. The root cause: BIB's depsolve runs in an isolated build environment, not inside the source container image. When BIB reads repo files from the container's `/etc/yum.repos.d/`, it finds `gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-terra44`, but the `file://` path resolves against BIB's own filesystem where that key doesn't exist.

**The critical insight is that STEP 11's repo disabling happens on the host, not inside the container image.** Repos must be disabled inside the container during `podman build`:

```dockerfile
# After installing all packages from Terra repos
RUN dnf config-manager --set-disabled 'terra*' || \
    find /etc/yum.repos.d/ -name '*terra*' -exec sed -i 's/enabled=1/enabled=0/g' {} \;
```

An alternative approach is switching from `--type anaconda-iso` to `--type iso`, which takes the container image and makes it directly bootable without Anaconda's depsolve step. This requires `dracut-live` and `squashfs-tools` installed in the image with the `dmsquash-live` dracut module enabled, but it completely sidesteps the GPG key issue.

## Self-building without BIB is possible for disk images

**BIB is designed exclusively as a container tool and cannot be installed as an RPM.** Its dependencies (osbuild, Go toolchain, depsolve infrastructure) are substantial, and running BIB inside the image it's building creates a circular dependency. However, self-building is achievable through alternative paths:

- **`bootc install to-disk`** is already available in every bootc image and creates raw disk images directly — no external tooling needed. It does not require depsolve or repo access. This handles bare metal and VM disk image creation.
- **`bootc install to-filesystem`** provides more flexibility for custom partition layouts and is what both Anaconda and BIB use internally.
- **osbuild (which IS installed)** executes build pipelines but cannot replace BIB because it requires hand-crafted JSON manifests — it doesn't generate them.
- **image-builder CLI** (from the `@osautomation/image-builder` COPR) is installable as an RPM and is expected to merge with BIB eventually. It supports `--force-data-dir` for custom repo configurations but currently focuses on traditional package-based inputs rather than bootc containers.

For ISO generation specifically, continue using the external BIB container (`quay.io/centos-bootc/bootc-image-builder:latest`). For raw disk images, `bootc install to-disk` provides true self-building capability today.

## Hyper-V memory must align to 2 MB boundaries

The `Set-VM` error ("Invalid memory value assigned ('47759' MB) is not properly aligned") occurs because **Hyper-V requires all memory values to be divisible by 2 MB**. The value 47759 is odd and fails this check. Round to **47758 MB or 47760 MB**. This applies to startup memory, minimum memory, and maximum memory for dynamic memory configurations. The fix in deployment scripts should be:

```powershell
$AlignedMemoryMB = [math]::Floor($DesiredMemoryMB / 2) * 2
Set-VM -Name $VMName -MemoryStartupBytes ($AlignedMemoryMB * 1MB)
```

## Conclusion

The boot hang has a clear primary cause (**Mutter 50's X11 removal killing xorgxrdp**) with two reinforcing factors (missing Hyper-V dracut modules and plymouth dependency deadlocks). The fix strategy is: replace xorgxrdp with `gnome-remote-desktop` for Wayland-native RDP, add explicit Hyper-V drivers to the initramfs via dracut drop-ins with `hostonly="no"`, and use kernel-parameter plymouth disabling instead of service masking. The BIB GPG failure is a known upstream bug solvable by disabling Terra repos *inside* the container image, not on the host. The lint warnings require moving versioned content from `/var` to `/usr` and adding a build-time cleanup step. The Flatpak service ordering is fixed by restructuring the Containerfile to COPY unit files before enabling them, following Bluefin's multi-stage bind-mount pattern. Together, these changes should produce a MiOS image that boots reliably across all five target surfaces.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
