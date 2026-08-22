<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes mios-freeipa-enroll.sh to perform zero-touch FreeIPA enrollment for WSL and non-containerized environments, triggered only if /etc/mios/ipa-enroll.env exists and /etc/ipa/default.conf is missing.
AI-related: /etc/mios/ipa-enroll.env, /usr/libexec/mios/mios-freeipa-enroll.sh, mios-freeipa-enroll, network-online.target, multi-user.target

<!-- mios-src:fb809dc60511 from usr/lib/systemd/system/mios-freeipa-enroll.service:1-2 -->

