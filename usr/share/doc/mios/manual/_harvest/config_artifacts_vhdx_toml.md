<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the VHDX disk image configuration for Hyper-V targets, specifying user credentials, kernel boot parameters (iommu/nouveau), and filesystem partition sizes for the MiOS guest OS.
bib-configs/vhdx.toml - 'MiOS' v0.3.0
Target: Hyper-V on Windows host (MiOS-2 bare metal + Win11 + RTX 4090)
BIB --type vhd emits VPC/.vhd; CI post-converts to .vhdx via qemu-img convert.

<!-- mios-src:b289fd8c2603 from config/artifacts/vhdx.toml:1-4 -->

