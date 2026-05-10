# /etc/profile.d/zz-mios-motd.sh
#
# MiOS interactive-shell startup verb dispatcher. The dotfile is a
# THIN wrapper -- it does NOT inline-print anything. Whatever shows
# up on terminal spawn is the verb declared in mios.toml
# [terminal.startup].linux (vendor default = "mini"). Operator
# 2026-05-10: "have the bash and pwsh/WT environment/dotfile(s)
# automatically run mios dash on open/launch--NOT PRINT ON LAUNCH!!!
# THE ACTUAL ENV/DOTFILE(S) SHOULD DICTATE THE COMMANDS/VERBS AND
# WHATS RUN ON CONSOLE SPAWN(ALL PLATFORMS GLOBALLY)--ALL SOURCED
# FROM THE MIOS.TOML"
#
# Cross-platform parity: the Windows pwsh profile body has the same
# dispatch, reading [terminal.startup].windows from the same TOML.
# Both default to "mini" (compact framed dashboard). The FULL
# `mios dash` render (ASCII banner + services + sys specs) is NOT
# auto-fired -- operators run it explicitly when they want it.
#
# The `zz-` prefix forces this to sort last in /etc/profile.d/, so
# /etc/profile.d/mios-env.sh + /etc/profile.d/mios-verbs.sh have
# already loaded by the time we dispatch.
#
# Skipped when:
#   - $PS1 unset (non-interactive shell)
#   - stdin/stdout are not TTYs (cron, sudo, scripted bash -c, ...)
#   - $MIOS_MOTD_SHOWN already set (already shown in this session)
#   - $TMUX or $STY set (re-printing inside every new tmux/screen
#     pane is too noisy; first parent shell already saw it)
#   - $MIOS_SKIP_MOTD set (operator opt-out)
#
# Compatible with bash, sh, zsh, dash login shells -- avoids any
# bashism so /bin/sh sources it cleanly.

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0
[ -z "${MIOS_MOTD_SHOWN:-}" ] || return 0
[ -z "${TMUX:-}" ] || return 0
[ -z "${STY:-}" ] || return 0
[ -z "${MIOS_SKIP_MOTD:-}" ] || return 0

# Resolve startup verb from mios.toml [terminal.startup]. Per-platform
# .linux key wins over the cross-platform .verb key. Layered overlay
# precedence: ~/.config (operator) > /etc/mios (host) > /usr/share/mios
# (vendor). Empty value = silent shell.
_mios_startup_verb() {
    local toml verb section_started key val
    for toml in \
        "${HOME:-/var/home/mios}/.config/mios/mios.toml" \
        /etc/mios/mios.toml \
        /usr/share/mios/mios.toml; do
        [ -r "$toml" ] || continue
        # awk: print value of [terminal.startup].linux first, fall back
        # to .verb. Prefer per-platform key.
        verb="$(awk '
            BEGIN { in_section=0; linux_val=""; verb_val="" }
            /^\[/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                in_section = (line == "[terminal.startup]") ? 1 : 0
                next
            }
            in_section && /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                eq=index(line, "="); if (eq==0) next
                key=substr(line, 1, eq-1); val=substr(line, eq+1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
                gsub(/^"|"$/, "", val)
                if (key == "linux") linux_val = val
                if (key == "verb")  verb_val  = val
            }
            END { if (linux_val != "") print linux_val; else print verb_val }
        ' "$toml" 2>/dev/null)"
        if [ -n "$verb" ]; then
            printf '%s' "$verb"
            return 0
        fi
    done
    # Vendor fallback: mini (the compact framed dashboard).
    printf 'mini'
}

_mios_verb="$(_mios_startup_verb)"
if [ -n "$_mios_verb" ]; then
    # The mios() function is defined by /etc/profile.d/mios-verbs.sh
    # (loaded earlier in this profile.d sequence because of `zz-`).
    # Type-check it as a function before invoking, in case verb-loading
    # was suppressed (e.g., $PS1 unset for some odd login flow).
    if type mios 2>/dev/null | head -1 | grep -q 'function'; then
        mios "$_mios_verb"
    fi
fi

MIOS_MOTD_SHOWN=1
export MIOS_MOTD_SHOWN
unset _mios_verb
