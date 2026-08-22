<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for mios_kvfork to verify KV-cache fork primitives, ensuring filename sanitization, length capping, and fork validation logic match the server's expected contract.
AI-related: mios_kvfork, mios-kv, mios-kv-abc, mios-kv-default, mios-kv-a_b_c, mios-kv-parent, mios-kv-child
AI-functions: _check, _reference_kv_filename, t_filename_matches_server, t_validate, t_plan, t_outcome, t_parse_bool, t_clamp, main

<!-- mios-src:4a594c7adc77 from usr/lib/mios/agent-pipe/test_mios_kvfork.py:1-3 -->

