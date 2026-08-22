<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd tmpfiles for Ceph orchestration, ensuring critical directories like /var/lib/ceph/crash/posted exist to prevent ceph-crash.service startup warnings and ensure proper storage path availability.
AI-related: ceph-crash.service
Required directories for Ceph orchestration.

Includes the crash collector subtree because the upstream
ceph-crash.service (shipped by the ceph RPM) walks /var/lib/ceph/
crash/ at startup and logs `directory /var/lib/ceph/crash/posted
does not exist; please create` on every boot when the path is
absent. ceph-crash starts on every shape that has the ceph package
(including WSL where no actual ceph cluster runs), so pre-creating
the dirs silences the warning without needing a per-shape gate.

<!-- mios-src:f49af4df72ea from usr/lib/tmpfiles.d/mios-ceph.conf:1-11 -->

