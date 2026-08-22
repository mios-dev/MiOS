<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_manifest -- verb-catalog -> ai/v1 manifest projection...

mios_manifest -- verb-catalog -> ai/v1 manifest projection (WS-A1, the AIOS
SSOT anti-drift layer).

Pure stdlib (tomllib + json). The agent-pipe's _VERB_CATALOG is the live SSOT
for the model-facing verb surface, but there was no COMMITTED, diffable
projection of it -- so the surface could drift from the SSOT silently. This
module projects the catalog into a deterministic manifest object; a CLI writes
it to ai/v1/tools.generated.json and a drift gate runs `--check` (regenerate +
diff) to FAIL when the committed projection no longer matches the SSOT.

registry_kind
=============
The existing ai/v1/tools.json is the file-backed HERMES build-tools registry
(9 tool descriptors pointing at chat-completions-api/responses-api/dispatcher
JSON). It is a DISJOINT namespace from the 100+ mios.toml [verbs.*] (which
project live via MCP /v1/verbs, not a static file). To stop the two being
conflated, manifests carry an explicit registry_kind: "hermes-build-tools" for
tools.json, "verb-catalog" for the generated verb projection.

<!-- mios-src:58782077aa39 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/manifest.py:3-21 -->
