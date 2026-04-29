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

# Building MiOS: a complete technical intelligence report

**The bootc ecosystem has matured dramatically through 2025-2026, and your MiOS project can now leverage battle-tested patterns from Universal Blue, SecureBlue, and the CNCF-sandboxed bootc project itself.** Bootc reached **v0.1.1** (March 2026) with composefs-native storage, tag-aware upgrades, and kernel argument drop-in directories. Fedora Rawhide now ships **kernel 7.0-rc6**, **systemd 260**, **GNOME 50**, and **Mesa 26.0** — all requiring specific adaptations for immutable workstation builds. This report synthesizes findings across mature bootc repositories, security hardening techniques, GPU passthrough ecosystem changes, and container orchestration patterns to inform every layer of the MiOS architecture.

---

## Containerfile patterns from production bootc projects

Universal Blue's ecosystem — spanning main, Bazzite, Bluefin, Aurora, and SecureBlue — has converged on a remarkably consistent Containerfile architecture. Every major project uses a **multi-stage build with a `FROM scratch AS ctx` context stage** that consolidates build scripts and system files, preventing COPY layer bloat in the final image. The pattern looks like this:

```dockerfile
FROM scratch AS ctx
COPY build_files /
COPY system_files /

FROM ghcr.io/ublue-os/silverblue-main:${FEDORA_VERSION} AS base
RUN --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build_files/build.sh

RUN rm -rf /opt && ln -s /var/opt /opt
CMD ["/sbin/init"]
RUN bootc container lint
```

**Three BuildKit mount types** appear universally: `type=cache` for dnf/rpm-ostree caches (dramatically speeds rebuilds), `type=bind` from the context stage for build scripts, and `type=tmpfs` for transient build data. The `bootc container lint` command runs as the **final validation step** in every production Containerfile, catching common errors before images ship.

Package management has **fully migrated from rpm-ostree to dnf5** for container builds (since Fedora 42). Bazzite's Containerfile demonstrates sophisticated package management with a repository priority hierarchy — Copr repos at priority 1-3 for patched packages, Negativo17 at priority 4 for proprietary drivers, RPM Fusion at priority 5, and Fedora repos as the fallback. Critical packages get version-locked via `dnf5 versionlock add`, and **all third-party repositories are disabled after build** to prevent runtime package installation. A `validate-repos.sh` script runs at build completion to enforce this.

The `/opt → /var/opt` symlink pattern appears in every project, making `/opt` writable on the otherwise immutable filesystem. Configuration that should be immutable gets moved from `/etc` to `/usr/lib` with a symlink back — CentOS bootc demonstrates this with crypto-policies: `mv /etc/crypto-policies /usr/lib/crypto-policies && ln -sr /usr/lib/crypto-policies /etc/crypto-policies`.

Bluefin adds GitHub token injection via `--mount=type=secret,id=GITHUB_TOKEN` for accessing private resources during build. Bazzite's Containerfile exceeds **850 lines** and produces 10+ image variants from a single file using multi-stage targets (`bazzite`, `bazzite-deck`, `bazzite-nvidia`), selected via Docker's `--target` flag in CI.

---

## Image signing, supply chain security, and CI/CD workflows

Every production bootc project signs images with **cosign** using the sigstore framework. The Universal Blue ecosystem uses key-based signing with `COSIGN_PRIVATE_KEY` stored as a GitHub Actions secret, while SecureBlue adds **SLSA provenance verification** that cryptographically proves images were built on valid GitHub runners from commits in the live branch.

For MiOS, the recommended GitHub Actions workflow uses **keyless signing** with Fulcio/Rekor, which requires the `id-token: write` permission:

```yaml
permissions:
  contents: read
  packages: write
  id-token: write  # Enables OIDC keyless signing

steps:
  - uses: sigstore/cosign-installer@v0.1.1
  - name: Sign image (keyless)
    run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

The corresponding container policy at `/etc/containers/policy.json` should enforce sigstore signatures:

```json
{
  "default": [{"type": "reject"}],
  "transports": {
    "docker": {
      "ghcr.io/mios-project/mios": [{
        "type": "sigstoreSigned",
        "fulcio": {
          "caPath": "/etc/pki/cosign/fulcio_v1.crt.pem",
          "oidcIssuer": "https://token.actions.githubusercontent.com",
          "subjectEmail": "https://github.com/mios-project/mios/.github/workflows/build.yml@refs/heads/main"
        },
        "rekorPublicKeyPath": "/etc/pki/cosign/rekor.pub",
        "signedIdentity": {"type": "matchRepository"}
      }]
    }
  }
}
```

**Critical caveat**: bootc's `--enforce-container-sigpolicy` flag works on `bootc switch` and `bootc install` but **not yet on `bootc upgrade`** (issue #528). This gap remains open. Additionally, **Cosign v3's new bundle format** can break signature verification in the ostree/containers ecosystem — use `--new-bundle-format=false` or pin Cosign v2 until compatibility improves.

All upstream base images should be **pinned by SHA256 digest** in an `image-versions.yaml` file, with Renovate Bot automatically updating digests via pull requests. Bluefin's build testing script validates 11 critical packages via `rpm -q`, checks for "footgun" packages (packages that should not be present), and verifies systemd units are enabled — adopt this pattern for MiOS's CI.

Post-build, Universal Blue projects run **image rechunking**, converting container layers to OSTree commits optimized for efficient delta updates. This dramatically reduces update download sizes for end users.

---

## Bootc v0.1.1 and the composefs revolution

Bootc was accepted as a **CNCF Sandbox project on January 21, 2025**, and the repository moved from `containers/bootc` to **`bootc-dev/bootc`**. The project now follows strict semver and has reached v0.1.1 with transformative features.

The most significant development is the **composefs-native backend** (tracking issue #1190), which aims to phase out ostree as a dependency entirely. Composefs-rs (a Rust implementation) generates composefs images directly from container images, and the feature gate was removed in v0.1.1. Key milestones achieved include composefs garbage collection (v0.1.1), SELinux enforcement for sealed images (v0.1.1), and pre-flight disk space checks (v0.1.1). Configure it in `/usr/lib/ostree/prepare-root.conf`:

```toml
[composefs]
enabled = true        # Default: composefs without requiring fsverity

[etc]
transient = true      # Recommended: transient /etc for maximum immutability

[root]
transient-ro = true   # New: read-only overlay with privileged remount capability
```

New CLI capabilities since v0.1.1 include **kernel argument drop-in directories** at `/usr/lib/bootc/kargs.d/` (eliminating the need to modify bootloader configs), **soft reboot** that detects SELinux policy deltas for userspace-only restarts, `bootc usroverlay --readonly` for read-only /usr overlays, `bootc container export --format=tar` for mutable installations, and `bootc completion <shell>` for shell completions. The **tag-aware upgrade operation** in v0.1.1 enables smarter upgrade strategies based on container image tags.

**Bootc Image Builder (BIB)** at `quay.io/centos-bootc/bootc-image-builder:latest` now supports output formats including ami, anaconda-iso, qcow2, raw, vhd, and vmdk. For Fedora, the `--rootfs` flag is required since Fedora has no default rootfs. A new `osautomation/image-builder-cli` project is being developed with SBOM generation (`--with-sbom`) and will eventually merge with BIB.

---

## Fedora Rawhide's generational package shifts

Fedora Rawhide (targeting Fedora 45) is undergoing several generational transitions simultaneously. The kernel has jumped to **v0.1.1-rc6** (the version bump from 6.x is purely cosmetic — Torvalds cited "getting confused by large numbers"). For VFIO, the `vfio_virqfd` module was consolidated into the base vfio module since kernel 6.2, simplifying dracut/initramfs configuration. **IOMMUFD** continues maturing as the replacement for legacy VFIO container model, with vIOMMU infrastructure landing in 6.13+.

**systemd 260** ships in Rawhide with several breaking changes. cgroup v1 support was **removed entirely in systemd 258**, and SysV service script support is also gone. The positive side: systemd-sysext and systemd-confext are now fully mature for extending immutable `/usr` and `/etc`, systemd-stub loads extensions from the ESP, and systemd-repart supports file-level fs-verity checks. New tools include `systemd-sbsign` for Secure Boot signing, `systemd-keyutil` for key management, and `updatectl` for system updates via systemd-sysupdate.

**GNOME 50 "Tokyo"** (50~rc) is in Rawhide. The critical change came in GNOME 49: systemd became a **hard dependency** — GDM now requires systemd's `userdb` infrastructure, and gnome-session's built-in service manager was removed entirely. Any bootc image with GNOME must include full systemd user session support. GNOME 48 brought dynamic triple buffering in Mutter and HDR configuration, while GTK's X11 and Broadway backends are deprecated, signaling a Wayland-only future.

**Mesa v0.1.1** brings Vulkan 1.4 across AMD (RADV), Intel (ANV), and NVIDIA (NVK) drivers, with **ACO becoming the default shader compiler for RadeonSI** (better performance, faster compile times). NVIDIA proprietary drivers have reached the **590 series**, which drops Pascal (GTX 10xx) support. Open kernel modules are now the **default for Turing and newer** and the only option for Blackwell GPUs.

---

## SecureBlue's hardening blueprint for MiOS

SecureBlue provides the most comprehensive security hardening model for bootc images. Its approach should be selectively adopted for MiOS based on your threat model.

**Kernel sysctl hardening** (`/etc/sysctl.d/99-hardening.conf`) forms the foundation:

```ini
kernel.kptr_restrict=2
kernel.dmesg_restrict=1
kernel.unprivileged_bpf_disabled=1
kernel.yama.ptrace_scope=2
kernel.sysrq=0
kernel.perf_event_paranoid=3
kernel.kexec_load_disabled=1
net.core.bpf_jit_harden=2
fs.suid_dumpable=0
net.ipv4.tcp_syncookies=1
net.ipv4.conf.all.accept_redirects=0
net.ipv4.conf.all.rp_filter=1
```

**Kernel boot parameters** for maximum security include `slab_nomerge`, `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1`, `randomize_kstack_offset=on`, `pti=on`, `vsyscall=none`, `debugfs=off`, and `lockdown=confidentiality`. MiOS can ship these via the new `/usr/lib/bootc/kargs.d/` drop-in directory.

SecureBlue integrates **GrapheneOS's hardened_malloc** globally (including for Flatpak apps), blacklists unnecessary kernel modules (Bluetooth, Thunderbolt, CD-ROM), removes SUID bits from binaries (replacing with Linux capabilities), enables **USBGuard** by default, disables XWayland, and configures DNS-over-TLS with DNSSEC via systemd-resolved. User namespace creation is restricted via SELinux policy, with targeted exceptions for Flatpak and containers via `udica`-generated policies.

**LKRG v0.1.1** (Linux Kernel Runtime Guard) released in September 2025 is worth evaluating — it performs runtime integrity checking of kernel code, data structures, and credential pointers. As an out-of-tree module, it must be compiled against the exact kernel in your bootc image during the container build.

For TPM2 integration, `bootc install to-disk --block-setup tpm2-luks` handles LUKS+TPM2 binding during installation. Post-install, use `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7` for PCR binding. **PCR 7 alone** (Secure Boot state) is recommended for bootc systems — binding to PCR 0+2+4+7 breaks on every kernel or firmware update. For systems using UKIs, the **signed policy approach** is preferred:

```bash
systemd-cryptenroll --wipe-slot tpm2 --tpm2-device auto \
  --tpm2-public-key /etc/systemd/tpm2-pcr-public-key-initrd.pem /dev/disk/by-label/root
```

---

## GPU passthrough: Looking Glass B7 and the RTX 50-series crisis

**Looking Glass B7** (March 2025) is the current stable release with full Wayland support, DXGI as the default capture interface, and PipeWire audio. Building for GNOME Wayland requires `-DENABLE_LIBDECOR=ON`. A critical NVIDIA+Wayland workaround: the EGL renderer causes flickering — **force OpenGL rendering** with `-r opengl` or `app:renderer=opengl` in config, which eliminates the issue with no performance penalty.

Bazzite's KVMFR integration provides the model for MiOS. The kvmfr kernel module ships in the system image with SELinux policies allowing `svirt_t` access to `/dev/kvmfr0`. Configuration at `/etc/modprobe.d/kvmfr.conf` sets `options kvmfr static_size_mb=128` (sufficient for 4K SDR; increase for ultrawide). The libvirt XML uses QEMU JSON syntax for the ivshmem device.

**NVIDIA consumer GPUs still lack SR-IOV and vGPU** — these remain enterprise-only features. More critically, the **RTX 50-series (Blackwell) has a severe VFIO reset bug**: after PCIe Function Level Reset, cards become completely unresponsive, requiring a full host power cycle. CloudRift.ai posted a **$1,000 bounty** for a fix, and NVIDIA has acknowledged the issue. RTX 40-series remains the safest choice for passthrough. Workarounds under investigation include `disable_idle_d3=1`, early VFIO binding via `softdep nvidia pre: vfio-pci`, and letting NVIDIA host drivers initialize the GPU before unbinding.

**QEMU 9.2** brings virtio-gpu Vulkan support via Venus (`-device virtio-gpu-gl,hostmem=8G,blob=true,venus=true`) and DRM native context support. IOMMUFD is maturing as the VFIO container model replacement, with vIOMMU infrastructure landing in kernel 6.13+.

**Waydroid v0.1.1** works well on AMD/Intel with Wayland but remains problematic on NVIDIA — 2D video playback works, but **3D games lack proper GPU acceleration** due to Android's Mesa dependency conflicting with NVIDIA's proprietary stack. On Fedora, ensure CONFIG_PSI=y, loop devices, and binder kernel modules are available. IPv6 must be enabled in the kernel for Waydroid networking.

**Gamescope** continues as the premiere gaming compositor. For embedded session mode on Fedora, launch via a Wayland session desktop entry calling `gamescope-session`. Bazzite's fork (branch `ba147`) patches Gamescope with `CAP_SYS_NICE` capability for priority scheduling, HDR, VRR, and frame scaling. On NVIDIA+Wayland, Gamescope requires `nvidia-drm.modeset=1` and driver v0.1.1+.

---

## K3s deployment and Podman quadlet patterns on bootc

K3s fits naturally on bootc because its data directory (`/var/lib/rancher/k3s`) already lives in the writable `/var` partition. The recommended approach bakes K3s into the bootc image at a pinned version:

```dockerfile
RUN curl -sfL https://get.k3s.io | INSTALL_K3S_SKIP_START=true \
    INSTALL_K3S_SKIP_ENABLE=true INSTALL_K3S_VERSION=v0.1.1+k3s1 sh -
RUN dnf install -y container-selinux k3s-selinux && dnf clean all
RUN systemctl enable k3s
```

K3s config at `/etc/rancher/k3s/config.yaml` should set `selinux: true` and `data-dir: /var/lib/rancher/k3s` (the default). **Moving the data directory away from this default is NOT supported under SELinux** without custom policy. For networking, Flannel vxlan works out of the box; Cilium provides eBPF-based networking, advanced NetworkPolicy enforcement, and Hubble observability but requires `--flannel-backend=none --disable-kube-proxy` at install time plus mounting bpffs at `/sys/fs/bpf`.

K3s version upgrades should follow the image-based model: build a new bootc image with the updated K3s version, then `bootc upgrade`. The system-upgrade-controller provides an alternative Kubernetes-native upgrade path using CRD Plan resources, but for a single-node workstation, image-based upgrades are simpler and more atomic.

**Podman quadlet files** are the recommended pattern for managing non-Kubernetes system services. Place `.container`, `.volume`, and `.network` files in `/etc/containers/systemd/` (writable, persists) or `/usr/share/containers/systemd/` (baked into image, immutable):

```ini
# /etc/containers/systemd/crowdsec.container
[Container]
Image=docker.io/crowdsecurity/crowdsec:latest
ContainerName=crowdsec
Volume=crowdsec-data.volume:/var/lib/crowdsec/data
Volume=crowdsec-config.volume:/etc/crowdsec
Network=host

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
```

Podman 5.x quadlets support template files (`foo@.container`), auto-update from registries (`AutoUpdate=registry`), and `.build` files for building images at service start. **Logically-bound images** can be pre-pulled at bootc install/update time by symlinking quadlet files into `/usr/lib/bootc/bound-images.d/`.

For storage, K3s's built-in **Local Path Provisioner** works immediately on bootc (storing PVs at `/var/lib/rancher/k3s/storage/`). **Longhorn** is the recommended upgrade path when snapshots and S3 backups are needed — it requires `open-iscsi` in the bootc image and stores data at `/var/lib/longhorn`. Rook-Ceph is viable for single-node but carries **500MB+ RAM overhead** and requires dedicated raw disks; reserve it for multi-node expansion scenarios.

**Pacemaker/Corosync** works on bootc because configuration persists in `/etc/corosync/` and state lives in `/var/lib/pacemaker/`. Package the stack via `dnf install pacemaker corosync pcs resource-agents` in the Containerfile. For a single workstation, consider whether K3s restart policies plus Podman quadlet `Restart=always` provide sufficient resilience without the complexity of a full HA cluster stack.

---

## CrowdSec deployment on immutable infrastructure

CrowdSec's firewall bouncer integrates with nftables directly, creating its own tables and chains alongside firewalld without conflict. Configure the bouncer at `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml` with `mode: nftables` and separate IPv4/IPv6 chain definitions at priority `-10`. For sovereign/offline deployments, CrowdSec operates with local-only decisions by disabling Central API communication and using manually curated blocklists. The Security Engine triggers "offline" status after 48 hours without CAPI connectivity.

On bootc, install CrowdSec and its bouncers as part of the image build, then mount `/var/lib/crowdsec/data` and `/etc/crowdsec` as persistent volumes. The firewall bouncer should run on the host (not containerized) for direct nftables access. CrowdSec's latest releases default to the **RE2 regex engine** for significantly improved scenario evaluation performance.

---

## Conclusion

MiOS should adopt **five architectural pillars** proven across the Universal Blue ecosystem: multi-stage Containerfile builds with scratch context stages and BuildKit cache mounts; dnf5-based package management with repository priority hierarchies and post-build repo disabling; cosign image signing with SHA256 digest pinning and Renovate-automated updates; systemd-first service management with quadlet files for containerized services; and the three-tier application model (RPM base → Flatpak GUI apps → container CLI tools).

The composefs-native backend represents bootc's future but remains under active development — use `[composefs] enabled = true` today as the stable path. The RTX 50-series VFIO reset bug is a blocking issue for Blackwell GPU passthrough; target RTX 40-series hardware until NVIDIA ships a fix. systemd 260's removal of cgroup v1 and SysV scripts means MiOS must exclusively use cgroup v2 and native systemd units. GNOME 49+'s hard systemd dependency requires full systemd user session support in the bootc image.

The kernel argument drop-in directory (`/usr/lib/bootc/kargs.d/`) is the ideal mechanism for shipping IOMMU, VFIO, and security hardening boot parameters in MiOS images, replacing fragile bootloader configuration modifications with declarative, image-versioned files that survive atomic updates cleanly.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
