<!-- AI-hint: Maps MiOS's defense-in-depth security posture onto the SecureBlue audit framework it draws from — which kernel kargs, sysctl values, and hardening policies MiOS adopts, which it deliberately diverges on, and why. Use to understand how MiOS's immutable workstation half stays hardened without breaking the GPU/AI/virt workloads the system is built for.
     AI-related: mios-hardening -->
# SecureBlue — the Audit Framework MiOS Draws From

## Why this doc exists

MiOS is one system built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** *and* a **local, self-replicating agentic AI OS**. Both
halves run on the operator's own hardware, offline-capable, with no vendor
account in the loop — which means MiOS has to be its own security boundary. The
GPU lanes that feed the inference stack (`mios-llm-light` and the gated heavy
lanes), the KVM/VFIO passthrough VMs, the rootless Podman quadlets, and the
agent plane all share one kernel and one composefs-mounted `/usr`. The hardening
posture is what keeps that shared substrate trustworthy.

That posture is not invented from scratch. It is **sourced primarily from
[SecureBlue](https://github.com/secureblue/secureblue)'s audit framework and the
Fedora hardening guidelines**, then *selectively adapted* so the security
measures don't break the very workloads MiOS exists to run (NVIDIA/CUDA,
Steam, libvirt, rootless containers, the AI lanes). This document is the map
between SecureBlue's recommended set and what MiOS actually ships — including
exactly what was relaxed and why, so a reviewer can audit the deltas at a
glance.

Its place in the whole system: the build pipeline bakes these kargs and sysctls
into the OCI image; the bootc lifecycle carries them forward atomically (and
`bootc rollback` reverts them as one unit); and Architectural Law 1
(USR-OVER-ETC) keeps the shipped hardening in `/usr/lib/*.d/` immutable while
leaving `/etc/` for admin overrides only.

## Upstream references

- SecureBlue repo: <https://github.com/secureblue/secureblue>
- Fedora hardening guidelines: <https://docs.fedoraproject.org/en-US/quick-docs/securing-fedora/>
- Kernel kargs reference: <https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html>
- Sysctl reference: <https://www.kernel.org/doc/Documentation/sysctl/>

## What MiOS adopts

Kernel boot arguments are spread across additive `usr/lib/bootc/kargs.d/*.toml`
files (bootc concatenates them in lexicographic order); sysctl hardening lives
in `usr/lib/sysctl.d/99-mios-hardening.conf`.

| SecureBlue measure | MiOS adoption | Where |
| --- | --- | --- |
| `slab_nomerge` | ✅ | `usr/lib/bootc/kargs.d/01-mios-hardening.toml` + `30-security.toml` |
| `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` | **❌ disabled** — can interfere with large CUDA allocations | `01-mios-hardening.toml` (commented out; security guide notes this) |
| `randomize_kstack_offset=on`, `pti=on`, `vsyscall=none` | ✅ | `01-mios-hardening.toml` |
| `lockdown=integrity` | ✅ (SecureBlue prefers `confidentiality`; MiOS chose `integrity` so MOK-enrolled signed NVIDIA modules can still load) | `30-security.toml` |
| Spectre/Meltdown/L1TF/GDS/MDS mitigations (full set: `spectre_v2`, `spectre_bhi`, `spec_store_bypass_disable`, `l1tf=full,force`, `gather_data_sampling=force`, `tsx=off`, `mds=full,force`, `tsx_async_abort=full,force`, `itlb_multihit=flush,force`) | ✅ | `01-mios-hardening.toml` + `31-secureblue-extended.toml` |
| Extended kargs: `page_poison=1`, `slub_debug=FZ`, `debugfs=off`, `oops=panic`, `random.trust_{bootloader,cpu}=off`, `efi=disable_early_pci_dma` | ✅ | `31-secureblue-extended.toml` |
| Strict IOMMU: `iommu.strict=1`, `iommu.passthrough=0` | ✅ | `31-secureblue-extended.toml` |
| `kernel.kptr_restrict=2`, `kernel.dmesg_restrict=1` | ✅ | `99-mios-hardening.conf` |
| `kernel.unprivileged_bpf_disabled=1`, `net.core.bpf_jit_harden=2` | ✅ | `99-mios-hardening.conf` |
| `kernel.yama.ptrace_scope=2`, `kernel.sysrq=0`, `kernel.printk=3 3 3 3` | ✅ | `99-mios-hardening.conf` |
| `fs.protected_*` series + `fs.suid_dumpable=0` | ✅ | `99-mios-hardening.conf` |
| Network: `rp_filter`, `tcp_syncookies`, `accept_redirects=0`, `accept_source_route=0`, `icmp_echo_ignore_broadcasts` | ✅ | `99-mios-hardening.conf` |
| fapolicyd deny-by-default | ✅ (root constrained to `trust=1` RPM-signed binaries) | `etc/fapolicyd/fapolicyd.rules` |
| USBGuard | ✅ (shipped + enabled in preset; admin generates an allow-policy) | `usr/lib/usbguard/usbguard-daemon.conf`, system preset |
| firewalld default-deny | ✅ (default zone set to `drop`) | `automation/33-firewall.sh` |
| Kernel module signing | ✅ (via base-image MOK) | inherited from `ucore-hci` |

## What MiOS diverges on (and why)

Every divergence below exists because a stock SecureBlue value would break a
workload MiOS is specifically built to support — the GPU/AI lanes, VFIO
passthrough, or signed-module loading. The deltas are documented inline in the
kargs/sysctl files themselves so the relaxation is never invisible.

- **`lockdown=integrity`, not `confidentiality`** — `confidentiality` would
  block the MOK-enrolled signed NVIDIA modules that the GPU lanes and
  passthrough VMs depend on. `module.sig_enforce` is *not* disabled; MOK keys
  remain sufficient. (Set in `30-security.toml`, which overrides any earlier
  `confidentiality`; the two files must not both set a value.)
- **`init_on_alloc` / `init_on_free` / `page_alloc.shuffle` disabled** — these
  can interfere with the large contiguous allocations CUDA makes. Left commented
  in `01-mios-hardening.toml` so the trade-off is explicit.
- **`kernel.unprivileged_userns_clone=1` kept enabled** — required by rootless
  Podman (the quadlet AI plane, Law 6), Waydroid, and Steam sandboxes. The `-`
  prefix suppresses the error on kernels (e.g. WSL2) that don't expose the key.
- **BPF: `unprivileged_bpf_disabled=1` + `bpf_jit_harden=2`, not a full BPF
  block** — blocks only *unprivileged* BPF load while leaving the root BPF that
  rootless Podman, k3s, and CrowdSec rely on unaffected.
- **Core dumps left on for normal processes** — CUDA crash triage needs cores;
  only set-uid dumps are disabled (`fs.suid_dumpable=0`).
- **USBGuard ships with no implicit allow-list** — the daemon is configured and
  enabled, but the admin still generates the device policy
  (`usbguard generate-policy`) for their hardware.
- **CrowdSec runs sovereign / offline** — no telemetry to crowdsec.net,
  consistent with MiOS's offline-capable, no-vendor-account design.

## How this fits the build/bootc lifecycle

These files are not applied by a running configuration agent — they are *baked*.
The Containerfile pipeline copies `usr/lib/bootc/kargs.d/`,
`usr/lib/sysctl.d/`, `etc/fapolicyd/`, and the USBGuard/firewall automation into
the image; the final `bootc container lint` (Law 4) gates the build; and on the
host `bootc upgrade`/`rollback` move the entire hardened image forward or back
as one atomic unit. There is no drift between "what the docs say" and "what's on
the box," because the doc, the kargs file, and the deployed `/usr` are the same
tree (repo root IS system root).

## Citation in MiOS docs

The canonical security guide (`usr/share/doc/mios/guides/security.md`) states:

> The posture is sourced primarily from SecureBlue's audit framework
> (<https://github.com/secureblue/secureblue>) and the Fedora hardening
> guidelines.

The root `SECURITY.md` redirects to that guide for the full posture. The
SecureBlue audit set is the *baseline*; MiOS's deviations are documented inline
in both the guide and the kargs/sysctl files themselves, so a reviewer can see
exactly what was relaxed and why.

## Cross-refs

- `usr/share/doc/mios/guides/security.md` — full MiOS hardening posture (kargs, SELinux, fapolicyd, USBGuard, CrowdSec, lockdown, MOK signing)
- `usr/lib/bootc/kargs.d/01-mios-hardening.toml`, `30-security.toml`, `31-secureblue-extended.toml` — the actual hardening kargs
- `usr/share/doc/mios/upstream/crowdsec-fapolicyd-usbguard.md` — the runtime IPS / execution-control / USB-control stack
- `SECURITY.md` — security policy + disclosure process (redirects to the guide)
