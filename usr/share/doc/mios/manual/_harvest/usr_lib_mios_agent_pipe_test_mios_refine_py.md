<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_refine (refactor R5 REFINE-classifier extraction). Pure stdlib, no server.py/DB/network/pytest. Drives the configure() DI seam with stub deps (no-op logger, empty agent registry, a small verb catalog, a fake httpx whose AsyncClient.post returns a canned model body) and asserts: (1) _salvage_refine_dispatch recovers a one-verb dispatch from a RESCUE corpus -- prose with embedded JSON, a VERB(args) call in narration, key=value + bare-positional args, longest-name-first matching, and a pure-prose miss -> None; (2) refine_intent parses representative classifier envelopes (plain JSON, ```json-fenced, <think>-wrapped, and a narrated/salvaged prose reply) end-to-end into the intent/refined_text/web/news/local_state shape with strict-bool coercion. Guards the prompt-sensitive classifier so a later move can't silently change the salvage or envelope-parse contract.
AI-related: ./mios_refine.py, ./mios_jsonsalvage.py
AI-functions: check, _configure, t_salvage_corpus, t_refine_envelope, main

<!-- mios-src:ad8c846d3e06 from usr/lib/mios/agent-pipe/test_mios_refine.py:1-4 -->

