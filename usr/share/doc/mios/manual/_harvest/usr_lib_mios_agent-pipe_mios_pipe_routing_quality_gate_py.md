<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Evaluate output quality against deterministic rules....

Evaluate output quality against deterministic rules.

    Returns:
        (quality_ok: bool, reason: str)
        If quality_ok is False, smartroute.should_escalate() will trigger escalation.
        Degrades open (returns True, "degrade_open") on unexpected exceptions.

<!-- mios-src:cf7bb41b5fd5 from usr/lib/mios/agent-pipe/mios_pipe/routing/quality_gate.py:56-62 -->
