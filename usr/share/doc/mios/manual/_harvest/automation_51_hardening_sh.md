<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Enables and symlinks security services (usbguard, auditd, fapolicyd) into the multi-user.target.wants directory and pre-generates fapolicyd trust databases to harden the system during the build/provisioning phase.
AI-related: mios-hardening, multi-user.target, usbguard.service, auditd.service, fapolicyd.service

<!-- mios-src:153168e72d02 from automation/51-hardening.sh:1-4 -->

