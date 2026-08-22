<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Provides helper functions for...

!/usr/bin/env bash
AI-hint: Provides helper functions for identifying, registering, and masking sensitive credentials (like GH_TOKEN or MIOS_PASSWORD) in logs and stdout, and provides a secure scurl wrapper for credential-aware requests.
AI-functions: add_mask, register_common_masks, mask_filter, ensure_cred, scurl

<!-- mios-src:fdb6be2b4488 from automation/lib/masking.sh:1-3 -->

