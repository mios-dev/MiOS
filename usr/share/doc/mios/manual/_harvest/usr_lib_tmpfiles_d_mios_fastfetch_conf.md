<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the system-wide fastfetch configuration by symlinking /etc/fastfetch/config.jsonc to /usr/share/mios/fastfetch/config.jsonc to ensure the MiOS branding persists across bootc redeploys.
AI-related: /usr/share/mios/fastfetch/config.jsonc, mios-fastfetch
/usr/lib/tmpfiles.d/mios-fastfetch.conf
Make the MiOS fastfetch config the system default. Bare `fastfetch`
invocations (no -c flag) fall back to /etc/fastfetch/config.jsonc
(or ~/.config/fastfetch/config.jsonc); without this symlink the
operator sees the upstream Fedora ASCII logo instead of MiOS.

L+ recreates the symlink on every boot so manual /etc edits don't
persist past a bootc redeploy. The MiOS fastfetch surface
(logo position:top, services modules) lives at
/usr/share/mios/fastfetch/config.jsonc per Architectural Law 1
(USR-OVER-ETC -- static config in /usr/lib or /usr/share, /etc/
is admin-override only).

<!-- mios-src:39c2e5839784 from usr/lib/tmpfiles.d/mios-fastfetch.conf:1-14 -->

