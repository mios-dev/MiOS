<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Proves `mios blade status`...

!/usr/bin/env bash
AI-hint: Proves `mios blade status` answers the one question a MiOS-Mini seat has -- is my blade there? On a seat every offload target is REMOTE, and an unreachable blade otherwise looks like a broken model: the lane resolver returns its terminal lane even when the probe fails (by design, so a turn degrades rather than dead-ends), so all the operator sees is a transport error. Drives the real verb against a real /etc/mios overlay and a real listening socket -- no mocks: one target is up, one is not, and the nodes the overlay does not name stay local.
AI-related: usr/libexec/mios/mios-blade, usr/lib/mios/blade.sh, usr/share/mios/mios.toml, usr/share/doc/mios/reference/mini-vs-hosted.md

<!-- mios-src:edd59d1cb68f from tests/test-blade-reachability.sh:1-3 -->

