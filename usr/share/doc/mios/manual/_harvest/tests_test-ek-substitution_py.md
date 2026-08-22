<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Smoke-test _substitute_ek_refs. Verifies the ReWOO #E<id>...

Smoke-test _substitute_ek_refs.

Verifies the ReWOO #E<id> placeholder substitution across the
shapes a planner might emit:
  * simple string substitution
  * multiple refs in one arg
  * refs to non-existent ids (preserved literal so dispatch errors)
  * non-string args (passed through)

<!-- mios-src:a9fa0f5051af from tests/test-ek-substitution.py:3-11 -->
