<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Provides an...

!/usr/bin/env python3
AI-hint: Provides an OpenAI-compatible HTTP shim for the opencode CLI, exposing /v1/models and /v1/chat/completions endpoints to integrate opencode as a standard agent-pipe peer.
AI-related: /usr/lib/mios/agents/opencode/bin/opencode, /etc/mios/opencode/opencode.json, mios-opencode
AI-functions: _selector, _flatten_messages, _run_opencode, log_message, _send, _sse_headers, _sse_write, do_GET, do_POST, _stream, main, class Handler

<!-- mios-src:d54188fdb857 from usr/lib/mios/agents/opencode-gateway/server.py:1-4 -->

