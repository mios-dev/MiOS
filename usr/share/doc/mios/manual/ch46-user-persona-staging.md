<!-- AI-hint: Chapter 46: User Persona Staging. Covers default accounts, credentials, and settings groups. Details template overlay merging home profile files. Explains isolation policies across different accounts. -->

# Chapter 46: User Persona Staging

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **User Persona Staging** under MiOS.

### <a name="46_default_user_creation"></a>46.Default User Creation: Default User Creation

> Path Reference: `/usr/share/doc/mios/manual.md#46_default_user_creation`

#### Overview

Sets up user accounts and home layouts.

## Configurations
- **Creation**: Executed via sysusers configs.
- **Script**: Handled by [11-user.sh](automation/11-user.sh).
- **Rights**: Adds user accounts to virtual and container groups.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="46_stagings_dotfiles_overlay"></a>46.Stagings Dotfiles Overlay: Stagings Dotfiles Overlay

> Path Reference: `/usr/share/doc/mios/manual.md#46_stagings_dotfiles_overlay`

#### Overview

Deploys template configuration files to user home folders.

## Flow
- **Dotfiles**: Seeds user folders (e.g. `~/.config/mios/`).
- **Templates**: Sourced from `/etc/skel/`.
- **Integrity**: Merges parameters without destroying custom changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="46_multi_user_sandboxes"></a>46.Multi-User Sandboxes: Multi-User Sandboxes

> Path Reference: `/usr/share/doc/mios/manual.md#46_multi_user_sandboxes`

#### Overview

Isolates configuration environments across different user accounts.

## Details
- **Sandboxing**: Confines user environments.
- **Groups**: Restricts group permissions.
- **Access**: Prevents cross-user configuration editing.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
