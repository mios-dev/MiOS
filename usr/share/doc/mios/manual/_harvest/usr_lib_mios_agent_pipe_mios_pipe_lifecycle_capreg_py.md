<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-2 unified capability registry projection -- the PURE half: merge the [verbs.*] catalog, the [recipes.*] OS-command templates, AND the structured JSON skills (usr/share/mios/skills/*.json, whose body.steps[].verb form the capability DAG) into ONE RBAC-filtered, platform-aware capability manifest (each tagged kind=verb|recipe|skill + its permission tier; a skill carries `uses` = its component verbs and is admitted only if its tier AND every component verb is permitted -- reachability fail-closed). build_capability_dag exposes the nodes/edges/cycles/dangling graph. FAIL-CLOSED on unknown tier/ceiling/dangling-edge/cycle (a security control, mirrors mios_pdp). Deterministic, stdlib-only so it unit-tests in isolation; server.py owns wiring this to the live surface + the generative-refusal (LLM) half. Complements mios_manifest (verb-only projection) + mios_registry (packages).
AI-related: ./mios_manifest.py, ./mios_pdp.py, ./mios_registry.py, /usr/share/mios/mios.toml, /usr/share/mios/skills, ./server.py, ./test_mios_capreg.py
AI-functions: tier_rank, allowed, recipe_platforms, skill_steps, skill_effective_tier, build_capability_manifest, manifest_summary, load_recipes_from_toml, load_skills_from_dir, build_capability_dag, project_from_toml, diff_capabilities

<!-- mios-src:e1a326a3b08d from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/capreg.py:1-3 -->

