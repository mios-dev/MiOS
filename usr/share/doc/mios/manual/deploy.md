<!-- AI-hint: Manual pages distilled from the source comments of deploy, sanitized, each passage anchored to the comment it came from. -->

# deploy

### MiOS Bare-Metal Direct Installer & Hardware Discovery...

MiOS Bare-Metal Direct Installer & Hardware Discovery Engine.

Orchestrates rapid bare-metal installation of MiOS to physical NVMe/SATA storage in under 3 minutes:
- Auto-discovers and ranks candidate block devices (prioritizing NVMe SSDs > SATA SSDs > HDDs).
- Asserts UEFI boot firmware support (/sys/firmware/efi).
- Enforces strict safety gates preventing accidental destruction of live/booted drives.
- Invokes 'bootc install to-disk' with container rootfs materialization and systemd-boot setup.

<!-- mios-src:1d8cdf6e791c from usr/libexec/mios/deploy/baremetal_install.py:5-13 -->

### Scoring algorithm

Scoring algorithm:
NVMe SSD: +1000
SATA SSD: +700
SATA HDD: +300
Size bonus: +1 per 10GB up to +100
Boot device penalty: score = 0, ineligible
< 32GB penalty: ineligible

<!-- mios-src:bd6ce2ef7258 from usr/libexec/mios/deploy/baremetal_install.py:166-172 -->

### WS-DIFFCYCLE (T-467): Boot Cycle Diff Accrual & Risk...

WS-DIFFCYCLE (T-467): Boot Cycle Diff Accrual & Risk Classifier.
Ingests historical diff snapshots across power cycles, deduplicates entries,
classifies file mutations into Safe vs High-Risk vs Review tiers,
and atomically exports structured audit ledgers for operator inspection and image baking.

<!-- mios-src:315d70b58baa from usr/libexec/mios/deploy/diff_accrual.py:5-10 -->

### WS-DIFFCYCLE (T-466): Pre-Poweroff Diff Snapshot Hook....

WS-DIFFCYCLE (T-466): Pre-Poweroff Diff Snapshot Hook.
Captures all filesystem and configuration modifications across system root (.git == /)
before shutdown, reboot, or kexec events with a strict sub-3s timeout SLA,
redacting all sensitive tokens and writing immutable JSON records.

<!-- mios-src:c7f9ae29c0fa from usr/libexec/mios/deploy/diff_snapshot.py:5-10 -->

### WS-DIFFCYCLE (T-469): Autonomous Background OCI Image...

WS-DIFFCYCLE (T-469): Autonomous Background OCI Image Synthesis Service.
Ingests operator-approved diffs from staged manifests, verifies against the quarantine ledger,
creates structured git commits at repo root (.git == /), builds updated container layers
inside podman-MiOS-DEV with low CPU/IO priority, and stages images via bootc switch --staged.

<!-- mios-src:947ac60aad52 from usr/libexec/mios/deploy/image_bake.py:5-10 -->

### MiOS Bootable Live Hybrid ISO Generator. Produces hybrid...

MiOS Bootable Live Hybrid ISO Generator.

Produces hybrid ISO images supporting dual UEFI (x86_64) and Legacy BIOS firmware boot,
featuring mandatory serial console redirection (console=ttyS0,115200n8) for headless
rackmount servers, BMC/IPMI SoL (Serial-over-LAN), and edge micro-nodes.

Constructs El Torito multi-boot headers and executes/simulates xorriso image mastering.

<!-- mios-src:23def7029b7f from usr/libexec/mios/deploy/iso_generate.py:5-13 -->

### MiOS OCI Image Layer Streaming Extractor. Extracts...

MiOS OCI Image Layer Streaming Extractor.

Extracts multi-gigabyte OCI container image layers directly into the destination
rootfs without 2x disk space overhead. Implements full OCI Image Specification v1
whiteout handling (.wh.<filename> deletions and .wh..wh..opq opaque directory masking),
extended attributes, hardlinks, symlinks, and permission retention.

<!-- mios-src:5b4e0c9a7209 from usr/libexec/mios/deploy/oci_extractor.py:5-12 -->

### MiOS Non-Destructive Dual-Boot Partition & Resize...

MiOS Non-Destructive Dual-Boot Partition & Resize Orchestrator.

Safely audits Windows NTFS volume health (dirty bit check), calculates safe shrink boundaries,
provisions dedicated MiOS XBOOTLDR (if existing ESP < 512MB) and Root partitions (Btrfs/XFS),
and generates systemd-boot loader entries chainloading Windows Boot Manager.

<!-- mios-src:bec987e028f7 from usr/libexec/mios/deploy/partition_dualboot.py:5-11 -->

### quadlet_prewarm.py — T-749 WS-BUILD Build-time Quadlet...

quadlet_prewarm.py — T-749 WS-BUILD
Build-time Quadlet container image pre-warmer and zstd chunked layer optimizer.

Pulls and unpacks enabled Quadlet containers directly into /var/lib/containers/storage
during build time, ensuring sub-100ms offline Day-0 container startup.

<!-- mios-src:c6d5fb8bc641 from usr/libexec/mios/deploy/quadlet_prewarm.py:4-10 -->

### self_replicate.py — T-966 WS-HCI Autonomous...

self_replicate.py — T-966 WS-HCI
Autonomous self-replication daemon and podman-MiOS-DEV build pipeline trigger.

Inspects local git tree changes, triggers containerized bootc-image-builder (BIB)
compilation in podman-MiOS-DEV, verifies cryptographic image digest signatures,
and stages hot-swapped OCI artifacts for atomic bootc switch.

<!-- mios-src:c1de9b3f8117 from usr/libexec/mios/deploy/self_replicate.py:5-12 -->

### MiOS Storage Health, Alignment & Integrity Verification...

MiOS Storage Health, Alignment & Integrity Verification Engine.

Performs critical hardware and filesystem integrity checks:
1. 4K / 1MB Partition Alignment: Verifies that starting LBAs are aligned to physical
   flash erase blocks to eliminate write amplification and degradation.
2. Streaming Block Read-Back Verification: Computes streaming SHA-256 digests over
   written blocks and matches against source ISO/raw images.
3. Counterfeit / Fake Flash Detection: Tests for wrapped memory controller registers
   and ghost storage via exponential boundary marker probes.

<!-- mios-src:4d7169f97cde from usr/libexec/mios/deploy/storage_verify.py:5-15 -->

### MiOS-Cat Removable USB Media Partition Formatter....

MiOS-Cat Removable USB Media Partition Formatter.

Provisions removable USB media with a hybrid GPT/MBR partition layout:
- Partition 1 (MiOS-Repo): FAT32 filesystem, ESP GUID (c12a7328-f81f-11d2-ba4b-00a0c93ec93b),
  legacy MBR 0xEF, boot/esp flags for UEFI & BIOS firmware bootloaders.
- Partition 2 (MiOS-Data): exFAT (or ext4) filesystem, Basic Data GUID
  (ebd0a0a2-b9e5-4433-87c0-68b6b72699c7), legacy MBR 0x07, storing OCI layers,
  AI model weights, and staging payloads.

Enforces strict safety invariants preventing inadvertent wiping of internal or OS drives.

<!-- mios-src:0ff462459357 from usr/libexec/mios/deploy/usb_format.py:5-16 -->
