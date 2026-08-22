<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles directory permissions and ownership for MiOS core components, ensuring the mios-ai user has proper access to the /var/lib/mios/ tree for model state, MCP context, and coderun scratch space.
AI-related: /usr/share/mios/memory/v1.jsonl, mios-ai, mios-hermes, mios-mcp, mios-ai-only, mios-coderun, mios-code-server, mios-agent-pipe, mios-open-webui, mios-user
/usr/lib/tmpfiles.d/mios.conf
Declares 'MiOS' state directories for systemd-tmpfiles. Created at boot.

<!-- mios-src:6ba738362cc3 from usr/lib/tmpfiles.d/mios.conf:1-4 -->

