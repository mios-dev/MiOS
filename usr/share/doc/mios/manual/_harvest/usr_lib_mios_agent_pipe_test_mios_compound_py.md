<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for the #49 read-tool-enrich domain-filter fix: a compound that spans domains must keep verbs refine EXPLICITLY hinted (and, for a local_state query, the deterministic core state verbs) even when the turn routed to one domain -- so "list windows AND system status" (apps_windows route) still grounds on system_status.
AI-related: server.py
AI-functions: _check, _enrich_keep, t_compound_cross_domain, t_local_state_core, t_no_overground, t_no_domain, main

<!-- mios-src:a7f308e36879 from usr/lib/mios/agent-pipe/test_mios_compound.py:1-3 -->

