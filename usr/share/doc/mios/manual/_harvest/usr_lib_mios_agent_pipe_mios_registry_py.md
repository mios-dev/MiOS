<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A17 versioned agent/tool package format + local registry projection. Pure core that wraps each capability (a verb/tool, an agent, a recipe) into a VERSIONED package descriptor (author/name/version/kind + manifest) and projects a registry INDEX over them -- the SSOT-derived, flag-gated local "package registry" (an AIOS agent/tool distribution unit), built from the same live catalogs WS-A1 projects. build_package/build_registry are deterministic; verify_registry diffs a regenerated index vs the committed one for a drift gate. The mios-registry CLI + automation/lib/generate-packages.sh own the I/O + build-time materialization; this module is pure (stdlib) so it unit-tests in isolation.
AI-related: ./mios_manifest.py, /usr/libexec/mios/mios-registry, /automation/lib/generate-packages.sh, /usr/lib/mios/schemas/mios-pkg.schema.json, /usr/lib/mios/schemas/mios-registry.schema.json, ./test_mios_registry.py
AI-functions: build_package, build_registry, registry_path, verify_registry

<!-- mios-src:4a704e1cd030 from usr/lib/mios/agent-pipe/mios_registry.py:1-3 -->

