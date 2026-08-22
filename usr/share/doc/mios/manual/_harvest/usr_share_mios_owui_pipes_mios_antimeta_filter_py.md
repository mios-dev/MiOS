<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Processes the OWUI output stream to wrap meta-narrative and reasoning lines in <think> tags for collapsible UI rendering while stripping hard refusal patterns based on the system's central refusal-patterns.txt (this display-side strip is the sole remaining consumer of that file; the daemon's refusal DETECTION is now model-driven, no pattern gate).
AI-related: /usr/share/mios/ai/, /usr/share/mios/ai/refusal-patterns.txt
AI-functions: _is_narration_line, __init__, _reload, _strip_refusals, _transform_lines, _flush_narration, _process, stream, outlet, class Filter, class Valves

<!-- mios-src:ed8a9d4a8162 from usr/share/mios/owui/pipes/mios_antimeta_filter.py:1-3 -->

