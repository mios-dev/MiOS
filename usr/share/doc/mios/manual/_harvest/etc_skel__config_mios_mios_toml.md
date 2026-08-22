<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Per-user configuration file for MiOS that overrides system-wide defaults for identity, locale, AI endpoints, and desktop preferences, serving as the highest-priority configuration layer for user-specific environment settings.
AI-related: /usr/share/mios/mios.toml, /etc/mios/mios.toml, /etc/mios/mios.toml., localhost:8080
~/.config/mios/mios.toml -- Per-user 'MiOS' profile (highest-priority layer).

This is the per-user copy of the unified user-config dotfile. The full
schema (every field, every default) is in two places you can copy from:
  - /usr/share/mios/mios.toml          vendor defaults (image-baked)
  - /etc/mios/mios.toml                host overlay (bootstrap-staged)
Higher layers overlay lower layers field-by-field, so this file only
needs the values that differ from /etc/mios/mios.toml.

Seeded from /etc/mios/mios.toml on first login by 'mios init-user-space'.
'mios reinit-user-space' overwrites this file from the system profile,
so back up your customizations first.

<!-- mios-src:f39bc499fa73 from etc/skel/.config/mios/mios.toml:1-14 -->

