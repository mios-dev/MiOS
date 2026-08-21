<!-- AI-hint: Chapter 20: Container Device Interface Plumbing. Covers CDI spec generation for CUDA applications running in rootless podman. Explains ROCm/KFD driver mounts and container bindings. Documents Intel graphics acceleration CDI specs. -->

# Chapter 20: Container Device Interface Plumbing

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Container Device Interface Plumbing** under MiOS.

### <a name="20_nvidia_cdi_automation"></a>20.Nvidia CDI Automation: Nvidia CDI Automation

> Path Reference: `/usr/share/doc/mios/manual.md#20_nvidia_cdi_automation`

#### Overview

NVIDIA CDI specs enable CUDA applications inside rootless containers.

## Setup
- **CDI Specs**: Generated automatically under `/var/run/cdi/`.
- **Refresh**: Refreshed via [45-nvidia-cdi-refresh.sh](automation/45-nvidia-cdi-refresh.sh).
- **Quadlets**: Containers request graphics resources via `CDIDevices=` entries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="20_amd_rocm_cdi_mappings"></a>20.AMD ROCm CDI Mappings: AMD ROCm CDI Mappings

> Path Reference: `/usr/share/doc/mios/manual.md#20_amd_rocm_cdi_mappings`

#### Overview

AMD CDI profiles map compute hardware to container environments.

## Operations
- **Mappings**: Maps `/dev/kfd` and AMD compute files.
- **Settings**: Configured in [41-gpu-cdi-toolkits.sh](automation/41-gpu-cdi-toolkits.sh).
- **Verification**: Validates GPU compute access inside containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="20_intel_gpu_cdi_specs"></a>20.Intel GPU CDI Specs: Intel GPU CDI Specs

> Path Reference: `/usr/share/doc/mios/manual.md#20_intel_gpu_cdi_specs`

#### Overview

Intel CDI maps integrated and discrete Intel graphics processors.

## Details
- **Specs**: Exposes Intel integrated and discrete graphics processors.
- **Conventions**: Exposes GPU nodes inside container layers.
- **Confinement**: Isolates GPU access boundaries to specific containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
