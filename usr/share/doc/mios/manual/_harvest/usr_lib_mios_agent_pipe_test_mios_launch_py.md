<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for the deterministic_action_route logic to ensure "open/launch" commands correctly strip filler phrases and map to open_app(name) instead of falling back to the LLM discovery path.
AI-related: /usr/share/mios/mios.toml
AI-functions: _check, _load_fillers, _extract, t_ssot, t_extraction, main

<!-- mios-src:4a22f1aaa73d from usr/lib/mios/agent-pipe/test_mios_launch.py:1-3 -->

