<!-- AI-hint: Chapter 38: Remote Desktop and GNOME GRD. Covers running GNOME inside headless Wayland sessions. Details TLS encryption and user credential checks. Documents setting up virtual display outputs on headless hosts. -->

# Chapter 38: Remote Desktop and GNOME GRD

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Remote Desktop and GNOME GRD** under MiOS.

### <a name="38_remote_wayland_sessions"></a>38.Remote Wayland Sessions: Remote Wayland Sessions

> Path Reference: `/usr/share/doc/mios/manual.md#38_remote_wayland_sessions`

#### Overview

Enables GUI remote management when running headless.

## Details
- **Script**: Configured via [26-gnome-remote-desktop.sh](automation/26-gnome-remote-desktop.sh).
- **Engine**: Integrates with GNOME Remote Desktop.
- **Bridges**: Exposes Wayland displays on ports.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="38_secure_rdp_authentication"></a>38.Secure RDP Authentication: Secure RDP Authentication

> Path Reference: `/usr/share/doc/mios/manual.md#38_secure_rdp_authentication`

#### Overview

Secures remote display sessions using TLS certificates.

## Setup
- **Credentials**: Configures certs and local PAM hooks.
- **Rules**: Restricts RDP connection requests to authorized IP slots.
- **Auditing**: Session access is logged in the system records.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="38_headless_desktop_toggle"></a>38.Headless Desktop Toggle: Headless Desktop Toggle

> Path Reference: `/usr/share/doc/mios/manual.md#38_headless_desktop_toggle`

#### Overview

Allows toggling display signals for virtual desktop environments.

## Actions
- **Toggle tool**: Executed via [mios-toggle-headless](automation/mios-toggle-headless).
- **Resolution**: Sets virtual display limits.
- **Tuning**: Optimizes screen frame buffers to save VRAM.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
