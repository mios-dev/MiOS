<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: The ONE shared outbound httpx.AsyncClient for the whole pipe, extracted verbatim from server.py, plus the WS-A6/T-226 batch-coalescing chokepoint that rides on it. Every upstream call in agent-pipe obtains its client from _get_client(), which makes the client -- not any call site -- the real chokepoint, so coalescing attaches as an httpx REQUEST EVENT HOOK and no call site had to be edited. The hook is registered ONLY when [dispatch].batch_enable is true: at the default the client is constructed with exactly the arguments it used before the feature existed. Settings arrive by one-way dependency injection through configure(); this module NEVER imports server.
AI-related: ./mios_pipe/scheduler/batch.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_httpclient.py, usr/share/doc/mios/manual/ch59-request-coalescing.md
AI-functions: configure, get_coalescer, reset, _batch_request_hook, _get_client

<!-- mios-src:5aba5098d805 from usr/lib/mios/agent-pipe/mios_pipe/kernel/httpclient.py:1-3 -->

