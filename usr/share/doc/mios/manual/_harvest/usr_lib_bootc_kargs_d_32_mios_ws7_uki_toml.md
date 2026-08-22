<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines boot-time kernel arguments for the WS-7 immutable-host hardening; currently a no-op drop-in to prevent boot-bricking while providing a location for future fapolicyd enforcement and lockdown flags.
AI-related: mios-ws7-uki, mios-ws7-permissive
32-mios-ws7-uki.toml
----------------------------------------------------------------------------
WS-7 (AIOS immutable-host hardening) -- kargs drop-in for the verity-rooted
UKI + fapolicyd observe rollout.

ABSOLUTELY CRITICAL: this file ships as a NO-OP by default -- it carries NO
active kargs. (Correction an earlier version set
`fapolicyd.permissive=1` here claiming it forced observe mode "at the kernel
level" -- that is FALSE. fapolicyd reads `permissive` from its CONFIG
(/etc/fapolicyd/fapolicyd.conf or --permissive), NOT /proc/cmdline; the kernel
ignores the unknown arg. The REAL observe switch is `permissive = 1` in
mios-ws7-permissive.conf, installed by the gated build step.) Every brick-
capable karg (enforce mode, signature-required UKI / lockdown=confidentiality,
rootflags=verity.require) is left COMMENTED so this drop-in cannot brick boot.
Promotion to enforce is a deliberate, documented, rollback-tested operator
step -- see usr/share/doc/mios/concepts/ws7-uki-fapolicyd.md.

bootc kargs.d format: flat top-level `kargs = [...]` array only (Law/lint).
Files are processed lexicographically; 32- lands just after 31-secureblue.

verity note: the verity-rooted UKI itself is produced by the gated build step
automation/lib/ws7-uki-fapolicyd-build.sh (ukify build with the composefs
fs-verity digest measured into the UKI). composefs verity is already on via
mios.toml [security].composefs_mode="verity" (automation/77-composefs-verity.sh).
This kargs file only carries the boot-time POSTURE switches, not the image.

<!-- mios-src:09ebf2498a20 from usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml:1-27 -->

