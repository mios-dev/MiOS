<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Resolves and exports MiOS environment variables (MIOS_*) by merging layered TOML configs and .env files to provide a unified configuration for CLI tools, agents, and the Hermes-Agent AI gateway.
AI-related: /usr/share/mios/mios.toml, /etc/mios/mios.toml, /etc/mios/env.d/, /etc/mios/install.env, /usr/lib/mios/userenv.sh, /usr/share/mios/tools/lib/userenv.sh, /etc/mios/env.d, /etc/mios/hermes/api.env, /usr/share/mios/ai, mios-env
AI-functions: _mios_source_if_readable
MIOS_AI_MODEL, and MIOS_AI_KEY are exported here so every OpenAI-API

<!-- mios-src:9a205840e43b from etc/profile.d/mios-env.sh:1-4 -->

