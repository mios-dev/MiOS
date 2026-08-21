<!-- AI-hint: Chapter 47: Virtual Machine Templates. Details template variables enabling vTPM and Secure Boot. Covers automating guest staging using init data. Explains hypervisor guest actions executed via virsh. -->

# Chapter 47: Virtual Machine Templates

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Virtual Machine Templates** under MiOS.

### <a name="47_windows_11_secureboot_xml"></a>47.Windows 11 SecureBoot XML: Windows 11 SecureBoot XML

> Path Reference: `/usr/share/doc/mios/manual.md#47_windows_11_secureboot_xml`

#### Overview

Provides VM templates meeting Windows 11 Secure Boot specifications.

## Template
- **File**: Shipped in [win11-secureboot-template.xml](tools/win11-secureboot-template.xml).
- **Features**: Includes vTPM, SecureBoot, and UEFI firmware settings.
- **Isolation**: Optimizes settings for VFIO passthrough.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="47_linux_guest_cloud_init"></a>47.Linux Guest Cloud-Init: Linux Guest Cloud-Init

> Path Reference: `/usr/share/doc/mios/manual.md#47_linux_guest_cloud_init`

#### Overview

Deploy virtual machines using pre-configured cloud-init settings.

## Operations
- **Cloud-Init**: Staged inside default VM tools.
- **Setup**: Configures default networks, accounts, and keys.
- **Tuning**: Speeds up guest environment provisioning.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="47_vm_lifecycle_management"></a>47.VM Lifecycle Management: VM Lifecycle Management

> Path Reference: `/usr/share/doc/mios/manual.md#47_vm_lifecycle_management`

#### Overview

Manages virtual guests using command tools.

## Actions
- **CLI**: Executed using libvirt's `virsh` tools.
- **States**: Starts, stops, and scales VM instances.
- **Tuning**: Configured in VM xml configurations.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
