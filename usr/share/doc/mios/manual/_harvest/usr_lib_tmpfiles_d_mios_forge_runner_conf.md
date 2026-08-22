<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem permissions and ownership for the Forgejo Runner's persistent state directory (/srv/mios/forge-runner) and the build-output sentinel directory (/var/lib/mios/forge-runner) used by mios-bootc-switch.
AI-related: mios-bootc-switch, mios-forgejo-runner, mios-forgejo-runner.container
'MiOS' Forgejo Runner -- runtime state declarations.
Required because /var paths cannot be created at OCI build time
(Architectural Law 2: NO-MKDIR-IN-VAR). The runner runs as root
(documented Privileged=true exception, see mios-forgejo-runner.container
header), so ownership is root:root.

<!-- mios-src:f25ead394d7d from usr/lib/tmpfiles.d/mios-forge-runner.conf:1-7 -->

