<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem paths, permissions, and ownership for the Forgejo service (SQLite DB, logs, and config overrides) to ensure correct runtime state and access for the mios-forge user.
AI-related: /etc/mios/forge, mios-forge, mios-services
'MiOS' Forge (Forgejo) -- runtime state declarations.
Required because /var paths cannot be created at OCI build time
(Architectural Law 2: NO-MKDIR-IN-VAR). Ownership matches the
mios-forge user declared in usr/lib/sysusers.d/50-mios-services.conf
at UID/GID 816. systemd-sysusers runs before systemd-tmpfiles at boot,
so the mios-forge user resolves cleanly here.

<!-- mios-src:2cb44453a833 from usr/lib/tmpfiles.d/mios-forge.conf:1-8 -->

