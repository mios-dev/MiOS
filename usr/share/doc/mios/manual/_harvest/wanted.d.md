<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Non-critical greenboot check that...

!/bin/bash
AI-hint: Non-critical greenboot check that probes blade reachability per ADR-0016 §8 / AGY-1600. Records reachability state without triggering a rollback unless blade_reachability_critical = true.
AI-related: /usr/share/mios/mios.toml, /etc/mios/mios.toml, /usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh

<!-- mios-src:701840bcf238 from usr/lib/greenboot/check/wanted.d/70-blade-reachability.sh:1-3 -->
