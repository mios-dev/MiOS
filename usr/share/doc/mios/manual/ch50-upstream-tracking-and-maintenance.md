<!-- AI-hint: Chapter 50: Upstream Tracking and Maintenance. Covers checking changes between host and remote overlays. Details Justfile build automation and check goals. Explains checklist targets required to tag release stages. -->

# Chapter 50: Upstream Tracking and Maintenance

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Upstream Tracking and Maintenance** under MiOS.

### <a name="50_upstream_drift_monitor"></a>50.Upstream Drift Monitor: Upstream Drift Monitor

> Path Reference: `/usr/share/doc/mios/manual.md#50_upstream_drift_monitor`

#### Overview

Monitors updates and changes inside upstream base OCI images.

## Details
- **Monitor**: Run [mios-upstream-monitor.sh](tools/mios-upstream-monitor.sh).
- **Checks**: Compares package indexes against target reference lists.
- **Gating**: Detects drift parameters.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="50_justfile_pipeline_automation"></a>50.Justfile Pipeline Automation: Justfile Pipeline Automation

> Path Reference: `/usr/share/doc/mios/manual.md#50_justfile_pipeline_automation`

#### Overview

Automates repetitive build and test targets using Justfile.

## Tasks
- **Build**: Compiles image files using `just build`.
- **Verification**: Runs validations using `just lint`.
- **Packaging**: Packages artifacts using target tags.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="50_release_maturity_runbook"></a>50.Release Maturity Runbook: Release Maturity Runbook

> Path Reference: `/usr/share/doc/mios/manual.md#50_release_maturity_runbook`

#### Overview

Runbook steps guide moving image builds to release configurations.

## Flow
- **Runbook**: Mapped in [maturity-and-release-runbook.md](usr/share/doc/mios/reference/maturity-and-release-runbook.md).
- **Checkpoints**: Verifies tests, SBOM compliance, and signatures.
- **Tagging**: Publishes checked builds under stable tags.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
