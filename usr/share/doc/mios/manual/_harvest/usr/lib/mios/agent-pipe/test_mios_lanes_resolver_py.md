<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Stdlib unit tests for mios_lanes_resolver (strangler-fig...

Stdlib unit tests for mios_lanes_resolver (strangler-fig extraction).

Drives the moved lane-resolver cluster with a fake httpx client + stubbed
config -- NO network, NO DB. Asserts: lane selection prefers the heavy lane when
its probe is up, falls back to the always-on light lane when the heavy lanes are
down, the legacy heavy/light probe is used when the resolver path raises, and the
_heavy_lane_up probe caches + degrades closed. Run: ``python test_mios_lanes_resolver.py``.

<!-- mios-src:74d2d1438d2c from usr/lib/mios/agent-pipe/test_mios_lanes_resolver.py:3-10 -->
