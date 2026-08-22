<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=universal AI-hint: Installs...

!/bin/bash
MIOS_APPLY_CLASS=universal
AI-hint: Installs operator-selected Flatpaks into the system image during the build process to ensure the final deployment (ISO, VHDX, etc.) contains the user's chosen desktop applications without requiring a network connection on first boot.
AI-related: 57-gnome.sh, /usr/share/mios/flatpak-list, /usr/share/mios/vendored/, /usr/lib/mios/state, /usr/lib/mios/state/flatpak-bake.env, mios-flatpak-install

<!-- mios-src:eef939ff9fa7 from automation/61-flatpak-bake.sh:1-4 -->

