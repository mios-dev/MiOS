<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure cross-provider wire-format adapter extracted from server.py (refactor WS R2 leaf wave). MiOS's internal contract is OpenAI Chat Completions; an agent binding may declare api='anthropic'|'gemini', and this layer normalises tools, messages, and responses BOTH directions so alternative-provider endpoints are drop-in ("entire stacks to OpenAI standards for UNIVERSAL MODEL compatibility"). Invariants: OpenAI `arguments` is a JSON STRING while Anthropic `input` / Gemini `args` are OBJECTS; call-id correlation; results are messages; JSON-Schema scrub (drop top-level $ref/$schema/additionalProperties, force Gemini array items.type, relocate provider-rejected keywords into description). Self-contained pure functions -- only dependency is mios_jsonsalvage.loads_lenient (lenient JSON parse of model-emitted argument strings) + stdlib json. server.py re-imports every name under its original _-prefixed alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_jsonsalvage.py, ./mios_interop.py, ./test_mios_provider_translate.py
AI-functions: scrub_schema, oai_tools_to_anthropic, oai_tools_to_gemini, args_obj, oai_msgs_to_anthropic, anthropic_resp_to_oai, oai_msgs_to_gemini, gemini_resp_to_oai

<!-- mios-src:05b13bc69ace from usr/lib/mios/agent-pipe/mios_pipe/routing/provider_translate.py:1-3 -->

