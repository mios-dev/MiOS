<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines core kernel boot arguments for MiOS, including IOMMU settings, Nouveau driver blacklisting, and serial console configurations for x86_64 systems.
AI-related: systemd.mount
'MiOS' v0.3.0 -- Core kernel boot arguments
bootc kargs.d (v1.13+). Format: bare kargs = [...] ONLY.
NO [kargs] table headers. NO delete/append keys.

<!-- mios-src:0eee69cb5685 from usr/lib/bootc/kargs.d/00-mios.toml:1-5 -->

