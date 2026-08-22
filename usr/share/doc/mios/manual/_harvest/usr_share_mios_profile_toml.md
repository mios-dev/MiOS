<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Immutable vendor-default configuration for MiOS system identity, locale, network, and AI agent parameters (Hermes-Agent) used as the base layer for the three-tier profile resolution.
AI-related: /usr/share/mios/profile.toml, /etc/mios/profile.toml, /usr/share/mios/ai/v1/mcp.json, mios-bootstrap, mios-dev, mios-ceph, mios-k3s, mios-forge, mios-cockpit-link, mios-hermes
/usr/share/mios/profile.toml -- 'MiOS' Profile Defaults (vendor-immutable)

This file ships in mios.git and is baked into every image. It is the
read-only DEFAULT layer of the three-layer profile resolution:

  1. ~/.config/mios/profile.toml     per-user override   (highest)
  2. /etc/mios/profile.toml          host/admin override (bootstrap user-edit)
  3. /usr/share/mios/profile.toml    vendor defaults     (THIS FILE -- lowest)

At install time, mios-bootstrap.git ships /etc/mios/profile.toml as the
user-edit copy with the same field shape; bootstrap install.sh reads
defaults here, overlays the user values from /etc/mios/profile.toml,
and stages a copy to each Linux user's ~/.config/mios/profile.toml from
/etc/skel/.config/mios/profile.toml.

Edit this file ONLY to change the vendor default for every fresh install.
For per-host or per-user overrides, edit the respective layer above.

Format: TOML 1.0 -- https://toml.io/en/v1.0.0.

<!-- mios-src:1bfce1026e22 from usr/share/mios/profile.toml:1-21 -->

