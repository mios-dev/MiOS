<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Executes the full MiOS system...

!/usr/bin/env bash
AI-hint: Executes the full MiOS system bootstrap to transform a bare Fedora host into a complete MiOS workstation by installing all core components, configuring FHS paths, and setting up the environment.
AI-related: packages.sh, /usr/share/mios/mios.toml, mios-dev, mios-stage-XXXXXX
AI-functions: log_info, log_ok, log_warn, log_err, log_phase, require_root, detect_host_kind, check_network, prompt_default, prompt_password, prompt_yesno, main

<!-- mios-src:4ebf3210e5a8 from automation/install-bootstrap.sh:1-4 -->

