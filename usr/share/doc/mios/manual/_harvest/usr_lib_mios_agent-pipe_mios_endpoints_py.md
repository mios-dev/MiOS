<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Endpoint capability detection (pure leaf extracted from...

Endpoint capability detection (pure leaf extracted from server.py).

MiOS is OpenAI-/v1-only -- every lane exposes ``/v1/chat/completions``, so there
is no wire-dialect to detect. This module probes what FEATURE-SET a given /v1
endpoint supports: a llama.cpp ``llama-server`` that can do ``/slots`` KV paging,
whether it accepts ``tool_choice='required'``, and whether its model reliably
emits well-formed PARALLEL tool calls. Every probe is CONFIG-FIRST (a
per-binding/agent ``api`` field wins) and falls back to an env-SSOT host:port
hint tuple, so no bare port literal lives in the routing code. All functions are
pure (endpoint string + cfg dict + optional engine); the only dependency is
``mios_config._DISPATCH_TOML`` for the hint defaults. ``server.py`` re-imports
every name under its original ``_``-prefixed alias so the module's importable
surface is byte-identical (surface-parity gate).

<!-- mios-src:6cefc369b17a from usr/lib/mios/agent-pipe/mios_endpoints.py:3-16 -->
