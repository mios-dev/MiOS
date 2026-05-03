# SecureBlue — Audit Framework 'MiOS' Draws From

> MiOS's `SECURITY.md` is "sourced primarily from SecureBlue's audit
> framework and the Fedora hardening guidelines." Most of the kargs and
> sysctl values in 'MiOS' trace to SecureBlue's recommended set.

## Project

- Repo: <https://github.com/secureblue/secureblue>
- Fedora hardening guidelines: <https://docs.fedoraproject.org/en-US/quick-docs/securing-fedora/>
- Kernel kargs reference: <https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html>
- Sysctl reference: <https://www.kernel.org/doc/Documentation/sysctl/>

## What 'MiOS' adopts

| SecureBlue measure | 'MiOS' adoption | Where |
| --- | --- | --- |
| `slab_nomerge` | ✅ | `usr/lib/bootc/kargs.d/00-mios.toml` |
| `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` | **❌ disabled** — CUDA incompatibility | `00-mios.toml` (commented; SECURITY.md notes this) |
| `randomize_kstack_offset=on`, `pti=on`, `vsyscall=none` | ✅ | `00-mios.toml` |
| `lockdown=integrity` | ✅ (SecureBlue prefers `confidentiality`; 'MiOS' chose `integrity` to allow signed-but-unlocked workloads) | `00-mios.toml` |
| Spectre/Meltdown/L1TF/GDS mitigations (full set) | ✅ | `00-mios.toml` |
| `kernel.kptr_restrict=2`, `kernel.dmesg_restrict=1` | ✅ | `usr/lib/sysctl.d/99-mios-hardening.conf` |
| `kernel.unprivileged_bpf_disabled=1`, `net.core.bpf_jit_harden=2` | ✅ | `99-mios-hardening.conf` |
| `kernel.kexec_load_disabled=1`, `kernel.io_uring_disabled=2` | ✅ | `99-mios-hardening.conf` |
| `fs.protected_*` series | ✅ | `99-mios-hardening.conf` |
| Network: rp_filter, tcp_syncookies, accept_redirects=0 | ✅ | `99-mios-hardening.conf` |
| fapolicyd deny-by-default | ✅ | `etc/fapolicyd/fapolicyd.rules` |
| USBGuard | ✅ (off by default) | per `SECURITY.md` §USBGuard |
| firewalld default-deny | ✅ (drop zone) | `automation/33-firewall.sh` |
| Kernel module signing | ✅ (via base-image MOK) | inherited from ucore-hci |

## What 'MiOS' diverges on

- `lockdown=integrity` not `confidentiality` (allows kexec for in-image testing flows)
- `init_on_alloc`/`init_on_free`/`page_alloc.shuffle` disabled (NVIDIA CUDA)
- USBGuard off by default (admin opt-in via `usbguard generate-policy`)
- CrowdSec sovereign/offline mode (no telemetry to crowdsec.net)

## Citations in 'MiOS' docs

`SECURITY.md` opens with:

> Defense-in-depth posture, sourced primarily from SecureBlue's audit
> framework (https://github.com/secureblue/secureblue) and the Fedora
> hardening guidelines.

The SecureBlue audit set is the *baseline* — MiOS's deviations are
documented inline so a reviewer can see exactly what was relaxed and
why.

## Cross-refs

- `usr/share/doc/mios/80-security.md`
- `usr/share/doc/mios/40-kargs.md`
- `usr/share/doc/mios/upstream/crowdsec-fapolicyd-usbguard.md`
