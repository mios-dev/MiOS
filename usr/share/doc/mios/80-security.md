# Security Hardening (Defense in Depth)

> Source: `SECURITY.md` (~200 lines), drawn from SecureBlue
> (`github.com/secureblue/secureblue`) and Fedora hardening guidelines.

## Layer 1 -- Kernel boot parameters

Shipped via `usr/lib/bootc/kargs.d/00-mios.toml` and friends. See
`40-kargs.md` for the full table. Notable: `lockdown=integrity` (NOT
`confidentiality`); `init_on_alloc=1`/`init_on_free=1`/
`page_alloc.shuffle=1` are **disabled** in 'MiOS' due to NVIDIA/CUDA
memory-init incompatibility.

## Layer 2 -- Sysctl

Shipped via `usr/lib/sysctl.d/99-mios-hardening.conf`. Admin overrides
go in `/etc/sysctl.d/`.

### Kernel pointer & debug restrictions

| Sysctl | Value | Purpose |
| --- | --- | --- |
| `kernel.kptr_restrict` | 2 | Hide kernel pointers from all users |
| `kernel.dmesg_restrict` | 1 | Restrict `dmesg` to root |
| `kernel.perf_event_paranoid` | 3 | Disable `perf` for unprivileged users |
| `kernel.sysrq` | 0 | Disable Magic SysRq |
| `kernel.yama.ptrace_scope` | 2 | Only root can `ptrace` |
| `kernel.unprivileged_bpf_disabled` | 1 | Block unprivileged eBPF |
| `net.core.bpf_jit_harden` | 2 | Harden BPF JIT |
| `kernel.kexec_load_disabled` | 1 | Prevent runtime kernel replacement |
| `kernel.io_uring_disabled` | 2 | Block io_uring (broad attack surface) |

### Network hardening

| Sysctl | Value | Purpose |
| --- | --- | --- |
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
| --- | --- | --- |
| `fs.suid_dumpable` | 0 | No core dumps for SUID binaries |
| `fs.protected_hardlinks` | 1 | Restrict hardlink creation |
| `fs.protected_symlinks` | 1 | Restrict symlink following |
| `fs.protected_fifos` | 2 | Restrict FIFOs in sticky dirs |
| `fs.protected_regular` | 2 | Restrict regular files in sticky dirs |

## Layer 3 -- SELinux

Mode: enforcing. Five custom modules built and shipped at
`usr/share/selinux/packages/mios/` (compiled but **not auto-loaded** at
build -- they're available via `semodule -i`):

| Module | Purpose |
| --- | --- |
| `mios_portabled` | systemd-portabled D-Bus for sysext/confext |
| `mios_kvmfr` | Looking Glass shared-memory device access |
| `mios_cdi` | NVIDIA CDI spec generation fcontext |
| `mios_quadlet` | Podman Quadlet container management |
| `mios_sysext` | systemd-sysext extension activation |

Booleans enabled: `container_use_cephfs`, `virt_use_samba`. Fcontext:
`/var/home(/.*)?` labeled `user_home_dir_t`.

```bash
getenforce                          # must return Enforcing
ausearch -m AVC -ts recent          # any recent denials
semodule -l | grep mios             # which mios_* modules are loaded
```

## Layer 4 -- firewalld

Default-deny zone `drop`. Allowed: cockpit (9090/tcp), ssh (22/tcp),
libvirt bridge, CrowdSec nftables bouncer integration. Configured in
`automation/33-firewall.sh`.

## Layer 5 -- CrowdSec (sovereign mode)

`automation/12-virt.sh:42-50` disables `online_client` in
`/etc/crowdsec/config.yaml` (this is one of the documented `/etc/`
exceptions to LAW 1: USR-OVER-ETC, since the upstream CrowdSec contract
has no `/usr/lib/` drop-in mechanism). Monitors logs, applies nftables
bans.

```bash
sudo cscli metrics
sudo cscli decisions list
sudo cscli alerts list
```

## Layer 6 -- fapolicyd

Trust rules at `etc/fapolicyd/fapolicyd.rules`. Blocks unauthorized
binary execution.

```bash
systemctl status fapolicyd
fapolicyd-cli --dump-db | head -20
```

## Layer 7 -- USBGuard

Off by default. To enable, generate a policy from currently-connected
devices:

```bash
sudo usbguard generate-policy > /etc/usbguard/rules.conf
sudo systemctl restart usbguard
sudo usbguard list-devices
sudo usbguard allow-device <id>
```

## Layer 8 -- composefs

Enabled via `usr/lib/ostree/prepare-root.conf`:

```
[composefs]
enabled = true

[etc]
transient = true

[root]
transient-ro = true
```

Provides content-addressed deduplication and verified boot.

## Layer 9 -- Image signing

CI signs every push with cosign keyless via GitHub Actions OIDC. See
`60-ci-signing.md`.

## Override surfaces

| Subsystem | Override path |
| --- | --- |
| Kernel kargs | `bootc kargs edit` (runtime) or higher-priority `usr/lib/bootc/kargs.d/*.toml` (image-time) |
| Sysctl | `/etc/sysctl.d/` |
| SELinux | `setenforce 0` (transient), `/etc/selinux/config` (persistent) |
| Firewall | `firewall-cmd --add-service=...`, `--add-port=...` |
| CrowdSec | `sudo cscli decisions delete --all` |
| fapolicyd | `/etc/fapolicyd/fapolicyd.trust` |
| USBGuard | `/etc/usbguard/rules.conf`, `usbguard allow-device` |

## Reporting vulnerabilities

GitHub private vulnerability reporting on the 'MiOS' repo (Security tab →
Report a vulnerability). Do not file public issues for sensitive
disclosures.
