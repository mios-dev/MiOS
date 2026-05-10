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
# Operator can bypass by passing any explicit -p / --preset arg:
#   btop          -> btop -p 3
#   btop -p 4     -> btop -p 4         (operator override wins)
#   btop --preset 1 -> btop --preset 1 (operator override wins)
#
# Interactive-shell only; cron/scripted btop sees the real binary.

[ -n "${PS1:-}" ] || return 0

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
