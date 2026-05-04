# 'MiOS' -- Package Manifest (single source of truth for image RPMs)
> **Attribution:** MiOS-DEV (Administrative Alias)
> **Infrastructure:** 'MiOS' Open-Source Build Pipeline
> **License:** Apache-2.0 (Open-Source Infrastructure)

---

## DELIVERY POLICY (project-wide invariant)

Every software artifact in MiOS ships as **one of three formats**:

| Format | What goes here | Where it's defined |
|---|---|---|
| **Flatpak** | User-facing applications (GUI apps, games, IDEs, file managers, terminal emulators, viewers, editors, gaming clients, virt GUIs). | `mios-bootstrap/mios.toml` `[desktop].flatpaks` → `MIOS_FLATPAKS` build-arg → `/usr/lib/mios/env.d/flatpaks.env` → `mios-flatpak-install` at first boot. |
| **Container** (Quadlet / Podman / Distrobox) | Long-lived services and isolated workloads (LocalAI, Ollama, Forgejo, Ceph daemons, k3s workloads, AI CLI agents, NUT). | `etc/containers/systemd/*.container` (Quadlet) or `usr/share/distrobox/`. |
| **VM** (libvirt / QEMU) | Heavyweight guest workloads needing a full guest OS (Windows guests, legacy distros, hardware-emulation testbeds). | Driven by libvirt/QEMU from the host substrate. |

**RPM (this file)** is reserved strictly for the **irreducible host
substrate** — the minimum set required for the three delivery formats
above to function. That means: kernel + drivers + firmware, boot
tooling, init / PID-1, system libraries, system daemons, the runtimes
themselves (Podman/bootc, Flatpak/portals, libvirt/QEMU), display-
server foundation, host-scope security daemons, filesystem drivers,
core CLI admin tools, and image-build toolchain.

**Before adding any RPM to this file:** ask "is this an app, a service,
or a guest workload?" If yes to any, it does NOT belong here — route
it to the appropriate Flatpak / Container / VM channel above. Repos
in `automation/05-enable-external-repos.sh` follow the same rule:
no application RPM repos (the VSCodium repo was removed for this
reason).

**SECUREBOOT NOTE:** Proprietary NVIDIA drivers are included as
essential RPM artifacts for Microsoft-compliant SecureBoot verification.
Steam ships exclusively as a Flatpak (`com.valvesoftware.Steam`).

---

# 'MiOS' v0.2.0 -- Package Manifest

This file is both documentation and the **single source of truth** for all RPM packages installed in MiOS.
Build scripts parse the fenced code blocks below using `scripts/lib/packages.sh`.
To add a package, add it to the appropriate section. One package per line.
Apps go in `mios.toml` `[desktop].flatpaks`, services in `etc/containers/systemd/`.

**CHANGELOG v0.2.0:**
- Standardized versioning across the entire stack.
- Added uupd (unified updater replacing bootc-fetch-apply-updates.timer)
- Added greenboot + greenboot-default-health-checks (auto-rollback on boot failure)
- Added cosign (signed image verification for `bootc switch --enforce-container-sigpolicy`)
- Added toolbox (companion to existing distrobox)
- Added kubectl, helm (client tooling; k3s binary still from rancher install)
- Added podman-plugins, podman-docker, containers-common
- Added nvidia-container-selinux (missing SELinux policy for toolkit on bootc)
- Added steam-devices (udev rules for controllers)
- Added aide, openscap-scanner, scap-security-guide, libpwquality, setools-console, nftables (security)
- Added cloud-init, wslu, python3-pip, libei (Podman-machine + WSL + desktop input)
- Added freerdp, freerdp-libs, virt-viewer, qemu-device-display-virtio-gpu (remote/display)
- NEW SECTION: packages-updater (uupd + greenboot) wired into 43-uupd-installer.sh
- Fix: Containerfile removed external akmods FROM stages (ucore-hci bakes NVIDIA in)
- Fix: scripts/41-47 no longer duplicate dnf installs - PACKAGES.md is now the
       sole source of truth; 40-series scripts handle config+services only
- Added missing audited tools: strace, lsof, iotop, ntfs-3g, efibootmgr, nm-connection-editor

**CHANGELOG v0.2.0 (previous):**
- Added bootupd (unified bootloader updates -- Fedora 44 phase 1)
- Added dnf5-plugins (versionlock support for critical package pinning)
- Added systemd-boot-unsigned (UKI preparation -- future composefs+UKI chain)
- Added libsss_nss_idmap (fixes sssd-related dep resolution on F44)
- Added tpm2-tools (TPM2 support for measured boot / future attestation)
- Added clevis, clevis-luks (automated LUKS unlock via TPM2/Tang)
- Moved driverctl from security to utils (better categorization)

**CHANGELOG v0.2.0 (previous):**
- Removed htop (use btop instead)
- Added nvidia-settings to NVIDIA section
- Added avahi/nss-mdns for .local network discovery
- Added network-discovery package section

---

## Repositories

RPMFusion Free + Nonfree for NVIDIA drivers and multimedia codecs.
CrowdSec official repo with Fedora 40 fallback for Rawhide compatibility.

```packages-repos
rpmfusion-free-release-rawhide
rpmfusion-nonfree-release-rawhide
fedora-workstation-repositories
dnf-plugins-core
dnf5-plugins
```

## Base -- Security Stack (installed pre-pipeline)

Installed by Containerfile before automation/build.sh runs because every
later phase assumes SELinux tooling, audit, fapolicyd, crowdsec, and
usbguard are already present. Strict install: a missing package here is a
build failure, not a silent skip.

```packages-base
policycoreutils-python-utils
selinux-policy-targeted
firewalld
audit
fapolicyd
crowdsec
usbguard
# D-Bus: dbus-broker (CoreOS default) is the system bus on every
# deployment shape, including WSL. The WSL audit-subsystem-stripped
# kernel is handled by usr/lib/systemd/system/dbus-broker.service.d/
# 10-mios-no-audit.conf, which drops `--audit` from the broker's
# ExecStart. The legacy /usr/bin/dbus-daemon package is intentionally
# NOT installed -- shipping both broker and reference daemon would
# create a unit-file conflict (alias dbus.service -> two providers).
```

## Moby -- Docker-compatible engine

Installed by automation/21-moby-engine.sh.

```packages-moby
moby-engine
```

## UKI -- Unified Kernel Image tooling

Installed by automation/23-uki-render.sh.

```packages-uki
systemd-ukify
```

## SBOM -- Software Bill of Materials tooling

Installed by automation/90-generate-sbom.sh.

```packages-sbom-tools
syft
```

## K3s SELinux build dependencies

Installed by automation/19-k3s-selinux.sh to build the k3s SELinux module.

```packages-k3s-selinux-build
selinux-policy-devel
git
make
```

## Kernel

Kernel extras + development headers for akmod-nvidia and DKMS builds.
Base kernel ships with fedora-bootc:rawhide -- NEVER upgrade it in-container.
Upgrading triggers dracut under tmpfs which breaks the initramfs.

```packages-kernel
kernel-modules-extra
kernel-devel
kernel-headers
kernel-tools
glibc-headers
glibc-devel
python3
```

## GNOME 50 Desktop

MINIMAL GNOME shell -- infrastructure ONLY. **PROJECT INVARIANT:**
applications ship as Flatpaks (see `mios.toml` `[desktop].flatpaks`),
only system dependencies ship as RPMs. No exceptions.

GNOME 49+: systemd is a HARD dependency. gnome-session's built-in service
manager was removed. Full systemd user session support is required.
GNOME 50: X11 session removed upstream. Wayland-only (Fedora 43+ dropped X11).

```packages-gnome
# ── Core shell (auto-pulls: mutter, gjs, gtk4, libadwaita, gnome-desktop4,
#    gnome-session, gnome-settings-daemon, gsettings-desktop-schemas, colord,
#    dconf, adwaita-icon-theme, adwaita-cursor-theme, pipewire, polkit) ──
gnome-shell
gnome-session-wayland-session
gnome-control-center
gnome-keyring
gdm
# ── System services (NOT apps) ──
# gnome-remote-desktop is a systemd-managed RDP/VNC service, not a user app.
gnome-remote-desktop
# Theme/wallpaper data, not an executable app.
gnome-backgrounds
# ── Application RPMs removed per project invariant ──
# ptyxis           -> Flathub: org.gnome.Ptyxis
# nautilus         -> Flathub: org.gnome.Nautilus
# gnome-software   -> Flathub: org.gnome.Software (native GNOME, already in mios.toml)
# ── Extensions ──
gnome-shell-extension-appindicator
gnome-shell-extension-dash-to-dock
# ── Portals ──
xdg-user-dirs
xdg-utils
xdg-desktop-portal
xdg-desktop-portal-gnome
xdg-desktop-portal-gtk
# ── Audio ──
pipewire-alsa
pipewire-pulseaudio
wireplumber
# ── GStreamer (MUST be explicit -- ucore fc43 base ships older GStreamer that
#    is ABI-incompatible with GNOME 50. Without these, gnome-shell crashes on
#    launch with "undefined symbol: gst_state_get_name" in libgstplay) ──
gstreamer1
gstreamer1-plugins-base
gstreamer1-plugins-good
# ── Hardware ──
upower
gnome-bluetooth
bluez
bluez-tools
# ── Flatpak (gnome-software manages these -- no rpm-ostree plugin needed) ──
flatpak
# ── Filesystem access ──
gvfs
gvfs-smb
gvfs-mtp
# ── Networking ──
NetworkManager-wifi
NetworkManager-openvpn-gnome
nm-connection-editor
# ── Locale ──
glibc-langpack-en
# ── Qt Adwaita theming ──
qt6-qtbase-gui
qt6-qtwayland
qadwaitadecorations-qt5
adw-gtk3-theme
```

## GNOME Flatpak Runtime -- portals + audio + theming for Flatpaks via WSLg

The MiOS-DEV podman backend (Windows-side) does not host its own
GNOME session -- WSLg is the Windows compositor and operators see
Flatpaks (Ptyxis terminal, Nautilus file manager, Software app store,
Epiphany browser, Flatseal permissions UI) as Windows windows routed
through the WSLg portal. Those Flatpaks ship their own GTK/libadwaita
via `org.gnome.Platform`, but they still need a **host portal +
audio router + Qt-Adwaita theming** so file dialogs, drag-and-drop,
audio output, and consistent theming all work. This section is the
**runtime-only** subset of `packages-gnome` -- the bits required for
Flatpaks to function on the dev VM, with **no display manager, no
gnome-shell, no GDM, no session services**.

Deployed bare-metal / Hyper-V / QEMU MiOS hosts install
`packages-gnome` (full session) instead.

```packages-gnome-flatpak-runtime
# ── Portals: file dialogs / drag-and-drop / desktop integration ──
xdg-user-dirs
xdg-utils
xdg-desktop-portal
xdg-desktop-portal-gnome
xdg-desktop-portal-gtk
# ── Audio: PipeWire is the host router; Flatpaks bind to it via
#    portal sockets ──
pipewire-alsa
pipewire-pulseaudio
wireplumber
# ── GStreamer base: required by libsoup / libgweather inside
#    Flatpak runtimes for media-rendering helpers ──
gstreamer1
gstreamer1-plugins-base
gstreamer1-plugins-good
# ── GVFS: lets Nautilus / Software / Ptyxis traverse SMB / MTP /
#    other backend filesystems via the host ──
gvfs
gvfs-smb
gvfs-mtp
# ── Locale ──
glibc-langpack-en
# ── Qt Adwaita theming -- so Qt apps (e.g. Wireshark Flatpak)
#    match GNOME look on WSLg ──
qt6-qtbase-gui
qt6-qtwayland
qadwaitadecorations-qt5
adw-gtk3-theme
# ── Flatpak itself; org.gnome.Software (Flathub) handles install/upgrade ──
flatpak
```

## GNOME Core Apps -- DO NOT INSTALL AS RPM

**PROJECT INVARIANT:** GNOME Core apps are user-facing applications and
ship STRICTLY as Flatpaks. Add the Flathub ref to `mios.toml`
`[desktop].flatpaks` instead of uncommenting an RPM here.

| RPM (do not use) | Flathub ref |
|---|---|
| papers              | org.gnome.Papers |
| loupe               | org.gnome.Loupe |
| showtime            | org.gnome.Showtime |
| gnome-text-editor   | org.gnome.TextEditor |
| gnome-disk-utility  | org.gnome.DiskUtility |
| gnome-system-monitor| (not on Flathub; use `btop`/`nvtop` CLI) |
| baobab              | org.gnome.baobab |
| gnome-connections   | org.gnome.Connections |
| gnome-tweaks        | (use Flathub: com.mattjakeman.ExtensionManager) |
| file-roller         | org.gnome.FileRoller |
| gnome-calculator    | org.gnome.Calculator |
| gnome-calendar      | org.gnome.Calendar |
| gnome-contacts      | org.gnome.Contacts |
| gnome-clocks        | org.gnome.clocks |
| gnome-weather       | org.gnome.Weather |
| gnome-maps          | org.gnome.Maps |
| gnome-characters    | org.gnome.Characters |
| gnome-font-viewer   | org.gnome.FontManager |
| gnome-music         | org.gnome.Music |
| snapshot            | org.gnome.Snapshot |
| decibels            | org.gnome.Decibels |
| cheese              | org.gnome.Cheese |
| gnome-logs          | org.gnome.Logs |
| deja-dup            | org.gnome.DejaDup |
| simple-scan         | org.gnome.SimpleScan |
| seahorse            | org.gnome.seahorse.Application |
| gnome-boxes         | org.gnome.Boxes |

```packages-gnome-core-apps
# Intentionally empty. See table above; install via mios.toml flatpaks.
```

## GPU Drivers -- Mesa (AMD / Intel / software fallback)

Universal Mesa stack supporting all AMD and Intel GPUs out of the box.
Mesa 26: ACO is now default shader compiler for RadeonSI.

```packages-gpu-mesa
mesa-vulkan-drivers
mesa-dri-drivers
mesa-va-drivers
vulkan-loader
vulkan-tools
libva-utils
linux-firmware
# microcode_ctl removed: redundant on F44+
```

## GPU Drivers -- AMD Compute (optional, fault-tolerant)

ROCm OpenCL/HIP for AMD compute workloads.

```packages-gpu-amd-compute
rocm-opencl
rocm-hip
rocm-runtime
rocm-smi
rocminfo
```

## GPU Drivers -- Intel Compute (oneAPI Level Zero)

Intel GPU compute runtime for OpenCL and Level Zero API.
Supports Intel Arc, Iris Xe, and integrated GPUs.
All packages are in official Fedora repos -- no extra repo needed.

```packages-gpu-intel-compute
intel-compute-runtime
intel-media-driver
# level-zero REMOVED: not in F44 repos as standalone package.
# intel-gpu-tools REMOVED: needs libproc2.so.0 missing in F44.
```

## GPU Drivers -- NVIDIA (akmod, builds for any NVIDIA card)

NVIDIA proprietary drivers via RPMFusion akmod. Builds kmod at image time.
Driver 590+: Open kernel modules are DEFAULT for Turing (RTX 20+) and newer.
Blackwell (RTX 50): Open modules are the ONLY option -- proprietary incompatible.
WARNING: RTX 50-series has a VFIO reset bug -- see /usr/share/doc/mios-vfio-warning.txt
CDI is now the default mode in nvidia-container-toolkit v1.19+.

```packages-gpu-nvidia
akmod-nvidia
xorg-x11-drv-nvidia-cuda
nvidia-container-toolkit
nvidia-persistenced
nvidia-settings
xorg-x11-drv-nvidia-power
# v2.2 additions
nvidia-container-selinux
```

## Virtualization -- KVM / QEMU / Libvirt

System-level KVM stack: hypervisor, libvirt daemon, firmware, CLI helpers.
GUI front-ends ship as Flatpaks per project invariant -- see `mios.toml`
`[desktop].flatpaks` (`org.virt_manager.Manager`,
`org.remmina.Remmina` for VNC/SPICE/RDP viewer needs).

```packages-virt
qemu-kvm
libvirt
libvirt-daemon
virt-install
edk2-ovmf
swtpm
swtpm-tools
dnsmasq
mdevctl
libguestfs-tools
# v2.2 additions
virt-v2v
qemu-device-display-virtio-gpu
virt-firmware
python3-cryptography
# ── Application RPMs removed per project invariant ──
# virt-manager  -> Flathub: org.virt_manager.Manager
# virt-viewer   -> Flathub: org.remmina.Remmina (covers SPICE/VNC/RDP)
```

## Container Runtime

Podman, Buildah, Skopeo, bootc tooling, and OCI image building.

```packages-containers
podman
podman-compose
buildah
skopeo
bootc
osbuild
osbuild-composer
osbuild-selinux
composer-cli
rpm-ostree
crun
netavark
aardvark-dns
slirp4netns
composefs
container-selinux
qemu-img
image-builder
bootc-image-builder
dracut-live
squashfs-tools
containers-common
toolbox
kubectl
helm
podman-plugins
cosign
# Build toolchain moved to `packages-build-toolchain` (image-build only;
# stripped by automation/91-strip-build-toolchain.sh before image commit
# so the deployed runtime carries no compilers).
# REMOVED -- podman-docker: conflicts with moby-engine from ucore-hci base
```

## Build Toolchain (image-build time ONLY)

These compilers and devel headers are required by image-build phases
(`19-k3s-selinux.sh` builds the k3s SELinux policy module,
`53-bake-lookingglass-client.sh` compiles Looking Glass B7 from source)
but **do not belong on the runtime image** -- a deployed host carrying
gcc/cmake/golang is unnecessary attack surface for any process that
gets a shell.

`automation/12-virt.sh` installs this block early, the build phases
that need it consume it, and `automation/91-strip-build-toolchain.sh`
removes it after `90-generate-sbom.sh` records the versions and before
`99-cleanup.sh` runs. The block is also in the FHS-install exclude
list (`mios-bootstrap/build-mios.sh`) so a deployed FHS host never
installs it in the first place.

```packages-build-toolchain
make
gcc
gcc-c++
cmake
golang
selinux-policy-devel
binutils
pkgconf-pkg-config
```

## Self-Building Tools (Experimental/Repository dependent)

Tools needed for the image to rebuild itself. May fail if specialized repos
are not enabled.

```packages-self-build
bootc-base-imagectl
konflux-image-tools
```

## Boot & Update Management

Bootloader updates and system update tooling for bootc systems.
bootupd: unified bootloader update service (Fedora 44 phase 1).
dnf5-plugins: versionlock for pinning critical packages (Mesa, PipeWire, etc.)

```packages-boot
bootupd
dnf5-plugins
systemd-boot-unsigned
efibootmgr
systemd-ukify
binutils
efitools
sbsigntools
tpm2-tss
```

## Cockpit Web Management

Full Cockpit ecosystem with file browser and all plugins.
cockpit-pcp removed (PCP metrics now native in cockpit-bridge since Cockpit 326).

```packages-cockpit
cockpit
cockpit-system
cockpit-ws
cockpit-bridge
cockpit-storaged
cockpit-networkmanager
cockpit-podman
cockpit-machines
cockpit-ostree
cockpit-selinux
cockpit-files
pcp
pcp-system-tools
```

## Windows Interop & Remote Desktop

Tools for Hyper-V Enhanced Session, SMB, and native RDP.

```packages-wintools
hyperv-tools
samba
samba-client
cifs-utils
# freerdp-libs stays as a system library (gnome-remote-desktop and other
# host services link against it). The freerdp CLI client itself was an
# application -- removed per project invariant; use org.remmina.Remmina
# (already in mios.toml [desktop].flatpaks) for RDP/SPICE/VNC.
freerdp-libs
```

## Security

Host-based IPS, application whitelisting, USB device control.
CRITICAL: nvidia-container-toolkit >= v1.17.8 required (CVE-2025-23266/23267).

```packages-security
crowdsec
crowdsec-firewall-bouncer-nftables
firewalld
fapolicyd
fapolicyd-selinux
usbguard
setroubleshoot-server
policycoreutils-python-utils
audit
tpm2-tools
clevis
clevis-luks
# v2.2 additions
aide
openscap-scanner
scap-security-guide
libpwquality
nftables
policycoreutils
setools-console
cosign
# v2.3 additions
# iptables-legacy: WSL2 kernel does NOT support nftables. Without this package
#   iptables-nft fails and Podman networking breaks inside WSL. Safe on bare
#   metal - coexists with nftables, only invoked when WSLInterop is detected.
iptables-legacy
```

## Gaming

Gaming clients and Wine ship STRICTLY as Flatpaks per project invariant.
This section retains only the system-level pieces that Flatpak gaming
clients depend on (gamemode daemon, vulkan tooling, controller udev
rules, the gamemode shell extension).

NTSYNC kernel module available in Fedora 44 for improved Wine/Steam
performance via the Steam Flatpak's bundled Proton.

```packages-gaming
# ── System daemons / shell extension / udev (NOT apps) ──
gamemode
gnome-shell-extension-gamemode
vulkan-tools
steam-devices
# ── Application RPMs removed per project invariant ──
# steam            -> Flathub: com.valvesoftware.Steam (bundles Proton)
# lutris           -> Flathub: net.lutris.Lutris
# dosbox-staging   -> Flathub: io.github.dosbox_staging.dosbox-staging
# protontricks     -> Flathub: com.github.Matoking.protontricks
# mangohud         -> Flathub extension: org.freedesktop.Platform.VulkanLayer.MangoHud
# gamescope        -> shipped inside Steam Flatpak; install separately only if
#                     a non-Steam Wayland gaming session is required (then via
#                     Flathub: org.gamescope.Session if/when published)
# wine, wine-mono, wine-dxvk, winetricks
#                  -> non-Steam Windows apps: Flathub com.usebottles.bottles
#                     (bundles its own Wine/DXVK/winetricks)
```

## Guest Agents

Hypervisor integration services for VMs.

```packages-guests
qemu-guest-agent
hyperv-daemons
open-vm-tools
spice-vdagent
spice-webdavd
libvirt-nss
```

## Storage

Distributed/shared storage, multipath, iSCSI.

```packages-storage
nfs-utils
rpcbind
glusterfs
glusterfs-fuse
glusterfs-server
ceph-common
iscsi-initiator-utils
targetcli
device-mapper-multipath
sg3_utils
lvm2
stratis-cli
stratisd
xfsprogs
btrfs-progs
e2fsprogs
mdadm
ntfs-3g
```

## Ceph Distributed Storage

Cephadm orchestrator + CephFS kernel client for native distributed storage.
All Ceph server daemons (MON/OSD/MGR/MDS) run as Podman containers via cephadm.

```packages-ceph
ceph-common
cephadm
ceph-fuse
ceph-selinux
```

## K3s Lightweight Kubernetes

K3s binary is downloaded directly (not via dnf).
k3s-selinux only exists for RHEL/CentOS -- not available on Fedora Rawhide.

```packages-k3s
container-selinux
```

## High Availability -- Pacemaker / Corosync

Full HA cluster stack with fence agents and SBD.

```packages-ha
pacemaker
corosync
pcs
fence-agents-all
fence-virt
resource-agents
sbd
booth
booth-core
booth-test
dlm
corosync-qdevice
corosync-qnetd
libqb
libibverbs
```

## CLI Utilities

Common command-line tools and system utilities.

```packages-utils
git
tmux
vim-enhanced
wget2-wget
curl
btop
nvtop
fastfetch
lm_sensors
smartmontools
tuned
tuned-ppd
fuse
fuse3
7zip-standalone
unzip
zstd
rsync
tree
jq
yq
bc
patch
openssl
distrobox
just
driverctl
tmt
ansible-core
# v2.2 additions
wslu
python3-pip
# /usr/bin/mios (Python CLI) imports the 'requests' module. Without
# this package the import fails at runtime and a pip install isn't
# viable on the read-only composefs /usr surface.
python3-requests
cloud-init
libei
strace
lsof
iotop
# v2.4 Universal Para-virt additions
socat
syft
oras-cli
```

## Android -- Waydroid

Waydroid container runtime for Android apps.
Note: NVIDIA GPUs lack full 3D acceleration in Waydroid (Mesa/AMD/Intel only).

```packages-android
waydroid
```

## Looking Glass B7 -- Build Dependencies

These packages are installed during the build to compile Looking Glass B7.
They are REMOVED after compilation to keep the image small.

```packages-looking-glass-build
cmake
gcc
gcc-c++
make
binutils
pkgconf-pkg-config
libglvnd-devel
fontconfig
fontconfig-devel
spice-protocol
nettle-devel
gnutls-devel
libXi-devel
libXinerama-devel
libXcursor-devel
libXpresent-devel
libXScrnSaver-devel
libxkbcommon-x11-devel
wayland-devel
wayland-protocols-devel
libdecor-devel
pipewire-devel
libsamplerate-devel
```

## Cockpit Plugin Build Dependencies

Build dependencies for Cockpit plugins from git.

```packages-cockpit-plugins-build
npm
gettext
```

## Network Discovery -- Avahi / mDNS

mDNS/DNS-SD for automatic .local hostname discovery on LAN.
Every 'MiOS' instance advertises Cockpit and RDP services.

```packages-network-discovery
avahi
avahi-tools
nss-mdns
```


### Phosh (Mobile Session)
```packages-phosh
phosh
phoc
gnome-calls
feedbackd
```

## Updater -- uupd / Greenboot (v2.2)

uupd is the Universal Blue unified updater. It replaces `bootc-fetch-apply-updates.timer`,
flatpak update timer, and distrobox update timer with a single Go binary that
handles all three. Ships via ublue-os/packages COPR (enabled in 05-enable-external-repos.sh).

Greenboot provides health-check driven auto-rollback: 3 failed boots triggers
`bootc rollback` via grub boot_counter. Health checks live in /etc/greenboot/check/{required,wanted}.d/.

```packages-updater
uupd
greenboot
greenboot-default-health-checks
```

---

## FreeIPA & SSSD
Zero-touch enrollment and identity management.

```packages-freeipa
freeipa-client
sssd
sssd-tools
libsss_nss_idmap
```

## AI Tools
Rust-based LLM CLI agents and shell integrations.

`aichat` and `aichat-ng` are NOT Fedora RPMs -- they ship as static
musl binaries fetched by `automation/37-aichat.sh` from upstream
GitHub releases. They are user-facing CLI applications and should
run inside a Distrobox container per the project invariant
(VM | Container | Flatpak only). The current direct-to-`/usr/bin`
install is a transitional state; an open task is to wrap these
agents in a Distrobox container so the host substrate carries no
application binaries.

```packages-ai
# python3-openai: official OpenAI Python SDK, used by /usr/bin/mios to
# drive the local OpenAI-API-compatible endpoint at MIOS_AI_ENDPOINT.
# The SDK provides the streaming + tool-call roundtrip + structured-
# outputs surface that maps onto Architectural Law 5. F44+ ships the
# SDK in repos as python3-openai; we install via dnf rather than pip
# so it is captured by the image SBOM.
#
# aichat/aichat-ng install via 37-aichat.sh (musl tarball -> /usr/bin).
# Migrate to Distrobox in a follow-up.
python3-openai
```
<!--
  ollama is NOT a Fedora RPM; it ships as a tarball from
  https://github.com/ollama/ollama/releases and is fetched by
  automation/37-ollama-prep.sh at build time. The runtime container
  also has its own ollama binary baked into the docker.io/ollama/
  ollama image used by the mios-ollama Quadlet -- both are
  ARM/x86_64-multi-arch and share the same model store at
  /usr/share/ollama/models (build-baked) and /var/lib/ollama/models
  (runtime, hardlink-seeded by mios-ollama-firstboot.service).
-->

## Internal -- Critical Validation

These packages MUST be present in the final image. Build scripts use this
section for post-build verification.

```packages-critical
gnome-shell
gdm
podman
bootc
libvirt
kernel-core
firewalld
cockpit
NetworkManager
pipewire
tuned
chrony
openssh-server
```

## Internal -- Bloat Removal

These packages are explicitly removed during the build to keep the image
lean and free of unwanted UI components.

```packages-bloat
malcontent-control
malcontent-pam
malcontent-tools
gnome-tour
gnome-initial-setup
PackageKit
PackageKit-command-not-found
```

## Network UPS Tools (NUT)

Managed via Distrobox container to decouple hardware config from immutable core.

```packages-nut
nut
nut-client
nut-xml
usbutils
```

---
### Bootc ecosystem & resources

- bootc: <https://github.com/containers/bootc>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- bootc docs: <https://bootc-dev.github.io/bootc/>
- Universal Blue (uCore base): <https://github.com/ublue-os/main>
- uupd: <https://github.com/ublue-os/uupd>
- rechunk: <https://github.com/hhd-dev/rechunk>
- cosign: <https://github.com/sigstore/cosign>
- Project repo: <https://github.com/mios-dev/mios>
- **Sole Proprietor:** MiOS-DEV
---
