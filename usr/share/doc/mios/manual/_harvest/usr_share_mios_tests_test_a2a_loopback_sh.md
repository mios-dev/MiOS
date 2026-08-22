<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Shell entrypoint for the A2A...

!/usr/bin/env bash
AI-hint: Shell entrypoint for the A2A federation loopback smoke test (roadmap B5 / T-066). Thin wrapper over mios-a2a-test --loopback: MiOS speaks to itself over the /a2a JSON-RPC surface and asserts a Message -> Task -> Artifact round-trip plus a recorded delegation chain. Operator runs this on a booted host.
AI-related: usr/libexec/mios/mios-a2a-test, usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py

<!-- mios-src:7ebadc439ce6 from usr/share/mios/tests/test-a2a-loopback.sh:1-3 -->

