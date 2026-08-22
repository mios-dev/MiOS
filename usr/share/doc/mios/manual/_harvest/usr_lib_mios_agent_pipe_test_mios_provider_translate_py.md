<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_provider_translate (refactor WS R2 leaf extraction). Pure stdlib, no server.py/DB/pytest. Pins the OpenAI<->Anthropic/Gemini wire-format invariants that make alternative-provider endpoints drop-in: schema scrub drops $ref/$schema/additionalProperties (both) and relocates Gemini-rejected keywords (format/min*/max*/pattern) into description + forces array items.type; OpenAI tool arguments (JSON STRING) round-trip to Anthropic input / Gemini args OBJECTS and back to a JSON STRING; system messages fold to the top-level system param; assistant.tool_calls -> tool_use/functionCall and role:tool -> tool_result/functionResponse with id correlation. Guards the extracted leaf so a later move/refactor can't silently change provider wire shapes.
AI-related: ./mios_provider_translate.py
AI-functions: check, t_scrub, t_tools, t_args_obj, t_msgs_anthropic, t_resp_anthropic, t_msgs_gemini, t_resp_gemini, main

<!-- mios-src:884d5191c640 from usr/lib/mios/agent-pipe/test_mios_provider_translate.py:1-4 -->

