<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: tmpfiles.d that creates the /var/lib/mios parent state dir (0755 root:root); the grd/gnome-remote-desktop var dir is intentionally NOT declared here (upstream's grd tmpfiles owns /var/lib/gnome-remote-desktop).
/var/lib/gnome-remote-desktop is created by upstream's gnome-remote-desktop
tmpfiles.d (also at 0770 grd:grd), so we don't re-declare it here.

<!-- mios-src:b4740b9df8c4 from usr/lib/tmpfiles.d/mios-grd.conf:1-3 -->

