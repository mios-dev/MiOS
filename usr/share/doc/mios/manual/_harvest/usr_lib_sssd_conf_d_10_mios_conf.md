<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Provides base SSSD nss/pam defaults for MiOS, specifically filtering root users/groups and setting reconnection retries, serving as the foundational configuration layer before realm-specific overrides.
AI-related: /usr/libexec/mios/mios-freeipa-enroll.sh, /etc/mios/ipa-enroll.env, mios-freeipa-enroll
'MiOS' SSSD base configuration.
This file provides nss/pam defaults only.
Realm-specific settings are written by ipa-client-install (invoked by
/usr/libexec/mios/mios-freeipa-enroll.sh on first boot when
/etc/mios/ipa-enroll.env is present).

NOTE: sssd.conf itself is written by ipa-client-install.
This drop-in is merged by libini and honoured since libini v0.2.0.
Files in conf.d/ must be root:root 0600.

<!-- mios-src:d0d81fb8d5d6 from usr/lib/sssd/conf.d/10-mios.conf:1-11 -->

