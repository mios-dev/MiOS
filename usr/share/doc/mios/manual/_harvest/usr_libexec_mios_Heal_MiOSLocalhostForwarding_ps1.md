<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Purges stale netsh portproxy entries (0.0.0.0:N to 127.0.0.1:N) that cause Windows to intercept and blackhole local browser requests to MiOS services, restoring proper WSL2 localhost routing.
AI-related: /usr/libexec/mios/Heal-MiOSLocalhostForwarding.ps1
/usr/libexec/mios/Heal-MiOSLocalhostForwarding.ps1

Remove the stale `netsh interface portproxy v4tov4 0.0.0.0:N ->
127.0.0.1:N` entries left behind by an earlier version of
Setup-MiOSLanPortProxy.ps1. Those entries make Windows itself answer
`localhost:N` from the proxy listener (which loops to its own
127.0.0.1 where nothing runs), blackholing every browser tab the
operator opens to a MiOS service URL.

WSL2's built-in localhostForwarding=true in %USERPROFILE%\.wslconfig
is the right path for Windows-side localhost; LAN-side access from
phone/tablet needs a different connectaddress (the WSL VM IP,
resolved at proxy-add time -- handled by the rewritten
Setup-MiOSLanPortProxy.ps1).

MUST run elevated. Self-elevates via UAC if not already admin.
Operator-flagged "WEB SERVICES ARENT REACHABLE IN LOCAL
WINDOWS BROWSER AGAIN!!!!".

<!-- mios-src:8bb3d97e49e0 from usr/libexec/mios/Heal-MiOSLocalhostForwarding.ps1:1-20 -->

