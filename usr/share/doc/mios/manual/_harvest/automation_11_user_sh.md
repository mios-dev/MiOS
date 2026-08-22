<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=universal AI-hint: Configures...

!/bin/bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures PAM via authselect, creates the primary system user with fixed UID 1000, and assigns group memberships (wheel, libvirt, docker) to ensure proper session permissions and container access.
AI-related: mios-custom, mios-home, mios-wheel, mios-nfs

<!-- mios-src:249acad8a0b5 from automation/11-user.sh:1-4 -->

