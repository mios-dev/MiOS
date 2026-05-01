# MiOS Security Hardening

Defense-in-depth posture, sourced primarily from SecureBlue's audit
framework (<https://github.com/secureblue/secureblue>) and the Fedora
hardening guidelines (<https://docs.fedoraproject.org/en-US/quick-docs/securing-fedora/>).
Every measure below cites the file that enforces it; admin overrides are
listed in the right column.

## Kernel boot parameters

Shipped via `usr/lib/bootc/kargs.d/00-mios.toml` (and other priority files
in the same directory). bootc renders all `kargs.d/*.toml` into the active
kernel cmdline at upgrade time.

| Parameter | Purpose | Override |
|---|---|---|
| `slab_nomerge` | Prevent slab cache merging (heap isolation) | Remove from kargs.d TOML |
| ~~`init_on_alloc=1`~~ | Disabled — causes CUDA memory init failures; enable for CPU-only builds | Higher-priority kargs.d file |
| ~~`init_on_free=1`~~ | Disabled — same CUDA incompatibility | Higher-priority kargs.d file |
| ~~`page_alloc.shuffle=1`~~ | Disabled — NVIDIA driver instability | Higher-priority kargs.d file |
| `randomize_kstack_offset=on` | Per-syscall kernel stack randomization | `=off` |
| `pti=on` | Page Table Isolation (Meltdown) | `=off` (not recommended) |
| `vsyscall=none` | Disable legacy vsyscall table | `=emulate` |
| `iommu=pt` | IOMMU passthrough for VFIO | Required for GPU passthrough |
| `amd_iommu=on` / `intel_iommu=on` | Enable IOMMU | Required for VFIO |
| `nvidia-drm.modeset=1` | NVIDIA DRM modesetting (Wayland) | Required for GNOME Wayland |
| `lockdown=integrity` | Kernel lockdown mode | Remove to allow unsigned modules |
| `spectre_v2=on` | Spectre v2 mitigation | Performance cost ~2-5% |
| `spec_store_bypass_disable=on` | Spectre v4 SSB mitigation | Performance cost ~1-2% |
| `l1tf=full,force` | L1TF mitigation | Affects HyperThreading |
| `gather_data_sampling=force` | GDS/Downfall mitigation | Intel-specific |

Source: kernel admin-guide,
<https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html>.

## Sysctl hardening

Shipped via `usr/lib/sysctl.d/99-mios-hardening.conf`. Admin overrides go
in `/etc/sysctl.d/`.

### Kernel pointer and debug restrictions

| Sysctl | Value | Purpose |
|---|---|---|
| `kernel.kptr_restrict` | 2 | Hide kernel pointers from all users |
| `kernel.dmesg_restrict` | 1 | Restrict dmesg to root |
| `kernel.perf_event_paranoid` | 3 | Disable perf for unprivileged users |
| `kernel.sysrq` | 0 | Disable Magic SysRq |
| `kernel.yama.ptrace_scope` | 2 | Only root can ptrace |
| `kernel.unprivileged_bpf_disabled` | 1 | Block unprivileged eBPF |
| `net.core.bpf_jit_harden` | 2 | Harden BPF JIT |
| `kernel.kexec_load_disabled` | 1 | Prevent runtime kernel replacement |
| `kernel.io_uring_disabled` | 2 | Block io_uring |

### Network hardening

| Sysctl | Value | Purpose |
|---|---|---|
| `net.ipv4.tcp_syncookies` | 1 | SYN flood protection |
| `net.ipv4.conf.all.accept_redirects` | 0 | Block ICMP redirects |
| `net.ipv4.conf.all.send_redirects` | 0 | Don't send ICMP redirects |
| `net.ipv4.conf.all.rp_filter` | 1 | Reverse-path filtering |
| `net.ipv4.conf.all.accept_source_route` | 0 | Block source-routed packets |
| `net.ipv4.conf.all.log_martians` | 1 | Log impossible addresses |
| `net.ipv4.icmp_echo_ignore_broadcasts` | 1 | Ignore broadcast pings |
| `net.ipv4.tcp_timestamps` | 0 | Disable timestamps (anti-fingerprint) |

IPv6 equivalents are set for `accept_redirects` and `accept_source_route`.

### Filesystem protection

| Sysctl | Value | Purpose |
|---|---|---|
| `fs.suid_dumpable` | 0 | No core dumps for SUID binaries |
| `fs.protected_hardlinks` | 1 | Restrict hardlink creation |
| `fs.protected_symlinks` | 1 | Restrict symlink following |
| `fs.protected_fifos` | 2 | Restrict FIFOs in sticky dirs |
| `fs.protected_regular` | 2 | Restrict regular files in sticky dirs |

Source: kernel admin-guide / sysctl,
<https://www.kernel.org/doc/Documentation/sysctl/>.

## SELinux

Mode: enforcing. Custom modules built and shipped in
`usr/share/selinux/packages/mios/`:

| Module | Purpose |
|---|---|
| `mios_portabled` | systemd-portabled D-Bus for sysext/confext |
| `mios_kvmfr` | Looking Glass shared-memory device access |
| `mios_cdi` | NVIDIA CDI spec generation fcontext |
| `mios_quadlet` | Podman Quadlet container management |
| `mios_sysext` | systemd-sysext extension activation |

Booleans enabled: `container_use_cephfs`, `virt_use_samba`. Fcontext:
`/var/home(/.*)?` labeled `user_home_dir_t`.

Status:

```bash
getenforce
ausearch -m AVC -ts recent
semodule -l | grep mios
```

## Firewall

`firewalld` default-deny. Default zone `drop`. Allowed: cockpit (9090/tcp),
ssh (22/tcp), libvirt bridge, CrowdSec nftables bouncer integration.
Configured in `automation/33-firewall.sh`.

```bash
firewall-cmd --list-all
firewall-cmd --list-all-zones
```

## CrowdSec

Sovereign/offline mode (`automation/12-virt.sh:42-50` disables
`online_client` in `/etc/crowdsec/config.yaml` — upstream-contract /etc/
location, no /usr/lib drop-in mechanism exists). Monitors logs, applies
nftables bans.

```bash
sudo cscli metrics
sudo cscli decisions list
sudo cscli alerts list
```

## fapolicyd

Trust rules in `etc/fapolicyd/fapolicyd.rules`. Blocks unauthorized
binary execution.

```bash
systemctl status fapolicyd
fapolicyd-cli --dump-db | head -20
```

## USBGuard

Off by default. To enable, generate a policy from currently-connected
devices:

```bash
sudo usbguard generate-policy > /etc/usbguard/rules.conf
sudo systemctl restart usbguard
sudo usbguard list-devices
sudo usbguard allow-device <id>
```

## composefs

Enabled via `usr/lib/ostree/prepare-root.conf`:

```toml
[composefs]
enabled = true

[etc]
transient = true

[root]
transient-ro = true
```

Provides content-addressed deduplication and verified boot. Source:
<https://github.com/containers/composefs>.

## Image signing

CI signs every push with cosign keyless via GitHub Actions OIDC
(`.github/workflows/mios-ci.yml`). Verify before deploying:

```bash
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

## Override surfaces

| Subsystem | Override path |
|---|---|
| Kernel kargs | `bootc kargs edit`, or higher-priority `usr/lib/bootc/kargs.d/*.toml` |
| Sysctl | `/etc/sysctl.d/` |
| SELinux | `setenforce 0` (transient), `/etc/selinux/config` (persistent) |
| Firewall | `firewall-cmd --add-service=...`, `--add-port=...` |
| CrowdSec | `sudo cscli decisions delete --all` |
| fapolicyd | `/etc/fapolicyd/fapolicyd.trust` |
| USBGuard | `/etc/usbguard/rules.conf`, `usbguard allow-device` |

## Reporting vulnerabilities

GitHub private vulnerability reporting on this repo (Security tab → Report
a vulnerability). Do not file public issues for sensitive disclosures.
