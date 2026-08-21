<!-- AI-hint: Chapter 33: Sandboxed Execution and Coder Sandbox. Covers configuring unprivileged containers for code interpretation. Details how policies restrict container sandbox processes. Explains output validation and script execution controls. -->

# Chapter 33: Sandboxed Execution and Coder Sandbox

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Sandboxed Execution and Coder Sandbox** under MiOS.

### <a name="33_coder_sandbox_quadlet"></a>33.Coder Sandbox Quadlet: Coder Sandbox Quadlet

> Path Reference: `/usr/share/doc/mios/manual.md#33_coder_sandbox_quadlet`

#### Overview

Confines untrusted coding tasks within rootless containers.

## Settings
- **Service**: Mapped in `mios-coderun-sandbox@` Quadlet.
- **User**: Runs with unprivileged user namespace limits.
- **Bridges**: Disables host networks to prevent outbound leaks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="33_selinux_sandbox_policies"></a>33.SELinux Sandbox Policies: SELinux Sandbox Policies

> Path Reference: `/usr/share/doc/mios/manual.md#33_selinux_sandbox_policies`

#### Overview

Custom SELinux profiles prevent sandbox escape actions.

## Policies
- **Rules**: Applied on first boot configuration.
- **Bounds**: Blocks container escape vulnerabilities.
- **Verification**: Logs violations inside audit files.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="33_safe_code_interpretation"></a>33.Safe Code Interpretation: Safe Code Interpretation

> Path Reference: `/usr/share/doc/mios/manual.md#33_safe_code_interpretation`

#### Overview

Validates code actions and sanitizes script outputs securely.

## Methods
- **Sanitizer**: Filters execution outputs to remove credentials.
- **Validation**: Enforces strict timeout limits on executions.
- **Logs**: Processes are logged in system containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
