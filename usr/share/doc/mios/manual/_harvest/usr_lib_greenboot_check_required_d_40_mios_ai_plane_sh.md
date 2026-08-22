<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/bash AI-hint: greenboot required check that...

!/usr/bin/bash
AI-hint: greenboot required check that verifies the core MiOS AI plane (agent-pipe, llm-light, pgvector) answered after boot; a non-zero exit triggers bootc rollback. Service ports are sourced from the SSOT bridge (/etc/mios/install.env) and only ENABLED services are probed, so it degrades open instead of false-failing.
AI-related: mios-greenboot, mios-agent-pipe.service, mios-llm-light.service, mios-pgvector.service, hermes-worker.service, /etc/mios/install.env, mios-sync-env

<!-- mios-src:b172a52fee5c from usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh:1-3 -->

