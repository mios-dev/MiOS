<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### A7: agent_memory recall applies the SHARED blended rerank...

A7: agent_memory recall applies the SHARED blended rerank (not flat cosine).
    With rank_age>0 a recently-saved fact OUTRANKS a stale one at EQUAL cosine
    (recency breaks the tie); at rank_age==0 the blend is inert (pure cosine), so the
    contrast proves the recency weighting drove the order. DEGRADE-OPEN: agent_memory
    has no access/tier/outcome columns -> those blend terms read neutral, only cosine
    + ts contribute, and nothing crashes.

<!-- mios-src:6d1217ae691e from usr/lib/mios/agent-pipe/test_mios_knowledge.py:196-201 -->
