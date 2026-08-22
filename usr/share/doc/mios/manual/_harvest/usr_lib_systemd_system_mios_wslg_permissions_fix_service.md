<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: A systemd oneshot service that enforces 0700 permissions on /mnt/wslg/runtime-dir to enable Wayland VAIL mode and replaces the /tmp/.X11-unix symlink with a physical directory to ensure Flatpak/bwrap compatibility.
AI-related: /usr/libexec/mios/mios-flatpak-icon-sanitize, mios-flatpak-icon-sanitize, mios-dev, systemd-tmpfiles-setup.service, wslg-x11.service, wslg-wayland.service, multi-user.target, default.target

<!-- mios-src:60f341b676cc from usr/lib/systemd/system/mios-wslg-permissions-fix.service:1-2 -->

