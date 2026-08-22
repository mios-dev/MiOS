<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures Windows Firewall and netsh portproxy rules to map physical NIC ports to local WSL containers, enabling LAN-wide access to MiOS services like Forge, Open-WebUI, and mios-llm-light.
AI-related: /usr/libexec/mios/Setup-MiOSLanPortProxy.ps1, usr/share/mios/windows/Setup-MiOSLanPortProxy.ps1
/usr/libexec/mios/Setup-MiOSLanPortProxy.ps1

Open the MiOS service ports on Windows' physical NIC so other LAN
devices (phone / tablet / laptop) can reach the dev VM's containers
at <Windows-host-IP>:NNNN. Adds Windows Firewall inbound allow rules
+ netsh portproxy 0.0.0.0:NNNN -> 127.0.0.1:NNNN entries (the
127.0.0.1 side bounces into WSL via .wslconfig's localhostForwarding).

MUST run elevated. The script self-checks and re-launches itself
via UAC if not already admin.

<!-- mios-src:1e1cd1fdb43d from usr/libexec/mios/Setup-MiOSLanPortProxy.ps1:1-12 -->

