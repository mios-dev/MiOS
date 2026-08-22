<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes /usr/libexec/mios/verify-root.sh to validate the integrity of the root filesystem during early boot, gated by the presence of /run/ostree-booted.
AI-related: /usr/libexec/mios/verify-root.sh, greenboot-healthcheck.service, ostree-remount.service, basic.target, local-fs.target

<!-- mios-src:58a68cf678dc from usr/lib/systemd/system/mios-verify-root.service:1-2 -->

