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

# MiOS Upstream Implementation Work Plan
# Generated: 2026-04-24 UTC | Agent: System Code (Sonnet 4.6)

> Derived from upstream-research-plan.md.
> All items are concrete file changes ordered by priority tier.
> Each change is self-contained and reverts cleanly.

---

## TIER 1 — Security hardening gaps (implement now)

### T1.1 — Fix `30-security.toml` missing `match-architectures`
**File:** `usr/lib/bootc/kargs.d/30-security.toml`
**Problem:** All other kargs.d files have `match-architectures = ["x86_64"]`. This file is the only one missing it. On a multi-arch build this would apply these kargs universally.
**Fix:** Append `match-architectures = ["x86_64"]` below the `kargs` array.

### T1.2 — New hardening kargs in `01-mios-hardening.toml`
**File:** `usr/lib/bootc/kargs.d/01-mios-hardening.toml`
**Problem:** Three upstream-recommended mitigations missing:
- `spectre_bhi=on` — Branch History Injection (BHI/Spectre-BHB) mitigation, not covered by `spectre_v2=on`
- `kvm.nx_huge_pages=force` — Forces KVM to use NX-mapped huge pages, preventing cross-VM data leakage via huge page aliasing
- `tsx=off` — Disables Intel TSX (TAA/MDS attack surface); no-op on AMD (9950X3D) but correct for Intel deployments of MiOS
**Fix:** Add three new karg entries to the existing array.

### T1.3 — Add BPF JIT hardening + sysrq + printk to sysctl
**File:** `usr/lib/sysctl.d/99-mios-hardening.conf`
**Problem:** Three Fedora-44-targeted hardening sysctls not yet present:
- `net.core.bpf_jit_harden = 2` — Hardens BPF JIT against JIT-spray attacks (eBPF is heavily used by CrowdSec, K3s, CNI — this restricts BPF-compiled code to non-mappable memory)
- `kernel.unprivileged_bpf_disabled = 1` — Prevents unprivileged users from loading BPF programs (rootless Podman/K3s use cgroup BPF as root, unaffected)
- `kernel.sysrq = 0` — Disables magic SysRq key on production systems (prevents physical console attacks)
- `kernel.printk = 3 3 3 3` — Suppresses kernel messages from leaking to the console (avoids information disclosure on physical console; journal still gets everything)
**Fix:** Append four new sysctl entries with comments.

### T1.4 — Create `greenboot.conf` (file completely missing)
**File:** `etc/greenboot/greenboot.conf` (NEW)
**Problem:** The greenboot-rs daemon reads its configuration from `/etc/greenboot/greenboot.conf`. Without it, greenboot uses hardcoded defaults (3 boot attempts is already the default, but watchdog is disabled). Explicit config makes intent auditable.
**Fix:** Create the file with `GREENBOOT_MAX_BOOT_ATTEMPTS=3` and `GREENBOOT_WATCHDOG_CHECK_ENABLED=true`.

### T1.5 — Create MAC randomization NetworkManager config (file completely missing)
**File:** `usr/lib/NetworkManager/conf.d/rand_mac.conf` (NEW)
**Problem:** No MAC randomization configured. On WiFi, persistent MACs enable passive tracking across networks.
**Fix:** Create the NM config enabling stable WiFi scan + connection MAC randomization (secureblue pattern). `stable` mode uses a per-connection seed so MACs are consistent within the same network but differ across networks.

---

## TIER 2 — Completeness gaps (implement now)

### T2.1 — Add greenboot network health check
**File:** `etc/greenboot/check/required.d/30-network.sh` (NEW)
**Problem:** No network reachability check in greenboot. If a bad image breaks the network stack, the system should auto-rollback.
**Fix:** Create a required.d script that waits up to 30s for DNS resolution of `ghcr.io` (the update registry). Failure triggers rollback. Uses `systemd-resolve` (available in ucore).

### T2.2 — Add greenboot K3s health check
**File:** `etc/greenboot/check/wanted.d/60-k3s.sh` (NEW — `wanted.d`, not `required.d`)
**Problem:** K3s may not be enabled on all MiOS roles (desktop role has it disabled). A `required.d` check would cause desktop-role machines to always fail greenboot. Use `wanted.d` so failure is logged but does not trigger rollback; the `40-role-target.sh` check (already present) handles role-level failures.
**Fix:** Create `wanted.d/60-k3s.sh` that checks K3s only if it is active/enabled.

### T2.3 — Add `HttpProxy=false` to all Quadlet container files
**Files:** All `.container` files in `usr/share/containers/systemd/`
**Problem:** Without `HttpProxy=false`, Podman forwards the host's `http_proxy`/`https_proxy` env vars into every container. On workstations this leaks potential corporate proxy credentials or proxy config into untrusted containers.
**Containers to patch:**
- `crowdsec-dashboard.container` — add `HttpProxy=false`
- `mios-guacamole.container` — add `HttpProxy=false`
- `mios-guacd.container` — DELETED (consolidated into guacd.container)
- `guacamole-postgres.container` — add `HttpProxy=false`
- `guacd.container` — add `HttpProxy=false`
- `ceph-radosgw.container` — add `HttpProxy=false` (also needs `GlobalArgs` since it's NOT in bound-images.d — actually it should NOT get GlobalArgs since it's not bound; skip GlobalArgs for ceph)

### T2.4 — Add `cockpit.socket.d/10-mios.conf` (ordering fix)
**File:** `usr/lib/systemd/system/cockpit.socket.d/10-mios.conf` (NEW)
**Problem:** `cockpit.socket` activates before `libvirtd.socket`. When a user opens the Machines page immediately after boot, libvirtd may not be ready, causing "Failed to connect to libvirt" errors. Adding the ordering dependency prevents the race.
**Fix:** New drop-in with `[Unit] After=libvirtd.socket`.

### T2.5 — Add bootc bash completion to Containerfile  ✅ DONE
**File:** `Containerfile`
**Status:** Implemented at `Containerfile:154` (`RUN bootc completion bash > /etc/bash_completion.d/bootc`) before the final `bootc container lint`. Verified 2026-04-25 by System Opus 4.7.

---

## TIER 3 — Documentation / coordination

### T3.1 — Append AI journal entry
**File:** `.ai/foundation/memories/journal.md`
**Action:** Append complete session journal entry (THOUGHT, LEARNING, DISCOVERY, ACTION, SUGGESTED ALTERNATIVE) covering all changes made in this session.

### T3.2 — Update .env
**File:** `.env`
**Action:** Update `AI_ARCH_BASELINE` to reflect the upstream research integration. Add notes about cosign v3 hold and cayo monitoring.

---

## ITEMS DELIBERATELY DEFERRED (not in this pass)

| Item | Reason deferred |
|------|----------------|
| `osautomation/bootc-image-builder-action@v0.1.1` migration | Current `ublue-os` action still works; migration is non-trivial and needs testing |
| K3s containerd v3 config template | Requires knowing exact K3s install path in image; needs deeper audit of `13-ceph-k3s.sh` |
| K3s airgap `.cache.json` | Requires knowing which images are pre-pulled; needs separate research pass |
| `bootc upgrade --download-only` systemd timer | Runtime feature, not build-time; document in DIAGNOSTICS.md separately |
| `ublue-os/cayo` base migration evaluation | Cayo not yet stable; track in NEXT-RESEARCH.md |
| TPM2-LUKS `bootc install --block-setup tpm2-luks` | Has known reboot unlock bug (Issue #421); defer until fixed |
| `[etc] transient = true` in prepare-root.conf | Too aggressive for workstation — breaks NM keyfiles, SSH config |
| Adding `ceph-radosgw.container` to bound-images.d | Requires separate RADOS gateway architecture decision |

---

## File Change Summary

| File | Operation | Category |
|------|-----------|----------|
| `usr/lib/bootc/kargs.d/30-security.toml` | MODIFY | T1.1 |
| `usr/lib/bootc/kargs.d/01-mios-hardening.toml` | MODIFY | T1.2 |
| `usr/lib/sysctl.d/99-mios-hardening.conf` | MODIFY | T1.3 |
| `etc/greenboot/greenboot.conf` | CREATE | T1.4 |
| `usr/lib/NetworkManager/conf.d/rand_mac.conf` | CREATE | T1.5 |
| `etc/greenboot/check/required.d/30-network.sh" | CREATE | T2.1 |
| `etc/greenboot/check/wanted.d/60-k3s.sh` | CREATE | T2.2 |
| `usr/share/containers/systemd/crowdsec-dashboard.container` | MODIFY | T2.3 |
| `usr/share/containers/systemd/mios-guacamole.container` | MODIFY | T2.3 |
| `usr/share/containers/systemd/guacamole-postgres.container` | MODIFY | T2.3 |
| `usr/share/containers/systemd/guacd.container` | MODIFY | T2.3 |
| `usr/share/containers/systemd/ceph-radosgw.container` | MODIFY | T2.3 |
| `usr/lib/systemd/system/cockpit.socket.d/10-mios.conf` | CREATE | T2.4 |
| `Containerfile` | DONE (line 154) | T2.5 |
| `.ai-context/ai-journal.md` | APPEND | T3.1 |
| `.ai-context/AI-ENVIRONMENT.md` | MODIFY | T3.2 |

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
