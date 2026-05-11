# /etc/profile.d/mios-btop.sh
#
# Wrap `btop` so plain invocations land on the canonical MiOS preset
# (preset 3 = cpu+mem full, transparent-bg, mios palette). Operator
# 2026-05-10: "btop -p 3 is the correct profile -- make it default
# launch to preset 3 and have the background be uncolored so we can
# utilize the Windows acrylic rendering".
#
# `btop -p 4` (also reachable via `mios proc`-style) shows only the
# processes section per operator's preset-4 request.
#
# Operator-flagged 2026-05-10 (screenshot): btop launched at preset 3
# but rendered cpu+NET (btop's compiled-in default preset 3) with
# update_ms=2000 (default). That's btop ignoring our config entirely.
# Root cause: btop reads `$XDG_CONFIG_HOME/btop/btop.conf` ->
# `$HOME/.config/btop/btop.conf` and DOESN'T fall back to /etc when
# either is unset/invalid. On the dev VM, `mios` user's $HOME can
# resolve to `/` (the /=git root), and `/.config/btop/btop.conf`
# may not exist if the build-time seed missed that path. Force the
# resolution explicitly via BTOP_CONFIG_DIR so the canonical MiOS
# config under /etc/btop/ is always honored.

[ -n "${PS1:-}" ] || return 0

# Resolve BTOP_CONFIG_DIR if the operator hasn't pinned one. Prefer
# the user's own config if it exists; otherwise fall back to the
# system-wide MiOS preset baked into the image.
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
        command btop -p 3 "$@"
    else
        command btop "$@"
    fi
}
