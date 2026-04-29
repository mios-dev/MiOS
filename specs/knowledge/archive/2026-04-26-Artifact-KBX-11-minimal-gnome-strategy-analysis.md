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

# Minimal GNOME desktop strategy for MiOS

**A Fedora Rawhide bootc workstation needs exactly 30–35 core GNOME packages to deliver a fully functional shell, and everything else is removable bloat.** The official Fedora Workstation ostree config pulls in roughly 290 RPM packages across two auto-generated manifests, but the hard dependency chain from `gnome-shell` downward touches fewer than 20 libraries and daemons. The critical finding: **malcontent cannot be dnf-removed**, but `malcontent-control`, `malcontent-pam`, and `malcontent-tools` can be cleanly uninstalled via dnf, while `malcontent-libs` must remain because flatpak dynamically links against `libmalcontent-0.so.0`. This report extracts exact package lists from all four primary sources and delivers a production-ready Containerfile `RUN` block for building a stripped GNOME 50 bootc image.

## How Fedora CoreOS and the ostree config define "minimal"

Fedora CoreOS establishes the philosophical foundation: **"The Fedora CoreOS image is kept minimal by design."** Their treefile architecture uses three key mechanisms that directly apply to a desktop variant. First, `exclude-packages` in the treefile actively blocks packages from being pulled in as dependencies — if a manifest package hard-depends on an excluded package, the build fails; if it only recommends it, the recommendation is silently dropped. Second, `recommends: false` disables all weak dependency resolution, which is the single most impactful setting for preventing bloat. Third, CoreOS uses `postprocess-remove` to strip files after the OSTree commit is assembled.

The canonical Fedora Workstation ostree config at `pagure.io/workstation-ostree-config` generates its package lists automatically from `comps-sync.py` against the `workstation-product-environment` group in `fedora-comps`. The repo structure now uses `common.yaml` (base treefile settings), `common-desktop-pkgs.yaml` (packages shared across all Atomic Desktop variants, ~229 packages), and `gnome-desktop-pkgs.yaml` (GNOME-specific packages, ~62 packages). **Critically, `install_weak_deps` is set to `true`** in the official Silverblue config, which is why the installed image is so much larger than necessary. The `fedora-silverblue.yaml` top-level treefile adds variant-specific packages: `fedora-release-silverblue`, `desktop-backgrounds-gnome`, `gnome-shell-extension-background-logo`, `pinentry-gnome3`, `qgnomeplatform`, `evince-thumbnailer`, `evince-previewer`, and `totem-video-thumbnailer`.

The `gnome-desktop-pkgs.yaml` auto-generated manifest includes these GNOME packages (F42 era, regenerated via comps-sync regularly):

- **Core shell**: gdm, gnome-shell, gnome-control-center, gnome-settings-daemon, gnome-session-wayland-session, gnome-session-xsession, gnome-classic-session
- **System integration**: ModemManager, NetworkManager-adsl/-openconnect-gnome/-openvpn-gnome/-ppp/-pptp-gnome/-ssh-gnome/-vpnc-gnome/-wwan, avahi, dconf, glib-networking, polkit
- **Desktop apps (removable)**: gnome-browser-connector, gnome-color-manager, gnome-disk-utility, gnome-initial-setup, gnome-remote-desktop, gnome-software, gnome-system-monitor, gnome-terminal, gnome-terminal-nautilus, gnome-user-docs, gnome-user-share, orca, rygel, yelp
- **File system**: nautilus, gvfs-afc, gvfs-afp, gvfs-archive, gvfs-fuse, gvfs-goa, gvfs-gphoto2, gvfs-mtp, gvfs-smb
- **Libraries/infrastructure**: at-spi2-atk, at-spi2-core, fprintd-pam, gnome-backgrounds, gnome-bluetooth, gnome-themes-extra, libcanberra-gtk3, libproxy-duktape, librsvg2, libsane-hpaio, mesa-dri-drivers, mesa-libEGL, systemd-oomd-defaults, tracker, tracker-miners, xdg-desktop-portal, xdg-desktop-portal-gnome, xdg-desktop-portal-gtk, xdg-user-dirs-gtk
- **Fonts**: adobe-source-code-pro-fonts

The `common-desktop-pkgs.yaml` adds another ~229 packages including the full audio stack (now PipeWire, historically PulseAudio), extensive firmware packages, printing infrastructure (cups, hplip, gutenprint), IBus input methods, fonts, X.org drivers, and system tools. The excluded packages (from `common.yaml`) include `gstreamer1-plugin-openh264`, `mozilla-openh264`, `openh264`, `dnf`, `dnf-plugins-core`, `dnf5`, `dnf5-plugins`, `grubby`, `sdubby`, and `bootupd`.

## ucore's layered hierarchy pattern for selective packaging

Universal Blue's ucore project demonstrates the **layered image hierarchy** pattern: Fedora CoreOS → `ucore-minimal` → `ucore` → `ucore-hci`, where each layer adds only the packages needed for its use case. ucore uses `rpm-ostree install` (not dnf) since it builds on CoreOS, and applies `rpm-ostree cleanup -m` followed by `ostree container commit` for layer finalization. The key architectural lesson for a desktop variant is the **multi-stage COPY pattern** for kernel modules:

```dockerfile
COPY --from=ghcr.io/ublue-os/akmods:TAG / /tmp/akmods-common
RUN rpm-ostree install /tmp/rpms/ublue-os/ublue-os-akmods*.rpm
```

ucore-minimal adds only **10 packages** to the CoreOS base: bootc, firewalld, qemu-guest-agent, open-vm-tools, docker-buildx, docker-compose, podman-compose, tailscale, wireguard-tools, and tmux. Services are installed but **not enabled by default** — each requires explicit `systemctl enable`. The cockpit web interface notably runs as a podman container rather than an installed RPM, avoiding its dependency tree entirely. This "install-but-don't-enable" and "containerize-heavy-services" pattern maps directly to desktop image design: install GNOME shell infrastructure as RPMs, but deliver applications via Flatpak.

## Bluefin's build pipeline and package management patterns

Bluefin's Containerfile executes a single `RUN` directive that calls `/ctx/build_files/shared/build-base.sh`, using `--mount=type=cache,dst=/var/cache/libdnf5` and `--mount=type=cache,dst=/var/cache/rpm-ostree` for build caching, and `--mount=type=bind,from=ctx` to inject build files without baking them into the image. All scripts use **`set -eoux pipefail`** (note: `-x` for debug tracing, critical for build log visibility).

The build pipeline executes in strict numerical order: `00-image-info.sh` → `03-install-kernel-akmods.sh` → **`04-packages.sh`** (primary package management) → `05-override-install.sh` → `build-gnome-extensions.sh` → `08-firmware.sh` → **`17-cleanup.sh`** (service configuration and removal) → `18-workarounds.sh` → **`20-tests.sh`** (validation). Phase 1 of `build.sh` removes conflicting packages using `rpm -e --nodeps` before copying system files: specifically `ublue-os-just`, `ublue-os-signing`, and `fedora-logos` are force-removed to prevent conflicts with Bluefin's own replacements.

The `20-tests.sh` validation script enforces two arrays. **IMPORTANT_PACKAGES** (must be present, build fails if missing): `distrobox`, `fish`, `flatpak`, `mutter`, `pipewire`, `gnome-shell`, `ptyxis`, `gdm`, `systemd`, `tailscale`, `uupd`, `wireplumber`, `zsh`. **UNWANTED_PACKAGES** (must be absent, build fails if found) — the exact list could not be retrieved from the raw source, but the enforcement pattern is clear: `rpm -q "${package}"` success for an unwanted package aborts the build. Bluefin is actively transitioning from rpm-ostree to dnf5 for build scripts (tracked in issue #1946), and the broader ublue-os/main project completed this switch with v0.1.1.

**Bluefin's malcontent strategy is coexistence, not removal.** Release changelogs show malcontent being routinely updated alongside other packages (e.g., `malcontent v0.1.1-2 → v0.1.1-3`). Instead of fighting the dependency chain, Bluefin neutralizes unwanted behavior through GSettings schema overrides (e.g., `welcome-dialog-last-shown-version='4294967295'` to suppress the welcome dialog), desktop file overlays from `projectbluefin/common`, and replacing GNOME Software entirely with Bazaar as the application storefront.

## The malcontent dependency trap and its precise solution

The malcontent dependency chain is **gnome-shell → gnome-control-center → malcontent** (hard `Requires`). This exists because Fedora builds gnome-control-center with `-Dmalcontent=true` in the meson configuration, making the parental controls library a compile-time requirement. RHEL builds it with `-Dmalcontent=false`, avoiding the trap entirely. Attempting `dnf remove malcontent` on Fedora 42/43/Rawhide proposes removing **27 packages** including gdm, gnome-shell, gnome-control-center, gnome-session-wayland-session, all gnome-shell extensions, and critical daemons like power-profiles-daemon and switcheroo-control.

The package breakdown reveals the safe removal path:

| Package | Purpose | Safe to remove? |
|---------|---------|----------------|
| **malcontent** | Parental controls daemon + D-Bus service | Only via `rpm -e --nodeps` (gnome-control-center hard requires it) |
| **malcontent-libs** | Shared library (`libmalcontent-0.so.0`) | **NO — flatpak links against it; removal breaks ALL Flatpaks** |
| **malcontent-control** | GUI parental controls app | **YES — `dnf remove` works cleanly** |
| **malcontent-pam** | PAM module for parental controls | **YES — `dnf remove` works cleanly** |
| **malcontent-tools** | CLI tools for parental controls | **YES — `dnf remove` works cleanly** |
| **malcontent-ui-libs** | UI library for malcontent GUI | **YES — removed as unused dep when malcontent-control goes** |

Confirmed from Fedora Discussion (October 2025): **`sudo dnf remove malcontent-control malcontent-pam malcontent-tools`** executes cleanly and removes `malcontent-ui-libs` as an unused dependency, without cascading. The `malcontent` base package and `malcontent-libs` must remain. For a Containerfile build where you need the main `malcontent` daemon gone too, use `rpm -e --nodeps malcontent` after all dnf operations are complete, then add `malcontent` to `/etc/dnf/dnf.conf` exclude list to prevent reinstallation during updates.

## Every package that can be safely removed from GNOME 50

The following categorization is based on reverse-dependency analysis. **Category A packages are leaf applications with zero reverse dependencies on core GNOME** — removing them via `dnf remove` will never cascade.

**Category A — pure leaf applications (safe `dnf remove`):**
gnome-maps, gnome-weather, gnome-contacts, gnome-calendar, gnome-clocks, gnome-calculator, gnome-characters, gnome-connections, gnome-logs, gnome-font-viewer, gnome-text-editor, gnome-tour, gnome-system-monitor, totem (or showtime on F43+), cheese, loupe (image viewer, replaced eog), evince (or papers on F43+), simple-scan, baobab, gnome-boxes, gnome-music, gnome-user-share, gnome-photos (if present), rhythmbox (if present), epiphany/gnome-web (if present), gnome-user-docs, gnome-getting-started-docs

**Category B — utilities safe to remove with considerations:**
gnome-software (and gnome-software-rpm-ostree) — nothing in core GNOME depends on it; you lose GUI update notifications. yelp — help browser, leaf package, has known CVEs, actively proposed for removal from Silverblue. gnome-initial-setup — gdm only `Recommends` it (not hard requires); safe to remove after first boot or if user creation is handled in Containerfile. gnome-disk-utility — leaf app, useful but not required. gnome-color-manager — leaf, only needed for color profile management. gnome-remote-desktop — test with `dnf remove --assumeno` first; may cascade on some builds. orca — screen reader, leaf package unless accessibility is required. rygel — media server, leaf package. gnome-browser-connector — browser extension support, leaf.

**Category C — packages requiring `rpm -e --nodeps`:**
malcontent (the daemon only, after removing malcontent-control/pam/tools via dnf first). gnome-classic-session (if unwanted, test cascade first).

**Category D — hide with NoDisplay=true, do NOT remove:**
Any package where `dnf remove --assumeno` shows cascading into gnome-shell/gdm/mutter. Also use NoDisplay for packages you want invisible in the launcher but whose libraries are needed.

**MUST NOT remove (hard dependencies of gnome-shell/gdm/mutter):**
gnome-shell, mutter, gdm, gnome-session, gnome-settings-daemon, gnome-control-center, evolution-data-server, gjs, gnome-desktop4, gsettings-desktop-schemas, polkit/polkit-libs, xdg-desktop-portal-gnome, xdg-desktop-portal-gtk, xdg-user-dirs-gtk, tecla, upower, switcheroo-control, malcontent-libs, localsearch/tinysparql (removing breaks Nautilus search and Activities Overview), accountsservice/accountsservice-libs, webkitgtk6.0 (captive portal helper), gnome-bluetooth (if Bluetooth hardware is present), nautilus + gvfs stack

## Complete bloat removal script for the Containerfile

This script goes in a `RUN` block **after all packages are installed but before final cleanup/relayering**. It uses `set -euo pipefail` (drop `-x` for production or keep for debug). The approach: first do clean dnf removes of all leaf packages, then handle the malcontent trap with targeted rpm operations, then apply NoDisplay overrides for anything that can't be removed, then clean up.

```bash
RUN set -euo pipefail && \
    \
    # ============================================================
    # PHASE 1: Clean dnf removal of leaf GNOME applications
    # These have ZERO reverse dependencies on gnome-shell/gdm/mutter.
    # Using --setopt=install_weak_deps=False for any resolver ops.
    # --no-autoremove prevents pulling out shared libs still needed.
    # ============================================================
    dnf remove -y --setopt=install_weak_deps=False \
        gnome-maps \
        gnome-weather \
        gnome-contacts \
        gnome-calendar \
        gnome-clocks \
        gnome-calculator \
        gnome-characters \
        gnome-connections \
        gnome-logs \
        gnome-font-viewer \
        gnome-text-editor \
        gnome-tour \
        gnome-system-monitor \
        totem \
        cheese \
        loupe \
        evince \
        simple-scan \
        baobab \
        gnome-boxes \
        gnome-music \
        gnome-photos \
        rhythmbox \
        epiphany \
        gnome-user-share \
        gnome-user-docs \
        gnome-getting-started-docs \
        yelp \
        || true && \
    \
    # ============================================================
    # PHASE 2: Remove GNOME Software (replace with flatpak CLI or
    # a Flatpak storefront like Bazaar)
    # ============================================================
    dnf remove -y \
        gnome-software \
        gnome-software-rpm-ostree \
        || true && \
    \
    # ============================================================
    # PHASE 3: Remove optional system utilities
    # gnome-initial-setup: not needed if users are pre-created
    # gnome-remote-desktop: not needed for local workstation
    # orca: remove if accessibility not required
    # rygel: DLNA media server, not needed
    # gnome-color-manager: optional color calibration
    # gnome-browser-connector: optional browser extension bridge
    # ============================================================
    dnf remove -y \
        gnome-initial-setup \
        gnome-remote-desktop \
        orca \
        rygel \
        gnome-color-manager \
        gnome-browser-connector \
        || true && \
    \
    # ============================================================
    # PHASE 4: Handle the malcontent dependency trap
    # SAFE: dnf-remove the UI/PAM/tools components
    # malcontent-control, malcontent-pam, malcontent-tools can go.
    # malcontent-ui-libs auto-removes as unused dep.
    # KEEP: malcontent (daemon) — gnome-control-center hard requires
    # KEEP: malcontent-libs — flatpak links against libmalcontent-0.so.0
    # ============================================================
    dnf remove -y \
        malcontent-control \
        malcontent-pam \
        malcontent-tools \
        || true && \
    \
    # ============================================================
    # PHASE 5: Force-remove malcontent daemon (optional, aggressive)
    # Only if you want the daemon binary gone too.
    # gnome-control-center's Users panel will lose parental controls
    # entry but will otherwise function normally.
    # ============================================================
    rpm -e --nodeps malcontent 2>/dev/null || true && \
    \
    # ============================================================
    # PHASE 6: NoDisplay overrides for apps that can't be removed
    # These packages have libraries or integration points needed
    # by the core shell but show unnecessary launcher entries.
    # Write overrides to /usr/share/applications/ (immutable layer).
    # ============================================================
    HIDE_APPS=( \
        org.gnome.Nautilus \
    ) && \
    for app in "${HIDE_APPS[@]}"; do \
        desktop_file="/usr/share/applications/${app}.desktop"; \
        if [ -f "$desktop_file" ]; then \
            if ! grep -q "^NoDisplay=" "$desktop_file"; then \
                echo "NoDisplay=true" >> "$desktop_file"; \
            else \
                sed -i 's/^NoDisplay=.*/NoDisplay=true/' "$desktop_file"; \
            fi; \
        fi; \
    done && \
    \
    # ============================================================
    # PHASE 7: Prevent removed packages from returning on updates
    # Write excludes to dnf.conf so they don't get pulled back in
    # ============================================================
    if ! grep -q "^excludepkgs=" /etc/dnf/dnf.conf 2>/dev/null; then \
        echo "excludepkgs=malcontent" >> /etc/dnf/dnf.conf; \
    fi && \
    \
    # ============================================================
    # PHASE 8: Disable localsearch/tracker indexing without removing
    # (removing localsearch breaks Nautilus search + Activities)
    # ============================================================
    mkdir -p /etc/xdg/autostart && \
    for tracker_autostart in \
        localsearch-3.desktop \
        localsearch-control-3.desktop \
        localsearch-writeback-3.desktop; do \
        if [ -f "/etc/xdg/autostart/$tracker_autostart" ]; then \
            echo "Hidden=true" >> "/etc/xdg/autostart/$tracker_autostart"; \
        fi; \
    done && \
    \
    # ============================================================
    # PHASE 9: Remove leftover cache and documentation artifacts
    # ============================================================
    dnf clean all && \
    rm -rf /var/cache/dnf /var/cache/libdnf5 && \
    rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* && \
    rm -rf /usr/share/gnome/help/* /usr/share/help/* && \
    rm -rf /tmp/* /var/tmp/*
```

## Architectural recommendations beyond package removal

The removal script handles the immediate bloat problem, but three architectural patterns from the sources deserve emphasis. First, **always pass `--setopt=install_weak_deps=False` when installing packages** in the Containerfile. The official Fedora Silverblue config ships with `install_weak_deps: true`, which is why every GNOME app drags in optional dependencies. Bluefin and the broader ublue-os ecosystem use this flag consistently. For MiOS, set it globally in `/etc/dnf/dnf.conf` as `install_weakdeps=False` early in the build, before any `dnf install` operations.

Second, **prefer the "build from minimal base + add" approach over "start full + remove."** Fedora CoreOS's derivation model — start from `quay.io/fedora/fedora-bootc:rawhide`, then `dnf install` only the packages you need — produces a cleaner, more predictable image than starting from a Silverblue base and stripping. The minimal GNOME desktop install (`dnf install gnome-shell gnome-console nautilus xdg-user-dirs xdg-user-dirs-gtk flatpak`) pulls in ~180–200 packages versus Workstation's 1000+, and avoids the malcontent trap entirely because gnome-control-center comes in as a dependency with only the libraries it actually needs at runtime.

Third, the **NoDisplay override pattern is more robust than removal for edge cases**. Bluefin's approach of writing `.desktop` file overrides through rsync'd system files (from `projectbluefin/common`) and GSettings schema overrides (e.g., `zz2-org.gnome.shell.gschema.override`) neutralizes unwanted functionality without fighting RPM dependency resolution. For packages where `dnf remove --assumeno` shows any cascade risk, always prefer `NoDisplay=true` over forced removal. The override files bake into the immutable `/usr` layer and survive updates cleanly, unlike `rpm -e --nodeps` removals which get silently reinstated by the next image update that touches the same dependency chain.

## The "build up" alternative eliminates most removal complexity

Rather than the removal script above (which is the right approach when starting from Silverblue), the cleanest MiOS architecture starts from `fedora-bootc:rawhide` and installs only what's needed:

```bash
FROM quay.io/fedora/fedora-bootc:rawhide

RUN set -euo pipefail && \
    echo "install_weakdeps=False" >> /etc/dnf/dnf.conf && \
    dnf install -y \
        gnome-shell gdm mutter gnome-session \
        gnome-settings-daemon gnome-control-center \
        gjs gnome-keyring polkit \
        xdg-desktop-portal xdg-desktop-portal-gnome \
        xdg-desktop-portal-gtk \
        pipewire pipewire-pulseaudio wireplumber \
        NetworkManager NetworkManager-wifi \
        NetworkManager-bluetooth bluez \
        nautilus gvfs-fuse gvfs-mtp gvfs-gphoto2 \
        flatpak xdg-user-dirs-gtk \
        libadwaita adw-gtk3-theme \
        adwaita-qt5 adwaita-qt6 \
        qadwaitadecorations-qt5 qadwaitadecorations-qt6 \
        gnome-bluetooth gnome-backgrounds \
        mesa-dri-drivers mesa-vulkan-drivers \
        plymouth plymouth-system-theme \
    && dnf clean all && \
    systemctl enable gdm && \
    systemctl set-default graphical.target
```

This "build up" approach produces a **~180-package GNOME desktop** versus removing from Silverblue's ~1000+ packages. It never encounters the malcontent trap because `malcontent` is pulled in only as a dependency of `gnome-control-center`, and with `install_weakdeps=False`, none of its control/pam/tools subpackages are installed. The base `malcontent` and `malcontent-libs` packages come in as hard deps (unavoidable), but the UI components stay out. This is the pattern Fedora CoreOS's own documentation recommends for derived images and is exactly how the Fedora Magazine's "Building your own Atomic Desktop" guide structures custom bootc images.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
