<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-sysusers prerequisites to pre-create the 'cockpit' group for /var/lib/cockpit persistence, ensuring compatibility with tmpfiles.d entries in OCI build environments where RPM scriptlets may fail.
AI-related: mios-infra
'MiOS' tmpfiles.d prerequisite users/groups.

Pre-create users/groups that MiOS-owned tmpfiles.d entries reference
but that aren't declared by any sysusers.d file (typically because the
upstream RPM creates them via a %pre scriptlet -- 'groupadd -r ...' --
that doesn't reliably fire in OCI build contexts). At runtime
systemd-sysusers runs before systemd-tmpfiles, so anything declared
here is in /etc/group by the time tmpfiles entries are processed.

Auto-allocate ('-') keeps the GID in the system range. If the upstream
RPM later wants to create the group with a specific GID, the
'getent group' check at the top of its scriptlet sees our entry,
treats it as already-present, and skips -- our pre-creation is a
no-op that the RPM accepts.

<!-- mios-src:c678942e314d from usr/lib/sysusers.d/30-mios-tmpfiles-prereq.conf:1-16 -->

