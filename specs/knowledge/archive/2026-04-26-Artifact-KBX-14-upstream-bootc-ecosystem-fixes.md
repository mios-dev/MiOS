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

# Upstream bootc ecosystem fixes for MiOS

**MiOS can resolve the majority of its runtime issues by adopting proven patterns from Universal Blue, Fedora CoreOS, and the rapidly maturing bootc upstream.** The bootc project—now a CNCF Sandbox project at v0.1.1—has gained composefs-native backend work, tag-aware upgrades, and robust linting tools since early 2025. Universal Blue's Bluefin, Bazzite, and uCore projects collectively represent the most battle-tested bootc deployment patterns, covering everything from SELinux workarounds to NVIDIA driver integration. This report maps each of MiOS's 20 known issues to specific upstream solutions with actionable code patterns, GitHub references, and implementation recommendations.

---

## SELinux, systemd services, and PAM configuration

**SELinux on bootc requires fundamentally different approaches than traditional Fedora.** The read-only composefs root means `chcon` cannot set extended attributes on immutable files—only `/etc` and `/var` are mutable. MiOS should adopt three upstream patterns:

**The bind-mount + restorecon workaround** is Bluefin's canonical solution for mislabeled binaries. A systemd oneshot service copies the binary from read-only `/usr` to mutable `/usr/local/bin/overrides/`, bind-mounts it over the original, then runs `restorecon`. Bluefin's `incus-workaround.service` demonstrates this pattern. For bootupctl accessing `/boot/bootupd-state.json` and gdm-session-worker `.cache` access, this same pattern applies. For `systemd-homed` accessing `/home` (the `/var/home` symlink), the upstream approach uses `semanage fcontext` in the Containerfile rather than `chcon`:

```dockerfile
# WORKS in container builds:
RUN semanage fcontext -a -t home_root_t "/var/home(/.*)?"
# FAILS in container builds:
RUN chcon -t home_root_t /var/home
```

For the `chcon mac_admin` capability denial, Bazzite tracks this at [ublue-os/bazzite#3619](https://github.com/ublue-os/bazzite/issues/3619). The fix involves building custom SELinux policy modules via `semodule -i` during the container build. For SELinux booleans (like `container_manage_cgroup`), Fedora CoreOS established the pattern of applying them non-persistently via a systemd oneshot service on every boot, avoiding the problem where `setsebool -P` modifies `/etc/selinux/` binary files and prevents future policy updates from taking effect ([coreos/fedora-coreos-tracker#701](https://github.com/coreos/fedora-coreos-tracker/issues/701)).

**systemd service enablement** works directly in Containerfiles via `RUN systemctl enable <service>`—this creates symlinks only and is officially supported. For distribution-level defaults, use preset files at `/usr/lib/systemd/system-preset/10-mios.preset`. Drop-in overrides belong in `/usr/lib/systemd/system/<unit>.d/` (immutable layer), not `/etc/systemd/system/` (mutable). Gate services that shouldn't start during container builds with `ConditionVirtualization=!container`.

**Authselect on Fedora 43+ bootc** should use the `local` profile (default since Fedora 40), not `sssd`, unless remote identity is needed. The correct Containerfile invocation is `RUN authselect select local with-fingerprint with-mdns4 with-silent-lastlog --force`. This simultaneously handles mDNS/Avahi nsswitch.conf integration. Never edit `/etc/pam.d/` or `/etc/nsswitch.conf` directly—use authselect features and `/etc/authselect/user-nsswitch.conf` ([coreos/fedora-coreos-tracker#1051](https://github.com/coreos/fedora-coreos-tracker/issues/1051)).

---

## Cockpit, WSL2, and Hyper-V platform support

**Cockpit 330+ is mandatory for bootc images.** Prior versions used a setuid `cockpit-session` binary that got wrong ownership when installed in container builds, causing login failures ([cockpit-project/cockpit#21201](https://github.com/cockpit-project/cockpit/issues/21201)). Cockpit 330 (December 2024) eliminated the setuid requirement entirely by switching to systemd socket activation. For bootc workstations, install Cockpit RPMs directly in the Containerfile rather than using the CoreOS containerized `cockpit-ws` approach:

```dockerfile
RUN dnf install -y cockpit cockpit-ws cockpit-bridge cockpit-podman \
    cockpit-storaged cockpit-selinux && dnf clean all
RUN systemctl enable cockpit.socket
RUN firewall-offline-cmd --add-service=cockpit
```

Configure the listen address via a systemd socket drop-in at `/etc/systemd/system/cockpit.socket.d/listen.conf`. The empty `ListenStream=` line is required to reset the default port. No `cockpit-ostree` or `cockpit-bootc` management plugin exists—bootc management remains CLI-only.

**WSL2 support is essentially non-existent upstream.** The `bootc-image-builder` lacks WSL tarball output ([osautomation/bootc-image-builder#172](https://github.com/osautomation/bootc-image-builder/issues/172), open since February 2024). The Podman Desktop bootc extension explicitly states WSL2 is unsupported due to the custom Microsoft kernel. Universal Blue has no WSL-specific repos or images. The dbus-broker failure is caused by the WSL2 kernel lacking full audit subsystem support—the workaround is switching to `dbus-daemon`:

```bash
systemctl mask dbus-broker.service
systemctl enable dbus-daemon.service
```

For WSL2 deployment, treat it as a container runtime (not a bootable host): `podman export $(podman create my-bootc) -o image.tar.gz && wsl --import MyDistro path image.tar.gz`. This does NOT create a proper bootc-managed system.

**For Hyper-V**, bootc-image-builder produces VHD (Azure VPC format), not native VHDX. Convert via `qemu-img convert -f raw -O vhdx -o subformat=dynamic disk.raw disk.vhdx`. Include the `hyperv-daemons` package and enable `hypervkvpd.service`, `hypervvssd.service`, and `hypervfcopyd.service` in the image. Use Generation 2 VMs for UEFI boot.

---

## GTK3 theming, Flatpak management, and bootc lint

**adw-gtk3-theme must remain in the image until all GTK3 apps are migrated to GTK4.** Bazzite learned this the hard way in September 2025 when commit `77e6daa` dropped adw-gtk3, breaking dark mode for Lutris and other GTK3 apps ([ublue-os/bazzite#3142](https://github.com/ublue-os/bazzite/issues/3142)). The complete theming approach requires three layers: the `adw-gtk3-theme` RPM in the image, Flatpak theme runtimes (`org.gtk.Gtk3theme.adw-gtk3-dark`), and dconf/GSettings overrides. Bazzite uses a two-layer configuration system—GSchema overrides at `/usr/share/glib-2.0/schemas/` compiled with `glib-compile-schemas --strict`, plus a dconf database at `/etc/dconf/db/distro.d/`:

```ini
[org/gnome/desktop/interface]
gtk-theme='adw-gtk3-dark'
color-scheme='prefer-dark'
```

Run `dconf update` at build time or via a first-boot systemd oneshot service.

**Flatpak should never be pre-installed during container build.** This is Universal Blue's firm position, driven by three factors: pre-installing Flatpaks generates **36,890+ symlinks** in `/var/lib/flatpak` that trigger massive bootc lint warnings; it bloats the container image dramatically; and `/var` content in containers behaves like a Docker VOLUME—only copied on first deployment, never updated. Instead, use a first-boot systemd service. Bazzite's `bazzite-flatpak-manager` and Bluefin's `flatpak-preinstall.service` both read app lists from `/etc/` or `/usr/share/` and install at first boot. For ISO-based installations, Universal Blue's Titanoboa project rsync's Flatpaks from the live environment into the deployed system during kickstart post-install.

**bootc container lint** should be the final `RUN` line in every Containerfile. Current lint checks include `nonempty-boot`, `var-tmpfiles`, `var-log`, `sysusers`, `nonempty-run-tmp`, and `kernel`. For `/var` content, create `tmpfiles.d` entries and remove the actual directories: `echo 'd /var/lib/myapp 0755 root root - -' > /usr/lib/tmpfiles.d/myapp.conf && rm -rf /var/lib/myapp`. Use `--skip var-tmpfiles` for Flatpak-related warnings that cannot be resolved. The `--skip nonempty-boot` flag handles kernel packages that place files in `/boot`.

---

## Image signing, rechunking, and update infrastructure

**Universal Blue uses key-based Cosign signing, not keyless OIDC.** A private key is stored as GitHub Actions secret `SIGNING_SECRET`, with the public key committed to the repo. The workflow pattern across all ublue-os repos:

```yaml
- uses: sigstore/cosign-installer@v0.1.1
- name: Sign Images
  env:
    SIGNING_KEY: ${{ secrets.SIGNING_SECRET }}
  run: cosign sign -y --key env://SIGNING_KEY $IMAGE_NAME:$digest
```

The sigpolicy issue ([bootc-dev/bootc#528](https://github.com/bootc-dev/bootc/issues/528)) is now closed. Configure `/etc/containers/policy.json` system-wide with `sigstoreSigned` type and `matchRepository` identity. **Critical warning**: Cosign v3's new bundle format uses the OCI referrers API, which rpm-ostree and ostree don't support yet ([coreos/rpm-ostree#5509](https://github.com/coreos/rpm-ostree/issues/5509)). Use `--new-bundle-format=false` or pin to Cosign v2.

**Rechunking reduces update sizes 5–10×.** The rechunker (now at [hhd-dev/rechunk](https://github.com/hhd-dev/rechunk), originally ublue-os/rechunk) flattens the OCI image to remove files replaced in later layers, reads the RPM database to group packages by version into "meta" packages, then re-partitions into N equally-sized layers using timestamp clamping so unchanged packages produce identical layer hashes. For MiOS's large images with NVIDIA drivers, ROCm, and Wine/Steam, rechunking is essential. Aurora/Bluefin integrate it via a three-step process (`1_prune.sh`, `2_create.sh`, `3_chunk.sh`) invoked in their GitHub Actions workflow with `PREV_REF` pointing to the previous production image for layer stability.

**For automated updates**, avoid the built-in `bootc-fetch-apply-updates.timer`—it shuts down without warning. Universal Blue uses [uupd](https://github.com/ublue-os/uupd), a Go program that coordinates Flatpak, Distrobox, Homebrew, and bootc updates with hardware-aware checks (battery %, CPU load, memory). bootc v0.1.1 added `--download-only` and `--from-downloaded` flags for staged updates. Bluefin maintains three deployments simultaneously (current, staged, rollback) with automatic checks every 6 hours.

---

## K3s, Ceph, and CrowdSec on immutable filesystems

**K3s binary belongs in `/usr/local/bin/k3s`** with symlinks for `kubectl`, `crictl`, and `ctr`. The systemd unit goes in `/usr/lib/systemd/system/k3s.service`, and all stateful data stays in `/var/lib/rancher/k3s/`. The most concrete reference implementation is [cdrage/containerfiles](https://github.com/cdrage/containerfiles) (`bootc-k3s-master/` and `bootc-k3s-node/` directories), which downloads the K3s binary during `podman build`, installs `k3s-selinux` via RPM, and embeds the systemd unit. The K3s install script (`get.k3s.io`) writes to paths that are read-only on bootc, so it must be done at build time. Kairos offers an alternative using systemd system extensions (`.sysext.raw`). Known limitation: `k3s-uninstall.sh` fails on bootc because `yum remove` hits the read-only filesystem ([k3s-io/k3s#13710](https://github.com/k3s-io/k3s/issues/13710)), and custom `--data-dir` under SELinux is not supported.

**For Ceph on bootc, ceph-fuse is preferred over kernel CephFS.** Fedora CoreOS encountered kernel compatibility issues with Ceph after kernel upgrades ([coreos/fedora-coreos-tracker#1393](https://github.com/coreos/fedora-coreos-tracker/issues/1393)). ceph-fuse operates in userspace, making it resilient to kernel changes. For running a Ceph cluster, cephadm is container-native and well-suited for bootc—it deploys all daemons as Podman containers, needing only Python 3, LVM2, and Podman on the host. State stores under `/var/lib/ceph/<fsid>/`. Bake `ceph-common` and `ceph-fuse` into the image; do not rely on `cephadm add-repo` at runtime (it writes to read-only `/etc/yum.repos.d/`).

**CrowdSec runs best as a Podman quadlet container on bootc.** Set `DISABLE_ONLINE_API=true` for sovereign/offline mode. Pre-install collections via the `COLLECTIONS` environment variable. Two volumes are mandatory: `/var/lib/crowdsec/data/` (required since v0.1.1) and `/etc/crowdsec/`. For the firewall bouncer, install it natively in the bootc image since it needs host iptables access. Hub updates require internet—for air-gapped environments, pre-populate `/etc/crowdsec/hub/` at image build time. Use `config.yaml.local` for overrides that survive CrowdSec upgrades.

---

## NVIDIA drivers and GPU passthrough with VFIO

**Universal Blue pre-builds NVIDIA kernel modules in CI** rather than compiling at boot. The [ublue-os/akmods](https://github.com/ublue-os/akmods) repository builds kmod RPMs into OCI container images tagged `KERNEL_TYPE-FEDORA_RELEASE-NVIDIA_VERSION`. Downstream Containerfiles use `COPY --from=ghcr.io/ublue-os/akmods-nvidia:TAG / /tmp/akmods-nvidia` to pull pre-built modules. The `ublue-os-akmods-addons` RPM installs the ublue kmods signing key for Secure Boot MOK enrollment. Bazzite has moved to [bazzite-org/nvidia-drivers](https://github.com/bazzite-org/nvidia-drivers) (a negativo17 mirror build) for its latest images. CDI support comes via `nvidia-container-toolkit` (v1.14+), with an accompanying NVIDIA container SELinux policy adapted from [NVIDIA/dgx-selinux](https://github.com/NVIDIA/dgx-selinux). Kernel updates are handled atomically—a new image is built with matching kernel + kmod, and users receive both together via `bootc upgrade`.

**VFIO/Looking Glass on Bazzite uses `ujust setup-virtualization`** with options for `vfio-on`, `vfio-off`, `shm` (Looking Glass shared memory), and `kvmfr` (KVMFR kernel module). VFIO kernel arguments are set via `rpm-ostree kargs --append="iommu=pt" --append="rd.driver.pre=vfio_pci"`. The **KVMFR module is pre-built as an akmod** in the ublue-os/akmods extra stream ([PR #169](https://github.com/ublue-os/akmods)), since atomic desktops cannot compile kernel modules at runtime. Looking Glass client is NOT shipped—users compile it in a Distrobox container with Wayland + PipeWire flags (`-DENABLE_X11=OFF -DENABLE_WAYLAND=ON`), then copy the binary to `~/.local/bin/`. A dracut VFIO config ships at `80-vfio.conf`.

---

## Gamescope/Steam session and Waydroid integration

**Bazzite uses [gamescope-session-plus](https://github.com/bazzite-org/gamescope-session)** (forked from ChimeraOS) as the session launcher. The Wayland session desktop entry at `/usr/share/wayland-sessions/gamescope-session-steam.desktop` runs `gamescope-session-plus steam`. The session definition at `/usr/share/gamescope-session-plus/sessions.d/steam` defines `CLIENTCMD` as `steam -steamos -pipewire-dmabuf -gamepadui`. GDM users select "Steam (Gamescope)" from the login screen; SDDM (KDE) auto-logs in directly. Ported SteamOS scripts include `steamos-session-select` (invokes Steam shutdown and returns to the display manager) and dummy scripts for `jupiter-biosupdate`, `steamos-select-branch`, and `steamos-update`. Steam is installed as a **layered RPM from negativo17**, not as a Flatpak, with a `bazzite-steam` wrapper. User overrides go in `~/.config/gamescope-session-plus/sessions.d/steam` ([PR #2461](https://github.com/ublue-os/bazzite/pull/2461)).

**Waydroid on bootc requires binder kernel support** (provided by Bazzite's custom kernel) and binderfs device nodes. Bazzite's `ujust setup-waydroid` handles initialization, GApps installation (via [ublue-os/waydroid_script](https://github.com/ublue-os/waydroid_script)), GPU selection for multi-GPU systems, and multi-window integration. The init process enables `waydroid-container.service`, runs `sudo waydroid init` with OTA URLs, then critically runs `restorecon -R /var/lib/waydroid` for proper SELinux labels ([ublue-os/bazzite#1998](https://github.com/ublue-os/bazzite/issues/1998)). Waydroid does **not work on NVIDIA hardware**—it requires Mesa/GPU rendering. In Steam gaming mode, Waydroid runs through a Weston compositor intermediary since `WAYLAND_DISPLAY` is not set.

---

## bootc-image-builder and Containerfile architecture patterns

**BIB supports `qcow2`, `iso`, `raw`, `vhd`, and `vmdk` output** ([osautomation/bootc-image-builder](https://github.com/osautomation/bootc-image-builder)). For ISO generation, use a `config.toml` with `[customizations.installer.kickstart]` for automated installs. Note that `[customizations.user]` and kickstart sections cannot be combined ([BIB#528](https://github.com/osautomation/bootc-image-builder/issues/528)). Images can embed default config at `/usr/lib/bootc-image-builder/config.toml`. The `--target-imgref` flag in `bootc install` allows installing from one image while configuring the system to track a different registry/tag for future updates. A [GitHub Action](https://github.com/osautomation/bootc-image-builder-action) wraps BIB for CI integration.

**Bluefin's Containerfile architecture** is the gold standard—only **48 lines** using multi-stage builds with a `FROM scratch AS ctx` context stage, `--mount=type=bind,from=ctx` to avoid polluting image layers, `--mount=type=cache,dst=/var/cache/libdnf5` for build speed, and a single `RUN` delegating to an external `build.sh` script. The `/opt → /var/opt` symlink makes `/opt` writable at runtime. Every image ends with `CMD ["/sbin/init"]` and `RUN bootc container lint`.

The broader ecosystem now includes **composefs-native backend** development (tracked at [bootc-dev/bootc#1190](https://github.com/bootc-dev/bootc/issues/1190)), which will replace the ostree backend with composefs-rs, enable UKI support, and provide fs-verity validation. bootc v0.1.1 (March 2026) added tag-aware upgrades, cached update info, and multiple composefs fixes. GNOME OS is now natively bootc-compatible, and bootcrew projects (opensuse-bootc, arch-bootc, debian-bootc) already use the composefs-native backend.

---

## Conclusion

MiOS's 20 runtime issues map cleanly to established upstream solutions. The highest-impact adoptions are: **Cockpit ≥330** (eliminates the setuid/SELinux bug entirely), **the bind-mount + restorecon pattern** from Bluefin (resolves most SELinux denials), **first-boot Flatpak services** rather than build-time installation (eliminates 36K+ lint warnings and image bloat), **pre-built NVIDIA akmods** from ublue-os/akmods (atomic kernel+driver updates), and **hhd-dev/rechunk** (5–10× smaller update downloads for large images). WSL2 remains the single issue with no viable upstream solution—the recommendation is to treat WSL2 as a container runtime rather than a bootc deployment target. The composefs-native backend transition is the most significant architectural change on the horizon, and MiOS should track [bootc-dev/bootc#1190](https://github.com/bootc-dev/bootc/issues/1190) to prepare for filesystem semantics changes in upcoming releases.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
