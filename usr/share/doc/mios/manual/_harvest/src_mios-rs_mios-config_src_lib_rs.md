<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Schema-generic configuration container. Owns stable fields...

Schema-generic configuration container. Owns stable fields directly
(`meta`, `identity`, `build`) while storing all dynamic/operator-defined
sections generically in `raw` to prevent recompilation on mios.toml schema changes.

<!-- mios-src:62e97279e9f1 from src/mios-rs/mios-config/src/lib.rs:102-104 -->
