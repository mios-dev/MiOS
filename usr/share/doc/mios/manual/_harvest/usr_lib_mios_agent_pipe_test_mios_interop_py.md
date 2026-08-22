<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_interop (WS-11 3-projection: the A2A skill shape). Pure stdlib, no server.py/DB/pytest. Verifies to_a2a_skill renders the A2A AgentCard skill entry (id/name/description/tags), namespaces recipe/skill ids (mios_recipe__/mios_skill__) to match relay routing while verbs keep the bare id, derives tags from kind/section/permission/tier (deduped), uses model_name as the display name, and project_all aligns the function-name vs a2a-id vs description across the three projections.
AI-related: ./mios_interop.py
AI-functions: check, main

<!-- mios-src:2ba133baac4e from usr/lib/mios/agent-pipe/test_mios_interop.py:1-4 -->

