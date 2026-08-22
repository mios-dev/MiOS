<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Read the component lists from SSOT. A missing or empty list...

Read the component lists from SSOT. A missing or empty list is FATAL, not a
fallback: `for x in ${EMPTY}` runs zero iterations and the loop still prints
"OK", so an SSOT edit that dropped a list would turn this whole harness into a
vacuous pass. The old fallbacks also hardcoded paths (Law 7) and capitalised
them ("Usr/..."), so they could never have matched anything anyway.

<!-- mios-src:91e227c14aae from tests/bake-smoke.sh:22-26 -->
