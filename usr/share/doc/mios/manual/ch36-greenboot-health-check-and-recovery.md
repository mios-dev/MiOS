<!-- AI-hint: Chapter 36: Greenboot Health Check and Recovery. Covers greenboot scripts verifying service states. Explains atomic image swap checks triggered on boot failures. Documents dynamic cleanup tasks executed during recoveries. -->

# Chapter 36: Greenboot Health Check and Recovery

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Greenboot Health Check and Recovery** under MiOS.

### <a name="36_automatic_os_health_checks"></a>36.Automatic OS Health Checks: Automatic OS Health Checks

> Path Reference: `/usr/share/doc/mios/manual.md#36_automatic_os_health_checks`

#### Overview

Greenboot verifies service status after system upgrades.

## Flow
- **Script**: Checked in [46-greenboot.sh](automation/46-greenboot.sh).
- **Actions**: Checks core components (systemd, drivers, AI gateways).
- **Timing**: Enforces timeout limits for checks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="36_rollback_trigger_policies"></a>36.Rollback Trigger Policies: Rollback Trigger Policies

> Path Reference: `/usr/share/doc/mios/manual.md#36_rollback_trigger_policies`

#### Overview

Rollback triggers swap root partition indexes back to working slots on boot failures.

## Policies
- **Threshold**: Triggers rollback after 3 failed boot attempts.
- **Actions**: Atomic switch of boot partition variables.
- **Logs**: Records rollback events inside bootstrap logs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="36_recovery_state_scripts"></a>36.Recovery State Scripts: Recovery State Scripts

> Path Reference: `/usr/share/doc/mios/manual.md#36_recovery_state_scripts`

#### Overview

Automated scripts attempt self-repair tasks on service start failures.

## Settings
- **Scripts**: Mapped in `/etc/greenboot/red.d/`.
- **Actions**: Restarts containers and purges stale caches.
- **Controls**: Logs status diagnostics for operator review.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
