<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_crl (WS-A10 cert/token revocation list). Pure stdlib, no server.py/DB/pytest/network. Verifies the CRL class: revoke()->is_revoked True, restore()->False, ids() reflects the current sorted set, load() round-trips from list/tuple/set/dict-with-revoked/malformed (degrade-open to empty), merge() unions ids, __init__ normalization (str-coerce + strip + drop-empty + dedup), unknown-id negatives, and the whitespace/None/empty edge cases the verifier relies on.
AI-related: ./mios_crl.py
AI-functions: check, main

<!-- mios-src:68abe0f332ba from usr/lib/mios/agent-pipe/test_mios_crl.py:1-4 -->

