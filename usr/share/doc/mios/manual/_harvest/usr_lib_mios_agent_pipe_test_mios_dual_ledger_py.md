<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for T-030 (Dual-Ledger + Typed-Output Synthesis). Pure stdlib + asyncio, no server.py/DB/network. Verifies fact_ledger & progress_ledger table insertion triggers, both-intent DAG dependency wiring, parse_research_claims extractor, fact injection into action prompts, synthesis reducer, and stall re-plan triggers.
AI-related: ./mios_pipe/routing/dag_exec.py, ./mios_pipe/routing/swarm.py
AI-functions: check, t_both_intent_deps, t_parse_research_claims, t_execute_dag_node_ledger_writes, t_synthesis_reducer, t_replan_stall_trigger, main

<!-- mios-src:1b22d02b6dd9 from usr/lib/mios/agent-pipe/test_mios_dual_ledger.py:1-4 -->

