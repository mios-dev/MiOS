<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Parses layered TOML...

!/usr/bin/env bash
AI-hint: Parses layered TOML configuration files (vendor, host, and user) to export unified MIOS_ environment variables for identity, locale, network, AI, and image build settings used by all system tools and scripts.
AI-related: ./tools/lib/userenv.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/env.defaults, /usr/lib/mios/mios.d, mios-bootstrap, mios-colors, mios-opencode-gateway, mios-llm-heavy-alt, mios-llm-heavy
AI-functions: _mios_load_unified, _mios_legacy_get
MIOS_* environment variables. Sourced by Justfile, /etc/profile.d, every script.

<!-- mios-src:36b90430c33f from usr/lib/mios/userenv.sh:1-5 -->

