<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Smoke-test reflect_on_step_failure. Calls the reflection...

Smoke-test reflect_on_step_failure.

Calls the reflection helper with a deliberately-bad failed_node
(unknown verb) and verifies the small refine model returns a
correction with a non-empty tool name + rationale.

Live test -- hits the actual refine endpoint -- so it's slow
(15-30s on CPU) but exercises the real path.

<!-- mios-src:d63f63fff4d6 from tests/test-reflection.py:3-11 -->
