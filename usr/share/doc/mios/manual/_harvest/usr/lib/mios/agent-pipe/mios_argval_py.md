<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Tool-Manager parameter validation (ref AIOS kernel C 3.7...

Tool-Manager parameter validation (ref AIOS kernel C 3.7: "validate
    parameters before execution to prevent tool crashes"). Reject a verb
    arg whose value falls outside the enum DECLARED for it in mios.toml
    [verbs.<tool>.params.<arg>.enum], BEFORE the command reaches the
    broker -- previously such values passed through as a stray env var and
    silently misbehaved.

<!-- mios-src:eb46518aa256 from usr/lib/mios/agent-pipe/mios_argval.py:39-44 -->
