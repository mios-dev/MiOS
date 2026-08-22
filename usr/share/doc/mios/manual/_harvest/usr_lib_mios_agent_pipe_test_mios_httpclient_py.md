<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_pipe.kernel.httpclient -- the ONE shared outbound AsyncClient and the T-226 batch-coalescing chokepoint riding on it. Proves the clause the roadmap called "a proven no-op": at the default flag the hook is not merely inert, it is NEVER REGISTERED, so the client is constructed with exactly the arguments it used before the feature existed. With the flag on it proves the opposite direction -- the hook is on the client, a native lane is not held, concurrent non-native POSTs are held together for the window, a GET is never held, an unreadable/streaming body degrades open, and server.py still re-exports _get_client under its original name.
AI-related: ./mios_pipe/kernel/httpclient.py, ./mios_pipe/scheduler/batch.py, ./server.py
AI-functions: check, t_default_off, t_flag_on, t_degrades_open, t_server_reexport, main

<!-- mios-src:37be1bc4680f from usr/lib/mios/agent-pipe/test_mios_httpclient.py:1-4 -->

