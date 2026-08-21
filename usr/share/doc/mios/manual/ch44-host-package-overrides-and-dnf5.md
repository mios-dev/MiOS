<!-- AI-hint: Chapter 44: Host Package Overrides and DNF5. Covers configurations prioritization mappings. Details manual package installations resolving hardware conflicts. Explains troubleshooting procedures for dnf packages errors. -->

# Chapter 44: Host Package Overrides and DNF5

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Host Package Overrides and DNF5** under MiOS.

### <a name="44_usr_vs_etc_overrides"></a>44.USR vs ETC Overrides: USR vs ETC Overrides

> Path Reference: `/usr/share/doc/mios/manual.md#44_usr_vs_etc_overrides`

#### Overview

Manages file priority rules across system overlays.

## Overrides
- **USR**: Contains static default settings.
- **ETC**: Contains host-specific override scripts.
- **Priority**: System units parse ETC files before defaults.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="44_rpm_ostree_exemptions"></a>44.RPM OSTree Exemptions: RPM-OSTree Exemptions

> Path Reference: `/usr/share/doc/mios/manual.md#44_rpm_ostree_exemptions`

#### Overview

Exemptions allow manual packages installation for debugging.

## Rules
- **Access**: Enables installing individual debug packages.
- **Actions**: Restricts packages to target runtime slots.
- **Audit**: Logged in system configuration tracking.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="44_dependency_conflict_resolution"></a>44.Dependency Conflict Resolution: Dependency Conflict Resolution

> Path Reference: `/usr/share/doc/mios/manual.md#44_dependency_conflict_resolution`

#### Overview

Solves dependency conflicts during system builds.

## Troubleshooting
- **Helpers**: uses DNF5 commands with resolution flags.
- **Guards**: Stops builds on unresolvable conflict errors.
- **Testing**: Validates package versions integrity.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
