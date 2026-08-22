<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines static UID/GID mappings for MiOS system accounts (e.g., mios-virt) to ensure consistent ownership of system resources and persistent permissions across image rebuilds.
AI-related: mios-virt
'MiOS' v0.2.4 -- Static system user/group definitions
Prevents UID/GID drift across image rebuilds.
These override dynamic allocation so /var ownership stays stable.

Format: u USER UID GROUP GECOS HOME SHELL
        g GROUP GID

<!-- mios-src:1ce6a7376f37 from usr/lib/sysusers.d/50-mios.conf:1-8 -->

