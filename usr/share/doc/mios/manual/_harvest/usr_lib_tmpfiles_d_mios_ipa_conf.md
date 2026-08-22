<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles permissions and ownership for the IPA client sysrestore directory to resolve configuration conflicts and ensure proper access for the mios-freeipa service.
AI-related: mios-freeipa
/var/lib/ipa-client/sysrestore is owned by mios-freeipa.conf (the
topical file). This file used to declare it with mode 0700; the
canonical entry is 0755 there. Removing the duplicate here silences
the systemd-tmpfiles "Duplicate line for path" warning at every boot.

<!-- mios-src:9352fc51e546 from usr/lib/tmpfiles.d/mios-ipa.conf:1-6 -->

