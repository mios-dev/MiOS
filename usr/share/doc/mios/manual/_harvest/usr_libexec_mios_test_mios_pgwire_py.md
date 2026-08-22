<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for the v3 extended-query wire builders in mios-pg-query (WS-A3 parameterized --exec-json path). Pure stdlib, no socket/DB/pytest. Loads the hyphenated mios-pg-query script via SourceFileLoader (does NOT run main) and verifies exact byte framing of Sync/Execute/Parse/Bind (type byte + self-inclusive Int32 length, NUL-terminated strings, text format codes, NULL=-1 length), encode_param coercion, and parse_envelope single-vs-batch + malformed handling.
AI-related: ./mios-pg-query
AI-functions: check, _declared_len_ok, main

<!-- mios-src:ec9cd888b625 from usr/libexec/mios/test_mios_pgwire.py:1-4 -->

