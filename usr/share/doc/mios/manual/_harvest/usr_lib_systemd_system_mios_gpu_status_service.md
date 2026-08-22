<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that detects GPU hardware (NVIDIA, AMD, Intel) and virtualization status, exporting the results to /run/mios/gpu-passthrough.status and enabling the container_use_devices SELinux boolean.
AI-related: mios-gpu, systemd-udev-trigger.service, systemd-modules-load.service, podman.socket, docker.socket, local-fs.target, basic.target, sockets.target, multi-user.target

<!-- mios-src:a6241e634496 from usr/lib/systemd/system/mios-gpu-status.service:1-2 -->

