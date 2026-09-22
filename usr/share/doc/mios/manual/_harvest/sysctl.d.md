<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: sysctl for OverlayFS stacking depth, inotify limits and neighbour table sizes.
--- systemd-sysext / OverlayFS Stacking --------------------------------------
Note: Upstream hard limit is 2. MiOS-OS uses OSTree + verity.
Repackaging multiple small .sysext images into a single large one is
handled via the 'mios-sysext-pack' helper (Planned).

<!-- mios-src:8d5582898694 from usr/lib/sysctl.d/90-mios-overlayfs.conf:1-5 -->
