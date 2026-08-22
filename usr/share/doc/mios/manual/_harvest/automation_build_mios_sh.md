<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: This script is the primary installation...

!/bin/bash
AI-hint: This script is the primary installation and ignition tool for MiOS; an agent uses it to clone the MiOS repository and merge its components into the Fedora Server root filesystem.
AI-related: /usr/share/mios/mios.toml.example., /etc/mios/install.env, mios-ignition, localhost:8080
AI-functions: log, log_warn, log_error, log_info, show_banner, collect_user_config, check_prerequisites, install_dependencies, fetch_mios_repo, queue_environment_files, merge_mios_structure, create_user_account

<!-- mios-src:04791f399af5 from automation/build-mios.sh:1-4 -->

