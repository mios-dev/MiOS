<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Final build-time validation script that enforces mandatory security invariants, such as OpenSSH version minimums and Cockpit configuration checks, to abort the build if the image is insecure or non-compliant.
AI-related: /usr/share/mios/ai, /etc/mios/ai, mios-ceph, mios-k3s, wsl-init.service
AI-functions: _sysusers_effective, _gid_in_etc_group

<!-- mios-src:845010814b0e from automation/99-postcheck.sh:1-5 -->

