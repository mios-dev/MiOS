<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for the #61 generated k3s manifests: every committed usr/share/mios/k3s/generated/*.yaml parses, declares an apiVersion, carries the AI-hint header, and has the volatile fields (creationTimestamp / bind-mount-options / podman-version) stripped (the determinism contract). Guards the committed artifacts; needs no podman.
AI-related: tools/generate-k3s-manifests.sh, usr/share/mios/k3s
AI-functions: _check, _gen_dir, main

<!-- mios-src:4629cb16ffa7 from usr/lib/mios/agent-pipe/test_mios_k3s.py:1-3 -->

