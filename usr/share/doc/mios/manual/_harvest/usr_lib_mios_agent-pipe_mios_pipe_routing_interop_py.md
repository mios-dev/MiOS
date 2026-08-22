<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_interop -- 3-projection interop for the MiOS...

mios_interop -- 3-projection interop for the MiOS agent-pipe (WS-11).

Pure stdlib. A capability (verb/recipe/skill) is advertised three ways: the MCP
`tools/list` shape, the OpenAI function shape (both already projected in
server.py), and -- the missing third -- the A2A AgentCard `skills[]` shape so a
federated peer discovers MiOS capabilities over the open A2A standard. This
module renders that A2A shape + a parity view of all three, deterministically.

A2A skill entry (AgentCard.skills[], stable across A2A 0.3/1.0):
  {id, name, description, tags[]}  -- id is the canonical capability key.

<!-- mios-src:98598f6a982f from usr/lib/mios/agent-pipe/mios_pipe/routing/interop.py:3-13 -->
