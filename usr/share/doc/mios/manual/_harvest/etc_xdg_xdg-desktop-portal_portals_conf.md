<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### MiOS default portal backend selection. xdg-desktop-portal...

MiOS default portal backend selection.

xdg-desktop-portal uses this file (alongside <desktop>-portals.conf)
to decide which backend implements each portal interface. With
XDG_CURRENT_DESKTOP=GNOME (set by /etc/profile.d/mios-wslg.sh), the
portal also reads gnome-portals.conf -- but that file is shipped by
xdg-desktop-portal-gnome and may not always exist. This file is the
fallback that guarantees a backend is selected even when
XDG_CURRENT_DESKTOP is unset (PAM-bypass logins on WSL2,
`wsl --user mios -- foo` invocations from Windows that skip
/etc/profile.d sourcing, etc).

`default=gnome` routes ALL portal interfaces (FileChooser,
Notification, Inhibit, Screenshot, ScreenCast, Settings, OpenURI,
etc.) to xdg-desktop-portal-gnome. The gnome backend is appropriate
for both the bare-metal MiOS GNOME session AND the WSLg dev VM
(Wayland surface routed through WSLg's compositor).

<!-- mios-src:b57058e53661 from etc/xdg/xdg-desktop-portal/portals.conf:4-20 -->
