# /etc/profile.d/mios-btop.sh
#
# Wrap `btop` so plain invocations land on the canonical MiOS preset
# (preset 4 = proc only, transparent-bg, mios palette).
#
# btop reads $XDG_CONFIG_HOME/btop/btop.conf -> $HOME/.config/btop/
# btop.conf and does NOT fall back to /etc/btop/. Seed the user
# config from /etc/btop/ on first interactive launch so the MiOS
# preset, palette, and theme_background=False all apply.

[ -n "${PS1:-}" ] || return 0

_mios_btop_seed_user_config() {
    local _src=/etc/btop/btop.conf
    local _dst="${HOME:-/root}/.config/btop/btop.conf"
    [ -f "$_src" ] || return 0
    [ -f "$_dst" ] && return 0
    mkdir -p "$(dirname "$_dst")" 2>/dev/null || return 0
    cp "$_src" "$_dst" 2>/dev/null && chmod 0644 "$_dst" 2>/dev/null
    # Also seed the mios theme if not already present in the user dir.
    if [ -f /etc/btop/themes/mios.theme ] && [ ! -f "${HOME:-/root}/.config/btop/themes/mios.theme" ]; then
        mkdir -p "${HOME:-/root}/.config/btop/themes" 2>/dev/null
        cp /etc/btop/themes/mios.theme "${HOME:-/root}/.config/btop/themes/mios.theme" 2>/dev/null
    fi
}
_mios_btop_seed_user_config
unset -f _mios_btop_seed_user_config

if [ -z "${BTOP_CONFIG_DIR:-}" ]; then
    if [ -f "${HOME:-/root}/.config/btop/btop.conf" ]; then
        export BTOP_CONFIG_DIR="${HOME:-/root}/.config/btop"
    elif [ -f /etc/btop/btop.conf ]; then
        export BTOP_CONFIG_DIR=/etc/btop
    fi
fi

btop() {
    local has_preset=0
    for arg in "$@"; do
        case "$arg" in
            -p|--preset|-p[0-9]*|--preset=*) has_preset=1; break ;;
        esac
    done
    if [ $has_preset -eq 0 ]; then
        command btop -p 4 "$@"
    else
        command btop "$@"
    fi
}
