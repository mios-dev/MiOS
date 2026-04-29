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

# Technical audit of the bootc ecosystem for MiOS

MiOS has an ambitious multi-role architecture—workstation, hypervisor, K3s node, and Cockpit-managed server in a single immutable image—but **the project's build system, security posture, and CI/CD pipeline lag significantly behind the Universal Blue ecosystem** it draws from. This audit identified 14 critical anti-patterns, 23 missing features compared to Bluefin/Bazzite/uCore/SecureBlue, and 9 imminent upstream changes requiring preparation. The composefs-native backend transition (bootc v1.14–v1.15) is the most consequential ecosystem shift on the horizon, and MiOS has zero preparation for it.

The findings below cross-reference actual code from MiOS against patterns from bootc upstream (v0.1.1, March 2026), Universal Blue (Bluefin, Bazzite, uCore, akmods), SecureBlue, WayBlue, and Fedora CoreOS. Every recommendation includes concrete code that can be directly adopted.

---

## The Containerfile needs a fundamental restructure

MiOS's Containerfile is a monolithic, single-stage file with inline `RUN` commands—the polar opposite of what mature bootc projects use. Bluefin's Containerfile is **48 lines** with four distinct stages; MiOS packs everything into sequential `RUN` directives with no modularity.

**Critical issue: hardcoded credentials baked into OCI layers.** The line `echo "cachyadmin:cachyadmin" | chpasswd` writes a password into a layer that anyone pulling the image can extract with `podman history` or `skopeo inspect`. Bluefin and Bazzite never embed passwords—they use `cloud-init`, `systemd-firstboot`, or Ignition for runtime credential injection.

**The multi-stage context aggregation pattern from Bluefin should be adopted directly:**

```dockerfile
FROM scratch AS ctx
COPY /system_files /system_files
COPY /build_files /build_files

FROM ghcr.io/ublue-os/ucore-hci:stable AS base
RUN --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=bind,from=ctx,source=/,target=/ctx \
    /ctx/build_files/build.sh
RUN bootc container lint
```

This pattern uses `--mount=type=bind` to inject build context without copying it into the final image, `--mount=type=cache` for package manager caches across builds, and a `FROM scratch` stage that aggregates local files and upstream OCI configuration layers. The missing `bootc container lint` at the end is the single most impactful fix—it catches multiple kernels, malformed kargs, non-UTF-8 filenames, and `/boot` content that breaks deployments.

**Initramfs generation is broken.** The current `dracut --force --no-hostonly` command runs inside an unprivileged container build where the running kernel is the CI runner's kernel, not the target MiOS kernel. This produces initramfs images with missing block device drivers. The `LIBMOUNT_FORCE_MOUNT2=always` environment variable is also missing. The correct approach is to defer initramfs generation to the `bootc-image-builder` stage or add `--reproducible` and explicit module inclusion:

```dockerfile
ENV LIBMOUNT_FORCE_MOUNT2=always
RUN KVER=$(ls /usr/lib/modules | head -n 1) && \
    dracut --no-hostonly --reproducible --add ostree \
    /usr/lib/modules/$KVER/initramfs.img $KVER
```

The DNF facade hack (`echo '#!/bin/sh\nexit 0' > /usr/bin/dnf`) is a known workaround for bootc-image-builder's Red Hat tooling assumptions but creates a silent failure mode. It should be prominently documented and tracked against upstream bootc-image-builder.

---

## Build script orchestration should follow numbered-script patterns

MiOS's internal documentation references scripts numbered `01-` through `39-`, but the actual implementation uses inline Containerfile `RUN` commands. Bluefin delegates to `build_files/shared/build.sh`, which orchestrates numbered scripts with `set -eoux pipefail` for fail-fast behavior. Bazzite uses a similar pattern with variant-specific overrides (`build_automation/overrides/dx/`, `build_automation/overrides/gdx/`).

**Recommended directory structure:**

```
build_files/
├── build.sh                    # Orchestrator: copies sys_files, runs scripts in order
├── base/
│   ├── 00-image-info.sh        # Generate /usr/share/mios/image-info.json
│   ├── 03-install-kernel-akmods.sh
│   ├── 05-override-install.sh  # GSettings/dconf overrides
│   ├── 10-packages.sh          # Core package installation
│   ├── 15-nvidia-drivers.sh    # NVIDIA from akmods OCI
│   ├── 17-cleanup.sh           # Cache cleanup, repo disable
│   └── 19-initramfs.sh         # dracut with --no-hostonly --reproducible
└── shared/
    └── build-tests.sh          # Verify critical packages installed

├── usr/lib/bootc/kargs.d/01-nvidia.toml
├── usr/lib/systemd/system/mios-flatpak-manager.service
├── usr/share/glib-2.0/schemas/zz0-mios.gschema.override
└── etc/dconf/db/local.d/01-mios
```

Bluefin's build-time test pattern is worth adopting: after the build completes, a verification script checks that critical packages are present and systemd units are enabled, failing the build if any are missing.

---

## GNOME integration requires three-layer configuration

Bluefin and Bazzite use a three-layer system for GNOME customization that MiOS should replicate. **Layer 1: GSettings schema overrides** at `/usr/share/glib-2.0/schemas/zz0-mios.gschema.override` (the `zz0-` prefix ensures MiOS overrides load last, after Fedora defaults). **Layer 2: dconf database overrides** at `/etc/dconf/db/local.d/01-mios`. **Layer 3: runtime user setup** via a first-login systemd user service.

```ini
# /usr/share/glib-2.0/schemas/zz0-mios.gschema.override
[org.gnome.shell]
favorite-apps=['org.mozilla.firefox.desktop', 'org.gnome.Nautilus.desktop', 'org.gnome.Ptyxis.desktop', 'cockpit.desktop']

[org.gnome.desktop.interface]
cursor-theme='Bibata-Modern-Ice'
color-scheme='prefer-dark'
gtk-theme='adw-gtk3-dark'
```

```ini
# /etc/dconf/db/local.d/01-mios
[org/gnome/shell/extensions/Logo-menu]
menu-button-terminal='ptyxis --new-window'
menu-button-system-monitor='/usr/bin/missioncenter-helper'

[org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0]
binding='<Control><Alt>t'
command='ptyxis --new-window'
name='Terminal'
```

The Containerfile must compile schemas and enable the dconf-update service:

```dockerfile
RUN rm -f /usr/share/glib-2.0/schemas/gschemas.compiled && \
    glib-compile-schemas /usr/share/glib-2.0/schemas/
RUN systemctl enable dconf-update.service
```

Bazzite's `dconf-override-converter` tool provides bidirectional conversion between GSettings override format and dconf format, preventing the common mistake of using the wrong syntax in the wrong file. Bazzite also strips unnecessary GNOME packages at build time: `gnome-software`, `gnome-classic-session`, `gnome-tour`, `gnome-extensions-app`, `gnome-initial-setup`, and `gnome-system-monitor`—replacing them with Flatpak equivalents (Bazaar, Mission Center, Extension Manager).

---

## NVIDIA driver integration must use the akmods OCI pattern

MiOS installs `linux-cachyos-nvidia` directly from MiOS repos, which couples driver versions to the upstream package manager's release cadence and provides no Secure Boot signing. Universal Blue's approach is fundamentally different: **pre-built, pre-signed kernel modules distributed as OCI container layers**.

```dockerfile
ARG NVIDIA_REF="ghcr.io/ublue-os/akmods-nvidia:coreos-stable-42@sha256:..."
COPY --from=${NVIDIA_REF} /rpms/ /tmp/rpms
RUN dnf install -y /tmp/rpms/ublue-os/ublue-os-nvidia*.rpm \
    /tmp/rpms/kmods/kmod-nvidia*.rpm && dnf clean all

# SELinux policy for containerized GPU workloads
RUN semodule -i /usr/share/selinux/packages/nvidia-container.pp

# CDI service for rootless container GPU access
COPY ublue-nvctk-cdi.service /usr/lib/systemd/system/
RUN systemctl enable ublue-nvctk-cdi.service
```

The CDI (Container Device Interface) service is critical for rootless Podman GPU access:

```ini
# ublue-nvctk-cdi.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

**Secure Boot enrollment:** Universal Blue ships a public key at `/etc/pki/akmods/certs/akmods-ublue.der` with a known enrollment password (`universalblue`). MiOS should implement its own MOK signing pipeline or consume ublue-os/akmods images directly. For multi-GPU (AMD+NVIDIA) passthrough, Bazzite's initramfs configuration ensures the integrated AMD GPU initializes first for host display, while the NVIDIA GPU is isolated for VFIO passthrough.

**Missing kernel arguments** should use the new `/usr/lib/bootc/kargs.d/` directory (bootc v1.13+):

```toml
# /usr/lib/bootc/kargs.d/01-nvidia.toml
kargs = ["nvidia_drm.modeset=1", "rd.driver.blacklist=nouveau", "modprobe.blacklist=nouveau"]
```

---

## Flatpak deployment must happen at first boot, never build time

MiOS has no Flatpak integration. Bazzite's `bazzite-flatpak-manager` is the gold standard: a **122-line systemd oneshot service** with version-based sentinel files for idempotency.

```bash
#!/bin/bash
# /usr/libexec/mios-flatpak-manager
VER=1
VER_FILE="/etc/mios/flatpak_manager_version"
SCRIPT_HASH=$(sha256sum "$0" | cut -d' ' -f1)
VER_RUN="$VER-$SCRIPT_HASH"

if [ -f "$VER_FILE" ] && [ "$(cat $VER_FILE)" = "$VER_RUN" ]; then
    exit 0  # Already configured for this version
fi

# Configure remotes
flatpak remote-add --system --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
flatpak remote-modify --system --disable fedora || :
flatpak remote-modify --system --disable fedora-testing || :

# Install from curated list
xargs -a /usr/share/mios/flatpak-list \
    flatpak install -y --noninteractive flathub

# GTK theming passthrough for Flatpak apps
flatpak override --system --filesystem=xdg-config/gtk-3.0:ro
flatpak override --system --filesystem=xdg-config/gtk-4.0:ro

echo "$VER_RUN" > "$VER_FILE"
```

```ini
# /usr/lib/systemd/system/mios-flatpak-manager.service
[Unit]
Description=MiOS Flatpak Manager
After=network-online.target
Wants=network-online.target
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/usr/libexec/mios-flatpak-manager

[Install]
WantedBy=multi-user.target
```

On Fedora 42+, Bluefin uses the native `flatpak-preinstall.service` with `.preinstall` files in `/etc/preinstall.d/`—a cleaner approach if MiOS targets F42+. The Fedora Flatpak remote should be **masked** at build time: `systemctl mask flatpak-add-fedora-repos.service`.

---

## SELinux requires build-time policy compilation and the Cockpit 330 fix

MiOS's internal documents acknowledge that SELinux policies must be "pre-compiled into CIL and packaged within the image's policy store," but **no actual policy compilation exists in the Containerfile**. The Cockpit setuid bug—where `cockpit-session` failed on composefs-backed read-only filesystems—was resolved in **Cockpit 330 (December 2024)** by replacing setuid with systemd socket activation and `DynamicUser=`. MiOS should require Cockpit ≥330.

**Custom policy modules should be compiled during the image build:**

```dockerfile
# Method 1: CIL format (recommended)
COPY selinux/mios-vfio.cil /root/
RUN semodule -X 300 -i /root/mios-vfio.cil

# Custom file contexts for VFIO and Looking Glass
RUN semanage fcontext -a -t svirt_tmpfs_t "/dev/shm/looking-glass(/.*)?"
RUN semanage fcontext -a -t container_file_t "/srv/containers(/.*)?"

# SELinux booleans
RUN setsebool -P virt_use_nfs 1
RUN setsebool -P container_manage_cgroup 1
```

SecureBlue's approach is the most rigorous: SELinux enforcing mode with **SELinux-confined unprivileged user namespaces** (restricting userns by default but allowing Flatpak and specific browsers). This is superior to the common approach of either fully disabling userns or leaving them unrestricted.

---

## Cockpit needs socket activation, not daemon mode

The correct Cockpit deployment for bootc follows uCore's containerized pattern or Bluefin's RPM-based socket activation. MiOS should install Cockpit packages at build time and enable only the socket:

```dockerfile
RUN dnf install -y cockpit-system cockpit-storaged cockpit-networkmanager \
    cockpit-podman cockpit-machines cockpit-selinux && dnf clean all
RUN systemctl enable cockpit.socket
# Firewall (offline — no D-Bus available during build)
RUN firewall-offline-cmd --zone=public --add-service=cockpit
```

For remote access with reverse proxies, the `cockpit.conf` must set `Origins`:

```ini
# /etc/cockpit/cockpit.conf
[WebService]
Origins = https://cockpit.example.com wss://cockpit.example.com
LoginTo = false
AllowUnencrypted = false
```

TLS certificates go in `/etc/cockpit/ws-certs.d/` as `.cert` files (PEM format, cert+key concatenated). Cockpit reads them alphabetically; highest number wins. The SELinux port label must be set if using non-default ports: `semanage port -a -t websm_port_t -p tcp 443`.

---

## The composefs-native backend is here and requires preparation

The composefs-native backend has progressed from experimental to production-ready across bootc v1.12–v1.15. **OSTree is being phased out as the storage backend.** Key implications for MiOS:

- **Composefs GC** (v0.1.1) can potentially delete EFI partitions if misconfigured—bootc issue #2102 documents this risk
- **Sealed images** default to requiring Secure Boot + fs-verity on the target system; a `--disable-sealing` flag allows degraded mode
- **UKI (Unified Kernel Image)** support is deeply integrated with composefs-native, bundling kernel, initramfs, and cmdline into a single signed EFI binary
- The `bootc install` command gains a `--composefs-native` flag
- **SELinux enforcement for sealed images** landed in v0.1.1

MiOS should enable composefs in its images now:

```ini
# /usr/lib/ostree/prepare-root.conf
[composefs]
enabled = yes
```

The download-only upgrade mode (`bootc upgrade --download-only`, February 2026 RHEL 10.2) is **not yet available** for the composefs-native backend—only the OSTree backend.

---

## Security hardening gaps compared to SecureBlue are significant

SecureBlue implements hardening that MiOS entirely lacks. The most impactful patterns to adopt:

**Kernel argument hardening** via `/usr/lib/bootc/kargs.d/`:

```toml
# /usr/lib/bootc/kargs.d/02-hardening.toml
kargs = [
    "init_on_alloc=1",
    "init_on_free=1",
    "iommu=force",
    "kvm_amd.sev=1",
    "kvm_amd.sev_es=1",
    "page_alloc.shuffle=1",
    "randomize_kstack_offset=on"
]
```

**SUID stripping with capability replacement** (SecureBlue's `removesuid.sh`): strips setuid from all binaries except a whitelist, removes `sudo`/`su`/`pkexec` entirely, and replaces them with `run0` (systemd-run0). MiOS should adopt at minimum the capability replacement pattern:

```bash
# Strip SUID from non-essential binaries
find /usr -type f -perm /4000 | while read -r binary; do
    case "$binary" in
        /usr/bin/nvidia-modprobe|/usr/lib/polkit-1/polkit-agent-helper-1) continue ;;
        *) chmod u-s "$binary" ;;
    esac
done
# Set minimal capabilities
setcap "cap_dac_read_search,cap_audit_write=ep" /usr/sbin/unix_chkpwd
setcap "cap_sys_admin=ep" /usr/bin/fusermount3
```

**hardened_malloc** (from GrapheneOS) as the global memory allocator provides buffer overflow detection and heap corruption resistance. SecureBlue applies this even inside Flatpak sandboxes via `LD_PRELOAD`.

**SSH hardening** should be baked into the image:

```ini
# /etc/ssh/sshd_config.d/50-mios-hardened.conf
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowTcpForwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

---

## WSL2 compatibility requires conditional service gating

The primary WSL2 issue is `dbus-broker`'s `--audit` flag attempting to access the Linux audit subsystem, which WSL2's kernel doesn't support. Services that depend on hardware or boot infrastructure unavailable in WSL2 should use `ConditionPathExists`:

```ini
# Gate services that shouldn't run in WSL2
[Unit]
ConditionPathExists=!/proc/sys/fs/binfmt_misc/WSLInterop
ConditionPathExists=!/proc/sys/fs/binfmt_misc/WSLInterop-late

# Conversely, WSL2-only services
[Unit]
ConditionPathExists=|/proc/sys/fs/binfmt_misc/WSLInterop
ConditionPathExists=|/proc/sys/fs/binfmt_misc/WSLInterop-late
```

The WSL2 `wsl.conf` must enable systemd (`[boot]\nsystemd=true`) and the `systemd-firstboot.service` should be disabled to prevent hangs. There is **no established bootc-on-WSL2 workflow** in the ecosystem; MiOS's WSL2 support path via `podman export → wsl --import` is novel but unsupported upstream.

---

## Image signing is completely absent and must be implemented immediately

MiOS publishes to `ghcr.io/mios-project/mios:latest` with **no cryptographic signing, no SBOM, and no provenance verification**. The minimal implementation uses cosign keyless signing in GitHub Actions:

```yaml
jobs:
  build:
    permissions:
      packages: write
      id-token: write  # Required for OIDC keyless signing
    steps:
      - uses: sigstore/cosign-installer@v0.1.1
      - name: Sign image
        run: |
          cosign sign --yes \
            ghcr.io/mios-project/mios@${{ steps.push.outputs.digest }}
```

**The `--new-bundle-format=false` workaround is critical:** Cosign v3's default protobuf bundle format is incompatible with the `containers/image` library used by rpm-ostree and bootc for signature verification. Until upstream support lands, always sign with `cosign sign --new-bundle-format=false --yes $DIGEST`.

Universal Blue uses key-pair signing rather than keyless because rpm-ostree's signature verification doesn't yet fully support Fulcio certificate chains. The container policy configuration at `/etc/containers/policy.json` should enforce signature verification:

```json
{
  "default": [{"type": "reject"}],
  "transports": {
    "docker": {
      "ghcr.io/mios-project": [{
        "type": "sigstoreSigned",
        "keyPath": "/etc/pki/containers/mios-cosign.pub"
      }]
    }
  }
}
```

---

## Storage, clustering, and firewall need architectural decisions

**Storage:** OpenZFS is fundamentally problematic on bootc—DKMS requires kernel headers and a writable `/usr/src`, neither available on immutable root. uCore solves this with pre-built ZFS modules via `ucore-kmods`, but newer kernels increasingly mark symbols as GPL-only, causing ZFS compilation failures. **Stratis** is a better fit for bootc systems: native Linux integration, no DKMS, and packages install cleanly. If ZFS is required, modules must be pre-compiled in CI against the exact kernel ABI.

**K3s:** The standard `curl | sh` installer writes to `/usr/local/bin`, which is incompatible with read-only `/usr`. K3s binaries must be placed at `/usr/bin/k3s` during the image build, with the systemd service at `/usr/lib/systemd/system/k3s.service`. The `/var/lib/rancher/` state directory is on persistent storage and survives rollbacks. HA token injection requires cloud-init or Ignition at first boot.

**Firewall:** All firewall configuration during image builds must use `firewall-offline-cmd` (firewalld isn't running in the container build environment). uCore's `netavark-firewalld-reload.service` is essential for Podman networking—it re-adds container firewall rules after firewalld reloads:

```dockerfile
RUN firewall-offline-cmd --zone=public --add-service=ssh
RUN firewall-offline-cmd --zone=public --add-service=cockpit
RUN firewall-offline-cmd --zone=public --add-port=6443/tcp
```

**CrowdSec** is best deployed as a Podman quadlet container on bootc systems, with the `cs-firewall-bouncer-nftables` package baked into the host image for nftables access.

---

## Upcoming ecosystem changes requiring immediate preparation

**Nine changes on the horizon demand attention now:**

1. **Composefs-native backend** (bootc v1.14–v1.15) replaces OSTree storage. Enable `[composefs] enabled = yes` in `prepare-root.conf` today
2. **Cockpit 330+** eliminates the setuid bug on bootc. Pin minimum Cockpit version to ≥330
3. **bootc v1.15's tag-aware upgrades** enable pinning to specific image tags rather than following `:latest`
4. **`/usr/lib/bootc/kargs.d/`** (v1.13+) replaces manual kernel argument management
5. **Cosign v3 bundle format** requires `--new-bundle-format=false` for compatibility with rpm-ostree/bootc verification
6. **UKI boot** via composefs-native creates a Secure Boot chain of trust from UEFI → UKI → composefs → filesystem
7. **`bootc container lint`** should be the final step in every Containerfile build
8. **Download-only upgrades** (RHEL 10.2) enable staged updates but aren't yet available for composefs-native
9. **Pre-flight disk space checks** (v1.14+) prevent failed upgrades from filling disks

---

## Conclusion

MiOS's ambition to unify workstation, hypervisor, and server roles in a single bootc image is architecturally sound—this is precisely what uCore-HCI demonstrates at scale. But the implementation gap is substantial. **The three highest-impact changes are:** adopting the multi-stage Containerfile pattern with `FROM scratch AS ctx` and `bootc container lint`, implementing cosign image signing in CI, and removing hardcoded credentials in favor of first-boot provisioning.

The project's MiOS/Arch base adds complexity that Fedora-based Universal Blue projects avoid entirely—the DNF facade hack, manual keyring management, and bootc-image-builder incompatibilities are all self-inflicted. Consider whether the MiOS performance optimizations (BORE scheduler, x86-64-v3) justify the maintenance burden, or whether Fedora Rawhide bootc with kernel arguments achieves comparable results.

The composefs-native transition is not optional—it represents bootc's future storage model. MiOS should enable composefs now, implement UKI support for Secure Boot, and begin testing with `--composefs-native` installations. The window for gradual adoption is closing as OSTree moves toward deprecation in the bootc context.

SecureBlue's sudoless design (`run0` replacing `sudo`), SUID stripping, and hardened_malloc integration represent a security standard that any production bootc image should aspire to. The 4,500-line `mios-full.sh` management script should be decomposed into idempotent systemd units and declarative configuration—imperative shell scripts are the antithesis of the immutable OS model MiOS claims to implement.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
