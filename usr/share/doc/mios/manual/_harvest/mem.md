<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Automated tmpfs...

!/usr/bin/env python3
AI-hint: Automated tmpfs spill-to-NVMe manager monitoring Linux PSI (/proc/pressure/memory) and migrating temporary data with LRU eviction.
AI-related: usr/lib/systemd/system/mios-tmpfs-spill.service, usr/lib/systemd/system/mios-tmpfs-spill.timer, tests/test-tmpfs-spill.py
AI-functions: read_memory_pressure_psi, get_available_memory_ratio, scan_spillable_files, execute_spill_file, enforce_spill_quota_lru, unspill_files, main

<!-- mios-src:8fa9a888d30f from usr/libexec/mios/mem/mios-tmpfs-spill:1-4 -->
