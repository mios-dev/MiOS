<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A1 anti-drift manifest projection -- the PURE core that projects the live verb catalog (mios.toml [verbs.*]) into a deterministic ai/v1 manifest object (registry_kind="verb-catalog"), so the model-facing verb surface has a committed, diffable SSOT projection separate from the file-backed Hermes build-tools registry (tools.json, registry_kind="hermes-build-tools" -- a DISJOINT namespace). load_verbs_from_toml parses the catalog the same way the agent-pipe loader does (section-gated); project_verb_catalog renders the stable manifest; diff_manifest compares a freshly-generated manifest against the committed one for the --check drift gate. The mios-ai-manifest-gen CLI + 98-drift-checks own the I/O; this module is pure (tomllib+json) so it unit-tests in isolation.
AI-related: /usr/libexec/mios/mios-ai-manifest-gen, ./server.py, /usr/share/mios/mios.toml, /usr/share/mios/ai/v1/tools.json, ./test_mios_ai_manifest.py, ./automation/98-drift-checks.sh
AI-functions: load_verbs_from_toml, project_verb_catalog, diff_manifest

<!-- mios-src:722b21261066 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/manifest.py:1-3 -->

