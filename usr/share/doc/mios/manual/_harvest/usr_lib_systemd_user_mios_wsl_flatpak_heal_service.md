<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: User-level systemd unit that executes a script to restart stalled flatpak portal services in WSL2g environments to prevent sandbox-credential failures during application launches.
AI-related: /usr/libexec/mios/mios-wsl-flatpak-heal, mios-wsl-flatpak-heal, portal.service, mios-wsl-flatpak-heal.timer, graphical-session.target
/usr/lib/systemd/user/mios-wsl-flatpak-heal.service

Phase E.2 of the AgentOS roadmap: keep WSL2g flatpak portal
stack warm so flatpak launches don't die at sandbox-credential
bootstrap. Operator-flagged 2026-05-18 root cause: flatpak-
portal.service idle-times out (~10-18min) without dbus auto-
activation re-firing it; every subsequent flatpak fails.

Runs as a USER systemd unit (the portals are per-user). Paired
with mios-wsl-flatpak-heal.timer for a 5-min cadence, and can
also be triggered explicitly via `systemctl --user start
mios-wsl-flatpak-heal.service`.

Idempotent: the heal script no-ops when services are already
active.

<!-- mios-src:23fe1cebd1d6 from usr/lib/systemd/user/mios-wsl-flatpak-heal.service:1-17 -->

