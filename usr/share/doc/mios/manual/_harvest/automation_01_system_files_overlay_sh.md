<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=universal AI-hint: Overlay...

!/bin/bash
MIOS_APPLY_CLASS=universal
AI-hint: Overlay script that maps the /ctx/ source directory onto the rootfs during build, specifically handling the /usr/local to /var/usrlocal symlink logic and syncing the system version file.
AI-related: /usr/share/mios/VERSION, /usr/libexec/mios/motd, /usr/libexec/mios/mios-dashboard.sh, /usr/share/mios/mios.toml, mios-dashboard, mios-infra, mios-bootstrap, wsl-init.service

<!-- mios-src:6ab528c3ee27 from automation/01-system-files-overlay.sh:1-4 -->

