<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Builds a verity-rooted Unified...

!/usr/bin/env bash
AI-hint: Builds a verity-rooted Unified Kernel Image (UKI) and configures fapolicyd in permissive mode based on mios.toml flags; use this to generate the hardened UKI artifact and carve-out rules for the WS-7 security profile.
AI-related: mios-ws7-permissive, mios-agent-codegen, mios-verity
AI-functions: _ws7_scalar, _ws7_is_true, ws7_install_fapolicyd_observe, ws7_build_verity_uki, main

<!-- mios-src:4f4814ea7fe4 from automation/lib/ws7-uki-fapolicyd-build.sh:1-4 -->

