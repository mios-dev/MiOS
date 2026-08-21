<!-- AI-hint: Chapter 29: Web Management and Configurator UI. Covers configuration editing via the static index HTML form. Details how the UI panel maps active container metrics. Explains TOML serialization and service reload hooks. -->

# Chapter 29: Web Management and Configurator UI

> Part VI: Storage, Network & Web Planes of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Web Management and Configurator UI** under MiOS.

### <a name="29_mios_html_toml_editor"></a>29.Mios HTML TOML Editor: MiOS HTML TOML Editor

> Path Reference: `/usr/share/doc/mios/manual.md#29_mios_html_toml_editor`

#### Overview

The configuration dashboard allows graphical form editing of system parameters.

## Details
- **Dashboard**: Shipped in [mios.html](usr/share/mios/configurator/mios.html).
- **Precedence**: Writes updates back to user and host files.
- **Sync**: Triggers `mios-sync-env` to apply updates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="29_host_to_container_portal"></a>29.Host-to-Container Portal: Host-to-Container Portal

> Path Reference: `/usr/share/doc/mios/manual.md#29_host_to_container_portal`

#### Overview

The web panel monitors resource usages and active containers.

## Metrics
- **Resource Monitoring**: Tracks system usage (VRAM, CPU, RAM).
- **Service Management**: Allows quick container restarts.
- **Host View**: Integrates with Cockpit metrics interfaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="29_settings_sync_mechanisms"></a>29.Settings Sync Mechanisms: Settings Sync Mechanisms

> Path Reference: `/usr/share/doc/mios/manual.md#29_settings_sync_mechanisms`

#### Overview

Config settings are synchronized back to target system files on save.

## Mechanisms
- **Sync script**: Syncing handled by Python and PowerShell tools.
- **Update Checks**: Validates configuration integrity before reboot.
- **State Merging**: Merges updates without breaking custom changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
