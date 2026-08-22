<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Runtime port allocator -- derives every [ports] value from the [ports.categories] schema (base + index*stride) after layer merging, so operator/OEM overrides re-derive live. Mirrors mios_toml.derive_ports.
AI-related: usr/lib/mios/mios_toml.py, usr/share/mios/mios.toml, tools/render-ports.py

<!-- mios-src:e17cfe6511d1 from tools/native/mios-resolver/src/ports.rs:1-2 -->

