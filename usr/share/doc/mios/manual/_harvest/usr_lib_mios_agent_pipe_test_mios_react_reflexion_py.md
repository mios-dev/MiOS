<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for T-031 (ReAct+Reflexion Durable Loop + Checkpoint-per-Superstep). Pure stdlib + asyncio, no server.py/DB/network. Verifies reflexion gate checks, reflexion retry event logging, superstep checkpoint saving/loading for both execute_dag and v1_secondary_tool_loop.
AI-related: ./mios_pipe/routing/dag_exec.py, ./mios_pipe/routing/secondary_loop.py
AI-functions: check, t_reflexion_gate, t_tool_failure_reflexion_flow, t_superstep_checkpoints, t_dag_execution_checkpoint_resume, main

<!-- mios-src:43b621ff467e from usr/lib/mios/agent-pipe/test_mios_react_reflexion.py:1-4 -->

