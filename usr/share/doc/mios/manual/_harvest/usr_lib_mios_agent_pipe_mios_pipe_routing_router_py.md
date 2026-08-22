<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1: the pure Router. Maps a refined plan's intent (chat|dispatch|multi_task|agent|dag, + deep/deterministic flags) to a typed RouteDecision (mode + whether to fan out + the single dispatch tool), the "decide" half of the AIOS Router/Dispatcher split that today lives as a sprawling refined.get('intent') cascade inline in chat_completions. This module is PURE (no server/FastAPI/IO) so the routing decision is unit-testable in isolation; server.py keeps the branch BODIES for now and (Stage 2, VM-verified) will delegate the classification here. Additive + unwired in Stage 1 -> zero behaviour change.
AI-related: ./server.py, ./mios_kernel.py (Stage 2), ./test_mios_router.py
AI-functions: route, should_fanout, class RouteDecision, class Router

<!-- mios-src:498bbaf2a4bc from usr/lib/mios/agent-pipe/mios_pipe/routing/router.py:1-3 -->

