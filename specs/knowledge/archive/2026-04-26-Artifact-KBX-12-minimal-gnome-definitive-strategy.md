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

# Minimal GNOME for Fedora Rawhide bootc: the definitive package strategy

**The absolute minimum GNOME Wayland desktop on Fedora Rawhide (fc45/GNOME 50) requires approximately 25 explicitly installed RPM packages** — everything else resolves as hard dependencies. The critical technique is `--setopt=install_weak_deps=False`, which prevents DNF from pulling hundreds of Recommends/Suggests packages. The single most dangerous removal on Fedora is `malcontent`: its shared library (`malcontent-libs`) is a **compile-time hard dependency** of `gnome-control-center`, which chains upward to `gnome-shell` and `gdm`. Every other GNOME application — from gnome-tour to Firefox — can be safely removed without cascade. Universal Blue projects (Bluefin, Bazzite) do not actually strip GNOME; they build additive layers on full Silverblue images. For MiOS, the correct pattern is building from the bare `quay.io/fedora/fedora-bootc` base and installing individual packages rather than using `@gnome-desktop`.

---

## The 25-package minimal GNOME desktop

Starting from the bare `quay.io/fedora/fedora-bootc:45` image, the following explicit install list produces a fully functional GNOME Wayland desktop with GDM, all portals, audio, Bluetooth, networking, security, and proper theming. GNOME 50 ("Tokyo") is **Wayland-only** — the `gnome-session-xsession` package no longer exists on fc45, so there is zero X11 session overhead.

```dockerfile
FROM quay.io/fedora/fedora-bootc:45

RUN dnf install -y --setopt=install_weak_deps=False \
    gnome-shell \
    gdm \
    gnome-session-wayland-session \
    gnome-control-center \
    xdg-desktop-portal \
    xdg-desktop-portal-gnome \
    xdg-desktop-portal-gtk \
    gnome-keyring \
    gnome-keyring-pam \
    pipewire-pulseaudio \
    wireplumber \
    bluez \
    NetworkManager \
    NetworkManager-wifi \
    NetworkManager-config-connectivity-fedora \
    power-profiles-daemon \
    adw-gtk3 \
    adwaita-qt5 \
    adwaita-qt6 \
    qadwaitadecorations-qt5 \
    qadwaitadecorations-qt6 \
    xdg-user-dirs \
    xdg-user-dirs-gtk \
    dejavu-sans-fonts \
    dejavu-sans-mono-fonts \
    Legacy-Cloud-noto-emoji-color-fonts \
    && dnf clean all

RUN systemctl enable gdm.service && \
    systemctl set-default graphical.target
```

The `--setopt=install_weak_deps=False` flag is **non-negotiable for minimalism**. Without it, DNF pulls in hundreds of Recommends packages including Xwayland, various input drivers, and utilities that inflate the image. When `gnome-shell` is installed, it automatically resolves `mutter`, `gnome-session`, `gnome-settings-daemon`, `gjs`, `gnome-desktop4`, `gsettings-desktop-schemas`, `pipewire` (via mutter), `libadwaita`, `cantarell-fonts`, `colord`, and `libinput`. Installing `gnome-control-center` resolves `polkit`, `gnome-bluetooth`, `gnome-online-accounts`, `gnome-color-manager`, and `cups-pk-helper`. Installing `gdm` resolves `gnome-shell` and `gnome-session` again (already present). **No explicit installation of mutter, polkit, libadwaita, or gnome-settings-daemon is needed.**

One critical caveat: with weak deps disabled, `xorg-x11-server-Xwayland` may not be pulled in. If legacy X11 application support is needed (many Electron apps, older Java GUIs, Wine), add it explicitly. For a pure-Wayland target, it can be omitted. Similarly, `mesa-dri-drivers` and `mesa-vulkan-drivers` should be verified — GPU acceleration requires them, and they may not arrive as hard deps of mutter on all configurations.

### What breaks without each package

| Missing package | Failure mode |
|---|---|
| `gnome-session-wayland-session` | GDM displays **no session** — blank session list, cannot log in |
| `gnome-control-center` | No GUI settings — cannot configure Wi-Fi, displays, Bluetooth, or power |
| `xdg-desktop-portal-gnome` | Screen sharing fails in Firefox/Chrome; screenshot portal non-functional |
| `gnome-keyring-pam` | Keyring not auto-unlocked; prompted for keyring password every login |
| `pipewire-pulseaudio` | **Zero audio output** — apps speak PulseAudio protocol |
| `wireplumber` | PipeWire runs but audio devices are never routed to applications |
| `NetworkManager-wifi` | Wi-Fi networks invisible; only wired connections function |
| `adw-gtk3` | GTK3 apps (including RPM Firefox) visually inconsistent with GTK4 apps |

---

## The malcontent trap and other cascade dangers

The **most dangerous dependency chain** on Fedora Rawhide GNOME is confirmed active on `gnome-control-center-50.0-1.fc45`:

```
malcontent / malcontent-libs
    ↑ hard Requires (compile-time link against libmalcontent-0.so)
gnome-control-center-50.0-1.fc45
    ↑ hard Requires
gnome-shell-50.0-1.fc45
    ↑ hard Requires
gdm
```

Running `dnf remove malcontent` cascades to removing **27+ packages** including `gdm`, `gnome-shell`, `gnome-control-center`, `gnome-session`, and every shell extension. This exists because Fedora's `gnome-control-center.spec` uses `%bcond malcontent %[!0%{?rhel}]` — malcontent is enabled on Fedora and disabled on RHEL. The Users panel links against `libmalcontent-0.so` at compile time, creating an unbreakable runtime dependency. Fedora Bootc made this optional in gnome-control-center 42.3-2; **Fedora has not followed suit**.

**Safe workaround**: Remove only the user-facing malcontent components while keeping the library:
```bash
dnf remove -y malcontent-control malcontent-pam malcontent-tools
```
This strips the parental controls GUI and CLI tools but preserves `malcontent` and `malcontent-libs` that gnome-control-center needs. SecureBlue discovered this the hard way — their issue #609 documents restoring `malcontent-ui-libs` after the cascade broke their builds.

### Complete cascade danger map

| Package | Cascade result | Dependency type |
|---|---|---|
| `malcontent` or `malcontent-libs` | Removes gnome-control-center → gnome-shell → gdm → entire desktop | Hard `Requires` (compile-time) |
| `gnome-control-center` | Removes gnome-shell → gdm | Hard `Requires` |
| `gnome-settings-daemon` | Removes gnome-shell + gnome-control-center | Hard `Requires` |
| `mutter` | Removes gnome-shell → cascade above | Hard `Requires` |
| `gjs` | Removes gnome-shell → cascade above | Hard `Requires` (gjs >= v0.1.1) |

**Every other GNOME application is safe to remove.** All apps in the user's list — gnome-tour, gnome-text-editor, gnome-calculator, gnome-calendar, gnome-contacts, gnome-weather, gnome-maps, gnome-clocks, gnome-characters, gnome-font-viewer, gnome-system-monitor, gnome-disk-utility, baobab, cheese/snapshot, simple-scan, gnome-connections, totem/showtime, eog/loupe, evince/papers, file-roller, gnome-music, gnome-photos, rhythmbox, seahorse, deja-dup, gnome-boxes, gnome-logs, yelp, gnome-classic-session, all `gnome-shell-extension-*` packages, and Firefox — are standalone applications with no reverse dependencies from `gnome-shell`, `gdm`, or `mutter`. They can all be `dnf remove`d cleanly.

**One historical caveat**: Bug RHBZ#1955179 (2021) reported that removing `gnome-tour` cascaded to `gnome-initial-setup`. This was a packaging bug likely fixed in current Rawhide, but **always verify with `dnf remove --assumeno PACKAGE`** before committing to removal in a Containerfile.

### Recommended safe removal block for Containerfile

```dockerfile
RUN dnf remove -y \
    gnome-tour \
    gnome-initial-setup \
    gnome-classic-session \
    gnome-shell-extension-background-logo \
    gnome-shell-extension-apps-menu \
    gnome-shell-extension-places-menu \
    gnome-shell-extension-window-list \
    gnome-shell-extension-launch-new-instance \
    yelp \
    malcontent-control malcontent-pam malcontent-tools \
    && dnf clean all
```

---

## How Universal Blue actually handles this (they don't strip GNOME)

A key finding: **none of the Universal Blue projects build minimal GNOME images**. Bluefin, Bazzite, and the base Universal Blue images all use `ghcr.io/ublue-os/silverblue-main` as their foundation — a full Fedora Silverblue image with the complete `@gnome-desktop` package set already installed. Their approach is purely additive.

**Bluefin** delegates its build to numbered shell scripts (`build_files/base/04-packages.sh`, `18-workarounds.sh`, etc.) that add GNOME extensions (Logo Menu, Tailscale QS, AppIndicator), Extension Manager, Tailscale, Cockpit, Homebrew, and developer tooling. It is transitioning from `rpm-ostree` to `dnf5` (tracked in issue #1946). Bluefin's Flatpak strategy uses "Bazaar" as the app storefront with **14 default Flatpaks** pre-configured via `/etc/preinstall.d/`, and Flatpaks auto-update twice daily. Notably, Bluefin is prototyping **"Dakota"** (`@ublue-os/dakota`) — a distroless approach building from GNOME OS base images instead of Silverblue, which would be the first UBlue project to start minimal and build up.

**Bazzite** uses a large ~846-line multi-stage Containerfile with `dnf5` throughout. Its most interesting technique is **`dnf5 -y swap --repo=<repo>`** to replace upstream Fedora packages with custom/Valve-patched versions of wireplumber, pipewire, bluez, Xwayland, NetworkManager, and mesa. It locks these swapped packages with `dnf5 versionlock add` and sets repository priorities (Bazzite repos priority 1, Terra priority 3, Negativo17 priority 4, RPM Fusion priority 5). Bazzite does minimal removal — it removes `pipewire-config-raop` and `gamemode` — and relies on configuration overlays (dconf databases, gschema overrides) rather than package stripping.

**SecureBlue** uses BlueBuild YAML recipes rather than raw Containerfiles and focuses on **hardening rather than minimization**. It disables GNOME user extensions by default, disables Xwayland, removes `gnome-software` (later restored without the ostree backend), removes `sushi` and `gnome-photos`, and removes `gnome-tour`. SecureBlue explicitly dealt with the malcontent issue in issue #609, having to restore `malcontent-ui-libs` after cascading failures. Their planned switch to `--setopt=install_weak_deps=False` (issue #712) was closed as "not planned."

**The takeaway for MiOS**: Do not follow the UBlue pattern of layering on full Silverblue. Instead, start from the bare `fedora-bootc` image and install the **25 explicit packages** listed above. This produces a dramatically smaller image.

---

## Fedora package groups and the netinstall alternative

Fedora's comps system (maintained at `pagure.io/fedora-comps` in `comps-rawhide.xml.in`) defines three relevant tiers for GNOME:

The **`@gnome-desktop`** group contains mandatory packages (gnome-shell, gdm, gnome-control-center, nautilus, gnome-disk-utility, gnome-system-monitor, gnome-text-editor, gnome-calculator, gnome-logs, eog/loupe, evince/papers, file-roller, baobab, gnome-characters, gnome-font-viewer, gnome-initial-setup, gnome-classic-session, orca, xdg-desktop-portal-gnome), default packages (gnome-boxes, gnome-connections, gnome-maps, gnome-weather, gnome-clocks, gnome-contacts, cheese/snapshot, totem/showtime, rygel, sushi, NM VPN plugins), and optional packages.

Installing with `dnf group install gnome-desktop --setopt=group_package_types=mandatory` pulls only the mandatory tier — still far heavier than the 25-package approach because it includes apps like nautilus, gnome-disk-utility, gnome-system-monitor, gnome-calculator, gnome-text-editor, baobab, file-roller, orca, and gnome-initial-setup. The **`@workstation-product-environment`** adds `@firefox`, `@libreoffice`, `@multimedia`, `@printing`, `@fonts`, `@hardware-support`, and `@guest-desktop-agents` on top.

The **`@base-x`** group historically provided the Xorg display server stack (xorg-x11-drv-* drivers, xorg-x11-server-Xorg, etc.). For a Wayland-only GNOME 50 desktop, this group is unnecessary and wastes significant space. Skip it entirely for MiOS.

For Fedora Everything netinstall, the Anaconda Software Selection screen offers all environment groups. Selecting "Fedora Workstation" and unchecking optional groups gives a leaner install, but kickstart with `@gnome-desktop --nodefaults` is equivalent to the mandatory-only approach. The most minimal path remains individual package installation from `fedora-bootc`.

---

## The Flatpak-only application architecture

For a bootc image where all user applications come from Flatpak, the system divides cleanly into four layers:

**Kernel/firmware layer (RPM only)**: `kernel`, `linux-firmware`, GPU drivers (`mesa-dri-drivers`, `mesa-vulkan-drivers`, or `akmod-nvidia`), `bootc`, `ostree`.

**System services layer (RPM only)**: `systemd`, `NetworkManager`, `firewalld`, `fwupd`, `podman`, `buildah`, `skopeo`, `toolbox`/`distrobox`, SELinux policy packages. For virtualization: `libvirt`, `qemu-kvm`, `virt-manager`, `libvirt-daemon-config-network`, `guestfs-tools`. **virt-manager has no viable Flatpak** — it requires direct access to libvirt sockets, KVM kernel modules, and host-level bridge networking. GNOME Boxes exists on Flathub as a simplified alternative but still requires `libvirt` RPMs on the host.

**Desktop shell layer (RPM only)**: The 25 packages above, plus `nautilus` and `gvfs` backends (`gvfs-smb`, `gvfs-mtp`, `gvfs-goa`, `gvfs-nfs`). **Nautilus should remain an RPM** — it handles desktop integration, relies on host-level gvfs for network mounts (SMB, NFS, MTP, WebDAV), loads native extensions from `/usr/lib64/nautilus/extensions-4/`, and depends on `tracker-miners`/`localsearch` for file indexing. The Flatpak version is primarily for development testing and sandboxing limits cripple its functionality. Fedora Silverblue ships Nautilus as an RPM for the same reasons.

**Flatpak portal/integration layer (RPM only)**: `flatpak`, `xdg-desktop-portal`, `xdg-desktop-portal-gnome`, `xdg-desktop-portal-gtk`, `gnome-software` (for Flathub browsing). GNOME ships a default portal configuration at `/usr/share/xdg-desktop-portal/gnome-portals.conf` that routes to `gnome;gtk;` backends automatically when `XDG_CURRENT_DESKTOP=GNOME`.

**Flathub configuration** in the Containerfile:
```dockerfile
RUN flatpak remote-add --system --if-not-exists flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
RUN flatpak remote-modify --disable fedora || true
```

Disabling the filtered Fedora Flatpak remote and using unfiltered Flathub directly gives access to the full catalog. All user applications — Firefox, LibreOffice, media players, communication apps, development IDEs, GNOME circle apps (Calculator, Calendar, Maps, Weather, etc.) — install from Flathub. Essential companion Flatpaks include **Flatseal** (`com.github.tchx84.Flatseal`) for permission management and **Extension Manager** (`com.mattjakeman.ExtensionManager`) for GNOME Shell extension management.

### Qt theming environment variables

For Qt Adwaita integration to function, set these in `/etc/environment` or a profile script within the bootc image:
```
QT_QPA_PLATFORMTHEME=gnome
QT_WAYLAND_DECORATION=adwaita
QT_STYLE_OVERRIDE=adwaita
```

---

## Conclusion: a practical build strategy for MiOS

The optimal strategy for MiOS is **not** to install `@gnome-desktop` and then remove bloat — that fights Fedora's packaging assumptions and risks cascade traps. Instead, build from `fedora-bootc` and install the **25 explicit packages**, then add system infrastructure (podman, libvirt, virt-manager, fwupd, nautilus, gvfs backends). Use `--setopt=install_weak_deps=False` on every `dnf install` call. Never attempt to remove `malcontent` or `malcontent-libs` — only strip the UI components (`malcontent-control`, `malcontent-pam`, `malcontent-tools`). Pre-configure Flathub as the system-wide remote and ship zero user applications as RPMs. The resulting image will contain roughly **400–500 total packages** versus the **1,800+** in a full Fedora Workstation install — a 70%+ reduction in attack surface and image size while retaining complete GNOME desktop functionality, all XDG portals, full audio/Bluetooth/networking, proper theming across GTK3/GTK4/Qt, and seamless Flatpak integration.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
