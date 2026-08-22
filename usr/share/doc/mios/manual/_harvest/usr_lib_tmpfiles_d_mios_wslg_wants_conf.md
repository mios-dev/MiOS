<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures systemd user-level symlinks to ensure the mios-wsl-env-import and mios-wsl-graphical-session services are automatically activated for WSLg graphical sessions.
AI-related: mios-wsl-env-import, mios-wsl-graphical-session, mios-wslg-wants, mios-wsl-env-import.service, mios-wsl-graphical-session.service, graphical-session.target, default.target
/usr/lib/tmpfiles.d/mios-wslg-wants.conf

Materializes systemd user-level wants symlinks for the WSLg
graphical-session.target activator + env-import. Without these
symlinks the units are inert until `systemctl --user preset-all`
runs -- which doesn't fire automatically per user-bus startup,
so a fresh install would still see graphical-session.target
inactive even though the units exist on disk.

Both units have ConditionPathIsDirectory=/mnt/wslg, so they're
inert outside WSLg. Materializing the symlinks unconditionally
is therefore safe across every MiOS shape (bare-metal, Hyper-V,
QEMU, OCI, and WSLg).

'L+' = force-create a symlink (overwrites if a stale one exists
from a previous version of MiOS).

Path layout: user-systemd reads /etc/systemd/user/, so the
wants directory lives there. Symlinks point back to the unit
files in /usr/lib/systemd/user/ -- relative paths so the chain
survives `bootc switch` / chroot / container moves.

<!-- mios-src:5409384a07a3 from usr/lib/tmpfiles.d/mios-wslg-wants.conf:1-23 -->

