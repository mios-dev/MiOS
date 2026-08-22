<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit file that manages the ttyd service to provide a browser-accessible bash shell via WebSockets, mapping a terminal session to the mios user's environment.
AI-related: /usr/libexec/mios/mios-ttyd-launch, /etc/mios/userenv.sh, mios-ttyd-launch, mios-ttyd-bash, network-online.target, multi-user.target, localhost:7681
/usr/lib/systemd/system/mios-ttyd-bash.service
Phase D.2 of the AgentOS roadmap: browser-accessible Linux
terminal. Operator hits http://localhost:7681 in any browser
and gets a bash session over a WebSocket pty.

Bound to 127.0.0.1 by default -- flip via [ttyd].bind in
mios.toml for LAN access (auth credentials enforced by
mios-ttyd-launch when bind != loopback).

<!-- mios-src:b5d6ee6cf9ea from usr/lib/systemd/system/mios-ttyd-bash.service:1-10 -->

