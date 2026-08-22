<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_tokenize (WS-A5 tokenizer seam). Pure stdlib, no server.py/DB/pytest. Verifies the heuristic backend reproduces the pipe's prior len//4 estimate EXACTLY (byte-for-byte parity for count_text/count_messages, so swapping the inline //4 is behaviour-preserving), truncate_to_tokens honours the token budget (and == the old [:N] char slice), and set_backend swaps the measurement while degrading safely.
AI-related: ./mios_tokenize.py
AI-functions: check, main

<!-- mios-src:3685f873d597 from usr/lib/mios/agent-pipe/test_mios_tokenize.py:1-4 -->

