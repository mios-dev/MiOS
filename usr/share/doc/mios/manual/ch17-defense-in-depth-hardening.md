<!-- AI-hint: Chapter 17: Defense in Depth Hardening. Covers telemetry monitoring, IP bans, and custom local parsers. Details binary execution blocking on unauthorized directories. Explains protection policies against rogue USB devices. -->

# Chapter 17: Defense in Depth Hardening

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Defense in Depth Hardening** under MiOS.

### <a name="17_crowdsec_intrusion_prevention"></a>17.CrowdSec Intrusion Prevention: CrowdSec Intrusion Prevention

> Path Reference: `/usr/share/doc/mios/manual.md#17_crowdsec_intrusion_prevention`

#### Overview

CrowdSec monitors local logs to detect threat activities.

## Settings
- **Logs**: Parses system logs, SSH, and container logs.
- **Enforcement**: Blocks attackers using local firewalld rules.
- **Sovereign Mode**: Runs offline without requiring cloud accounts.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="17_fapolicyd_application_whitelisting"></a>17.Fapolicyd Application Whitelisting: fapolicyd Application Whitelisting

> Path Reference: `/usr/share/doc/mios/manual.md#17_fapolicyd_application_whitelisting`

#### Overview

fapolicyd blocks execution of untrusted scripts and binaries.

## Rules
- **Policy**: Denies execution of all files outside `/usr` and trusted directories.
- **Paths**: Blocks executions inside `/tmp`, `/var`, or user home directories.
- **Trust DB**: Managed in `/etc/fapolicyd/fapolicyd.trust`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="17_usbguard_hardware_control"></a>17.USBGuard Hardware Control: USBGuard Hardware Control

> Path Reference: `/usr/share/doc/mios/manual.md#17_usbguard_hardware_control`

#### Overview

USBGuard safeguards against hardware security exploits.

## Details
- **Policy**: Blocks unauthorized USB devices at connection.
- **Rules**: Allows only authorized USB controllers and keyboards.
- **Logs**: Hardware actions are logged in system journals.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
