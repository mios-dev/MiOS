<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: NetworkManager offline...

!/usr/bin/env python3
AI-hint: NetworkManager offline connection keyfile pre-seeder enforcing strict 0600 permissions
AI-related: tests/test-nm-preseed.py, usr/share/mios/mios.toml, usr/libexec/mios/ux/firstboot_wizard.py
AI-functions: NetworkManagerPreseedEngine, ConnectionProfile, generate_keyfile

<!-- mios-src:cc49bb39f9bd from usr/libexec/mios/net/nm_preseed.py:1-4 -->

### !/usr/bin/env python3 AI-hint: PTP IEEE 1588 hardware...

!/usr/bin/env python3
AI-hint: PTP IEEE 1588 hardware timestamping and Chrony NTS smooth clock synchronization daemon.
AI-related: tests/test-ptp-time.py, usr/lib/systemd/system/ptp4l.service, automation/42-chrony-render.sh
AI-functions: PTPCapabilityProbe, PTPConfigGenerator, PTPStatusMonitor, PTPTimeSyncDaemon, main

<!-- mios-src:514cb6a3bd83 from usr/libexec/mios/net/ptp_time_sync.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Declarative nftables VPN...

!/usr/bin/env python3
AI-hint: Declarative nftables VPN kill-switch and fwmark split-tunnel manager for MiOS.
Enforces strict default-drop on non-VPN public WAN traffic while preserving local mesh connectivity via fwmark 0x100.
AI-doc: usr/share/doc/mios/manual/ch28-dynamic-network-and-firewall-management.md

<!-- mios-src:a22483c494d4 from usr/libexec/mios/net/vpn_killswitch.py:1-4 -->
