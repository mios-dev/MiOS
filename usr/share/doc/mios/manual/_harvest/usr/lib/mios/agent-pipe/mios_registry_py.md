<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_registry -- versioned package + local registry...

mios_registry -- versioned package + local registry projection (WS-A17, the
AIOS agent/tool packaging layer).

Pure stdlib. A "package" is a versioned, self-describing wrapper around ONE
capability the live SSOT already defines -- a verb/tool, an agent, or a recipe.
The registry INDEX is a flat catalogue of those packages keyed by
author/name/version. Both are deterministic projections of the live catalogs
(the same ones WS-A1 projects), so the whole thing is a materialized SSOT
mirror, gated behind [ai].package_registry (ships inert -> nothing emitted, the
drift gate is a trivial pass).

Path layout (when materialized):
    ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml   (per-package manifest)
    ai/v1/packages/registry.json                              (the index)

<!-- mios-src:8b04ab691e00 from usr/lib/mios/agent-pipe/mios_registry.py:3-17 -->
