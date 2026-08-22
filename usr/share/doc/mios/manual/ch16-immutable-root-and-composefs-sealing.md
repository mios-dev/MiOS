<!-- AI-hint: Chapter 16: Immutable Root and Composefs Sealing. Explains composefs structures and /usr partition read-only mounts. Covers system file validation against trusted cryptographic hashes. Describes how upgrades resolve changes between base and current states. -->

# Chapter 16: Immutable Root and Composefs Sealing

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Immutable Root and Composefs Sealing** under MiOS.

### <a name="16_composefs_read_only_mounts"></a>16.Composefs Read-Only Mounts: Composefs Read-Only Mounts

> Path Reference: `/usr/share/doc/mios/manual.md#16_composefs_read_only_mounts`

#### Overview

The system root `/usr` is mounted as a read-only composefs image to prevent run-time modification.

## Features
- **Integrity**: Block device files are read-only at the kernel level.
- **Storage**: System files are stored inside content-addressed OCI indexes.
- **Baking**: Composefs files are rendered during the OCI build.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="16_fs_verity_signature_verification"></a>16.Fs-Verity Signature Verification: fs-verity Signature Verification

> Path Reference: `/usr/share/doc/mios/manual.md#16_fs_verity_signature_verification`

#### Overview

fs-verity protects binaries from offline tampering.

## Operations
- **Hashes**: Cryptographic signature blocks are generated for system files.
- **Verification**: The kernel verifies hashes on open operations.
- **Enforcement**: Any modification to signed binaries triggers block errors.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="16_host_upgrade_reconciliation"></a>16.Host Upgrade Reconciliation: Host Upgrade Reconciliation

> Path Reference: `/usr/share/doc/mios/manual.md#16_host_upgrade_reconciliation`

#### Overview

System updates are applied transactionally on booted hosts.

## Process
1. **Trigger**: Run `bootc upgrade` to fetch updated image layers.
2. **Reconciliation**: System files under `/usr` are replaced by the new image, while host settings in `/etc` are merged.
3. **Activation**: Cleans inactive files and switches to the new index on reboot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
