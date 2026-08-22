<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Structural governor-coverage...

!/usr/bin/env python3
AI-hint: Structural governor-coverage gate for mios-daemon: asserts every autonomous *_loop consults the host-pressure gate, that the SSOT [daemon] and [budget] knobs all have real consumers (no declared-and-dead safety knob), and that the agent-pipe budget fallbacks match the SSOT values rather than drifting more permissive.
AI-related: usr/libexec/mios/mios-daemon, usr/share/mios/mios.toml, usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py, automation/98-drift-checks.sh

<!-- mios-src:ce4227fb8222 from tools/check-daemon-governor.py:1-3 -->

