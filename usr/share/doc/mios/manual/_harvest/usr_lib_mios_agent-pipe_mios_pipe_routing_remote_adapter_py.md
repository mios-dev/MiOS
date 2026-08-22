<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Adapt and issue a chat completion request to a remote node...

Adapt and issue a chat completion request to a remote node endpoint.

    If node_cfg['api'] is 'anthropic' or 'gemini', translates request format and
    translates provider response back to OpenAI Chat Completion format.
    Otherwise (openai / unset / unknown), passes the request through directly.

<!-- mios-src:1f0e307102d3 from usr/lib/mios/agent-pipe/mios_pipe/routing/remote_adapter.py:30-35 -->
