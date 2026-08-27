<!-- AI-hint: Per-feature audit of MiOS's shipped-but-inert runtime features (greenboot, clevis/LUKS, chrony, ROCm/venus, ceph, mdevctl, freeipa/lldap, nut, guacamole/guacd, virt-v2v) classifying each as wired-from-SSOT or dead weight with file:line evidence, plus a self-contained drop-in artifact that projects [greenboot].critical_services from mios.toml into a generated env file + a rollback-safe required.d health-check, closing the triple-hardcoded critical-services gap. -->
<!-- AI-related: usr/share/mios/mios.toml, automation/42-chrony-render.sh, automation/43-nut-render.sh, automation/78-greenboot.sh, automation/13-accounts-db.sh, automation/15-freeipa-client.sh, automation/23-gpu-passthrough.sh, automation/25-gpu-cdi-toolkits.sh, automation/98-drift-checks.sh, usr/libexec/mios/mios-luks-enroll, usr/libexec/mios/mios-clevis-luks-gen, usr/libexec/mios/mios-mdev-define-gen, usr/libexec/mios/mios-lldap-seed, usr/libexec/mios/mios-v2v-import, usr/libexec/mios/mios-chrony-ptp-dropin, usr/lib/systemd/system/mios-luks-enroll.service, usr/lib/systemd/system/mios-chrony-ptp.service, usr/lib/systemd/system/mios-gpu-amd.service, usr/lib/systemd/system/mios-sriov-init.service, usr/lib/systemd/system-preset/90-mios.preset, usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh, docs/agy/doc-container-runtime.md -->

# MiOS Runtime Wire Audit — SSOT Feature Integration

**Date:** 2026-07-31 · **SSOT:** `usr/share/mios/mios.toml`

## Feature Integration Summary
- **Greenboot:** Health check probes `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh` evaluate `mios-agent-pipe`, `mios-llm-light`, and `mios-pgvector` services.
- **Disk Encryption:** `[security.disk_encryption]` drives `usr/libexec/mios/mios-luks-enroll` (TPM2/systemd-cryptenroll).
- **Time Sync:** `[network.ntp]` drives `automation/42-chrony-render.sh` and PTP drop-in units.
- **GPU & Virtualization:** `[gpu.vendors]` and CDI toolkits manage VFIO passthrough and hardware acceleration.
