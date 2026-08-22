<!-- AI-hint: Chapter 34: Identity Management and FreeIPA. Covers configuring FreeIPA libraries inside Fedora overlay. Details staging user and system accounts prior to install. Explains automatic domain enrollment on first boot. -->

# Chapter 34: Identity Management and FreeIPA

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Identity Management and FreeIPA** under MiOS.

### <a name="34_freeipa_client_configuration"></a>34.FreeIPA Client Configuration: FreeIPA Client Configuration

> Path Reference: `/usr/share/doc/mios/manual.md#34_freeipa_client_configuration`

#### Overview

Resolves host client authentication with central FreeIPA domains.

## Details
- **Script**: Staged via [22-freeipa-client.sh](automation/22-freeipa-client.sh).
- **Client**: Integrates SSSD services inside Fedora core layers.
- **Policies**: Handles identity resolving and domain settings.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="34_enforced_user_sysusers"></a>34.Enforced User Sysusers: Enforced User Sysusers

> Path Reference: `/usr/share/doc/mios/manual.md#34_enforced_user_sysusers`

#### Overview

Sysusers definitions pre-stage user and system accounts prior to install.

## Rules
- **Templates**: Stored under `/usr/lib/sysusers.d/*.conf`.
- **System Accounts**: Configures IDs for database and daemon tasks.
- **Integrity**: Prevents changes during deployment overlays.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="34_domain_join_automation"></a>34.Domain Join Automation: Domain Join Automation

> Path Reference: `/usr/share/doc/mios/manual.md#34_domain_join_automation`

#### Overview

Automates joining host systems to corporate domains.

## Flow
- **Execution**: Connects to IPA servers using OIDC tokens.
- **Certificates**: Generates secure host certificates on setup.
- **Renewals**: Handles automatic credential ticket updates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
