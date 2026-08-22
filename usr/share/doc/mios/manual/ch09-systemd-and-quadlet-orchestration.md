<!-- AI-hint: Chapter 09: Systemd and Quadlet Orchestration. Defines user-space daemon layers and systemd-generator permissions configuration. Explains how podman quadlets render systemd unit files on startup. Details service lifecycle states triggered by sync-env or user edits. -->

# Chapter 09: Systemd and Quadlet Orchestration

> Part III: Core OS Infrastructure of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Systemd and Quadlet Orchestration** under MiOS.

### <a name="09_unprivileged_systemd_tiers"></a>09.Unprivileged Systemd Tiers: Unprivileged Systemd Tiers

> Path Reference: `/usr/share/doc/mios/manual.md#09_unprivileged_systemd_tiers`

#### Overview

MiOS uses unprivileged systemd user services to run AI components safely within user space boundaries.

## Architecture
- **User Unit Path**: `/usr/lib/systemd/user/` or `~/.config/systemd/user/`.
- **System-User Map**: Enforced via systemd sysusers templates in [31-user.sh](automation/31-user.sh).
- **Execution Limits**: Systemd user instances map execution boundaries using user namespaces, isolating processes from direct host root access.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="09_quadlet_configuration_syntax"></a>09.Quadlet Configuration Syntax: Quadlet Configuration Syntax

> Path Reference: `/usr/share/doc/mios/manual.md#09_quadlet_configuration_syntax`

#### Overview

Podman Quadlets simplify systemd container management by translating `.container`, `.volume`, and `.network` configuration files into native systemd units on boot.

## Code Conventions
- **Source Paths**: Shipped under `/usr/share/containers/systemd/` or `/etc/containers/systemd/`.
- **Translation Engine**: Parsed by `podman-systemd-generator`.
- **Key Settings**: `[Container]` section specifying images, mounts, and network bridges; `User=mios` and `Group=mios` limits.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="09_dynamic_service_activation"></a>09.Dynamic Service Activation: Dynamic Service Activation

> Path Reference: `/usr/share/doc/mios/manual.md#09_dynamic_service_activation`

#### Overview

Services are dynamically activated, stopped, or scaled based on host states and profile settings.

## Execution Flows
- **Trigger**: Run `mios-sync-env` to regenerate `/etc/mios/install.env`.
- **Service Reload**: Triggers `systemctl daemon-reload` and user daemon reloads to parse environment updates.
- **Gating**: Services check system status indicators (`ConditionPathExists`, etc.) before completing startup.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
