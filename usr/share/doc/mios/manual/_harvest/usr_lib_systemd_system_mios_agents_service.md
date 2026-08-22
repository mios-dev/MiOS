<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Runs the mios-agents A2O super-container (code-server IDE + tmux war room + Claude CLI + agy/Gemini + the mios-a2o muxer) as a systemd-managed container. ExecStartPre builds the local image if absent; ExecStart runs it every boot on the code-server port MIOS_PORT_CODE_SERVER (mios-agents REPLACES the retired mios-code-server -- one IDE, no duplicate service). Persistent /home/coder (agy/claude logins) lives in /var/lib/mios/agents; the deployed root / is the workspace at /mnt/mios-root, so agents develop MiOS from within itself.
AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, /usr/libexec/mios/mios-agents-firstboot.sh, /etc/mios/install.env, /var/lib/mios/agents, mios-code-server.service, mios-agents-firstboot
/usr/lib/systemd/system/mios-agents.service

<!-- mios-src:833bb32cbeef from usr/lib/systemd/system/mios-agents.service:1-3 -->

