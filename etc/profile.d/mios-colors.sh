# AI-hint: Configures the terminal's visual identity by emitting OSC escape sequences to apply the MiOS unified color palette (Hokusai) to interactive shells, ensuring consistent UI branding across supported terminal emulators.
# AI-related: /etc/mios/install.env, /usr/share/mios/mios.toml, mios-colors, mios-sync-env, mios-env
# AI-functions: _mios_osc

[ -t 1 ] || return 0
case "${TERM:-}" in linux|dumb|"") return 0 ;; esac
[ -n "${MIOS_COLORS_APPLIED:-}" ] && return 0

# MIOS_ANSI_* are available below. Bootstrap writes [colors] keys
if [ -r /etc/mios/install.env ]; then
    set -a
    . /etc/mios/install.env 2>/dev/null
    set +a
fi

_mios_osc() { printf '\033]%s;%s\007' "$1" "$2"; }

_a0="${MIOS_ANSI_0_BLACK:-#282262}"
_a1="${MIOS_ANSI_1_RED:-#DC271B}"
_a2="${MIOS_ANSI_2_GREEN:-#3E7765}"
_a3="${MIOS_ANSI_3_YELLOW:-#F35C15}"
_a4="${MIOS_ANSI_4_BLUE:-#1A407F}"
_a5="${MIOS_ANSI_5_MAGENTA:-#734F39}"
_a6="${MIOS_ANSI_6_CYAN:-#B7C9D7}"
_a7="${MIOS_ANSI_7_WHITE:-#E7DFD3}"
_a8="${MIOS_ANSI_8_BRIGHT_BLACK:-#948E8E}"
_a9="${MIOS_ANSI_9_BRIGHT_RED:-#FF6B5C}"
_a10="${MIOS_ANSI_10_BRIGHT_GREEN:-#5FAA8E}"
_a11="${MIOS_ANSI_11_BRIGHT_YELLOW:-#FF8540}"
_a12="${MIOS_ANSI_12_BRIGHT_BLUE:-#3D6BA8}"
_a13="${MIOS_ANSI_13_BRIGHT_MAGENTA:-#9D7660}"
_a14="${MIOS_ANSI_14_BRIGHT_CYAN:-#E0E0E0}"
_a15="${MIOS_ANSI_15_BRIGHT_WHITE:-#FFFFFF}"
_fg="${MIOS_COLOR_FG:-#E7DFD3}"
_bg="${MIOS_COLOR_BG:-#282262}"
_cur="${MIOS_COLOR_CURSOR:-#F35C15}"
_sel="${MIOS_COLOR_ACCENT:-#1A407F}"

_mios_osc 4 "0;${_a0}"
_mios_osc 4 "1;${_a1}"
_mios_osc 4 "2;${_a2}"
_mios_osc 4 "3;${_a3}"
_mios_osc 4 "4;${_a4}"
_mios_osc 4 "5;${_a5}"
_mios_osc 4 "6;${_a6}"
_mios_osc 4 "7;${_a7}"
_mios_osc 4 "8;${_a8}"
_mios_osc 4 "9;${_a9}"
_mios_osc 4 "10;${_a10}"
_mios_osc 4 "11;${_a11}"
_mios_osc 4 "12;${_a12}"
_mios_osc 4 "13;${_a13}"
_mios_osc 4 "14;${_a14}"
_mios_osc 4 "15;${_a15}"

_mios_osc 10 "${_fg}"
_mios_osc 11 "${_bg}"
_mios_osc 12 "${_cur}"
_mios_osc 17 "${_sel}"

unset -f _mios_osc
unset _a0 _a1 _a2 _a3 _a4 _a5 _a6 _a7 _a8 _a9 _a10 _a11 _a12 _a13 _a14 _a15
unset _fg _bg _cur _sel
export MIOS_COLORS_APPLIED=1
