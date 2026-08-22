<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/sh AI-hint: Points the interactive opencode TUI/CLI...

!/bin/sh
AI-hint: Points the interactive opencode TUI/CLI at the MiOS local inference backend by exporting OPENCODE_CONFIG, so opencode resolves the MiOS provider (mios-llm-light, port key `llm_light`) + the mios-opencode model instead of prompting for a cloud login.
AI-related: /etc/mios/opencode/opencode.json, opencode, mios-opencode-gateway, mios-llm-light, usr/lib/mios/agents/opencode-gateway/server.py

<!-- mios-src:4d782bc4bf0a from etc/profile.d/mios-opencode.sh:1-3 -->

