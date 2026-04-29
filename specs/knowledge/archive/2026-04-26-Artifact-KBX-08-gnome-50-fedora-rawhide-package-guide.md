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

# GNOME 50 on Fedora Rawhide: complete package reference

Fedora Rawhide (fc45) fully carries **GNOME 50 "Tokyo"** as of March 18, 2026, with all core libraries, shell components, and replacement apps updated to their 50.0 stable releases. The `fedora-bootc:rawhide` container image does not ship a desktop by default but can install GNOME 50 via a single `dnf` group install with no special repo configuration. Below is every RPM name, gsettings key, environment variable, and renderer detail needed to build and configure a GNOME 50 desktop on Rawhide.

## Core library and shell versions are all GNOME 50 stable

GNOME 50, codenamed **"Tokyo"**, was officially released on March 18, 2026. Fedora Rawhide received the coordinated update on **March 16, 2026**, pushed by Red Hat's Milan Crha. Every core component now tracks the 50.0 stable branch:

| RPM package name | Version-Release | Upstream version | Notes |
|---|---|---|---|
| `gtk4` | **v0.1.1-1.fc45** | GTK 4.22 | Even-numbered GTK stable; GNOME 50's toolkit |
| `libadwaita` | **v0.1.1-1.fc45** | libadwaita 1.9 | Requires gtk4 ≥ v0.1.1 |
| `mutter` | **50.0-1.fc45** | Mutter 50 | Provides `libmutter-18.so` |
| `gnome-shell` | **50.0-1.fc45** | GNOME Shell 50 | Provides `libshell-18.so` |

GTK follows its own versioning scheme: even minors (4.20, 4.22, 4.24) are stable, odd minors (4.21, 4.23) are development. The 4.21.x builds visible in Koji were pre-release; the stable **v0.1.1** landed alongside the rest of the GNOME 50 stack. GNOME 50 is the default desktop for Fedora 44 (stable) and Ubuntu 26.04 LTS. Key GNOME 50 highlights include the complete removal of the X11 session (Wayland-only), VRR and fractional scaling enabled by default, and GPU-accelerated remote desktop.

## Replacement app RPM names on Rawhide

GNOME 50 completes the transition away from legacy apps. All core replacements carry 50.0 versions in Rawhide and use their upstream project names as package names — no `gnome-` prefix needed:

| App | RPM package name | Version | Replaces |
|---|---|---|---|
| Papers (document viewer) | `papers` | **50.0-1.fc45** | Evince |
| Showtime (video player) | `showtime` | **50.0-1.fc45** | Totem / GNOME Videos |
| Loupe (image viewer) | `loupe` | **50.0-1.fc45** | Eye of GNOME (`eog`) |
| Ptyxis (terminal) | `ptyxis` | **50.0-1.fc45** | GNOME Terminal / Console |
| Resources (system monitor) | `resources` | Independent versioning | GNOME System Monitor |

**Resources** is a GNOME Circle app, not a GNOME Core app, so it does not follow the 50.x numbering scheme — it maintains its own release cadence. The other four are GNOME Core apps and were updated to 50.0 in the same March 16 batch. Ptyxis is described as "a container-oriented terminal for GNOME" with native Podman, Distrobox, and Toolbx support, making it particularly relevant for bootc workflows.

## The bootc base image is minimal — here's how to add GNOME 50

The `quay.io/fedora/fedora-bootc:rawhide` image is a **headless, server-oriented base** with roughly bootc, systemd, kernel, dnf5, NetworkManager, and SSH. It ships zero graphical packages. Fedora Rawhide enables a single repository — `rawhide` — defined in `/etc/yum.repos.d/fedora-rawhide.repo`, with `$releasever` resolving to **45**. There are no separate `fedora` or `updates` repos as on stable Fedora.

Because Rawhide already contains GNOME 50 packages, **no version pinning or special repo configuration is needed**. A working Containerfile looks like this:

```dockerfile
FROM quay.io/fedora/fedora-bootc:rawhide

RUN mkdir -p /var/roothome

# Full Fedora Workstation environment (GNOME + LibreOffice, fonts, multimedia)
RUN dnf -y install @workstation-product-environment && dnf clean all

# Or lighter: just the GNOME desktop
# RUN dnf -y install @gnome-desktop-environment && dnf clean all

RUN systemctl set-default graphical.target

# Remove packages that conflict with immutable-OS semantics
RUN dnf -y remove gnome-software PackageKit-command-not-found && dnf clean all

RUN bootc container lint
```

The key group names are **`@workstation-product-environment`** (full Fedora Workstation experience) and **`@gnome-desktop-environment`** (just the GNOME desktop). The `mkdir -p /var/roothome` step prevents build failures during package scriptlets. Always run `bootc container lint` as the final step to validate the image. If you need RPM Fusion for multimedia codecs, install the release RPM with `dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm`.

## Dash to Dock is in the official Fedora repos

The exact package name is **`gnome-shell-extension-dash-to-dock`**, and it lives in the **main Fedora repositories** — no COPR or RPM Fusion required. The source RPM is hosted at `src.fedoraproject.org/rpms/gnome-shell-extension-dash-to-dock` with branches going back to f26.

The current Rawhide build is **version 103-1.fc45**, which explicitly declares GNOME 50 support. Upstream, version 103 was released on February 12, 2025, and includes PR #2474 ("metadata.json: Declare support for GNOME 50") and PR #2499 ("Some fixes for GNOME 50") by Marco Trevisan. The extension carries over **10.7 million downloads** on extensions.gnome.org and supports GNOME 45 through 50.

Install and enable with:

```bash
dnf install gnome-shell-extension-dash-to-dock
gnome-extensions enable dash-to-dock@micxgx.gmail.com
```

Both the RPM and the extensions.gnome.org listing are viable installation paths. The RPM is preferred on Fedora for system-level images since it integrates with dnf transactions and bootc layering.

## LibAdwaita theming schemas, keys, and environment variables

All dark-mode, accent-color, and portal settings live under the **`org.gnome.desktop.interface`** GSettings schema, provided by the `gsettings-desktop-schemas` package. No new theming environment variables were introduced in GNOME 50 / libadwaita 1.9 — the existing mechanisms carry forward unchanged.

**Color scheme (dark mode)** uses the key `color-scheme` at dconf path `/org/gnome/desktop/interface/color-scheme`. It accepts three string values: **`'default'`** (follow system / light), **`'prefer-dark'`**, and **`'prefer-light'`**. LibAdwaita's internal `AdwColorScheme` enum extends this with `FORCE_LIGHT` and `FORCE_DARK` for programmatic use, but the gsettings key uses only the three preference strings.

**Accent colors**, introduced in **libadwaita 1.6 / GNOME 47**, use the key `accent-color` at dconf path `/org/gnome/desktop/interface/accent-color`. Nine named values are supported: **`blue`** (default), **`teal`**, **`green`**, **`yellow`**, **`orange`**, **`red`**, **`pink`**, **`purple`**, and **`slate`**. Each maps to a specific hex color internally (e.g., blue → #3584e4, red → #e62d42).

Setting both via CLI:

```bash
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
gsettings set org.gnome.desktop.interface accent-color 'purple'
```

The critical environment variables LibAdwaita reads are:

| Variable | Purpose | Typical value |
|---|---|---|
| `ADW_DISABLE_PORTAL` | Bypass xdg-desktop-portal; read GSettings directly | `1` |
| `ADW_DEBUG_COLOR_SCHEME` | Override color scheme (debug/dev only) | `prefer-dark` |
| `ADW_DEBUG_HIGH_CONTRAST` | Override high-contrast mode | `1` |
| `ADW_DEBUG_ACCENT_COLOR` | Override accent color | `red`, `blue`, etc. |
| `GTK_THEME` | Force a GTK theme | `Adwaita:dark` |

**Portal integration** is the key subtlety. LibAdwaita **prefers** reading appearance settings from `xdg-desktop-portal-gnome` via D-Bus (`org.freedesktop.portal.Settings` → `org.freedesktop.appearance` namespace) rather than GSettings directly. In containers or non-GNOME sessions where the portal is unavailable, set **`ADW_DISABLE_PORTAL=1`** to force direct GSettings/dconf reads. Without this, libadwaita defaults to light appearance and reports `system-supports-color-schemes = FALSE`. Flatpak containers get portal access automatically through the D-Bus session bus, but bootc or Toolbx environments may need the portal daemon and `xdg-desktop-portal-gnome` package explicitly installed.

## The NGL renderer, Vulkan defaults, and surviving Hyper-V

GTK 4.22 (GNOME 50) ships with a **unified rendering architecture** where the NGL (OpenGL) and Vulkan renderers share the same codebase, differing only in their GPU API abstraction layer. The old legacy GL renderer was **completely removed in GTK 4.18** — setting `GSK_RENDERER=gl` now maps to the NGL renderer rather than the old one.

The default renderer depends on the display backend. On **Wayland** (GNOME 50's only session type), **Vulkan is the default** since GTK 4.16. On X11, NGL is the default. The `GSK_RENDERER` environment variable controls this:

| Value | Effect |
|---|---|
| `opengl` or `gl` or `ngl` | Force the OpenGL/NGL renderer |
| `vulkan` | Force the Vulkan renderer |
| `cairo` | Force Cairo software rendering (safest fallback) |
| `help` | Print available renderers |

For **Hyper-V VMs without GPU passthrough**, the synthetic video adapter (`hyperv_drm` / `hyperv_fb` kernel driver) provides **no hardware 3D acceleration**. All OpenGL calls fall through to Mesa's **llvmpipe** software rasterizer. While llvmpipe technically supports the GL 3.3+ / GLES 3.0+ that NGL requires, there are **well-documented rendering bugs** with GTK4's GPU renderers in virtual machines (Ubuntu Bug #2061118, Fedora Bug #2274930) — missing UI elements, colored rectangles, and artifacts.

The required Mesa packages on Fedora are:

- **`mesa-dri-drivers`** — hardware and software (llvmpipe) DRI drivers
- **`mesa-libEGL`** — EGL runtime (GTK4 requires EGL 1.4+)
- **`mesa-libGL`** — OpenGL runtime
- **`mesa-libgbm`** — Generic Buffer Management (essential for Wayland)
- **`mesa-vulkan-drivers`** — Vulkan ICDs including lavapipe (software Vulkan)

For reliable rendering in a Hyper-V VM, the **recommended configuration** is to force Cairo software rendering and disable Vulkan entirely:

```bash
# /etc/environment
GSK_RENDERER=cairo
GDK_DISABLE=vulkan
```

This bypasses all GL/Vulkan driver issues at the cost of losing 3D transforms and some animation smoothness — a worthwhile trade in a VM without GPU acceleration. If you want to try hardware-path rendering first, `GSK_RENDERER=ngl` with `GDK_DISABLE=vulkan` is the next-best option, but test thoroughly for rendering artifacts.

## Conclusion

Fedora Rawhide fc45 is fully aligned with GNOME 50 "Tokyo" across every component — from gtk4 4.22 and libadwaita 1.9 through gnome-shell 50.0 and all the modern replacement apps (`papers`, `showtime`, `loupe`, `ptyxis`, `resources`). Building a GNOME 50 bootc image requires nothing more than `dnf -y install @workstation-product-environment` on the rawhide base, since the single `rawhide` repo already contains everything. The Dash to Dock extension (`gnome-shell-extension-dash-to-dock` v103) is in the official repos with native GNOME 50 support. For theming, the `org.gnome.desktop.interface` schema handles both `color-scheme` and `accent-color`, with `ADW_DISABLE_PORTAL=1` being the critical environment variable for containers where the portal daemon isn't running. In Hyper-V VMs, set `GSK_RENDERER=cairo` and `GDK_DISABLE=vulkan` to avoid the known rendering bugs that affect GTK4's GPU renderers under software-only graphics stacks.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
