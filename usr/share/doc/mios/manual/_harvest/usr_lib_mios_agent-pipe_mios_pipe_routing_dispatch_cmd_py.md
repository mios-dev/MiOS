<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Return (cmd, workspace_or_None). When SANDBOX_ENFORCE is on...

Return (cmd, workspace_or_None). When SANDBOX_ENFORCE is on AND `tool` OPTS
    IN to confinement (an explicit [verbs.*].sandbox_profile) AND the resolved
    profile is confined AND the cmd does not already self-confine, prefix it with
    mios-sandbox-exec (--level enforce, +--net iff the tier allows egress) bound to
    a fresh per-dispatch workspace. Otherwise the cmd is returned unchanged. The
    OPT-IN gate (explicit override, not tier alone) is what keeps OS-control/launch
    verbs -- which bwrap would break -- from ever being wrapped here.

<!-- mios-src:e1a811185cb1 from usr/lib/mios/agent-pipe/mios_pipe/routing/dispatch_cmd.py:54-60 -->
