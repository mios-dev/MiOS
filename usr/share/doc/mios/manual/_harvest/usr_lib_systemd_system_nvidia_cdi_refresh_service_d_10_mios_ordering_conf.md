<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Overrides the nvidia-cdi-refresh.service ordering to break circular dependencies caused by multi-user.target, ensuring it runs after kernel modules and udev triggers instead of waiting for high-level services.
AI-related: nvidia-cdi-refresh.service, multi-user.target, podman.service, k3s.service, systemd-modules-load.service, systemd-udev-trigger.service
'MiOS' v0.2.4 drop-in for nvidia-cdi-refresh.service
----------------------------------------------------------------------------
Workaround for NVIDIA/nvidia-container-toolkit#1735: v0.2.0 added
`After=multi-user.target` to the stock unit, creating an ordering cycle
with any unit that both WantedBy=multi-user.target and
Requires=nvidia-cdi-refresh.service (e.g. podman.service, k3s.service).

Empty `After=` clears the inherited value, then re-declare minimal sane
ordering: kernel modules loaded + udev coldplug fired (udev-trigger, not
the deprecated udev-settle which warns at boot).
----------------------------------------------------------------------------

<!-- mios-src:a7f2ac415f91 from usr/lib/systemd/system/nvidia-cdi-refresh.service.d/10-mios-ordering.conf:1-13 -->

