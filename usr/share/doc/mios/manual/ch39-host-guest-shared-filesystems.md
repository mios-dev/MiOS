<!-- AI-hint: Chapter 39: Host-Guest Shared Filesystems. Covers high-speed file sharing cache configurations. Details exposing system paths inside guest virtual overlays. Explains UID/GID mappings translation across OS barriers. -->

# Chapter 39: Host-Guest Shared Filesystems

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Host-Guest Shared Filesystems** under MiOS.

### <a name="39_virtiofs_performance_tuning"></a>39.Virtiofs Performance Tuning: Virtiofs Performance Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#39_virtiofs_performance_tuning`

#### Overview

Tuning virtiofs settings allows high-speed file sharing with guests.

## Setup
- **Mounts**: Exposes host folders using XML templates.
- **Caching**: Configures high-performance host caches.
- **Tuning**: Optimizes thread limits inside libvirt.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="39_shared_directories_overlay"></a>39.Shared Directories Overlay: Shared Directories Overlay

> Path Reference: `/usr/share/doc/mios/manual.md#39_shared_directories_overlay`

#### Overview

Overlay folders expose host configurations to guest runtimes.

## Flow
- **Overlay**: Exposes `/usr/share/` and guest dotfiles.
- **Sandboxing**: Restricts write access inside guests.
- **Conventions**: Maps locations securely inside hypervisor targets.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="39_permission_translation_models"></a>39.Permission Translation Models: Permission Translation Models

> Path Reference: `/usr/share/doc/mios/manual.md#39_permission_translation_models`

#### Overview

Maps user IDs across host and guest environments.

## Details
- **Mapping**: Translates guest UIDs to matching host accounts.
- **Security**: Prevents guest root tasks from escaping permissions.
- **Verification**: Validates folder access credentials.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
