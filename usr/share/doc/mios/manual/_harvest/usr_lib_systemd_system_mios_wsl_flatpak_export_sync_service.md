<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Syncs flatpak .desktop files and icons from /var/lib/flatpak/exports/share to /usr/share to ensure WSL Start Menu visibility, triggered after mios-wsl-early.service and gated by the /run/mios-is-wsl marker.
AI-related: /usr/libexec/mios/mios-wsl-flatpak-export-sync.sh, mios-wsl-early, mios-is-wsl, mios-wsl-flatpak-export-sync, mios-wsl-early.service, multi-user.target, default.target

<!-- mios-src:54fbc0be5c19 from usr/lib/systemd/system/mios-wsl-flatpak-export-sync.service:1-2 -->

