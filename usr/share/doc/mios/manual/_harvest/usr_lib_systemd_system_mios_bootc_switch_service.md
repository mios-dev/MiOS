<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that triggers bootc switch via /usr/libexec/mios/bootc-switch-from-build.sh when a build sentinel in /var/lib/mios/forge-runner/last-build.txt is updated, automating the transition to a new image.
AI-related: /usr/libexec/mios/bootc-switch-from-build.sh, mios-bootc-switch, local-fs.target, multi-user.target
/usr/lib/systemd/system/mios-bootc-switch.service
Host-side counterpart of the Forgejo Runner build step.

Triggered by mios-bootc-switch.path watching
/var/lib/mios/forge-runner/last-build.txt for changes. Reads the sentinel
(timestamp + image ref), verifies the image exists in containers-storage,
and stages it via `bootc switch --transport containers-storage <ref>`.
Closes the build->switch half of the self-replication loop without
letting the runner container itself touch bootc.

<!-- mios-src:e6535e9cd807 from usr/lib/systemd/system/mios-bootc-switch.service:1-11 -->

