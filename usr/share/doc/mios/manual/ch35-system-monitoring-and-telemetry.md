<!-- AI-hint: Chapter 35: System Monitoring and Telemetry. Covers collecting CPU, RAM, and GPU stats via node-exporters. Details tracking query duration, tokens, and routing lanes. Maps visual dashboards for monitoring resource use. -->

# Chapter 35: System Monitoring and Telemetry

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **System Monitoring and Telemetry** under MiOS.

### <a name="35_prometheus_exporter_setup"></a>35.Prometheus Exporter Setup: Prometheus Exporter Setup

> Path Reference: `/usr/share/doc/mios/manual.md#35_prometheus_exporter_setup`

#### Overview

Exporters collect system metrics from physical hardware.

## Settings
- **Exporters**: System and GPU metrics collection daemons.
- **Ports**: Exposes metrics on localhost ports.
- **Frequency**: Configured to scrape resources at regular intervals.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="35_ai_gateway_telemetry"></a>35.AI Gateway Telemetry: AI Gateway Telemetry

> Path Reference: `/usr/share/doc/mios/manual.md#35_ai_gateway_telemetry`

#### Overview

Logs query times, token counts, and routing states.

## Diagnostics
- **Recording**: Mapped inside the Postgres log tables.
- **Metrics**: Logs tokens per second and model swap speeds.
- **Anonymization**: Filters queries to protect credentials.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="35_grafana_dashboard_profiles"></a>35.Grafana Dashboard Profiles: Grafana_Dashboard_Profiles

> Path Reference: `/usr/share/doc/mios/manual.md#35_grafana_dashboard_profiles`

#### Overview

Configures dashboards to monitor system and AI workloads.

## Details
- **Widgets**: Mapped inside cockpit or local dashboards.
- **Alerts**: Triggers notifications on VRAM threshold limits.
- **Tuning**: Configured in system monitoring profiles.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
