<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines static GIDs for video (39) and render (105) groups to ensure consistent GPU passthrough permissions across containerized environments.
'MiOS' v0.2.4 - pin Fedora static GIDs for container GPU passthrough.
setup package ships these as static but render is still listed as
"soft-static" upstream -- pin explicitly to avoid drift.
Format: Type Name ID GECOS HomeDir Shell

<!-- mios-src:991cc2bbd288 from usr/lib/sysusers.d/50-mios-gpu.conf:1-5 -->

