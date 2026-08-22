<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Verb -> bash COMMAND BUILDER, extracted VERBATIM from mios_dispatch.py (T-273). The pure-ish half of the dispatch chokepoint: _dispatch_sandbox_profile (resolve the WS-A13 confinement profile from the verb's permission tier + optional explicit override), _sandbox_wrap_cmd (prefix mios-sandbox-exec when the verb OPTS IN and the profile is confined -- the opt-in gate is what keeps OS-control/launch verbs bwrap would break from ever being wrapped), normalize_container_exec (docker->podman + tty-flag normalisation), and _build_dispatch_cmd (the per-verb guard registry mapping verb+args -> the broker bash line). SECURITY-CRITICAL and NAME-KEYED: never rename a verb key, a permission tier, or a membership set. The launcher proper, the taint/HITL/Rule-of-Two/quarantine gates and the broker socket I/O stay in mios_dispatch.py -- this module builds a command, it never runs one. _template_to_cmd / _arg_with_synonyms come DIRECTLY from their sibling modules; the verb catalog and the two sandbox knobs are dependency-INJECTED via configure() (one-way boundary -- this module never imports server or mios_dispatch).
AI-related: ../../mios_dispatch.py, ../../mios_sandbox.py, ../../mios_template.py, ../../mios_argval.py, ../../test_mios_dispatch.py
AI-functions: configure, _dispatch_sandbox_profile, _sandbox_wrap_cmd, normalize_container_exec, _build_dispatch_cmd

<!-- mios-src:8dbf302be76a from usr/lib/mios/agent-pipe/mios_pipe/routing/dispatch_cmd.py:1-3 -->

