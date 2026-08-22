<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### MUST run before anything else. check_ai_manifests_fresh...

MUST run before anything else. check_ai_manifests_fresh compares the
manifests against a fresh walk of automation/ and tools/, and dozens of
the tests below create, mutate and restore files in exactly those trees
(some restore via `echo "$orig" >`, which drops a trailing newline). Run
it last and it grades the wreckage of every preceding test instead of the
committed state.

<!-- mios-src:1a2b377668f5 from tests/drift-gate-negatives.sh:3330-3335 -->
