<!-- AI-hint: Chapter 03: System Configuration and Governance. Explains the management of packages, AI lanes, and quadlets centrally via mios.toml. Maps configuration resolution precedence across vendor, host, and user levels. Documents DNF5 integration, flatpak configurations, and the separation of PACKAGES.md. -->

# Chapter 03: System Configuration and Governance

> Part I: Foundations & Philosophy of the [MiOS manual](../manual.md).

This chapter covers the documentation for **System Configuration and Governance** under MiOS.

### <a name="03_single_source_of_truth"></a>03.Single Source Of Truth: Single Source of Truth

> Path Reference: `/usr/share/doc/mios/manual.md#03_single_source_of_truth`

#### Overview

System configuration on MiOS is managed centrally via one configuration format: `mios.toml`.

This file controls user parameters, package selections, Flatpaks, AI stack configurations, and hardware allocations. A graphical configurator tool is shipped at [mios.html](usr/share/mios/configurator/mios.html). Running `sudo mios-sync-env` refreshes `/etc/mios/install.env` to align systemd environment variables.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 20** (Buildah): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L78)
- **Row 21** (Skopeo): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L79)
- **Row 22** (dnf5): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L80)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="03_three_layer_override_model"></a>03.Three Layer Override Model: Three-Layer Override Model

> Path Reference: `/usr/share/doc/mios/manual.md#03_three_layer_override_model`

#### Overview

Configuration resolution follows a strict three-layer precedence model to ensure system immutable integrity while allowing flexible per-user settings:

1. `~/.config/mios/mios.toml` -- per-user override (highest precedence)
2. `/etc/mios/mios.toml` -- host/admin override (shipped by bootstrap)
3. `/usr/share/mios/mios.toml` -- vendor defaults (shipped by image, lowest precedence)

All settings are merged key-by-key at runtime, where higher layers supersede lower layers.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 23** (bootc-image-builder (BIB)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L81)
- **Row 24** (image-builder-cli): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L82)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="03_declarative_package_management"></a>03.Declarative Package Management: Declarative Package Management

> Path Reference: `/usr/share/doc/mios/manual.md#03_declarative_package_management`

#### Overview

To ensure that the root remains clean and deterministic, packages are declared statically in the system configuration.

- **System Packages**: Declared in `/usr/share/mios/mios.toml` under `[packages.<section>].pkgs` and installed using DNF5.
- **Flatpaks**: Desktop GUI apps are declared in the same file under `[flatpaks]` and baked into the image Flatpak store.
- **Package Rationale**: Human-readable descriptions are documented in [PACKAGES.md](usr/share/doc/mios/reference/PACKAGES.md).

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 25** (rechunk): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L83)
- **Row 26** (Anaconda): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L84)
- **Row 27** (Renovate): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L85)
- **Row 28** (GitHub Actions): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L86)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
