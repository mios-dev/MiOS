<!-- AI-hint: Manual pages distilled from the source comments of hw, sanitized, each passage anchored to the comment it came from. -->

# hw

### Guest virtual ACPI battery and power state passthrough...

Guest virtual ACPI battery and power state passthrough daemon for MiOS.

Reads physical power supply state from /sys/class/power_supply/ (BAT0, AC, etc.)
and generates QMP/ACPI event notifications for guest virtual machines.

Architectural Invariant:
Do NOT poll power supply sysfs files faster than once every 5 seconds to conserve CPU power.

<!-- mios-src:9e4ad8e2b4f6 from usr/libexec/mios/hw/battery_passthrough.py:4-11 -->

### Automated CPU governor switcher and frequency scaling...

Automated CPU governor switcher and frequency scaling manager for MiOS.

Manages CPU frequency governors via /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor.
Integrates with libvirt qemu hook to dynamically set performance mode when VMs run,
and restore prior power-saving governors upon VM termination.

Architectural Invariant:
Do NOT keep CPUs in fixed performance governor indefinitely when the machine is idle.

<!-- mios-src:2608fbb3e646 from usr/libexec/mios/hw/cpu_governor.py:4-12 -->

### "L1.2", "L1.1", "Disabled"

"L1.2", "L1.1", "Disabled"

<!-- mios-src:945dbf639682 from usr/libexec/mios/hw/gpu_powerd.py:30-30 -->

### MiOS GPU Slicing, Partitioning & Container Device Interface...

MiOS GPU Slicing, Partitioning & Container Device Interface (CDI) Engine.

Manages fractional GPU hardware compute allocation:
1. Physical GPU Discovery: Detects NVIDIA (Ampere, Hopper, Blackwell) and AMD (CDNA, RDNA) compute devices.
2. Declarative MIG Partitioning: Validates and configures Multi-Instance GPU profiles.
3. Dynamic CDI Generation: Synthesizes OCI-compliant Container Device Interface specifications
   so Podman Quadlet containers can attach isolated GPU fractions without root privileges.

<!-- mios-src:e89e537a1da8 from usr/libexec/mios/hw/gpu_slice.py:4-12 -->

### GPU thermal, junction temperature, and clock frequency...

GPU thermal, junction temperature, and clock frequency watchdog for MiOS.

Monitors discrete GPU junction/hotspot temperatures via DRM/hwmon and NVML,
calculating dynamic fan curves to maintain junction temperatures under 80°C.

Architectural Invariant:
Do NOT set fan speeds to 0% under any operational thermal condition.

<!-- mios-src:0ddf929795a7 from usr/libexec/mios/hw/gpu_thermal_watchdog.py:4-11 -->

### Calculate target fan duty cycle percentage based on...

Calculate target fan duty cycle percentage based on temperature.

        Enforces:
        - Fan floor invariant: duty cycle >= self.min_fan_floor_percent (NEVER 0%).
        - Target ceiling: 100% when temp >= target junction temp (80.0°C).

<!-- mios-src:29ec5a44792e from usr/libexec/mios/hw/gpu_thermal_watchdog.py:279-284 -->

### Power-supply state detector (mios-powerd) and battery-aware...

Power-supply state detector (mios-powerd) and battery-aware AI inference downscaler.

Monitors AC/DC power supply state via /sys/class/power_supply or netlink udev events.
On DC (Battery):
  - Downscales llama-swap inference models to lightweight 3B/7B GGUF tier ('light_3b').
  - Pauses background fine-tuning containers ('mios-finetune', 'mios-embed-backfill').
  - Sets CPU energy performance preference (EPP) to 'power' and governor to 'powersave'.
  - Restricts GPU power state / cap.
On AC (Mains):
  - Restores full inference model allocations ('heavy').
  - Unpauses background fine-tuning containers.
  - Sets CPU EPP to 'balance_performance' and governor to 'performance'.
  - Restores GPU full power state.

Architectural Invariant:
Do NOT run unconstrained multi-GPU heavy training while operating on battery power.

<!-- mios-src:c9eac6e2fdd0 from usr/libexec/mios/hw/powerd.py:4-20 -->

### USB hotplug manager routing game controllers and audio DACs...

USB hotplug manager routing game controllers and audio DACs dynamically to guests.

Scans USB bus topology, classifies devices into eligible guest passthrough targets
(Xbox, PlayStation, Nintendo, 8BitDo, USB Audio DACs) while strictly protecting
host keyboards, mice, and critical inputs from accidental detachment.

Architectural Invariant:
Do NOT hotplug host keyboards or mice that would lock the operator out of the host OS.

<!-- mios-src:b23219dbb9de from usr/libexec/mios/hw/usb_hotplug.py:4-12 -->
