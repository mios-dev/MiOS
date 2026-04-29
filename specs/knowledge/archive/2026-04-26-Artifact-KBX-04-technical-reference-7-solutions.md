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

# MiOS technical reference: 7 practical solutions

**This report covers seven distinct technical issues encountered while building MiOS**, a Fedora Rawhide bootc immutable workstation. Each section provides tested commands, correct syntax, and configuration snippets ready for use in Containerfiles and deployment scripts. The common thread: making container-native and WSL2 deployments of a bootc image work seamlessly alongside the bare-metal host.

---

## 1. K3s agents can join from containers and WSL2 — but need privileges

A K3s agent running inside a Podman container or WSL2 instance **can** join a K3s cluster on the bare-metal MiOS host. The agent connects outbound to the server on **port 6443 TCP** using a reverse WebSocket tunnel, meaning the agent container needs no inbound ports opened. The server's node token (at `/var/lib/rancher/k3s/server/node-token`) authenticates the join.

**Running the agent in Podman** requires rootful mode with `--privileged` — this is non-negotiable because K3s needs cgroup management, iptables control, and kernel module access. Use `--network host` to avoid double-NAT issues with Flannel VXLAN:

```bash
HOST_IP="1.1.1.100"
NODE_TOKEN="$(sudo cat /var/lib/rancher/k3s/server/node-token)"

sudo podman run -d \
  --privileged \
  --name k3s-agent \
  --network host \
  --tmpfs /run \
  --tmpfs /var/run \
  -e K3S_URL=https://${HOST_IP}:6443 \
  -e K3S_TOKEN=${NODE_TOKEN} \
  -e K3S_NODE_NAME=k3s-agent-podman \
  -v k3s-agent-data:/var/lib/rancher/k3s \
  --ulimit nproc=65535 \
  --ulimit nofile=65535:65535 \
  rancher/k3s:v0.1.1-k3s1 agent
```

Critical details: always use an **explicit version tag** (`v0.1.1-k3s1` with hyphens, not plus signs) because the `latest` tag is unmaintained. Use **K3s v1.28+** on Fedora Rawhide for proper cgroup v2 support — older versions fail with cgroupv2 errors. The persistent volume on `/var/lib/rancher/k3s` preserves agent state across restarts, and `--node-name` prevents hostname collisions.

**For WSL2 deployments**, the K3s binary can run directly (no nested container needed). Modern WSL2 kernels include all required modules (`br_netfilter`, `overlay`, `vxlan`). Enable systemd first via `/etc/wsl.conf`, then:

```bash
sudo k3s agent --server https://1.1.1.100:6443 \
  --token <TOKEN> --node-name wsl2-agent
```

WSL2's NAT layer can cause issues with Flannel VXLAN (UDP 8472). Consider `--flannel-backend=wireguard-native` if pod-to-pod networking between WSL2 agents and bare-metal nodes fails. On the bare-metal host, open the firewall for the API server and pod/service CIDRs:

```bash
firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --zone=trusted --add-source=0.0.0.0/16
firewall-cmd --permanent --zone=trusted --add-source=0.0.0.0/16
firewall-cmd --permanent --add-port=8472/udp
firewall-cmd --reload
```

Rootless Podman **will not work** for K3s agents. SELinux on Fedora may also require the `k3s-selinux` policy package from `rpm.rancher.io`.

---

## 2. Cockpit socket already binds 0.0.0.0 — the real fix is elsewhere

**By default, `cockpit.socket` listens on all interfaces on port 9090**, not just localhost. The base unit file specifies `ListenStream=9090` without an address prefix, which systemd interprets as binding to `[::]` (all IPv6 and IPv4 via dual-stack). So if Cockpit is unreachable from a container or WSL2 instance, the listen address is probably not the problem.

The actual issues in containerized/WSL2 deployments are typically: missing systemd (Cockpit requires socket activation), missing D-Bus, or missing port mapping. For Podman containers, **`--systemd=true`** is mandatory — Cockpit cannot function without systemd as PID 1:

```bash
podman run -d --name mios \
  -p 9090:9090 \
  --systemd=true \
  --privileged \
  your-registry/mios:latest
```

If you do need to override the listen address explicitly (e.g., to force IPv4-only), create a drop-in file. The **first empty `ListenStream=` line is mandatory** to reset the inherited value — without it, you get two listening sockets:

```bash
mkdir -p /etc/systemd/system/cockpit.socket.d/
cat > /etc/systemd/system/cockpit.socket.d/listen.conf << 'EOF'
[Socket]
ListenStream=
ListenStream=0.0.0.0:9090
EOF
systemctl daemon-reload && systemctl restart cockpit.socket
```

One subtle gotcha: **capitalization of `ListenStream` must be exact**. Writing `Listenstream` silently fails. And `cockpit.conf` **cannot** change the port or bind address — only the systemd socket unit controls this.

**For WSL2 deployments**, localhost forwarding from WSL2 to Windows works automatically in modern builds — accessing `https://localhost:9090` from the Windows browser should reach Cockpit inside WSL2. If it doesn't, find the WSL2 IP with `hostname -I` and access that directly, or set up port proxying:

```powershell
netsh interface portproxy add v4tov4 listenport=9090 listenaddress=0.0.0.0 connectport=9090 connectaddress=$(wsl hostname -I)
```

For the bootc Containerfile, bake in Cockpit enablement and the WSL2 systemd config:

```dockerfile
RUN dnf install -y cockpit cockpit-ws cockpit-system cockpit-podman && \
    systemctl enable cockpit.socket && \
    printf '[boot]\nsystemd=true\n' > /etc/wsl.conf
```

---

## 3. WSL import demands exactly three arguments with no spaces in the name

The `wsl --import` command requires **exactly three positional arguments**: distribution name, install location, and tarball path. The most common cause of `E_INVALIDARG` is spaces in the distribution name — even when quoted, this triggers the error.

**Correct syntax:**
```powershell
wsl --import MiOS C:\WSL\MiOS C:\path\to\mios.tar.gz --version 2
```

The `--version 2` flag is necessary if your system's default WSL version is set to 1 (check with `wsl --status`). The install location directory will be created automatically — it must not already contain an `ext4.vhdx` from a previous import.

**Supported tarball formats** are `.tar` and `.tar.gz` only. `.tar.xz` is **not supported** (open feature request since 2020). The tarball root must contain the filesystem directly (`/bin`, `/etc`, `/usr` at top level), not nested inside a subdirectory. Create tarballs with:

```bash
podman export <container-id> -o mios.tar
# Or for gzip compression:
podman export <container-id> | gzip > mios.tar.gz
```

**Complete E_INVALIDARG troubleshooting checklist:**

- **No spaces in distribution name** — use `MiOS` not `"Cloud WS"` (confirmed bug in GitHub issue #9859)
- **Type dashes manually** — copy-pasting `--import` from formatted documents can silently substitute en-dashes (`–`) for double-hyphens (`--`)
- **Quote paths with spaces** — `"C:\My Path\file.tar"` but never quote the distro name
- **Don't use .tar.xz** — only .tar and .tar.gz are supported
- **Update WSL** — run `wsl --update` to get the Vendor Store version; older in-box `wsl.exe` may not support `--import` at all
- **Ensure virtualization** is enabled in BIOS and "Virtual Machine Platform" is enabled in Windows Features
- **Fresh install directory** — if the path already has an `ext4.vhdx`, you get error 0x80070050

The newer **`wsl --install --from-file <path.wsl>`** syntax (WSL v0.1.1+, November 2024) takes only one argument and reads the distro name from `/etc/wsl-distribution.conf` inside the tarball. It also runs the OOBE first-run setup. This requires renaming the tarball to `.wsl` extension and embedding a config file — a different workflow from `--import`.

---

## 4. Neither cockpit-ceph-installer nor cockpit-ceph-deploy exists in Fedora

**`cockpit-ceph-installer` is not in Fedora repos and never was.** It was a Red Hat Ceph Storage 4 product component, distributed only through Red Hat subscription channels. Red Hat **officially deprecated it in RHCS 5**, stating that cephadm replaces it. The GitHub repo at `red-hat-storage/cockpit-ceph-installer` targets Ceph Nautilus-era ceph-ansible and is effectively abandoned — it is incompatible with modern Ceph versions (Pacific, Quincy, Reef) which use cephadm instead.

**45Drives' `cockpit-ceph-deploy`** is a separate project but also unavailable in Fedora. It builds RPMs only for EL8, with the last release (v0.1.1) from mid-2023. It similarly depends on ceph-ansible (45Drives' fork) and is designed specifically for their storage hardware. Installing it on Fedora Rawhide would require manual RPM adaptation.

**The recommended alternative is the Ceph Dashboard**, a ceph-mgr module that ships with Ceph itself and is available in Fedora Rawhide:

```bash
dnf install ceph-mgr-dashboard
ceph mgr module enable dashboard
ceph dashboard create-self-signed-cert
ceph dashboard ac-user-create admin -i <password-file> administrator
```

The Ceph Dashboard provides comprehensive cluster management — OSD, pool, RBD, CephFS, and RGW management plus Grafana integration — and is actively maintained upstream. It runs on **port 8443** by default and serves as the modern replacement for all the cockpit-ceph-* projects.

---

## 5. Waydroid GAPPS needs the `-s GAPPS` flag and correct OTA channels

The "Minimal Android" display with empty System/Vendor OTA fields means `waydroid init` ran without specifying GAPPS (it defaults to VANILLA) or the OTA channel was unreachable. The fix is straightforward:

```bash
sudo waydroid init -s GAPPS -f \
  -c https://ota.waydro.id/system \
  -v https://ota.waydro.id/vendor
```

The `-s GAPPS` flag selects Cloud Apps images, `-f` forces re-initialization, and the `-c`/`-v` flags explicitly set the OTA channels in case automatic resolution fails. This downloads **LineageOS 20.0 (Android 13)** GAPPS images from SourceForge.

**The config file lives at `/var/lib/waydroid/waydroid.cfg`** (not `/etc/waydroid/waydroid.cfg`). After a successful GAPPS init on x86_64, it contains:

```ini
[waydroid]
system_ota = https://ota.waydro.id/system/lineage/waydroid_x86_64/GAPPS.json
vendor_ota = https://ota.waydro.id/vendor/waydroid_x86_64/MAINLINE.json
```

The OTA URL construction follows a pattern: `{channel}/{rom_type}/waydroid_{arch}/{type}.json`. Vendor images are architecture-specific but identical across GAPPS/VANILLA/FOSS — only the system image differs. The channel defaults come from `/usr/share/waydroid-extra/channels.cfg` where `system_type = VANILLA` is the default.

To **pre-configure GAPPS in a bootc image** for automated deployment, either bake the waydroid.cfg into the image or create a first-boot script that runs the init command. For manual config editing, set `system_datetime = 0` and `vendor_datetime = 0` to force image re-download on next init.

If OTA is unreachable (firewall, DNS, or SourceForge issues), download images manually:

```bash
wget "https://sourceforge.net/projects/waydroid/files/images/system/lineage/waydroid_x86_64/lineage-20.0-20260312-GAPPS-waydroid_x86_64-system.zip/download" -O system.zip
wget "https://sourceforge.net/projects/waydroid/files/images/vendor/waydroid_x86_64/lineage-20.0-20260302-MAINLINE-waydroid_x86_64-vendor.zip/download" -O vendor.zip
sudo mkdir -p /var/lib/waydroid/images
sudo unzip system.zip -d /var/lib/waydroid/images/
sudo unzip vendor.zip -d /var/lib/waydroid/images/
```

---

## 6. GNOME app folders use a relocatable dconf schema with explicit app lists

GNOME Shell app folders are controlled through the `org.gnome.desktop.app-folders` schema. The `folder-children` key lists folder identifiers, and each folder has its own configuration at a relocatable path. All changes take effect immediately in the GNOME overview.

**Adding Waydroid to a Virtualization folder** (the .desktop file is **`Waydroid.desktop`** with a capital W):

```bash
# Get current folders and add Virtualization
gsettings get org.gnome.desktop.app-folders folder-children
# Suppose output: ['Utilities', 'Development']

# Add Virtualization, keep existing folders
gsettings set org.gnome.desktop.app-folders folder-children \
  "['Utilities', 'Virtualization']"

# Configure the folder
gsettings set org.gnome.desktop.app-folders.folder:/org/gnome/desktop/app-folders/folders/Virtualization/ \
  name 'Virtualization'
gsettings set org.gnome.desktop.app-folders.folder:/org/gnome/desktop/app-folders/folders/Virtualization/ \
  translate false
gsettings set org.gnome.desktop.app-folders.folder:/org/gnome/desktop/app-folders/folders/Virtualization/ \
  apps "['Waydroid.desktop', 'virt-manager.desktop', 'gnome-boxes.desktop']"
```

**Removing the Development folder** — simply omit it from `folder-children` (as shown above where Development was dropped), then optionally purge its config:

```bash
dconf reset -f /org/gnome/desktop/app-folders/folders/Development/
```

**Adding a Ceph Dashboard .desktop entry** — create the file at `/usr/share/applications/ceph-dashboard.desktop` (system-wide for bootc) or `~/.local/share/applications/` (per-user):

```ini
[Desktop Entry]
Type=Application
Name=Ceph Dashboard
Comment=Ceph Storage Cluster Dashboard
Exec=xdg-open https://localhost:8443
Icon=web-browser
Terminal=false
Categories=System;Monitor;
```

Then reference `ceph-dashboard.desktop` (filename only, no path) in a folder's `apps` list. Each folder supports these keys: **`name`** (display string), **`apps`** (explicit .desktop list), **`categories`** (auto-match by desktop category), **`excluded-apps`** (override category matches), and **`translate`** (use desktop-directories translations).

For bootc image deployment, use `dconf load` with a config dump or place override files in `/etc/dconf/db/local.d/` for system-wide defaults.

---

## 7. StartLimitIntervalSec belongs in [Unit] — [Service] silently ignores it

**`StartLimitIntervalSec` and `StartLimitBurst` must be in the `[Unit]` section.** Placing them in `[Service]` produces the warning `Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring` — meaning your rate limiting is **not being applied at all**.

This changed in **systemd 230** (February 2016, commit `6bf0f408`) when Lennart Poettering moved the start-limit directives from `[Service]` to `[Unit]` so they apply to all unit types, not just services. The old name `StartLimitInterval` (without "Sec") is still accepted in `[Service]` for backward compatibility, but the modern name `StartLimitIntervalSec` works only in `[Unit]`.

Correct placement:

```ini
[Unit]
Description=My Service
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/usr/bin/myapp
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

The math matters: **`StartLimitIntervalSec` should exceed `RestartSec × StartLimitBurst`** for the rate limiter to function properly. With `RestartSec=10` and `StartLimitBurst=5`, set `StartLimitIntervalSec` to at least 60 seconds. Setting `StartLimitIntervalSec=0` disables rate limiting entirely. Use `systemctl reset-failed <unit>` to flush the counter after hitting the limit.

---

## Conclusion

The overarching pattern across these issues is that MiOS's multi-target deployment model (bare metal, Podman containers, WSL2 tarballs) requires explicit attention to systemd availability, network namespace boundaries, and privilege escalation. K3s agents and Cockpit both need systemd and privileged container access. WSL2 imports fail on subtle formatting issues rather than fundamental incompatibilities. The Ceph ecosystem has fully moved to cephadm and the built-in Dashboard — the cockpit-ceph plugins are dead ends. Waydroid's OTA system works reliably once the GAPPS flag and channel URLs are explicitly provided. And systemd's [Unit] vs [Service] placement for start-limit directives is a post-2016 change that still catches experienced administrators because older documentation and examples persist across the web.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
