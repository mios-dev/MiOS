<!-- AI-hint: Manual pages distilled from the source comments of kargs.d, sanitized, each passage anchored to the comment it came from. -->

# kargs.d

### PROMOTION-ONLY KARGS (commented; DO NOT uncomment until the...

---- PROMOTION-ONLY KARGS (commented; DO NOT uncomment until the documented
---- permissive->enforce procedure has passed on THIS image + a rollback is
---- staged). Uncommenting any of these on an unproven whitelist / unsigned
---- UKI can BRICK BOOT.

Enforce fapolicyd execution whitelist (the brick-capable flip):
  "fapolicyd.permissive=0",

Require a signed UKI / full kernel lockdown (only after UKI is signed with
an enrolled MOK; 30-security.toml currently sets lockdown=integrity which is
the NVIDIA-safe level -- raising to confidentiality can block module load):
  "lockdown=confidentiality",

Enforce fs-verity on the root composefs (tamper-evident -> tamper-PROOF;
only after a verity-rooted UKI build is confirmed bootable + rollback-tested).
MUST be the MERGED form -- a bare `rootflags=verity.require` OVERRIDES
15-rootflags.toml's `rootflags=discard=async,noatime` (duplicate key on the
cmdline, last wins -> silently drops discard/noatime):
  "rootflags=discard=async,noatime,verity.require",

<!-- mios-src:26ab3272add0 from usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml:35-53 -->
