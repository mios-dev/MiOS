<!-- AI-hint: Chapter 27: Shell Configuration and Environment Cascade. Maps configuration overrides bubbling up to login shells. Covers theme configuration and prompt status icons. Documents timezone and UTF-8 locale staging setups. -->

# Chapter 27: Shell Configuration and Environment Cascade

> Part VI: Storage, Network & Web Planes of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Shell Configuration and Environment Cascade** under MiOS.

### <a name="27_environment_defaults_and_precedence"></a>27.Env Defaults and Precedence: Environment Defaults and Precedence

> Path Reference: `/usr/share/doc/mios/manual.md#27_environment_defaults_and_precedence`

#### Overview

Environment variables are resolved through a multi-layer cascade.

## Cascade
1. `~/.config/mios/env` (highest precedence)
2. `/etc/mios/install.env`
3. `/etc/mios/env.d/*.env`
4. `/usr/share/mios/env.defaults` (lowest precedence)

Use `mios-env --explain` to trace key resolution layers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="27_oh_my_posh_prompt_theming"></a>27.Oh My Posh Prompt Theming: Oh My Posh Prompt Theming

> Path Reference: `/usr/share/doc/mios/manual.md#27_oh_my_posh_prompt_theming`

#### Overview

The system shell uses Oh My Posh themes to show system status.

## Themes
- **Prompt**: Configured in [38-oh-my-posh.sh](automation/38-oh-my-posh.sh).
- **Icons**: Displays git status, active model, and CPU usage.
- **Themes File**: Stored inside `/usr/share/mios/shell/`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="27_user_locale_standardization"></a>27.User Locale Standardization: User Locale Standardization

> Path Reference: `/usr/share/doc/mios/manual.md#27_user_locale_standardization`

#### Overview

Standard locale and time formats are staging targets during deployment.

## Settings
- **Locale**: Sets UTF-8 encoding.
- **Timezone**: Set in [30-locale-theme.sh](automation/30-locale-theme.sh).
- **Customizations**: Customized in `mios.toml`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
