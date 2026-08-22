<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares /etc/mios/theme (Law 2: NO-MKDIR-IN-VAR / no ad-hoc mkdir
 at build or run time -- every /var and /etc runtime-writable path this repo
 creates is declared here so systemd-tmpfiles owns creation + permissions).
 Populated by usr/libexec/mios/mios-sync-theme (theme.json + mios-theme.css),
 the CSS/QML-facing sibling of the existing /etc/mios/install.env bridge.

Type Path                Mode User Group Age Argument

<!-- mios-src:9ef2c60811ba from usr/lib/tmpfiles.d/mios-theme.conf:1-7 -->

