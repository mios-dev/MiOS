<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Provides shell functions to parse and...

!/bin/bash
AI-hint: Provides shell functions to parse and extract package lists from mios.toml configuration files, supporting layered overrides and specific installation modes (strict/optional) for automated package management.
AI-related: automation/lib/packages.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/configurator/mios.html, mios-bootstrap
AI-functions: _resolve_mios_toml, get_packages_from_toml, get_packages, get_packages_strict, _is_section_enabled, install_packages, install_packages_strict, install_packages_optional

<!-- mios-src:e0f2122b5016 from automation/lib/packages.sh:1-4 -->

