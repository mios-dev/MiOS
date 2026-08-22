<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes mios-swarm-pack-firstboot to arm concurrent small-model worker units if gpu_profile is "swarm", enforcing VRAM budgets and provisioning GGUFs during the first boot sequence.
AI-related: /usr/libexec/mios/mios-swarm-pack-firstboot, mios-swarm-pack-firstboot, mios-llm-worker, mios-cdi-detect, mios-ai-firstboot, mios-cdi-detect.service, mios-ai-firstboot.service, network-online.target, multi-user.target
SWARM Phase-2 (operator 2026-06-12): arm the concurrent small-model server pack
at boot IF [dispatch].gpu_profile == "swarm" (else the script is a no-op). The
script self-gates + enforces the VRAM budget, so this unit is safe to enable
unconditionally; it only ever starts mios-llm-worker@<name> units when the
operator has flipped the profile + provisioned GGUFs.

<!-- mios-src:6ea92de16fd6 from usr/lib/systemd/system/mios-swarm-pack-firstboot.service:1-7 -->

