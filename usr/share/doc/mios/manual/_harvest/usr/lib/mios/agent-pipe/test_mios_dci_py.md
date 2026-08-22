<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### The dissent-extraction cutoff must read from the SSOT knob...

The dissent-extraction cutoff must read from the SSOT knob
    (DCI_FLOW_TRIGGER_CONF), not a baked literal. Drive the same flow
    with the knob raised ABOVE the challenger's 0.9 confidence and
    assert the challenge is NO LONGER extracted as dissent -- proving
    the cutoff is config-driven, then restore the knob.

<!-- mios-src:ae2e74d3a2df from usr/lib/mios/agent-pipe/test_mios_dci.py:132-136 -->
