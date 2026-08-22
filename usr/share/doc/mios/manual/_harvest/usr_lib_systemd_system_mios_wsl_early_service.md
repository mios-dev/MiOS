<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Executes /usr/libexec/mios/wsl-early to perform critical WSL2 pre-sysinit fixes, including rshared root and mounting /dev/net/tun and /dev/fuse, enabling subsequent system sandboxing.
AI-related: /usr/libexec/mios/wsl-early, systemd-tmpfiles-setup-dev.service, systemd-remount-fs.service, sysinit.target, basic.target, shutdown.target

<!-- mios-src:c75f9b814fbb from usr/lib/systemd/system/mios-wsl-early.service:1-2 -->

