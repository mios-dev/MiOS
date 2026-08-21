<!-- AI-hint: Chapter 41: Machine Owner Key Management. Covers generating secure build-keys inside automation. Details UEFI enrollment prompts triggered on boots. Explains dynamic module signatures added on kernel upgrades. -->

# Chapter 41: Machine Owner Key Management

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Machine Owner Key Management** under MiOS.

### <a name="41_private_key_generation"></a>41.Private Key Generation: Private Key Generation

> Path Reference: `/usr/share/doc/mios/manual.md#41_private_key_generation`

#### Overview

Generates secure signature keys for custom kernel drivers.

## Details
- **Keys**: Cryptographic keys are generated inside automation layers.
- **Script**: Managed via [generate-mok-key.sh](automation/generate-mok-key.sh).
- **Storage**: Keys are isolated in root-only directories.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="41_secure_boot_enrollment_flow"></a>41.Secure Boot Enrollment Flow: Secure Boot Enrollment Flow

> Path Reference: `/usr/share/doc/mios/manual.md#41_secure_boot_enrollment_flow`

#### Overview

Enrolls Machine Owner Keys (MOK) inside host firmware.

## Flow
1. **Trigger**: Run [enroll-mok.sh](automation/enroll-mok.sh).
2. **Registration**: Imports certificates to system structures.
3. **Enrollment**: Prompts enrollment on subsequent reboot.
4. **Validation**: Verified by Secure Boot on driver loading.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="41_automatic_module_signing"></a>41.Automatic Module Signing: Automatic Module Signing

> Path Reference: `/usr/share/doc/mios/manual.md#41_automatic_module_signing`

#### Overview

Signs compiled driver binaries automatically during kernel upgrades.

## Processes
- **Compilation**: Triggers driver compile actions on kernel changes.
- **Signing**: Signs binaries using registered MOK keys.
- **Verification**: Confirms signed driver loading logs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
