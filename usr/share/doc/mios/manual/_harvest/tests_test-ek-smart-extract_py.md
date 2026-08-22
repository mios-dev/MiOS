<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Verify the ReWOO #E<id> substitution now smart-extracts a...

Verify the ReWOO #E<id> substitution now smart-extracts a single
field instead of pasting the whole upstream JSON blob.

Test cases derived from operator's failure trace where the planner
emitted open_app(name=#En1) and substitution pasted mios_apps's
entire NDJSON output as the arg.

<!-- mios-src:fd04fe58468c from tests/test-ek-smart-extract.py:3-9 -->
