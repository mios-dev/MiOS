<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Renders every [ports] entry from mios.toml into install.env as MIOS_PORT_* via miosd, resolved by absolute path.
AI-related: usr/share/mios/mios.toml, src/mios-rs/miosd/src/main.rs, automation/lib/globals.sh

<!-- mios-src:65e71b99004d from automation/35-render-ports.sh:1-4 -->

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Projects UPS settings from mios.toml [power.ups] SSOT into the NUT config directory via miosd, resolved by absolute path.
AI-related: usr/share/mios/mios.toml, src/mios-rs/miosd/src/main.rs, usr/lib/mios/log.sh

<!-- mios-src:209dd7ffb4b3 from automation/43-nut-render.sh:1-4 -->

### !/usr/bin/env bash AI-hint: Compiles native Rust workspace...

!/usr/bin/env bash
AI-hint: Compiles native Rust workspace crates (tools/native and src/mios-rs) and installs binaries into /usr/libexec/mios during image bake.
AI-related: tools/native/Cargo.toml, src/mios-rs/Cargo.toml, automation/85-bake-plan.sh, /usr/libexec/mios/

<!-- mios-src:2d59fc6e121c from automation/55-native-build.sh:1-3 -->

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Projects kernel arguments from mios.toml [kargs] SSOT into /usr/lib/bootc/kargs.d via miosd, resolved by absolute path.
AI-related: usr/share/mios/mios.toml, usr/lib/bootc/kargs.d, src/mios-rs/miosd/src/main.rs, usr/lib/mios/log.sh

<!-- mios-src:97f6869911f3 from automation/75-kargs-render.sh:1-4 -->

### !/usr/bin/env bash...

!/usr/bin/env bash
MIOS_INSTALLER_ROLE=fhs-overlay-installer
AI-hint: Installs the MiOS FHS overlay onto non-bootc Fedora hosts by syncing usr/, etc/, var/, and srv/ directories, materializing required users/groups, and configuring services.
AI-doc: usr/share/doc/mios/manual/automation.md

<!-- mios-src:cd1fa7c76643 from automation/install-fhs.sh:1-4 -->
