<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "memories"
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

# MiOS Upstream Research Plan
# Generated: 2026-04-24 UTC | Agent: System Code (Sonnet 4.6)

> This document summarises every upstream finding from the April 2026 bootc
> ecosystem survey and maps each finding to an actionable MiOS item.

---

## 1. bootc Upstream (bootc-dev/bootc v0.1.1)

### 1.1 New Commands — Implement via MOTD / tooling
| Finding | MiOS Action |
|---------|---------------|
| `bootc upgrade --download-only` / `--from-downloaded` staged-update pattern | Document in MOTD; add greenboot check that verifies `bootc status --booted` |
| `bootc completion bash` — shell completions | Add `RUN bootc completion bash > /etc/bash_completion.d/bootc` in Containerfile |
| `bootc usroverlay --readonly` (v0.1.1) | Document in DIAGNOSTICS.md as inspection tool |
| `bootc status --booted` | Use in greenboot health checks |
| `bootc rollback` NOT supported on composefs-native | Stay on OSTree backend (already doing this via `prepare-root.conf enabled=verity` over OSTree, not composefs-native backend) |

### 1.2 kargs.d Format
| Finding | MiOS Action |
|---------|---------------|
| `match-architectures` must use Rust arch names (`x86_64`, not `amd64`) | Already correct on all files EXCEPT `30-security.toml` — add it |
| No `[kargs]` headers or `delete` keys — lint enforced | Already compliant |

### 1.3 composefs / prepare-root.conf
| Finding | MiOS Action |
|---------|---------------|
| `[composefs] enabled = verity` requires ext4 or btrfs (NOT XFS) | Already `ext4` in bib-configs — correct |
| composefs-native backend lacks `bootc rollback` and `--download-only` | Already on OSTree backend, NOT composefs-native — correct |
| `[sysroot] readonly = true` for read-only sysroot | Already present in `prepare-root.conf` — correct |

### 1.4 bootc container lint rules (v1.15.x)
| Finding | MiOS Action |
|---------|---------------|
| Checks `/var` dirs for missing `tmpfiles.d` entries | Already compliant (recent audit confirmed) |
| Validates `match-architectures` values | Fix `30-security.toml` |
| Checks for files in `/usr/etc` (forbidden) | No files there — correct |

---

## 2. Universal Blue / ucore-hci

### 2.1 NVIDIA
| Finding | MiOS Action |
|---------|---------------|
| ucore-hci now on NVIDIA v0.1.1 open modules | Inherited via base image — no action |
| RTX 50xx requires open modules exclusively | Already handled by `34-gpu-detect.sh` |
| `NVreg_UseKernelSuspendNotifiers=1` — only set if specific suspend issues appear | Do NOT add unconditionally — journal this finding |
| CDI is default mode in nvidia-container-toolkit v0.1.1 | Already enabled via `nvidia-cdi-refresh.path/.service` — correct |
| DO NOT use nvidia-container-toolkit v0.1.1 (CDI regression) | Tracked in research notes |

### 2.2 MOK / Secure Boot
| Finding | MiOS Action |
|---------|---------------|
| Microsoft UEFI CA 2011 cert expires June 26, 2026 | Existing enrollments unaffected; ensure new shim uses 2023 key; update edk2-ovmf on VM hosts; document in DIAGNOSTICS.md |
| MOK key must be 2048-bit RSA only (4096-bit hangs some shim versions) | Already 2048-bit — correct |

### 2.3 ucore Notable Defaults
| Finding | MiOS Action |
|---------|---------------|
| Cockpit ≥ 330 required for composefs compat | Fedora 42 ships 349+ — satisfied |
| `cockpit.socket` race with `libvirtd.socket` | Add `After=libvirtd.socket` to `cockpit.socket.d/10-mios.conf` |
| `libvirtd` 45s shutdown timeout too short | Already fixed in `libvirtd.service.d/10-mios.conf` (TimeoutStopSec=120) |
| `uBlue COPR repos disabled before generic installs` (Apr 2026 commit) | If MiOS re-enables COPR repos, wrap with explicit enable/disable |
| `ublue-os/cayo` — composefs-native HCI successor to ucore-hci | Monitor for MiOS-3 base migration (no action now) |

### 2.4 Cosign / Signing (CRITICAL — DO NOT UPGRADE)
| Finding | MiOS Action |
|---------|---------------|
| Cosign v3 `--new-bundle-format` BREAKS rpm-ostree/bootc (rpm-ostree#5509) | Stay on cosign v0.1.1 — already pinned correctly |
| `cosign-installer@v0.1.1` with `cosign-release: v0.1.1` — correct pattern | Already correct in `build.yml` — no change |
| Always pass `--new-bundle-format=false` when signing | Already in `build.yml` signing steps — correct |

---

## 3. Fedora bootc Ecosystem

### 3.1 Fedora 44 / GNOME 50
| Finding | MiOS Action |
|---------|---------------|
| GNOME 50 (Mar 18, 2026): X11 completely removed | Already migrated to `gnome-remote-desktop` in scripts — correct |
| GNOME 50 GRD: Vulkan/VA-API HW acceleration for RDP | Already using GRD — benefits automatically on F44 |
| VRR + fractional scaling default ON in Mutter | Benefits automatically |
| FUSE 2 removed from Atomic Desktops | Verify `fuse3` used everywhere (not `fuse`) |

### 3.2 Fedora 44 Sysctl Hardening Proposals
| Finding | MiOS Action |
|---------|---------------|
| `net.core.bpf_jit_harden = 2` (Fedora 44 default) | Add to `99-mios-hardening.conf` now (ahead of F44) |
| `kernel.yama.ptrace_scope = 1` (Fedora 44 default) | Already at `= 2` — more restrictive, correct |
| `kernel.unprivileged_bpf_disabled = 1` | Add to `99-mios-hardening.conf` |
| `kernel.sysrq = 0` (production hardening) | Add to `99-mios-hardening.conf` |
| `kernel.printk = 3 3 3 3` (suppress kernel log to console) | Add to `99-mios-hardening.conf` |

### 3.3 DNF5 / Package
| Finding | MiOS Action |
|---------|---------------|
| DNF5 is default in Fedora 42+ | Already using `${DNF_SETOPT[@]}` — correct |
| `bootupd automatic bootloader updates` — do NOT mask | Verify service not masked in preset |

---

## 4. Podman Quadlets (v5.7/v5.8)

### 4.1 New Directives
| Finding | MiOS Action |
|---------|---------------|
| `HttpProxy=false` in `[Container]` — prevents host proxy credential leak to containers | Add to ALL MiOS Quadlet `.container` files |
| `StopTimeout=120` in `[Pod]` — no pod files currently — N/A | N/A |
| `.artifact` file type — NOT yet valid for bound-images.d | Do not use until bootc supports it |
| Quadlet `%i` specifier for templated volume/network names | Note for future multi-instance workloads |

### 4.2 bound-images.d
| Finding | MiOS Action |
|---------|---------------|
| Only `.image` and `.container` valid as symlink targets | All current symlinks are `.container` — correct |
| Do NOT add `/usr/lib/bootc/storage` to global `storage.conf` | Verify — should only be per-Quadlet `GlobalArgs` |
| Correct: `GlobalArgs=--storage-opt=additionalimagestore=/usr/lib/bootc/storage` per bound Quadlet | Already on guacamole, crowdsec-dashboard, postgres, guacd — correct |

---

## 5. K3s on bootc

### 5.1 K3s v0.1.1 Changes
| Finding | MiOS Action |
|---------|---------------|
| containerd 2.0 config schema changed → `config-v3.toml.tmpl` | Add K3s containerd v3 config template to system_files |
| `k3s-selinux` RPM must be installed BEFORE k3s binary | Verify `19-k3s-selinux.sh` order |
| NVIDIA auto-detected by K3s v1.34+ in `$PATH` | No action needed |
| Airgap `.cache.json` for conditional image import (v0.1.1+) | Add to k3s-manifests if airgap deployment is needed |

### 5.2 Greenboot K3s Health Check
| Finding | MiOS Action |
|---------|---------------|
| Add K3s ready check to greenboot required.d | Create `required.d/40-k3s.sh` |

---

## 6. Greenboot-rs (Fedora 43+ default)

### 6.1 Configuration
| Finding | MiOS Action |
|---------|---------------|
| `greenboot.conf` with `GREENBOOT_MAX_BOOT_ATTEMPTS=3`, `GREENBOOT_WATCHDOG_CHECK_ENABLED=true` | Create `etc/greenboot/greenboot.conf` (currently missing) |
| `greenboot-rs` v0.1.1+ — same script directories, same systemd integration | No structural changes needed |
| Rollback via `bootc rollback` for bootc systems | Already integrated via greenboot-rs |

---

## 7. CrowdSec Sovereign Mode
| Finding | MiOS Action |
|---------|---------------|
| Disable CAPI (cloud API) by leaving `credentials_path: ""` | Verify sovereign mode config in system_files |
| Pre-install hub collections at build time with `cscli collections install` | Verify in 13-ceph-k3s.sh or equivalent |
| Journald acquisition for systemd logs | Verify acquis.d pattern |

---

## 8. Security Hardening

### 8.1 New kargs
| Finding | MiOS Action |
|---------|---------------|
| `spectre_bhi=on` — Branch History Injection mitigation (newer Spectre variant) | Add to `01-mios-hardening.toml` |
| `kvm.nx_huge_pages=force` — KVM security for NX huge pages | Add to `01-mios-hardening.toml` |
| `tsx=off` — Transactional Sync Extensions (Intel security) | Add to `01-mios-hardening.toml` |

### 8.2 MAC Randomization (secureblue pattern)
| Finding | MiOS Action |
|---------|---------------|
| `/usr/lib/NetworkManager/conf.d/rand_mac.conf` — WiFi scan + stable MAC randomization | Create this file (currently missing) |

### 8.3 fapolicyd
| Finding | MiOS Action |
|---------|---------------|
| `db_max_size = auto` prevents DB fill on large images | Verify in fapolicyd config |
| Run `fapolicyd-cli --update` after package installation | Verify in `20-fapolicyd-trust.sh` |

---

## 9. CI / GitHub Actions

### 9.1 BIB Action
| Finding | MiOS Action |
|---------|---------------|
| `ublue-os/bootc-image-builder-action` is in maintenance mode; upstream is `osautomation/bootc-image-builder-action@v0.1.1` | Evaluate migration — note in research doc; do not rush |

### 9.2 bootc Shell Completions
| Finding | MiOS Action |
|---------|---------------|
| `bootc completion bash` generates bash completions | Add to Containerfile after bootc install |

---

## 10. Network / Infrastructure

### 10.1 cockpit.socket ordering
| Finding | MiOS Action |
|---------|---------------|
| cockpit.socket may start before libvirtd.socket, breaking Machines UI | Add `cockpit.socket.d/10-mios.conf` with `[Unit] After=libvirtd.socket` |
| `cockpit.socket.d/` already has `listen.conf` and `listen-all.conf` — do not modify | Add new file only |

---

## Summary: Items Already Correct (No Action)
- `prepare-root.conf` `enabled = verity` + `readonly = true` ✅
- All kargs.d files use flat `kargs = [...]` ✅ (except 30-security.toml missing match-architectures)
- Cosign v0.1.1 pinned, `--new-bundle-format=false` in all signing steps ✅
- `crowdsec-dashboard.container`, `mios-guacamole.container`, `guacamole-postgres.container`, `guacd.container` all have `GlobalArgs=--storage-opt=additionalimagestore=/usr/lib/bootc/storage` ✅
- `libvirtd.service.d/10-mios.conf` has `After=libvirtd.socket` + `TimeoutStopSec=120` ✅
- `kernel.yama.ptrace_scope = 2` (more restrictive than F44's planned `= 1`) ✅
- `kernel.kptr_restrict = 2` ✅
- GNOME 50 migration to `gnome-remote-desktop` complete ✅
- NVIDIA blacklist by default, bare-metal unblacklist pattern ✅
- BIB using `ext4` (compatible with composefs verity) ✅
- weekly GHCR cleanup in build.yml ✅

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
