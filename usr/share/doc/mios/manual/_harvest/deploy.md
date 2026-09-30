<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: NVMe hardware discovery and...

!/usr/bin/env python3
AI-hint: NVMe hardware discovery and automated bootc install to-disk baremetal deployer
AI-related: tests/test-baremetal-install.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/usb_format.py
AI-functions: BareMetalInstaller, DiskCandidate, HardwareDiscoveryEngine, install_to_disk

<!-- mios-src:f0f3200ec8ca from usr/libexec/mios/deploy/baremetal_install.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Boot cycle diff accrual...

!/usr/bin/env python3
AI-hint: Boot cycle diff accrual analyzer classifying safe vs high-risk modifications and emitting audit ledgers.
AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md, tests/test-diff-accrual.py
AI-functions: DiffAccrualEngine, classify_risk, classify_path, redact_secrets, atomic_write_json, snapshot_diffs, accrue_diffs, main

<!-- mios-src:50b89e0378b3 from usr/libexec/mios/deploy/diff_accrual.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Pre-shutdown diff...

!/usr/bin/env python3
AI-hint: Pre-shutdown diff snapshotting hook capturing git status, modified configs, and skills with sub-3s SLA.
AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md, tests/test-diff-snapshot.py
AI-functions: DiffSnapshotEngine, redact_secrets, classify_risk, atomic_write_json, main

<!-- mios-src:f1b186c9f307 from usr/libexec/mios/deploy/diff_snapshot.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Autonomous background OCI...

!/usr/bin/env python3
AI-hint: Autonomous background OCI image synthesis service rolling approved diffs into new immutable bootc images.
AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md, tests/test-image-bake.py
AI-functions: ImageBakeEngine, atomic_write_json, main

<!-- mios-src:2bbb427aff8a from usr/libexec/mios/deploy/image_bake.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Bootable live hybrid ISO...

!/usr/bin/env python3
AI-hint: Bootable live hybrid ISO generator with dual UEFI/BIOS and serial IPMI console
AI-related: tests/test-iso-generate.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
AI-functions: IsoGeneratorEngine, IsoStructurePlan, generate_bootable_iso

<!-- mios-src:b197421b6321 from usr/libexec/mios/deploy/iso_generate.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Streaming OCI image layer...

!/usr/bin/env python3
AI-hint: Streaming OCI image layer unpack and rootfs extractor with whiteout handling
AI-related: tests/test-oci-extractor.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
AI-functions: OciExtractorEngine, LayerInfo, WhiteoutHandler, extract_oci_layers

<!-- mios-src:bc28c68b8d1f from usr/libexec/mios/deploy/oci_extractor.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Non-destructive Windows NTFS...

!/usr/bin/env python3
AI-hint: Non-destructive Windows NTFS partition shrink and dual-boot ESP/Root provisioning
AI-related: tests/test-partition-dualboot.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
AI-functions: DualBootPartitionEngine, PartitionPlan, NtfsHealthStatus, plan_dualboot_layout

<!-- mios-src:567a0ac1d880 from usr/libexec/mios/deploy/partition_dualboot.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Flash drive block integrity...

!/usr/bin/env python3
AI-hint: Flash drive block integrity, 4K partition alignment, and counterfeit fake-capacity detection
AI-related: tests/test-storage-verify.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/usb_format.py
AI-functions: StorageVerifierEngine, AlignmentReport, FakeCapacityReport, verify_storage_target

<!-- mios-src:ba5328220ca6 from usr/libexec/mios/deploy/storage_verify.py:1-4 -->

### !/usr/bin/env python3 AI-hint: MiOS-Cat USB hybrid GPT/MBR...

!/usr/bin/env python3
AI-hint: MiOS-Cat USB hybrid GPT/MBR partition formatter with FAT32 EFI + exFAT Data
AI-related: tests/test-usb-format.py, usr/share/mios/mios.toml, cat/MiOS-Cat.sh
AI-functions: UsbFormatEngine, PartitionInfo, DeviceSafetyCheck, format_usb_media

<!-- mios-src:05cc967c63ee from usr/libexec/mios/deploy/usb_format.py:1-4 -->
