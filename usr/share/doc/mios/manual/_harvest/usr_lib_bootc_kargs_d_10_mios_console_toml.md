<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures kernel arguments to disable plymouth, ensuring boot messages are visible on framebuffer and serial consoles in Hyper-V/QEMU environments.
AI-related: mios-verbose
'MiOS' v0.3.0: Disable plymouth (no-op on framebuffer/serial consoles)
Plymouth steals the framebuffer, making Hyper-V/QEMU/serial boot invisible.
Console output args are in 00-mios.toml + 10-mios-verbose.toml; this file only disables plymouth.

<!-- mios-src:5ba0526c5f15 from usr/lib/bootc/kargs.d/10-mios-console.toml:1-5 -->

