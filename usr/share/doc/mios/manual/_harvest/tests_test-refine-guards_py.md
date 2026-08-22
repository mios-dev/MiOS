<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Verify the new refine post-parse guards demote...

Verify the new refine post-parse guards demote misclassified
intents to `agent`. Three cases:

  1. Long multi-step prompt -- exact operator-flagged trace:
     "find all of my installed games; research all their ratings,
     review and launch the highest reviewed game I have installed
     for me on my PC". Refine model may emit intent=dispatch (as
     it did in the failure trace); the length guard should promote
     to agent so the planner can decompose.
  2. Short legitimate dispatch -- "open chrome". Should pass
     through as intent=dispatch (length under threshold).
  3. Multi-word arg value -- simulate a refine output via direct
     guard invocation (refine model is non-deterministic, so we
     can't always force it; this case is exercised by calling the
     guard logic directly with a forged envelope).

Live test against the real refine endpoint -- slow (15-30s per
call on CPU).

<!-- mios-src:7f133c2ab83a from tests/test-refine-guards.py:3-21 -->
