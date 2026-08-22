<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes /usr/libexec/mios/role-apply to parse /etc/mios/role.conf and toggle system services based on the environment, specifically handling WSL-specific role gating during boot.
AI-related: /usr/libexec/mios/role-apply, /etc/mios/role.conf, network-online.target, local-fs.target, sysinit.target, multi-user.target

<!-- mios-src:a53fea381ce0 from usr/lib/systemd/system/mios-role.service:1-2 -->

