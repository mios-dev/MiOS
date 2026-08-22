<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_hitl (WS-6 HITL decision...

Standalone unit test for mios_hitl (WS-6 HITL decision helpers).

Pure stdlib + the sibling module only -- no server.py / DB. The live
pending_action I/O + approval endpoints are verified by the operator on
MiOS-DEV; this covers the deterministic decision logic.

Run:  python test_mios_hitl.py

<!-- mios-src:b23ebc543e08 from usr/lib/mios/agent-pipe/test_mios_hitl.py:3-10 -->
