<!-- AI-hint: Chapter 42: Kernel Upgrade and Build Pipelines. Covers base image upgrades and validation procedures. Details compilation gating rules verifying module states. Explains bootc-image-builder actions transforming OCI tags. -->

# Chapter 42: Kernel Upgrade and Build Pipelines

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Kernel Upgrade and Build Pipelines** under MiOS.

### <a name="42_stable_lts_kernel_updates"></a>42.Stable LTS Kernel Updates: Stable LTS Kernel Updates

> Path Reference: `/usr/share/doc/mios/manual.md#42_stable_lts_kernel_updates`

#### Overview

Upgrading host kernels relies on stable LTS packages.

## Guidelines
- **Base image**: Kernel packages inherit from uCore base structures.
- **Updates**: Applied transactionally using system image updates.
- **Verification**: Run preflight checks before updating core kernels.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="42_akmod_compilation_guards"></a>42.Akmod Compilation Guards: Akmod Compilation Guards

> Path Reference: `/usr/share/doc/mios/manual.md#42_akmod_compilation_guards`

#### Overview

Guards compilation tasks to prevent boot failures from driver updates.

## Details
- **Guards**: Enabled via [22-akmod-guards.sh](automation/22-akmod-guards.sh).
- **Validation**: Enforces driver binary compilation checks.
- **Actions**: Restores previous functional configurations on failure.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="42_bib_disk_image_generation"></a>42.BIB Disk Image Generation: BIB Disk Image Generation

> Path Reference: `/usr/share/doc/mios/manual.md#42_bib_disk_image_generation`

#### Overview

Compiling images relies on bootc-image-builder (BIB) containers.

## Runtimes
- **BIB target**: Executed inside `just vhdx` / `just raw` targets.
- **Pipeline**: Converts OCI image outputs to UEFI disk configurations.
- **Output**: Writes boot images directly to host directories.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
