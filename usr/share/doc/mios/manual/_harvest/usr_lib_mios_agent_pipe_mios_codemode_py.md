<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Provides pure, side-effect-free logic for WS-2 Code Mode, including session ID derivation, podman exec argument construction, and tool-call normalization to reduce context window usage by executing code in a local sandbox.
AI-related: mios-coderun-codemode
AI-functions: normalize_lang, clamp_timeout, session_id, extract_code, validate_request, _truthy, is_enabled, net_allowed, podman_exec_argv, parse_result, _try_json_tail, safe_session_token

<!-- mios-src:bcec4f258c0c from usr/lib/mios/agent-pipe/mios_codemode.py:1-3 -->

