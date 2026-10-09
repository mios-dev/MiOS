# shellcheck shell=bash
# AI-hint: Dispatches the interactive shell startup verb defined in mios.toml [terminal.startup] to the terminal on login, ensuring the MiOS dashboard or "mini" view is ren...
# AI-doc: usr/share/doc/mios/manual/profile.d.md

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0
[ -z "${MIOS_MOTD_SHOWN:-}" ] || return 0
[ -z "${TMUX:-}" ] || return 0
[ -z "${STY:-}" ] || return 0
[ -z "${MIOS_SKIP_MOTD:-}" ] || return 0

_mios_startup_verb() {
    local verb
    verb="$(/usr/bin/mios-toml-get terminal.startup linux)" || return
    if [ -z "$verb" ]; then
        verb="$(/usr/bin/mios-toml-get terminal.startup verb)" || return
    fi
    case "$verb" in
        ''|*[!a-zA-Z0-9_-]*) printf '[FAIL] Invalid or missing resolved terminal.startup.linux\n' >&2; return 1 ;;
    esac
    printf '%s' "$verb"
}

_mios_verb="$(_mios_startup_verb)" || return 1
if [ -n "$_mios_verb" ]; then
    if type mios 2>/dev/null | head -1 | grep -q 'function'; then
        mios "$_mios_verb"
    fi
fi

MIOS_MOTD_SHOWN=1
export MIOS_MOTD_SHOWN
unset _mios_verb
