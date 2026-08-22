<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_grounding (refactor R2 leaf extraction of the per-turn ENV-GROUNDING cluster). Pure stdlib, no server.py/DB/network/pytest. Stubs the injected _client_env_var ContextVar + _current_date_str helper via configure(), then pins the grounding invariants: _env_block() emits a parseable <env> key:value block carrying current_date/surface/host/cwd/location/location_source from the live forwarded env; _env_grounding() composes the <env> block + the non-negotiable local-only identity guard + self-architecture + temporal + client prose; _capability_grounding() renders the live verb catalog as 'section: names' lines; _client_env() normalises OWUI metadata.variables (braced keys, sentinels dropped) into the flat env dict; _host_timezone()/_get_os_info() return strings. Guards the extracted leaf so a later move can't silently change the system-role grounding shape.
AI-related: ./mios_grounding.py
AI-functions: check, FakeVar, FakeHeaders, t_capability, t_host_os, t_client_env, t_env_block, t_env_grounding, t_principal_bind, main

<!-- mios-src:58ccb1ec8e5b from usr/lib/mios/agent-pipe/test_mios_grounding.py:1-4 -->

