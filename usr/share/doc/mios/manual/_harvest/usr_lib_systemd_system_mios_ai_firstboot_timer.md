<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Timer that re-triggers mios-ai-firstboot.service on a cadence until the .ai-firstboot-done sentinel exists, replacing the unit's former Restart=on-failure retry storm so a partial (network-less) AI provision degrades open instead of crash-looping.
AI-related: /usr/libexec/mios/mios-ai-firstboot, mios-ai-firstboot.service, /var/lib/mios/.ai-firstboot-done

<!-- mios-src:0675db6f7f5a from usr/lib/systemd/system/mios-ai-firstboot.timer:1-2 -->

