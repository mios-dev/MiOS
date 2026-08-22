<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for mios_codemode logic to verify language normalization, timeout clamping, and session ID generation without requiring the full agent-pipe runtime or database.
AI-related: mios_codemode, /usr/libexec/mios/mios-coderun-codemode, mios-coderun-codemode, mios-coderun-sandbox-cm-abc
AI-functions: _check, t_normalize_lang, t_clamp_timeout, t_session_id, t_extract_code, t_validate_request, t_gating, t_net_allowed, t_podman_argv, t_parse_result, t_build_cli_argv, t_safe_token

<!-- mios-src:972b30663097 from usr/lib/mios/agent-pipe/test_mios_codemode.py:1-3 -->

