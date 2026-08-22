<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures kernel arguments to force verbose systemd status and logging to the console, ensuring boot progress is visible during the boot process and preventing framebuffer hijacking by plymouth.
'MiOS' -- Force verbose boot output on console
Without this, plymouth steals the framebuffer and hides all systemd output.
In Hyper-V this means a black screen with no progress indication.

<!-- mios-src:2adfd3d68e57 from usr/lib/bootc/kargs.d/10-mios-verbose.toml:1-4 -->

