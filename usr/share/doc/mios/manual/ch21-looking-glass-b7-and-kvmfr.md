<!-- AI-hint: Chapter 21: Looking Glass B7 and KVMFR. Explains building and signing KVMFR module from source. Details allocations under /dev/shm for low-latency memory copy. Documents Wayland client build and input mappings. -->

# Chapter 21: Looking Glass B7 and KVMFR

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Looking Glass B7 and KVMFR** under MiOS.

### <a name="21_kvmfr_kernel_module_bake"></a>21.KVMFR Kernel Module Bake: KVMFR Kernel Module Bake

> Path Reference: `/usr/share/doc/mios/manual.md#21_kvmfr_kernel_module_bake`

#### Overview

Looking Glass requires the KVM Framebuffer (KVMFR) driver to share screen memory.

## Build
- **Compilation**: Compiled from source during [52-bake-kvmfr.sh](automation/52-bake-kvmfr.sh).
- **Signing**: Signed automatically with the host's MOK.
- **Verification**: Loaded on boot to expose the virtual memory channel.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="21_shared_memory_framebuffer"></a>21.Shared Memory Framebuffer: Shared Memory Framebuffer

> Path Reference: `/usr/share/doc/mios/manual.md#21_shared_memory_framebuffer`

#### Overview

Looking Glass uses host shared memory to pass frames.

## Setup
- **Allocation**: Configured via tmpfiles configuration templates.
- **Buffer**: Creates `/dev/shm/looking-glass` with correct permissions.
- **Tuning**: Size boundaries are calculated based on guest resolution.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="21_looking_glass_client_setup"></a>21.Looking Glass Client Setup: Looking Glass Client Setup

> Path Reference: `/usr/share/doc/mios/manual.md#21_looking_glass_client_setup`

#### Overview

The host client renders guest framebuffers on the Wayland display.

## Execution
- **Client**: Shipped inside [53-bake-lookingglass-client.sh](automation/53-bake-lookingglass-client.sh).
- **Command**: Launches the Wayland-native client to display virtual displays.
- **Tuning**: Configured for mouse and audio integration.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
