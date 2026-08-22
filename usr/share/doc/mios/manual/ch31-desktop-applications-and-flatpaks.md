<!-- AI-hint: Chapter 31: Desktop Applications and Flatpaks. Covers pre-downloading and staging Flatpaks inside the image. Explains locking Flatpak permissions using Flatseal overrides. Details sync hooks registering menus and MIME shortcuts. -->

# Chapter 31: Desktop Applications and Flatpaks

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Desktop Applications and Flatpaks** under MiOS.

### <a name="31_declarative_flatpak_bake"></a>31.Declarative Flatpak Bake: Declarative Flatpak Bake

> Path Reference: `/usr/share/doc/mios/manual.md#31_declarative_flatpak_bake`

#### Overview

Flatpaks are defined in system configs and pre-downloaded to reduce setup times.

## Setup
- **Declarations**: Listed in `mios.toml` under `[flatpaks]`.
- **Bake Script**: Configured in [40-flatpak-bake.sh](automation/40-flatpak-bake.sh).
- **Details**: Pre-downloads application runtimes into the image storage.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="31_application_permissions_gating"></a>31.Application Permissions Gating: Application Permissions Gating

> Path Reference: `/usr/share/doc/mios/manual.md#31_application_permissions_gating`

#### Overview

Flatpak permissions are confined using Flatseal profiles.

## Hardening
- **Confinement**: Restricts access to host files, network, and sockets.
- **Exceptions**: Allows necessary GPU access paths.
- **Overrides**: Controlled via custom scripts on first boot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="31_desktop_shortcuts_sync"></a>31.Desktop Shortcuts Sync: Desktop Shortcuts Sync

> Path Reference: `/usr/share/doc/mios/manual.md#31_desktop_shortcuts_sync`

#### Overview

Syncs application icons and shortcuts to the GNOME desktop launcher menu.

## Flow
- **Script**: Managed via [refresh-flatpak-shortcuts.ps1](tools/refresh-flatpak-shortcuts.ps1).
- **Sync**: Maps application desktop files to target directory folders.
- **Updates**: Refreshed dynamically on configuration changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
