<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Ensures the cockpit.socket unit waits for libvirtd.socket to be active, preventing "Failed to connect to libvirt" errors in the Machines panel during early boot.
AI-related: cockpit.socket, libvirtd.socket
Prevent cockpit.socket from activating before libvirtd.socket is ready.
Without this, opening the Machines panel immediately after boot races
against libvirtd startup and produces "Failed to connect to libvirt" errors.

<!-- mios-src:787e4904c286 from usr/lib/systemd/system/cockpit.socket.d/10-mios.conf:1-5 -->

