<!-- AI-hint: Chapter 40: System Log Aggregation. Covers sync hooks pulling logs into bootstrap sectors. Details systemd service parameters for log copy tasks. Explains compiling system diagnostics into single archives. -->

# Chapter 40: System Log Aggregation

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **System Log Aggregation** under MiOS.

### <a name="40_journald_sync_to_bootstrap"></a>40.Journald Sync to Bootstrap: Journald Sync to Bootstrap

> Path Reference: `/usr/share/doc/mios/manual.md#40_journald_sync_to_bootstrap`

#### Overview

Copies system journals to bootstrap drives for offline diagnostics.

## Flow
- **Script**: Executed by [log-to-bootstrap.sh](tools/log-to-bootstrap.sh).
- **Logs**: Copies core files, boot output, and services records.
- **Targets**: Mapped directly onto host storage sectors.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="40_log_copy_daemon_configuration"></a>40.Log-Copy Daemon Configuration: Log-Copy Daemon Configuration

> Path Reference: `/usr/share/doc/mios/manual.md#40_log_copy_daemon_configuration`

#### Overview

Configures background daemons to aggregate container logs.

## Setup
- **Unit**: Configured in [50-enable-log-copy-service.sh](automation/50-enable-log-copy-service.sh).
- **Service**: Runs system log synchronization helpers.
- **Storage**: Mapped inside `/var/log/mios/`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="40_diagnostic_log_bundles"></a>40.Diagnostic Log Bundles: Diagnostic Log Bundles

> Path Reference: `/usr/share/doc/mios/manual.md#40_diagnostic_log_bundles`

#### Overview

Assembles diagnostic packages to simplify system troubleshooting.

## Details
- **Bundler**: Bundles active logs, specs, and status variables.
- **Output**: Generates compressed archives.
- **Triggers**: Executed on system health checks failures.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
