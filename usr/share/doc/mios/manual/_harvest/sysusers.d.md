<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines system user/group IDs and permissions for the 'mios' login account, ensuring correct UID 1000 assignment and group memberships for hardware access, service integration, and cross-domain data access.
AI-doc: usr/share/doc/mios/manual/sysusers.d.md

<!-- mios-src:9e4303bfc2d6 from usr/lib/sysusers.d/10-mios.conf:1-2 -->

### AI-hint

AI-hint: Defines systemd-sysusers prerequisites to pre-create the 'cockpit' group for /var/lib/cockpit persistence, ensuring compatibility with tmpfiles.d entries in OCI build environments where RPM scriptlets may fail.
AI-doc: usr/share/doc/mios/manual/sysusers.d.md
cockpit -- referenced by /usr/lib/tmpfiles.d/mios-infra.conf:5-6
(/var/lib/cockpit + /var/lib/cockpit/motd.d). The cockpit RPM
expects this group to own /var/lib/cockpit so the daemon can persist
its state.

<!-- mios-src:b00db0d52371 from usr/lib/sysusers.d/30-mios-tmpfiles-prereq.conf:1-6 -->

### AI-hint

AI-hint: Defines static GIDs for video (39) and render (105) groups to ensure consistent GPU passthrough permissions across containerized environments. 'MiOS' v0.2.4 - pin Fedora static GIDs for container GPU passthrough.
AI-doc: usr/share/doc/mios/manual/sysusers.d.md

<!-- mios-src:8834432b71bd from usr/lib/sysusers.d/50-mios-gpu.conf:1-2 -->

### AI-hint

AI-hint: Defines static UID/GID mappings for MiOS system accounts (e.g., mios-virt) to ensure consistent ownership of system resources and persistent permissions across image rebuilds.
AI-doc: usr/share/doc/mios/manual/sysusers.d.md
'MiOS' service accounts (stable IDs in 800-899 range)

<!-- mios-src:6c8fe777999e from usr/lib/sysusers.d/50-mios.conf:1-3 -->
