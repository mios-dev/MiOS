<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-11 layered-interop 3-projection core. Pure-stdlib projector that renders ONE MiOS capability (a verb, a recipe, or a promoted skill) into the A2A AgentCard "skill" shape -- the THIRD interop projection alongside the MCP tool + OpenAI function shapes server.py already emits -- plus project_all() returning the key fields of all three for parity-checking. Lets the A2A directory advertise the full capability surface (passport-gated by the caller) in the open A2A standard, not only via MCP/OpenAI. server.py owns wiring the A2A skills into the agent card; this module owns the pure projection so it unit-tests in isolation.
AI-related: ./mios_manifest.py, ./server.py, /.well-known/agent-card.json, ./test_mios_interop.py
AI-functions: to_a2a_skill, project_all, _tags

<!-- mios-src:dc928938d8b7 from usr/lib/mios/agent-pipe/mios_pipe/routing/interop.py:1-3 -->

