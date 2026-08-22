<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_verity (refactor R6 extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the anti-fabrication invariants of the extracted POLISH/VERITY cluster: _strip_ungrounded_figures drops a $-price sentence whose number is ABSENT from the haystack while KEEPING a grounded one (and honours the >half-the-figures fail-safe by leaving the answer untouched); polish_response short-circuits to None on empty raw_text, and -- with every injected dep stubbed + httpx monkeypatched to a canned 200 + verity gated off (no hint_tools) -- passes a no-figure/no-contradiction draft through unchanged. Guards the extracted cluster + its configure() DI seam so a later move can't silently change fact-check behaviour.
AI-related: ./mios_verity.py
AI-functions: check, t_strip_figures, t_strip_failsafe, t_strip_unicode_sentence, t_abbr_from_ssot, t_polish_empty, t_polish_passthrough, t_clarify_empty, t_clarify_extracts_question, main

<!-- mios-src:7e895664fab1 from usr/lib/mios/agent-pipe/test_mios_verity.py:1-4 -->

