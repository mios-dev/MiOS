<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "audit"
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

# NEXT-RESEARCH — agenda for 2026-04-28 and beyond

> Prepared by `System Code (Sonnet 4.6)` at end of the 2026-04-26 research pass.
> Replaces the 2026-04-25 agenda.
> Full findings: `Knowledge-19-upstream-research-2026-04-26.md`

---

## ✅ RESOLVED — April 26, 2026

1. **Fedora 44 GA confirmed** — GO decision April 23; release April 28. `f44-ga-rpmfusion-stable` branch staged and ready.
2. **ucore-hci F43 confirmed current** — no F44 tag yet; expected 24–48h post-GA.
3. **bootc v1.15.1 confirmed latest** — Intel VROC support and `--karg-delete` added.
4. **Cockpit v361 confirmed latest** — includes CVE-2026-4631 fix.
5. **NVIDIA CTK version corrected** — latest is v1.19.0 (v1.x series). Prior "v0.1.1" reference was erroneous. CDI stable.
6. **BIB action N/A for MiOS** — MiOS uses `quay.io/centos-bootc/bootc-image-builder:latest` directly; ublue-os action deprecation does not apply.
7. **Renovate already migrated** — `minimumReleaseAge` already in `renovate.json`. No action.
8. **CrowdSec v1.7.7 confirmed** — no v2.x exists. Monthly cadence maintained.
9. **Waydroid #1883 still stalled** — no upstream progress.
10. **All T1/T2 upstream implementation items complete** — full implementation status verified.

---

## 🚨 ACTION REQUIRED — flagged for Kabu

### A. April 28 — Fedora 44 GA Day Checklist
1. **Merge `f44-ga-rpmfusion-stable`** — RPMFusion `release-44` URLs go live on GA day. Do not merge before.
2. **Watch ucore-hci digest** — poll `{{MIOS_BASE_IMAGE}}` for F44 tag (24–48h post-GA)
3. **Trigger image build** — once F44 tag is live, trigger full MiOS build from F44 base
4. **Post-build verification:**
   - `cockpit --version` ≥ 361 (CVE-2026-4631 fix)
   - `bootc --version` ≥ 1.15.1
   - `bootc container lint` passes cleanly
   - RPMFusion `release-44` URLs resolve (not 404)
   - `greenboot --check` passes on a test VM boot

### B. Fix `60-k3s.sh` wanted.d exit code
- **File:** `etc/greenboot/check/wanted.d/60-k3s.sh`
- **Issue:** Script exits `0` on K3s failure — greenboot cannot log the warning
- **Fix:** Change failure-path `exit 0` to `exit 1` (wanted.d logs non-zero as warning, does NOT trigger rollback)
- Low risk, cosmetic correctness fix

### C. Pre-rebase Cockpit mitigation (if current build is in production)
- Add `LoginTo = false` to `usr/lib/cockpit/cockpit.conf` to neutralize CVE-2026-4631 until F44 rebase delivers Cockpit ≥ 360
- Decision: Kabu to determine if current F43-based image is deployed in production

---

## Priority queue for 2026-04-28+

Order reflects decreasing urgency.

### 1. F44 rebase and smoke test (April 28)
- See checklist in ACTION REQUIRED § A above

### 2. bootc v1.14.0 feature adoption review
- Review bootc v1.14.0 changelog for new features applicable to MiOS
- Specifically: pre-flight disk space check behavior — does it affect BIB builds?
- Track issues #2130–#2132 (install-time failures) against ucore-hci F44 base

### 3. Post-rebase GNOME 50.1 / Mutter VRR check
- F44 ships GNOME 50.1 with the NVIDIA Mutter regression fixed (upstream fix April 15, 2026)
- Verify VRR and fractional scaling are functional on F44-based test build

### 4. Cockpit weekly cadence
- After F44 rebase confirms ≥ 360, check for 362+ Quadlet management regressions
- Next cadence check: ~May 5, 2026

### 5. NVIDIA CTK v1.19.0 integration
- Verify MiOS packages install v1.19.0 from the NVIDIA CTK COPR
- Confirm `45-nvidia-cdi-refresh.sh` ≥1.18 requirement satisfied (v1.19.0 > 1.18 ✅)

### 6. ublue-os/cayo stability check (monthly)
- Monitor ublue-os/cayo for MiOS-3 base migration candidacy. This monitoring is crucial for evaluating its suitability as a future base image.
- Still not production-stable as of April 2026

### 7. Waydroid #1883 (monthly)
- Check for any developer assignment or PR activity

### 8. CrowdSec v1.8.x watch (monthly)
- v1.7.7 is current; no urgency

---

## Upstream feeds to monitor

- **bootc releases:** https://github.com/bootc-dev/bootc/releases
- **bootc issues #2130–2132:** https://github.com/bootc-dev/bootc/issues
- **ucore-hci F44 packages:** https://github.com/orgs/ublue-os/packages/container/package/ucore-hci
- **Cockpit releases:** https://github.com/cockpit-project/cockpit/releases
- **NVIDIA CTK releases:** https://github.com/NVIDIA/nvidia-container-toolkit/releases
- **NVIDIA open kernel modules:** https://github.com/NVIDIA/open-gpu-kernel-modules/releases
- **Waydroid #1883:** https://github.com/waydroid/waydroid/issues/1883
- **ublue-os/cayo:** https://github.com/ublue-os/cayo
- **CrowdSec releases:** https://github.com/crowdsecurity/crowdsec/releases
- **RPM Fusion Fedora 44 release:** https://rpmfusion.org/RPM_Fusion_Free_Repository_Status
- **Fedora 44 errata / updates:** https://bodhi.fedoraproject.org/updates/?release=F44

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
