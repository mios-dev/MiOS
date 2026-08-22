<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_a2a_principal (#60 WS-6 signed A2A delegation principal). Pure stdlib, no server.py/DB/pytest/network. Verifies text_digest determinism + SHA-256 correctness + input sensitivity + None/empty/int coercion, build_claims/build_metadata required keys+shapes+digest binding, and verify() round-trip: valid->True, tampered text->False(text_digest_mismatch BEFORE sig check), no-key/unsigned degrade->False(unsigned), absent block->None, bad signature->False. Injects fake sign_fn/verify_fn (no external Ed25519 key material).
AI-related: ./mios_a2a_principal.py
AI-functions: check, main

<!-- mios-src:943617de4433 from usr/lib/mios/agent-pipe/test_mios_a2a_principal.py:1-4 -->

