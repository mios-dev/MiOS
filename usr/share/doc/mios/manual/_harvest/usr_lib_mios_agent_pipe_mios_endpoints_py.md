<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure endpoint capability detection extracted verbatim from server.py (strangler-fig refactor R-wave). MiOS is OpenAI-/v1-only: every lane speaks /v1/chat/completions, so this module no longer classifies a wire DIALECT -- it answers "what FEATURES does THIS /v1 lane support?" from CONFIG-first signals: _binding_api reads the per-engine/per-agent `api` field; _endpoint_is_llamacpp (llama.cpp llama-server that exposes /slots KV paging), _endpoint_supports_tool_choice (llama.cpp 400s on tool_choice='required'), _endpoint_supports_parallel_tools (only the capable heavy lane emits well-formed parallel calls) all fall back to env-SSOT host:port hint tuples so NO bare port literal lives in the routing decision. The hint tuples + api-name sets (_NO_TOOL_CHOICE_*/_PARALLEL_TOOLS_HINTS/_LLAMACPP_API/_KV_PAGING_HINTS) moved with the fns since only this cluster consumed them. Self-contained + side-effect-free (stdlib + mios_config._DISPATCH_TOML); NO DI, never imports server. server.py re-imports every name under its original _-prefixed alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./test_mios_endpoints.py
AI-functions: _binding_api, _endpoint_supports_tool_choice, _endpoint_supports_parallel_tools, _endpoint_is_llamacpp

<!-- mios-src:504c818958a2 from usr/lib/mios/agent-pipe/mios_endpoints.py:1-3 -->

