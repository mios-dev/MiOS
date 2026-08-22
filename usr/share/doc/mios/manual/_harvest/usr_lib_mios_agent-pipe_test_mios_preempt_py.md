<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Regression guard

Regression guard: with queue_enable OFF, _higher_priority_waiting is byte-
    identical to the T-019 probe-only path even if the queue holds a higher-priority
    turn -- so the queue can never silently change default-off preemption.

<!-- mios-src:8d8418cfe25d from usr/lib/mios/agent-pipe/test_mios_preempt.py:646-648 -->
