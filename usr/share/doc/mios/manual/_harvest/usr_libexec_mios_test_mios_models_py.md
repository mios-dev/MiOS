<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Stdlib offline tests for the...

!/usr/bin/env python3
AI-hint: Stdlib offline tests for the FBM model plane (T-201). Covers the CLI (`mios models list` reads the LAYERED [ai].firstboot_models rather than globbing the filesystem, so a declared-but-missing model is visible; add/rm edit the USER overlay and never the vendor file; a duplicate add is refused) and the first-boot fetcher's sha256 gate, driven end-to-end through a curl stub: a payload matching the declared digest installs, a mismatching one is REJECTED and the part file discarded so nothing unverified lands under a name the lanes would load. Before this the fetcher printed "Verifying sha256" and renamed without hashing anything. No network, no real models. Run: python3 test_mios_models.py
AI-related: ./mios-models, ./mios-models-firstboot, usr/share/mios/mios.toml
AI-functions: run_cli, mk_fetcher, main

<!-- mios-src:6a689b38a186 from usr/libexec/mios/test_mios_models.py:1-4 -->

