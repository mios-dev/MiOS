<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit for the Hermes gateway -- the ONLY unit in the tree running `hermes gateway run`. A real agent with its OWN native browser/CDP/terminal/skills tool loop and its OWN inference on the heavy lane (port key `vllm`, mios-heavy). Binds the port key `hermes`; its HERMES_HOME is private so no other instance can contend its pid/lock/state.
AI-related: /usr/lib/mios/agents/.venv/bin/hermes, /var/lib/mios/hermes-worker, /var/lib/mios/hermes-worker/config.yaml, /etc/mios/hermes/api.env, mios-hermes-browser-worker.service, mios-llm-heavy.service, mios-llm-light.service, usr/share/mios/mios.toml

<!-- mios-src:0febf28bd7f6 from usr/lib/systemd/system/hermes-worker.service:1-2 -->

