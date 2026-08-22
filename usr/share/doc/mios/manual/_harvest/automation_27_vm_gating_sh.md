<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash MIOS_APPLY_CLASS=universal AI-hint: Configures...

!/bin/bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures Hyper-V Enhanced Session support by enabling hv_sock, configuring gnome-remote-desktop for Wayland-native RDP via vsock, and gating services like nvidia-powerd and waydroid for VM environments.
AI-related: mios-container, mios-hyperv-enhanced, mios-grd-setup, mios-no-audit, polkit.service, cockpit.socket, mios-hyperv-enhanced.service, dbus-broker.service, systemd-machined.service, dev-binderfs.mount

<!-- mios-src:6162b1732f52 from automation/27-vm-gating.sh:1-4 -->

