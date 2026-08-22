<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for the #49 enrich domain-filter...

Standalone unit test for the #49 enrich domain-filter contract.

server.py `_read_tool_enrich` restricts AUTO-added enrich verbs to the routed
domain, but must NOT drop (a) verbs refine explicitly hinted -- a compound can
span domains -- nor (b) the deterministic local_state core verbs when the turn is
a state query mis-routed to e.g. apps_windows. This pins that set-logic with a
reference impl (pure stdlib; mirrors the server.py keep computation), the same
pattern as test_mios_launch. Live behaviour is verified on MiOS-DEV.

Run:  python test_mios_compound.py

<!-- mios-src:a4070d756c4b from usr/lib/mios/agent-pipe/test_mios_compound.py:3-13 -->
