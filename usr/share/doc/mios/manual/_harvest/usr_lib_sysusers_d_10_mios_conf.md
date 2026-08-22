<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines system user/group IDs and permissions for the 'mios' login account, ensuring correct UID 1000 assignment and group memberships for hardware access, service integration, and cross-domain data access.
AI-related: /etc/mios/hermes/api.env, mios-virt, mios-guacamole, mios-hermes, mios-env, mios-services, mios-ai, mios-sys
'MiOS' System Users
CRITICAL: 'mios' is a LOGIN user. UID must be >= UID_MIN (1000 default).
Auto-allocation ('-') picks from the SYSTEM range (<1000), which makes
systemd-logind skip XDG_RUNTIME_DIR creation -- dbus/dconf/Wayland session
services then all fail. Pin to 1000.

The 'g mios 1000' line MUST come BEFORE the 'u mios' line: sysusers reads
the second field of `u name UID:GID` as a NAME LOOKUP via NSS (or as an
existing numeric GID). It does NOT auto-create a group with the given GID.
Creating the group explicitly first is the canonical pattern used by every
other mios-* user in this directory (mios-virt, mios-guacamole, ...).

<!-- mios-src:0d5f4442af02 from usr/lib/sysusers.d/10-mios.conf:1-13 -->

