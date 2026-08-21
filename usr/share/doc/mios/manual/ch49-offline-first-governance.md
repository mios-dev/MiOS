<!-- AI-hint: Chapter 49: Offline-First Governance. Covers staging local mirror caches inside container build overlay. Details models weights verification loaded under /srv/ai. Explains fallback behaviors resolving missing active gateways. -->

# Chapter 49: Offline-First Governance

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Offline-First Governance** under MiOS.

### <a name="49_local_package_mirrors"></a>49.Local Package Mirrors: Local Package Mirrors

> Path Reference: `/usr/share/doc/mios/manual.md#49_local_package_mirrors`

#### Overview

Configures local update repositories to support air-gapped runtimes.

## Setup
- **Mirrors**: Maps DNF5 to local package directories.
- **Baking**: Packages are pre-loaded during image generation.
- **Rules**: Avoids network access requests on host update calls.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="49_sovereign_model_storage"></a>49.Sovereign Model Storage: Sovereign Model Storage

> Path Reference: `/usr/share/doc/mios/manual.md#49_sovereign_model_storage`

#### Overview

Caches model weights locally to prevent telemetry leaks.

## Storage
- **Weights**: Safely stored inside `/srv/ai/models/`.
- **Gating**: Missing weights prevent inference lanes from starting.
- **Updates**: Models are updated via offline imports.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="49_non_network_degradation_modes"></a>49.Non-Network Degradation Modes: Non-Network Degradation Modes

> Path Reference: `/usr/share/doc/mios/manual.md#49_non_network_degradation_modes`

#### Overview

Ensures local tools remain functional when offline.

## Settings
- **Degradation**: Disables search queries when offline.
- **Core Stacks**: Keeps local inference lanes active.
- **Governance**: Complies with the OFFLINE-FIRST law.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
