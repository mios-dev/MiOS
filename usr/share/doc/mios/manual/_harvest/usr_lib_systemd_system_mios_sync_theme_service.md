<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Oneshot that regenerates /etc/mios/theme/{theme.json,mios-theme.css}
from mios.toml via usr/libexec/mios/mios-sync-theme. Mirrors the existing
mios-forge-firstboot.service / mios-sync-env pattern: runs once at boot so
the bridge file exists before mios-agent-pipe.service (Portal),
hermes-dashboard.service, and Quickshell's Theme.qml try to read it, and is
safe to `systemctl start mios-sync-theme.service` by hand after editing
mios.toml [colors] instead of hand-editing CSS/QML hex codes.
AI-related: usr/libexec/mios/mios-sync-theme, usr/lib/tmpfiles.d/mios-theme.conf
usr/share/mios/quickshell/Theme.qml, usr/share/mios/branding/mios-theme.css

<!-- mios-src:4613445949ae from usr/lib/systemd/system/mios-sync-theme.service:1-9 -->

