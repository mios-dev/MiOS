<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Blacklists NVIDIA GPU drivers by default to prevent conflicts in virtualized environments, unless the mios-gpu-detect service detects bare metal hardware and removes this configuration to enable native drivers.
AI-related: mios-gpu-detect
'MiOS': nvidia blacklisted by default in the image.
The mios-gpu-detect service removes this file on bare metal
with an actual NVIDIA GPU, then loads the modules.
In VMs: this file stays, nvidia never loads, hyperv_drm/virtio-gpu works.

<!-- mios-src:ae2e82a513c0 from usr/lib/modprobe.d/mios-nvidia-blacklist.conf:1-6 -->

