<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Executable proof of...

!/usr/bin/env python3
AI-hint: Executable proof of ADR-0016's central claim -- that offloading a service to another machine is purely an addressing change, achieved by an /etc/mios overlay with no file under usr/ edited. Each resolution runs in its OWN subprocess with MIOS_HOST_TOML set, because load_merged() caches per process and because that is how a booted host resolves. Also pins the measurement that corrects Decision 1: [urls] emits MIOS_URLS_* which no shipped code reads, while [ai].endpoint emits MIOS_AI_ENDPOINT which many do, so a service's canonical address is the key its consumers already resolve.
AI-related: usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py, usr/share/doc/mios/adr/0016-blade-node-topology.md, tools/check-service-urls.py

<!-- mios-src:7bfcd7952c5a from tests/test-offload-overlay.py:1-3 -->

