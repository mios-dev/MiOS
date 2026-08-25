<!-- AI-hint: Chapter 67: Discrete GPU VFIO Passthrough, Looking Glass B6 IVSHMEM & Inter-VM Audio. -->
# <a name="67_discrete_gpu_vfio_looking_glass_and_displays"></a>Chapter 67: Discrete GPU VFIO Passthrough, Looking Glass B6 IVSHMEM & Inter-VM Audio

> Part IV: Virtualization & Hardware Isolation of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#67_discrete_gpu_vfio_looking_glass_and_displays`

#### Overview

MiOS supports mixed-workload workstations that switch seamlessly between high-throughput AI inference and dedicated Windows/Linux guest virtual machines (`WS-VFIO` / ADR-0016).

#### <a name="67_dynamic_vfio_switching"></a>67.1 Dynamic Whole-Device Passthrough

* **IOMMU Isolation**: `usr/libexec/mios/mios-iommu-audit` validates PCIe group isolation before passthrough.
* **Dynamic Driver Binding**: `usr/libexec/mios/mios-gpu-switch` unbinds host drivers (NVIDIA/amdgpu) and binds devices to `vfio-pci` dynamically without rebooting the host.

#### <a name="67_looking_glass_b6"></a>67.2 Looking Glass B6 Inter-VM Framebuffer

* **Shared Memory Transport**: Framebuffers stream directly from guest GPUs to host Wayland compositors via `/dev/kvmfr0` IVSHMEM shared memory.
* **Direct Input Integration**: SPICE direct socket input capture provides sub-millisecond mouse and keyboard responsiveness.

#### <a name="67_pipewire_jack_audio"></a>67.3 Sub-5ms PipeWire JACK Audio Bridge

Guest audio streams across shared memory (`/dev/shm/scream`) directly into host PipeWire JACK audio graphs with sub-5ms latency, eliminating crackling and synchronization drift.
