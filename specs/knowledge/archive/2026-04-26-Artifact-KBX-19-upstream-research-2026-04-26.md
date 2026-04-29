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

# MiOS Upstream Research — April 26, 2026
# Agent: System Code (Sonnet 4.6) | Scheduled research pass

> This document replaces the open items from `Historical-Next-Research.md` (2026-04-25 agenda).
> All findings are from live web research performed 2026-04-26.

---

## Executive Summary

All TIER 1 and TIER 2 upstream implementation items are **complete**. The `f44-ga-rpmfusion-stable` branch is staged and ready. The primary operational focus for the next 72 hours is the **F44 GA window (April 28)**. One minor defect was found in `60-k3s.sh`. No critical security gaps remain beyond what the F44 rebase will resolve.

---

## 1. Fedora 44 GA

**Status:** Confirmed GO — release on **April 28, 2026**

- Final GO decision issued April 23, 2026 after two prior delays (original date: April 14)
- ucore-hci **still on Fedora 43** as of April 26. `stable-nvidia` tag will NOT point to F44 until ublue-os publishes F44-based images after the GA date
- Expected ucore-hci F44 availability: 24–48 hours after April 28 GA

**MiOS actions:**
- `f44-ga-rpmfusion-stable` branch: merge on **April 28** (RPMFusion `rawhide` → `release-44` URLs become live on GA)
- After merging, wait for `{{MIOS_BASE_IMAGE}}` digest to update before triggering a full image build
- Monitor: `docker manifest inspect {{MIOS_BASE_IMAGE}}` for Fedora 44 base

---

## 2. bootc Latest Release

**Status:** **v1.15.1** (as of April 24, 2026)

- Significantly newer than the "v1.1.x" cited in prior research documentation.
- **v1.15.1 Fixes:** Intel VROC support, `--karg-delete` command, and IPC namespace deadlock fix.
- **v1.15.0 Features:** `bootc container inspect` verb for image metadata, `--download-only` for caching updates.
- Includes pre-flight disk-space checks to prevent out-of-space failures.
- bootc is delivered via the base image (ucore-hci) — MiOS inherits whichever version ucore-hci ships; no explicit version management needed.

**MiOS actions:**
- None immediately. Post-F44-rebase, verify `bootc --version` in a test build matches ≥1.15.1.
- Continue deferring composefs-native backend (Issue #1190): OSTree backend is stable and `bootc rollback` depends on it.

---

## 3. Cockpit CVE-2026-4631

**Status:** FIXED in Cockpit 360 (April 8, 2026); Latest is **v361** (April 21, 2026).

**Vulnerability:**
- CVSS 9.8 — Unauthenticated RCE via SSH argument injection in the remote-login web UI.
- Fixed in v360; v361 is the current stable release.
- Affects Cockpit ≥ 327 / < 360 paired with OpenSSH < 9.6.

**Pre-rebase mitigation** (if the current F43-based build is in production):
```ini
# usr/lib/cockpit/cockpit.conf  (or drop-in)
[WebService]
LoginTo = false
```
This disables the remote-login endpoint entirely, removing the attack surface without disabling Cockpit.

**Post-rebase verification** (April 28+):
- Confirm `cockpit --version` ≥ 360 in the F44-based image.
- F44 is confirmed to ship ≥ 360/361.

---

## 4. NVIDIA Container Toolkit

**Status:** v1.19.0 (March 2025) — stable; CDI is production-ready

**Correction from prior research:** Previous journal entries cited "v0.1.1 (Mar 2026)" for the CTK — this was incorrect. The CTK version series is **v1.x.x**. v1.19.0 is the current latest.

**CDI status:**
- CDI has been production-stable since v1.12.0; v1.19.0 adds improvements for systemd service triggering and initramfs support
- MiOS `45-nvidia-cdi-refresh.sh` already requires ≥ 1.18 — satisfied by v1.19.0 ✅
- `Avoid NCT 1.16.2` rule still applies (unresolvable CDI devices regression)

**MiOS actions:** None. Current setup is correct.

---

## 5. NVIDIA Driver / RTX 50xx (Blackwell)

**Status:** Proprietary drivers do NOT support RTX 50xx. Open modules (driver 570+) are mandatory.

- RTX 5090/5080/5070/5060 all require open kernel module variant (MIT/GPL)
- Driver series is 570+, not 600-series
- No 600-series driver announced; no new high-end gaming GPU expected before 2028 (RTX 60 series)

**MiOS status:** `34-gpu-detect.sh` already handles open module requirement for RTX 50xx via the RTX 50-series detection logic. No action needed.

---

## 6. Waydroid CDI Issue #1883

**Status:** Stalled — no developer assigned, no PRs, no official response since May 2025

- Full GPU acceleration for Waydroid + NVIDIA CDI has no upstream path
- No timeline for resolution
- SwiftShader fallback (already in MiOS via `35-gpu-pv-shim.sh` for Hyper-V) is the only working GPU option in Waydroid

**MiOS actions:** Continue monitoring monthly. No action.

---

## 7. osautomation/bootc-image-builder-action (BIB)

**Status:** v0.0.2 (early-stage). ublue-os action is in maintenance mode.

**NOT applicable to MiOS** — MiOS `build-artifacts.yml` uses `quay.io/centos-bootc/bootc-image-builder:latest` directly as a container, not via a GitHub Action. The ublue-os/osbuild action migration does not apply to this workflow.

**MiOS actions:** None. Re-evaluate when osautomation/bootc-image-builder-action reaches v1.0.

---

## 8. Renovate Configuration

**Status:** MiOS already uses `minimumReleaseAge` — migration already complete ✅

- `stabilityDays` was renamed to `minimumReleaseAge` (PR #21376). Renovate auto-migrates configs.
- `renovate.json` already contains `"minimumReleaseAge": "7 days"` — no action needed.

---

## 9. CrowdSec

**Status:** v1.7.7 (March 23, 2026). No v2.x exists.

- Latest stable: v1.7.7 with RE2 regex library adoption and WAF rule improvements
- Prior research reference to "v0.1.1" was likely a version-number confusion. The CrowdSec release series remains v1.x.x
- No new CVEs in release notes

**MiOS actions:** None. Monthly cadence confirmed.

---

## 10. Konflux Signing Key Chain

**Status:** No Fulcio root rotation announced. Existing signing infrastructure continues.

- F44 bootc artifacts will be built and signed via Konflux (approved F44 change proposal)
- No `policy.json` changes detected; Fedora signing keys continue
- Post-F44-rebase: verify Fedora 44 bootc base image verifies cleanly against existing `policy.json`

---

## Defect Found: `60-k3s.sh` Silent Success on K3s Failure

**File:** `etc/greenboot/check/wanted.d/60-k3s.sh`

**Issue:** Script exits `0` even when K3s health check fails (timeout reached, `kubectl get nodes` never succeeded). This prevents greenboot from logging the failure in its `wanted.d` warning log.

**Correct behavior for `wanted.d`:** Exit `1` on failure. Greenboot will log the non-zero exit as a warning and continue without triggering rollback (unlike `required.d` which does trigger rollback). Current `exit 0` silently discards the failure signal entirely.

**Fix:** Replace final `exit 0` with `exit 1` in the failure path:
```bash
echo "K3s check failed: nodes not reachable after ${TIMEOUT}s."
exit 1  # wanted.d: logged as warning, does NOT trigger rollback
```

This is a low-risk correctness fix. No rollback behavior changes; only greenboot's warning log is affected.

---

## Summary: Action Queue for April 28, 2026

| Priority | Action | Owner | When |
|----------|--------|-------|------|
| 1 | Merge `f44-ga-rpmfusion-stable` | Kabu | April 28 (GA day) |
| 2 | Watch ucore-hci digest for F44 tag | Kabu / System | April 28–30 |
| 3 | Post-rebase: verify Cockpit ≥ 360 | Build agent | After F44 image builds |
| 4 | Post-rebase: verify `bootc --version` ≥ 1.14.0 | Build agent | After F44 image builds |
| 5 | Fix `60-k3s.sh` exit 1 on failure | System | Next build pass |
| 6 | Pre-rebase: consider Cockpit `LoginTo=false` mitigation | Kabu decision | Before April 28 if prod |

---

## Items Remaining Deferred

| Item | Reason |
|------|--------|
| composefs-native backend testing | OSTree backend stable; `bootc rollback` requires it |
| UKI architecture (Issue #806) | Blocked on composefs-native and ucore-hci adoption |
| K3s containerd v3 config template | Needs deeper audit of `13-ceph-k3s.sh` |
| systemd-remount-fs unmask | Upstream bug not resolved |
| osbuild BIB action migration | Not applicable; MiOS uses BIB container directly |

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
