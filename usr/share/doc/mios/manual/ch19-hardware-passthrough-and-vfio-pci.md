<!-- AI-hint: Chapter 19: Hardware Passthrough and VFIO-PCI. Details binding GPUs to vfio-pci on boot, bypassing host drivers. Explains the XML schema mapping for physical GPU passthrough to guests. Documents driver setups in guest OS to avoid error codes. -->

# Chapter 19: Hardware Passthrough and VFIO-PCI

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Hardware Passthrough and VFIO-PCI** under MiOS.

### <a name="19_gpu_isolation_via_vfio"></a>19.GPU Isolation VFIO: GPU Isolation via VFIO

> Path Reference: `/usr/share/doc/mios/manual.md#19_gpu_isolation_via_vfio`

#### Overview

Isolating host graphics cards allows direct passthrough to virtual guests.

## Methods
- **Driver Bind**: Target GPUs are bound to the `vfio-pci` driver during early boot.
- **Script**: Configured via [rtx4090-vfio-configurator.sh](tools/rtx4090-vfio-configurator.sh).
- **Verification**: Run `vfio-verify.sh` to check GPU binding status.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="19_libvirt_pci_routing"></a>19.Libvirt PCI Routing: Libvirt PCI Routing

> Path Reference: `/usr/share/doc/mios/manual.md#19_libvirt_pci_routing`

#### Overview

PCI routing maps isolated hardware into VM XML configurations.

## XML Structure
- **Device Node**: Defines target host PCI addresses.
- **Guest Bus**: Maps physical hardware to virtual guest PCIe slots.
- **Configuration**: Uses custom XML tags to bypass hypervisor detection.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="19_guest_drivers_enforcement"></a>19.Guest Drivers Enforcement: Guest Drivers Enforcement

> Path Reference: `/usr/share/doc/mios/manual.md#19_guest_drivers_enforcement`

#### Overview

Guest systems require clean driver configurations to utilize passed hardware.

## Tuning
- **Hypervisor Gating**: Hides hypervisor signatures from Windows guests.
- **Driver Setup**: Installs clean driver packages inside guests.
- **Validation**: Checks driver device status after startup.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
