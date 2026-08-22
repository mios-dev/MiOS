<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_knowledge (refactor R6 KNOWLEDGE-cluster extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the recency-weighting invariants (_recency_mult: inert==1.0 when rank_age==0; bounded decay so a fresh row outranks an older one within the half-life and the factor stays in [1-rank_age, 1.0]), the possessive recall-floor (_recall_floor drops to the lower preference floor only when a 1st/2nd-person possessive is present, else the default), and the blended pgvector rerank (_recall_knowledge_pg, driven through the DI seam with async stubs for _embed_one/_MEMORY.retrieve/_rls_owner/_db_fire/_db_update) so a hot+satisfied+frequently-accessed row outranks a cold+unsatisfied one at equal cosine. Guards the extracted cluster so a later move can't silently change the recency math, the floor logic, or the recall ordering.
AI-related: ./mios_knowledge.py
AI-functions: check, t_recall_floor, t_recency_mult, t_recall_blend, _FakeVar, t_rls_owner, t_recall_agent_memory, t_kg_lookup, main

<!-- mios-src:0a1737c3fbc2 from usr/lib/mios/agent-pipe/test_mios_knowledge.py:1-4 -->

