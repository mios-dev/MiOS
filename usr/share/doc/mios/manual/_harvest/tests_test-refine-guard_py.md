<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Smoke-test the refine chat-promotion guard. Calls...

Smoke-test the refine chat-promotion guard.

Calls refine_intent() with three actionable inputs that a small
refine model has historically misclassified as chat (operator-
flagged trace: 'mios-open-url https://...' returned intent=chat
+ fabricated 'Wikipedia has been opened' confirmation when nothing
was actually executed). Verifies the post-parse guard rewrites
chat -> dispatch.

<!-- mios-src:eeb00086dc8c from tests/test-refine-guard.py:3-11 -->
