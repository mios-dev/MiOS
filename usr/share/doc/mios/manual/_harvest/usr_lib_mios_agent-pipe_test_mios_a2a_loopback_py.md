<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Offline tests for T-066 (A2A federation loopback smoke...

Offline tests for T-066 (A2A federation loopback smoke test).

The network/CLI half of mios-a2a-test needs a live agent-pipe; the pure
protocol helpers (build_message / extract_artifact_text / classify_task) are
exercised here with stub Task payloads so the round-trip's shape logic is
guarded without any live service.

<!-- mios-src:69d603946b75 from usr/lib/mios/agent-pipe/test_mios_a2a_loopback.py:3-9 -->
