<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the terminal's visual identity by emitting OSC escape sequences to apply the MiOS unified color palette (Hokusai) to interactive shells, ensuring consistent UI branding across supported terminal emulators.
AI-related: /etc/mios/install.env, /usr/share/mios/mios.toml, mios-colors, mios-sync-env, mios-env
AI-functions: _mios_osc
/etc/profile.d/mios-colors.sh

Repaint the operator's terminal to the MiOS unified palette
(Hokusai + operator neutrals) on every interactive shell start.
Works on every emulator that honors the OSC color escape sequences:
xterm, Konsole, Ptyxis, GNOME Terminal, kitty, alacritty, foot,
Windows Terminal (via WSL), Ptyxis-via-WSLg, ssh sessions, etc.

Sequences emitted:
  OSC 4 ; <slot> ; <hex>          set ANSI 16-color palette slot
  OSC 10 ; <hex>                  default foreground
  OSC 11 ; <hex>                  default background
  OSC 12 ; <hex>                  cursor color
  OSC 17 ; <hex>                  highlight (selected) background

Skipped on:
  - non-interactive shells (cron, scripts, sudo non-tty)
  - Linux console (TERM=linux) -- tty0 has its own kernel palette
    wired via /etc/vconsole.conf; OSC4 doesn't apply there
  - Already-applied sessions (idempotent via $MIOS_COLORS_APPLIED)

Palette is the SSOT in mios.toml [colors]; sync via `mios-sync-env`
if the operator overrides via the configurator HTML.

<!-- mios-src:1a10edec349a from etc/profile.d/mios-colors.sh:1-26 -->

