<!-- AI-hint: Chapter 08: Bootloader and Unified Kernel Images (UKI). Covers compilation and structure of Unified Kernel Images via systemd-ukify. Details kernel module signing, trust models, and cryptographic verification chains. Explains static kernel arguments in kargs.d mapping to VM and GPU isolation. -->

# Chapter 08: Bootloader and Unified Kernel Images (UKI)

> Part III: Core OS Infrastructure of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Bootloader and Unified Kernel Images (UKI)** under MiOS.

### <a name="08_uki_layout_and_baking"></a>08.UKI Layout and Baking: UKI Layout and Baking

> Path Reference: `/usr/share/doc/mios/manual.md#08_uki_layout_and_baking`

#### Overview

Unified Kernel Images (UKIs) combine the Linux kernel, initramfs, and kernel command-line arguments into a single EFI executable. This ensures that the system boot configuration cannot be altered by modifying individual config files on disk.

## Implementation Details
- **Build tool**: Compiled via `systemd-ukify` during the OCI build.
- **Baking script**: Executed by [76-uki-render.sh](automation/76-uki-render.sh).
- **Output**: The output `.efi` image is placed directly in the EFI system partition under `/boot/EFI/Linux/`.
- **Validation**: Verified by `validate-kargs.py` to ensure core arguments are baked into the UKI.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="08_secure_boot_integrity"></a>08.Secure Boot Integrity: Secure Boot Integrity

> Path Reference: `/usr/share/doc/mios/manual.md#08_secure_boot_integrity`

#### Overview

Secure Boot ensures that only cryptographically signed binaries can be executed during the boot phase.

## Validation Chain
1. **UEFI Keys**: The motherboard firmware holds the PK (Platform Key), KEK (Key Exchange Key), and db (Signature Database).
2. **Custom Keys**: MiOS signs custom kernel modules (like ZFS and KVMFR) using a Machine Owner Key (MOK).
3. **MOK Enrollment**: Handled via [enroll-mok.sh](automation/enroll-mok.sh) and [generate-mok-key.sh](automation/generate-mok-key.sh).
4. **Enforcement**: Secure Boot enforces that all drivers compiled at build time are verified against the MOK database before launching the kernel.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="08_kernel_arguments_and_gating"></a>08.Kernel Arguments and Gating: Kernel Arguments and Gating

> Path Reference: `/usr/share/doc/mios/manual.md#08_kernel_arguments_and_gating`

#### Overview

Kernel arguments customize hardware and hypervisor settings during system launch.

## Active Arguments
- **VFIO Isolation**: `intel_iommu=on` or `amd_iommu=on` and `iommu=pt` to enable PCI passthrough.
- **Immutable Root**: `ostree=` and `composefs=` parameters directing ostree to mount `/usr` as a composefs index.
- **Gating**: Verified dynamically during early boot. Incorrect configurations trigger fallback states.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
