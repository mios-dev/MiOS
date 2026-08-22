<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines global environment variables for MiOS to unify UI consistency across GTK, Qt, Electron, and Flatpak apps, enforcing dark mode, Wayland protocols, and synchronized cursor/theme rendering.
AI-related: mios-theme
-- Cursor Theme (OS-wide: GDM, GNOME, XWayland, Flatpaks) -----------------
16px matches /etc/dconf/db/local.d/00-mios-theme.cursor-size and the
/var/lib/flatpak/overrides/* XCURSOR_SIZE so the cursor renders the
same size in every surface (host shell, flatpak, XWayland).

<!-- mios-src:178c7cb1ee86 from usr/lib/environment.d/50-mios.conf:1-6 -->

