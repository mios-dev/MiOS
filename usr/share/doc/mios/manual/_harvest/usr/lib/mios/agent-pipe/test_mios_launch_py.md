<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for the deterministic launch-target...

Standalone unit test for the deterministic launch-target extraction
(server.py `_deterministic_action_route`: SSOT trailing-filler strip + word-count
+ compound-connective guard that binds an unambiguous 'open/launch <app>' to
open_app(name=<app>)).

Pure stdlib -- no server.py import, so it runs on any Python 3.11+ without the
agent-pipe runtime deps. Mirrors the test_mios_kvfork standalone pattern: a
reference impl PINS the contract, and the REAL mios.toml
[routing].launch_filler_phrases SSOT is loaded so a drift in either the list or the
logic is caught. Regression guard for the operator e2e bug where
'open notepad for me' bound name='notepad for me' and 'open spotify on my desktop'
fell through to the LLM path and mis-routed to discovery.

Run:  python test_mios_launch.py

<!-- mios-src:61ce4340e077 from usr/lib/mios/agent-pipe/test_mios_launch.py:3-17 -->
