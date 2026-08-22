<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_router -- the pure routing decision for the MiOS...

mios_router -- the pure routing decision for the MiOS agent-pipe (WS-A11/WS-3
kernel decomposition, Stage 1).

A request's refined plan carries an `intent`; today chat_completions selects its
execution shape through a large, scattered `refined.get('intent')` cascade. This
module extracts the PRIMARY classification into one pure function: refined plan
-> RouteDecision. The Dispatcher (Stage 2) runs the decision; the Kernel facade
(Stage 2) composes Router + Dispatcher + the manager seams. Keeping Stage 1
additive + unwired means it is fully testable with ZERO risk to the live path
until the Stage-2 delegation is verified in the VM.

Modes (the execution shape the Dispatcher will run):
  chat       -- conversational reply, no tools / no fan-out
  dispatch   -- exactly ONE MiOS verb call (RouteDecision.tool)
  multi_task -- broad swarm fan-out (parallel facets)
  dag        -- a structured multi-node DAG plan
  agent      -- general single-agent tool-loop (the safe default; may deepen)

<!-- mios-src:facc301ef708 from usr/lib/mios/agent-pipe/mios_pipe/routing/router.py:3-20 -->
