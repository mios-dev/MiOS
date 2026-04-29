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

# MiOS comprehensive research compendium

**This report covers 13 technical research areas for building a Fedora Rawhide bootc immutable workstation OS**, spanning WSL2/Hyper-V virtualization, build modularization, desktop theming, system management tooling, and licensing. The most impactful findings include systemd's built-in hostname wildcard feature (`mios-?????` in `/etc/hostname`), the `FROM scratch AS ctx` Containerfile pattern used universally across ublue-os projects, and the `cockpit-desktop` mode that eliminates TLS certificate issues entirely. The MiOS repository at `github.com/mios-project/mios` is currently private/inaccessible, but ecosystem analysis from comparable projects provides strong architectural guidance.

---

## 1. WSL2 Podman machine image: packages, architecture, and custom replacement

Podman on Windows uses WSL2 as its machine provider and pulls a custom Fedora-based OCI image from **`quay.io/podman/machine-os-wsl`** — not Fedora CoreOS, which is used only for QEMU/Hyper-V/Apple providers. The image is built in the `containers/podman-machine-os` repository (previously `containers/podman-machine-wsl-os`, merged in v5.6). The build process pulls a base `docker.io/library/fedora` image, installs packages, removes `/etc/resolv.conf`, and exports as a zstd-compressed rootfs tarball that gets imported via `wsl --import`.

The **official WSL machine image package list** includes: `procps-ng`, `openssh-server`, `net-tools`, `iproute`, `dhcp-client`, `crun-wasm`, `wasmedge-rt`, `qemu-user-static`, `subscription-manager`, `gvisor-tap-vsock-gvforwarder`, `cifs-utils`, `nfs-utils-coreos`, `ansible-core`, and `iptables-nft`. Podman itself pulls in `crun`, `conmon`, `netavark`, `aardvark-dns`, `passt/pasta`, `catatonit`, `containers-common`, `buildah`, and `fuse-overlayfs`. One critical gotcha: the WSL kernel does not support nftables, so **`iptables-legacy` is needed instead of `iptables-nft`** (issue #25952).

Red Hat's RHEL WSL-as-Podman-machine guide requires `podman`, `podman-docker`, `procps-ng`, `openssh-server`, `net-tools`, `iproute`, `dhcp-client`, `sudo`, `systemd`, and `systemd-networkd`. The default machine user is `user` (not `core` as with FCOS), and SSH connections are configured automatically during bootstrap.

For **replacing the default image with a custom OCI image**, three approaches exist. First, `podman machine init --image <path-or-URL>` accepts a fully qualified registry path, URL, or local `.tar.gz`/`.tar.zst` rootfs archive. Second, for FCOS-based machines, `podman machine os apply` layers changes on top of the running machine using a Containerfile `FROM quay.io/podman/machine-os`. Third, for WSL specifically, you can export an existing distribution via `wsl --export`, modify it, re-tar, and feed it back to `podman machine init --image`.

For **WSLg compatibility**, the system WSLg distro provides Weston (Wayland compositor), XWayland, PulseAudio, and FreeRDP. User distributions need environment variables (`DISPLAY`, `WAYLAND_DISPLAY`, `PULSE_SERVER`, `XDG_RUNTIME_DIR`) which WSLg auto-sets, plus socket mounts at `/tmp/.X11-unix` and `/mnt/wslg/runtime-dir/wayland-0`. GPU-accelerated rendering requires **Mesa 21.0+ with the D3D12 Gallium driver** enabled (`mesa-dri-drivers`), plus `mesa-vulkan-drivers` for Vulkan via the `dzn` (Dozen) driver.

---

## 2. GPU-PV paravirtualization: dxgkrnl, Mesa d3d12, and the NVIDIA/AMD divide

GPU-PV in WSL2 works through a Linux kernel driver called **dxgkrnl** that exposes `/dev/dxg` and communicates over Hyper-V VM Bus to the host's GPU driver stack. The user-mode components — `libd3d12.so`, `libdxcore.so`, `libcuda.so`, and GPU vendor drivers — are closed-source binaries shipped with Windows and automatically mounted at `/usr/lib/wsl/lib/` and `/usr/lib/wsl/drivers/` inside WSL2. No additional kernel module installation is needed in WSL2 distributions since dxgkrnl is built into the Microsoft WSL kernel.

The **Mesa D3D12 Gallium driver** (upstreamed by Microsoft/Collabora in Mesa 21.0) translates OpenGL, OpenCL, and Vulkan calls into D3D12 API calls, which flow through dxgkrnl to the host GPU. It supports OpenGL 4.5 core, OpenGL ES 3.2, and Vulkan via the Dozen driver. Verification: `glxinfo | grep "OpenGL renderer"` should show `D3D12 (<GPU Name>)` rather than `llvmpipe`. Some distributions default to llvmpipe even when D3D12 is available — setting `export GALLIUM_DRIVER=d3d12` forces the correct driver.

**NVIDIA support in WSL2 is comprehensive**: CUDA, DirectML, OpenGL (via Mesa d3d12), Vulkan, and VAAPI video acceleration all work, with `nvidia-smi` available through the mounted libraries. **AMD support is more limited** — OpenGL works via Mesa d3d12, but there is no native ROCm in WSL2; compute must use DirectML instead. Intel GPUs work via the same d3d12 pathway.

For **Hyper-V Gen2 Linux VMs**, GPU-PV is NOT officially supported by Microsoft for Linux guests — it's a community-driven effort. The dxgkrnl module must be compiled from source using the WSL2-Linux-Kernel source tree, available as DKMS packages from projects like `staralt/dxgkrnl-dkms`. GPU driver files must be manually copied from the Windows host (`C:\Windows\System32\DriverStore\FileRepository\` and `C:\Windows\System32\lxss\lib`) into the guest at `/usr/lib/wsl/lib/` and `/usr/lib/wsl/drivers/`. Community testing confirms working setups on Debian 12/13, Ubuntu 24.04, Fedora 41, and Fedora Bootc. Microsoft has posted dxgkrnl v2 patches (~24 patches, 16.5k lines) for potential mainlining into the upstream Linux kernel, but this remains under review.

---

## 3. Containerfile modularization: patterns from the ublue-os ecosystem

The dominant pattern across all major Fedora bootc projects is the **`FROM scratch AS ctx` context stage**, which copies build files into a scratch layer that's then mounted (not copied) into the real build stage via `--mount=type=bind,from=ctx,source=/,target=/ctx`. This keeps build scripts accessible during the build without adding layers to the final image. The ublue-os image-template, bazzite, and bluefin all use this pattern.

**Bazzite** (8.1k stars) uses a single ~846-line Containerfile with multi-stage builds producing 10+ image variants. Stages include `bazzite` (main desktop), `bazzite-deck` (Steam Deck), and `bazzite-nvidia`. Build target selection uses `podman build --target bazzite-deck`. Configuration files live in a `` tree organized by variant (`desktop/shared/`, `desktop/kinoite/`, `desktop/silverblue/`, `deck/shared/`), and external pre-built artifacts are pulled via `COPY --from=ghcr.io/ublue-os/brew:latest /system_files /`. Every stage ends with `bootc container lint` for validation.

**Bluefin** (2.4k stars) takes the opposite approach: the Containerfile is intentionally minimal (~49 lines), delegating all logic to **numerically-prefixed build scripts** in `build_files/`: `00-packages.sh`, `03-signing.sh`, `05-config.sh`, `08-cleanup.sh`, `20-tests.sh`. Gaps in numbering (no 01, 02, 06, 07) allow future insertions. Package declarations live in `packages.json`, and image dependencies are pinned to SHA256 digests in `image-versions.yml`. Validation tests verify cosign checksums, critical package presence, and systemd unit enablement.

**uCore** (602 stars) uses a tiered image architecture: `ucore-minimal` → `ucore` → `ucore-hci`, each adding layers of functionality. Kernel modules are pulled via `COPY --from=ghcr.io/ublue-os/akmods`. **secureblue** (847 stars) uses **BlueBuild**, a YAML-to-Containerfile abstraction where recipes define modules (`rpm-ostree`, `script`, `files`) in declarative YAML rather than shell scripts.

For MiOS, the **recommended architecture** based on ecosystem patterns would be: a minimal Containerfile using the `FROM scratch AS ctx` pattern, numbered build scripts in `build_files/` for each concern (packages, services, desktop config, development tools), a `` tree for configuration overlays, and `bootc container lint` at the end. Use `--mount=type=cache,dst=/var/cache/libdnf5` for dnf caching across builds.

---

## 4. The ujust CLI pattern: just-based system management

Every Universal Blue project uses **`ujust`**, which is simply an alias for the `just` command runner (a Rust-based task runner) pointed at system-level justfiles. The `just` binary is installed via RPM at `/usr/bin/just`, and system justfiles live at `/usr/share/ublue-os/just/` with a master file at `/usr/share/ublue-os/justfile` that imports all numbered `.just` files.

Bazzite organizes recipes with **numbered file prefixes**: `80-bazzite.just` (~763 lines of core config), `81-bazzite-fixes.just`, `82-bazzite-apps.just`, `83-bazzite-audio.just`, `84-bazzite-virt.just`, etc. Numbers 80-99 are reserved for image-specific recipes; 0-59 for shared recipes. Each recipe follows a **three-mode pattern**: help mode (`ACTION="help"` prints usage), interactive mode (`ACTION=""` shows a TUI menu via `ugum choose`), and direct mode (`ACTION="enable"` executes immediately).

A helper library at `/usr/lib/ujust/ujust.sh` provides color variables (`$bold`, `$red`, `$green`), a `Choose` function wrapping `gum`-based interactive selection, and an `Assemble` function for distrobox management. Bazzite also includes `bazzite-ujust-picker`, a compiled binary providing a searchable, categorized TUI for discovering recipes without knowing their names.

For MiOS, implementing a `mios` CLI would mean: install `just` via RPM, create justfiles at `/usr/share/mios/just/`, create a shell alias `alias mios='just --justfile /usr/share/mios/justfile'`, and write bash-based recipes for common operations (updates, service toggles, status checks). The `just --list` command provides built-in `--help`-like functionality, and `just --choose` enables interactive recipe selection when `fzf` or `gum` is installed.

---

## 5. Hyper-V enhanced session: the GDM-first challenge remains unsolved

Hyper-V Enhanced Session Mode uses **VSOCK transport** (`port=vsock://-1:3389` in xrdp.ini) rather than standard TCP networking, with the `hv_sock` kernel module loaded in the guest. Required packages on Fedora are `hyperv-tools`, `xrdp`, `xrdp-selinux`, and `xorgxrdp` (with optional `xorgxrdp-glamor` for GPU-accelerated rendering). Key xrdp.ini settings: `security_layer=rdp`, `crypt_level=none`, `bitmap_compression=false`, and `vmconnect=true`.

**The core problem with GDM-first flow**: when enhanced session is enabled, Hyper-V VMConnect uses RDP via VSOCK instead of the console framebuffer, so xrdp presents its own login dialog rather than the native GDM greeter. GDM runs on VT1/VT7 which is no longer rendered. There is **no reliable, well-documented method** to have xrdp reconnect to a console-initiated GDM/GNOME session — the architectures are fundamentally different.

Three workaround approaches exist. **Approach A**: Use GNOME's built-in `gnome-remote-desktop` service (GNOME 42+/Fedora 42+) instead of xrdp — user logs in via GDM on console, then connects via standard `mstsc.exe` RDP. This provides native Wayland session with audio but cannot be used as the enhanced session transport (Hyper-V doesn't detect it as an enhanced session provider). **Approach B**: Boot in basic (non-enhanced) session mode, let user see GDM and log in normally, then switch to enhanced session via VMConnect's View menu. **Approach C**: Accept xrdp's login screen and configure it for the best GNOME experience — ensure `gnome-session-xsession` is installed since xrdp requires X11 (Wayland is incompatible), set up PolicyKit rules for color-manager to prevent errors, and configure PAM for GNOME keyring integration.

Critical additional notes: Fedora defaults to Wayland since F34, but xrdp only works with Xorg. Audio requires `pipewire-module-xrdp` compiled separately. SELinux may need the `xrdp-selinux` package. For hybrid VSOCK + TCP, use `port=3389 vsock://-1:3389` (space-separated) to enable both enhanced session and standard network RDP. Community scripts for Fedora include `secana/EnhancedSessionMode` and `hu-ximing/Hyper-V-RHEL-Fedora-enhanced-session`.

---

## 6. Network reachability: mirrored mode, external switches, and Avahi

For **Hyper-V VMs**, the simplest approach is an External Virtual Switch, which gives the VM its own LAN IP via DHCP. Create via PowerShell: `New-VMSwitch -Name "ExternalSwitch" -NetAdapterName "Ethernet" -AllowManagementOS $true`. The VM becomes fully reachable from all LAN devices. Wi-Fi adapters may not work with external switches (hardware-dependent), and creating/modifying external switches briefly disrupts host network connectivity.

For **WSL2**, the recommended approach since Windows 11 22H2 is **mirrored networking mode**, configured in `%UserProfile%\.wslconfig` with `networkingMode=mirrored`. This gives WSL2 the same IP as the Windows host, and services become accessible from LAN devices after configuring the Hyper-V firewall: `Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow`. The older `bridged` mode (`networkingMode=bridged` + `vmSwitch=<name>`) broke in Windows 11 23H2. For legacy NAT mode, use `netsh interface portproxy add v4tov4` for port forwarding, but this only supports TCP and requires re-running when WSL2's internal IP changes.

For **`.local` hostname discovery**, install `avahi` and `nss-mdns` on Fedora (`dnf install avahi nss-mdns avahi-tools`), enable `avahi-daemon.service`, and open firewall port 5353/UDP (`firewall-cmd --add-service=mdns --permanent`). The `/etc/nsswitch.conf` hosts line should include `mdns4_minimal [NOTFOUND=return]`. Custom service advertisements go in `/etc/avahi/services/` as XML files. Note that Fedora 40+ ships `passim` which starts Avahi by default, and `systemd-resolved` has built-in mDNS that can conflict — either disable systemd-resolved's mDNS (`MulticastDNS=no` in `/etc/systemd/resolved.conf`) or skip Avahi.

---

## 7. Unique hostname generation: systemd's built-in wildcard is the answer

The most elegant solution is a **built-in systemd feature (v249+)**: if the `?` character appears in `/etc/hostname`, each `?` is automatically substituted by a hexadecimal character derived from `/etc/machine-id` via cryptographic hashing. This is deterministic and stable across reboots.

**Implementation in a Containerfile is one line:**
```dockerfile
RUN echo "mios-?????" > /etc/hostname
```

Each deployed instance gets a unique machine-id on first boot (systemd generates it from D-Bus machine ID, KVM DMI `product_uuid`, kernel `container_uuid`, or random UUID), which deterministically expands to a unique hostname like `mios-92a9f`. No custom scripts, systemd services, or firstboot logic needed. The hostname is stable across reboots (same machine-id produces the same expansion) but unique per deployment.

For bootc images, **`/etc` is mutable and persistent by default** using OSTree 3-way merge semantics: locally modified files (including `/etc/hostname` after expansion) are retained across image updates. The `/etc/machine-id` should be empty or missing in the container image to trigger `ConditionFirstBoot=yes` semantics and proper machine-id generation.

If running an older systemd without wildcard support, the fallback is a custom oneshot service with `ConditionFirstBoot=yes` that runs `hostnamectl set-hostname "mios-$(head -c 5 /etc/machine-id)"`. Fedora CoreOS uses Ignition for this purpose, writing `/etc/hostname` from Butane YAML config, with dynamic hostnames generated via custom oneshot services that query cloud metadata.

---

## 8. Kernel pinning: versionlock, COPR repos, and the Bazzite model

As of **rpm-ostree 2025.2 and Fedora bootc 42+**, DNF can manage kernel packages directly in Containerfiles thanks to kernel-install integration. The official bootc docs explicitly warn: **do not invoke `dnf -y update`** in Containerfiles — kernel and bootloader updates may not work correctly.

**Option A — dnf versionlock** pins all kernel subpackages (you must lock `kernel`, `kernel-core`, `kernel-modules`, `kernel-modules-core`, and `kernel-modules-extra` together to prevent partial upgrades):
```dockerfile
RUN dnf install -y python3-dnf-plugins-extras-versionlock && \
    dnf versionlock add kernel kernel-core kernel-modules kernel-modules-core && \
    dnf clean all
```

**Option B — COPR alternative kernels** provide dedicated stable/LTS options. Bazzite uses `sentry/kernel-fsync` (futex/fsync patches for gaming) with explicit version gating logic to avoid regressions. The MiOS COPR (`bieszczaders/kernel-cachyos`) offers LTS, RT, and server variants with BORE scheduler and AMD optimizations. The `kwizart/kernel-longterm` COPR provides true LTS kernel branches (6.1, 6.6, etc.). The official `@kernel-vanilla/stable` COPRs won't provide older kernels than Rawhide's default, making them less useful for this purpose.

**Option C — Install from a stable Fedora release repo**: `dnf -y --releasever=42 --repo=fedora,updates install kernel kernel-core kernel-modules kernel-modules-core` then versionlock. This gives a true stable kernel but risks ABI mismatches with Rawhide userspace packages.

**Option D — dnf exclude**: Add `exclude=kernel*` to `/etc/dnf/dnf.conf` to prevent any kernel updates. Bazzite's approach is the most battle-tested: it downloads the fsync COPR repo file, installs the fsync kernel, builds custom akmods for it, and handles Secure Boot key enrollment since COPR kernels aren't signed with Fedora's keys.

---

## 9. Cockpit as a native web app: cockpit-desktop eliminates TLS pain

The cleanest approach for local Cockpit access is **`cockpit-desktop`**, a purpose-built program in the `cockpit-ws` package. It starts cockpit-ws and a web browser in an isolated network namespace, runs cockpit-bridge in the existing user session, requires **no login and no TLS** (uses `--no-tls` implicitly), and needs no `cockpit.socket` enabled system-wide. Usage: `cockpit-desktop /` opens the main page, `cockpit-desktop /storage` opens the storage page directly.

For an Epiphany web app approach, GNOME Web's "Install as Web Application" feature creates a standalone app with its own window, isolated cookies, and a `.desktop` file. **Critical limitation**: this feature only works with the native RPM version of Epiphany, not the Flatpak version (Flatpak can't write `.desktop` files to the host). Self-signed certificate warnings in Epiphany/WebKitGTK have no bypass mechanism — WebKitGTK deliberately enforces strict TLS validation with no `about:config` equivalent.

The practical solution is to avoid TLS for localhost entirely. **Cockpit already allows unencrypted HTTP from localhost by default** — accessing `http://localhost:9090` works without HTTPS redirect. Setting `AllowUnencrypted = true` in `/etc/cockpit/cockpit.conf` extends this to all connections. For the bootc image, pre-provision a `.desktop` file at `/usr/share/applications/cockpit.desktop` pointing to either `cockpit-desktop /` (preferred) or `xdg-open http://localhost:9090` (simpler).

---

## 10. Fastfetch: command modules display service statuses and URLs

Fastfetch configuration uses JSONC format at `~/.config/fastfetch/config.jsonc` (or system-wide at `/etc/fastfetch/config.jsonc`). The **`command` module** executes arbitrary shell commands, making it ideal for displaying service statuses and management URLs:

```jsonc
{
  "type": "command",
  "key": "🔧 Cockpit",
  "keyColor": "green",
  "text": "systemctl is-active cockpit.socket 2>/dev/null && echo '✓ http://localhost:9090' || echo '✗ inactive'"
}
```

The `custom` module displays static formatted text (useful for section headers like `── Services & Management ──`). Each module supports `key` (custom label with Unicode/emoji), `keyColor`, `format` (template string with placeholders), and `keyWidth` overrides. Generate a full default config with `fastfetch --gen-config-full`, and use the JSON schema (`"$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json"`) for IDE autocomplete. For bootc deployment, place the config at `/etc/fastfetch/config.jsonc` and add `fastfetch` to the shell profile (`.bashrc` or `/etc/profile.d/`).

---

## 11. GTK4/libadwaita dark theme: a six-layer configuration stack

Achieving consistent dark theme across all GNOME window types requires configuring **six separate layers**. The primary setting is `gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'`, which libadwaita/GTK4 apps and the GNOME Shell read directly. GTK3 legacy apps additionally need `gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'` (or the community `adw-gtk3-dark` theme for better visual consistency with libadwaita).

**GDM** runs as the `gdm` user with its own dconf database. Create `/etc/dconf/profile/gdm` (containing `user-db:user` and `system-db:gdm`), then `/etc/dconf/db/gdm.d/01-dark-theme` with `color-scheme='prefer-dark'` and `gtk-theme='Adwaita-dark'` under `[org/gnome/desktop/interface]`, then run `dconf update`. GNOME 47+ accent colors on GDM require the additional key `accent-color='<color>'`.

**Flatpak apps** receive the dark preference through `xdg-desktop-portal-gnome`, which exposes `org.freedesktop.appearance.color-scheme` automatically. If portal integration fails, the fallback is `sudo flatpak override --env=GTK_THEME=Adwaita:dark`. **Qt apps** need `adwaita-qt5`, `adwaita-qt6`, `qgnomeplatform-qt5`, and `qgnomeplatform-qt6` installed, with `QT_QPA_PLATFORMTHEME=gnome` set in `/etc/environment` (note: QGnomePlatform is marked unmaintained since August 2023 but still functions). The Kvantum theme engine with KvGnomeDark is an alternative.

For system-wide bootc deployment, create `/etc/dconf/db/local.d/99-dark-defaults` with all desired settings and `/etc/dconf/profile/user` with `user-db:user` and `system-db:local`, then run `dconf update` in the Containerfile. The **GNOME lock screen inherits** from the user session automatically, requiring no separate configuration. Electron apps may need `--force-dark-mode` flags in their `.desktop` files, and Firefox requires "System Theme (automatic)" in about:addons plus `xdg-desktop-portal-gnome` installed.

---

## 12. Podman garbage collection: prune strategies and the build cache gap

The core cleanup command is **`podman system prune --all --volumes --build --force`**, which removes all unused containers, pods, networks, images, build containers, and volumes. The `--filter until=<duration>` flag provides time-based filtering (e.g., `until=168h` keeps images younger than 7 days). Use `podman system df` and `podman system df -v` to monitor disk usage before pruning.

A critical gap exists: **build-time cache mounts** (`--mount=type=cache` in Containerfiles) are NOT removed by `podman system prune -af --volumes`. This is a known issue (buildah #4486, podman #19604), and the only workaround is `podman system reset` (which destroys everything). For CI/CD build machines, `podman build --no-cache --pull` ensures clean release builds, and `podman builder prune -a` clears the build cache specifically.

Podman maintainers **rejected a PR (#25864) to add built-in systemd prune timers** because pruning races with `podman-auto-update` — if auto-update pulls a new image and restarts a container, the old image might have no users and get incorrectly pruned. Instead, create custom systemd timers aware of your workload patterns:

```ini
# /etc/systemd/system/podman-cleanup.timer
[Timer]
OnCalendar=weekly
Persistent=true
```

The cleanup service should run `podman container prune -f`, `podman image prune -a -f --filter 'until=168h'`, `podman volume prune -f`, and `podman network prune -f`. For threshold-based automation, script `podman system df` output to trigger cleanup when storage exceeds a percentage. Storage configuration in `/etc/containers/storage.conf` can redirect `graphroot` to a dedicated large partition and use `imagestore` to split image storage from container writable layers. Always use the **overlay storage driver** (not vfs) for Copy-on-Write layer deduplication, and consider XFS with `pquota` mount option for per-container disk quotas.

---

## 13. Open source licensing when AI tools assist development

Under current U.S. law (solidified by the Copyright Office's January 2025 report and the Thaler v. Perlmutter ruling affirmed by the D.C. Circuit in March 2025), **purely AI-generated content cannot be copyrighted** — only works with sufficient human creative input qualify. The Supreme Court declined to review Thaler, establishing "human authorship" as a firm statutory requirement. AI used as an assistant (autocomplete, bug-finding, refactoring) does not affect copyright eligibility of the resulting work, but prompts alone are insufficient for authorship.

**Permissive licenses (MIT, Apache 2.0) are least affected** by AI copyright uncertainty — they function normally since the license applies to copyrightable human-authored portions. GPL/copyleft licenses face a fundamental tension: AI-generated code that cannot be copyrighted effectively becomes public domain, breaking the copyleft reciprocity mechanism. For projects mixing human and AI contributions, Red Hat recommends **MIT or Apache 2.0** for maximum compatibility.

For attribution, Red Hat's October 2025 guidance suggests: trivial AI uses (autocomplete, variable naming) don't require disclosure; substantial AI use should be marked via commit trailers (`Assisted-by:`, `Generated-by:`, or `Co-authored-by:`), PR descriptions, and source code comments. A README AI Disclosure section should state which tools were used, that all AI-generated code was reviewed by human maintainers, and that AI-generated portions may not be independently copyrightable under current law. Existing LICENSE files should remain unchanged — add notes in NOTICE files if desired. The Open Source Initiative released the Open Source AI Definition (OSAID) v1.0 in October 2024, requiring code, model parameters, and detailed data information for AI to be called "open source," while the FSF takes a stricter position requiring actual training data to be free.

---

## Conclusion: architectural decisions for MiOS

Several findings are directly actionable for the project. The **systemd hostname wildcard** (`echo "mios-?????" > /etc/hostname`) is the single most elegant solution discovered — it eliminates all custom scripting for unique hostname generation. For build modularization, Bluefin's numbered-scripts pattern (`00-packages.sh`, `05-config.sh`, `20-tests.sh`) provides the cleanest separation of concerns, combined with the universal `FROM scratch AS ctx` Containerfile pattern. The `just`-based CLI system used by every ublue project is production-proven and simple to implement — no custom tooling needed, just `.just` files with bash recipes.

The Hyper-V enhanced session GDM-first challenge remains architecturally unsolvable without upstream changes — GNOME's built-in RDP (`gnome-remote-desktop`) is the most promising path but cannot yet serve as the enhanced session transport. For GPU-PV in Hyper-V Linux guests, the dxgkrnl DKMS approach works but requires manual driver file copying and is entirely community-supported. WSL2 GPU-PV is production-ready with automatic driver mounting.

For kernel management, the Bazzite/fsync-kernel COPR model is battle-tested at scale, but the simpler dnf versionlock approach may suffice for MiOS's needs. `cockpit-desktop` eliminates all TLS certificate complexity for local Cockpit access. And for licensing, Apache 2.0 with an AI Disclosure section in the README represents current best practice for AI-assisted open source projects.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
