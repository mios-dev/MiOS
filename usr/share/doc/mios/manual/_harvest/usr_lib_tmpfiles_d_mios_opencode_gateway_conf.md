<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles for the opencode-gateway service, ensuring the mios-ai user owns the runtime work directories and the configuration directory required for OpenAI gateway operations.
AI-related: /usr/share/mios/opencode/opencode.json, /etc/mios/opencode, mios-ai, mios-opencode-gateway, mios-opencode-gateway.service
/usr/lib/tmpfiles.d/mios-opencode-gateway.conf
'MiOS' opencode -> OpenAI /v1 gateway runtime directories.

mios-opencode-gateway.service runs as mios-ai with ProtectSystem=strict, so
its HOME + run cwd (the opencode scratch workdir) must pre-exist owned by
mios-ai. Mirrors [ai].opencode_gateway_workdir in mios.toml.

<!-- mios-src:f1c2bb40423b from usr/lib/tmpfiles.d/mios-opencode-gateway.conf:1-8 -->

