# /etc/profile.d/mios-colors.sh
#
# Repaint the operator's terminal to the MiOS unified palette
# (Hokusai + operator neutrals) on every interactive shell start.
# Works on every emulator that honors the OSC color escape sequences:
# xterm, Konsole, Ptyxis, GNOME Terminal, kitty, alacritty, foot,
# Windows Terminal (via WSL), Ptyxis-via-WSLg, ssh sessions, etc.
#
# Sequences emitted:
#   OSC 4 ; <slot> ; <hex>          set ANSI 16-color palette slot
#   OSC 10 ; <hex>                  default foreground
#   OSC 11 ; <hex>                  default background
#   OSC 12 ; <hex>                  cursor color
#   OSC 17 ; <hex>                  highlight (selected) background
#
# Skipped on:
#   - non-interactive shells (cron, scripts, sudo non-tty)
#   - Linux console (TERM=linux) -- tty0 has its own kernel palette
#     wired via /etc/vconsole.conf; OSC4 doesn't apply there
#   - Already-applied sessions (idempotent via $MIOS_COLORS_APPLIED)
#
# Palette is the SSOT in mios.toml [colors]; sync via `mios-sync-env`
# if the operator overrides via the configurator HTML.

[ -t 1 ] || return 0
case "${TERM:-}" in linux|dumb|"") return 0 ;; esac
[ -n "${MIOS_COLORS_APPLIED:-}" ] && return 0

# Helper: emit OSC <code>;<value> with the trailing BEL terminator.
_mios_osc() { printf '\033]%s;%s\007' "$1" "$2"; }

# ── ANSI 16-color slots (OSC 4 ; <0..15> ; <#rgb>) ────────────────────────
_mios_osc 4 '0;#282262'   # 0 black             -- deep indigo
_mios_osc 4 '1;#DC271B'   # 1 red               -- coral red
_mios_osc 4 '2;#3E7765'   # 2 green             -- wave green
_mios_osc 4 '3;#F35C15'   # 3 yellow            -- sunset orange (warning)
_mios_osc 4 '4;#1A407F'   # 4 blue              -- operator blue
_mios_osc 4 '5;#734F39'   # 5 magenta           -- brown
_mios_osc 4 '6;#B7C9D7'   # 6 cyan              -- pale blue-grey
_mios_osc 4 '7;#E7DFD3'   # 7 white             -- cream
_mios_osc 4 '8;#948E8E'   # 8 bright black      -- warm grey
_mios_osc 4 '9;#FF6B5C'   # 9 bright red        -- lighter coral
_mios_osc 4 '10;#5FAA8E'  # 10 bright green     -- lighter wave-green
_mios_osc 4 '11;#FF8540'  # 11 bright yellow    -- lighter sunset
_mios_osc 4 '12;#3D6BA8'  # 12 bright blue      -- lighter operator blue
_mios_osc 4 '13;#9D7660'  # 13 bright magenta   -- lighter brown
_mios_osc 4 '14;#E0E0E0'  # 14 bright cyan      -- operator silver
_mios_osc 4 '15;#FFFFFF'  # 15 bright white     -- pure white

# ── Defaults (foreground / background / cursor / highlight) ───────────────
_mios_osc 10 '#E7DFD3'   # default fg -- cream
_mios_osc 11 '#282262'   # default bg -- deep indigo
_mios_osc 12 '#F35C15'   # cursor     -- sunset orange (high contrast)
_mios_osc 17 '#1A407F'   # selection  -- operator blue (readable both ways)

unset -f _mios_osc
export MIOS_COLORS_APPLIED=1
