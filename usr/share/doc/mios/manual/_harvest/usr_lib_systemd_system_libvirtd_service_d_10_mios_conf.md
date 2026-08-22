<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures libvirtd.service to ensure it starts after the libvirtd.socket and extends the shutdown timeout to 120s to prevent race conditions with Cockpit and handle slow VM storage during teardown.
AI-related: libvirtd.service, libvirtd.socket
Prevent startup race condition between Cockpit and libvirt on ucore bases

<!-- mios-src:9a4c191ccf81 from usr/lib/systemd/system/libvirtd.service.d/10-mios.conf:1-3 -->

