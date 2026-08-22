<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Default configuration for aichat/aichat-ng that redirects OpenAI-compatible requests to the local Agent-Pipe Quadlet at http://localhost:8640/v1, ensuring seamless local LLM integration for all users.
AI-related: /etc/mios/profile.toml, mios-ai, mios-ai.container, localhost:8640
~/.config/aichat/config.yaml -- 'MiOS' AIChat / AIChat-NG default config.

Architectural Law 5 (UNIFIED-AI-REDIRECTS): every OpenAI-API-shaped
client on a 'MiOS' system targets http://localhost:8640/v1 by default.
This file is seeded into every uid >= 1000 home from /etc/skel/ at
install time so 'aichat' and 'aichat-ng' resolve the local Agent-Pipe
Quadlet (mios-agent-pipe) without any per-user setup.

Spec for this file's schema:
  https://github.com/sigoden/aichat/blob/main/config.example.yaml

Override per-user by editing this file in $HOME, or system-wide by
editing /etc/mios/profile.toml's [ai] section -- the bootstrap layer
regenerates this from profile.toml on every install.

<!-- mios-src:bc84cb791e37 from etc/skel/.config/aichat/config.yaml:1-16 -->

