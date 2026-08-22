<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures kernel module autoloading for the VFIO stack (vfio, vfio_iommu_type1, vfio_pci) to enable GPU passthrough functionality during system boot.
'MiOS': autoload VFIO stack at boot for GPU passthrough.
kvmfr is explicitly NOT autoloaded - users modprobe it only when running
Looking Glass, to avoid reserving shmem when passthrough isn't in use.

<!-- mios-src:24982ee73cb2 from usr/lib/modules-load.d/mios-vfio.conf:1-4 -->

