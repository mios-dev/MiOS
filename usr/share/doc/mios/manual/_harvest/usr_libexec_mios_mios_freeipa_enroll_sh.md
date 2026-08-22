<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Bash oneshot run by...

!/usr/bin/env bash
AI-hint: Bash oneshot run by mios-freeipa-enroll.service that joins the host to a FreeIPA domain via ipa-client-install; gated on /etc/mios/ipa-enroll.env existing (operator opt-in) and /etc/ipa/default.conf absent (not already enrolled).
AI-related: /usr/lib/mios/paths.sh, /etc/mios/ipa-enroll.env, mios-freeipa-enroll, mios-freeipa-enroll.service
AI-functions: _log

<!-- mios-src:83f5630c4673 from usr/libexec/mios/mios-freeipa-enroll.sh:1-4 -->

