<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem permissions and directory structures for FreeIPA, certmonger, and SSSD components to ensure proper runtime access and security for identity management.
AI-related: mios-domain, mios-infra
'MiOS' -- FreeIPA/SSSD runtime directory skeletons.
ipa-client and certmonger expect these dirs at runtime.
On immutable images, rpm postinst can't create them, so tmpfiles does it.
bz 2332433: /var/lib/ipa-client/sysrestore/ missing causes ipa-client-install to fail.

<!-- mios-src:28f20d0d65c6 from usr/lib/tmpfiles.d/mios-freeipa.conf:1-6 -->

