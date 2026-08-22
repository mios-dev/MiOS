<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for the #61 pods->k3s generated...

Standalone unit test for the #61 pods->k3s generated manifests.

Validates the COMMITTED artifacts (not the generator, which needs live pods +
podman): each manifest must parse as YAML, declare an apiVersion, carry the
deterministic AI-hint header, and contain none of the volatile fields the
generator strips -- so a malformed or un-stripped manifest can never land. Skips
cleanly if pyyaml is unavailable.

Run:  python test_mios_k3s.py

<!-- mios-src:6a5839b5edb4 from usr/lib/mios/agent-pipe/test_mios_k3s.py:3-12 -->
